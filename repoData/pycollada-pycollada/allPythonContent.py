__FILENAME__ = animation
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains objects representing animations."""

from collada import source
from collada.common import DaeObject, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError

class Animation(DaeObject):
    """Class for holding animation data coming from <animation> tags."""

    def __init__(self, id, name, sourceById, children, xmlnode=None):
        self.id = id
        self.name = name
        self.children = children
        self.sourceById = sourceById
        self.xmlnode = xmlnode
        if self.xmlnode is None:
            self.xmlnode = None

    @staticmethod
    def load( collada, localscope, node ):
        id = node.get('id') or ''
        name = node.get('name') or ''

        sourcebyid = localscope
        sources = []
        sourcenodes = node.findall(tag('source'))
        for sourcenode in sourcenodes:
            ch = source.Source.load(collada, {}, sourcenode)
            sources.append(ch)
            sourcebyid[ch.id] = ch

        child_nodes = node.findall(tag('animation'))
        children = []
        for child in child_nodes:
            try:
                child = Animation.load(collada, sourcebyid, child)
                children.append(child)
            except DaeError as ex:
                collada.handleError(ex)

        anim = Animation(id, name, sourcebyid, children, node)
        return anim

    def __str__(self): return '<Animation id=%s, children=%d>' % (self.id, len(self.children))
    def __repr__(self): return str(self)

########NEW FILE########
__FILENAME__ = asset
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains COLLADA asset information."""

import numpy
import datetime
import dateutil.parser

from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import _correctValInNode
from collada.xmlutil import etree as ElementTree


class UP_AXIS:
    """The up-axis of the collada document."""
    X_UP = 'X_UP'
    """Indicates X direction is up"""
    Y_UP = 'Y_UP'
    """Indicates Y direction is up"""
    Z_UP = 'Z_UP'
    """Indicates Z direction is up"""

class Contributor(DaeObject):
    """Defines authoring information for asset management"""

    def __init__(self, author=None, authoring_tool=None, comments=None, copyright=None, source_data=None, xmlnode=None):
        """Create a new contributor

        :param str author:
          The author's name
        :param str authoring_tool:
          Name of the authoring tool
        :param str comments:
          Comments from the contributor
        :param str copyright:
          Copyright information
        :param str source_data:
          URI referencing the source data
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.author = author
        """Contains a string with the author's name."""
        self.authoring_tool = authoring_tool
        """Contains a string with the name of the authoring tool."""
        self.comments = comments
        """Contains a string with comments from this contributor."""
        self.copyright = copyright
        """Contains a string with copyright information."""
        self.source_data = source_data
        """Contains a string with a URI referencing the source data for this asset."""

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the contributor."""
        else:
            self.xmlnode = E.contributor()
            if author is not None:
                self.xmlnode.append(E.author(str(author)))
            if authoring_tool is not None:
                self.xmlnode.append(E.authoring_tool(str(authoring_tool)))
            if comments is not None:
                self.xmlnode.append(E.comments(str(comments)))
            if copyright is not None:
                self.xmlnode.append(E.copyright(str(copyright)))
            if source_data is not None:
                self.xmlnode.append(E.source_data(str(source_data)))

    @staticmethod
    def load(collada, localscope, node):
        author = node.find( tag('author') )
        authoring_tool = node.find( tag('authoring_tool') )
        comments = node.find( tag('comments') )
        copyright = node.find( tag('copyright') )
        source_data = node.find( tag('source_data') )
        if author is not None: author = author.text
        if authoring_tool is not None: authoring_tool = authoring_tool.text
        if comments is not None: comments = comments.text
        if copyright is not None: copyright = copyright.text
        if source_data is not None: source_data = source_data.text
        return Contributor(author=author, authoring_tool=authoring_tool,
                           comments=comments, copyright=copyright, source_data=source_data, xmlnode=node)

    def save(self):
        """Saves the contributor info back to :attr:`xmlnode`"""
        _correctValInNode(self.xmlnode, 'author', self.author)
        _correctValInNode(self.xmlnode, 'authoring_tool', self.authoring_tool)
        _correctValInNode(self.xmlnode, 'comments', self.comments)
        _correctValInNode(self.xmlnode, 'copyright', self.copyright)
        _correctValInNode(self.xmlnode, 'source_data', self.source_data)

    def __str__(self): return '<Contributor author=%s>' % (str(self.author),)
    def __repr__(self): return str(self)

class Asset(DaeObject):
    """Defines asset-management information"""

    def __init__(self, created=None, modified=None, title=None, subject=None, revision=None,
               keywords=None, unitname=None, unitmeter=None, upaxis=None, contributors=None, xmlnode=None):
        """Create a new set of information about an asset

        :param datetime.datetime created:
          When the asset was created. If None, this will be set to the current date and time.
        :param datetime.datetime modified:
          When the asset was modified. If None, this will be set to the current date and time.
        :param str title:
          The title of the asset
        :param str subject:
          The description of the topical subject of the asset
        :param str revision:
          Revision information about the asset
        :param str keywords:
          A list of words used for search criteria for the asset
        :param str unitname:
          The name of the unit of distance for this asset
        :param float unitmeter:
          How many real-world meters are in one distance unit
        :param `collada.asset.UP_AXIS` upaxis:
          The up-axis of the asset. If None, this will be set to Y_UP
        :param list contributors:
          The list of contributors for the asset
        :param xmlnode:
          If loaded from xml, the xml node

        """

        if created is None:
            created = datetime.datetime.now()
        self.created = created
        """Instance of :class:`datetime.datetime` indicating when the asset was created"""

        if modified is None:
            modified = datetime.datetime.now()
        self.modified = modified
        """Instance of :class:`datetime.datetime` indicating when the asset was modified"""

        self.title = title
        """String containing the title of the asset"""
        self.subject = subject
        """String containing the description of the topical subject of the asset"""
        self.revision = revision
        """String containing revision information about the asset"""
        self.keywords = keywords
        """String containing a list of words used for search criteria for the asset"""
        self.unitname = unitname
        """String containing the name of the unit of distance for this asset"""
        self.unitmeter = unitmeter
        """Float containing how many real-world meters are in one distance unit"""

        if upaxis is None:
            upaxis = UP_AXIS.Y_UP
        self.upaxis = upaxis
        """Instance of type :class:`collada.asset.UP_AXIS` indicating the up-axis of the asset"""

        if contributors is None:
            contributors = []
        self.contributors = contributors
        """A list of instances of :class:`collada.asset.Contributor`"""

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the asset."""
        else:
            self._recreateXmlNode()

    def _recreateXmlNode(self):
        self.xmlnode = E.asset()
        for contributor in self.contributors:
            self.xmlnode.append(contributor.xmlnode)
        self.xmlnode.append(E.created(self.created.isoformat()))
        if self.keywords is not None:
            self.xmlnode.append(E.keywords(self.keywords))
        self.xmlnode.append(E.modified(self.modified.isoformat()))
        if self.revision is not None:
            self.xmlnode.append(E.revision(self.revision))
        if self.subject is not None:
            self.xmlnode.append(E.subject(self.subject))
        if self.title is not None:
            self.xmlnode.append(E.title(self.title))
        if self.unitmeter is not None and self.unitname is not None:
            self.xmlnode.append(E.unit(name=self.unitname, meter=str(self.unitmeter)))
        self.xmlnode.append(E.up_axis(self.upaxis))

    def save(self):
        """Saves the asset info back to :attr:`xmlnode`"""
        self._recreateXmlNode()

    @staticmethod
    def load(collada, localscope, node):
        contributornodes = node.findall( tag('contributor') )
        contributors = []
        for contributornode in contributornodes:
            contributors.append(Contributor.load(collada, localscope, contributornode))

        created = node.find( tag('created') )
        if created is not None:
            try: created = dateutil.parser.parse(created.text)
            except: created = None

        keywords = node.find( tag('keywords') )
        if keywords is not None: keywords = keywords.text

        modified = node.find( tag('modified') )
        if modified is not None:
            try: modified = dateutil.parser.parse(modified.text)
            except: modified = None

        revision = node.find( tag('revision') )
        if revision is not None: revision = revision.text

        subject = node.find( tag('subject') )
        if subject is not None: subject = subject.text

        title = node.find( tag('title') )
        if title is not None: title = title.text

        unitnode = node.find( tag('unit') )
        if unitnode is not None:
            unitname = unitnode.get('name')
            try: unitmeter = float(unitnode.get('meter'))
            except:
                unitname = None
                unitmeter = None
        else:
            unitname = None
            unitmeter = None

        upaxis = node.find( tag('up_axis') )
        if upaxis is not None:
            upaxis = upaxis.text
            if not(upaxis == UP_AXIS.X_UP or upaxis == UP_AXIS.Y_UP or \
                    upaxis == UP_AXIS.Z_UP):
                upaxis = None

        return Asset(created=created, modified=modified, title=title,
                subject=subject, revision=revision, keywords=keywords,
                unitname=unitname, unitmeter=unitmeter, upaxis=upaxis,
                contributors=contributors, xmlnode=node)

    def __str__(self):
        return '<Asset title=%s>' % (str(self.title),)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = camera
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains objects for representing cameras"""

import numpy

from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError
from collada.xmlutil import etree as ElementTree


class Camera(DaeObject):
    """Base camera class holding data from <camera> tags."""

    @staticmethod
    def load(collada, localscope, node):
        tecnode = node.find('%s/%s' % (tag('optics'),tag('technique_common')))
        if tecnode is None or len(tecnode) == 0:
            raise DaeIncompleteError('Missing common technique in camera')
        camnode = tecnode[0]
        if camnode.tag == tag('perspective'):
            return PerspectiveCamera.load(collada, localscope, node)
        elif camnode.tag == tag('orthographic'):
            return OrthographicCamera.load(collada, localscope, node)
        else:
            raise DaeUnsupportedError('Unrecognized camera type: %s' % camnode.tag)


class PerspectiveCamera(Camera):
    """Perspective camera as defined in COLLADA tag <perspective>."""

    def __init__(self, id, znear, zfar, xfov=None, yfov=None,
            aspect_ratio=None, xmlnode = None):
        """Create a new perspective camera.

        Note: ``aspect_ratio = tan(0.5*xfov) / tan(0.5*yfov)``

        You can specify one of:
         * :attr:`xfov` alone
         * :attr:`yfov` alone
         * :attr:`xfov` and :attr:`yfov`
         * :attr:`xfov` and :attr:`aspect_ratio`
         * :attr:`yfov` and :attr:`aspect_ratio`

        Any other combination will raise :class:`collada.common.DaeMalformedError`

        :param str id:
          Identifier for the camera
        :param float znear:
          Distance to the near clipping plane
        :param float zfar:
          Distance to the far clipping plane
        :param float xfov:
          Horizontal field of view, in degrees
        :param float yfov:
          Vertical field of view, in degrees
        :param float aspect_ratio:
          Aspect ratio of the field of view
        :param xmlnode:
          If loaded from xml, the xml node

        """

        self.id = id
        """Identifier for the camera"""
        self.xfov = xfov
        """Horizontal field of view, in degrees"""
        self.yfov = yfov
        """Vertical field of view, in degrees"""
        self.aspect_ratio = aspect_ratio
        """Aspect ratio of the field of view"""
        self.znear = znear
        """Distance to the near clipping plane"""
        self.zfar = zfar
        """Distance to the far clipping plane"""

        self._checkValidParams()

        if xmlnode is not  None:
            self.xmlnode = xmlnode
            """ElementTree representation of the data."""
        else:
            self._recreateXmlNode()

    def _recreateXmlNode(self):
        perspective_node = E.perspective()
        if self.xfov is not None:
            perspective_node.append(E.xfov(str(self.xfov)))
        if self.yfov is not None:
            perspective_node.append(E.yfov(str(self.yfov)))
        if self.aspect_ratio is not None:
            perspective_node.append(E.aspect_ratio(str(self.aspect_ratio)))
        perspective_node.append(E.znear(str(self.znear)))
        perspective_node.append(E.zfar(str(self.zfar)))
        self.xmlnode = E.camera(
            E.optics(
                E.technique_common(perspective_node)
            )
        , id=self.id, name=self.id)

    def _checkValidParams(self):
        if self.xfov is not None and self.yfov is None \
                and self.aspect_ratio is None:
            pass
        elif self.xfov is None and self.yfov is not None \
                and self.aspect_ratio is None:
            pass
        elif self.xfov is not None and self.yfov is None \
                and self.aspect_ratio is not None:
            pass
        elif self.xfov is None and self.yfov is not None \
                and self.aspect_ratio is not None:
            pass
        elif self.xfov is not None and self.yfov is not None \
                and self.aspect_ratio is None:
            pass
        else:
            raise DaeMalformedError("Received invalid combination of xfov (%s), yfov (%s), and aspect_ratio (%s)" %
                    (str(self.xfov), str(self.yfov), str(self.aspect_ratio)))

    def save(self):
        """Saves the perspective camera's properties back to xmlnode"""
        self._checkValidParams()
        self._recreateXmlNode()


    @staticmethod
    def load(collada, localscope, node):
        persnode = node.find( '%s/%s/%s'%(tag('optics'),tag('technique_common'),
            tag('perspective') ))

        if persnode is None:
            raise DaeIncompleteError('Missing perspective for camera definition')

        xfov = persnode.find( tag('xfov') )
        yfov = persnode.find( tag('yfov') )
        aspect_ratio = persnode.find( tag('aspect_ratio') )
        znearnode = persnode.find( tag('znear') )
        zfarnode = persnode.find( tag('zfar') )
        id = node.get('id', '')

        try:
            if xfov is not None:
                xfov = float(xfov.text)
            if yfov is not None:
                yfov = float(yfov.text)
            if aspect_ratio is not None:
                aspect_ratio = float(aspect_ratio.text)
            znear = float(znearnode.text)
            zfar = float(zfarnode.text)
        except (TypeError, ValueError) as ex:
            raise DaeMalformedError('Corrupted float values in camera definition')

        #There are some exporters that incorrectly output all three of these.
        # Worse, they actually got the caculation of aspect_ratio wrong!
        # So instead of failing to load, let's just add one more hack because of terrible exporters
        if xfov is not None and yfov is not None and aspect_ratio is not None:
            aspect_ratio = None

        return PerspectiveCamera(id, znear, zfar, xfov=xfov, yfov=yfov,
                aspect_ratio=aspect_ratio, xmlnode=node)

    def bind(self, matrix):
        """Create a bound camera of itself based on a transform matrix.

        :param numpy.array matrix:
          A numpy transformation matrix of size 4x4

        :rtype: :class:`collada.camera.BoundPerspectiveCamera`

        """
        return BoundPerspectiveCamera(self, matrix)

    def __str__(self): return '<PerspectiveCamera id=%s>' % self.id
    def __repr__(self): return str(self)

class OrthographicCamera(Camera):
    """Orthographic camera as defined in COLLADA tag <orthographic>."""

    def __init__(self, id, znear, zfar, xmag=None, ymag=None, aspect_ratio=None, xmlnode = None):
        """Create a new orthographic camera.

        Note: ``aspect_ratio = xmag / ymag``

        You can specify one of:
         * :attr:`xmag` alone
         * :attr:`ymag` alone
         * :attr:`xmag` and :attr:`ymag`
         * :attr:`xmag` and :attr:`aspect_ratio`
         * :attr:`ymag` and :attr:`aspect_ratio`

        Any other combination will raise :class:`collada.common.DaeMalformedError`

        :param str id:
          Identifier for the camera
        :param float znear:
          Distance to the near clipping plane
        :param float zfar:
          Distance to the far clipping plane
        :param float xmag:
          Horizontal magnification of the view
        :param float ymag:
          Vertical magnification of the view
        :param float aspect_ratio:
          Aspect ratio of the field of view
        :param xmlnode:
          If loaded from xml, the xml node

        """

        self.id = id
        """Identifier for the camera"""
        self.xmag = xmag
        """Horizontal magnification of the view"""
        self.ymag = ymag
        """Vertical magnification of the view"""
        self.aspect_ratio = aspect_ratio
        """Aspect ratio of the field of view"""
        self.znear = znear
        """Distance to the near clipping plane"""
        self.zfar = zfar
        """Distance to the far clipping plane"""

        self._checkValidParams()

        if xmlnode is not  None:
            self.xmlnode = xmlnode
            """ElementTree representation of the data."""
        else:
            self._recreateXmlNode()

    def _recreateXmlNode(self):
        orthographic_node = E.orthographic()
        if self.xmag is not None:
            orthographic_node.append(E.xmag(str(self.xmag)))
        if self.ymag is not None:
            orthographic_node.append(E.ymag(str(self.ymag)))
        if self.aspect_ratio is not None:
            orthographic_node.append(E.aspect_ratio(str(self.aspect_ratio)))
        orthographic_node.append(E.znear(str(self.znear)))
        orthographic_node.append(E.zfar(str(self.zfar)))
        self.xmlnode = E.camera(
            E.optics(
                E.technique_common(orthographic_node)
            )
        , id=self.id, name=self.id)

    def _checkValidParams(self):
        if self.xmag is not None and self.ymag is None \
                and self.aspect_ratio is None:
            pass
        elif self.xmag is None and self.ymag is not None \
                and self.aspect_ratio is None:
            pass
        elif self.xmag is not None and self.ymag is None \
                and self.aspect_ratio is not None:
            pass
        elif self.xmag is None and self.ymag is not None \
                and self.aspect_ratio is not None:
            pass
        elif self.xmag is not None and self.ymag is not None \
                and self.aspect_ratio is None:
            pass
        else:
            raise DaeMalformedError("Received invalid combination of xmag (%s), ymag (%s), and aspect_ratio (%s)" %
                    (str(self.xmag), str(self.ymag), str(self.aspect_ratio)))

    def save(self):
        """Saves the orthographic camera's properties back to xmlnode"""
        self._checkValidParams()
        self._recreateXmlNode()


    @staticmethod
    def load(collada, localscope, node):
        orthonode = node.find('%s/%s/%s' % (
            tag('optics'),
            tag('technique_common'),
            tag('orthographic')))

        if orthonode is None: raise DaeIncompleteError('Missing orthographic for camera definition')

        xmag = orthonode.find( tag('xmag') )
        ymag = orthonode.find( tag('ymag') )
        aspect_ratio = orthonode.find( tag('aspect_ratio') )
        znearnode = orthonode.find( tag('znear') )
        zfarnode = orthonode.find( tag('zfar') )
        id = node.get('id', '')

        try:
            if xmag is not None:
                xmag = float(xmag.text)
            if ymag is not None:
                ymag = float(ymag.text)
            if aspect_ratio is not None:
                aspect_ratio = float(aspect_ratio.text)
            znear = float(znearnode.text)
            zfar = float(zfarnode.text)
        except (TypeError, ValueError) as ex:
            raise DaeMalformedError('Corrupted float values in camera definition')

        #There are some exporters that incorrectly output all three of these.
        # Worse, they actually got the caculation of aspect_ratio wrong!
        # So instead of failing to load, let's just add one more hack because of terrible exporters
        if xmag is not None and ymag is not None and aspect_ratio is not None:
            aspect_ratio = None

        return OrthographicCamera(id, znear, zfar, xmag=xmag, ymag=ymag,
                aspect_ratio=aspect_ratio, xmlnode=node)

    def bind(self, matrix):
        """Create a bound camera of itself based on a transform matrix.

        :param numpy.array matrix:
          A numpy transformation matrix of size 4x4

        :rtype: :class:`collada.camera.BoundOrthographicCamera`

        """
        return BoundOrthographicCamera(self, matrix)

    def __str__(self):
        return '<OrthographicCamera id=%s>' % self.id

    def __repr__(self):
        return str(self)

class BoundCamera(object):
    """Base class for bound cameras"""
    pass

class BoundPerspectiveCamera(BoundCamera):
    """Perspective camera bound to a scene with a transform. This gets created when a
        camera is instantiated in a scene. Do not create this manually."""

    def __init__(self, cam, matrix):
        self.xfov = cam.xfov
        """Horizontal field of view, in degrees"""
        self.yfov = cam.yfov
        """Vertical field of view, in degrees"""
        self.aspect_ratio = cam.aspect_ratio
        """Aspect ratio of the field of view"""
        self.znear = cam.znear
        """Distance to the near clipping plane"""
        self.zfar = cam.zfar
        """Distance to the far clipping plane"""
        self.matrix = matrix
        """The matrix bound to"""
        self.position = matrix[:3,3]
        """The position of the camera"""
        self.direction = -matrix[:3,2]
        """The direction the camera is facing"""
        self.up = matrix[:3,1]
        """The up vector of the camera"""
        self.original = cam
        """Original :class:`collada.camera.PerspectiveCamera` object this is bound to."""

    def __str__(self):
        return '<BoundPerspectiveCamera bound to %s>' % self.original.id

    def __repr__(self):
        return str(self)

class BoundOrthographicCamera(BoundCamera):
    """Orthographic camera bound to a scene with a transform. This gets created when a
        camera is instantiated in a scene. Do not create this manually."""

    def __init__(self, cam, matrix):
        self.xmag = cam.xmag
        """Horizontal magnification of the view"""
        self.ymag = cam.ymag
        """Vertical magnification of the view"""
        self.aspect_ratio = cam.aspect_ratio
        """Aspect ratio of the field of view"""
        self.znear = cam.znear
        """Distance to the near clipping plane"""
        self.zfar = cam.zfar
        """Distance to the far clipping plane"""
        self.matrix = matrix
        """The matrix bound to"""
        self.position = matrix[:3,3]
        """The position of the camera"""
        self.direction = -matrix[:3,2]
        """The direction the camera is facing"""
        self.up = matrix[:3,1]
        """The up vector of the camera"""
        self.original = cam
        """Original :class:`collada.camera.OrthographicCamera` object this is bound to."""

    def __str__(self):
        return '<BoundOrthographicCamera bound to %s>' % self.original.id

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = common
from collada.xmlutil import etree, ElementMaker, COLLADA_NS

E = ElementMaker(namespace=COLLADA_NS, nsmap={None: COLLADA_NS})


def tag(text):
    return str(etree.QName(COLLADA_NS, text))


class DaeObject(object):
    """This class is the abstract interface to all collada objects.

    Every <tag> in a COLLADA that we recognize and load has mirror
    class deriving from this one. All instances will have at least
    a :meth:`load` method which creates the object from an xml node and
    an attribute called :attr:`xmlnode` with the ElementTree representation
    of the data. Even if it was created on the fly. If the object is
    not read-only, it will also have a :meth:`save` method which saves the
    object's information back to the :attr:`xmlnode` attribute.

    """

    xmlnode = None
    """ElementTree representation of the data."""

    @staticmethod
    def load(collada, localscope, node):
        """Load and return a class instance from an XML node.

        Inspect the data inside node, which must match
        this class tag and create an instance out of it.

        :param collada.Collada collada:
          The collada file object where this object lives
        :param dict localscope:
          If there is a local scope where we should look for local ids
          (sid) this is the dictionary. Otherwise empty dict ({})
        :param node:
          An Element from python's ElementTree API

        """
        raise Exception('Not implemented')

    def save(self):
        """Put all the data to the internal xml node (xmlnode) so it can be serialized."""

class DaeError(Exception):
    """General DAE exception."""
    def __init__(self, msg):
        super(DaeError,self).__init__()
        self.msg = msg

    def __str__(self):
        return type(self).__name__ + ': ' + self.msg

    def __repr__(self):
        return type(self).__name__ + '("' + self.msg + '")'

class DaeIncompleteError(DaeError):
    """Raised when needed data for an object isn't there."""
    pass

class DaeBrokenRefError(DaeError):
    """Raised when a referenced object is not found in the scope."""
    pass

class DaeMalformedError(DaeError):
    """Raised when data is found to be corrupted in some way."""
    pass

class DaeUnsupportedError(DaeError):
    """Raised when some unexpectedly unsupported feature is found."""
    pass

class DaeSaveValidationError(DaeError):
    """Raised when XML validation fails when saving."""
    pass


########NEW FILE########
__FILENAME__ = controller
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains objects representing controllers. Currently has partial
    support for loading Skin and Morph. **This module is highly
    experimental. More support will be added in version 0.4.**"""

import numpy

from collada import source
from collada.common import DaeObject, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.geometry import Geometry
from collada.util import checkSource
from collada.xmlutil import etree as ElementTree


class Controller(DaeObject):
    """Base controller class holding data from <controller> tags."""

    def bind(self, matrix, materialnodebysymbol):
        pass

    @staticmethod
    def load( collada, localscope, node ):
        controller = node.find(tag('skin'))
        if controller is None:
            controller = node.find(tag('morph'))
        if controller is None: raise DaeUnsupportedError('Unknown controller node')

        sourcebyid = {}
        sources = []
        sourcenodes = node.findall('%s/%s'%(controller.tag, tag('source')))
        for sourcenode in sourcenodes:
            ch = source.Source.load(collada, {}, sourcenode)
            sources.append(ch)
            sourcebyid[ch.id] = ch

        if controller.tag == tag('skin'):
            return Skin.load(collada, sourcebyid, controller, node)
        else:
            return Morph.load(collada, sourcebyid, controller, node)

class BoundController( object ):
    """Base class for a controller bound to a transform matrix and materials mapping."""

class Skin(Controller):
    """Class containing data collada holds in the <skin> tag"""

    def __init__(self, sourcebyid, bind_shape_matrix, joint_source, joint_matrix_source,
                 weight_source, weight_joint_source, vcounts, vertex_weight_index,
                 offsets, geometry, controller_node=None, skin_node=None):
        """Create a skin.

        :Parameters:
          sourceById
            A dict mapping id's to a collada source
          bind_shape_matrix
            A numpy array of floats (pre-shape)
          joint_source
            The string id for the joint source
          joint_matrix_source
            The string id for the joint matrix source
          weight_source
            The string id for the weight source
          weight_joint_source
            The string id for the joint source of weights
          vcounts
            A list with the number of influences on each vertex
          vertex_weight_index
            An array with the indexes as they come from <v> array
          offsets
            A list with the offsets in the weight index array for each source
            in (joint, weight)
          geometry
            The source geometry this should be applied to (geometry.Geometry)
          controller_node
            XML node of the <controller> tag which is the parent of this
          skin_node
            XML node of the <skin> tag if this is from there

        """
        self.sourcebyid = sourcebyid
        self.bind_shape_matrix = bind_shape_matrix
        self.joint_source = joint_source
        self.joint_matrix_source = joint_matrix_source
        self.weight_source = weight_source
        self.weight_joint_source = weight_joint_source
        self.vcounts = vcounts
        self.vertex_weight_index = vertex_weight_index
        self.offsets = offsets
        self.geometry = geometry
        self.controller_node = controller_node
        self.skin_node = skin_node
        self.xmlnode = controller_node

        if not type(self.geometry) is Geometry:
            raise DaeMalformedError('Invalid reference geometry in skin')

        self.id = controller_node.get('id')
        if self.id is None:
            raise DaeMalformedError('Controller node requires an ID')

        self.nindices = max(self.offsets) + 1

        if len(bind_shape_matrix) != 16:
            raise DaeMalformedError('Corrupted bind shape matrix in skin')
        self.bind_shape_matrix.shape = (4,4)

        if not(joint_source in sourcebyid and joint_matrix_source in sourcebyid):
            raise DaeBrokenRefError("Input in joints not found")
        if not(type(sourcebyid[joint_source]) is source.NameSource or type(sourcebyid[joint_source]) is source.IDRefSource):
            raise DaeIncompleteError("Could not find joint name input for skin")
        if not type(sourcebyid[joint_matrix_source]) is source.FloatSource:
            raise DaeIncompleteError("Could not find joint matrix source for skin")
        joint_names = [j for j in sourcebyid[joint_source]]
        joint_matrices = sourcebyid[joint_matrix_source].data
        joint_matrices.shape = (-1,4,4)
        if len(joint_names) != len(joint_matrices):
            raise DaeMalformedError("Skin joint and matrix inputs must be same length")
        self.joint_matrices = {}
        for n,m in zip(joint_names, joint_matrices):
            self.joint_matrices[n] = m

        if not(weight_source in sourcebyid and weight_joint_source in sourcebyid):
            raise DaeBrokenRefError("Weights input in joints not found")
        if not type(sourcebyid[weight_source]) is source.FloatSource:
            raise DaeIncompleteError("Could not find weight inputs for skin")
        if not(type(sourcebyid[weight_joint_source]) is source.NameSource or type(sourcebyid[weight_joint_source]) is source.IDRefSource):
            raise DaeIncompleteError("Could not find weight joint source input for skin")
        self.weights = sourcebyid[weight_source]
        self.weight_joints = sourcebyid[weight_joint_source]

        try:
            newshape = []
            at = 0
            for ct in self.vcounts:
                this_set = self.vertex_weight_index[self.nindices*at:self.nindices*(at+ct)]
                this_set.shape = (ct, self.nindices)
                newshape.append(numpy.array(this_set))
                at+=ct
            self.index = newshape
        except:
            raise DaeMalformedError('Corrupted vcounts or index in skin weights')

        try:
            self.joint_index = [influence[:, self.offsets[0]] for influence in self.index]
            self.weight_index = [influence[:, self.offsets[1]] for influence in self.index]
        except:
            raise DaeMalformedError('Corrupted joint or weight index in skin')

        self.max_joint_index = numpy.max( [numpy.max(joint) if len(joint) > 0 else 0 for joint in self.joint_index] )
        self.max_weight_index = numpy.max( [numpy.max(weight) if len(weight) > 0 else 0 for weight in self.weight_index] )
        checkSource(self.weight_joints, ('JOINT',), self.max_joint_index)
        checkSource(self.weights, ('WEIGHT',), self.max_weight_index)

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        return self.index[i]

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound morph from this one, transform and material mapping"""
        return BoundSkin(self, matrix, materialnodebysymbol)

    @staticmethod
    def load( collada, localscope, skinnode, controllernode ):
        if len(localscope) < 3:
            raise DaeMalformedError('Not enough sources in skin')

        geometry_source = skinnode.get('source')
        if geometry_source is None or len(geometry_source) < 2 \
                or geometry_source[0] != '#':
            raise DaeBrokenRefError('Invalid source attribute of skin node')
        if not geometry_source[1:] in collada.geometries:
            raise DaeBrokenRefError('Source geometry for skin node not found')
        geometry = collada.geometries[geometry_source[1:]]

        bind_shape_mat = skinnode.find(tag('bind_shape_matrix'))
        if bind_shape_mat is None:
            bind_shape_mat = numpy.identity(4, dtype=numpy.float32)
            bind_shape_mat.shape = (-1,)
        else:
            try:
                values = [ float(v) for v in bind_shape_mat.text.split()]
            except ValueError:
                raise DaeMalformedError('Corrupted bind shape matrix in skin')
            bind_shape_mat = numpy.array( values, dtype=numpy.float32 )

        inputnodes = skinnode.findall('%s/%s'%(tag('joints'), tag('input')))
        if inputnodes is None or len(inputnodes) < 2:
            raise DaeIncompleteError("Not enough inputs in skin joints")

        try:
            inputs = [(i.get('semantic'), i.get('source')) for i in inputnodes]
        except ValueError as ex:
            raise DaeMalformedError('Corrupted inputs in skin')

        joint_source = None
        matrix_source = None
        for i in inputs:
            if len(i[1]) < 2 or i[1][0] != '#':
                raise DaeBrokenRefError('Input in skin node %s not found'%i[1])
            if i[0] == 'JOINT':
                joint_source = i[1][1:]
            elif i[0] == 'INV_BIND_MATRIX':
                matrix_source = i[1][1:]

        weightsnode = skinnode.find(tag('vertex_weights'))
        if weightsnode is None:
            raise DaeIncompleteError("No vertex_weights found in skin")
        indexnode = weightsnode.find(tag('v'))
        if indexnode is None:
            raise DaeIncompleteError('Missing indices in skin vertex weights')
        vcountnode = weightsnode.find(tag('vcount'))
        if vcountnode is None:
            raise DaeIncompleteError('Missing vcount in skin vertex weights')
        inputnodes = weightsnode.findall(tag('input'))

        try:
            index = numpy.array([float(v)
                for v in indexnode.text.split()], dtype=numpy.int32)
            vcounts = numpy.array([int(v)
                for v in vcountnode.text.split()], dtype=numpy.int32)
            inputs = [(i.get('semantic'), i.get('source'), int(i.get('offset')))
                           for i in inputnodes]
        except ValueError as ex:
            raise DaeMalformedError('Corrupted index or offsets in skin vertex weights')

        weight_joint_source = None
        weight_source = None
        offsets = [0, 0]
        for i in inputs:
            if len(i[1]) < 2 or i[1][0] != '#':
                raise DaeBrokenRefError('Input in skin node %s not found' % i[1])
            if i[0] == 'JOINT':
                weight_joint_source = i[1][1:]
                offsets[0] = i[2]
            elif i[0] == 'WEIGHT':
                weight_source = i[1][1:]
                offsets[1] = i[2]

        if joint_source is None or weight_source is None:
            raise DaeMalformedError('Not enough inputs for vertex weights in skin')

        return Skin(localscope, bind_shape_mat, joint_source, matrix_source,
                weight_source, weight_joint_source, vcounts, index, offsets,
                geometry, controllernode, skinnode)


class BoundSkin(BoundController):
    """A skin bound to a transform matrix and materials mapping."""

    def __init__(self, skin, matrix, materialnodebysymbol):
        self.matrix = matrix
        self.materialnodebysymbol = materialnodebysymbol
        self.skin = skin
        self.id = skin.id
        self.index = skin.index
        self.joint_matrices = skin.joint_matrices
        self.geometry = skin.geometry.bind(numpy.dot(matrix,skin.bind_shape_matrix), materialnodebysymbol)

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        return self.index[i]

    def getJoint(self, i):
        return self.skin.weight_joints[i]

    def getWeight(self, i):
        return self.skin.weights[i]

    def primitives(self):
        for prim in self.geometry.primitives():
            bsp = BoundSkinPrimitive(prim, self)
            yield bsp


class BoundSkinPrimitive(object):
    """A bound skin bound to a primitive."""

    def __init__(self, primitive, boundskin):
        self.primitive = primitive
        self.boundskin = boundskin

    def __len__(self):
        return len(self.primitive)

    def shapes(self):
        for shape in self.primitive.shapes():
            indices = shape.indices
            yield shape


class Morph(Controller):
    """Class containing data collada holds in the <morph> tag"""

    def __init__(self, source_geometry, target_list, xmlnode=None):
        """Create a morph instance

        :Parameters:
          source_geometry
            The source geometry (Geometry)
          targets
            A list of tuples where each tuple (g,w) contains
            a Geometry (g) and a float weight value (w)
          xmlnode
            When loaded, the xmlnode it comes from

        """
        self.id = xmlnode.get('id')
        if self.id is None:
            raise DaeMalformedError('Controller node requires an ID')
        self.source_geometry = source_geometry
        """The source geometry (Geometry)"""
        self.target_list = target_list
        """A list of tuples where each tuple (g,w) contains
            a Geometry (g) and a float weight value (w)"""

        self.xmlnode = xmlnode
        #TODO

    def __len__(self):
        return len(self.target_list)

    def __getitem__(self, i):
        return self.target_list[i]

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound morph from this one, transform and material mapping"""
        return BoundMorph(self, matrix, materialnodebysymbol)

    @staticmethod
    def load( collada, localscope, morphnode, controllernode ):
        baseid = morphnode.get('source')
        if len(baseid) < 2 or baseid[0] != '#' or \
                not baseid[1:] in collada.geometries:
            raise DaeBrokenRefError('Base source of morph %s not found' % baseid)
        basegeom = collada.geometries[baseid[1:]]

        method = morphnode.get('method')
        if method is None:
            method = 'NORMALIZED'
        if not (method == 'NORMALIZED' or method == 'RELATIVE'):
            raise DaeMalformedError("Morph method must be either NORMALIZED or RELATIVE. Found '%s'" % method)

        inputnodes = morphnode.findall('%s/%s'%(tag('targets'), tag('input')))
        if inputnodes is None or len(inputnodes) < 2:
            raise DaeIncompleteError("Not enough inputs in a morph")

        try:
            inputs = [(i.get('semantic'), i.get('source')) for i in inputnodes]
        except ValueError as ex:
            raise DaeMalformedError('Corrupted inputs in morph')

        target_source = None
        weight_source = None
        for i in inputs:
            if len(i[1]) < 2 or i[1][0] != '#' or not i[1][1:] in localscope:
                raise DaeBrokenRefError('Input in morph node %s not found' % i[1])
            if i[0] == 'MORPH_TARGET':
                target_source = localscope[i[1][1:]]
            elif i[0] == 'MORPH_WEIGHT':
                weight_source = localscope[i[1][1:]]

        if not type(target_source) is source.IDRefSource or \
                not type(weight_source) is source.FloatSource:
            raise DaeIncompleteError("Not enough inputs in targets of morph")

        if len(target_source) != len(weight_source):
            raise DaeMalformedError("Morph inputs must be of same length")

        target_list = []
        for target, weight in zip(target_source, weight_source):
            if len(target) < 1 or not(target in collada.geometries):
                raise DaeBrokenRefError("Targeted geometry %s in morph not found"%target)
            target_list.append((collada.geometries[target], weight[0]))

        return Morph(basegeom, target_list, controllernode)

    def save(self):
        #TODO
        pass


class BoundMorph(BoundController):
    """A morph bound to a transform matrix and materials mapping."""

    def __init__(self, morph, matrix, materialnodebysymbol):
        self.matrix = matrix
        self.materialnodebysymbol = materialnodebysymbol
        self.original = morph

    def __len__(self):
        return len(self.original)

    def __getitem__(self, i):
        return self.original[i]


########NEW FILE########
__FILENAME__ = geometry
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains objects for representing a geometry."""

import numpy

from collada import source
from collada import triangleset
from collada import lineset
from collada import polylist
from collada import polygons
from collada import primitive
from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.xmlutil import etree as ElementTree


class Geometry(DaeObject):
    """A class containing the data coming from a COLLADA <geometry> tag"""

    def __init__(self, collada, id, name, sourcebyid, primitives=None,
            xmlnode=None, double_sided=False):
        """Create a geometry instance

          :param collada.Collada collada:
            The collada object this geometry belongs to
          :param str id:
            A unique string identifier for the geometry
          :param str name:
            A text string naming the geometry
          :param sourcebyid:
            A list of :class:`collada.source.Source` objects or
            a dictionary mapping source ids to the actual objects
          :param list primitives:
            List of primitive objects contained within the geometry.
            Do not set this argument manually. Instead, create a
            :class:`collada.geometry.Geometry` first and then append
            to :attr:`primitives` with the `create*` functions.
          :param xmlnode:
            When loaded, the xmlnode it comes from.
          :param bool double_sided:
            Whether or not the geometry should be rendered double sided

        """
        self.collada = collada
        """The :class:`collada.Collada` object this geometry belongs to"""

        self.id = id
        """The unique string identifier for the geometry"""

        self.name = name
        """The text string naming the geometry"""

        self.double_sided = double_sided
        """A boolean indicating whether or not the geometry should be rendered double sided"""

        self.sourceById = sourcebyid
        """A dictionary containing :class:`collada.source.Source` objects indexed by their id."""

        if isinstance(sourcebyid, list):
            self.sourceById = {}
            for src in sourcebyid:
                self.sourceById[src.id] = src

        self.primitives = []
        """List of primitives (base type :class:`collada.primitive.Primitive`) inside this geometry."""
        if primitives is not None:
            self.primitives = primitives

        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the geometry."""
        else:
            sourcenodes = []
            verticesnode = None
            for srcid, src in self.sourceById.items():
                sourcenodes.append(src.xmlnode)
                if verticesnode is None:
                    #pick first source to be in the useless <vertices> tag
                    verticesnode = E.vertices(E.input(semantic='POSITION', source="#%s"%srcid),
                                              id=srcid + '-vertices')
            meshnode = E.mesh(*sourcenodes)
            meshnode.append(verticesnode)
            self.xmlnode = E.geometry(meshnode)
            if len(self.id) > 0: self.xmlnode.set("id", self.id)
            if len(self.name) > 0: self.xmlnode.set("name", self.name)

    def createLineSet(self, indices, inputlist, materialid):
        """Create a set of lines for use in this geometry instance.

        :param numpy.array indices:
          unshaped numpy array that contains the indices for
          the inputs referenced in inputlist
        :param collada.source.InputList inputlist:
          The inputs for this primitive
        :param str materialid:
          A string containing a symbol that will get used to bind this lineset
          to a material when instantiating into a scene

        :rtype: :class:`collada.lineset.LineSet`
        """
        inputdict = primitive.Primitive._getInputsFromList(self.collada, self.sourceById, inputlist.getList())
        return lineset.LineSet(inputdict, materialid, indices)

    def createTriangleSet(self, indices, inputlist, materialid):
        """Create a set of triangles for use in this geometry instance.

        :param numpy.array indices:
          unshaped numpy array that contains the indices for
          the inputs referenced in inputlist
        :param collada.source.InputList inputlist:
          The inputs for this primitive
        :param str materialid:
          A string containing a symbol that will get used to bind this triangleset
          to a material when instantiating into a scene

        :rtype: :class:`collada.triangleset.TriangleSet`
        """
        inputdict = primitive.Primitive._getInputsFromList(self.collada, self.sourceById, inputlist.getList())
        return triangleset.TriangleSet(inputdict, materialid, indices)

    def createPolylist(self, indices, vcounts, inputlist, materialid):
        """Create a polylist for use with this geometry instance.

        :param numpy.array indices:
          unshaped numpy array that contains the indices for
          the inputs referenced in inputlist
        :param numpy.array vcounts:
          unshaped numpy array that contains the vertex count
          for each polygon in this polylist
        :param collada.source.InputList inputlist:
          The inputs for this primitive
        :param str materialid:
          A string containing a symbol that will get used to bind this polylist
          to a material when instantiating into a scene

        :rtype: :class:`collada.polylist.Polylist`
        """
        inputdict = primitive.Primitive._getInputsFromList(self.collada, self.sourceById, inputlist.getList())
        return polylist.Polylist(inputdict, materialid, indices, vcounts)

    def createPolygons(self, indices, inputlist, materialid):
        """Create a polygons for use with this geometry instance.

        :param numpy.array indices:
          list of unshaped numpy arrays that each contain the indices for
          a single polygon
        :param collada.source.InputList inputlist:
          The inputs for this primitive
        :param str materialid:
          A string containing a symbol that will get used to bind this polygons
          to a material when instantiating into a scene

        :rtype: :class:`collada.polygons.Polygons`
        """
        inputdict = primitive.Primitive._getInputsFromList(self.collada, self.sourceById, inputlist.getList())
        return polygons.Polygons(inputdict, materialid, indices)

    @staticmethod
    def load( collada, localscope, node ):
        id = node.get("id") or ""
        name = node.get("name") or ""
        meshnode = node.find(tag('mesh'))
        if meshnode is None: raise DaeUnsupportedError('Unknown geometry node')
        sourcebyid = {}
        sources = []
        sourcenodes = node.findall('%s/%s'%(tag('mesh'), tag('source')))
        for sourcenode in sourcenodes:
            ch = source.Source.load(collada, {}, sourcenode)
            sources.append(ch)
            sourcebyid[ch.id] = ch

        verticesnode = meshnode.find(tag('vertices'))
        if verticesnode is None:
            vertexsource = None
        else:
            inputnodes = {}
            for inputnode in verticesnode.findall(tag('input')):
                semantic = inputnode.get('semantic')
                inputsource = inputnode.get('source')
                if not semantic or not inputsource or not inputsource.startswith('#'):
                    raise DaeIncompleteError('Bad input definition inside vertices')
                inputnodes[semantic] = sourcebyid.get(inputsource[1:])
            if (not verticesnode.get('id') or len(inputnodes)==0 or
                not 'POSITION' in inputnodes):
                raise DaeIncompleteError('Bad vertices definition in mesh')
            sourcebyid[verticesnode.get('id')] = inputnodes
            vertexsource = verticesnode.get('id')

        double_sided_node = node.find('.//%s//%s' % (tag('extra'), tag('double_sided')))
        double_sided = False
        if double_sided_node is not None and double_sided_node.text is not None:
            try:
                val = int(double_sided_node.text)
                if val == 1:
                    double_sided = True
            except ValueError: pass

        _primitives = []
        for subnode in meshnode:
            if subnode.tag == tag('polylist'):
                _primitives.append( polylist.Polylist.load( collada, sourcebyid, subnode ) )
            elif subnode.tag == tag('triangles'):
                _primitives.append( triangleset.TriangleSet.load( collada, sourcebyid, subnode ) )
            elif subnode.tag == tag('lines'):
                _primitives.append( lineset.LineSet.load( collada, sourcebyid, subnode ) )
            elif subnode.tag == tag('polygons'):
                _primitives.append( polygons.Polygons.load( collada, sourcebyid, subnode ) )
            elif subnode.tag != tag('source') and subnode.tag != tag('vertices') and subnode.tag != tag('extra'):
                raise DaeUnsupportedError('Unknown geometry tag %s' % subnode.tag)
        geom = Geometry(collada, id, name, sourcebyid, _primitives, xmlnode=node, double_sided=double_sided )
        return geom

    def save(self):
        """Saves the geometry back to :attr:`xmlnode`"""
        meshnode = self.xmlnode.find(tag('mesh'))
        for src in self.sourceById.values():
            if isinstance(src, source.Source):
                src.save()
                if src.xmlnode not in meshnode.getchildren():
                    meshnode.insert(0, src.xmlnode)

        deletenodes = []
        for oldsrcnode in meshnode.findall(tag('source')):
            if oldsrcnode not in [src.xmlnode
                    for src in self.sourceById.values()
                    if isinstance(src, source.Source)]:
                deletenodes.append(oldsrcnode)
        for d in deletenodes:
            meshnode.remove(d)

        #Look through primitives to find a vertex source
        vnode = self.xmlnode.find(tag('mesh')).find(tag('vertices'))

        #delete any inputs in vertices tag that no longer exist and find the vertex input
        delete_inputs = []
        for input_node in vnode.findall(tag('input')):
            if input_node.get('semantic') == 'POSITION':
                input_vnode = input_node
            else:
                srcid = input_node.get('source')[1:]
                if srcid not in self.sourceById:
                    delete_inputs.append(input_node)

        for node in delete_inputs:
            vnode.remove(node)

        vert_sources = []
        for prim in self.primitives:
            for src in prim.sources['VERTEX']:
                vert_sources.append(src[2][1:])

        vert_src = vnode.get('id')
        vert_ref = input_vnode.get('source')[1:]

        if not(vert_src in vert_sources or vert_ref in vert_sources) and len(vert_sources) > 0:
            if vert_ref in self.sourceById and vert_ref in vert_sources:
                new_source = vert_ref
            else:
                new_source = vert_sources[0]
            self.sourceById[new_source + '-vertices'] = self.sourceById[new_source]
            input_vnode.set('source', '#' + new_source)
            vnode.set('id', new_source + '-vertices')

        #any source references in primitives that are pointing to the
        # same source that the vertices tag is pointing to to instead
        # point to the vertices id
        vert_src = vnode.get('id')
        vert_ref = input_vnode.get('source')[1:]
        for prim in self.primitives:
            for node in prim.xmlnode.findall(tag('input')):
                src = node.get('source')[1:]
                if src == vert_ref:
                    node.set('source', '#%s' % vert_src)

        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.name)

        for prim in self.primitives:
            if type(prim) is triangleset.TriangleSet and prim.xmlnode.tag != tag('triangles'):
                prim._recreateXmlNode()
            if prim.xmlnode not in meshnode.getchildren():
                meshnode.append(prim.xmlnode)

        deletenodes = []
        primnodes = [prim.xmlnode for prim in self.primitives]
        for child in meshnode.getchildren():
            if child.tag != tag('vertices') and child.tag != tag('source') and child not in primnodes:
                deletenodes.append(child)
        for d in deletenodes:
            meshnode.remove(d)

    def bind(self, matrix, materialnodebysymbol):
        """Binds this geometry to a transform matrix and material mapping.
        The geometry's points get transformed by the given matrix and its
        inputs get mapped to the given materials.

        :param numpy.array matrix:
          A 4x4 numpy float matrix
        :param dict materialnodebysymbol:
          A dictionary with the material symbols inside the primitive
          assigned to :class:`collada.scene.MaterialNode` defined in the
          scene

        :rtype: :class:`collada.geometry.BoundGeometry`

        """
        return BoundGeometry(self, matrix, materialnodebysymbol)

    def __str__(self):
        return '<Geometry id=%s, %d primitives>' % (self.id, len(self.primitives))

    def __repr__(self):
        return str(self)


class BoundGeometry( object ):
    """A geometry bound to a transform matrix and material mapping.
        This gets created when a geometry is instantiated in a scene.
        Do not create this manually."""

    def __init__(self, geom, matrix, materialnodebysymbol):
        self.matrix = matrix
        """The matrix bound to"""
        self.materialnodebysymbol = materialnodebysymbol
        """Dictionary with the material symbols inside the primitive
          assigned to :class:`collada.scene.MaterialNode` defined in the
          scene"""
        self._primitives = geom.primitives
        self.original = geom
        """The original :class:`collada.geometry.Geometry` object this
        is bound to"""

    def __len__(self):
        """Returns the number of primitives in the bound geometry"""
        return len(self._primitives)

    def primitives(self):
        """Returns an iterator that iterates through the primitives in
        the bound geometry. Each value returned will be of base type
        :class:`collada.primitive.BoundPrimitive`"""
        for p in self._primitives:
            boundp = p.bind( self.matrix, self.materialnodebysymbol )
            yield boundp

    def __str__(self):
        return '<BoundGeometry id=%s, %d primitives>' % (self.original.id, len(self))

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = light
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Contains objects for representing lights."""

import numpy

from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import _correctValInNode
from collada.xmlutil import etree as ElementTree


class Light(DaeObject):
    """Base light class holding data from <light> tags."""

    @staticmethod
    def load(collada, localscope, node):
        tecnode = node.find( tag('technique_common') )
        if tecnode is None or len(tecnode) == 0:
            raise DaeIncompleteError('Missing common technique in light')
        lightnode = tecnode[0]
        if lightnode.tag == tag('directional'):
            return DirectionalLight.load( collada, localscope, node )
        elif lightnode.tag == tag('point'):
            return PointLight.load( collada, localscope, node )
        elif lightnode.tag == tag('ambient'):
            return AmbientLight.load( collada, localscope, node )
        elif lightnode.tag == tag('spot'):
            return SpotLight.load( collada, localscope, node )
        else:
            raise DaeUnsupportedError('Unrecognized light type: %s'%lightnode.tag)


class DirectionalLight(Light):
    """Directional light as defined in COLLADA tag <directional> tag."""

    def __init__(self, id, color, xmlnode = None):
        """Create a new directional light.

        :param str id:
          A unique string identifier for the light
        :param tuple color:
          Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The unique string identifier for the light"""
        self.direction = numpy.array( [0, 0, -1], dtype=numpy.float32 )
        #Not documenting this because it doesn't make sense to set the direction
        # of an unbound light. The direction isn't set until binding in a scene.
        self.color = color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the light."""
        else:
            self.xmlnode = E.light(
                E.technique_common(
                    E.directional(
                        E.color(' '.join(map(str, self.color)))
                    )
                )
            , id=self.id, name=self.id)

    def save(self):
        """Saves the light's properties back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        colornode = self.xmlnode.find('%s/%s/%s' % (tag('technique_common'),
            tag('directional'), tag('color')))
        colornode.text = ' '.join(map(str, self.color))


    @staticmethod
    def load(collada, localscope, node):
        colornode = node.find( '%s/%s/%s'%(tag('technique_common'),tag('directional'),
                                           tag('color') ) )
        if colornode is None:
            raise DaeIncompleteError('Missing color for directional light')
        try:
            color = tuple([float(v) for v in colornode.text.split()])
        except ValueError as ex:
            raise DaeMalformedError('Corrupted color values in light definition')
        return DirectionalLight(node.get('id'), color, xmlnode = node)

    def bind(self, matrix):
        """Binds this light to a transform matrix.

        :param numpy.array matrix:
          A 4x4 numpy float matrix

        :rtype: :class:`collada.light.BoundDirectionalLight`

        """
        return BoundDirectionalLight(self, matrix)

    def __str__(self):
        return '<DirectionalLight id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class AmbientLight(Light):
    """Ambient light as defined in COLLADA tag <ambient>."""

    def __init__(self, id, color, xmlnode = None):
        """Create a new ambient light.

        :param str id:
          A unique string identifier for the light
        :param tuple color:
          Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The unique string identifier for the light"""
        self.color = color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the light."""
        else:
            self.xmlnode = E.light(
                E.technique_common(
                    E.ambient(
                        E.color(' '.join(map(str, self.color)))
                    )
                )
            , id=self.id, name=self.id)

    def save(self):
        """Saves the light's properties back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        colornode = self.xmlnode.find('%s/%s/%s' % (tag('technique_common'),
            tag('ambient'), tag('color')))
        colornode.text = ' '.join(map(str, self.color))


    @staticmethod
    def load(collada, localscope, node):
        colornode = node.find('%s/%s/%s' % (tag('technique_common'),
            tag('ambient'), tag('color')))
        if colornode is None:
            raise DaeIncompleteError('Missing color for ambient light')
        try:
            color = tuple( [ float(v) for v in colornode.text.split() ] )
        except ValueError as ex:
            raise DaeMalformedError('Corrupted color values in light definition')
        return AmbientLight(node.get('id'), color, xmlnode = node)

    def bind(self, matrix):
        """Binds this light to a transform matrix.

        :param numpy.array matrix:
          A 4x4 numpy float matrix

        :rtype: :class:`collada.light.BoundAmbientLight`

        """
        return BoundAmbientLight(self, matrix)

    def __str__(self):
        return '<AmbientLight id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class PointLight(Light):
    """Point light as defined in COLLADA tag <point>."""

    def __init__(self, id, color, constant_att=None, linear_att=None,
            quad_att=None, zfar=None, xmlnode = None):
        """Create a new sun light.

        :param str id:
          A unique string identifier for the light
        :param tuple color:
          Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light
        :param float constant_att:
          Constant attenuation factor
        :param float linear_att:
          Linear attenuation factor
        :param float quad_att:
          Quadratic attenuation factor
        :param float zfar:
          Distance to the far clipping plane
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The unique string identifier for the light"""
        self.position = numpy.array( [0, 0, 0], dtype=numpy.float32 )
        #Not documenting this because it doesn't make sense to set the position
        # of an unbound light. The position isn't set until binding in a scene.
        self.color = color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.constant_att = constant_att
        """Constant attenuation factor."""
        self.linear_att = linear_att
        """Linear attenuation factor."""
        self.quad_att = quad_att
        """Quadratic attenuation factor."""
        self.zfar = zfar
        """Distance to the far clipping plane"""

        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the light."""
        else:
            pnode = E.point(
                E.color(' '.join(map(str, self.color ) ))
            )
            if self.constant_att is not None:
                pnode.append(E.constant_attenuation(str(self.constant_att)))
            if self.linear_att is not None:
                pnode.append(E.linear_attenuation(str(self.linear_att)))
            if self.quad_att is not None:
                pnode.append(E.quadratic_attenuation(str(self.quad_att)))
            if self.zfar is not None:
                pnode.append(E.zfar(str(self.zvar)))

            self.xmlnode = E.light(
                E.technique_common(pnode)
            , id=self.id, name=self.id)

    def save(self):
        """Saves the light's properties back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        pnode = self.xmlnode.find( '%s/%s'%(tag('technique_common'),tag('point')) )
        colornode = pnode.find( tag('color') )
        colornode.text = ' '.join(map(str, self.color ) )
        _correctValInNode(pnode, 'constant_attenuation', self.constant_att)
        _correctValInNode(pnode, 'linear_attenuation', self.linear_att)
        _correctValInNode(pnode, 'quadratic_attenuation', self.quad_att)
        _correctValInNode(pnode, 'zfar', self.zfar)

    @staticmethod
    def load(collada, localscope, node):
        pnode = node.find('%s/%s' % (tag('technique_common'), tag('point')))
        colornode = pnode.find( tag('color') )
        if colornode is None:
            raise DaeIncompleteError('Missing color for point light')
        try:
            color = tuple([float(v) for v in colornode.text.split()])
        except ValueError as ex:
            raise DaeMalformedError('Corrupted color values in light definition')
        constant_att = linear_att = quad_att = zfar = None
        qattnode = pnode.find( tag('quadratic_attenuation') )
        cattnode = pnode.find( tag('constant_attenuation') )
        lattnode = pnode.find( tag('linear_attenuation') )
        zfarnode = pnode.find( tag('zfar') )
        try:
            if cattnode is not None:
                constant_att = float(cattnode.text)
            if lattnode is not None:
                linear_att = float(lattnode.text)
            if qattnode is not None:
                quad_att = float(qattnode.text)
            if zfarnode is not None:
                zfar = float(zfarnode.text)
        except ValueError as ex:
            raise DaeMalformedError('Corrupted values in light definition')
        return PointLight(node.get('id'), color, constant_att, linear_att,
                quad_att, zfar, xmlnode = node)

    def bind(self, matrix):
        """Binds this light to a transform matrix.

        :param numpy.array matrix:
          A 4x4 numpy float matrix

        :rtype: :class:`collada.light.BoundPointLight`

        """
        return BoundPointLight(self, matrix)

    def __str__(self):
        return '<PointLight id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class SpotLight(Light):
    """Spot light as defined in COLLADA tag <spot>."""

    def __init__(self, id, color, constant_att=None, linear_att=None,
            quad_att=None, falloff_ang=None, falloff_exp=None, xmlnode = None):
        """Create a new spot light.

        :param str id:
          A unique string identifier for the light
        :param tuple color:
          Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light
        :param float constant_att:
          Constant attenuation factor
        :param float linear_att:
          Linear attenuation factor
        :param float quad_att:
          Quadratic attenuation factor
        :param float falloff_ang:
          Falloff angle
        :param float falloff_exp:
          Falloff exponent
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The unique string identifier for the light"""
        self.color = color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.constant_att = constant_att
        """Constant attenuation factor."""
        self.linear_att = linear_att
        """Linear attenuation factor."""
        self.quad_att = quad_att
        """Quadratic attenuation factor."""
        self.falloff_ang = falloff_ang
        """Falloff angle"""
        self.falloff_exp = falloff_exp
        """Falloff exponent"""

        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the light."""
        else:
            pnode = E.spot(
                E.color(' '.join(map(str, self.color ) )),
            )
            if self.constant_att is not None:
                pnode.append(E.constant_attenuation(str(self.constant_att)))
            if self.linear_att is not None:
                pnode.append(E.linear_attenuation(str(self.linear_att)))
            if self.quad_att is not None:
                pnode.append(E.quadratic_attenuation(str(self.quad_att)))
            if self.falloff_ang is not None:
                pnode.append(E.falloff_angle(str(self.falloff_ang)))
            if self.falloff_exp is not None:
                pnode.append(E.falloff_exponent(str(self.falloff_exp)))

            self.xmlnode = E.light(
                E.technique_common(pnode)
            , id=self.id, name=self.id)

    def save(self):
        """Saves the light's properties back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        pnode = self.xmlnode.find('%s/%s' % (tag('technique_common'), tag('spot')))
        colornode = pnode.find(tag('color'))
        colornode.text = ' '.join(map(str, self.color ) )
        _correctValInNode(pnode, 'constant_attenuation', self.constant_att)
        _correctValInNode(pnode, 'linear_attenuation', self.linear_att)
        _correctValInNode(pnode, 'quadratic_attenuation', self.quad_att)
        _correctValInNode(pnode, 'falloff_angle', self.falloff_ang)
        _correctValInNode(pnode, 'falloff_exponent', self.falloff_exp)

    @staticmethod
    def load(collada, localscope, node):
        pnode = node.find( '%s/%s'%(tag('technique_common'),tag('spot')) )
        colornode = pnode.find( tag('color') )
        if colornode is None:
            raise DaeIncompleteError('Missing color for spot light')
        try:
            color = tuple([float(v) for v in colornode.text.split()])
        except ValueError as ex:
            raise DaeMalformedError('Corrupted color values in spot light definition')
        constant_att = linear_att = quad_att = falloff_ang = falloff_exp = None
        cattnode = pnode.find( tag('constant_attenuation') )
        lattnode = pnode.find( tag('linear_attenuation') )
        qattnode = pnode.find( tag('quadratic_attenuation') )
        fangnode = pnode.find( tag('falloff_angle') )
        fexpnode = pnode.find( tag('falloff_exponent') )
        try:
            if cattnode is not None:
                constant_att = float(cattnode.text)
            if lattnode is not None:
                linear_att = float(lattnode.text)
            if qattnode is not None:
                quad_att = float(qattnode.text)
            if fangnode is not None:
                falloff_ang = float(fangnode.text)
            if fexpnode is not None:
                falloff_exp = float(fexpnode.text)
        except ValueError as ex:
            raise DaeMalformedError('Corrupted values in spot light definition')
        return SpotLight(node.get('id'), color, constant_att, linear_att,
                quad_att, falloff_ang, falloff_exp, xmlnode = node)

    def bind(self, matrix):
        """Binds this light to a transform matrix.

        :param numpy.array matrix:
          A 4x4 numpy float matrix

        :rtype: :class:`collada.light.BoundSpotLight`

        """
        return BoundSpotLight(self, matrix)

    def __str__(self):
        return '<SpotLight id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class BoundLight(object):
    """Base class for bound lights"""
    pass


class BoundPointLight(BoundLight):
    """Point light bound to a scene with transformation. This gets created when a
        light is instantiated in a scene. Do not create this manually."""

    def __init__(self, plight, matrix):
        self.position = numpy.dot( matrix[:3,:3], plight.position ) + matrix[:3,3]
        """Numpy array of length 3 representing the position of the light in the scene"""
        self.color = plight.color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.constant_att = plight.constant_att
        if self.constant_att is None:
            self.constant_att = 1.0
        """Constant attenuation factor."""
        self.linear_att = plight.linear_att
        if self.linear_att is None:
            self.linear_att = 0.0
        """Linear attenuation factor."""
        self.quad_att = plight.quad_att
        if self.quad_att is None:
            self.quad_att = 0.0
        """Quadratic attenuation factor."""
        self.zfar = plight.zfar
        """Distance to the far clipping plane"""
        self.original = plight
        """The original :class:`collada.light.PointLight` this is bound to"""

    def __str__(self):
        return '<BoundPointLight bound to id=%s>' % str(self.original.id)

    def __repr__(self):
        return str(self)


class BoundSpotLight(BoundLight):
    """Spot light bound to a scene with transformation. This gets created when a
        light is instantiated in a scene. Do not create this manually."""

    def __init__(self, slight, matrix):
        self.position = matrix[:3,3]
        """Numpy array of length 3 representing the position of the light in the scene"""
        self.direction = -matrix[:3,2]
        """Direction of the spot light"""
        self.up = matrix[:3,1]
        """Up vector of the spot light"""
        self.matrix = matrix
        """Transform matrix for the bound light"""
        self.color = slight.color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.constant_att = slight.constant_att
        if self.constant_att is None:
            self.constant_att = 1.0
        """Constant attenuation factor."""
        self.linear_att = slight.linear_att
        if self.linear_att is None:
            self.linear_att = 0.0
        """Linear attenuation factor."""
        self.quad_att = slight.quad_att
        if self.quad_att is None:
            self.quad_att = 0.0
        """Quadratic attenuation factor."""
        self.falloff_ang = slight.falloff_ang
        if self.falloff_ang is None:
            self.falloff_ang = 180.0
        """Falloff angle"""
        self.falloff_exp = slight.falloff_exp
        if self.falloff_exp is None:
            self.falloff_exp = 0.0
        """Falloff exponent"""
        self.original = slight
        """The original :class:`collada.light.SpotLight` this is bound to"""

    def __str__(self):
        return '<BoundSpotLight bound to id=%s>' % str(self.original.id)

    def __repr__(self):
        return str(self)

class BoundDirectionalLight(BoundLight):
    """Directional light bound to a scene with transformation. This gets created when a
        light is instantiated in a scene. Do not create this manually."""

    def __init__(self, dlight, matrix):
        self.direction = numpy.dot( matrix[:3,:3], dlight.direction )
        """Numpy array of length 3 representing the direction of the light in the scene"""
        self.color = dlight.color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.original = dlight
        """The original :class:`collada.light.DirectionalLight` this is bound to"""

    def __str__(self):
        return '<BoundDirectionalLight bound to id=%s>' % str(self.original.id)

    def __repr__(self):
        return str(self)

class BoundAmbientLight(BoundLight):
    """Ambient light bound to a scene with transformation. This gets created when a
        light is instantiated in a scene. Do not create this manually."""

    def __init__(self, alight, matrix):
        self.color = alight.color
        """Either a tuple of size 3 containing the RGB color value
          of the light or a tuple of size 4 containing the RGBA
          color value of the light"""
        self.original = alight
        """The original :class:`collada.light.AmbientLight` this is bound to"""

    def __str__(self):
        return '<BoundAmbientLight bound to id=%s>' % str(self.original.id)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = lineset
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module containing classes and functions for the <lines> primitive."""

import numpy

from collada import primitive
from collada.util import toUnitVec, checkSource
from collada.common import E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.xmlutil import etree as ElementTree


class Line(object):
    """Single line representation. Represents the line between two points
    ``(x0,y0,z0)`` and ``(x1,y1,z1)``. A Line is read-only."""
    def __init__(self, indices, vertices, normals, texcoords, material):
        """A Line should not be created manually."""

        self.vertices = vertices
        """A (2, 3) numpy float array containing the endpoints of the line"""
        self.normals = normals
        """A (2, 3) numpy float array with the normals for the endpoints of the line. Can be None."""
        self.texcoords = texcoords
        """A tuple where entries are numpy float arrays of size (2, 2) containing
        the texture coordinates for the endpoints of the line for each texture
        coordinate set. Can be length 0 if there are no texture coordinates."""
        self.material = material
        """If coming from an unbound :class:`collada.lineset.LineSet`, contains a
        string with the material symbol. If coming from a bound
        :class:`collada.lineset.BoundLineSet`, contains the actual
        :class:`collada.material.Effect` the line is bound to."""
        self.indices = indices

        # Note: we can't generate normals for lines if there are none

    def __repr__(self):
        return '<Line (%s, %s, "%s")>'%(str(self.vertices[0]), str(self.vertices[1]), str(self.material))

    def __str__(self):
        return repr(self)


class LineSet(primitive.Primitive):
    """Class containing the data COLLADA puts in a <lines> tag, a collection of
    lines. The LineSet object is read-only. To modify a LineSet, create a new
    instance using :meth:`collada.geometry.Geometry.createLineSet`.

    * If ``L`` is an instance of :class:`collada.lineset.LineSet`, then ``len(L)``
      returns the number of lines in the set. ``L[i]`` returns the i\ :sup:`th`
      line in the set."""

    def __init__(self, sources, material, index, xmlnode=None):
        """A LineSet should not be created manually. Instead, call the
        :meth:`collada.geometry.Geometry.createLineSet` method after
        creating a geometry instance.
        """

        if len(sources) == 0: raise DaeIncompleteError('A line set needs at least one input for vertex positions')
        if not 'VERTEX' in sources: raise DaeIncompleteError('Line set requires vertex input')

        #find max offset
        max_offset = max([ max([input[0] for input in input_type_array])
                          for input_type_array in sources.values() if len(input_type_array) > 0])

        self.sources = sources
        self.material = material
        self.index = index
        self.indices = self.index
        self.nindices = max_offset + 1
        self.index.shape = (-1, 2, self.nindices)
        self.nlines = len(self.index)

        if len(self.index) > 0:
            self._vertex = sources['VERTEX'][0][4].data
            self._vertex_index = self.index[:,:, sources['VERTEX'][0][0]]
            self.maxvertexindex = numpy.max( self._vertex_index )
            checkSource(sources['VERTEX'][0][4], ('X', 'Y', 'Z'),
                    self.maxvertexindex)
        else:
            self._vertex = None
            self._vertex_index = None
            self.maxvertexindex = -1

        if 'NORMAL' in sources and len(sources['NORMAL']) > 0 \
                and len(self.index) > 0:
            self._normal = sources['NORMAL'][0][4].data
            self._normal_index = self.index[:,:, sources['NORMAL'][0][0]]
            self.maxnormalindex = numpy.max( self._normal_index )
            checkSource(sources['NORMAL'][0][4], ('X', 'Y', 'Z'),
                    self.maxnormalindex)
        else:
            self._normal = None
            self._normal_index = None
            self.maxnormalindex = -1

        if 'TEXCOORD' in sources and len(sources['TEXCOORD']) > 0 \
                and len(self.index) > 0:
            self._texcoordset = tuple([texinput[4].data
                for texinput in sources['TEXCOORD']])
            self._texcoord_indexset = tuple([ self.index[:,:, sources['TEXCOORD'][i][0]]
                for i in xrange(len(sources['TEXCOORD'])) ])
            self.maxtexcoordsetindex = [numpy.max(tex_index)
                for tex_index in self._texcoord_indexset]
            for i, texinput in enumerate(sources['TEXCOORD']):
                checkSource(texinput[4], ('S', 'T'), self.maxtexcoordsetindex[i])
        else:
            self._texcoordset = tuple()
            self._texcoord_indexset = tuple()
            self.maxtexcoordsetindex = -1

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the line set."""
        else:
            self.index.shape = (-1)
            acclen = len(self.index)
            txtindices = ' '.join(map(str, self.index.tolist()))
            self.index.shape = (-1, 2, self.nindices)

            self.xmlnode = E.lines(count=str(self.nlines),
                    material=self.material)

            all_inputs = []
            for semantic_list in self.sources.values():
                all_inputs.extend(semantic_list)
            for offset, semantic, sourceid, set, src in all_inputs:
                inpnode = E.input(offset=str(offset), semantic=semantic,
                        source=sourceid)
                if set is not None:
                    inpnode.set('set', str(set))
                self.xmlnode.append(inpnode)

            self.xmlnode.append(E.p(txtindices))

    def __len__(self):
        """The number of lines in this line set."""
        return len(self.index)

    def __getitem__(self, i):
        v = self._vertex[ self._vertex_index[i] ]
        if self._normal is None:
            n = None
        else:
            n = self._normal[ self._normal_index[i] ]
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uv.append( self._texcoordset[j][ uvindex[i] ] )
        return Line(self._vertex_index[i], v, n, uv, self.material)

    @staticmethod
    def load( collada, localscope, node ):
        indexnode = node.find(tag('p'))
        if indexnode is None: raise DaeIncompleteError('Missing index in line set')

        source_array = primitive.Primitive._getInputs(collada, localscope, node.findall(tag('input')))

        try:
            if indexnode.text is None:
                index = numpy.array([],  dtype=numpy.int32)
            else:
                index = numpy.fromstring(indexnode.text, dtype=numpy.int32, sep=' ')
            index[numpy.isnan(index)] = 0
        except: raise DaeMalformedError('Corrupted index in line set')

        lineset = LineSet(source_array, node.get('material'), index, node)
        lineset.xmlnode = node
        return lineset

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound line set from this line set, transform and material mapping"""
        return BoundLineSet( self, matrix, materialnodebysymbol)

    def __str__(self):
        return '<LineSet length=%d>' % len(self)

    def __repr__(self):
        return str(self)


class BoundLineSet(primitive.BoundPrimitive):
    """A line set bound to a transform matrix and materials mapping.

    * If ``bs`` is an instance of :class:`collada.lineset.BoundLineSet`, ``len(bs)``
      returns the number of lines in the set and ``bs[i]`` returns the i\ :superscript:`th`
      line in the set.

    """

    def __init__(self, ls, matrix, materialnodebysymbol):
        """Create a bound line set from a line set, transform and material mapping. This gets created when a
        line set is instantiated in a scene. Do not create this manually."""
        M = numpy.asmatrix(matrix).transpose()
        self._vertex = None
        if ls._vertex is not None:
            self._vertex = numpy.asarray(ls._vertex * M[:3,:3]) + matrix[:3,3]
        self._normal = None
        if ls._normal is not None:
            self._normal = numpy.asarray(ls._normal * M[:3,:3])
        self._texcoordset = ls._texcoordset
        matnode = materialnodebysymbol.get( ls.material )
        if matnode:
            self.material = matnode.target
            self.inputmap = dict([ (sem, (input_sem, set))
                for sem, input_sem, set in matnode.inputs ])
        else: self.inputmap = self.material = None
        self.index = ls.index
        self._vertex_index = ls._vertex_index
        self._normal_index = ls._normal_index
        self._texcoord_indexset = ls._texcoord_indexset
        self.nlines = ls.nlines
        self.original = ls

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        v = self._vertex[ self._vertex_index[i] ]
        if self._normal is None:
            n = None
        else:
            n = self._normal[ self._normal_index[i] ]
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uv.append( self._texcoordset[j][ uvindex[i] ] )
        return Line(self._vertex_index[i], v, n, uv, self.material)

    def lines(self):
        """Iterate through all the lines contained in the set.

        :rtype: generator of :class:`collada.lineset.Line`
        """
        for i in xrange(self.nlines): yield self[i]

    def shapes(self):
        """Iterate through all the lines contained in the set.

        :rtype: generator of :class:`collada.lineset.Line`
        """
        return self.lines()

    def __str__(self):
        return '<BoundLineSet length=%d>' % len(self)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = material
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module for material, effect and image loading

This module contains all the functionality to load and manage:
- Images in the image library
- Surfaces and samplers2D in effects
- Effects (that are now used as materials)

"""

import copy
import numpy

from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import falmostEqual, StringIO
from collada.xmlutil import etree as ElementTree

try:
    from PIL import Image as pil
except:
    pil = None


class DaeMissingSampler2D(Exception):
    """Raised when a <texture> tag references a texture without a sampler."""
    pass


class CImage(DaeObject):
    """Class containing data coming from a <image> tag.

    Basically is just the path to the file, but we give an extended
    functionality if PIL is available. You can in that case get the
    image object or numpy arrays in both int and float format. We
    named it CImage to avoid confusion with PIL's Image class.

    """
    def __init__(self, id, path, collada = None, xmlnode = None):
        """Create an image object.

        :param str id:
          A unique string identifier for the image
        :param str path:
          Path relative to the collada document where the image is located
        :param collada.Collada collada:
          The collada object this image belongs to
        :param xmlnode:
          If loaded from xml, the node this data comes from

        """
        self.id = id
        """The unique string identifier for the image"""
        self.path = path
        """Path relative to the collada document where the image is located"""

        self.collada = collada
        self._data = None
        self._pilimage = None
        self._uintarray = None
        self._floatarray = None
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the image."""
        else:
            self.xmlnode = E.image(
                E.init_from(path)
            , id=self.id, name=self.id)

    def getData(self):
        if self._data is None:
            try: self._data = self.collada.getFileData( self.path )
            except DaeBrokenRefError as ex:
                self._data = ''
                self.collada.handleError(ex)
        return self._data

    def getImage(self):
        if pil is None or self._pilimage == 'failed':
            return None
        if self._pilimage:
            return self._pilimage
        else:
            data = self.getData()
            if not data:
                self._pilimage = 'failed'
                return None
            try:
                self._pilimage = pil.open( StringIO(data) )
                self._pilimage.load()
            except IOError as ex:
                self._pilimage = 'failed'
                return None
            return self._pilimage

    def getUintArray(self):
        if self._uintarray == 'failed': return None
        if self._uintarray != None: return self._uintarray
        img = self.getImage()
        if not img:
            self._uintarray = 'failed'
            return None
        nchan = len(img.mode)
        self._uintarray = numpy.fromstring(img.tostring(), dtype=numpy.uint8)
        self._uintarray.shape = (img.size[1], img.size[0], nchan)
        return self._uintarray

    def getFloatArray(self):
        if self._floatarray == 'failed': return None
        if self._floatarray != None: return self._floatarray
        array = self.getUintArray()
        if array is None:
            self._floatarray = 'failed'
            return None
        self._floatarray = numpy.asarray( array, dtype=numpy.float32)
        self._floatarray *= 1.0/255.0
        return self._floatarray

    def setData(self, data):
        self._data = data
        self._floatarray = None
        self._uintarray = None
        self._pilimage = None

    data = property( getData, setData )
    """Raw binary image file data if the file is readable. If `aux_file_loader` was passed to
    :func:`collada.Collada.__init__`, this function will be called to retrieve the data.
    Otherwise, if the file came from the local disk, the path will be interpreted from
    the local file system. If the file was a zip archive, the archive will be searched."""
    pilimage = property( getImage )
    """PIL Image object if PIL is available and the file is readable."""
    uintarray = property( getUintArray )
    """Numpy array (height, width, nchannels) in integer format."""
    floatarray = property( getFloatArray )
    """Numpy float array (height, width, nchannels) with the image data normalized to 1.0."""

    @staticmethod
    def load( collada, localspace, node ):
        id = node.get('id')
        initnode = node.find( tag('init_from') )
        if initnode is None: raise DaeIncompleteError('Image has no file path')
        path = initnode.text
        return CImage(id, path, collada, xmlnode = node)

    def save(self):
        """Saves the image back to :attr:`xmlnode`. Only the :attr:`id` attribute is saved.
        The image itself will have to be saved to its original source to make modifications."""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        initnode = self.xmlnode.find( tag('init_from') )
        initnode.text = self.path

    def __str__(self):
        return '<CImage id=%s path=%s>' % (self.id, self.path)

    def __repr__(self):
        return str(self)


class Surface(DaeObject):
    """Class containing data coming from a <surface> tag.

    Collada materials use this to access to the <image> tag.
    The only extra information we store right now is the
    image format. In theory, this enables many more features
    according to the collada spec, but no one seems to actually
    use them in the wild, so for now, it's unimplemented.

    """

    def __init__(self, id, img, format=None, xmlnode=None):
        """Creates a surface.

        :param str id:
          A string identifier for the surface within the local scope of the material
        :param collada.material.CImage img:
          The image object
        :param str format:
          The format of the image
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The string identifier for the surface within the local scope of the material"""
        self.image = img
        """:class:`collada.material.CImage` object from the image library."""
        self.format = format if format is not None else "A8R8G8B8"
        """Format string."""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the surface."""
        else:
            self.xmlnode = E.newparam(
                E.surface(
                    E.init_from(self.image.id),
                    E.format(self.format)
                , type="2D")
            , sid=self.id)

    @staticmethod
    def load( collada, localscope, node ):
        surfacenode = node.find( tag('surface') )
        if surfacenode is None: raise DaeIncompleteError('No surface found in newparam')
        if surfacenode.get('type') != '2D': raise DaeMalformedError('Hard to imagine a non-2D surface, isn\'t it?')
        initnode = surfacenode.find( tag('init_from') )
        if initnode is None: raise DaeIncompleteError('No init image found in surface')
        formatnode = surfacenode.find( tag('format') )
        if formatnode is None: format = None
        else: format = formatnode.text
        imgid = initnode.text
        id = node.get('sid')
        if imgid in localscope:
            img = localscope[imgid]
        else:
            img = collada.images.get(imgid)
        if img is None: raise DaeBrokenRefError("Missing image '%s' in surface '%s'" % (imgid, id))
        return Surface(id, img, format, xmlnode=node)

    def save(self):
        """Saves the surface data back to :attr:`xmlnode`"""
        surfacenode = self.xmlnode.find( tag('surface') )
        initnode = surfacenode.find( tag('init_from') )
        if self.format:
            formatnode = surfacenode.find( tag('format') )
            if formatnode is None:
                surfacenode.append(E.format(self.format))
            else:
                formatnode.text = self.format
        initnode.text = self.image.id
        self.xmlnode.set('sid', self.id)

    def __str__(self):
        return '<Surface id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class Sampler2D(DaeObject):
    """Class containing data coming from <sampler2D> tag in material.

    Collada uses the <sampler2D> tag to map to a <surface>. The only
    information we store about the sampler right now is minfilter and
    magfilter. Theoretically, the collada spec has many more parameters
    here, but no one seems to be using them in the wild, so they are
    currently unimplemented.

    """
    def __init__(self, id, surface, minfilter=None, magfilter=None, xmlnode=None):
        """Create a Sampler2D object.

        :param str id:
          A string identifier for the sampler within the local scope of the material
        :param collada.material.Surface surface:
          Surface instance that this object samples from
        :param str minfilter:
          Minification filter string id, see collada spec for details
        :param str magfilter:
          Maximization filter string id, see collada spec for details
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The string identifier for the sampler within the local scope of the material"""
        self.surface = surface
        """Surface instance that this object samples from"""
        self.minfilter = minfilter
        """Minification filter string id, see collada spec for details"""
        self.magfilter = magfilter
        """Maximization filter string id, see collada spec for details"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the sampler."""
        else:
            sampler_node = E.sampler2D(E.source(self.surface.id))
            if minfilter:
                sampler_node.append(E.minfilter(self.minfilter))
            if magfilter:
                sampler_node.append(E.magfilter(self.magfilter))

            self.xmlnode = E.newparam(sampler_node, sid=self.id)

    @staticmethod
    def load( collada, localscope, node ):
        samplernode = node.find( tag('sampler2D') )
        if samplernode is None: raise DaeIncompleteError('No sampler found in newparam')
        sourcenode = samplernode.find( tag('source') )
        if sourcenode is None: raise DaeIncompleteError('No source found in sampler')
        minnode = samplernode.find( tag('minfilter') )
        if minnode is None: minfilter = None
        else: minfilter = minnode.text
        magnode = samplernode.find( tag('magfilter') )
        if magnode is None: magfilter = None
        else: magfilter = magnode.text

        surfaceid = sourcenode.text
        id = node.get('sid')
        surface = localscope.get(surfaceid)
        if surface is None or type(surface) != Surface: raise DaeBrokenRefError('Missing surface ' + surfaceid)
        return Sampler2D(id, surface, minfilter, magfilter, xmlnode=node)

    def save(self):
        """Saves the sampler data back to :attr:`xmlnode`"""
        samplernode = self.xmlnode.find( tag('sampler2D') )
        sourcenode = samplernode.find( tag('source') )
        if self.minfilter:
            minnode = samplernode.find( tag('minfilter') )
            minnode.text = self.minfilter
        if self.magfilter:
            maxnode = samplernode.find( tag('magfilter') )
            maxnode.text = self.magfilter
        sourcenode.text = self.surface.id
        self.xmlnode.set('sid', self.id)

    def __str__(self):
        return '<Sampler2D id=%s>' % (self.id,)

    def __repr__(self):
        return str(self)


class Map(DaeObject):
    """Class containing data coming from <texture> tag inside material.

    When a material defines its properties like `diffuse`, it can give you
    a color or a texture. In the latter, the texture is mapped with a
    sampler and a texture coordinate channel. If a material defined a texture
    for one of its properties, you'll find an object of this class in the
    corresponding attribute.

    """
    def __init__(self, sampler, texcoord, xmlnode=None):
        """Create a map instance to a sampler using a texcoord channel.

        :param collada.material.Sampler2D sampler:
          A sampler object to map
        :param str texcoord:
          Texture coordinate channel symbol to use
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.sampler = sampler
        """:class:`collada.material.Sampler2D` object to map"""
        self.texcoord = texcoord
        """Texture coordinate channel symbol to use"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the map"""
        else:
            self.xmlnode = E.texture(texture=self.sampler.id, texcoord=self.texcoord)

    @staticmethod
    def load( collada, localscope, node ):
        samplerid = node.get('texture')
        texcoord = node.get('texcoord')
        sampler = localscope.get(samplerid)
        #Check for the sampler ID as the texture ID because some exporters suck
        if sampler is None:
            for s2d in localscope.itervalues():
                if type(s2d) is Sampler2D:
                    if s2d.surface.image.id == samplerid:
                        sampler = s2d
        if sampler is None or type(sampler) != Sampler2D:
            err = DaeMissingSampler2D('Missing sampler ' + samplerid + ' in node ' + node.tag)
            err.samplerid = samplerid
            raise err
        return Map(sampler, texcoord, xmlnode = node)

    def save(self):
        """Saves the map back to :attr:`xmlnode`"""
        self.xmlnode.set('texture', self.sampler.id)
        self.xmlnode.set('texcoord', self.texcoord)

    def __str__(self):
        return '<Map sampler=%s texcoord=%s>' % (self.sampler.id, self.texcoord)

    def __repr__(self):
        return str(self)

class OPAQUE_MODE:
    """The opaque mode of an effect."""
    A_ONE = 'A_ONE'
    """Takes the transparency information from the color's alpha channel, where the value 1.0 is opaque (default)."""
    RGB_ZERO = 'RGB_ZERO'
    """Takes the transparency information from the color's red, green, and blue
    channels, where the value 0.0 is opaque, with each channel modulated
    independently."""

class Effect(DaeObject):
    """Class containing data coming from an <effect> tag.
    """
    supported = [ 'emission', 'ambient', 'diffuse', 'specular',
                  'shininess', 'reflective', 'reflectivity',
                  'transparent', 'transparency', 'index_of_refraction' ]
    """Supported material properties list."""
    shaders = [ 'phong', 'lambert', 'blinn', 'constant']
    """Supported shader list."""

    def __init__(self, id, params, shadingtype, bumpmap = None, double_sided = False,
                       emission = (0.0, 0.0, 0.0, 1.0),
                       ambient = (0.0, 0.0, 0.0, 1.0),
                       diffuse = (0.0, 0.0, 0.0, 1.0),
                       specular = (0.0, 0.0, 0.0, 1.0),
                       shininess = 0.0,
                       reflective = (0.0, 0.0, 0.0, 1.0),
                       reflectivity = 0.0,
                       transparent = (0.0, 0.0, 0.0, 1.0),
                       transparency = None,
                       index_of_refraction = None,
                       opaque_mode = None,
                       xmlnode = None):
        """Create an effect instance out of properties.

        :param str id:
          A string identifier for the effect
        :param list params:
          A list containing elements of type :class:`collada.material.Sampler2D`
          and :class:`collada.material.Surface`
        :param str shadingtype:
          The type of shader to be used for this effect. Right now, we
          only supper the shaders listed in :attr:`shaders`
        :param `collada.material.Map` bumpmap:
          The bump map for this effect, or None if there isn't one
        :param bool double_sided:
          Whether or not the material should be rendered double sided
        :param emission:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param ambient:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param diffuse:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param specular:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param shininess:
          Either a single float or an instance of :class:`collada.material.Map`
        :param reflective:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param reflectivity:
          Either a single float or an instance of :class:`collada.material.Map`
        :param tuple transparent:
          Either an RGBA-format tuple of four floats or an instance
          of :class:`collada.material.Map`
        :param transparency:
          Either a single float or an instance of :class:`collada.material.Map`
        :param float index_of_refraction:
          A single float indicating the index of refraction for perfectly
          refracted light
        :param `collada.material.OPAQUE_MODE` opaque_mode:
          The opaque mode for the effect. If not specified, defaults to A_ONE.
        :param xmlnode:
          If loaded from xml, the xml node

        """
        self.id = id
        """The string identifier for the effect"""
        self.params = params
        """A list containing elements of type :class:`collada.material.Sampler2D`
          and :class:`collada.material.Surface`"""
        self.shadingtype = shadingtype
        """String with the type of the shading."""
        self.bumpmap = bumpmap
        """Either the bump map of the effect of type :class:`collada.material.Map`
        or None if there is none."""
        self.double_sided = double_sided
        """A boolean indicating whether or not the material should be rendered double sided"""
        self.emission = emission
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.ambient = ambient
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.diffuse = diffuse
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.specular = specular
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.shininess = shininess
        """Either a single float or an instance of :class:`collada.material.Map`"""
        self.reflective = reflective
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.reflectivity = reflectivity
        """Either a single float or an instance of :class:`collada.material.Map`"""
        self.transparent = transparent
        """Either an RGB-format tuple of three floats or an instance
          of :class:`collada.material.Map`"""
        self.transparency = transparency
        """Either a single float or an instance of :class:`collada.material.Map`"""
        self.index_of_refraction = index_of_refraction
        """A single float indicating the index of refraction for perfectly
          refracted light"""
        self.opaque_mode = OPAQUE_MODE.A_ONE if opaque_mode is None else opaque_mode
        """The opaque mode for the effect. An instance of :class:`collada.material.OPAQUE_MODE`."""

        if self.transparency is None:
            if self.opaque_mode == OPAQUE_MODE.A_ONE:
                self.transparency = 1.0
            else:
                self.transparency = 0.0

        self._fixColorValues()

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the effect"""
        else:
            shadnode = E(self.shadingtype)

            for prop in self.supported:
                value = getattr(self, prop)
                if value is None: continue
                propnode = E(prop)
                if prop == 'transparent' and self.opaque_mode == OPAQUE_MODE.RGB_ZERO:
                    propnode.set('opaque', OPAQUE_MODE.RGB_ZERO)
                shadnode.append( propnode )
                if type(value) is Map:
                    propnode.append(value.xmlnode)
                elif type(value) is float:
                    propnode.append(E.float(str(value)))
                else:
                    propnode.append(E.color(' '.join(map(str, value) )))

            effect_nodes = [param.xmlnode for param in self.params]
            effect_nodes.append(E.technique(shadnode, sid='common'))
            self.xmlnode = E.effect(
                E.profile_COMMON(*effect_nodes)
            , id=self.id, name=self.id)


    @staticmethod
    def load(collada, localscope, node):
        localscope = {} # we have our own scope, shadow it
        params = []
        id = node.get('id')
        profilenode = node.find( tag('profile_COMMON') )
        if profilenode is None:
            raise DaeUnsupportedError('Found effect with profile other than profile_COMMON')

        #<image> can be local to a material instead of global in <library_images>
        for imgnode in profilenode.findall( tag('image') ):
            local_image = CImage.load(collada, localscope, imgnode)
            localscope[local_image.id] = local_image

            global_image_id = local_image.id
            uniquenum = 2
            while global_image_id in collada.images:
                global_image_id = local_image.id + "-" + uniquenum
                uniquenum += 1
            collada.images.append(local_image)

        for paramnode in profilenode.findall( tag('newparam') ):
            if paramnode.find( tag('surface') ) is not None:
                param = Surface.load(collada, localscope, paramnode)
                params.append(param)
                localscope[param.id] = param
            elif paramnode.find( tag('sampler2D') ) is not None:
                param = Sampler2D.load(collada, localscope, paramnode)
                params.append(param)
                localscope[param.id] = param
            else:
                floatnode = paramnode.find( tag('float') )
                if floatnode is None: floatnode = paramnode.find( tag('float2') )
                if floatnode is None: floatnode = paramnode.find( tag('float3') )
                if floatnode is None: floatnode = paramnode.find( tag('float4') )
                paramid = paramnode.get('sid')
                if floatnode is not None and paramid is not None and len(paramid) > 0 and floatnode.text is not None:
                    localscope[paramid] = [float(v) for v in floatnode.text.split()]
        tecnode = profilenode.find( tag('technique') )
        shadnode = None
        for shad in Effect.shaders:
            shadnode = tecnode.find(tag(shad))
            shadingtype = shad
            if not shadnode is None:
                break
        if shadnode is None: raise DaeIncompleteError('No material properties found in effect')
        props = {}
        for key in Effect.supported:
            pnode = shadnode.find( tag(key) )
            if pnode is None: props[key] = None
            else:
                try: props[key] = Effect._loadShadingParam(collada, localscope, pnode)
                except DaeMissingSampler2D as ex:
                    if ex.samplerid in collada.images:
                        #Whoever exported this collada file didn't include the proper references so we will create them
                        surf = Surface(ex.samplerid + '-surface', collada.images[ex.samplerid], 'A8R8G8B8')
                        sampler = Sampler2D(ex.samplerid, surf, None, None);
                        params.append(surf)
                        params.append(sampler)
                        localscope[surf.id] = surf
                        localscope[sampler.id] = sampler
                        try:
                            props[key] = Effect._loadShadingParam(
                                    collada, localscope, pnode)
                        except DaeUnsupportedError as ex:
                            props[key] = None
                            collada.handleError(ex)
                except DaeUnsupportedError as ex:
                    props[key] = None
                    collada.handleError(ex) # Give the chance to ignore error and load the rest

                if key == 'transparent' and key in props and props[key] is not None:
                    opaque_mode = pnode.get('opaque')
                    if opaque_mode is not None and opaque_mode == OPAQUE_MODE.RGB_ZERO:
                        props['opaque_mode'] = OPAQUE_MODE.RGB_ZERO
        props['xmlnode'] = node

        bumpnode = node.find('.//%s//%s' % (tag('extra'), tag('texture')))
        if bumpnode is not None:
            bumpmap =  Map.load(collada, localscope, bumpnode)
        else:
            bumpmap = None

        double_sided_node = node.find('.//%s//%s' % (tag('extra'), tag('double_sided')))
        double_sided = False
        if double_sided_node is not None and double_sided_node.text is not None:
            try:
                val = int(double_sided_node.text)
                if val == 1:
                    double_sided = True
            except ValueError:
                pass
        return Effect(id, params, shadingtype, bumpmap, double_sided, **props)

    @staticmethod
    def _loadShadingParam( collada, localscope, node ):
        """Load from the node a definition for a material property."""
        children = node.getchildren()
        if not children: raise DaeIncompleteError('Incorrect effect shading parameter '+node.tag)
        vnode = children[0]
        if vnode.tag == tag('color'):
            try:
                value = tuple([ float(v) for v in vnode.text.split() ])
            except ValueError as ex:
                raise DaeMalformedError('Corrupted color definition in effect '+id)
            except IndexError as ex:
                raise DaeMalformedError('Corrupted color definition in effect '+id)
        elif vnode.tag == tag('float'):
            try: value = float(vnode.text)
            except ValueError as ex:
                raise DaeMalformedError('Corrupted float definition in effect '+id)
        elif vnode.tag == tag('texture'):
            value = Map.load(collada, localscope, vnode)
        elif vnode.tag == tag('param'):
            refid = vnode.get('ref')
            if refid is not None and refid in localscope:
                value = localscope[refid]
            else:
                return None
        else:
            raise DaeUnsupportedError('Unknown shading param definition ' + \
                    vnode.tag)
        return value

    def _fixColorValues(self):
        for prop in self.supported:
            propval = getattr(self, prop)
            if isinstance(propval, tuple):
                if len(propval) < 4:
                    propval = list(propval)
                    while len(propval) < 3:
                        propval.append(0.0)
                    while len(propval) < 4:
                        propval.append(1.0)
                    setattr(self, prop, tuple(propval))

    def save(self):
        """Saves the effect back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        self.xmlnode.set('name', self.id)
        profilenode = self.xmlnode.find( tag('profile_COMMON') )
        tecnode = profilenode.find( tag('technique') )
        tecnode.set('sid', 'common')

        self._fixColorValues()

        for param in self.params:
            param.save()
            if param.xmlnode not in profilenode.getchildren():
                profilenode.insert(list(profilenode).index(tecnode),
                        param.xmlnode)

        deletenodes = []
        for oldparam in profilenode.findall( tag('newparam') ):
            if oldparam not in [param.xmlnode for param in self.params]:
                deletenodes.append(oldparam)
        for d in deletenodes:
            profilenode.remove(d)

        for shader in self.shaders:
            shadnode = tecnode.find(tag(shader))
            if shadnode is not None and shader != self.shadingtype:
                tecnode.remove(shadnode)

        def getPropNode(prop, value):
            propnode = E(prop)
            if prop == 'transparent' and self.opaque_mode == OPAQUE_MODE.RGB_ZERO:
                propnode.set('opaque', OPAQUE_MODE.RGB_ZERO)
            if type(value) is Map:
                propnode.append(copy.deepcopy(value.xmlnode))
            elif type(value) is float:
                propnode.append(E.float(str(value)))
            else:
                propnode.append(E.color(' '.join(map(str, value) )))
            return propnode

        shadnode = tecnode.find(tag(self.shadingtype))
        if shadnode is None:
            shadnode = E(self.shadingtype)
            for prop in self.supported:
                value = getattr(self, prop)
                if value is None: continue
                shadnode.append(getPropNode(prop, value))
            tecnode.append(shadnode)
        else:
            for prop in self.supported:
                value = getattr(self, prop)
                propnode = shadnode.find(tag(prop))
                if propnode is not None:
                    shadnode.remove(propnode)
                if value is not None:
                    shadnode.append(getPropNode(prop, value))

        double_sided_node = profilenode.find('.//%s//%s' % (tag('extra'), tag('double_sided')))
        if double_sided_node is None or double_sided_node.text is None:
            extranode = profilenode.find(tag('extra'))
            if extranode is None:
                extranode = E.extra()
                profilenode.append(extranode)

            teqnodes = extranode.findall(tag('technique'))
            goognode = None
            for teqnode in teqnodes:
                if teqnode.get('profile') == 'GOOGLEEARTH':
                    goognode = teqnode
                    break
            if goognode is None:
                goognode = E.technique(profile='GOOGLEEARTH')
                extranode.append(goognode)
            double_sided_node = goognode.find(tag('double_sided'))
            if double_sided_node is None:
                double_sided_node = E.double_sided()
                goognode.append(double_sided_node)

        double_sided_node.text = "1" if self.double_sided else "0"

    def __str__(self):
        return '<Effect id=%s type=%s>' % (self.id, self.shadingtype)

    def __repr__(self):
        return str(self)

    def almostEqual(self, other):
        """Checks if this effect is almost equal (within float precision)
        to the given effect.

        :param collada.material.Effect other:
          Effect to compare to

        :rtype: bool

        """
        if self.shadingtype != other.shadingtype:
            return False
        if self.double_sided != other.double_sided:
            return False
        for prop in self.supported:
            thisprop = getattr(self, prop)
            otherprop = getattr(other, prop)
            if type(thisprop) != type(otherprop):
                return False
            elif type(thisprop) is float:
                if not falmostEqual(thisprop, otherprop):
                    return False
            elif type(thisprop) is Map:
                if thisprop.sampler.surface.image.id != otherprop.sampler.surface.image.id or thisprop.texcoord != otherprop.texcoord:
                    return False
            elif type(thisprop) is tuple:
                if len(thisprop) != len(otherprop):
                    return False
                for valthis, valother in zip(thisprop, otherprop):
                    if not falmostEqual(valthis, valother):
                        return False
        return True


class Material(DaeObject):
    """Class containing data coming from a <material> tag.

    Right now, this just stores a reference to the effect
    which is instantiated in the material. The effect instance
    can have parameters, but this is rarely used in the wild,
    so it is not yet implemented.

    """

    def __init__(self, id, name, effect, xmlnode=None):
        """Creates a material.

        :param str id:
          A unique string identifier for the material
        :param str name:
          A name for the material
        :param collada.material.Effect effect:
          The effect instantiated in this material
        :param xmlnode:
          If loaded from xml, the xml node

        """

        self.id = id
        """The unique string identifier for the material"""
        self.name = name
        """The name for the material"""
        self.effect = effect
        """The :class:`collada.material.Effect` instantiated in this material"""

        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the surface."""
        else:
            self.xmlnode = E.material(
                E.instance_effect(url="#%s" % self.effect.id)
            , id=str(self.id), name=str(self.name))

    @staticmethod
    def load( collada, localscope, node ):
        matid = node.get('id')
        matname = node.get('name')

        effnode = node.find( tag('instance_effect'))
        if effnode is None: raise DaeIncompleteError('No effect inside material')
        effectid = effnode.get('url')

        if not effectid.startswith('#'):
            raise DaeMalformedError('Corrupted effect reference in material %s' % effectid)

        effect = collada.effects.get(effectid[1:])
        if not effect:
            raise DaeBrokenRefError('Effect not found: '+effectid)

        return Material(matid, matname, effect, xmlnode=node)

    def save(self):
        """Saves the material data back to :attr:`xmlnode`"""
        self.xmlnode.set('id', str(self.id))
        self.xmlnode.set('name', str(self.name))
        effnode = self.xmlnode.find( tag('instance_effect') )
        effnode.set('url', '#%s' % self.effect.id)

    def __str__(self):
        return '<Material id=%s effect=%s>' % (self.id, self.effect.id)

    def __repr__(self):
        return str(self)

########NEW FILE########
__FILENAME__ = polygons
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module containing classes and functions for the <polygons> primitive."""

import numpy

from collada import primitive
from collada import polylist
from collada import triangleset
from collada.common import E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import toUnitVec, checkSource
from collada.xmlutil import etree as ElementTree


class Polygons(polylist.Polylist):
    """Class containing the data COLLADA puts in a <polygons> tag, a collection of
    polygons that can have holes.

    * The Polygons object is read-only. To modify a
      Polygons, create a new instance using :meth:`collada.geometry.Geometry.createPolygons`.

    * Polygons with holes are not currently supported, so for right now, this class is
      essentially the same as a :class:`collada.polylist.Polylist`. Use a polylist instead
      if your polygons don't have holes.
    """

    def __init__(self, sources, material, polygons, xmlnode=None):
        """A Polygons should not be created manually. Instead, call the
        :meth:`collada.geometry.Geometry.createPolygons` method after
        creating a geometry instance.
        """

        max_offset = max([ max([input[0] for input in input_type_array])
            for input_type_array in sources.values()
            if len(input_type_array) > 0])

        vcounts = numpy.zeros(len(polygons), dtype=numpy.int32)
        for i, poly in enumerate(polygons):
            vcounts[i] = len(poly) / (max_offset + 1)

        if len(polygons) > 0:
            indices = numpy.concatenate(polygons)
        else:
            indices = numpy.array([], dtype=numpy.int32)

        super(Polygons, self).__init__(sources, material, indices, vcounts, xmlnode)

        if xmlnode is not None: self.xmlnode = xmlnode
        else:
            acclen = len(polygons)

            self.xmlnode = E.polygons(count=str(acclen), material=self.material)

            all_inputs = []
            for semantic_list in self.sources.values():
                all_inputs.extend(semantic_list)
            for offset, semantic, sourceid, set, src in all_inputs:
                inpnode = E.input(offset=str(offset), semantic=semantic, source=sourceid)
                if set is not None:
                    inpnode.set('set', str(set))
                self.xmlnode.append(inpnode)

            for poly in polygons:
                self.xmlnode.append(E.p(' '.join(map(str, poly.flatten().tolist()))))

    @staticmethod
    def load( collada, localscope, node ):
        indexnodes = node.findall(tag('p'))
        if indexnodes is None: raise DaeIncompleteError('Missing indices in polygons')

        polygon_indices = []
        for indexnode in indexnodes:
            index = numpy.fromstring(indexnode.text, dtype=numpy.int32, sep=' ')
            index[numpy.isnan(index)] = 0
            polygon_indices.append(index)

        all_inputs = primitive.Primitive._getInputs(collada, localscope, node.findall(tag('input')))

        polygons = Polygons(all_inputs, node.get('material'), polygon_indices, node)
        return polygons

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound polygons from this polygons, transform and material mapping"""
        return BoundPolygons( self, matrix, materialnodebysymbol )

    def __str__(self):
        return '<Polygons length=%d>' % len(self)

    def __repr__(self):
        return str(self)


class BoundPolygons(polylist.BoundPolylist):
    """Polygons bound to a transform matrix and materials mapping."""

    def __init__(self, pl, matrix, materialnodebysymbol):
        """Create a BoundPolygons from a Polygons, transform and material mapping"""
        super(BoundPolygons, self).__init__(pl, matrix, materialnodebysymbol)

    def __str__(self):
        return '<BoundPolygons length=%d>' % len(self)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = polylist
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module containing classes and functions for the <polylist> primitive."""

import numpy

from collada import primitive
from collada import triangleset
from collada.common import E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import toUnitVec, checkSource, xrange
from collada.xmlutil import etree as ElementTree


class Polygon(object):
    """Single polygon representation. Represents a polygon of N points."""
    def __init__(self, indices, vertices, normal_indices, normals, texcoord_indices, texcoords, material):
        """A Polygon should not be created manually."""

        self.vertices = vertices
        """A (N, 3) float array containing the points in the polygon."""
        self.normals = normals
        """A (N, 3) float array with the normals for points in the polygon. Can be None."""
        self.texcoords = texcoords
        """A tuple where entries are numpy float arrays of size (N, 2) containing
        the texture coordinates for the points in the polygon for each texture
        coordinate set. Can be length 0 if there are no texture coordinates."""
        self.material = material
        """If coming from an unbound :class:`collada.polylist.Polylist`, contains a
        string with the material symbol. If coming from a bound
        :class:`collada.polylist.BoundPolylist`, contains the actual
        :class:`collada.material.Effect` the line is bound to."""
        self.indices = indices
        """A (N,) int array containing the indices for the vertices
           of the N points in the polygon."""
        self.normal_indices = normal_indices
        """A (N,) int array containing the indices for the normals of
           the N points in the polygon"""
        self.texcoord_indices = texcoord_indices
        """A (N,2) int array with texture coordinate indexes for the
           texcoords of the N points in the polygon"""

    def triangles(self):
        """This triangulates the polygon using a simple fanning method.

        :rtype: generator of :class:`collada.polylist.Polygon`
        """

        npts = len(self.vertices)

        for i in range(npts-2):

            tri_indices = numpy.array([
                self.indices[0], self.indices[i+1], self.indices[i+2]
                ], dtype=numpy.float32)

            tri_vertices = numpy.array([
                self.vertices[0], self.vertices[i+1], self.vertices[i+2]
                ], dtype=numpy.float32)

            if self.normals is None:
                tri_normals = None
                normal_indices = None
            else:
                tri_normals = numpy.array([
                    self.normals[0], self.normals[i+1], self.normals[i+2]
                    ], dtype=numpy.float32)
                normal_indices = numpy.array([
                    self.normal_indices[0],
                    self.normal_indices[i+1],
                    self.normal_indices[i+2]
                    ], dtype=numpy.float32)

            tri_texcoords = []
            tri_texcoord_indices = []
            for texcoord, texcoord_indices in zip(
                    self.texcoords, self.texcoord_indices):
                tri_texcoords.append(numpy.array([
                    texcoord[0],
                    texcoord[i+1],
                    texcoord[i+2]
                    ], dtype=numpy.float32))
                tri_texcoord_indices.append(numpy.array([
                    texcoord_indices[0],
                    texcoord_indices[i+1],
                    texcoord_indices[i+2]
                    ], dtype=numpy.float32))

            tri = triangleset.Triangle(
                    tri_indices, tri_vertices,
                    normal_indices, tri_normals,
                    tri_texcoord_indices, tri_texcoords,
                    self.material)
            yield tri

    def __repr__(self):
        return '<Polygon vertices=%d>' % len(self.vertices)

    def __str__(self):
        return repr(self)


class Polylist(primitive.Primitive):
    """Class containing the data COLLADA puts in a <polylist> tag, a collection of
    polygons. The Polylist object is read-only. To modify a Polylist, create a new
    instance using :meth:`collada.geometry.Geometry.createPolylist`.

    * If ``P`` is an instance of :class:`collada.polylist.Polylist`, then ``len(P)``
      returns the number of polygons in the set. ``P[i]`` returns the i\ :sup:`th`
      polygon in the set.
    """

    def __init__(self, sources, material, index, vcounts, xmlnode=None):
        """A Polylist should not be created manually. Instead, call the
        :meth:`collada.geometry.Geometry.createPolylist` method after
        creating a geometry instance.
        """

        if len(sources) == 0: raise DaeIncompleteError('A polylist set needs at least one input for vertex positions')
        if not 'VERTEX' in sources: raise DaeIncompleteError('Polylist requires vertex input')

        #find max offset
        max_offset = max([ max([input[0] for input in input_type_array])
                          for input_type_array in sources.values() if len(input_type_array) > 0])

        self.material = material
        self.index = index
        self.indices = self.index
        self.nindices = max_offset + 1
        self.vcounts = vcounts
        self.sources = sources
        self.index.shape = (-1, self.nindices)
        self.npolygons = len(self.vcounts)
        self.nvertices = numpy.sum(self.vcounts) if len(self.index) > 0 else 0
        self.polyends = numpy.cumsum(self.vcounts)
        self.polystarts = self.polyends - self.vcounts
        self.polyindex = numpy.dstack((self.polystarts, self.polyends))[0]

        if len(self.index) > 0:
            self._vertex = sources['VERTEX'][0][4].data
            self._vertex_index = self.index[:,sources['VERTEX'][0][0]]
            self.maxvertexindex = numpy.max( self._vertex_index )
            checkSource(sources['VERTEX'][0][4], ('X', 'Y', 'Z'), self.maxvertexindex)
        else:
            self._vertex = None
            self._vertex_index = None
            self.maxvertexindex = -1

        if 'NORMAL' in sources and len(sources['NORMAL']) > 0 and len(self.index) > 0:
            self._normal = sources['NORMAL'][0][4].data
            self._normal_index = self.index[:,sources['NORMAL'][0][0]]
            self.maxnormalindex = numpy.max( self._normal_index )
            checkSource(sources['NORMAL'][0][4], ('X', 'Y', 'Z'), self.maxnormalindex)
        else:
            self._normal = None
            self._normal_index = None
            self.maxnormalindex = -1

        if 'TEXCOORD' in sources and len(sources['TEXCOORD']) > 0 \
                and len(self.index) > 0:
            self._texcoordset = tuple([texinput[4].data
                for texinput in sources['TEXCOORD']])
            self._texcoord_indexset = tuple([ self.index[:,sources['TEXCOORD'][i][0]]
                for i in xrange(len(sources['TEXCOORD'])) ])
            self.maxtexcoordsetindex = [numpy.max(each)
                for each in self._texcoord_indexset]
            for i, texinput in enumerate(sources['TEXCOORD']):
                checkSource(texinput[4], ('S', 'T'), self.maxtexcoordsetindex[i])
        else:
            self._texcoordset = tuple()
            self._texcoord_indexset = tuple()
            self.maxtexcoordsetindex = -1

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the line set."""
        else:
            txtindices = ' '.join(map(str, self.indices.flatten().tolist()))
            acclen = len(self.indices)

            self.xmlnode = E.polylist(count=str(self.npolygons),
                    material=self.material)

            all_inputs = []
            for semantic_list in self.sources.values():
                all_inputs.extend(semantic_list)
            for offset, semantic, sourceid, set, src in all_inputs:
                inpnode = E.input(offset=str(offset), semantic=semantic,
                        source=sourceid)
                if set is not None:
                    inpnode.set('set', str(set))
                self.xmlnode.append(inpnode)

            vcountnode = E.vcount(' '.join(map(str, self.vcounts)))
            self.xmlnode.append(vcountnode)
            self.xmlnode.append(E.p(txtindices))

    def __len__(self):
        return self.npolygons

    def __getitem__(self, i):
        polyrange = self.polyindex[i]
        vertindex = self._vertex_index[polyrange[0]:polyrange[1]]
        v = self._vertex[vertindex]

        normalindex = None
        if self.normal is None:
            n = None
        else:
            normalindex = self._normal_index[polyrange[0]:polyrange[1]]
            n = self._normal[normalindex]

        uvindices = []
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uvindices.append( uvindex[polyrange[0]:polyrange[1]] )
            uv.append( self._texcoordset[j][ uvindex[polyrange[0]:polyrange[1]] ] )

        return Polygon(vertindex, v, normalindex, n, uvindices, uv, self.material)

    _triangleset = None
    def triangleset(self):
        """This performs a simple triangulation of the polylist using the fanning method.

        :rtype: :class:`collada.triangleset.TriangleSet`
        """

        if self._triangleset is None:
            indexselector = numpy.zeros(self.nvertices) == 0
            indexselector[self.polyindex[:,1]-1] = False
            indexselector[self.polyindex[:,1]-2] = False
            indexselector = numpy.arange(self.nvertices)[indexselector]

            firstpolyindex = numpy.arange(self.nvertices)
            firstpolyindex = firstpolyindex - numpy.repeat(self.polyends - self.vcounts, self.vcounts)
            firstpolyindex = firstpolyindex[indexselector]

            if len(self.index) > 0:
                triindex = numpy.dstack( (self.index[indexselector-firstpolyindex],
                                          self.index[indexselector+1],
                                          self.index[indexselector+2]) )
                triindex = numpy.swapaxes(triindex, 1,2).flatten()
            else:
                triindex = numpy.array([], dtype=self.index.dtype)

            triset = triangleset.TriangleSet(self.sources, self.material, triindex, self.xmlnode)

            self._triangleset = triset
        return self._triangleset

    @staticmethod
    def load( collada, localscope, node ):
        indexnode = node.find(tag('p'))
        if indexnode is None: raise DaeIncompleteError('Missing index in polylist')
        vcountnode = node.find(tag('vcount'))
        if vcountnode is None: raise DaeIncompleteError('Missing vcount in polylist')

        try:
            if vcountnode.text is None:
                vcounts = numpy.array([], dtype=numpy.int32)
            else:
                vcounts = numpy.fromstring(vcountnode.text, dtype=numpy.int32, sep=' ')
            vcounts[numpy.isnan(vcounts)] = 0
        except ValueError as ex:
            raise DaeMalformedError('Corrupted vcounts in polylist')

        all_inputs = primitive.Primitive._getInputs(collada, localscope, node.findall(tag('input')))

        try:
            if indexnode.text is None:
                index = numpy.array([], dtype=numpy.int32)
            else:
                index = numpy.fromstring(indexnode.text, dtype=numpy.int32, sep=' ')
            index[numpy.isnan(index)] = 0
        except: raise DaeMalformedError('Corrupted index in polylist')

        polylist = Polylist(all_inputs, node.get('material'), index, vcounts, node)
        return polylist

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound polylist from this polylist, transform and material mapping"""
        return BoundPolylist( self, matrix, materialnodebysymbol)

    def __str__(self):
        return '<Polylist length=%d>' % len(self)

    def __repr__(self):
        return str(self)


class BoundPolylist(primitive.BoundPrimitive):
    """A polylist bound to a transform matrix and materials mapping.

    * If ``P`` is an instance of :class:`collada.polylist.BoundPolylist`, then ``len(P)``
      returns the number of polygons in the set. ``P[i]`` returns the i\ :sup:`th`
      polygon in the set.
    """

    def __init__(self, pl, matrix, materialnodebysymbol):
        """Create a bound polylist from a polylist, transform and material mapping.
        This gets created when a polylist is instantiated in a scene. Do not create this manually."""
        M = numpy.asmatrix(matrix).transpose()
        self._vertex = None if pl._vertex is None else numpy.asarray(pl._vertex * M[:3,:3]) + matrix[:3,3]
        self._normal = None if pl._normal is None else numpy.asarray(pl._normal * M[:3,:3])
        self._texcoordset = pl._texcoordset
        matnode = materialnodebysymbol.get( pl.material )
        if matnode:
            self.material = matnode.target
            self.inputmap = dict([ (sem, (input_sem, set)) for sem, input_sem, set in matnode.inputs ])
        else: self.inputmap = self.material = None
        self.index = pl.index
        self.nvertices = pl.nvertices
        self._vertex_index = pl._vertex_index
        self._normal_index = pl._normal_index
        self._texcoord_indexset = pl._texcoord_indexset
        self.polyindex = pl.polyindex
        self.npolygons = pl.npolygons
        self.matrix = matrix
        self.materialnodebysymbol = materialnodebysymbol
        self.original = pl

    def __len__(self): return self.npolygons

    def __getitem__(self, i):
        polyrange = self.polyindex[i]
        vertindex = self._vertex_index[polyrange[0]:polyrange[1]]
        v = self._vertex[vertindex]

        normalindex = None
        if self.normal is None:
            n = None
        else:
            normalindex = self._normal_index[polyrange[0]:polyrange[1]]
            n = self._normal[normalindex]

        uvindices = []
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uvindices.append( uvindex[polyrange[0]:polyrange[1]] )
            uv.append( self._texcoordset[j][ uvindex[polyrange[0]:polyrange[1]] ] )

        return Polygon(vertindex, v, normalindex, n, uvindices, uv, self.material)

    _triangleset = None
    def triangleset(self):
        """This performs a simple triangulation of the polylist using the fanning method.

        :rtype: :class:`collada.triangleset.BoundTriangleSet`
        """
        if self._triangleset is None:
            triset = self.original.triangleset()
            boundtriset = triset.bind(self.matrix, self.materialnodebysymbol)
            self._triangleset = boundtriset
        return self._triangleset

    def polygons(self):
        """Iterate through all the polygons contained in the set.

        :rtype: generator of :class:`collada.polylist.Polygon`
        """
        for i in xrange(self.npolygons): yield self[i]

    def shapes(self):
        """Iterate through all the polygons contained in the set.

        :rtype: generator of :class:`collada.polylist.Polygon`
        """
        return self.polygons()

    def __str__(self):
        return '<BoundPolylist length=%d>' % len(self)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = primitive
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module containing the base class for primitives"""
import numpy
import types

from collada.common import DaeObject
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.source import InputList

class Primitive(DaeObject):
    """Base class for all primitive sets like TriangleSet, LineSet, Polylist, etc."""

    vertex = property( lambda s: s._vertex, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertex points in the
    primitive's vertex source array.""" )
    normal = property( lambda s: s._normal, doc=
    """Read-only numpy.array of size Nx3 where N is the number of normal values in the
    primitive's normal source array.""" )
    texcoordset = property( lambda s: s._texcoordset, doc=
    """Read-only tuple of texture coordinate arrays. Each value is a numpy.array of size
    Nx2 where N is the number of texture coordinates in the primitive's source array.""" )
    textangentset = property( lambda s: s._textangentset, doc=
    """Read-only tuple of texture tangent arrays. Each value is a numpy.array of size
    Nx3 where N is the number of texture tangents in the primitive's source array.""" )
    texbinormalset = property( lambda s: s._texbinormalset, doc=
    """Read-only tuple of texture binormal arrays. Each value is a numpy.array of size
    Nx3 where N is the number of texture binormals in the primitive's source array.""" )

    vertex_index = property( lambda s: s._vertex_index, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertices in the primitive.
    To get the actual vertex points, one can use this array to select into the vertex
    array, e.g. ``vertex[vertex_index]``.""" )
    normal_index = property( lambda s: s._normal_index, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertices in the primitive.
    To get the actual normal values, one can use this array to select into the normals
    array, e.g. ``normal[normal_index]``.""" )
    texcoord_indexset = property( lambda s: s._texcoord_indexset, doc=
    """Read-only tuple of texture coordinate index arrays. Each value is a numpy.array of size
    Nx2 where N is the number of vertices in the primitive. To get the actual texture
    coordinates, one can use the array to select into the texcoordset array, e.g.
    ``texcoordset[0][texcoord_indexset[0]]`` would select the first set of texture
    coordinates.""" )
    textangent_indexset = property( lambda s: s._textangent_indexset, doc=
    """Read-only tuple of texture tangent index arrays. Each value is a numpy.array of size
    Nx3 where N is the number of vertices in the primitive. To get the actual texture
    tangents, one can use the array to select into the textangentset array, e.g.
    ``textangentset[0][textangent_indexset[0]]`` would select the first set of texture
    tangents.""" )
    texbinormal_indexset = property( lambda s: s._texbinormal_indexset, doc=
    """Read-only tuple of texture binormal index arrays. Each value is a numpy.array of size
    Nx3 where N is the number of vertices in the primitive. To get the actual texture
    binormals, one can use the array to select into the texbinormalset array, e.g.
    ``texbinormalset[0][texbinormal_indexset[0]]`` would select the first set of texture
    binormals.""" )

    def bind(self, matrix, materialnodebysymbol):
        """Binds this primitive to a transform matrix and material mapping.
        The primitive's points get transformed by the given matrix and its
        inputs get mapped to the given materials.

        :param numpy.array matrix:
          A 4x4 numpy float matrix
        :param dict materialnodebysymbol:
          A dictionary with the material symbols inside the primitive
          assigned to :class:`collada.scene.MaterialNode` defined in the
          scene

        :rtype: :class:`collada.primitive.Primitive`

        """
        pass

    @staticmethod
    def _getInputsFromList(collada, localscope, inputs):
        #first let's save any of the source that are references to a dict
        to_append = []
        for input in inputs:
            offset, semantic, source, set = input
            if semantic == 'VERTEX':
                vertex_source = localscope.get(source[1:])
                if isinstance(vertex_source, dict):
                    for inputsemantic, inputsource in vertex_source.items():
                        if inputsemantic == 'POSITION':
                            to_append.append([offset, 'VERTEX', '#' + inputsource.id, set])
                        else:
                            to_append.append([offset, inputsemantic, '#' + inputsource.id, set])

        #remove all the dicts
        inputs[:] = [input for input in inputs
                if not isinstance(localscope.get(input[2][1:]), dict)]

        #append the dereferenced dicts
        for a in to_append:
            inputs.append(a)

        vertex_inputs = []
        normal_inputs = []
        texcoord_inputs = []
        textangent_inputs = []
        texbinormal_inputs = []
        color_inputs = []
        tangent_inputs = []
        binormal_inputs = []

        all_inputs = {}

        for input in inputs:
            offset, semantic, source, set = input
            if len(source) < 2 or source[0] != '#':
                raise DaeMalformedError('Incorrect source id "%s" in input' % source)
            if source[1:] not in localscope:
                raise DaeBrokenRefError('Source input id "%s" not found' % source)
            input = (input[0], input[1], input[2], input[3], localscope[source[1:]])
            if semantic == 'VERTEX':
                vertex_inputs.append(input)
            elif semantic == 'NORMAL':
                normal_inputs.append(input)
            elif semantic == 'TEXCOORD':
                texcoord_inputs.append(input)
            elif semantic == 'TEXTANGENT':
                textangent_inputs.append(input)
            elif semantic == 'TEXBINORMAL':
                texbinormal_inputs.append(input)
            elif semantic == 'COLOR':
                color_inputs.append(input)
            elif semantic == 'TANGENT':
                tangent_inputs.append(input)
            elif semantic == 'BINORMAL':
                binormal_inputs.append(input)
            else:
                try:
                    raise DaeUnsupportedError('Unknown input semantic: %s' % semantic)
                except DaeUnsupportedError as ex:
                    collada.handleError(ex)
                unknown_input = all_inputs.get(semantic, [])
                unknown_input.append(input)
                all_inputs[semantic] = unknown_input

        all_inputs['VERTEX'] = vertex_inputs
        all_inputs['NORMAL'] = normal_inputs
        all_inputs['TEXCOORD'] = texcoord_inputs
        all_inputs['TEXBINORMAL'] = texbinormal_inputs
        all_inputs['TEXTANGENT'] = textangent_inputs
        all_inputs['COLOR'] = color_inputs
        all_inputs['TANGENT'] = tangent_inputs
        all_inputs['BINORMAL'] = binormal_inputs

        return all_inputs

    @staticmethod
    def _getInputs(collada, localscope, inputnodes):
        try:
            inputs = [(int(i.get('offset')), i.get('semantic'),
                    i.get('source'), i.get('set'))
                for i in inputnodes]
        except ValueError as ex:
            raise DaeMalformedError('Corrupted offsets in primitive')

        return Primitive._getInputsFromList(collada, localscope, inputs)

    def getInputList(self):
        """Gets a :class:`collada.source.InputList` representing the inputs from a primitive"""
        inpl = InputList()
        for (key, tupes) in self.sources.iteritems():
            for (offset, semantic, source, set, srcobj) in tupes:
                inpl.addInput(offset, semantic, source, set)
        return inpl

    def save(self):
        return NotImplementedError("Primitives are read-only")

class BoundPrimitive(object):
    """A :class:`collada.primitive.Primitive` bound to a transform matrix
    and material mapping."""

    def shapes(self):
        """Iterate through the items in this primitive. The shape returned
        depends on the primitive type. Examples: Triangle, Polygon."""
        pass

    vertex = property( lambda s: s._vertex, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertex points in the
    primitive's vertex source array. The values will be transformed according to the
    bound transformation matrix.""" )
    normal = property( lambda s: s._normal, doc=
    """Read-only numpy.array of size Nx3 where N is the number of normal values in the
    primitive's normal source array. The values will be transformed according to the
    bound transformation matrix.""" )
    texcoordset = property( lambda s: s._texcoordset, doc=
    """Read-only tuple of texture coordinate arrays. Each value is a numpy.array of size
    Nx2 where N is the number of texture coordinates in the primitive's source array. The
    values will be transformed according to the bound transformation matrix.""" )
    vertex_index = property( lambda s: s._vertex_index, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertices in the primitive.
    To get the actual vertex points, one can use this array to select into the vertex
    array, e.g. ``vertex[vertex_index]``. The values will be transformed according to the
    bound transformation matrix.""" )
    normal_index = property( lambda s: s._normal_index, doc=
    """Read-only numpy.array of size Nx3 where N is the number of vertices in the primitive.
    To get the actual normal values, one can use this array to select into the normals
    array, e.g. ``normal[normal_index]``. The values will be transformed according to the
    bound transformation matrix.""" )
    texcoord_indexset = property( lambda s: s._texcoord_indexset, doc=
    """Read-only tuple of texture coordinate index arrays. Each value is a numpy.array of size
    Nx2 where N is the number of vertices in the primitive. To get the actual texture
    coordinates, one can use the array to select into the texcoordset array, e.g.
    ``texcoordset[0][texcoord_indexset[0]]`` would select the first set of texture
    coordinates. The values will be transformed according to the bound transformation matrix.""" )

########NEW FILE########
__FILENAME__ = scene
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""This module contains several classes related to the scene graph.

Supported scene nodes are:
  * <node> which is loaded as a Node
  * <instance_camera> which is loaded as a CameraNode
  * <instance_light> which is loaded as a LightNode
  * <instance_material> which is loaded as a MaterialNode
  * <instance_geometry> which is loaded as a GeometryNode
  * <instance_controller> which is loaded as a ControllerNode
  * <scene> which is loaded as a Scene

"""

import copy
import numpy

from collada.common import DaeObject, E, tag
from collada.common import DaeError, DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import toUnitVec
from collada.xmlutil import etree as ElementTree


class DaeInstanceNotLoadedError(Exception):
    """Raised when an instance_node refers to a node that isn't loaded yet. Will always be caught"""
    def __init__(self, msg):
        super(DaeInstanceNotLoadedError,self).__init__()
        self.msg = msg


class SceneNode(DaeObject):
    """Abstract base class for all nodes within a scene."""

    def objects(self, tipo, matrix=None):
        """Iterate through all objects under this node that match `tipo`.
        The objects will be bound and transformed via the scene transformations.

        :param str tipo:
          A string for the desired object type. This can be one of 'geometry',
          'camera', 'light', or 'controller'.
        :param numpy.matrix matrix:
          An optional transformation matrix

        :rtype: generator that yields the type specified

        """
        pass


def makeRotationMatrix(x, y, z, angle):
    """Build and return a transform 4x4 matrix to rotate `angle` radians
    around (`x`,`y`,`z`) axis."""
    c = numpy.cos(angle)
    s = numpy.sin(angle)
    t = (1-c)
    return numpy.array([[t*x*x+c,     t*x*y - s*z, t*x*z + s*y, 0],
                        [t*x*y+s*z,   t*y*y + c,   t*y*z - s*x, 0],
                        [t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0],
                        [0,           0,           0,           1]],
                       dtype=numpy.float32 )


class Transform(DaeObject):
    """Base class for all transformation types"""

    def save(self):
        pass


class TranslateTransform(Transform):
    """Contains a translation transformation as defined in the collada <translate> tag."""

    def __init__(self, x, y, z, xmlnode=None):
        """Creates a translation transformation

        :param float x:
          x coordinate
        :param float y:
          y coordinate
        :param float z:
          z coordinate
        :param xmlnode:
           When loaded, the xmlnode it comes from

        """
        self.x = x
        """x coordinate"""
        self.y = y
        """y coordinate"""
        self.z = z
        """z coordinate"""
        self.matrix = numpy.identity(4, dtype=numpy.float32)
        """The resulting transformation matrix. This will be a numpy.array of size 4x4."""
        self.matrix[:3,3] = [ x, y, z ]
        self.xmlnode = xmlnode
        """ElementTree representation of the transform."""
        if xmlnode is None:
            self.xmlnode = E.translate(' '.join([str(x),str(y),str(z)]))

    @staticmethod
    def load(collada, node):
        floats = numpy.fromstring(node.text, dtype=numpy.float32, sep=' ')
        if len(floats) != 3:
            raise DaeMalformedError("Translate node requires three float values")
        return TranslateTransform(floats[0], floats[1], floats[2], node)

    def __str__(self):
        return '<TranslateTransform (%s, %s, %s)>' % (self.x, self.y, self.z)

    def __repr__(self):
        return str(self)


class RotateTransform(Transform):
    """Contains a rotation transformation as defined in the collada <rotate> tag."""

    def __init__(self, x, y, z, angle, xmlnode=None):
        """Creates a rotation transformation

        :param float x:
          x coordinate
        :param float y:
          y coordinate
        :param float z:
          z coordinate
        :param float angle:
          angle of rotation, in radians
        :param xmlnode:
           When loaded, the xmlnode it comes from

        """
        self.x = x
        """x coordinate"""
        self.y = y
        """y coordinate"""
        self.z = z
        """z coordinate"""
        self.angle = angle
        """angle of rotation, in radians"""
        self.matrix = makeRotationMatrix(x, y, z, angle*numpy.pi/180.0)
        """The resulting transformation matrix. This will be a numpy.array of size 4x4."""
        self.xmlnode = xmlnode
        """ElementTree representation of the transform."""
        if xmlnode is None:
            self.xmlnode = E.rotate(' '.join([str(x),str(y),str(z),str(angle)]))

    @staticmethod
    def load(collada, node):
        floats = numpy.fromstring(node.text, dtype=numpy.float32, sep=' ')
        if len(floats) != 4:
            raise DaeMalformedError("Rotate node requires four float values")
        return RotateTransform(floats[0], floats[1], floats[2], floats[3], node)

    def __str__(self):
        return '<RotateTransform (%s, %s, %s) angle=%s>' % (self.x, self.y, self.z, self.angle)

    def __repr__(self):
        return str(self)


class ScaleTransform(Transform):
    """Contains a scale transformation as defined in the collada <scale> tag."""

    def __init__(self, x, y, z, xmlnode=None):
        """Creates a scale transformation

        :param float x:
          x coordinate
        :param float y:
          y coordinate
        :param float z:
          z coordinate
        :param xmlnode:
           When loaded, the xmlnode it comes from

        """
        self.x = x
        """x coordinate"""
        self.y = y
        """y coordinate"""
        self.z = z
        """z coordinate"""
        self.matrix = numpy.identity(4, dtype=numpy.float32)
        """The resulting transformation matrix. This will be a numpy.array of size 4x4."""
        self.matrix[0,0] = x
        self.matrix[1,1] = y
        self.matrix[2,2] = z
        self.xmlnode = xmlnode
        """ElementTree representation of the transform."""
        if xmlnode is None:
            self.xmlnode = E.scale(' '.join([str(x),str(y),str(z)]))

    @staticmethod
    def load(collada, node):
        floats = numpy.fromstring(node.text, dtype=numpy.float32, sep=' ')
        if len(floats) != 3:
            raise DaeMalformedError("Scale node requires three float values")
        return ScaleTransform(floats[0], floats[1], floats[2], node)

    def __str__(self):
        return '<ScaleTransform (%s, %s, %s)>' % (self.x, self.y, self.z)

    def __repr__(self):
        return str(self)


class MatrixTransform(Transform):
    """Contains a matrix transformation as defined in the collada <matrix> tag."""

    def __init__(self, matrix, xmlnode=None):
        """Creates a matrix transformation

        :param numpy.array matrix:
          This should be an unshaped numpy array of floats of length 16
        :param xmlnode:
           When loaded, the xmlnode it comes from

        """
        self.matrix = matrix
        """The resulting transformation matrix. This will be a numpy.array of size 4x4."""
        if len(self.matrix) != 16: raise DaeMalformedError('Corrupted matrix transformation node')
        self.matrix.shape = (4, 4)
        self.xmlnode = xmlnode
        """ElementTree representation of the transform."""
        if xmlnode is None:
            self.xmlnode = E.matrix(' '.join(map(str, self.matrix.flat)))

    @staticmethod
    def load(collada, node):
        floats = numpy.fromstring(node.text, dtype=numpy.float32, sep=' ')
        return MatrixTransform(floats, node)

    def __str__(self):
        return '<MatrixTransform>'

    def __repr__(self):
        return str(self)


class LookAtTransform(Transform):
    """Contains a transformation for aiming a camera as defined in the collada <lookat> tag."""

    def __init__(self, eye, interest, upvector, xmlnode=None):
        """Creates a lookat transformation

        :param numpy.array eye:
          An unshaped numpy array of floats of length 3 containing the position of the eye
        :param numpy.array interest:
          An unshaped numpy array of floats of length 3 containing the point of interest
        :param numpy.array upvector:
          An unshaped numpy array of floats of length 3 containing the up-axis direction
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.eye = eye
        """A numpy array of length 3 containing the position of the eye"""
        self.interest = interest
        """A numpy array of length 3 containing the point of interest"""
        self.upvector = upvector
        """A numpy array of length 3 containing the up-axis direction"""

        if len(eye) != 3 or len(interest) != 3 or len(upvector) != 3:
            raise DaeMalformedError('Corrupted lookat transformation node')

        self.matrix = numpy.identity(4, dtype=numpy.float32)
        """The resulting transformation matrix. This will be a numpy.array of size 4x4."""

        front = toUnitVec(numpy.subtract(eye,interest))
        side = numpy.multiply(-1, toUnitVec(numpy.cross(front, upvector)))
        self.matrix[0,0:3] = side
        self.matrix[1,0:3] = upvector
        self.matrix[2,0:3] = front
        self.matrix[3,0:3] = eye

        self.xmlnode = xmlnode
        """ElementTree representation of the transform."""
        if xmlnode is None:
            self.xmlnode = E.lookat(' '.join(map(str,
                                        numpy.concatenate((self.eye, self.interest, self.upvector)) )))
    @staticmethod
    def load(collada, node):
        floats = numpy.fromstring(node.text, dtype=numpy.float32, sep=' ')
        if len(floats) != 9:
            raise DaeMalformedError("Lookat node requires 9 float values")
        return LookAtTransform(floats[0:3], floats[3:6], floats[6:9], node)

    def __str__(self):
        return '<LookAtTransform>'

    def __repr__(self):
        return str(self)


class Node(SceneNode):
    """Represents a node object, which is a point on the scene graph, as defined in the collada <node> tag.

    Contains the list of transformations effecting the node as well as any children.
    """

    def __init__(self, id, children=None, transforms=None, xmlnode=None):
        """Create a node in the scene graph.

        :param str id:
          A unique string identifier for the node
        :param list children:
          A list of child nodes of this node. This can contain any
          object that inherits from :class:`collada.scene.SceneNode`
        :param list transforms:
          A list of transformations effecting the node. This can
          contain any object that inherits from :class:`collada.scene.Transform`
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.id = id
        """The unique string identifier for the node"""
        self.children = []
        """A list of child nodes of this node. This can contain any
          object that inherits from :class:`collada.scene.SceneNode`"""
        if children is not None:
            self.children = children
        self.transforms = []
        if transforms is not None:
            self.transforms = transforms
        """A list of transformations effecting the node. This can
          contain any object that inherits from :class:`collada.scene.Transform`"""
        self.matrix = numpy.identity(4, dtype=numpy.float32)
        """A numpy.array of size 4x4 containing a transformation matrix that
        combines all the transformations in :attr:`transforms`. This will only
        be updated after calling :meth:`save`."""

        for t in self.transforms:
            self.matrix = numpy.dot(self.matrix, t.matrix)

        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the transform."""
        else:
            self.xmlnode = E.node(id=self.id, name=self.id)
            for t in self.transforms:
                self.xmlnode.append(t.xmlnode)
            for c in self.children:
                self.xmlnode.append(c.xmlnode)

    def objects(self, tipo, matrix=None):
        """Iterate through all objects under this node that match `tipo`.
        The objects will be bound and transformed via the scene transformations.

        :param str tipo:
          A string for the desired object type. This can be one of 'geometry',
          'camera', 'light', or 'controller'.
        :param numpy.matrix matrix:
          An optional transformation matrix

        :rtype: generator that yields the type specified

        """
        if matrix != None: M = numpy.dot( matrix, self.matrix )
        else: M = self.matrix
        for node in self.children:
            for obj in node.objects(tipo, M):
                yield obj

    def save(self):
        """Saves the geometry back to :attr:`xmlnode`. Also updates
        :attr:`matrix` if :attr:`transforms` has been modified."""
        self.matrix = numpy.identity(4, dtype=numpy.float32)
        for t in self.transforms:
            self.matrix = numpy.dot(self.matrix, t.matrix)

        for child in self.children:
            child.save()

        if self.id is not None:
            self.xmlnode.set('id', self.id)
            self.xmlnode.set('name', self.id)
        for t in self.transforms:
            if t.xmlnode not in self.xmlnode:
                self.xmlnode.append(t.xmlnode)
        for c in self.children:
            if c.xmlnode not in self.xmlnode:
                self.xmlnode.append(c.xmlnode)
        xmlnodes = [c.xmlnode for c in self.children]
        xmlnodes.extend([t.xmlnode for t in self.transforms])
        for n in self.xmlnode:
            if n not in xmlnodes:
                self.xmlnode.remove(n)

    @staticmethod
    def load( collada, node, localscope ):
        id = node.get('id')
        children = []
        transforms = []

        for subnode in node:
            try:
                n = loadNode(collada, subnode, localscope)
                if isinstance(n, Transform):
                    transforms.append(n)
                elif n is not None:
                    children.append(n)
            except DaeError as ex:
                collada.handleError(ex)

        return Node(id, children, transforms, xmlnode=node)

    def __str__(self):
        return '<Node transforms=%d, children=%d>' % (len(self.transforms), len(self.children))

    def __repr__(self):
        return str(self)


class NodeNode(Node):
    """Represents a node being instantiated in a scene, as defined in the collada <instande_node> tag."""

    def __init__(self, node, xmlnode=None):
        """Creates a node node

        :param collada.scene.Node node:
          A node to instantiate in the scene
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.node = node
        """An object of type :class:`collada.scene.Node` representing the node to bind in the scene"""

        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the node node."""
        else:
            self.xmlnode = E.instance_node(url="#%s" % self.node.id)

    def objects(self, tipo, matrix=None):
        for obj in self.node.objects(tipo, matrix):
            yield obj

    id = property(lambda s: s.node.id)
    children = property(lambda s: s.node.children)
    matrix = property(lambda s: s.node.matrix)

    @staticmethod
    def load( collada, node, localscope ):
        url = node.get('url')
        if not url.startswith('#'):
            raise DaeMalformedError('Invalid url in node instance %s' % url)
        referred_node = localscope.get(url[1:])
        if not referred_node:
            referred_node = collada.nodes.get(url[1:])
        if not referred_node:
            raise DaeInstanceNotLoadedError('Node %s not found in library'%url)
        return NodeNode(referred_node, xmlnode=node)

    def save(self):
        """Saves the node node back to :attr:`xmlnode`"""
        self.xmlnode.set('url', "#%s" % self.node.id)

    def __str__(self):
        return '<NodeNode node=%s>' % (self.node.id,)

    def __repr__(self):
        return str(self)


class GeometryNode(SceneNode):
    """Represents a geometry instance in a scene, as defined in the collada <instance_geometry> tag."""

    def __init__(self, geometry, materials=None, xmlnode=None):
        """Creates a geometry node

        :param collada.geometry.Geometry geometry:
          A geometry to instantiate in the scene
        :param list materials:
          A list containing items of type :class:`collada.scene.MaterialNode`.
          Each of these represents a material that the geometry should be
          bound to.
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.geometry = geometry
        """An object of type :class:`collada.geometry.Geometry` representing the
        geometry to bind in the scene"""
        self.materials = []
        """A list containing items of type :class:`collada.scene.MaterialNode`.
          Each of these represents a material that the geometry is bound to."""
        if materials is not None:
            self.materials = materials
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the geometry node."""
        else:
            self.xmlnode = E.instance_geometry(url="#%s" % self.geometry.id)
            if len(self.materials) > 0:
                self.xmlnode.append(E.bind_material(
                    E.technique_common(
                        *[mat.xmlnode for mat in self.materials]
                    )
                ))

    def objects(self, tipo, matrix=None):
        """Yields a :class:`collada.geometry.BoundGeometry` if ``tipo=='geometry'``"""
        if tipo == 'geometry':
            if matrix is None: matrix = numpy.identity(4, dtype=numpy.float32)
            materialnodesbysymbol = {}
            for mat in self.materials:
                materialnodesbysymbol[mat.symbol] = mat
            yield self.geometry.bind(matrix, materialnodesbysymbol)

    @staticmethod
    def load( collada, node ):
        url = node.get('url')
        if not url.startswith('#'): raise DaeMalformedError('Invalid url in geometry instance %s' % url)
        geometry = collada.geometries.get(url[1:])
        if not geometry: raise DaeBrokenRefError('Geometry %s not found in library'%url)
        matnodes = node.findall('%s/%s/%s'%( tag('bind_material'), tag('technique_common'), tag('instance_material') ) )
        materials = []
        for matnode in matnodes:
            materials.append( MaterialNode.load(collada, matnode) )
        return GeometryNode( geometry, materials, xmlnode=node)

    def save(self):
        """Saves the geometry node back to :attr:`xmlnode`"""
        self.xmlnode.set('url', "#%s" % self.geometry.id)

        for m in self.materials:
            m.save()

        matparent = self.xmlnode.find('%s/%s'%( tag('bind_material'), tag('technique_common') ) )
        if matparent is None and len(self.materials)==0:
            return
        elif matparent is None:
            matparent = E.technique_common()
            self.xmlnode.append(E.bind_material(matparent))
        elif len(self.materials) == 0 and matparent is not None:
            bindnode = self.xmlnode.find('%s' % tag('bind_material'))
            self.xmlnode.remove(bindnode)
            return

        for m in self.materials:
            if m.xmlnode not in matparent:
                matparent.append(m.xmlnode)
        xmlnodes = [m.xmlnode for m in self.materials]
        for n in matparent:
            if n not in xmlnodes:
                matparent.remove(n)

    def __str__(self):
        return '<GeometryNode geometry=%s>' % (self.geometry.id,)

    def __repr__(self):
        return str(self)


class ControllerNode(SceneNode):
    """Represents a controller instance in a scene, as defined in the collada <instance_controller> tag. **This class is highly
    experimental. More support will be added in version 0.4.**"""

    def __init__(self, controller, materials, xmlnode=None):
        """Creates a controller node

        :param collada.controller.Controller controller:
          A controller to instantiate in the scene
        :param list materials:
          A list containing items of type :class:`collada.scene.MaterialNode`.
          Each of these represents a material that the controller should be
          bound to.
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.controller = controller
        """ An object of type :class:`collada.controller.Controller` representing
        the controller being instantiated in the scene"""
        self.materials = materials
        """A list containing items of type :class:`collada.scene.MaterialNode`.
          Each of these represents a material that the controller is bound to."""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the controller node."""
        else:
            self.xmlnode = ElementTree.Element( tag('instance_controller') )
            bindnode = ElementTree.Element( tag('bind_material') )
            technode = ElementTree.Element( tag('technique_common') )
            bindnode.append( technode )
            self.xmlnode.append( bindnode )
            for mat in materials: technode.append( mat.xmlnode )

    def objects(self, tipo, matrix=None):
        """Yields a :class:`collada.controller.BoundController` if ``tipo=='controller'``"""
        if tipo == 'controller':
            if matrix is None: matrix = numpy.identity(4, dtype=numpy.float32)
            materialnodesbysymbol = {}
            for mat in self.materials:
                materialnodesbysymbol[mat.symbol] = mat
            yield self.controller.bind(matrix, materialnodesbysymbol)

    @staticmethod
    def load( collada, node ):
        url = node.get('url')
        if not url.startswith('#'): raise DaeMalformedError('Invalid url in controller instance %s' % url)
        controller = collada.controllers.get(url[1:])
        if not controller: raise DaeBrokenRefError('Controller %s not found in library'%url)
        matnodes = node.findall('%s/%s/%s'%( tag('bind_material'), tag('technique_common'), tag('instance_material') ) )
        materials = []
        for matnode in matnodes:
            materials.append( MaterialNode.load(collada, matnode) )
        return ControllerNode( controller, materials, xmlnode=node)

    def save(self):
        """Saves the controller node back to :attr:`xmlnode`"""
        self.xmlnode.set('url', '#'+self.controller.id)
        for mat in self.materials:
            mat.save()

    def __str__(self):
        return '<ControllerNode controller=%s>' % (self.controller.id,)

    def __repr__(self):
        return str(self)


class MaterialNode(SceneNode):
    """Represents a material being instantiated in a scene, as defined in the collada <instance_material> tag."""

    def __init__(self, symbol, target, inputs, xmlnode = None):
        """Creates a material node

        :param str symbol:
          The symbol within a geometry this material should be bound to
        :param collada.material.Material target:
          The material object being bound to
        :param list inputs:
          A list of tuples of the form ``(semantic, input_semantic, set)`` mapping
          texcoords or other inputs to material input channels, e.g.
          ``('TEX0', 'TEXCOORD', '0')`` would map the effect parameter ``'TEX0'``
          to the ``'TEXCOORD'`` semantic of the geometry, using texture coordinate
          set ``0``.
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.symbol = symbol
        """The symbol within a geometry this material should be bound to"""
        self.target = target
        """An object of type :class:`collada.material.Material` representing the material object being bound to"""
        self.inputs = inputs
        """A list of tuples of the form ``(semantic, input_semantic, set)`` mapping
          texcoords or other inputs to material input channels, e.g.
          ``('TEX0', 'TEXCOORD', '0')`` would map the effect parameter ``'TEX0'``
          to the ``'TEXCOORD'`` semantic of the geometry, using texture coordinate
          set ``0``."""
        if xmlnode is not None:
            self.xmlnode = xmlnode
            """ElementTree representation of the material node."""
        else:
            self.xmlnode = E.instance_material(
                *[E.bind_vertex_input(semantic=sem, input_semantic=input_sem, input_set=set)
                  for sem, input_sem, set in self.inputs]
            , **{'symbol': self.symbol, 'target':"#%s"%self.target.id} )

    @staticmethod
    def load(collada, node):
        inputs = []
        for inputnode in node.findall( tag('bind_vertex_input') ):
            inputs.append( ( inputnode.get('semantic'), inputnode.get('input_semantic'), inputnode.get('input_set') ) )
        targetid = node.get('target')
        if not targetid.startswith('#'): raise DaeMalformedError('Incorrect target id in material '+targetid)
        target = collada.materials.get(targetid[1:])
        if not target: raise DaeBrokenRefError('Material %s not found'%targetid)
        return MaterialNode(node.get('symbol'), target, inputs, xmlnode = node)

    def objects(self):
        pass

    def save(self):
        """Saves the material node back to :attr:`xmlnode`"""
        self.xmlnode.set('symbol', self.symbol)
        self.xmlnode.set('target', "#%s"%self.target.id)

        inputs_in = []
        for i in self.xmlnode.findall( tag('bind_vertex_input') ):
            input_tuple = ( i.get('semantic'), i.get('input_semantic'), i.get('input_set') )
            if input_tuple not in self.inputs:
                self.xmlnode.remove(i)
            else:
                inputs_in.append(input_tuple)
        for i in self.inputs:
            if i not in inputs_in:
                self.xmlnode.append(E.bind_vertex_input(semantic=i[0], input_semantic=i[1], input_set=i[2]))

    def __str__(self):
        return '<MaterialNode symbol=%s targetid=%s>' % (self.symbol, self.target.id)

    def __repr__(self):
        return str(self)


class CameraNode(SceneNode):
    """Represents a camera being instantiated in a scene, as defined in the collada <instance_camera> tag."""

    def __init__(self, camera, xmlnode=None):
        """Create a camera instance

        :param collada.camera.Camera camera:
          The camera being instantiated
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.camera = camera
        """An object of type :class:`collada.camera.Camera` representing the instantiated camera"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the camera node."""
        else:
            self.xmlnode = E.instance_camera(url="#%s"%camera.id)

    def objects(self, tipo, matrix=None):
        """Yields a :class:`collada.camera.BoundCamera` if ``tipo=='camera'``"""
        if tipo == 'camera':
            if matrix is None: matrix = numpy.identity(4, dtype=numpy.float32)
            yield self.camera.bind(matrix)

    @staticmethod
    def load( collada, node ):
        url = node.get('url')
        if not url.startswith('#'): raise DaeMalformedError('Invalid url in camera instance %s' % url)
        camera = collada.cameras.get(url[1:])
        if not camera: raise DaeBrokenRefError('Camera %s not found in library'%url)
        return CameraNode( camera, xmlnode=node)

    def save(self):
        """Saves the camera node back to :attr:`xmlnode`"""
        self.xmlnode.set('url', '#'+self.camera.id)

    def __str__(self):
        return '<CameraNode camera=%s>' % (self.camera.id,)

    def __repr__(self):
        return str(self)


class LightNode(SceneNode):
    """Represents a light being instantiated in a scene, as defined in the collada <instance_light> tag."""

    def __init__(self, light, xmlnode=None):
        """Create a light instance

        :param collada.light.Light light:
          The light being instantiated
        :param xmlnode:
          When loaded, the xmlnode it comes from

        """
        self.light = light
        """An object of type :class:`collada.light.Light` representing the instantiated light"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the light node."""
        else:
            self.xmlnode = E.instance_light(url="#%s"%light.id)

    def objects(self, tipo, matrix=None):
        """Yields a :class:`collada.light.BoundLight` if ``tipo=='light'``"""
        if tipo == 'light':
            if matrix is None: matrix = numpy.identity(4, dtype=numpy.float32)
            yield self.light.bind(matrix)

    @staticmethod
    def load( collada, node ):
        url = node.get('url')
        if not url.startswith('#'): raise DaeMalformedError('Invalid url in light instance %s' % url)
        light = collada.lights.get(url[1:])
        if not light: raise DaeBrokenRefError('Light %s not found in library'%url)
        return LightNode( light, xmlnode=node)

    def save(self):
        """Saves the light node back to :attr:`xmlnode`"""
        self.xmlnode.set('url', '#'+self.light.id)

    def __str__(self): return '<LightNode light=%s>' % (self.light.id,)
    def __repr__(self): return str(self)


class ExtraNode(SceneNode):
    """Represents extra information in a scene, as defined in a collada <extra> tag."""

    def __init__(self, xmlnode):
        """Create an extra node which stores arbitrary xml

        :param xmlnode:
          Should be an ElementTree instance of tag type <extra>

        """
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the extra node."""
        else:
            self.xmlnode = E.extra()

    def objects(self, tipo, matrix=None):
        if tipo == 'extra':
            for e in self.xmlnode.findall(tag(tipo)):
                yield e

    @staticmethod
    def load( collada, node ):
        return ExtraNode(node)

    def save(self):
        pass


def loadNode( collada, node, localscope ):
    """Generic scene node loading from a xml `node` and a `collada` object.

    Knowing the supported nodes, create the appropiate class for the given node
    and return it.

    """
    if node.tag == tag('node'): return Node.load(collada, node, localscope)
    elif node.tag == tag('translate'): return TranslateTransform.load(collada, node)
    elif node.tag == tag('rotate'): return RotateTransform.load(collada, node)
    elif node.tag == tag('scale'): return ScaleTransform.load(collada, node)
    elif node.tag == tag('matrix'): return MatrixTransform.load(collada, node)
    elif node.tag == tag('lookat'): return LookAtTransform.load(collada, node)
    elif node.tag == tag('instance_geometry'): return GeometryNode.load(collada, node)
    elif node.tag == tag('instance_camera'): return CameraNode.load(collada, node)
    elif node.tag == tag('instance_light'): return LightNode.load(collada, node)
    elif node.tag == tag('instance_controller'): return ControllerNode.load(collada, node)
    elif node.tag == tag('instance_node'): return NodeNode.load(collada, node, localscope)
    elif node.tag == tag('extra'):
        return ExtraNode.load(collada, node)
    elif node.tag == tag('asset'):
        return None
    else: raise DaeUnsupportedError('Unknown scene node %s' % str(node.tag))


class Scene(DaeObject):
    """The root object for a scene, as defined in a collada <scene> tag"""

    def __init__(self, id, nodes, xmlnode=None, collada=None):
        """Create a scene

        :param str id:
          A unique string identifier for the scene
        :param list nodes:
          A list of type :class:`collada.scene.Node` representing the nodes in the scene
        :param xmlnode:
          When loaded, the xmlnode it comes from
        :param collada:
          The collada instance this is part of

        """
        self.id = id
        """The unique string identifier for the scene"""
        self.nodes = nodes
        """A list of type :class:`collada.scene.Node` representing the nodes in the scene"""
        self.collada = collada
        """The collada instance this is part of"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the scene node."""
        else:
            self.xmlnode = E.visual_scene(id=self.id)
            for node in nodes:
                self.xmlnode.append( node.xmlnode )

    def objects(self, tipo):
        """Iterate through all objects in the scene that match `tipo`.
        The objects will be bound and transformed via the scene transformations.

        :param str tipo:
          A string for the desired object type. This can be one of 'geometry',
          'camera', 'light', or 'controller'.

        :rtype: generator that yields the type specified

        """
        matrix = None
        for node in self.nodes:
            for obj in node.objects(tipo, matrix): yield obj

    @staticmethod
    def load( collada, node ):
        id = node.get('id')
        nodes = []
        tried_loading = []
        succeeded = False
        localscope = {}
        for nodenode in node.findall(tag('node')):
            try:
                N = loadNode(collada, nodenode, localscope)
            except DaeInstanceNotLoadedError as ex:
                tried_loading.append((nodenode, ex))
            except DaeError as ex:
                collada.handleError(ex)
            else:
                if N is not None:
                    nodes.append( N )
                    if N.id and N.id not in localscope:
                        localscope[N.id] = N
                    succeeded = True
        while len(tried_loading) > 0 and succeeded:
            succeeded = False
            next_tried = []
            for nodenode, ex in tried_loading:
                try:
                    N = loadNode(collada, nodenode, localscope)
                except DaeInstanceNotLoadedError as ex:
                    next_tried.append((nodenode, ex))
                except DaeError as ex:
                    collada.handleError(ex)
                else:
                    if N is not None:
                        nodes.append( N )
                        succeeded = True
            tried_loading = next_tried
        if len(tried_loading) > 0:
            for nodenode, ex in tried_loading:
                raise DaeBrokenRefError(ex.msg)

        return Scene(id, nodes, xmlnode=node, collada=collada)

    def save(self):
        """Saves the scene back to :attr:`xmlnode`"""
        self.xmlnode.set('id', self.id)
        for node in self.nodes:
            node.save()
            if node.xmlnode not in self.xmlnode:
                self.xmlnode.append(node.xmlnode)
        xmlnodes = [n.xmlnode for n in self.nodes]
        for node in self.xmlnode:
            if node not in xmlnodes:
                self.xmlnode.remove(node)

    def __str__(self):
        return '<Scene id=%s nodes=%d>' % (self.id, len(self.nodes))

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = schema
#encoding:UTF-8
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""This module contains helper classes and functions for working
with the COLLADA 1.4.1 schema."""

import lxml
import lxml.etree
from collada.util import bytes, BytesIO

COLLADA_SCHEMA_1_4_1 = """<?xml version="1.0" encoding="utf-8"?>
<xs:schema xmlns="http://www.collada.org/2005/11/COLLADASchema" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" targetNamespace="http://www.collada.org/2005/11/COLLADASchema" elementFormDefault="qualified" version="1.4.1" xml:lang="EN" xsi:schemaLocation="http://www.w3.org/2001/XMLSchema http://www.w3.org/2001/XMLSchema.xsd">
    <!-- BEGIN COLLADA Format Schema -->
    <xs:annotation>
        <xs:documentation>
              COLLADA Schema
              Version 1.4.1 (June 23, 2006)

              Copyright (C) 2005, 2006 The Khronos Group Inc., Sony Computer Entertainment Inc.
             All Rights Reserved.

             Khronos is a trademark of The Khronos Group Inc.
             COLLADA is a trademark of Sony Computer Entertainment Inc. used by permission by Khronos.

             Note that this software document is distributed on an "AS IS" basis, with ALL EXPRESS AND
             IMPLIED WARRANTIES AND CONDITIONS DISCLAIMED, INCLUDING, WITHOUT LIMITATION, ANY IMPLIED
             WARRANTIES AND CONDITIONS OF MERCHANTABILITY, SATISFACTORY QUALITY, FITNESS FOR A PARTICULAR
             PURPOSE, AND NON-INFRINGEMENT.
        </xs:documentation>
    </xs:annotation>
    <!-- import needed for xml:base attribute-->
    <xs:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="http://www.w3.org/2001/03/xml.xsd"/>
    <!-- Root Element -->
    <xs:element name="COLLADA">
        <xs:annotation>
            <xs:appinfo>enable-xmlns</xs:appinfo>
            <xs:documentation>
            The COLLADA element declares the root of the document that comprises some of the content
            in the COLLADA schema.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset">
                    <xs:annotation>
                        <xs:documentation>
                        The COLLADA element must contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="library_animations">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_animations elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_animation_clips">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_animation_clips elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_cameras">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_cameras elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_controllers">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_controllerss elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_geometries">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_geometriess elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_effects">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_effects elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_force_fields">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_force_fields elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_images">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_images elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_lights">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_lights elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_materials">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_materials elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_nodes">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_nodes elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_physics_materials">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_materials elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_physics_models">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_physics_models elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_physics_scenes">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_physics_scenes elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="library_visual_scenes">
                        <xs:annotation>
                            <xs:documentation>
                            The COLLADA element may contain any number of library_visual_scenes elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element name="scene" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The scene embodies the entire set of information that can be visualized from the
                        contents of a COLLADA resource. The scene element declares the base of the scene
                        hierarchy or scene graph. The scene contains elements that comprise much of the
                        visual and transformational information content as created by the authoring tools.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="instance_physics_scene" type="InstanceWithExtra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The instance_physics_scene element declares the instantiation of a COLLADA physics_scene resource.
                                    The instance_physics_scene element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="instance_visual_scene" type="InstanceWithExtra" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The instance_visual_scene element declares the instantiation of a COLLADA visual_scene resource.
                                    The instance_visual_scene element may only appear once.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="version" type="VersionType" use="required">
                <xs:annotation>
                    <xs:documentation>
                        The version attribute is the COLLADA schema revision with which the instance document
                        conforms. Required Attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute ref="xml:base">
                <xs:annotation>
                    <xs:documentation>
                    The xml:base attribute allows you to define the base URI for this COLLADA document. See
                    http://www.w3.org/TR/xmlbase/ for more information.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Simple Types -->
    <!-- Primitive Types -->
    <xs:simpleType name="bool">
        <xs:restriction base="xs:boolean"/>
    </xs:simpleType>
    <xs:simpleType name="dateTime">
        <xs:restriction base="xs:dateTime"/>
    </xs:simpleType>
    <xs:simpleType name="float">
        <xs:restriction base="xs:double"/>
    </xs:simpleType>
    <xs:simpleType name="int">
        <xs:restriction base="xs:long"/>
    </xs:simpleType>
    <xs:simpleType name="Name">
        <xs:restriction base="xs:Name"/>
    </xs:simpleType>
    <xs:simpleType name="string">
        <xs:restriction base="xs:string"/>
    </xs:simpleType>
    <xs:simpleType name="token">
        <xs:restriction base="xs:token"/>
    </xs:simpleType>
    <xs:simpleType name="uint">
        <xs:restriction base="xs:unsignedLong"/>
    </xs:simpleType>
    <!-- Container Types -->
    <xs:simpleType name="ListOfBools">
        <xs:list itemType="bool"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfFloats">
        <xs:list itemType="float"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfHexBinary">
        <xs:list itemType="xs:hexBinary"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfInts">
        <xs:list itemType="int"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfNames">
        <xs:list itemType="Name"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfTokens">
        <xs:list itemType="token"/>
    </xs:simpleType>
    <xs:simpleType name="ListOfUInts">
        <xs:list itemType="uint"/>
    </xs:simpleType>
    <!-- Aggregate Types -->
    <xs:simpleType name="bool2">
        <xs:restriction base="ListOfBools">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="bool3">
        <xs:restriction base="ListOfBools">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="bool4">
        <xs:restriction base="ListOfBools">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float2">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float3">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float4">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float7">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="7"/>
            <xs:maxLength value="7"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float2x2">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float3x3">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float4x4">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float2x3">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float2x4">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float3x2">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float3x4">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float4x2">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="float4x3">
        <xs:restriction base="ListOfFloats">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int2">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int3">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int4">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int2x2">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int3x3">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="int4x4">
        <xs:restriction base="ListOfInts">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <!-- Basic Enumerations -->
    <xs:simpleType name="MorphMethodType">
        <xs:annotation>
            <xs:documentation>
            An enumuerated type specifying the acceptable morph methods.
            </xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="NORMALIZED"/>
            <xs:enumeration value="RELATIVE"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="NodeType">
        <xs:annotation>
            <xs:documentation>
            An enumerated type specifying the acceptable node types.
            </xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="JOINT"/>
            <xs:enumeration value="NODE"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="URIFragmentType">
        <xs:annotation>
            <xs:documentation>
            This type is used for URI reference which can only reference a resource declared within it's same document.
            </xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:pattern value="(#(.*))"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="UpAxisType">
        <xs:annotation>
            <xs:documentation>
            An enumerated type specifying the acceptable up-axis values.
            </xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="X_UP"/>
            <xs:enumeration value="Y_UP"/>
            <xs:enumeration value="Z_UP"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="VersionType">
        <xs:annotation>
            <xs:documentation>
            An enumerated type specifying the acceptable document versions.
            </xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="1.4.0"/>
            <xs:enumeration value="1.4.1"/>
        </xs:restriction>
    </xs:simpleType>
    <!-- Complex Types -->
    <xs:complexType name="InputGlobal">
        <xs:annotation>
            <xs:documentation>
            The InputGlobal type is used to represent inputs that can reference external resources.
            </xs:documentation>
        </xs:annotation>
        <xs:attribute name="semantic" type="xs:NMTOKEN" use="required">
            <xs:annotation>
                <xs:documentation>
                The semantic attribute is the user-defined meaning of the input connection. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="source" type="xs:anyURI" use="required">
            <xs:annotation>
                <xs:documentation>
                The source attribute indicates the location of the data source. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="InputLocal">
        <xs:annotation>
            <xs:documentation>
            The InputLocal type is used to represent inputs that can only reference resources declared in the same document.
            </xs:documentation>
        </xs:annotation>
        <xs:attribute name="semantic" type="xs:NMTOKEN" use="required">
            <xs:annotation>
                <xs:documentation>
                The semantic attribute is the user-defined meaning of the input connection. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="source" type="URIFragmentType" use="required">
            <xs:annotation>
                <xs:documentation>
                The source attribute indicates the location of the data source. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="InputLocalOffset">
        <xs:annotation>
            <xs:documentation>
            The InputLocalOffset type is used to represent indexed inputs that can only reference resources declared in the same document.
            </xs:documentation>
        </xs:annotation>
        <xs:attribute name="offset" type="uint" use="required">
            <xs:annotation>
                <xs:documentation>
                The offset attribute represents the offset into the list of indices.  If two input elements share
                the same offset, they will be indexed the same.  This works as a simple form of compression for the
                list of indices as well as defining the order the inputs should be used in.  Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="semantic" type="xs:NMTOKEN" use="required">
            <xs:annotation>
                <xs:documentation>
                The semantic attribute is the user-defined meaning of the input connection. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="source" type="URIFragmentType" use="required">
            <xs:annotation>
                <xs:documentation>
                The source attribute indicates the location of the data source. Required attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="set" type="uint">
            <xs:annotation>
                <xs:documentation>
                The set attribute indicates which inputs should be grouped together as a single set. This is helpful
                when multiple inputs share the same semantics.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The InstanceWithExtra type is used for all generic instance elements. A generic instance element
            is one which does not have any specific child elements declared.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>
                    The extra element may occur any number of times.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:sequence>
        <xs:attribute name="url" type="xs:anyURI" use="required">
            <xs:annotation>
                <xs:documentation>
                The url attribute refers to resource to instantiate. This may refer to a local resource using a
                relative URL fragment identifier that begins with the “#” character. The url attribute may refer
                to an external resource using an absolute or relative URL.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="sid" type="xs:NCName">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element. This
                value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="name" type="xs:NCName">
            <xs:annotation>
                <xs:documentation>
                The name attribute is the text string name of this element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="TargetableFloat">
        <xs:annotation>
            <xs:documentation>
            The TargetableFloat type is used to represent elements which contain a single float value which can
            be targeted for animation.
            </xs:documentation>
        </xs:annotation>
        <xs:simpleContent>
            <xs:extension base="float">
                <xs:attribute name="sid" type="xs:NCName">
                    <xs:annotation>
                        <xs:documentation>
                        The sid attribute is a text string value containing the sub-identifier of this element. This
                        value must be unique within the scope of the parent element. Optional attribute.
                        </xs:documentation>
                    </xs:annotation>
                </xs:attribute>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="TargetableFloat3">
        <xs:annotation>
            <xs:documentation>
            The TargetableFloat3 type is used to represent elements which contain a float3 value which can
            be targeted for animation.
            </xs:documentation>
        </xs:annotation>
        <xs:simpleContent>
            <xs:extension base="float3">
                <xs:attribute name="sid" type="xs:NCName">
                    <xs:annotation>
                        <xs:documentation>
                        The sid attribute is a text string value containing the sub-identifier of this element.
                        This value must be unique within the scope of the parent element. Optional attribute.
                        </xs:documentation>
                    </xs:annotation>
                </xs:attribute>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <!--Typed Array Elements-->
    <xs:element name="IDREF_array">
        <xs:annotation>
            <xs:documentation>
            The IDREF_array element declares the storage for a homogenous array of ID reference values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="xs:IDREFS">
                    <xs:attribute name="id" type="xs:ID">
                        <xs:annotation>
                            <xs:documentation>
                            The id attribute is a text string containing the unique identifier of this element. This value
                            must be unique within the instance document. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="count" type="uint" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The count attribute indicates the number of values in the array. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="Name_array">
        <xs:annotation>
            <xs:documentation>
            The Name_array element declares the storage for a homogenous array of Name string values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="ListOfNames">
                    <xs:attribute name="id" type="xs:ID">
                        <xs:annotation>
                            <xs:documentation>
                            The id attribute is a text string containing the unique identifier of this element.
                            This value must be unique within the instance document. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="count" type="uint" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The count attribute indicates the number of values in the array. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="bool_array">
        <xs:annotation>
            <xs:documentation>
            The bool_array element declares the storage for a homogenous array of boolean values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="ListOfBools">
                    <xs:attribute name="id" type="xs:ID">
                        <xs:annotation>
                            <xs:documentation>
                            The id attribute is a text string containing the unique identifier of this element.
                            This value must be unique within the instance document. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="count" type="uint" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The count attribute indicates the number of values in the array. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="float_array">
        <xs:annotation>
            <xs:documentation>
            The float_array element declares the storage for a homogenous array of floating point values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="ListOfFloats">
                    <xs:attribute name="id" type="xs:ID">
                        <xs:annotation>
                            <xs:documentation>
                            The id attribute is a text string containing the unique identifier of this element. This value
                            must be unique within the instance document. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="count" type="uint" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The count attribute indicates the number of values in the array. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="digits" type="xs:short" default="6">
                        <xs:annotation>
                            <xs:documentation>
                            The digits attribute indicates the number of significant decimal digits of the float values that
                            can be contained in the array. The default value is 6. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="magnitude" type="xs:short" default="38">
                        <xs:annotation>
                            <xs:documentation>
                            The magnitude attribute indicates the largest exponent of the float values that can be contained
                            in the array. The default value is 38. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="int_array">
        <xs:annotation>
            <xs:documentation>
            The int_array element declares the storage for a homogenous array of integer values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="ListOfInts">
                    <xs:attribute name="id" type="xs:ID">
                        <xs:annotation>
                            <xs:documentation>
                            The id attribute is a text string containing the unique identifier of this element.
                            This value must be unique within the instance document. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="count" type="uint" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The count attribute indicates the number of values in the array. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="minInclusive" type="xs:integer" default="-2147483648">
                        <xs:annotation>
                            <xs:documentation>
                            The minInclusive attribute indicates the smallest integer value that can be contained in
                            the array. The default value is –2147483648. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="maxInclusive" type="xs:integer" default="2147483647">
                        <xs:annotation>
                            <xs:documentation>
                            The maxInclusive attribute indicates the largest integer value that can be contained in
                            the array. The default value is 2147483647. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <!-- Dataflow Elements -->
    <xs:element name="accessor">
        <xs:annotation>
            <xs:documentation>
            The accessor element declares an access pattern to one of the array elements: float_array,
            int_array, Name_array, bool_array, and IDREF_array. The accessor element describes access
            to arrays that are organized in either an interleaved or non-interleaved manner, depending
            on the offset and stride attributes.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="param" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The accessor element may have any number of param elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of times the array is accessed. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="offset" type="uint" default="0">
                <xs:annotation>
                    <xs:documentation>
                    The offset attribute indicates the index of the first value to be read from the array.
                    The default value is 0. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="source" type="xs:anyURI">
                <xs:annotation>
                    <xs:documentation>
                    The source attribute indicates the location of the array to access using a URL expression. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="stride" type="uint" default="1">
                <xs:annotation>
                    <xs:documentation>
                    The stride attribute indicates number of values to be considered a unit during each access to
                    the array. The default value is 1, indicating that a single value is accessed. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="param">
        <xs:annotation>
            <xs:documentation>
            The param element declares parametric information regarding its parent element.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="xs:string">
                    <xs:attribute name="name" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The name attribute is the text string name of this element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="sid" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The sid attribute is a text string value containing the sub-identifier of this element.
                            This value must be unique within the scope of the parent element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="semantic" type="xs:NMTOKEN">
                        <xs:annotation>
                            <xs:documentation>
                            The semantic attribute is the user-defined meaning of the parameter. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                    <xs:attribute name="type" type="xs:NMTOKEN" use="required">
                        <xs:annotation>
                            <xs:documentation>
                            The type attribute indicates the type of the value data. This text string must be understood
                            by the application. Required attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="source">
        <xs:annotation>
            <xs:documentation>
            The source element declares a data repository that provides values according to the semantics of an
            input element that refers to it.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The source element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice minOccurs="0">
                    <xs:element ref="IDREF_array">
                        <xs:annotation>
                            <xs:documentation>
                            The source element may contain an IDREF_array.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="Name_array">
                        <xs:annotation>
                            <xs:documentation>
                            The source element may contain a Name_array.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="bool_array">
                        <xs:annotation>
                            <xs:documentation>
                            The source element may contain a bool_array.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="float_array">
                        <xs:annotation>
                            <xs:documentation>
                            The source element may contain a float_array.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="int_array">
                        <xs:annotation>
                            <xs:documentation>
                            The source element may contain an int_array.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element name="technique_common" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The technique common specifies the common method for accessing this source element's data.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="accessor">
                                <xs:annotation>
                                    <xs:documentation>
                                    The source's technique_common must have one and only one accessor.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Geometry Elements -->
    <xs:element name="geometry">
        <xs:annotation>
            <xs:documentation>
            Geometry describes the visual shape and appearance of an object in the scene.
            The geometry element categorizes the declaration of geometric information. Geometry is a
            branch of mathematics that deals with the measurement, properties, and relationships of
            points, lines, angles, surfaces, and solids.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The geometry element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice>
                    <xs:element ref="convex_mesh">
                        <xs:annotation>
                            <xs:documentation>
                            The geometry element may contain only one mesh or convex_mesh.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="mesh">
                        <xs:annotation>
                            <xs:documentation>
                            The geometry element may contain only one mesh or convex_mesh.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="spline"/>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="mesh">
        <xs:annotation>
            <xs:documentation>
            The mesh element contains vertex and primitive information sufficient to describe basic geometric meshes.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="source" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The mesh element must contain one or more source elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="vertices">
                    <xs:annotation>
                        <xs:documentation>
                        The mesh element must contain one vertices element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="lines">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of lines elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="linestrips">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of linestrips elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="polygons">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of polygons elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="polylist">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of polylist elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="triangles">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of triangles elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="trifans">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of trifans elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="tristrips">
                        <xs:annotation>
                            <xs:documentation>
                            The mesh element may contain any number of tristrips elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="spline">
        <xs:annotation>
            <xs:documentation>
            The spline element contains control vertex information sufficient to describe basic splines.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="source" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The mesh element must contain one or more source elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="control_vertices">
                    <xs:annotation>
                        <xs:documentation>The control vertices element  must occur  exactly one time. It is used to describe the CVs of the spline.</xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="input" type="InputLocal" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                        The input element must occur at least one time. These inputs are local inputs.
                        </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="closed" type="bool" default="false"/>
        </xs:complexType>
    </xs:element>
    <!-- Collation Elements -->
    <xs:element name="p" type="ListOfUInts">
        <xs:annotation>
            <xs:documentation>
            The p element represents primitive data for the primitive types (lines, linestrips, polygons,
            polylist, triangles, trifans, tristrips). The p element contains indices that reference into
            the parent's source elements referenced by the input elements.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="lines">
        <xs:annotation>
            <xs:documentation>
            The lines element provides the information needed to bind vertex attributes together and then
            organize those vertices into individual lines. Each line described by the mesh has two vertices.
            The first line is formed from first and second vertices. The second line is formed from the
            third and fourth vertices and so on.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the offset
                        and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The p element may occur once.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of line primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material at
                    the time of instantiation. If the material attribute is not specified then the lighting and
                    shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="linestrips">
        <xs:annotation>
            <xs:documentation>
            The linestrips element provides the information needed to bind vertex attributes together and
            then organize those vertices into connected line-strips. Each line-strip described by the mesh
            has an arbitrary number of vertices. Each line segment within the line-strip is formed from the
            current vertex and the preceding vertex.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the offset
                        and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The linestrips element may have any number of p elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of linestrip primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material
                    at the time of instantiation. If the material attribute is not specified then the lighting
                    and shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="polygons">
        <xs:annotation>
            <xs:documentation>
            The polygons element provides the information needed to bind vertex attributes together and
            then organize those vertices into individual polygons. The polygons described can contain
            arbitrary numbers of vertices. These polygons may be self intersecting and may also contain holes.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the
                        offset and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="p">
                        <xs:annotation>
                            <xs:documentation>
                            The p element may occur any number of times.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element name="ph">
                        <xs:annotation>
                            <xs:documentation>
                            The ph element descripes a polygon with holes.
                            </xs:documentation>
                        </xs:annotation>
                        <xs:complexType>
                            <xs:sequence>
                                <xs:element ref="p">
                                    <xs:annotation>
                                        <xs:documentation>
                                        Theere may only be one p element.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:element name="h" type="ListOfUInts" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The h element represents a hole in the polygon specified. There must be at least one h element.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of polygon primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material
                    at the time of instantiation. If the material attribute is not specified then the lighting
                    and shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="polylist">
        <xs:annotation>
            <xs:documentation>
            The polylist element provides the information needed to bind vertex attributes together and
            then organize those vertices into individual polygons. The polygons described in polylist can
            contain arbitrary numbers of vertices. Unlike the polygons element, the polylist element cannot
            contain polygons with holes.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the
                        offset and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="vcount" type="ListOfUInts" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The vcount element contains a list of integers describing the number of sides for each polygon
                        described by the polylist element. The vcount element may occur once.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The p element may occur once.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of polygon primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material at
                    the time of instantiation. If the material attribute is not specified then the lighting and
                    shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="triangles">
        <xs:annotation>
            <xs:documentation>
            The triangles element provides the information needed to bind vertex attributes together and
            then organize those vertices into individual triangles.    Each triangle described by the mesh has
            three vertices. The first triangle is formed from the first, second, and third vertices. The
            second triangle is formed from the fourth, fifth, and sixth vertices, and so on.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the
                        offset and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The triangles element may have any number of p elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of triangle primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material at
                    the time of instantiation. Optional attribute. If the material attribute is not specified then
                    the lighting and shading results are application defined.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="trifans">
        <xs:annotation>
            <xs:documentation>
            The trifans element provides the information needed to bind vertex attributes together and then
            organize those vertices into connected triangles. Each triangle described by the mesh has three
            vertices. The first triangle is formed from first, second, and third vertices. Each subsequent
            triangle is formed from the current vertex, reusing the first and the previous vertices.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the
                        offset and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The trifans element may have any number of p elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of triangle fan primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material
                    at the time of instantiation. If the material attribute is not specified then the lighting
                    and shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="tristrips">
        <xs:annotation>
            <xs:documentation>
            The tristrips element provides the information needed to bind vertex attributes together and then
            organize those vertices into connected triangles. Each triangle described by the mesh has three
            vertices. The first triangle is formed from first, second, and third vertices. Each subsequent
            triangle is formed from the current vertex, reusing the previous two vertices.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocalOffset" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element may occur any number of times. This input is a local input with the offset
                        and set attributes.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="p" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The tristrips element may have any number of p elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="count" type="uint" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The count attribute indicates the number of triangle strip primitives. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="material" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The material attribute declares a symbol for a material. This symbol is bound to a material
                    at the time of instantiation. If the material attribute is not specified then the lighting
                    and shading results are application defined. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="vertices">
        <xs:annotation>
            <xs:documentation>
            The vertices element declares the attributes and identity of mesh-vertices. The vertices element
            describes mesh-vertices in a mesh geometry. The mesh-vertices represent the position (identity)
            of the vertices comprising the mesh and other vertex attributes that are invariant to tessellation.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocal" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element must occur at least one time. These inputs are local inputs.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This
                    value must be unique within the instance document. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Transformational Elements -->
    <xs:element name="lookat">
        <xs:annotation>
            <xs:documentation>
            The lookat element contains a position and orientation transformation suitable for aiming a camera.
            The lookat element contains three mathematical vectors within it that describe:
            1.    The position of the object;
            2.    The position of the interest point;
            3.    The direction that points up.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="float3x3">
                    <xs:attribute name="sid" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The sid attribute is a text string value containing the sub-identifier of this element.
                            This value must be unique within the scope of the parent element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="matrix">
        <xs:annotation>
            <xs:documentation>
            Matrix transformations embody mathematical changes to points within a coordinate systems or the
            coordinate system itself. The matrix element contains a 4-by-4 matrix of floating-point values.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="float4x4">
                    <xs:attribute name="sid" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The sid attribute is a text string value containing the sub-identifier of this element.
                            This value must be unique within the scope of the parent element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="rotate">
        <xs:annotation>
            <xs:documentation>
            The rotate element contains an angle and a mathematical vector that represents the axis of rotation.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="float4">
                    <xs:attribute name="sid" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The sid attribute is a text string value containing the sub-identifier of this element.
                            This value must be unique within the scope of the parent element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="scale" type="TargetableFloat3">
        <xs:annotation>
            <xs:documentation>
            The scale element contains a mathematical vector that represents the relative proportions of the
            X, Y and Z axes of a coordinated system.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="skew">
        <xs:annotation>
            <xs:documentation>
            The skew element contains an angle and two mathematical vectors that represent the axis of
            rotation and the axis of translation.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:simpleContent>
                <xs:extension base="float7">
                    <xs:attribute name="sid" type="xs:NCName">
                        <xs:annotation>
                            <xs:documentation>
                            The sid attribute is a text string value containing the sub-identifier of this element.
                            This value must be unique within the scope of the parent element. Optional attribute.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:attribute>
                </xs:extension>
            </xs:simpleContent>
        </xs:complexType>
    </xs:element>
    <xs:element name="translate" type="TargetableFloat3">
        <xs:annotation>
            <xs:documentation>
            The translate element contains a mathematical vector that represents the distance along the
            X, Y and Z-axes.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <!-- Lighting and Shading Elements -->
    <xs:element name="image">
        <xs:annotation>
            <xs:documentation>
            The image element declares the storage for the graphical representation of an object.
            The image element best describes raster image data, but can conceivably handle other
            forms of imagery. The image elements allows for specifying an external image file with
            the init_from element or embed image data with the data element.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The image element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice>
                    <xs:element name="data" type="ListOfHexBinary">
                        <xs:annotation>
                            <xs:documentation>
                            The data child element contains a sequence of hexadecimal encoded  binary octets representing
                            the embedded image data.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element name="init_from" type="xs:anyURI">
                        <xs:annotation>
                            <xs:documentation>
                            The init_from element allows you to specify an external image file to use for the image element.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="format" type="xs:token">
                <xs:annotation>
                    <xs:documentation>
                    The format attribute is a text string value that indicates the image format. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="height" type="uint">
                <xs:annotation>
                    <xs:documentation>
                    The height attribute is an integer value that indicates the height of the image in pixel
                    units. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="width" type="uint">
                <xs:annotation>
                    <xs:documentation>
                    The width attribute is an integer value that indicates the width of the image in pixel units.
                    Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="depth" type="uint" default="1">
                <xs:annotation>
                    <xs:documentation>
                    The depth attribute is an integer value that indicates the depth of the image in pixel units.
                    A 2-D image has a depth of 1, which is also the default value. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="light">
        <xs:annotation>
            <xs:documentation>
            The light element declares a light source that illuminates the scene.
            Light sources have many different properties and radiate light in many different patterns and
            frequencies.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The light element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the light information for the common profile which all
                        COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:choice>
                            <xs:element name="ambient">
                                <xs:annotation>
                                    <xs:documentation>
                                    The ambient element declares the parameters required to describe an ambient light source.
                                    An ambient light is one that lights everything evenly, regardless of location or orientation.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="color" type="TargetableFloat3">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The color element contains three floating point numbers specifying the color of the light.
                                                The color element must occur exactly once.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="directional">
                                <xs:annotation>
                                    <xs:documentation>
                                    The directional element declares the parameters required to describe a directional light source.
                                    A directional light is one that lights everything from the same direction, regardless of location.
                                    The light’s default direction vector in local coordinates is [0,0,-1], pointing down the -Z axis.
                                    The actual direction of the light is defined by the transform of the node where the light is
                                    instantiated.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="color" type="TargetableFloat3">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The color element contains three floating point numbers specifying the color of the light.
                                                The color element must occur exactly once.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="point">
                                <xs:annotation>
                                    <xs:documentation>
                                    The point element declares the parameters required to describe a point light source.  A point light
                                    source radiates light in all directions from a known location in space. The intensity of a point
                                    light source is attenuated as the distance to the light source increases. The position of the light
                                    is defined by the transform of the node in which it is instantiated.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="color" type="TargetableFloat3">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The color element contains three floating point numbers specifying the color of the light.
                                                The color element must occur exactly once.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="constant_attenuation" type="TargetableFloat" default="1.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The constant_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="linear_attenuation" type="TargetableFloat" default="0.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The linear_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="quadratic_attenuation" type="TargetableFloat" default="0.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The quadratic_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="spot">
                                <xs:annotation>
                                    <xs:documentation>
                                    The spot element declares the parameters required to describe a spot light source.  A spot light
                                    source radiates light in one direction from a known location in space. The light radiates from
                                    the spot light source in a cone shape. The intensity of the light is attenuated as the radiation
                                    angle increases away from the direction of the light source. The intensity of a spot light source
                                    is also attenuated as the distance to the light source increases. The position of the light is
                                    defined by the transform of the node in which it is instantiated. The light’s default direction
                                    vector in local coordinates is [0,0,-1], pointing down the -Z axis. The actual direction of the
                                    light is defined by the transform of the node where the light is instantiated.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="color" type="TargetableFloat3">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The color element contains three floating point numbers specifying the color of the light.
                                                The color element must occur exactly once.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="constant_attenuation" type="TargetableFloat" default="1.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The constant_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="linear_attenuation" type="TargetableFloat" default="0.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The linear_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="quadratic_attenuation" type="TargetableFloat" default="0.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The quadratic_attenuation is used to calculate the total attenuation of this light given a distance.
                                                The equation used is A = constant_attenuation + Dist*linear_attenuation + Dist^2*quadratic_attenuation.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="falloff_angle" type="TargetableFloat" default="180.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The falloff_angle is used to specify the amount of attenuation based on the direction of the light.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="falloff_exponent" type="TargetableFloat" default="0.0" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The falloff_exponent is used to specify the amount of attenuation based on the direction of the light.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                        </xs:choice>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="material">
        <xs:annotation>
            <xs:documentation>
            Materials describe the visual appearance of a geometric object.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The material element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_effect">
                    <xs:annotation>
                        <xs:documentation>
                        The material must instance an effect.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Object Elements -->
    <xs:element name="camera">
        <xs:annotation>
            <xs:documentation>
            The camera element declares a view into the scene hierarchy or scene graph. The camera contains
            elements that describe the camera’s optics and imager.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The camera element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="optics">
                    <xs:annotation>
                        <xs:documentation>
                        Optics represents the apparatus on a camera that projects the image onto the image sensor.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="technique_common">
                                <xs:annotation>
                                    <xs:documentation>
                                    The technique_common element specifies the optics information for the common profile
                                    which all COLLADA implementations need to support.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:choice>
                                        <xs:element name="orthographic">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The orthographic element describes the field of view of an orthographic camera.
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:choice>
                                                        <xs:sequence>
                                                            <xs:element name="xmag" type="TargetableFloat">
                                                                <xs:annotation>
                                                                    <xs:documentation>
                                                                    The xmag element contains a floating point number describing the horizontal
                                                                    magnification of the view.
                                                                    </xs:documentation>
                                                                </xs:annotation>
                                                            </xs:element>
                                                            <xs:choice minOccurs="0">
                                                                <xs:element name="ymag" type="TargetableFloat">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The ymag element contains a floating point number describing the vertical
                                                                        magnification of the view.  It can also have a sid.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:element>
                                                                <xs:element name="aspect_ratio" type="TargetableFloat">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The aspect_ratio element contains a floating point number describing the aspect ratio of
                                                                        the field of view. If the aspect_ratio element is not present the aspect ratio is to be
                                                                        calculated from the xmag or ymag elements and the current viewport.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:element>
                                                            </xs:choice>
                                                        </xs:sequence>
                                                        <xs:sequence>
                                                            <xs:element name="ymag" type="TargetableFloat"/>
                                                            <xs:element name="aspect_ratio" type="TargetableFloat" minOccurs="0"/>
                                                        </xs:sequence>
                                                    </xs:choice>
                                                    <xs:element name="znear" type="TargetableFloat">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The znear element contains a floating point number that describes the distance to the near
                                                            clipping plane. The znear element must occur exactly once.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="zfar" type="TargetableFloat">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The zfar element contains a floating point number that describes the distance to the far
                                                            clipping plane. The zfar element must occur exactly once.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                        <xs:element name="perspective">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The perspective element describes the optics of a perspective camera.
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:choice>
                                                        <xs:sequence>
                                                            <xs:element name="xfov" type="TargetableFloat">
                                                                <xs:annotation>
                                                                    <xs:documentation>
                                                                    The xfov element contains a floating point number describing the horizontal field of view in degrees.
                                                                    </xs:documentation>
                                                                </xs:annotation>
                                                            </xs:element>
                                                            <xs:choice minOccurs="0">
                                                                <xs:element name="yfov" type="TargetableFloat">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The yfov element contains a floating point number describing the verticle field of view in degrees.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:element>
                                                                <xs:element name="aspect_ratio" type="TargetableFloat">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The aspect_ratio element contains a floating point number describing the aspect ratio of the field
                                                                        of view. If the aspect_ratio element is not present the aspect ratio is to be calculated from the
                                                                        xfov or yfov elements and the current viewport.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:element>
                                                            </xs:choice>
                                                        </xs:sequence>
                                                        <xs:sequence>
                                                            <xs:element name="yfov" type="TargetableFloat"/>
                                                            <xs:element name="aspect_ratio" type="TargetableFloat" minOccurs="0"/>
                                                        </xs:sequence>
                                                    </xs:choice>
                                                    <xs:element name="znear" type="TargetableFloat">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The znear element contains a floating point number that describes the distance to the near
                                                            clipping plane. The znear element must occur exactly once.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="zfar" type="TargetableFloat">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The zfar element contains a floating point number that describes the distance to the far
                                                            clipping plane. The zfar element must occur exactly once.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                    </xs:choice>
                                </xs:complexType>
                            </xs:element>
                            <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    This element may contain any number of non-common profile techniques.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element name="imager" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        Imagers represent the image sensor of a camera (for example film or CCD).
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="technique" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    This element may contain any number of non-common profile techniques.
                                    There is no common technique for imager.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Animation Elements -->
    <xs:element name="animation">
        <xs:annotation>
            <xs:documentation>
            The animation element categorizes the declaration of animation information. The animation
            hierarchy contains elements that describe the animation’s key-frame data and sampler functions,
            ordered in such a way to group together animations that should be executed together.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The animation element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice>
                    <xs:sequence>
                        <xs:element ref="source" maxOccurs="unbounded">
                            <xs:annotation>
                                <xs:documentation>
                                The animation element may contain any number of source elements.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:element>
                        <xs:choice>
                            <xs:sequence>
                                <xs:element ref="sampler" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The animation element may contain any number of sampler elements.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:element ref="channel" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The animation element may contain any number of channel elements.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:element ref="animation" minOccurs="0" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The animation may be hierarchical and may contain any number of other animation elements.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                            </xs:sequence>
                            <xs:element ref="animation" maxOccurs="unbounded"/>
                        </xs:choice>
                    </xs:sequence>
                    <xs:sequence>
                        <xs:element ref="sampler" maxOccurs="unbounded"/>
                        <xs:element ref="channel" maxOccurs="unbounded"/>
                        <xs:element ref="animation" minOccurs="0" maxOccurs="unbounded"/>
                    </xs:sequence>
                    <xs:element ref="animation" maxOccurs="unbounded"/>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="animation_clip">
        <xs:annotation>
            <xs:documentation>
            The animation_clip element defines a section of the animation curves to be used together as
            an animation clip.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The animation_clip element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="instance_animation" type="InstanceWithExtra" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The animation_clip must instance at least one animation element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="start" type="xs:double" default="0.0">
                <xs:annotation>
                    <xs:documentation>
                    The start attribute is the time in seconds of the beginning of the clip.  This time is
                    the same as that used in the key-frame data and is used to determine which set of
                    key-frames will be included in the clip.  The start time does not specify when the clip
                    will be played.  If the time falls between two keyframes of a referenced animation, an
                    interpolated value should be used.  The default value is 0.0.  Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="end" type="xs:double">
                <xs:annotation>
                    <xs:documentation>
                    The end attribute is the time in seconds of the end of the clip.  This is used in the
                    same way as the start time.  If end is not specified, the value is taken to be the end
                    time of the longest animation.  Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="channel">
        <xs:annotation>
            <xs:documentation>
            The channel element declares an output channel of an animation.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:attribute name="source" type="URIFragmentType" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The source attribute indicates the location of the sampler using a URL expression.
                    The sampler must be declared within the same document. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="target" type="xs:token" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The target attribute indicates the location of the element bound to the output of the sampler.
                    This text string is a path-name following a simple syntax described in Address Syntax.
                    Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="sampler">
        <xs:annotation>
            <xs:documentation>
            The sampler element declares an N-dimensional function used for animation. Animation function curves
            are represented by 1-D sampler elements in COLLADA. The sampler defines sampling points and how to
            interpolate between them.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="input" type="InputLocal" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The input element must occur at least one time. These inputs are local inputs.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Controller Elements -->
    <xs:element name="controller">
        <xs:annotation>
            <xs:documentation>
            The controller element categorizes the declaration of generic control information.
            A controller is a device or mechanism that manages and directs the operations of another object.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The controller element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice>
                    <xs:element ref="skin">
                        <xs:annotation>
                            <xs:documentation>
                            The controller element may contain either a skin element or a morph element.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="morph">
                        <xs:annotation>
                            <xs:documentation>
                            The controller element may contain either a skin element or a morph element.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="skin">
        <xs:annotation>
            <xs:documentation>
            The skin element contains vertex and primitive information sufficient to describe blend-weight skinning.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="bind_shape_matrix" type="float4x4" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        This provides extra information about the position and orientation of the base mesh before binding.
                        If bind_shape_matrix is not specified then an identity matrix may be used as the bind_shape_matrix.
                        The bind_shape_matrix element may occur zero or one times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="source" minOccurs="3" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The skin element must contain at least three source elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="joints">
                    <xs:annotation>
                        <xs:documentation>
                        The joints element associates joint, or skeleton, nodes with attribute data.
                        In COLLADA, this is specified by the inverse bind matrix of each joint (influence) in the skeleton.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="input" type="InputLocal" minOccurs="2" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The input element must occur at least twice. These inputs are local inputs.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element name="vertex_weights">
                    <xs:annotation>
                        <xs:documentation>
                        The vertex_weights element associates a set of joint-weight pairs with each vertex in the base mesh.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="input" type="InputLocalOffset" minOccurs="2" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The input element must occur at least twice.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="vcount" type="ListOfUInts" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The vcount element contains a list of integers describing the number of influences for each vertex.
                                    The vcount element may occur once.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="v" type="ListOfInts" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The v element describes which bones and attributes are associated with each vertex.  An index
                                    of –1 into the array of joints refers to the bind shape.  Weights should be normalized before use.
                                    The v element must occur zero or one times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                        <xs:attribute name="count" type="uint" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The count attribute describes the number of vertices in the base mesh. Required element.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="source" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The source attribute contains a URI reference to the base mesh, (a static mesh or a morphed mesh).
                    This also provides the bind-shape of the skinned mesh.  Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="morph">
        <xs:annotation>
            <xs:documentation>
            The morph element describes the data required to blend between sets of static meshes. Each
            possible mesh that can be blended (a morph target) must be specified.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="source" minOccurs="2" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The morph element must contain at least two source elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="targets">
                    <xs:annotation>
                        <xs:documentation>
                        The targets element declares the morph targets, their weights and any user defined attributes
                        associated with them.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="input" type="InputLocal" minOccurs="2" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The input element must occur at least twice. These inputs are local inputs.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="method" type="MorphMethodType" default="NORMALIZED">
                <xs:annotation>
                    <xs:documentation>
                    The method attribute specifies the which blending technique to use. The accepted values are
                    NORMALIZED, and RELATIVE. The default value if not specified is NORMALIZED.  Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="source" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The source attribute indicates the base mesh. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Meta Elements -->
    <xs:element name="asset">
        <xs:annotation>
            <xs:documentation>
            The asset element defines asset management information regarding its parent element.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="contributor" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The contributor element defines authoring information for asset management
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="author" type="xs:string" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The author element contains a string with the author's name.
                                    There may be only one author element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="authoring_tool" type="xs:string" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The authoring_tool element contains a string with the authoring tool's name.
                                    There may be only one authoring_tool element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="comments" type="xs:string" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The comments element contains a string with comments from this contributor.
                                    There may be only one comments element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="copyright" type="xs:string" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The copyright element contains a string with copyright information.
                                    There may be only one copyright element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="source_data" type="xs:anyURI" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The source_data element contains a URI reference to the source data used for this asset.
                                    There may be only one source_data element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element name="created" type="xs:dateTime">
                    <xs:annotation>
                        <xs:documentation>
                        The created element contains the date and time that the parent element was created and is
                        represented in an ISO 8601 format.  The created element may appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="keywords" type="xs:string" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The keywords element contains a list of words used as search criteria for the parent element.
                        The keywords element may appear zero or more times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="modified" type="xs:dateTime">
                    <xs:annotation>
                        <xs:documentation>
                        The modified element contains the date and time that the parent element was last modified and
                        represented in an ISO 8601 format. The modified element may appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="revision" type="xs:string" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The revision element contains the revision information for the parent element. The revision
                        element may appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="subject" type="xs:string" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The subject element contains a description of the topical subject of the parent element. The
                        subject element may appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="title" type="xs:string" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The title element contains the title information for the parent element. The title element may
                        appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="unit" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The unit element contains descriptive information about unit of measure. It has attributes for
                        the name of the unit and the measurement with respect to the meter. The unit element may appear
                        zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:attribute name="meter" type="float" default="1.0">
                            <xs:annotation>
                                <xs:documentation>
                                The meter attribute specifies the measurement with respect to the meter. The default
                                value for the meter attribute is “1.0”.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="name" type="xs:NMTOKEN" default="meter">
                            <xs:annotation>
                                <xs:documentation>
                                The name attribute specifies the name of the unit. The default value for the name
                                attribute is “meter”.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element name="up_axis" type="UpAxisType" default="Y_UP" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The up_axis element contains descriptive information about coordinate system of the geometric
                        data. All coordinates are right-handed by definition. This element specifies which axis is
                        considered up. The default is the Y-axis. The up_axis element may appear zero or one time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="extra">
        <xs:annotation>
            <xs:documentation>
            The extra element declares additional information regarding its parent element.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="technique" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element must contain at least one non-common profile technique.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="type" type="xs:NMTOKEN">
                <xs:annotation>
                    <xs:documentation>
                    The type attribute indicates the type of the value data. This text string must be understood by
                    the application. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="technique">
        <xs:annotation>
            <xs:appinfo>enable-xmlns</xs:appinfo>
            <xs:documentation>
            The technique element declares the information used to process some portion of the content. Each
            technique conforms to an associated profile. Techniques generally act as a “switch”. If more than
            one is present for a particular portion of content, on import, one or the other is picked, but
            usually not both. Selection should be based on which profile the importing application can support.
            Techniques contain application data and programs, making them assets that can be managed as a unit.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:any namespace="##any" processContents="lax" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="profile" type="xs:NMTOKEN" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The profile attribute indicates the type of profile. This is a vendor defined character
                    string that indicates the platform or capability target for the technique. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Hierarchical Elements -->
    <xs:element name="node">
        <xs:annotation>
            <xs:documentation>
            Nodes embody the hierarchical relationship of elements in the scene.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="lookat">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of lookat elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="matrix">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of matrix elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="rotate">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of rotate elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="scale">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of scale elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="skew">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of skew elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                    <xs:element ref="translate">
                        <xs:annotation>
                            <xs:documentation>
                            The node element may contain any number of translate elements.
                            </xs:documentation>
                        </xs:annotation>
                    </xs:element>
                </xs:choice>
                <xs:element ref="instance_camera" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may instance any number of camera objects.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_controller" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may instance any number of controller objects.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_geometry" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may instance any number of geometry objects.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_light" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may instance any number of light objects.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_node" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may instance any number of node elements or hierarchies objects.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="node" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The node element may be hierarchical and be the parent of any number of other node elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element.
                    This value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="type" type="NodeType" default="NODE">
                <xs:annotation>
                    <xs:documentation>
                    The type attribute indicates the type of the node element. The default value is “NODE”.
                    Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="layer" type="ListOfNames">
                <xs:annotation>
                    <xs:documentation>
                    The layer attribute indicates the names of the layers to which this node belongs.  For example,
                    a value of “foreground glowing” indicates that this node belongs to both the ‘foreground’ layer
                    and the ‘glowing’ layer.  The default value is empty, indicating that the node doesn’t belong to
                    any layer.  Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="visual_scene">
        <xs:annotation>
            <xs:documentation>
            The visual_scene element declares the base of the visual_scene hierarchy or scene graph. The
            scene contains elements that comprise much of the visual and transformational information
            content as created by the authoring tools.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The visual_scene element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="node" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The visual_scene element must have at least one node element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="evaluate_scene" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The evaluate_scene element declares information specifying a specific way to evaluate this
                        visual_scene. There may be any number of evaluate_scene elements.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="render" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The render element describes one effect pass to evaluate the scene.
                                    There must be at least one render element.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="layer" type="xs:NCName" minOccurs="0" maxOccurs="unbounded">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The layer element specifies which layer to render in this compositing step
                                                while evaluating the scene. You may specify any number of layers.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element ref="instance_effect" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The instance_effect element specifies which effect to render in this compositing step
                                                while evaluating the scene.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                    <xs:attribute name="camera_node" type="xs:anyURI" use="required">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The camera_node attribute refers to a node that contains a camera describing the viewpoint to
                                            render this compositing step from.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:attribute>
                                </xs:complexType>
                            </xs:element>
                        </xs:sequence>
                        <xs:attribute name="name" type="xs:NCName">
                            <xs:annotation>
                                <xs:documentation>
                                The name attribute is the text string name of this element. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="optional">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This
                    value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Instance Elements -->
    <xs:element name="bind_material">
        <xs:annotation>
            <xs:documentation>
            Bind a specific material to a piece of geometry, binding varying and uniform parameters at the
            same time.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="param" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The bind_material element may contain any number of param elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the bind_material information for the common
                        profile which all COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="instance_material" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The instance_material element specifies the information needed to bind a geometry
                                    to a material. This element must appear at least once.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_camera" type="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The instance_camera element declares the instantiation of a COLLADA camera resource.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="instance_controller">
        <xs:annotation>
            <xs:documentation>
            The instance_controller element declares the instantiation of a COLLADA controller resource.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="skeleton" type="xs:anyURI" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The skeleton element is used to indicate where a skin controller is to start to search for
                        the joint nodes it needs.  This element is meaningless for morph controllers.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="bind_material" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        Bind a specific material to a piece of geometry, binding varying and uniform parameters at the
                        same time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="url" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The url attribute refers to resource. This may refer to a local resource using a relative
                    URL fragment identifier that begins with the “#” character. The url attribute may refer to an
                    external resource using an absolute or relative URL.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_effect">
        <xs:annotation>
            <xs:documentation>
            The instance_effect element declares the instantiation of a COLLADA effect resource.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="technique_hint" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        Add a hint for a platform of which technique to use in this effect.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:attribute name="platform" type="xs:NCName" use="optional">
                            <xs:annotation>
                                <xs:documentation>
                                A platform defines a string that specifies which platform this is hint is aimed for.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="profile" type="xs:NCName" use="optional">
                            <xs:annotation>
                                <xs:documentation>
                                A profile defines a string that specifies which API profile this is hint is aimed for.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="ref" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                A reference to the technique to use for the specified platform.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element name="setparam" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        Assigns a new value to a previously defined parameter
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:group ref="fx_basic_type_common"/>
                        </xs:sequence>
                        <xs:attribute name="ref" type="xs:token" use="required"/>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="url" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The url attribute refers to resource.  This may refer to a local resource using a relative URL
                    fragment identifier that begins with the “#” character. The url attribute may refer to an external
                    resource using an absolute or relative URL.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_force_field" type="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The instance_force_field element declares the instantiation of a COLLADA force_field resource.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="instance_geometry">
        <xs:annotation>
            <xs:documentation>
            The instance_geometry element declares the instantiation of a COLLADA geometry resource.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="bind_material" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        Bind a specific material to a piece of geometry, binding varying and uniform parameters at the
                        same time.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="url" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The url attribute refers to resource.  This may refer to a local resource using a relative URL
                    fragment identifier that begins with the “#” character. The url attribute may refer to an external
                    resource using an absolute or relative URL.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_light" type="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The instance_light element declares the instantiation of a COLLADA light resource.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="instance_material">
        <xs:annotation>
            <xs:documentation>
            The instance_material element declares the instantiation of a COLLADA material resource.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="bind" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The bind element binds values to effect parameters upon instantiation.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:attribute name="semantic" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The semantic attribute specifies which effect parameter to bind.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="target" type="xs:token" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The target attribute specifies the location of the value to bind to the specified semantic.
                                This text string is a path-name following a simple syntax described in the “Addressing Syntax”
                                section.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element name="bind_vertex_input" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The bind_vertex_input element binds vertex inputs to effect parameters upon instantiation.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:attribute name="semantic" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The semantic attribute specifies which effect parameter to bind.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="input_semantic" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The input_semantic attribute specifies which input semantic to bind.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="input_set" type="uint">
                            <xs:annotation>
                                <xs:documentation>
                                The input_set attribute specifies which input set to bind.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="symbol" type="xs:NCName" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The symbol attribute specifies which symbol defined from within the geometry this material binds to.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="target" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The target attribute specifies the URL of the location of the object to instantiate.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_node" type="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The instance_node element declares the instantiation of a COLLADA node resource.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="instance_physics_material" type="InstanceWithExtra">
        <xs:annotation>
            <xs:documentation>
            The instance_physics_material element declares the instantiation of a COLLADA physics_material
            resource.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="instance_physics_model">
        <xs:annotation>
            <xs:documentation>
            This element allows instancing physics model within another physics model, or in a physics scene.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="instance_force_field" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The instance_physics_model element may instance any number of force_field elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_rigid_body" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The instance_physics_model element may instance any number of rigid_body elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_rigid_constraint" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The instance_physics_model element may instance any number of rigid_constraint elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="url" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The url attribute refers to resource.  This may refer to a local resource using a relative URL
                    fragment identifier that begins with the “#” character. The url attribute may refer to an external
                    resource using an absolute or relative URL.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="parent" type="xs:anyURI">
                <xs:annotation>
                    <xs:documentation>
                    The parent attribute points to the id of a node in the visual scene. This allows a physics model
                    to be instantiated under a specific transform node, which will dictate the initial position and
                    orientation, and could be animated to influence kinematic rigid bodies.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_rigid_body">
        <xs:annotation>
            <xs:documentation>
            This element allows instancing a rigid_body within an instance_physics_model.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the instance_rigid_body information for the common
                        profile which all COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="angular_velocity" type="float3" default="0.0 0.0 0.0" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Specifies the initial angular velocity of the rigid_body instance in degrees per second
                                    around each axis, in the form of an X-Y-Z Euler rotation.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="velocity" type="float3" default="0.0 0.0 0.0" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Specifies the initial linear velocity of the rigid_body instance.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="dynamic" minOccurs="0">
                                <xs:complexType>
                                    <xs:simpleContent>
                                        <xs:extension base="bool">
                                            <xs:attribute name="sid" type="xs:NCName">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    The sid attribute is a text string value containing the sub-identifier of this element.
                                                    This value must be unique within the scope of the parent element. Optional attribute.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:attribute>
                                        </xs:extension>
                                    </xs:simpleContent>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="mass" type="TargetableFloat" minOccurs="0"/>
                            <xs:element name="mass_frame" minOccurs="0">
                                <xs:complexType>
                                    <xs:choice maxOccurs="unbounded">
                                        <xs:element ref="translate"/>
                                        <xs:element ref="rotate"/>
                                    </xs:choice>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="inertia" type="TargetableFloat3" minOccurs="0"/>
                            <xs:choice minOccurs="0">
                                <xs:element ref="instance_physics_material"/>
                                <xs:element ref="physics_material"/>
                            </xs:choice>
                            <xs:element name="shape" minOccurs="0" maxOccurs="unbounded">
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="hollow" minOccurs="0">
                                            <xs:complexType>
                                                <xs:simpleContent>
                                                    <xs:extension base="bool">
                                                        <xs:attribute name="sid" type="xs:NCName">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                The sid attribute is a text string value containing the sub-identifier of this element. This value must be unique within the scope of the parent element. Optional attribute.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                        </xs:attribute>
                                                    </xs:extension>
                                                </xs:simpleContent>
                                            </xs:complexType>
                                        </xs:element>
                                        <xs:element name="mass" type="TargetableFloat" minOccurs="0"/>
                                        <xs:element name="density" type="TargetableFloat" minOccurs="0"/>
                                        <xs:choice minOccurs="0">
                                            <xs:element ref="instance_physics_material"/>
                                            <xs:element ref="physics_material"/>
                                        </xs:choice>
                                        <xs:choice>
                                            <xs:element ref="instance_geometry"/>
                                            <xs:element ref="plane"/>
                                            <xs:element ref="box"/>
                                            <xs:element ref="sphere"/>
                                            <xs:element ref="cylinder"/>
                                            <xs:element ref="tapered_cylinder"/>
                                            <xs:element ref="capsule"/>
                                            <xs:element ref="tapered_capsule"/>
                                        </xs:choice>
                                        <xs:choice minOccurs="0" maxOccurs="unbounded">
                                            <xs:element ref="translate"/>
                                            <xs:element ref="rotate"/>
                                        </xs:choice>
                                        <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The extra element may appear any number of times.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="body" type="xs:NCName" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The body attribute indicates which rigid_body to instantiate. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="target" type="xs:anyURI" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The target attribute indicates which node is influenced by this rigid_body instance.
                    Required attribute
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="instance_rigid_constraint">
        <xs:annotation>
            <xs:documentation>
            This element allows instancing a rigid_constraint within an instance_physics_model.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="constraint" type="xs:NCName" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The constraint attribute indicates which rigid_constraing to instantiate. Required attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="sid" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- Modularity elements -->
    <xs:element name="library_animations">
        <xs:annotation>
            <xs:documentation>
            The library_animations element declares a module of animation elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_animations element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="animation" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one animation element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_animation_clips">
        <xs:annotation>
            <xs:documentation>
            The library_animation_clips element declares a module of animation_clip elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_animation_clips element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="animation_clip" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one animation_clip element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_cameras">
        <xs:annotation>
            <xs:documentation>
            The library_cameras element declares a module of camera elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_cameras element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="camera" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one camera element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_controllers">
        <xs:annotation>
            <xs:documentation>
            The library_controllers element declares a module of controller elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_controllers element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="controller" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one controller element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_geometries">
        <xs:annotation>
            <xs:documentation>
            The library_geometries element declares a module of geometry elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_geometries element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="geometry" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one geometry element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_effects">
        <xs:annotation>
            <xs:documentation>
            The library_effects element declares a module of effect elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_effects element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="effect" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one effect element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_force_fields">
        <xs:annotation>
            <xs:documentation>
            The library_force_fields element declares a module of force_field elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_force_fields element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="force_field" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one force_field element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_images">
        <xs:annotation>
            <xs:documentation>
            The library_images element declares a module of image elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_images element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="image" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one image element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_lights">
        <xs:annotation>
            <xs:documentation>
            The library_lights element declares a module of light elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_lights element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="light" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one light element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_materials">
        <xs:annotation>
            <xs:documentation>
            The library_materials element declares a module of material elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_materials element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="material" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one material element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_nodes">
        <xs:annotation>
            <xs:documentation>
            The library_nodes element declares a module of node elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_nodes element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="node" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one node element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_physics_materials">
        <xs:annotation>
            <xs:documentation>
            The library_physics_materials element declares a module of physics_material elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_physics_materials element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="physics_material" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one physics_material element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_physics_models">
        <xs:annotation>
            <xs:documentation>
            The library_physics_models element declares a module of physics_model elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_physics_models element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="physics_model" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one physics_model element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_physics_scenes">
        <xs:annotation>
            <xs:documentation>
            The library_physics_scenes element declares a module of physics_scene elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_physics_scenes element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="physics_scene" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one physics_scene element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="library_visual_scenes">
        <xs:annotation>
            <xs:documentation>
            The library_visual_scenes element declares a module of visual_scene elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The library_visual_scenes element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="visual_scene" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There must be at least one visual_scene element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- -->
    <!-- COLLADA FX types in common scope     -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- -->
    <xs:simpleType name="fx_color_common">
        <xs:restriction base="float4"/>
    </xs:simpleType>
    <xs:simpleType name="fx_opaque_enum">
        <xs:restriction base="xs:string">
            <xs:enumeration value="A_ONE">
                <xs:annotation>
                    <xs:documentation>
                        When a transparent opaque attribute is set to A_ONE, it means the transparency information will be taken from the alpha channel of the color, texture, or parameter supplying the value. The value of 1.0 is opaque in this mode.
                    </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="RGB_ZERO">
                <xs:annotation>
                    <xs:documentation>
                        When a transparent opaque attribute is set to RGB_ZERO, it means the transparency information will be taken from the red, green, and blue channels of the color, texture, or parameter supplying the value. Each channel is modulated independently. The value of 0.0 is opaque in this mode.
                    </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_type_enum">
        <xs:restriction base="xs:string">
            <xs:enumeration value="UNTYPED">
                <xs:annotation>
                    <xs:documentation>
                        When a surface's type attribute is set to UNTYPED, its type is initially unknown and established later by the context in which it is used, such as by a texture sampler that references it. A surface of any other type may be changed into an UNTYPED surface at run-time, as if it were created by &lt;newparam&gt;, using &lt;setparam&gt;. If there is a type mismatch between a &lt;setparam&gt; operation and what the run-time decides the type should be, the result is profile- and platform-specific behavior.
                    </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="1D"/>
            <xs:enumeration value="2D"/>
            <xs:enumeration value="3D"/>
            <xs:enumeration value="RECT"/>
            <xs:enumeration value="CUBE"/>
            <xs:enumeration value="DEPTH"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_face_enum">
        <xs:restriction base="xs:string">
            <xs:enumeration value="POSITIVE_X"/>
            <xs:enumeration value="NEGATIVE_X"/>
            <xs:enumeration value="POSITIVE_Y"/>
            <xs:enumeration value="NEGATIVE_Y"/>
            <xs:enumeration value="POSITIVE_Z"/>
            <xs:enumeration value="NEGATIVE_Z"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_format_hint_channels_enum">
        <xs:annotation>
            <xs:documentation>The per-texel layout of the format.  The length of the string indicate how many channels there are and the letter respresents the name of the channel.  There are typically 0 to 4 channels.</xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="RGB">
                <xs:annotation>
                    <xs:documentation>RGB color  map</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="RGBA">
                <xs:annotation>
                    <xs:documentation>RGB color + Alpha map often used for color + transparency or other things packed into channel A like specular power </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="L">
                <xs:annotation>
                    <xs:documentation>Luminance map often used for light mapping </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="LA">
                <xs:annotation>
                    <xs:documentation>Luminance+Alpha map often used for light mapping </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="D">
                <xs:annotation>
                    <xs:documentation>Depth map often used for displacement, parellax, relief, or shadow mapping </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="XYZ">
                <xs:annotation>
                    <xs:documentation>Typically used for normal maps or 3component displacement maps.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="XYZW">
                <xs:annotation>
                    <xs:documentation>Typically used for normal maps where W is the depth for relief or parrallax mapping </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_format_hint_precision_enum">
        <xs:annotation>
            <xs:documentation>Each channel of the texel has a precision.  Typically these are all linked together.  An exact format lay lower the precision of an individual channel but applying a higher precision by linking the channels together may still convey the same information.</xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="LOW">
                <xs:annotation>
                    <xs:documentation>For integers this typically represents 8 bits.  For floats typically 16 bits.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MID">
                <xs:annotation>
                    <xs:documentation>For integers this typically represents 8 to 24 bits.  For floats typically 16 to 32 bits.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="HIGH">
                <xs:annotation>
                    <xs:documentation>For integers this typically represents 16 to 32 bits.  For floats typically 24 to 32 bits.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_format_hint_range_enum">
        <xs:annotation>
            <xs:documentation>Each channel represents a range of values. Some example ranges are signed or unsigned integers, or between between a clamped range such as 0.0f to 1.0f, or high dynamic range via floating point</xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="SNORM">
                <xs:annotation>
                    <xs:documentation>Format is representing a decimal value that remains within the -1 to 1 range. Implimentation could be integer-fixedpoint or floats.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="UNORM">
                <xs:annotation>
                    <xs:documentation>Format is representing a decimal value that remains within the 0 to 1 range. Implimentation could be integer-fixedpoint or floats.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SINT">
                <xs:annotation>
                    <xs:documentation>Format is representing signed integer numbers.  (ex. 8bits = -128 to 127)</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="UINT">
                <xs:annotation>
                    <xs:documentation>Format is representing unsigned integer numbers.  (ex. 8bits = 0 to 255)</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FLOAT">
                <xs:annotation>
                    <xs:documentation>Format should support full floating point ranges.  High precision is expected to be 32bit. Mid precision may be 16 to 32 bit.  Low precision is expected to be 16 bit.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_surface_format_hint_option_enum">
        <xs:annotation>
            <xs:documentation>Additional hints about data relationships and other things to help the application pick the best format.</xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="SRGB_GAMMA">
                <xs:annotation>
                    <xs:documentation>colors are stored with respect to the sRGB 2.2 gamma curve rather than linear</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NORMALIZED3">
                <xs:annotation>
                    <xs:documentation>the texel's XYZ/RGB should be normalized such as in a normal map.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NORMALIZED4">
                <xs:annotation>
                    <xs:documentation>the texel's XYZW/RGBA should be normalized such as in a normal map.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="COMPRESSABLE">
                <xs:annotation>
                    <xs:documentation>The surface may use run-time compression.  Considering the best compression based on desired, channel, range, precision, and options </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="fx_surface_format_hint_common">
        <xs:annotation>
            <xs:documentation>If the exact format cannot be resolve via other methods then the format_hint will describe the important features of the format so that the application may select a compatable or close format</xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="channels" type="fx_surface_format_hint_channels_enum">
                <xs:annotation>
                    <xs:documentation>The per-texel layout of the format.  The length of the string indicate how many channels there are and the letter respresents the name of the channel.  There are typically 0 to 4 channels.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="range" type="fx_surface_format_hint_range_enum">
                <xs:annotation>
                    <xs:documentation>Each channel represents a range of values. Some example ranges are signed or unsigned integers, or between between a clamped range such as 0.0f to 1.0f, or high dynamic range via floating point</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="precision" type="fx_surface_format_hint_precision_enum" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>Each channel of the texel has a precision.  Typically these are all linked together.  An exact format lay lower the precision of an individual channel but applying a higher precision by linking the channels together may still convey the same information.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="option" type="fx_surface_format_hint_option_enum" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>Additional hints about data relationships and other things to help the application pick the best format.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_surface_init_planar_common">
        <xs:annotation>
            <xs:documentation>For 1D, 2D, RECT surface types</xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:annotation>
                <xs:documentation>This choice exists for consistancy with other init types (volume and cube).  When other initialization methods are needed.</xs:documentation>
            </xs:annotation>
            <xs:element name="all">
                <xs:annotation>
                    <xs:documentation>Init the entire surface with one compound image such as DDS</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="fx_surface_init_volume_common">
        <xs:choice>
            <xs:element name="all">
                <xs:annotation>
                    <xs:documentation>Init the entire surface with one compound image such as DDS</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="primary">
                <xs:annotation>
                    <xs:documentation>Init mip level 0 of the surface with one compound image such as DDS.  Use of this element expects that the surface has element mip_levels=0 or mipmap_generate.</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="fx_surface_init_cube_common">
        <xs:choice>
            <xs:element name="all">
                <xs:annotation>
                    <xs:documentation>Init the entire surface with one compound image such as DDS</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="primary">
                <xs:annotation>
                    <xs:documentation>Init all primary mip level 0 subsurfaces with one compound image such as DDS.  Use of this element expects that the surface has element mip_levels=0 or mipmap_generate.</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:sequence minOccurs="0">
                        <xs:annotation>
                            <xs:documentation>This sequence exists to allow the order elements to be optional but require that if they exist there must be 6 of them.</xs:documentation>
                        </xs:annotation>
                        <xs:element name="order" type="fx_surface_face_enum" minOccurs="6" maxOccurs="6">
                            <xs:annotation>
                                <xs:documentation>If the image dues not natively describe the face ordering then this series of order elements will describe which face the index belongs too</xs:documentation>
                            </xs:annotation>
                        </xs:element>
                    </xs:sequence>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="face" minOccurs="6" maxOccurs="6">
                <xs:annotation>
                    <xs:documentation>Init each face mipchain with one compound image such as DDS</xs:documentation>
                </xs:annotation>
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:IDREF" use="required"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="fx_surface_init_from_common">
        <xs:annotation>
            <xs:documentation>
                This element is an IDREF which specifies the image to use to initialize a specific mip of a 1D or 2D surface, 3D slice, or Cube face.
            </xs:documentation>
        </xs:annotation>
        <xs:simpleContent>
            <xs:extension base="xs:IDREF">
                <xs:attribute name="mip" type="xs:unsignedInt" default="0"/>
                <xs:attribute name="slice" type="xs:unsignedInt" default="0"/>
                <xs:attribute name="face" type="fx_surface_face_enum" default="POSITIVE_X"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:group name="fx_surface_init_common">
        <xs:annotation>
            <xs:documentation>The common set of initalization options for surfaces.  Choose which is appropriate for your surface based on type and other characteristics. described by the annotation docs on the child elements.</xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="init_as_null">
                <xs:annotation>
                    <xs:documentation>This surface is intended to be initialized later externally by a "setparam" element.  If it is used before being initialized there is profile and platform specific behavior.  Most elements on the surface element containing this will be ignored including mip_levels, mipmap_generate, size, viewport_ratio, and format.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="init_as_target">
                <xs:annotation>
                    <xs:documentation>Init as a target for depth, stencil, or color.  It does not need image data. Surface should not have mipmap_generate when using this.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="init_cube" type="fx_surface_init_cube_common">
                <xs:annotation>
                    <xs:documentation>Init a CUBE from a compound image such as DDS</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="init_volume" type="fx_surface_init_volume_common">
                <xs:annotation>
                    <xs:documentation>Init a 3D from a compound image such as DDS</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="init_planar" type="fx_surface_init_planar_common">
                <xs:annotation>
                    <xs:documentation>Init a 1D,2D,RECT,DEPTH from a compound image such as DDS</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="init_from" type="fx_surface_init_from_common" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>Initialize the surface one sub-surface at a time by specifying combinations of mip, face, and slice which make sense for a particular surface type.  Each sub-surface is initialized by a common 2D image, not a complex compound image such as DDS. If not all subsurfaces are initialized, it is invalid and will result in profile and platform specific behavior unless mipmap_generate is responsible for initializing the remainder of the sub-surfaces</xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
    </xs:group>
    <xs:complexType name="fx_surface_common">
        <xs:annotation>
            <xs:documentation>
            The fx_surface_common type is used to declare a resource that can be used both as the source for texture samples and as the target of a rendering pass.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:group ref="fx_surface_init_common" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>The common set of initalization options for surfaces.  Choose which is appropriate for your surface based on the type attribute and other characteristics described by the annotation docs on the choiced child elements of this type.</xs:documentation>
                </xs:annotation>
            </xs:group>
            <xs:element name="format" type="xs:token" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>Contains a string representing the profile and platform specific texel format that the author would like this surface to use.  If this element is not specified then the application will use a common format R8G8B8A8 with linear color gradient, not  sRGB.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="format_hint" type="fx_surface_format_hint_common" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>If the exact format cannot be resolved via the "format" element then the format_hint will describe the important features of the format so that the application may select a compatable or close format</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:choice minOccurs="0">
                <xs:element name="size" type="int3" default="0 0 0">
                    <xs:annotation>
                        <xs:documentation>The surface should be sized to these exact dimensions</xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="viewport_ratio" type="float2" default="1 1">
                    <xs:annotation>
                        <xs:documentation>The surface should be sized to a dimension based on this ratio of the viewport's dimensions in pixels</xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:choice>
            <xs:element name="mip_levels" type="xs:unsignedInt" default="0" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>the surface should contain the following number of MIP levels.  If this element is not present it is assumed that all miplevels exist until a dimension becomes 1 texel.  To create a surface that has only one level of mip maps (mip=0) set this to 1.  If the value is 0 the result is the same as if mip_levels was unspecified, all possible mip_levels will exist.</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="mipmap_generate" type="xs:boolean" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>By default it is assumed that mipmaps are supplied by the author so, if not all subsurfaces are initialized, it is invalid and will result in profile and platform specific behavior unless mipmap_generate is responsible for initializing the remainder of the sub-surfaces</xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
        <xs:attribute name="type" type="fx_surface_type_enum" use="required">
            <xs:annotation>
                <xs:documentation>Specifying the type of a surface is mandatory though the type may be "UNTYPED".  When a surface is typed as UNTYPED, it is said to be temporarily untyped and instead will be typed later by the context it is used in such as which samplers reference it in that are used in a particular technique or pass.   If there is a type mismatch between what is set into it later and what the runtime decides the type should be the result in profile and platform specific behavior.</xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:simpleType name="fx_sampler_wrap_common">
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="NONE"/>
            <xs:enumeration value="WRAP"/>
            <xs:enumeration value="MIRROR"/>
            <xs:enumeration value="CLAMP"/>
            <xs:enumeration value="BORDER"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="fx_sampler_filter_common">
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="NONE"/>
            <xs:enumeration value="NEAREST"/>
            <xs:enumeration value="LINEAR"/>
            <xs:enumeration value="NEAREST_MIPMAP_NEAREST"/>
            <xs:enumeration value="LINEAR_MIPMAP_NEAREST"/>
            <xs:enumeration value="NEAREST_MIPMAP_LINEAR"/>
            <xs:enumeration value="LINEAR_MIPMAP_LINEAR"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="fx_sampler1D_common">
        <xs:annotation>
            <xs:documentation>
            A one-dimensional texture sampler.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="border_color" type="fx_color_common" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="0" minOccurs="0"/>
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_sampler2D_common">
        <xs:annotation>
            <xs:documentation>
            A two-dimensional texture sampler.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_t" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="border_color" type="fx_color_common" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="255" minOccurs="0"/>
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_sampler3D_common">
        <xs:annotation>
            <xs:documentation>
            A three-dimensional texture sampler.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_t" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_p" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="border_color" type="fx_color_common" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="255" minOccurs="0"/>
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_samplerCUBE_common">
        <xs:annotation>
            <xs:documentation>
            A texture sampler for cube maps.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_t" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_p" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="border_color" type="fx_color_common" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="255" minOccurs="0"/>
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_samplerRECT_common">
        <xs:annotation>
            <xs:documentation>
            A two-dimensional texture sampler.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_t" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="border_color" type="fx_color_common" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="255" minOccurs="0"/>
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="fx_samplerDEPTH_common">
        <xs:annotation>
            <xs:documentation>
            A texture sampler for depth maps.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="source" type="xs:NCName"/>
            <xs:element name="wrap_s" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="wrap_t" type="fx_sampler_wrap_common" default="WRAP" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>
    <xs:group name="fx_annotate_type_common">
        <xs:annotation>
            <xs:documentation>
            A group that specifies the allowable types for an annotation.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="bool" type="bool"/>
            <xs:element name="bool2" type="bool2"/>
            <xs:element name="bool3" type="bool3"/>
            <xs:element name="bool4" type="bool4"/>
            <xs:element name="int" type="int"/>
            <xs:element name="int2" type="int2"/>
            <xs:element name="int3" type="int3"/>
            <xs:element name="int4" type="int4"/>
            <xs:element name="float" type="float"/>
            <xs:element name="float2" type="float2"/>
            <xs:element name="float3" type="float3"/>
            <xs:element name="float4" type="float4"/>
            <xs:element name="float2x2" type="float2x2"/>
            <xs:element name="float3x3" type="float3x3"/>
            <xs:element name="float4x4" type="float4x4"/>
            <xs:element name="string" type="xs:string"/>
        </xs:choice>
    </xs:group>
    <xs:group name="fx_basic_type_common">
        <xs:annotation>
            <xs:documentation>
            A group that specifies the allowable types for effect scoped parameters.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="bool" type="bool"/>
            <xs:element name="bool2" type="bool2"/>
            <xs:element name="bool3" type="bool3"/>
            <xs:element name="bool4" type="bool4"/>
            <xs:element name="int" type="int"/>
            <xs:element name="int2" type="int2"/>
            <xs:element name="int3" type="int3"/>
            <xs:element name="int4" type="int4"/>
            <xs:element name="float" type="float"/>
            <xs:element name="float2" type="float2"/>
            <xs:element name="float3" type="float3"/>
            <xs:element name="float4" type="float4"/>
            <xs:element name="float1x1" type="float"/>
            <xs:element name="float1x2" type="float2"/>
            <xs:element name="float1x3" type="float3"/>
            <xs:element name="float1x4" type="float4"/>
            <xs:element name="float2x1" type="float2"/>
            <xs:element name="float2x2" type="float2x2"/>
            <xs:element name="float2x3" type="float2x3"/>
            <xs:element name="float2x4" type="float2x4"/>
            <xs:element name="float3x1" type="float3"/>
            <xs:element name="float3x2" type="float3x2"/>
            <xs:element name="float3x3" type="float3x3"/>
            <xs:element name="float3x4" type="float3x4"/>
            <xs:element name="float4x1" type="float4"/>
            <xs:element name="float4x2" type="float4x2"/>
            <xs:element name="float4x3" type="float4x3"/>
            <xs:element name="float4x4" type="float4x4"/>
            <xs:element name="surface" type="fx_surface_common"/>
            <xs:element name="sampler1D" type="fx_sampler1D_common"/>
            <xs:element name="sampler2D" type="fx_sampler2D_common"/>
            <xs:element name="sampler3D" type="fx_sampler3D_common"/>
            <xs:element name="samplerCUBE" type="fx_samplerCUBE_common"/>
            <xs:element name="samplerRECT" type="fx_samplerRECT_common"/>
            <xs:element name="samplerDEPTH" type="fx_samplerDEPTH_common"/>
            <xs:element name="enum" type="xs:string"/>
        </xs:choice>
    </xs:group>
    <xs:simpleType name="fx_modifier_enum_common">
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="CONST"/>
            <xs:enumeration value="UNIFORM"/>
            <xs:enumeration value="VARYING"/>
            <xs:enumeration value="STATIC"/>
            <xs:enumeration value="VOLATILE"/>
            <xs:enumeration value="EXTERN"/>
            <xs:enumeration value="SHARED"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="fx_colortarget_common">
        <xs:simpleContent>
            <xs:extension base="xs:NCName">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="face" type="fx_surface_face_enum" use="optional" default="POSITIVE_X"/>
                <xs:attribute name="mip" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="slice" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="fx_depthtarget_common">
        <xs:simpleContent>
            <xs:extension base="xs:NCName">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="face" type="fx_surface_face_enum" use="optional" default="POSITIVE_X"/>
                <xs:attribute name="mip" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="slice" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="fx_stenciltarget_common">
        <xs:simpleContent>
            <xs:extension base="xs:NCName">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="face" type="fx_surface_face_enum" use="optional" default="POSITIVE_X"/>
                <xs:attribute name="mip" type="xs:nonNegativeInteger" use="optional" default="0"/>
                <xs:attribute name="slice" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="fx_clearcolor_common">
        <xs:simpleContent>
            <xs:extension base="fx_color_common">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="fx_cleardepth_common">
        <xs:simpleContent>
            <xs:extension base="float">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:complexType name="fx_clearstencil_common">
        <xs:simpleContent>
            <xs:extension base="xs:byte">
                <xs:attribute name="index" type="xs:nonNegativeInteger" use="optional" default="0"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <xs:simpleType name="fx_draw_common">
        <xs:restriction base="xs:string"/>
    </xs:simpleType>
    <xs:simpleType name="fx_pipeline_stage_common">
        <xs:restriction base="xs:string">
            <xs:enumeration value="VERTEXPROGRAM"/>
            <xs:enumeration value="FRAGMENTPROGRAM"/>
            <xs:enumeration value="VERTEXSHADER"/>
            <xs:enumeration value="PIXELSHADER"/>
        </xs:restriction>
    </xs:simpleType>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- -->
    <!-- COLLADA FX elements in common scope    -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- -->
    <xs:complexType name="fx_annotate_common">
        <xs:sequence>
            <xs:group ref="fx_annotate_type_common"/>
        </xs:sequence>
        <xs:attribute name="name" type="xs:NCName" use="required"/>
    </xs:complexType>
    <xs:complexType name="fx_include_common">
        <xs:annotation>
            <xs:documentation>
            The include element is used to import source code or precompiled binary shaders into the FX Runtime by referencing an external resource.
            </xs:documentation>
        </xs:annotation>
        <xs:attribute name="sid" type="xs:NCName" use="required">
            <xs:annotation>
                <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element.
                    This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
        <xs:attribute name="url" type="xs:anyURI" use="required">
            <xs:annotation>
                <xs:documentation>
                    The url attribute refers to resource.  This may refer to a local resource using a relative URL
                    fragment identifier that begins with the “#” character. The url attribute may refer to an external
                    resource using an absolute or relative URL.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="fx_newparam_common">
        <xs:annotation>
            <xs:documentation>
            This element creates a new, named param object in the FX Runtime, assigns it a type, an initial value, and additional attributes at declaration time.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>
                    The annotate element allows you to specify an annotation for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="semantic" type="xs:NCName" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The semantic element allows you to specify a semantic for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="modifier" type="fx_modifier_enum_common" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The modifier element allows you to specify a modifier for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:group ref="fx_basic_type_common"/>
        </xs:sequence>
        <xs:attribute name="sid" type="xs:NCName" use="required">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX types in profile scope   -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <xs:complexType name="fx_code_profile">
        <xs:annotation>
            <xs:documentation>
            The fx_code_profile type allows you to specify an inline block of source code.
            </xs:documentation>
        </xs:annotation>
        <xs:simpleContent>
            <xs:extension base="xs:string">
                <xs:attribute name="sid" type="xs:NCName" use="optional">
                    <xs:annotation>
                        <xs:documentation>
                        The sid attribute is a text string value containing the sub-identifier of this element.
                        This value must be unique within the scope of the parent element. Optional attribute.
                        </xs:documentation>
                    </xs:annotation>
                </xs:attribute>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX effect elements    -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <xs:element name="fx_profile_abstract" abstract="true">
        <xs:annotation>
            <xs:documentation>
            The fx_profile_abstract element is only used as a substitution group hook for COLLADA FX profiles.
            </xs:documentation>
        </xs:annotation>
    </xs:element>
    <xs:element name="effect">
        <xs:annotation>
            <xs:documentation>
            A self contained description of a shader effect.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The effect element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The annotate element allows you to specify an annotation on this effect.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="image" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The image element allows you to create image resources which can be shared by multipe profiles.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="newparam" type="fx_newparam_common" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The newparam element allows you to create new effect parameters which can be shared by multipe profiles.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="fx_profile_abstract" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This is the substituion group hook which allows you to swap in other COLLADA FX profiles.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX GLSL elements                  -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <xs:simpleType name="GL_MAX_LIGHTS_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="GL_MAX_CLIP_PLANES_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="GL_MAX_TEXTURE_IMAGE_UNITS_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="gl_sampler1D">
        <xs:annotation>
            <xs:documentation>
            A one-dimensional texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_sampler1D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="gl_sampler2D">
        <xs:annotation>
            <xs:documentation>
            A two-dimensional texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_sampler2D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="gl_sampler3D">
        <xs:annotation>
            <xs:documentation>
            A three-dimensional texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_sampler3D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="gl_samplerCUBE">
        <xs:annotation>
            <xs:documentation>
            A cube map texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_samplerCUBE_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="gl_samplerRECT">
        <xs:annotation>
            <xs:documentation>
            A two-dimensional texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_samplerRECT_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="gl_samplerDEPTH">
        <xs:annotation>
            <xs:documentation>
            A depth texture sampler for the GLSL profile.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_samplerDEPTH_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:simpleType name="gl_blend_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="ZERO">
                <xs:annotation>
                    <xs:appinfo>value=0x0</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE">
                <xs:annotation>
                    <xs:appinfo>value=0x1</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SRC_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0300</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_SRC_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0301</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DEST_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0306</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_DEST_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0307</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0302</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0303</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DST_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0304</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_DST_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0305</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="CONSTANT_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x8001</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_CONSTANT_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x8002</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="CONSTANT_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x8003</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_CONSTANT_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x8004</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SRC_ALPHA_SATURATE">
                <xs:annotation>
                    <xs:appinfo>value=0x0308</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_face_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="FRONT">
                <xs:annotation>
                    <xs:appinfo>value=0x0404</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="BACK">
                <xs:annotation>
                    <xs:appinfo>value=0x0405</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FRONT_AND_BACK">
                <xs:annotation>
                    <xs:appinfo>value=0x0408</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_blend_equation_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="FUNC_ADD">
                <xs:annotation>
                    <xs:appinfo>value=0x8006</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FUNC_SUBTRACT">
                <xs:annotation>
                    <xs:appinfo>value=0x800A</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FUNC_REVERSE_SUBTRACT">
                <xs:annotation>
                    <xs:appinfo>value=0x800B</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MIN">
                <xs:annotation>
                    <xs:appinfo>value=0x8007</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MAX">
                <xs:annotation>
                    <xs:appinfo>value=0x8008</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_func_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="NEVER">
                <xs:annotation>
                    <xs:appinfo>value=0x0200</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="LESS">
                <xs:annotation>
                    <xs:appinfo>value=0x0201</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="LEQUAL">
                <xs:annotation>
                    <xs:appinfo>value=0x0203</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="EQUAL">
                <xs:annotation>
                    <xs:appinfo>value=0x0202</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="GREATER">
                <xs:annotation>
                    <xs:appinfo>value=0x0204</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NOTEQUAL">
                <xs:annotation>
                    <xs:appinfo>value=0x0205</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="GEQUAL">
                <xs:annotation>
                    <xs:appinfo>value=0x0206</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ALWAYS">
                <xs:annotation>
                    <xs:appinfo>value=0x0207</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_stencil_op_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="KEEP">
                <xs:annotation>
                    <xs:appinfo>value=0x1E00</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ZERO">
                <xs:annotation>
                    <xs:appinfo>value=0x0</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="REPLACE">
                <xs:annotation>
                    <xs:appinfo>value=0x1E01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INCR">
                <xs:annotation>
                    <xs:appinfo>value=0x1E02</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DECR">
                <xs:annotation>
                    <xs:appinfo>value=0x1E03</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INVERT">
                <xs:annotation>
                    <xs:appinfo>value=0x150A</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INCR_WRAP">
                <xs:annotation>
                    <xs:appinfo>value=0x8507</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DECR_WRAP">
                <xs:annotation>
                    <xs:appinfo>value=0x8508</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_material_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="EMISSION">
                <xs:annotation>
                    <xs:appinfo>value=0x1600</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="AMBIENT">
                <xs:annotation>
                    <xs:appinfo>value=0x1200</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DIFFUSE">
                <xs:annotation>
                    <xs:appinfo>value=0x1201</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SPECULAR">
                <xs:annotation>
                    <xs:appinfo>value=0x1202</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="AMBIENT_AND_DIFFUSE">
                <xs:annotation>
                    <xs:appinfo>value=0x1602</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_fog_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="LINEAR">
                <xs:annotation>
                    <xs:appinfo>value=0x2601</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="EXP">
                <xs:annotation>
                    <xs:appinfo>value=0x0800</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="EXP2">
                <xs:annotation>
                    <xs:appinfo>value=0x0801</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_fog_coord_src_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="FOG_COORDINATE">
                <xs:annotation>
                    <xs:appinfo>value=0x8451</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FRAGMENT_DEPTH">
                <xs:annotation>
                    <xs:appinfo>value=0x8452</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_front_face_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="CW">
                <xs:annotation>
                    <xs:appinfo>value=0x0900</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="CCW">
                <xs:annotation>
                    <xs:appinfo>value=0x0901</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_light_model_color_control_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="SINGLE_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x81F9</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SEPARATE_SPECULAR_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x81FA</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_logic_op_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="CLEAR">
                <xs:annotation>
                    <xs:appinfo>value=0x1500</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="AND">
                <xs:annotation>
                    <xs:appinfo>value=0x1501</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="AND_REVERSE">
                <xs:annotation>
                    <xs:appinfo>value=0x1502</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="COPY">
                <xs:annotation>
                    <xs:appinfo>value=0x1503</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="AND_INVERTED">
                <xs:annotation>
                    <xs:appinfo>value=0x1504</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NOOP">
                <xs:annotation>
                    <xs:appinfo>value=0x1505</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="XOR">
                <xs:annotation>
                    <xs:appinfo>value=0x1506</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="OR">
                <xs:annotation>
                    <xs:appinfo>value=0x1507</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NOR">
                <xs:annotation>
                    <xs:appinfo>value=0x1508</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="EQUIV">
                <xs:annotation>
                    <xs:appinfo>value=0x1509</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INVERT">
                <xs:annotation>
                    <xs:appinfo>value=0x150A</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="OR_REVERSE">
                <xs:annotation>
                    <xs:appinfo>value=0x150B</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="COPY_INVERTED">
                <xs:annotation>
                    <xs:appinfo>value=0x150C</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="NAND">
                <xs:annotation>
                    <xs:appinfo>value=0x150E</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SET">
                <xs:annotation>
                    <xs:appinfo>value=0x150F</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_polygon_mode_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="POINT">
                <xs:annotation>
                    <xs:appinfo>value=0x1B00</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="LINE">
                <xs:annotation>
                    <xs:appinfo>value=0x1B01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="FILL">
                <xs:annotation>
                    <xs:appinfo>value=0x1B02</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_shade_model_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="FLAT">
                <xs:annotation>
                    <xs:appinfo>value=0x1D00</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SMOOTH">
                <xs:annotation>
                    <xs:appinfo>value=0x1D01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_alpha_value_type">
        <xs:restriction base="xs:float">
            <xs:minInclusive value="0.0"/>
            <xs:maxInclusive value="1.0"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gl_enumeration">
        <xs:union memberTypes="gl_blend_type gl_face_type gl_blend_equation_type gl_func_type gl_stencil_op_type gl_material_type gl_fog_type gl_fog_coord_src_type gl_front_face_type gl_light_model_color_control_type gl_logic_op_type gl_polygon_mode_type gl_shade_model_type"/>
    </xs:simpleType>
    <xs:group name="gl_pipeline_settings">
        <xs:annotation>
            <xs:documentation>
            A group that defines all of the renderstates used for the CG and GLSL profiles.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="alpha_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="func">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="value">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_alpha_value_type" use="optional" default="0.0"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="src">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ONE"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="dest">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ZERO"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_func_separate">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="src_rgb">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ONE"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="dest_rgb">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ZERO"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="src_alpha">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ONE"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="dest_alpha">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ZERO"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_equation">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_blend_equation_type" use="optional" default="FUNC_ADD"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_equation_separate">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="rgb">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_equation_type" use="optional" default="FUNC_ADD"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="alpha">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_equation_type" use="optional" default="FUNC_ADD"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_material">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="face">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_face_type" use="optional" default="FRONT_AND_BACK"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mode">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_material_type" use="optional" default="AMBIENT_AND_DIFFUSE"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="cull_face">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_face_type" use="optional" default="BACK"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_func">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_mode">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_fog_type" use="optional" default="EXP"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_coord_src">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_fog_coord_src_type" use="optional" default="FOG_COORDINATE"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="front_face">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_front_face_type" use="optional" default="CCW"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_color_control">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_light_model_color_control_type" use="optional" default="SINGLE_COLOR"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="logic_op">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_logic_op_type" use="optional" default="COPY"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_mode">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="face">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_face_type" use="optional" default="FRONT_AND_BACK"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mode">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_polygon_mode_type" use="optional" default="FILL"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="shade_model">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_shade_model_type" use="optional" default="SMOOTH"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="func">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="ref">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="0"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mask">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="255"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_op">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="fail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zfail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zpass">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_func_separate">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="front">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="back">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="ref">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="0"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mask">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="255"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_op_separate">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="face">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_face_type" use="optional" default="FRONT_AND_BACK"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="fail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zfail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zpass">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_mask_separate">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="face">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_face_type" use="optional" default="FRONT_AND_BACK"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mask">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="255"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_diffuse">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_specular">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_position">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 1 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_constant_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_linear_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_quadratic_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_cutoff">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="180"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_direction">
                <xs:complexType>
                    <xs:attribute name="value" type="float3" use="optional" default="0 0 -1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_exponent">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture1D">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_sampler1D"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture2D">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_sampler2D"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture3D">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_sampler3D"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureCUBE">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_samplerCUBE"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureRECT">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_samplerRECT"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureDEPTH">
                <xs:complexType>
                    <xs:choice>
                        <xs:element name="value" type="gl_samplerDEPTH"/>
                        <xs:element name="param" type="xs:NCName"/>
                    </xs:choice>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture1D_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture2D_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture3D_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureCUBE_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureRECT_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="textureDEPTH_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture_env_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture_env_mode">
                <xs:complexType>
                    <xs:attribute name="value" type="string" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_TEXTURE_IMAGE_UNITS_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clip_plane">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_CLIP_PLANES_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clip_plane_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GL_MAX_CLIP_PLANES_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_stencil">
                <xs:complexType>
                    <xs:attribute name="value" type="int" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_depth">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="bool4" use="optional" default="true true true true"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_bounds">
                <xs:complexType>
                    <xs:attribute name="value" type="float2" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="true"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_range">
                <xs:complexType>
                    <xs:attribute name="value" type="float2" use="optional" default="0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_density">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_start">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_end">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.2 0.2 0.2 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="lighting_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_stipple">
                <xs:complexType>
                    <xs:attribute name="value" type="int2" use="optional" default="1 65536"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_width">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.2 0.2 0.2 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_diffuse">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.8 0.8 0.8 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_emission">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_shininess">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_specular">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="model_view_matrix">
                <xs:complexType>
                    <xs:attribute name="value" type="float4x4" use="optional" default="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_distance_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float3" use="optional" default="1 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_fade_threshold_size">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size_min">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size_max">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset">
                <xs:complexType>
                    <xs:attribute name="value" type="float2" use="optional" default="0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="projection_matrix">
                <xs:complexType>
                    <xs:attribute name="value" type="float4x4" use="optional" default="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="scissor">
                <xs:complexType>
                    <xs:attribute name="value" type="int4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="int" use="optional" default="4294967295"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="alpha_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="auto_normal_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_logic_op_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_material_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="true"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="cull_face_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_bounds_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_clamp_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="dither_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="true"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_local_viewer_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_two_side_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_smooth_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_stipple_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="logic_op_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="multisample_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="normalize_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_smooth_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset_fill_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset_line_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset_point_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_smooth_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_stipple_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="rescale_normal_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_alpha_to_coverage_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_alpha_to_one_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_coverage_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="scissor_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element ref="gl_hook_abstract"/>
        </xs:choice>
    </xs:group>
    <xs:element name="gl_hook_abstract" abstract="true"/>
    <xs:simpleType name="glsl_float">
        <xs:restriction base="xs:float"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_int">
        <xs:restriction base="xs:int"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_bool">
        <xs:restriction base="xs:boolean"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_ListOfBool">
        <xs:list itemType="glsl_bool"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_ListOfFloat">
        <xs:list itemType="glsl_float"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_ListOfInt">
        <xs:list itemType="glsl_int"/>
    </xs:simpleType>
    <xs:simpleType name="glsl_bool2">
        <xs:restriction base="glsl_ListOfBool">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_bool3">
        <xs:restriction base="glsl_ListOfBool">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_bool4">
        <xs:restriction base="glsl_ListOfBool">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float2">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float3">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float4">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float2x2">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float3x3">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_float4x4">
        <xs:restriction base="glsl_ListOfFloat">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_int2">
        <xs:restriction base="glsl_ListOfInt">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_int3">
        <xs:restriction base="glsl_ListOfInt">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_int4">
        <xs:restriction base="glsl_ListOfInt">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_pipeline_stage">
        <xs:restriction base="xs:string">
            <xs:enumeration value="VERTEXPROGRAM"/>
            <xs:enumeration value="FRAGMENTPROGRAM"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="glsl_identifier">
        <xs:restriction base="xs:token"/>
    </xs:simpleType>
    <xs:complexType name="glsl_newarray_type">
        <xs:annotation>
            <xs:documentation>
            The glsl_newarray_type is used to creates a parameter of a one-dimensional array type.
            </xs:documentation>
        </xs:annotation>
        <xs:choice minOccurs="0" maxOccurs="unbounded">
            <xs:group ref="glsl_param_type"/>
            <xs:element name="array" type="glsl_newarray_type">
                <xs:annotation>
                    <xs:documentation>
                    You may recursively nest glsl_newarray elements to create multidimensional arrays.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
        <xs:attribute name="length" type="xs:positiveInteger" use="required">
            <xs:annotation>
                <xs:documentation>
                The length attribute specifies the length of the array.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="glsl_setarray_type">
        <xs:annotation>
            <xs:documentation>
            The glsl_newarray_type is used to creates a parameter of a one-dimensional array type.
            </xs:documentation>
        </xs:annotation>
        <xs:choice minOccurs="0" maxOccurs="unbounded">
            <xs:group ref="glsl_param_type"/>
            <xs:element name="array" type="glsl_setarray_type">
                <xs:annotation>
                    <xs:documentation>
                    You may recursively nest glsl_newarray elements to create multidimensional arrays.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
        <xs:attribute name="length" type="xs:positiveInteger" use="optional">
            <xs:annotation>
                <xs:documentation>
                The length attribute specifies the length of the array.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="glsl_surface_type">
        <xs:annotation>
            <xs:documentation>
            A surface type for the GLSL profile. This surface inherits from the fx_surface_common type and adds the
            ability to programmatically generate textures.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_surface_common">
                <xs:sequence>
                    <xs:element name="generator" minOccurs="0">
                        <xs:annotation>
                            <xs:documentation>
                            A procedural surface generator.
                            </xs:documentation>
                        </xs:annotation>
                        <xs:complexType>
                            <xs:sequence>
                                <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The annotate element allows you to specify an annotation for this surface generator.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:choice maxOccurs="unbounded">
                                    <xs:element name="code" type="fx_code_profile">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The code element allows you to embed GLSL code to use for this surface generator.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:element>
                                    <xs:element name="include" type="fx_include_common">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The include element allows you to import GLSL code to use for this surface generator.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:element>
                                </xs:choice>
                                <xs:element name="name">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The entry symbol for the shader function.
                                        </xs:documentation>
                                    </xs:annotation>
                                    <xs:complexType>
                                        <xs:simpleContent>
                                            <xs:extension base="xs:NCName">
                                                <xs:attribute name="source" type="xs:NCName" use="optional"/>
                                            </xs:extension>
                                        </xs:simpleContent>
                                    </xs:complexType>
                                </xs:element>
                                <xs:element name="setparam" type="glsl_setparam_simple" minOccurs="0" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The setparam element allows you to assign a new value to a previously defined parameter.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <xs:group name="glsl_param_type">
        <xs:annotation>
            <xs:documentation>
            A group that specifies the allowable types for GLSL profile parameters.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="bool" type="glsl_bool"/>
            <xs:element name="bool2" type="glsl_bool2"/>
            <xs:element name="bool3" type="glsl_bool3"/>
            <xs:element name="bool4" type="glsl_bool4"/>
            <xs:element name="float" type="glsl_float"/>
            <xs:element name="float2" type="glsl_float2"/>
            <xs:element name="float3" type="glsl_float3"/>
            <xs:element name="float4" type="glsl_float4"/>
            <xs:element name="float2x2" type="glsl_float2x2"/>
            <xs:element name="float3x3" type="glsl_float3x3"/>
            <xs:element name="float4x4" type="glsl_float4x4"/>
            <xs:element name="int" type="glsl_int"/>
            <xs:element name="int2" type="glsl_int2"/>
            <xs:element name="int3" type="glsl_int3"/>
            <xs:element name="int4" type="glsl_int4"/>
            <xs:element name="surface" type="glsl_surface_type"/>
            <xs:element name="sampler1D" type="gl_sampler1D"/>
            <xs:element name="sampler2D" type="gl_sampler2D"/>
            <xs:element name="sampler3D" type="gl_sampler3D"/>
            <xs:element name="samplerCUBE" type="gl_samplerCUBE"/>
            <xs:element name="samplerRECT" type="gl_samplerRECT"/>
            <xs:element name="samplerDEPTH" type="gl_samplerDEPTH"/>
            <xs:element name="enum" type="gl_enumeration"/>
        </xs:choice>
    </xs:group>
    <xs:complexType name="glsl_newparam">
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
            <xs:element name="semantic" type="xs:NCName" minOccurs="0"/>
            <xs:element name="modifier" type="fx_modifier_enum_common" minOccurs="0"/>
            <xs:choice>
                <xs:group ref="glsl_param_type"/>
                <xs:element name="array" type="glsl_newarray_type"/>
            </xs:choice>
        </xs:sequence>
        <xs:attribute name="sid" type="glsl_identifier" use="required"/>
    </xs:complexType>
    <xs:complexType name="glsl_setparam_simple">
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
            <xs:group ref="glsl_param_type"/>
        </xs:sequence>
        <xs:attribute name="ref" type="glsl_identifier" use="required"/>
    </xs:complexType>
    <xs:complexType name="glsl_setparam">
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
            <xs:choice>
                <xs:group ref="glsl_param_type"/>
                <xs:element name="array" type="glsl_setarray_type"/>
            </xs:choice>
        </xs:sequence>
        <xs:attribute name="ref" type="glsl_identifier" use="required"/>
        <xs:attribute name="program" type="xs:NCName"/>
    </xs:complexType>
    <xs:element name="profile_GLSL" substitutionGroup="fx_profile_abstract">
        <xs:annotation>
            <xs:documentation>
            Opens a block of GLSL platform-specific data types and technique declarations.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0"/>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element name="code" type="fx_code_profile"/>
                    <xs:element name="include" type="fx_include_common"/>
                </xs:choice>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="image"/>
                    <xs:element name="newparam" type="glsl_newparam"/>
                </xs:choice>
                <xs:element name="technique" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        Holds a description of the textures, samplers, shaders, parameters, and passes necessary for rendering this effect using one method.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element name="code" type="fx_code_profile"/>
                                <xs:element name="include" type="fx_include_common"/>
                            </xs:choice>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element ref="image"/>
                                <xs:element name="newparam" type="glsl_newparam"/>
                                <xs:element name="setparam" type="glsl_setparam"/>
                            </xs:choice>
                            <xs:element name="pass" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    A static declaration of all the render states, shaders, and settings for one rendering pipeline.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="color_target" type="fx_colortarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="depth_target" type="fx_depthtarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="stencil_target" type="fx_stenciltarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="color_clear" type="fx_clearcolor_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="depth_clear" type="fx_cleardepth_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="stencil_clear" type="fx_clearstencil_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="draw" type="fx_draw_common" minOccurs="0"/>
                                        <xs:choice maxOccurs="unbounded">
                                            <xs:group ref="gl_pipeline_settings"/>
                                            <xs:element name="shader">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Declare and prepare a shader for execution in the rendering pipeline of a pass.
                                                    </xs:documentation>
                                                </xs:annotation>
                                                <xs:complexType>
                                                    <xs:sequence>
                                                        <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                                        <xs:sequence minOccurs="0">
                                                            <xs:element name="compiler_target">
                                                                <xs:annotation>
                                                                    <xs:documentation>
                                                                    A string declaring which profile or platform the compiler is targeting this shader for.
                                                                    </xs:documentation>
                                                                </xs:annotation>
                                                                <xs:complexType>
                                                                    <xs:simpleContent>
                                                                        <xs:extension base="xs:NMTOKEN"/>
                                                                    </xs:simpleContent>
                                                                </xs:complexType>
                                                            </xs:element>
                                                            <xs:element name="compiler_options" type="xs:string" minOccurs="0">
                                                                <xs:annotation>
                                                                    <xs:documentation>
                                                                    A string containing command-line operations for the shader compiler.
                                                                    </xs:documentation>
                                                                </xs:annotation>
                                                            </xs:element>
                                                        </xs:sequence>
                                                        <xs:element name="name">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                The entry symbol for the shader function.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                            <xs:complexType>
                                                                <xs:simpleContent>
                                                                    <xs:extension base="xs:NCName">
                                                                        <xs:attribute name="source" type="xs:NCName" use="optional"/>
                                                                    </xs:extension>
                                                                </xs:simpleContent>
                                                            </xs:complexType>
                                                        </xs:element>
                                                        <xs:element name="bind" minOccurs="0" maxOccurs="unbounded">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                Binds values to uniform inputs of a shader.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                            <xs:complexType>
                                                                <xs:choice>
                                                                    <xs:group ref="glsl_param_type"/>
                                                                    <xs:element name="param">
                                                                        <xs:complexType>
                                                                            <xs:attribute name="ref" type="xs:string" use="required"/>
                                                                        </xs:complexType>
                                                                    </xs:element>
                                                                </xs:choice>
                                                                <xs:attribute name="symbol" type="xs:NCName" use="required">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The identifier for a uniform input parameter to the shader (a formal function parameter or in-scope
                                                                        global) that will be bound to an external resource.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:attribute>
                                                            </xs:complexType>
                                                        </xs:element>
                                                    </xs:sequence>
                                                    <xs:attribute name="stage" type="glsl_pipeline_stage">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            In which pipeline stage this programmable shader is designed to execute, for example, VERTEX, FRAGMENT, etc.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:attribute>
                                                </xs:complexType>
                                            </xs:element>
                                        </xs:choice>
                                        <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                                    </xs:sequence>
                                    <xs:attribute name="sid" type="xs:NCName" use="optional">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The sid attribute is a text string value containing the sub-identifier of this element.
                                            This value must be unique within the scope of the parent element. Optional attribute.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:attribute>
                                </xs:complexType>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                        </xs:sequence>
                        <xs:attribute name="id" type="xs:ID">
                            <xs:annotation>
                                <xs:documentation>
                                The id attribute is a text string containing the unique identifier of this element.
                                This value must be unique within the instance document. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="sid" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The sid attribute is a text string value containing the sub-identifier of this element.
                                This value must be unique within the scope of the parent element. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="optional">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX common profile                   -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <xs:complexType name="common_float_or_param_type">
        <xs:choice>
            <xs:element name="float">
                <xs:complexType>
                    <xs:simpleContent>
                        <xs:extension base="float">
                            <xs:attribute name="sid" type="xs:NCName"/>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>
            </xs:element>
            <xs:element name="param">
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:NCName" use="required"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="common_color_or_texture_type">
        <xs:choice>
            <xs:element name="color">
                <xs:complexType>
                    <xs:simpleContent>
                        <xs:extension base="fx_color_common">
                            <xs:attribute name="sid" type="xs:NCName"/>
                        </xs:extension>
                    </xs:simpleContent>
                </xs:complexType>
            </xs:element>
            <xs:element name="param">
                <xs:complexType>
                    <xs:attribute name="ref" type="xs:NCName" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element ref="extra" minOccurs="0"/>
                    </xs:sequence>
                    <xs:attribute name="texture" type="xs:NCName" use="required"/>
                    <xs:attribute name="texcoord" type="xs:NCName" use="required"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:complexType>
    <xs:complexType name="common_transparent_type">
        <xs:complexContent>
            <xs:extension base="common_color_or_texture_type">
                <xs:attribute name="opaque" type="fx_opaque_enum" default="A_ONE"/>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="common_newparam_type">
        <xs:sequence>
            <xs:element name="semantic" type="xs:NCName" minOccurs="0"/>
            <xs:choice>
                <xs:element name="float" type="float"/>
                <xs:element name="float2" type="float2"/>
                <xs:element name="float3" type="float3"/>
                <xs:element name="float4" type="float4"/>
                <xs:element name="surface" type="fx_surface_common"/>
                <xs:element name="sampler2D" type="fx_sampler2D_common"/>
            </xs:choice>
        </xs:sequence>
        <xs:attribute name="sid" type="xs:NCName" use="required">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:element name="profile_COMMON" substitutionGroup="fx_profile_abstract">
        <xs:annotation>
            <xs:documentation>
            Opens a block of COMMON platform-specific data types and technique declarations.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0"/>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="image"/>
                    <xs:element name="newparam" type="common_newparam_type"/>
                </xs:choice>
                <xs:element name="technique">
                    <xs:annotation>
                        <xs:documentation>
                        Holds a description of the textures, samplers, shaders, parameters, and passes necessary for rendering this effect using one method.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="asset" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The technique element may contain an asset element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element ref="image"/>
                                <xs:element name="newparam" type="common_newparam_type"/>
                            </xs:choice>
                            <xs:choice>
                                <xs:element name="constant">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="emission" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflective" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflectivity" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="transparent" type="common_transparent_type" minOccurs="0"/>
                                            <xs:element name="transparency" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="index_of_refraction" type="common_float_or_param_type" minOccurs="0"/>
                                        </xs:sequence>
                                    </xs:complexType>
                                </xs:element>
                                <xs:element name="lambert">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="emission" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="ambient" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="diffuse" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflective" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflectivity" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="transparent" type="common_transparent_type" minOccurs="0"/>
                                            <xs:element name="transparency" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="index_of_refraction" type="common_float_or_param_type" minOccurs="0"/>
                                        </xs:sequence>
                                    </xs:complexType>
                                </xs:element>
                                <xs:element name="phong">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="emission" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="ambient" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="diffuse" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="specular" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="shininess" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="reflective" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflectivity" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="transparent" type="common_transparent_type" minOccurs="0"/>
                                            <xs:element name="transparency" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="index_of_refraction" type="common_float_or_param_type" minOccurs="0"/>
                                    </xs:sequence>
                                    </xs:complexType>
                                </xs:element>
                                <xs:element name="blinn">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="emission" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="ambient" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="diffuse" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="specular" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="shininess" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="reflective" type="common_color_or_texture_type" minOccurs="0"/>
                                            <xs:element name="reflectivity" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="transparent" type="common_transparent_type" minOccurs="0"/>
                                            <xs:element name="transparency" type="common_float_or_param_type" minOccurs="0"/>
                                            <xs:element name="index_of_refraction" type="common_float_or_param_type" minOccurs="0"/>
                                        </xs:sequence>
                                    </xs:complexType>
                                </xs:element>
                            </xs:choice>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                        <xs:attribute name="id" type="xs:ID">
                            <xs:annotation>
                                <xs:documentation>
                                The id attribute is a text string containing the unique identifier of this element.
                                This value must be unique within the instance document. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="sid" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The sid attribute is a text string value containing the sub-identifier of this element.
                                This value must be unique within the scope of the parent element. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="optional">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX Cg elements                      -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <xs:simpleType name="cg_bool">
        <xs:restriction base="xs:boolean"/>
    </xs:simpleType>
    <xs:simpleType name="cg_float">
        <xs:restriction base="xs:float"/>
    </xs:simpleType>
    <xs:simpleType name="cg_int">
        <xs:restriction base="xs:int"/>
    </xs:simpleType>
    <xs:simpleType name="cg_half">
        <xs:restriction base="xs:float"/>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed">
        <xs:restriction base="xs:float">
            <xs:minInclusive value="-2.0"/>
            <xs:maxInclusive value="2.0"/>
            <!-- as defined for fp30 profile -->
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool1">
        <xs:restriction base="xs:boolean"/>
    </xs:simpleType>
    <xs:simpleType name="cg_float1">
        <xs:restriction base="xs:float"/>
    </xs:simpleType>
    <xs:simpleType name="cg_int1">
        <xs:restriction base="xs:int"/>
    </xs:simpleType>
    <xs:simpleType name="cg_half1">
        <xs:restriction base="xs:float"/>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed1">
        <xs:restriction base="xs:float">
            <xs:minInclusive value="-2.0"/>
            <xs:maxInclusive value="2.0"/>
            <!-- as defined for fp30 profile -->
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_ListOfBool">
        <xs:list itemType="cg_bool"/>
    </xs:simpleType>
    <xs:simpleType name="cg_ListOfFloat">
        <xs:list itemType="cg_float"/>
    </xs:simpleType>
    <xs:simpleType name="cg_ListOfInt">
        <xs:list itemType="cg_int"/>
    </xs:simpleType>
    <xs:simpleType name="cg_ListOfHalf">
        <xs:list itemType="cg_half"/>
    </xs:simpleType>
    <xs:simpleType name="cg_ListOfFixed">
        <xs:list itemType="cg_fixed"/>
    </xs:simpleType>
    <xs:simpleType name="cg_bool2">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool3">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool4">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool1x1">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="1"/>
            <xs:maxLength value="1"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool1x2">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool1x3">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool1x4">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool2x1">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool2x2">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool2x3">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool2x4">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool3x1">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool3x2">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool3x3">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool3x4">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool4x1">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool4x2">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool4x3">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_bool4x4">
        <xs:restriction base="cg_ListOfBool">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float2">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float3">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float4">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float1x1">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="1"/>
            <xs:maxLength value="1"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float1x2">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float1x3">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float1x4">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float2x1">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float2x2">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float2x3">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float2x4">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float3x1">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float3x2">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float3x3">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float3x4">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float4x1">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float4x2">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float4x3">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_float4x4">
        <xs:restriction base="cg_ListOfFloat">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int2">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int3">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int4">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int1x1">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="1"/>
            <xs:maxLength value="1"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int1x2">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int1x3">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int1x4">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int2x1">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int2x2">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int2x3">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int2x4">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int3x1">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int3x2">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int3x3">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int3x4">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int4x1">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int4x2">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int4x3">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_int4x4">
        <xs:restriction base="cg_ListOfInt">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half2">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half3">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half4">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half1x1">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="1"/>
            <xs:maxLength value="1"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half1x2">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half1x3">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half1x4">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half2x1">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half2x2">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half2x3">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half2x4">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half3x1">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half3x2">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half3x3">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half3x4">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half4x1">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half4x2">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half4x3">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_half4x4">
        <xs:restriction base="cg_ListOfHalf">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed2">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed3">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed4">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed1x1">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="1"/>
            <xs:maxLength value="1"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed1x2">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed1x3">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed1x4">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed2x1">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="2"/>
            <xs:maxLength value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed2x2">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed2x3">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed2x4">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed3x1">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="3"/>
            <xs:maxLength value="3"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed3x2">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="6"/>
            <xs:maxLength value="6"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed3x3">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="9"/>
            <xs:maxLength value="9"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed3x4">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed4x1">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="4"/>
            <xs:maxLength value="4"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed4x2">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="8"/>
            <xs:maxLength value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed4x3">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="12"/>
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_fixed4x4">
        <xs:restriction base="cg_ListOfFixed">
            <xs:minLength value="16"/>
            <xs:maxLength value="16"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="cg_sampler1D">
        <xs:complexContent>
            <xs:extension base="fx_sampler1D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="cg_sampler2D">
        <xs:complexContent>
            <xs:extension base="fx_sampler2D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="cg_sampler3D">
        <xs:complexContent>
            <xs:extension base="fx_sampler3D_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="cg_samplerCUBE">
        <xs:complexContent>
            <xs:extension base="fx_samplerCUBE_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="cg_samplerRECT">
        <xs:complexContent>
            <xs:extension base="fx_samplerRECT_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:complexType name="cg_samplerDEPTH">
        <xs:complexContent>
            <xs:extension base="fx_samplerDEPTH_common"/>
        </xs:complexContent>
    </xs:complexType>
    <xs:simpleType name="cg_pipeline_stage">
        <xs:restriction base="xs:string">
            <xs:enumeration value="VERTEX"/>
            <xs:enumeration value="FRAGMENT"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="cg_identifier">
        <xs:restriction base="xs:token"/>
        <!-- type used to represent identifiers in Cg, e.g. "myLight.bitmap[2].width" -->
    </xs:simpleType>
    <xs:complexType name="cg_connect_param">
        <xs:annotation>
            <xs:documentation>
            Creates a symbolic connection between two previously defined parameters.
            </xs:documentation>
        </xs:annotation>
        <xs:attribute name="ref" type="cg_identifier" use="required"/>
    </xs:complexType>
    <xs:complexType name="cg_newarray_type">
        <xs:annotation>
            <xs:documentation>
            Creates a parameter of a one-dimensional array type.
            </xs:documentation>
        </xs:annotation>
        <xs:choice minOccurs="0" maxOccurs="unbounded">
            <xs:group ref="cg_param_type"/>
            <xs:element name="array" type="cg_newarray_type">
                <xs:annotation>
                    <xs:documentation>
                    Nested array elements allow you to create multidemensional arrays.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="usertype" type="cg_setuser_type">
                <xs:annotation>
                    <xs:documentation>
                    The usertype element allows you to create arrays of usertypes.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="connect_param" type="cg_connect_param"/>
        </xs:choice>
        <xs:attribute name="length" type="xs:positiveInteger" use="required">
            <xs:annotation>
                <xs:documentation>
                The length attribute specifies the length of the array.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="cg_setarray_type">
        <xs:annotation>
            <xs:documentation>
            Creates a parameter of a one-dimensional array type.
            </xs:documentation>
        </xs:annotation>
        <xs:choice minOccurs="0" maxOccurs="unbounded">
            <xs:group ref="cg_param_type"/>
            <xs:element name="array" type="cg_setarray_type">
                <xs:annotation>
                    <xs:documentation>
                    Nested array elements allow you to create multidemensional arrays.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="usertype" type="cg_setuser_type">
                <xs:annotation>
                    <xs:documentation>
                    The usertype element allows you to create arrays of usertypes.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
        <xs:attribute name="length" type="xs:positiveInteger" use="optional">
            <xs:annotation>
                <xs:documentation>
                The length attribute specifies the length of the array.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="cg_setuser_type">
        <xs:annotation>
            <xs:documentation>
            Creates an instance of a structured class.
            </xs:documentation>
        </xs:annotation>
        <xs:choice minOccurs="0">
            <xs:annotation>
                <xs:documentation>Some usertypes do not have data.  They may be used only to implement interface functions.</xs:documentation>
            </xs:annotation>
            <xs:choice maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>Use a combination of these to initialize the usertype in an order-dependent manner.</xs:documentation>
                </xs:annotation>
                <xs:group ref="cg_param_type"/>
                <xs:element name="array" type="cg_setarray_type"/>
                <xs:element name="usertype" type="cg_setuser_type"/>
                <xs:element name="connect_param" type="cg_connect_param"/>
            </xs:choice>
            <xs:element name="setparam" type="cg_setparam" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>Use a series of these to set the members by name.  The ref attribute will be relative to the usertype you are in right now.</xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
        <xs:attribute name="name" type="cg_identifier" use="required"/>
        <xs:attribute name="source" type="xs:NCName" use="required">
            <xs:annotation>
                <xs:documentation>
                    Reference a code or include element which defines the usertype
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="cg_surface_type">
        <xs:annotation>
            <xs:documentation>
            Declares a resource that can be used both as the source for texture samples and as the target of a rendering pass.
            </xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="fx_surface_common">
                <xs:sequence>
                    <xs:element name="generator" minOccurs="0">
                        <xs:annotation>
                            <xs:documentation>
                            A procedural surface generator for the cg profile.
                            </xs:documentation>
                        </xs:annotation>
                        <xs:complexType>
                            <xs:sequence>
                                <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The annotate element allows you to specify an annotation for this generator.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:choice maxOccurs="unbounded">
                                    <xs:element name="code" type="fx_code_profile">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The code element allows you to embed cg sourcecode for the surface generator.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:element>
                                    <xs:element name="include" type="fx_include_common">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The include element imports cg source code or precompiled binary shaders into the FX Runtime by referencing an external resource.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:element>
                                </xs:choice>
                                <xs:element name="name">
                                    <xs:annotation>
                                        <xs:documentation>
                                        The entry symbol for the shader function.
                                        </xs:documentation>
                                    </xs:annotation>
                                    <xs:complexType>
                                        <xs:simpleContent>
                                            <xs:extension base="xs:NCName">
                                                <xs:attribute name="source" type="xs:NCName" use="optional"/>
                                            </xs:extension>
                                        </xs:simpleContent>
                                    </xs:complexType>
                                </xs:element>
                                <xs:element name="setparam" type="cg_setparam_simple" minOccurs="0" maxOccurs="unbounded">
                                    <xs:annotation>
                                        <xs:documentation>
                                            Assigns a new value to a previously defined parameter.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                            </xs:sequence>
                        </xs:complexType>
                    </xs:element>
                </xs:sequence>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
    <xs:group name="cg_param_type">
        <xs:annotation>
            <xs:documentation>
            A group that specifies the allowable types for CG profile parameters.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="bool" type="cg_bool"/>
            <xs:element name="bool1" type="cg_bool1"/>
            <xs:element name="bool2" type="cg_bool2"/>
            <xs:element name="bool3" type="cg_bool3"/>
            <xs:element name="bool4" type="cg_bool4"/>
            <xs:element name="bool1x1" type="cg_bool1x1"/>
            <xs:element name="bool1x2" type="cg_bool1x2"/>
            <xs:element name="bool1x3" type="cg_bool1x3"/>
            <xs:element name="bool1x4" type="cg_bool1x4"/>
            <xs:element name="bool2x1" type="cg_bool2x1"/>
            <xs:element name="bool2x2" type="cg_bool2x2"/>
            <xs:element name="bool2x3" type="cg_bool2x3"/>
            <xs:element name="bool2x4" type="cg_bool2x4"/>
            <xs:element name="bool3x1" type="cg_bool3x1"/>
            <xs:element name="bool3x2" type="cg_bool3x2"/>
            <xs:element name="bool3x3" type="cg_bool3x3"/>
            <xs:element name="bool3x4" type="cg_bool3x4"/>
            <xs:element name="bool4x1" type="cg_bool4x1"/>
            <xs:element name="bool4x2" type="cg_bool4x2"/>
            <xs:element name="bool4x3" type="cg_bool4x3"/>
            <xs:element name="bool4x4" type="cg_bool4x4"/>
            <xs:element name="float" type="cg_float"/>
            <xs:element name="float1" type="cg_float1"/>
            <xs:element name="float2" type="cg_float2"/>
            <xs:element name="float3" type="cg_float3"/>
            <xs:element name="float4" type="cg_float4"/>
            <xs:element name="float1x1" type="cg_float1x1"/>
            <xs:element name="float1x2" type="cg_float1x2"/>
            <xs:element name="float1x3" type="cg_float1x3"/>
            <xs:element name="float1x4" type="cg_float1x4"/>
            <xs:element name="float2x1" type="cg_float2x1"/>
            <xs:element name="float2x2" type="cg_float2x2"/>
            <xs:element name="float2x3" type="cg_float2x3"/>
            <xs:element name="float2x4" type="cg_float2x4"/>
            <xs:element name="float3x1" type="cg_float3x1"/>
            <xs:element name="float3x2" type="cg_float3x2"/>
            <xs:element name="float3x3" type="cg_float3x3"/>
            <xs:element name="float3x4" type="cg_float3x4"/>
            <xs:element name="float4x1" type="cg_float4x1"/>
            <xs:element name="float4x2" type="cg_float4x2"/>
            <xs:element name="float4x3" type="cg_float4x3"/>
            <xs:element name="float4x4" type="cg_float4x4"/>
            <xs:element name="int" type="cg_int"/>
            <xs:element name="int1" type="cg_int1"/>
            <xs:element name="int2" type="cg_int2"/>
            <xs:element name="int3" type="cg_int3"/>
            <xs:element name="int4" type="cg_int4"/>
            <xs:element name="int1x1" type="cg_int1x1"/>
            <xs:element name="int1x2" type="cg_int1x2"/>
            <xs:element name="int1x3" type="cg_int1x3"/>
            <xs:element name="int1x4" type="cg_int1x4"/>
            <xs:element name="int2x1" type="cg_int2x1"/>
            <xs:element name="int2x2" type="cg_int2x2"/>
            <xs:element name="int2x3" type="cg_int2x3"/>
            <xs:element name="int2x4" type="cg_int2x4"/>
            <xs:element name="int3x1" type="cg_int3x1"/>
            <xs:element name="int3x2" type="cg_int3x2"/>
            <xs:element name="int3x3" type="cg_int3x3"/>
            <xs:element name="int3x4" type="cg_int3x4"/>
            <xs:element name="int4x1" type="cg_int4x1"/>
            <xs:element name="int4x2" type="cg_int4x2"/>
            <xs:element name="int4x3" type="cg_int4x3"/>
            <xs:element name="int4x4" type="cg_int4x4"/>
            <xs:element name="half" type="cg_half"/>
            <xs:element name="half1" type="cg_half1"/>
            <xs:element name="half2" type="cg_half2"/>
            <xs:element name="half3" type="cg_half3"/>
            <xs:element name="half4" type="cg_half4"/>
            <xs:element name="half1x1" type="cg_half1x1"/>
            <xs:element name="half1x2" type="cg_half1x2"/>
            <xs:element name="half1x3" type="cg_half1x3"/>
            <xs:element name="half1x4" type="cg_half1x4"/>
            <xs:element name="half2x1" type="cg_half2x1"/>
            <xs:element name="half2x2" type="cg_half2x2"/>
            <xs:element name="half2x3" type="cg_half2x3"/>
            <xs:element name="half2x4" type="cg_half2x4"/>
            <xs:element name="half3x1" type="cg_half3x1"/>
            <xs:element name="half3x2" type="cg_half3x2"/>
            <xs:element name="half3x3" type="cg_half3x3"/>
            <xs:element name="half3x4" type="cg_half3x4"/>
            <xs:element name="half4x1" type="cg_half4x1"/>
            <xs:element name="half4x2" type="cg_half4x2"/>
            <xs:element name="half4x3" type="cg_half4x3"/>
            <xs:element name="half4x4" type="cg_half4x4"/>
            <xs:element name="fixed" type="cg_fixed"/>
            <xs:element name="fixed1" type="cg_fixed1"/>
            <xs:element name="fixed2" type="cg_fixed2"/>
            <xs:element name="fixed3" type="cg_fixed3"/>
            <xs:element name="fixed4" type="cg_fixed4"/>
            <xs:element name="fixed1x1" type="cg_fixed1x1"/>
            <xs:element name="fixed1x2" type="cg_fixed1x2"/>
            <xs:element name="fixed1x3" type="cg_fixed1x3"/>
            <xs:element name="fixed1x4" type="cg_fixed1x4"/>
            <xs:element name="fixed2x1" type="cg_fixed2x1"/>
            <xs:element name="fixed2x2" type="cg_fixed2x2"/>
            <xs:element name="fixed2x3" type="cg_fixed2x3"/>
            <xs:element name="fixed2x4" type="cg_fixed2x4"/>
            <xs:element name="fixed3x1" type="cg_fixed3x1"/>
            <xs:element name="fixed3x2" type="cg_fixed3x2"/>
            <xs:element name="fixed3x3" type="cg_fixed3x3"/>
            <xs:element name="fixed3x4" type="cg_fixed3x4"/>
            <xs:element name="fixed4x1" type="cg_fixed4x1"/>
            <xs:element name="fixed4x2" type="cg_fixed4x2"/>
            <xs:element name="fixed4x3" type="cg_fixed4x3"/>
            <xs:element name="fixed4x4" type="cg_fixed4x4"/>
            <xs:element name="surface" type="cg_surface_type"/>
            <xs:element name="sampler1D" type="cg_sampler1D"/>
            <xs:element name="sampler2D" type="cg_sampler2D"/>
            <xs:element name="sampler3D" type="cg_sampler3D"/>
            <xs:element name="samplerRECT" type="cg_samplerRECT"/>
            <xs:element name="samplerCUBE" type="cg_samplerCUBE"/>
            <xs:element name="samplerDEPTH" type="cg_samplerDEPTH"/>
            <xs:element name="string" type="xs:string"/>
            <xs:element name="enum" type="gl_enumeration"/>
        </xs:choice>
    </xs:group>
    <xs:complexType name="cg_newparam">
        <xs:annotation>
            <xs:documentation>
            Create a new, named param object in the CG Runtime, assign it a type, an initial value, and additional attributes at declaration time.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>
                    The annotate element allows you to specify an annotation for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="semantic" type="xs:NCName" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The semantic element allows you to specify a semantic for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="modifier" type="fx_modifier_enum_common" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The modifier element allows you to specify a modifier for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:choice>
                <xs:group ref="cg_param_type"/>
                <xs:element name="usertype" type="cg_setuser_type"/>
                <xs:element name="array" type="cg_newarray_type"/>
            </xs:choice>
        </xs:sequence>
        <xs:attribute name="sid" type="cg_identifier" use="required"/>
    </xs:complexType>
    <xs:complexType name="cg_setparam_simple">
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
            <xs:group ref="cg_param_type"/>
        </xs:sequence>
        <xs:attribute name="ref" type="cg_identifier" use="required"/>
    </xs:complexType>
    <xs:complexType name="cg_setparam">
        <xs:annotation>
            <xs:documentation>
            Assigns a new value to a previously defined parameter.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:group ref="cg_param_type"/>
            <xs:element name="usertype" type="cg_setuser_type"/>
            <xs:element name="array" type="cg_setarray_type"/>
            <xs:element name="connect_param" type="cg_connect_param"/>
        </xs:choice>
        <xs:attribute name="ref" type="cg_identifier" use="required"/>
        <xs:attribute name="program" type="xs:NCName"/>
    </xs:complexType>
    <xs:element name="profile_CG" substitutionGroup="fx_profile_abstract">
        <xs:annotation>
            <xs:documentation>
            Opens a block of CG platform-specific data types and technique declarations.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0"/>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element name="code" type="fx_code_profile"/>
                    <xs:element name="include" type="fx_include_common"/>
                </xs:choice>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="image"/>
                    <xs:element name="newparam" type="cg_newparam"/>
                </xs:choice>
                <xs:element name="technique" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        Holds a description of the textures, samplers, shaders, parameters, and passes necessary for rendering this effect using one method.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="asset" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The technique element may contain an asset element.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element name="code" type="fx_code_profile"/>
                                <xs:element name="include" type="fx_include_common"/>
                            </xs:choice>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element ref="image"/>
                                <xs:element name="newparam" type="cg_newparam"/>
                                <xs:element name="setparam" type="cg_setparam"/>
                            </xs:choice>
                            <xs:element name="pass" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    A static declaration of all the render states, shaders, and settings for one rendering pipeline.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="color_target" type="fx_colortarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="depth_target" type="fx_depthtarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="stencil_target" type="fx_stenciltarget_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="color_clear" type="fx_clearcolor_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="depth_clear" type="fx_cleardepth_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="stencil_clear" type="fx_clearstencil_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="draw" type="fx_draw_common" minOccurs="0"/>
                                        <xs:choice maxOccurs="unbounded">
                                            <xs:group ref="gl_pipeline_settings"/>
                                            <xs:element name="shader">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Declare and prepare a shader for execution in the rendering pipeline of a pass.
                                                    </xs:documentation>
                                                </xs:annotation>
                                                <xs:complexType>
                                                    <xs:sequence>
                                                        <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                                        <xs:sequence minOccurs="0">
                                                            <xs:element name="compiler_target">
                                                                <xs:complexType>
                                                                    <xs:simpleContent>
                                                                        <xs:extension base="xs:NMTOKEN"/>
                                                                    </xs:simpleContent>
                                                                </xs:complexType>
                                                            </xs:element>
                                                            <xs:element name="compiler_options" type="xs:string" minOccurs="0">
                                                                <xs:annotation>
                                                                    <xs:documentation>
                                                                    A string containing command-line operations for the shader compiler.
                                                                    </xs:documentation>
                                                                </xs:annotation>
                                                            </xs:element>
                                                        </xs:sequence>
                                                        <xs:element name="name">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                The entry symbol for the shader function.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                            <xs:complexType>
                                                                <xs:simpleContent>
                                                                    <xs:extension base="xs:NCName">
                                                                        <xs:attribute name="source" type="xs:NCName" use="optional"/>
                                                                    </xs:extension>
                                                                </xs:simpleContent>
                                                            </xs:complexType>
                                                        </xs:element>
                                                        <xs:element name="bind" minOccurs="0" maxOccurs="unbounded">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                Binds values to uniform inputs of a shader.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                            <xs:complexType>
                                                                <xs:choice>
                                                                    <xs:group ref="cg_param_type"/>
                                                                    <xs:element name="param">
                                                                        <xs:annotation>
                                                                            <xs:documentation>
                                                                            References a predefined parameter in shader binding declarations.
                                                                            </xs:documentation>
                                                                        </xs:annotation>
                                                                        <xs:complexType>
                                                                            <xs:attribute name="ref" type="xs:NCName" use="required"/>
                                                                        </xs:complexType>
                                                                    </xs:element>
                                                                </xs:choice>
                                                                <xs:attribute name="symbol" type="xs:NCName" use="required">
                                                                    <xs:annotation>
                                                                        <xs:documentation>
                                                                        The identifier for a uniform input parameter to the shader (a formal function parameter or in-scope
                                                                        global) that will be bound to an external resource.
                                                                        </xs:documentation>
                                                                    </xs:annotation>
                                                                </xs:attribute>
                                                            </xs:complexType>
                                                        </xs:element>
                                                    </xs:sequence>
                                                    <xs:attribute name="stage" type="cg_pipeline_stage">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            In which pipeline stage this programmable shader is designed to execute, for example, VERTEX, FRAGMENT, etc.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:attribute>
                                                </xs:complexType>
                                            </xs:element>
                                        </xs:choice>
                                        <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                                    </xs:sequence>
                                    <xs:attribute name="sid" type="xs:NCName" use="optional">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The sid attribute is a text string value containing the sub-identifier of this element.
                                            This value must be unique within the scope of the parent element. Optional attribute.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:attribute>
                                </xs:complexType>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                        </xs:sequence>
                        <xs:attribute name="id" type="xs:ID">
                            <xs:annotation>
                                <xs:documentation>
                                The id attribute is a text string containing the unique identifier of this element.
                                This value must be unique within the instance document. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                        <xs:attribute name="sid" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The sid attribute is a text string value containing the sub-identifier of this element.
                                This value must be unique within the scope of the parent element. Optional attribute.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="optional">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="platform" type="xs:NCName" use="optional" default="PC">
                <xs:annotation>
                    <xs:documentation>
                    The type of platform. This is a vendor-defined character string that indicates the platform or capability target for the technique. Optional
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- COLLADA FX GLES elements                  -->
    <!-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= -->
    <!-- these maximum values are from the GL.h from Khronos. Not all of them are defined in the spec -->
    <xs:simpleType name="GLES_MAX_LIGHTS_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxExclusive value="7"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="GLES_MAX_CLIP_PLANES_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxExclusive value="5"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="GLES_MAX_TEXTURE_COORDS_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxExclusive value="8"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="GLES_MAX_TEXTURE_IMAGE_UNITS_index">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxExclusive value="31"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texenv_mode_enums">
        <xs:restriction base="xs:token">
            <xs:enumeration value="REPLACE">
                <xs:annotation>
                    <xs:appinfo>value=0x1E01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MODULATE">
                <xs:annotation>
                    <xs:appinfo>value=0x2100</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DECAL">
                <xs:annotation>
                    <xs:appinfo>value=0x2101</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="BLEND">
                <xs:annotation>
                    <xs:appinfo>value=0x0BE2</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ADD">
                <xs:annotation>
                    <xs:appinfo>value=0x0104</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="gles_texture_constant_type">
        <xs:attribute name="value" type="float4" use="optional"/>
        <xs:attribute name="param" type="xs:NCName" use="optional"/>
    </xs:complexType>
    <xs:complexType name="gles_texenv_command_type">
        <xs:sequence>
            <xs:element name="constant" type="gles_texture_constant_type" minOccurs="0"/>
        </xs:sequence>
        <xs:attribute name="operator" type="gles_texenv_mode_enums"/>
        <xs:attribute name="unit" type="xs:NCName"/>
    </xs:complexType>
    <xs:simpleType name="gles_texcombiner_operatorRGB_enums">
        <xs:restriction base="xs:token">
            <xs:enumeration value="REPLACE">
                <xs:annotation>
                    <xs:appinfo>value=0x1E01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MODULATE">
                <xs:annotation>
                    <xs:appinfo>value=0x2100</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ADD">
                <xs:annotation>
                    <xs:appinfo>value=0x0104</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ADD_SIGNED">
                <xs:annotation>
                    <xs:appinfo>value=0x8574</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INTERPOLATE">
                <xs:annotation>
                    <xs:appinfo>value=0x8575</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SUBTRACT">
                <xs:annotation>
                    <xs:appinfo>value=0x84E7</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DOT3_RGB">
                <xs:annotation>
                    <xs:appinfo>value=0x86AE</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DOT3_RGBA">
                <xs:annotation>
                    <xs:appinfo>value=0x86AF</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texcombiner_operatorAlpha_enums">
        <xs:restriction base="xs:token">
            <xs:enumeration value="REPLACE">
                <xs:annotation>
                    <xs:appinfo>value=0x1E01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="MODULATE">
                <xs:annotation>
                    <xs:appinfo>value=0x2100</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ADD">
                <xs:annotation>
                    <xs:appinfo>value=0x0104</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ADD_SIGNED">
                <xs:annotation>
                    <xs:appinfo>value=0x8574</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INTERPOLATE">
                <xs:annotation>
                    <xs:appinfo>value=0x8575</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SUBTRACT">
                <xs:annotation>
                    <xs:appinfo>value=0x84E7</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texcombiner_source_enums">
        <xs:restriction base="xs:token">
            <xs:enumeration value="TEXTURE">
                <xs:annotation>
                    <xs:appinfo>value=0x1702</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="CONSTANT">
                <xs:annotation>
                    <xs:appinfo>value=0x8576</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="PRIMARY">
                <xs:annotation>
                    <xs:appinfo>value=0x8577</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="PREVIOUS">
                <xs:annotation>
                    <xs:appinfo>value=0x8578</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texcombiner_operandRGB_enums">
        <xs:restriction base="gl_blend_type">
            <xs:enumeration value="SRC_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0300</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_SRC_COLOR">
                <xs:annotation>
                    <xs:appinfo>value=0x0301</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0302</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0303</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texcombiner_operandAlpha_enums">
        <xs:restriction base="gl_blend_type">
            <xs:enumeration value="SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0302</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ONE_MINUS_SRC_ALPHA">
                <xs:annotation>
                    <xs:appinfo>value=0x0303</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_texcombiner_argument_index_type">
        <xs:restriction base="xs:nonNegativeInteger">
            <xs:minInclusive value="0"/>
            <xs:maxInclusive value="2"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="gles_texcombiner_argumentRGB_type">
        <xs:attribute name="source" type="gles_texcombiner_source_enums"/>
        <xs:attribute name="operand" type="gles_texcombiner_operandRGB_enums" default="SRC_COLOR"/>
        <xs:attribute name="unit" type="xs:NCName" use="optional"/>
    </xs:complexType>
    <xs:complexType name="gles_texcombiner_argumentAlpha_type">
        <xs:attribute name="source" type="gles_texcombiner_source_enums"/>
        <xs:attribute name="operand" type="gles_texcombiner_operandAlpha_enums" default="SRC_ALPHA"/>
        <xs:attribute name="unit" type="xs:NCName" use="optional"/>
    </xs:complexType>
    <xs:complexType name="gles_texcombiner_commandRGB_type">
        <xs:annotation>
            <xs:documentation>
            Defines the RGB portion of a texture_pipeline command. This is a combiner-mode texturing operation.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="argument" type="gles_texcombiner_argumentRGB_type" maxOccurs="3"/>
        </xs:sequence>
        <xs:attribute name="operator" type="gles_texcombiner_operatorRGB_enums"/>
        <xs:attribute name="scale" type="xs:float" use="optional"/>
    </xs:complexType>
    <xs:complexType name="gles_texcombiner_commandAlpha_type">
        <xs:sequence>
            <xs:element name="argument" type="gles_texcombiner_argumentAlpha_type" maxOccurs="3"/>
        </xs:sequence>
        <xs:attribute name="operator" type="gles_texcombiner_operatorAlpha_enums"/>
        <xs:attribute name="scale" type="xs:float" use="optional"/>
    </xs:complexType>
    <xs:complexType name="gles_texcombiner_command_type">
        <xs:sequence>
            <xs:element name="constant" type="gles_texture_constant_type" minOccurs="0"/>
            <xs:element name="RGB" type="gles_texcombiner_commandRGB_type" minOccurs="0"/>
            <xs:element name="alpha" type="gles_texcombiner_commandAlpha_type" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
    <xs:complexType name="gles_texture_pipeline">
        <xs:annotation>
            <xs:documentation>
            Defines a set of texturing commands that will be converted into multitexturing operations using glTexEnv in regular and combiner mode.
            </xs:documentation>
        </xs:annotation>
        <xs:choice maxOccurs="unbounded">
            <xs:element name="texcombiner" type="gles_texcombiner_command_type">
                <xs:annotation>
                    <xs:documentation>
                    Defines a texture_pipeline command. This is a combiner-mode texturing operation.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="texenv" type="gles_texenv_command_type">
                <xs:annotation>
                    <xs:documentation>
                    Defines a texture_pipeline command. It is a simple noncombiner mode of texturing operations.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element ref="extra">
                <xs:annotation>
                    <xs:documentation>
                    The extra element may appear any number of times.
                    OpenGL ES extensions may be used here.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:choice>
        <xs:attribute name="sid" type="xs:NCName">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:complexType name="gles_texture_unit">
        <xs:sequence>
            <xs:element name="surface" type="xs:NCName" minOccurs="0"/>
            <xs:element name="sampler_state" type="xs:NCName" minOccurs="0"/>
            <xs:element name="texcoord" minOccurs="0">
                <xs:complexType>
                    <xs:attribute name="semantic" type="xs:NCName"/>
                </xs:complexType>
            </xs:element>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
        <xs:attribute name="sid" type="xs:NCName">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:simpleType name="gles_sampler_wrap">
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="REPEAT"/>
            <xs:enumeration value="CLAMP"/>
            <xs:enumeration value="CLAMP_TO_EDGE"/>
            <xs:enumeration value="MIRRORED_REPEAT">
                <xs:annotation>
                    <xs:documentation>
                    supported by GLES 1.1 only
                    </xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:complexType name="gles_sampler_state">
        <xs:annotation>
            <xs:documentation>
            Two-dimensional texture sampler state for profile_GLES. This is a bundle of sampler-specific states that will be referenced by one or more texture_units.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="wrap_s" type="gles_sampler_wrap" default="REPEAT" minOccurs="0"/>
            <xs:element name="wrap_t" type="gles_sampler_wrap" default="REPEAT" minOccurs="0"/>
            <xs:element name="minfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="magfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipfilter" type="fx_sampler_filter_common" default="NONE" minOccurs="0"/>
            <xs:element name="mipmap_maxlevel" type="xs:unsignedByte" default="255" minOccurs="0"/>
            <!-- perhaps bias not really supported but can be kludged in the app somewhat-->
            <xs:element name="mipmap_bias" type="xs:float" default="0.0" minOccurs="0"/>
            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>
                    The extra element may appear any number of times.
                    OpenGL ES extensions may be used here.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
        </xs:sequence>
        <xs:attribute name="sid" type="xs:NCName">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element. Optional attribute.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:simpleType name="gles_stencil_op_type">
        <xs:restriction base="xs:string">
            <xs:enumeration value="KEEP">
                <xs:annotation>
                    <xs:appinfo>value=0x1E00</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="ZERO">
                <xs:annotation>
                    <xs:appinfo>value=0x0</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="REPLACE">
                <xs:annotation>
                    <xs:appinfo>value=0x1E01</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INCR">
                <xs:annotation>
                    <xs:appinfo>value=0x1E02</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="DECR">
                <xs:annotation>
                    <xs:appinfo>value=0x1E03</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="INVERT">
                <xs:annotation>
                    <xs:appinfo>value=0x150A</xs:appinfo>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="gles_enumeration">
        <xs:union memberTypes="gl_blend_type gl_face_type gl_func_type gl_stencil_op_type gl_material_type gl_fog_type gl_front_face_type gl_light_model_color_control_type gl_logic_op_type gl_polygon_mode_type gl_shade_model_type"/>
    </xs:simpleType>
    <xs:group name="gles_pipeline_settings">
        <xs:annotation>
            <xs:documentation>
            A group that contains the renderstates available for the GLES profile.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="alpha_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="func">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="value">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_alpha_value_type" use="optional" default="0.0"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="src">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ONE"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="dest">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_blend_type" use="optional" default="ZERO"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_stencil">
                <xs:complexType>
                    <xs:attribute name="value" type="int" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clear_depth">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clip_plane">
                <xs:complexType>
                    <xs:attribute name="value" type="bool4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_CLIP_PLANES_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="bool4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="cull_face">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_face_type" use="optional" default="BACK"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_func">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_range">
                <xs:complexType>
                    <xs:attribute name="value" type="float2" use="optional" default="0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_color">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_density">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_mode">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_fog_type" use="optional" default="EXP"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_start">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_end">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="front_face">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_front_face_type" use="optional" default="CCW"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture_pipeline">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="value" type="gles_texture_pipeline" minOccurs="0"/>
                    </xs:sequence>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="logic_op">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_logic_op_type" use="optional" default="COPY"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_diffuse">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_specular">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_position">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 1 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_constant_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_linear_attenutation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_quadratic_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_cutoff">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="180"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_direction">
                <xs:complexType>
                    <xs:attribute name="value" type="float3" use="optional" default="0 0 -1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_spot_exponent">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.2 0.2 0.2 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_width">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_ambient">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.2 0.2 0.2 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_diffuse">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0.8 0.8 0.8 1.0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_emission">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_shininess">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="material_specular">
                <xs:complexType>
                    <xs:attribute name="value" type="float4" use="optional" default="0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="model_view_matrix">
                <xs:complexType>
                    <xs:attribute name="value" type="float4x4" use="optional" default="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_distance_attenuation">
                <xs:complexType>
                    <xs:attribute name="value" type="float3" use="optional" default="1 0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_fade_threshold_size">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size_min">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_size_max">
                <xs:complexType>
                    <xs:attribute name="value" type="float" use="optional" default="1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset">
                <xs:complexType>
                    <xs:attribute name="value" type="float2" use="optional" default="0 0"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="projection_matrix">
                <xs:complexType>
                    <xs:attribute name="value" type="float4x4" use="optional" default="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="scissor">
                <xs:complexType>
                    <xs:attribute name="value" type="int4" use="optional"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="shade_model">
                <xs:complexType>
                    <xs:attribute name="value" type="gl_shade_model_type" use="optional" default="SMOOTH"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_func">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="func">
                            <xs:complexType>
                                <xs:attribute name="value" type="gl_func_type" use="optional" default="ALWAYS"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="ref">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="0"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="mask">
                            <xs:complexType>
                                <xs:attribute name="value" type="xs:unsignedByte" use="optional" default="255"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_mask">
                <xs:complexType>
                    <xs:attribute name="value" type="int" use="optional" default="4294967295"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_op">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="fail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gles_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zfail">
                            <xs:complexType>
                                <xs:attribute name="value" type="gles_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                        <xs:element name="zpass">
                            <xs:complexType>
                                <xs:attribute name="value" type="gles_stencil_op_type" use="optional" default="KEEP"/>
                                <xs:attribute name="param" type="xs:NCName" use="optional"/>
                            </xs:complexType>
                        </xs:element>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
            <xs:element name="alpha_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="blend_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="clip_plane_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_CLIP_PLANES_index"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_logic_op_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="color_material_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="true"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="cull_face_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="depth_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="dither_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="fog_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="texture_pipeline_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                    <xs:attribute name="index" type="GLES_MAX_LIGHTS_index" use="required"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="lighting_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="light_model_two_side_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="line_smooth_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="multisample_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="normalize_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="point_smooth_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="polygon_offset_fill_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="rescale_normal_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_alpha_to_coverage_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_alpha_to_one_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="sample_coverage_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="scissor_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
            <xs:element name="stencil_test_enable">
                <xs:complexType>
                    <xs:attribute name="value" type="bool" use="optional" default="false"/>
                    <xs:attribute name="param" type="xs:NCName" use="optional"/>
                </xs:complexType>
            </xs:element>
        </xs:choice>
    </xs:group>
    <!-- - - - - - - - - - - - - - - - - - - - -->
    <xs:group name="gles_basic_type_common">
        <xs:annotation>
            <xs:documentation>
            A group that defines the available variable types for GLES parameters.
            </xs:documentation>
        </xs:annotation>
        <xs:choice>
            <xs:element name="bool" type="bool"/>
            <xs:element name="bool2" type="bool2"/>
            <xs:element name="bool3" type="bool3"/>
            <xs:element name="bool4" type="bool4"/>
            <xs:element name="int" type="int"/>
            <xs:element name="int2" type="int2"/>
            <xs:element name="int3" type="int3"/>
            <xs:element name="int4" type="int4"/>
            <xs:element name="float" type="float"/>
            <xs:element name="float2" type="float2"/>
            <xs:element name="float3" type="float3"/>
            <xs:element name="float4" type="float4"/>
            <xs:element name="float1x1" type="float"/>
            <xs:element name="float1x2" type="float2"/>
            <xs:element name="float1x3" type="float3"/>
            <xs:element name="float1x4" type="float4"/>
            <xs:element name="float2x1" type="float2"/>
            <xs:element name="float2x2" type="float2x2"/>
            <xs:element name="float2x3" type="float2x3"/>
            <xs:element name="float2x4" type="float2x4"/>
            <xs:element name="float3x1" type="float3"/>
            <xs:element name="float3x2" type="float3x2"/>
            <xs:element name="float3x3" type="float3x3"/>
            <xs:element name="float3x4" type="float3x4"/>
            <xs:element name="float4x1" type="float4"/>
            <xs:element name="float4x2" type="float4x2"/>
            <xs:element name="float4x3" type="float4x3"/>
            <xs:element name="float4x4" type="float4x4"/>
            <xs:element name="surface" type="fx_surface_common"/>
            <xs:element name="texture_pipeline" type="gles_texture_pipeline"/>
            <xs:element name="sampler_state" type="gles_sampler_state"/>
            <xs:element name="texture_unit" type="gles_texture_unit"/>
            <xs:element name="enum" type="gles_enumeration"/>
        </xs:choice>
    </xs:group>
    <xs:complexType name="gles_newparam">
        <xs:annotation>
            <xs:documentation>
            Create a new, named param object in the GLES Runtime, assign it a type, an initial value, and additional attributes at declaration time.
            </xs:documentation>
        </xs:annotation>
        <xs:sequence>
            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded">
                <xs:annotation>
                    <xs:documentation>
                    The annotate element allows you to specify an annotation for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="semantic" type="xs:NCName" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The semantic element allows you to specify a semantic for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:element name="modifier" type="fx_modifier_enum_common" minOccurs="0">
                <xs:annotation>
                    <xs:documentation>
                    The modifier element allows you to specify a modifier for this new param.
                    </xs:documentation>
                </xs:annotation>
            </xs:element>
            <xs:group ref="gles_basic_type_common"/>
        </xs:sequence>
        <xs:attribute name="sid" type="xs:NCName" use="required">
            <xs:annotation>
                <xs:documentation>
                The sid attribute is a text string value containing the sub-identifier of this element.
                This value must be unique within the scope of the parent element.
                </xs:documentation>
            </xs:annotation>
        </xs:attribute>
    </xs:complexType>
    <xs:simpleType name="gles_rendertarget_common">
        <xs:restriction base="xs:NCName"/>
    </xs:simpleType>
    <xs:element name="profile_GLES" substitutionGroup="fx_profile_abstract">
        <xs:annotation>
            <xs:documentation>
            Opens a block of GLES platform-specific data types and technique declarations.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0"/>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="image"/>
                    <xs:element name="newparam" type="gles_newparam"/>
                </xs:choice>
                <xs:element name="technique" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        Holds a description of the textures, samplers, shaders, parameters, and passes necessary for rendering this effect using one method.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element ref="asset" minOccurs="0"/>
                            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                            <xs:choice minOccurs="0" maxOccurs="unbounded">
                                <xs:element ref="image"/>
                                <xs:element name="newparam" type="gles_newparam"/>
                                <xs:element name="setparam">
                                    <xs:complexType>
                                        <xs:sequence>
                                            <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                            <xs:group ref="gles_basic_type_common"/>
                                        </xs:sequence>
                                        <xs:attribute name="ref" type="xs:NCName" use="required"/>
                                    </xs:complexType>
                                </xs:element>
                            </xs:choice>
                            <xs:element name="pass" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    A static declaration of all the render states, shaders, and settings for one rendering pipeline.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="annotate" type="fx_annotate_common" minOccurs="0" maxOccurs="unbounded"/>
                                        <xs:element name="color_target" type="gles_rendertarget_common" minOccurs="0"/>
                                        <xs:element name="depth_target" type="gles_rendertarget_common" minOccurs="0"/>
                                        <xs:element name="stencil_target" type="gles_rendertarget_common" minOccurs="0"/>
                                        <xs:element name="color_clear" type="fx_color_common" minOccurs="0"/>
                                        <xs:element name="depth_clear" type="float" minOccurs="0"/>
                                        <xs:element name="stencil_clear" type="xs:byte" minOccurs="0"/>
                                        <xs:element name="draw" type="fx_draw_common" minOccurs="0"/>
                                        <xs:choice minOccurs="0" maxOccurs="unbounded">
                                            <xs:group ref="gles_pipeline_settings"/>
                                        </xs:choice>
                                        <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                                    </xs:sequence>
                                    <xs:attribute name="sid" type="xs:NCName" use="optional">
                                        <xs:annotation>
                                            <xs:documentation>
                                            The sid attribute is a text string value containing the sub-identifier of this element.
                                            This value must be unique within the scope of the parent element. Optional attribute.
                                            </xs:documentation>
                                        </xs:annotation>
                                    </xs:attribute>
                                </xs:complexType>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
                        </xs:sequence>
                        <xs:attribute name="id" type="xs:ID"/>
                        <xs:attribute name="sid" type="xs:NCName" use="required">
                            <xs:annotation>
                                <xs:documentation>
                                The sid attribute is a text string value containing the sub-identifier of this element.
                                This value must be unique within the scope of the parent element.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID" use="optional">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="platform" type="xs:NCName" use="optional" default="PC">
                <xs:annotation>
                    <xs:documentation>
                    The type of platform. This is a vendor-defined character string that indicates the platform or capability target for the technique. Optional
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- COLLADA Physics -->
    <!-- new geometry types -->
    <xs:element name="box">
        <xs:annotation>
            <xs:documentation>
            An axis-aligned, centered box primitive.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="half_extents" type="float3">
                    <xs:annotation>
                        <xs:documentation>
                        3 float values that represent the extents of the box
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="plane">
        <xs:annotation>
            <xs:documentation>
            An infinite plane primitive.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="equation" type="float4">
                    <xs:annotation>
                        <xs:documentation>
                        4 float values that represent the coefficients for the plane’s equation:    Ax + By + Cz + D = 0
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="sphere">
        <xs:annotation>
            <xs:documentation>
            A centered sphere primitive.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="radius" type="float">
                    <xs:annotation>
                        <xs:documentation>
                        A float value that represents the radius of the sphere
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="ellipsoid">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="size" type="float3"/>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="cylinder">
        <xs:annotation>
            <xs:documentation>
            A cylinder primitive that is centered on, and aligned with. the local Y axis.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="height" type="float">
                    <xs:annotation>
                        <xs:documentation>
                        A float value that represents the length of the cylinder along the Y axis.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        float2 values that represent the radii of the cylinder.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="tapered_cylinder">
        <xs:annotation>
            <xs:documentation>
            A tapered cylinder primitive that is centered on and aligned with the local Y axis.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="height" type="float">
                    <xs:annotation>
                        <xs:documentation>
                        A float value that represents the length of the cylinder along the Y axis.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius1" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        Two float values that represent the radii of the tapered cylinder at the positive (height/2)
                        Y value. Both ends of the tapered cylinder may be elliptical.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius2" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        Two float values that represent the radii of the tapered cylinder at the negative (height/2)
                        Y value.Both ends of the tapered cylinder may be elliptical.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="capsule">
        <xs:annotation>
            <xs:documentation>
            A capsule primitive that is centered on and aligned with the local Y axis.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="height" type="float">
                    <xs:annotation>
                        <xs:documentation>
                        A float value that represents the length of the line segment connecting the centers
                        of the capping hemispheres.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        Two float values that represent the radii of the capsule (it may be elliptical)
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="tapered_capsule">
        <xs:annotation>
            <xs:documentation>
            A tapered capsule primitive that is centered on, and aligned with, the local Y axis.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="height" type="float">
                    <xs:annotation>
                        <xs:documentation>
                        A float value that represents the length of the line segment connecting the centers of the
                        capping hemispheres.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius1" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        Two float values that represent the radii of the tapered capsule at the positive (height/2)
                        Y value.Both ends of the tapered capsule may be elliptical.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="radius2" type="float2">
                    <xs:annotation>
                        <xs:documentation>
                        Two float values that represent the radii of the tapered capsule at the negative (height/2)
                        Y value.Both ends of the tapered capsule may be elliptical.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
    <xs:element name="convex_mesh">
        <xs:annotation>
            <xs:documentation>
            The definition of the convex_mesh element is identical to the mesh element with the exception that
            instead of a complete description (source, vertices, polygons etc.), it may simply point to another
            geometry to derive its shape. The latter case means that the convex hull of that geometry should
            be computed and is indicated by the optional “convex_hull_of” attribute.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence minOccurs="0">
                <xs:element ref="source" maxOccurs="unbounded"/>
                <xs:element ref="vertices"/>
                <xs:choice minOccurs="0" maxOccurs="unbounded">
                    <xs:element ref="lines"/>
                    <xs:element ref="linestrips"/>
                    <xs:element ref="polygons"/>
                    <xs:element ref="polylist"/>
                    <xs:element ref="triangles"/>
                    <xs:element ref="trifans"/>
                    <xs:element ref="tristrips"/>
                </xs:choice>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="convex_hull_of" type="xs:anyURI">
                <xs:annotation>
                    <xs:documentation>
                    The convex_hull_of attribute is a URI string of geometry to compute the convex hull of.
                    Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- physics object elements -->
    <xs:element name="force_field">
        <xs:annotation>
            <xs:documentation>
            A general container for force-fields. At the moment, it only has techniques and extra elements.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The force_field element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="technique" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element must contain at least one non-common profile technique.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element. This value
                    must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="physics_material">
        <xs:annotation>
            <xs:documentation>
            This element defines the physical properties of an object. It contains a technique/profile with
            parameters. The COMMON profile defines the built-in names, such as static_friction.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_material element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the physics_material information for the common profile
                        which all COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="dynamic_friction" type="TargetableFloat" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Dynamic friction coefficient
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="restitution" type="TargetableFloat" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The proportion of the kinetic energy preserved in the impact (typically ranges from 0.0 to 1.0)
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="static_friction" type="TargetableFloat" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Static friction coefficient
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="physics_scene">
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_scene element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_force_field" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There may be any number of instance_force_field elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_physics_model" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        There may be any number of instance_physics_model elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the physics_scene information for the common profile
                        which all COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="gravity" type="TargetableFloat3" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The gravity vector to use for the physics_scene.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="time_step" type="TargetableFloat" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The time_step for the physics_scene.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:simpleType name="SpringType">
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="LINEAR"/>
            <xs:enumeration value="ANGULAR"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:element name="rigid_body">
        <xs:annotation>
            <xs:documentation>
            This element allows for describing simulated bodies that do not deform. These bodies may or may
            not be connected by constraints (hinge, ball-joint etc.).  Rigid-bodies, constraints etc. are
            encapsulated in physics_model elements to allow for instantiating complex models.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the rigid_body information for the common profile which all
                        COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="dynamic" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    If false, the rigid_body is not moveable
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:simpleContent>
                                        <xs:extension base="bool">
                                            <xs:attribute name="sid" type="xs:NCName">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    The sid attribute is a text string value containing the sub-identifier of this element.
                                                    This value must be unique within the scope of the parent element. Optional attribute.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:attribute>
                                        </xs:extension>
                                    </xs:simpleContent>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="mass" type="TargetableFloat" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The total mass of the rigid-body
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element name="mass_frame" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Defines the center and orientation of mass of the rigid-body relative to the local origin of the
                                    “root” shape.This makes the off-diagonal elements of the inertia tensor (products of inertia) all
                                    0 and allows us to just store the diagonal elements (moments of inertia).
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:choice maxOccurs="unbounded">
                                        <xs:element ref="translate"/>
                                        <xs:element ref="rotate"/>
                                    </xs:choice>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="inertia" type="TargetableFloat3" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    float3 – The diagonal elements of the inertia tensor (moments of inertia), which is represented
                                    in the local frame of the center of mass. See above.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:choice minOccurs="0">
                                <xs:element ref="instance_physics_material">
                                    <xs:annotation>
                                        <xs:documentation>
                                        References a physics_material for the rigid_body.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                                <xs:element ref="physics_material">
                                    <xs:annotation>
                                        <xs:documentation>
                                        Defines a physics_material for the rigid_body.
                                        </xs:documentation>
                                    </xs:annotation>
                                </xs:element>
                            </xs:choice>
                            <xs:element name="shape" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    This element allows for describing components of a rigid_body.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="hollow" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                If true, the mass is distributed along the surface of the shape
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:simpleContent>
                                                    <xs:extension base="bool">
                                                        <xs:attribute name="sid" type="xs:NCName">
                                                            <xs:annotation>
                                                                <xs:documentation>
                                                                The sid attribute is a text string value containing the sub-identifier of this element.
                                                                This value must be unique within the scope of the parent element. Optional attribute.
                                                                </xs:documentation>
                                                            </xs:annotation>
                                                        </xs:attribute>
                                                    </xs:extension>
                                                </xs:simpleContent>
                                            </xs:complexType>
                                        </xs:element>
                                        <xs:element name="mass" type="TargetableFloat" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The mass of the shape.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:element name="density" type="TargetableFloat" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The density of the shape.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                        <xs:choice minOccurs="0">
                                            <xs:element ref="instance_physics_material">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    References a physics_material for the shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="physics_material">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a physics_material for the shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                        </xs:choice>
                                        <xs:choice>
                                            <xs:element ref="instance_geometry">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Instances a geometry to use to define this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="plane">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a plane to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="box">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a box to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="sphere">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a sphere to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="cylinder">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a cyliner to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="tapered_cylinder">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a tapered_cylinder to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="capsule">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a capsule to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="tapered_capsule">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Defines a tapered_capsule to use for this shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                        </xs:choice>
                                        <xs:choice minOccurs="0" maxOccurs="unbounded">
                                            <xs:element ref="translate">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Allows a tranformation for the shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                            <xs:element ref="rotate">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    Allows a tranformation for the shape.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:element>
                                        </xs:choice>
                                        <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The extra element may appear any number of times.
                                                </xs:documentation>
                                            </xs:annotation>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="sid" type="xs:NCName" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element. This
                    value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="rigid_constraint">
        <xs:annotation>
            <xs:documentation>
            This element allows for connecting components, such as rigid_body into complex physics models
            with moveable parts.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element name="ref_attachment">
                    <xs:annotation>
                        <xs:documentation>
                        Defines the attachment (to a rigid_body or a node) to be used as the reference-frame.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:choice minOccurs="0" maxOccurs="unbounded">
                            <xs:element ref="translate">
                                <xs:annotation>
                                    <xs:documentation>
                                    Allows you to "position" the attachment point.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="rotate">
                                <xs:annotation>
                                    <xs:documentation>
                                    Allows you to "position" the attachment point.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:choice>
                        <xs:attribute name="rigid_body" type="xs:anyURI">
                            <xs:annotation>
                                <xs:documentation>
                                The “rigid_body” attribute is a relative reference to a rigid-body within the same
                                physics_model.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element name="attachment">
                    <xs:annotation>
                        <xs:documentation>
                        Defines an attachment to a rigid-body or a node.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:choice minOccurs="0" maxOccurs="unbounded">
                            <xs:element ref="translate">
                                <xs:annotation>
                                    <xs:documentation>
                                    Allows you to "position" the attachment point.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="rotate">
                                <xs:annotation>
                                    <xs:documentation>
                                    Allows you to "position" the attachment point.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                            <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                                <xs:annotation>
                                    <xs:documentation>
                                    The extra element may appear any number of times.
                                    </xs:documentation>
                                </xs:annotation>
                            </xs:element>
                        </xs:choice>
                        <xs:attribute name="rigid_body" type="xs:anyURI">
                            <xs:annotation>
                                <xs:documentation>
                                The “rigid_body” attribute is a relative reference to a rigid-body within the same physics_model.
                                </xs:documentation>
                            </xs:annotation>
                        </xs:attribute>
                    </xs:complexType>
                </xs:element>
                <xs:element name="technique_common">
                    <xs:annotation>
                        <xs:documentation>
                        The technique_common element specifies the rigid_constraint information for the common profile
                        which all COLLADA implementations need to support.
                        </xs:documentation>
                    </xs:annotation>
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="enabled" default="true" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    If false, the constraint doesn’t exert any force or influence on the rigid bodies.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:simpleContent>
                                        <xs:extension base="bool">
                                            <xs:attribute name="sid" type="xs:NCName">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    The sid attribute is a text string value containing the sub-identifier of this element.
                                                    This value must be unique within the scope of the parent element. Optional attribute.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:attribute>
                                        </xs:extension>
                                    </xs:simpleContent>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="interpenetrate" default="false" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Indicates whether the attached rigid bodies may inter-penetrate.
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:simpleContent>
                                        <xs:extension base="bool">
                                            <xs:attribute name="sid" type="xs:NCName">
                                                <xs:annotation>
                                                    <xs:documentation>
                                                    The sid attribute is a text string value containing the sub-identifier of this element.
                                                    This value must be unique within the scope of the parent element. Optional attribute.
                                                    </xs:documentation>
                                                </xs:annotation>
                                            </xs:attribute>
                                        </xs:extension>
                                    </xs:simpleContent>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="limits" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    The limits element provides a flexible way to specify the constraint limits (degrees of freedom
                                    and ranges).
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="swing_cone_and_twist" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The swing_cone_and_twist element describes the angular limits along each rotation axis in degrees.
                                                The the X and Y limits describe a “swing cone” and the Z limits describe the “twist angle” range
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:element name="min" type="TargetableFloat3" default="0.0 0.0 0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The minimum values for the limit.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="max" type="TargetableFloat3" default="0.0 0.0 0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The maximum values for the limit.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                        <xs:element name="linear" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The linear element describes linear (translational) limits along each axis.
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:element name="min" type="TargetableFloat3" default="0.0 0.0 0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The minimum values for the limit.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="max" type="TargetableFloat3" default="0.0 0.0 0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The maximum values for the limit.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                            <xs:element name="spring" minOccurs="0">
                                <xs:annotation>
                                    <xs:documentation>
                                    Spring, based on distance (“LINEAR”) or angle (“ANGULAR”).
                                    </xs:documentation>
                                </xs:annotation>
                                <xs:complexType>
                                    <xs:sequence>
                                        <xs:element name="angular" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The angular spring properties.
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:element name="stiffness" type="TargetableFloat" default="1.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The stiffness (also called spring coefficient) has units of force/angle in degrees.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="damping" type="TargetableFloat" default="0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The spring damping coefficient.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="target_value" type="TargetableFloat" default="0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The spring's target or resting distance.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                        <xs:element name="linear" minOccurs="0">
                                            <xs:annotation>
                                                <xs:documentation>
                                                The linear spring properties.
                                                </xs:documentation>
                                            </xs:annotation>
                                            <xs:complexType>
                                                <xs:sequence>
                                                    <xs:element name="stiffness" type="TargetableFloat" default="1.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The stiffness (also called spring coefficient) has units of force/distance.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="damping" type="TargetableFloat" default="0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The spring damping coefficient.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                    <xs:element name="target_value" type="TargetableFloat" default="0.0" minOccurs="0">
                                                        <xs:annotation>
                                                            <xs:documentation>
                                                            The spring's target or resting distance.
                                                            </xs:documentation>
                                                        </xs:annotation>
                                                    </xs:element>
                                                </xs:sequence>
                                            </xs:complexType>
                                        </xs:element>
                                    </xs:sequence>
                                </xs:complexType>
                            </xs:element>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
                <xs:element ref="technique" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        This element may contain any number of non-common profile techniques.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="sid" type="xs:NCName" use="required">
                <xs:annotation>
                    <xs:documentation>
                    The sid attribute is a text string value containing the sub-identifier of this element.
                    This value must be unique within the scope of the parent element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <xs:element name="physics_model">
        <xs:annotation>
            <xs:documentation>
            This element allows for building complex combinations of rigid-bodies and constraints that
            may be instantiated multiple times.
            </xs:documentation>
        </xs:annotation>
        <xs:complexType>
            <xs:sequence>
                <xs:element ref="asset" minOccurs="0">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_model element may contain an asset element.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="rigid_body" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_model may define any number of rigid_body elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="rigid_constraint" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_model may define any number of rigid_constraint elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="instance_physics_model" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The physics_model may instance any number of other physics_model elements.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
                <xs:element ref="extra" minOccurs="0" maxOccurs="unbounded">
                    <xs:annotation>
                        <xs:documentation>
                        The extra element may appear any number of times.
                        </xs:documentation>
                    </xs:annotation>
                </xs:element>
            </xs:sequence>
            <xs:attribute name="id" type="xs:ID">
                <xs:annotation>
                    <xs:documentation>
                    The id attribute is a text string containing the unique identifier of this element.
                    This value must be unique within the instance document. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
            <xs:attribute name="name" type="xs:NCName">
                <xs:annotation>
                    <xs:documentation>
                    The name attribute is the text string name of this element. Optional attribute.
                    </xs:documentation>
                </xs:annotation>
            </xs:attribute>
        </xs:complexType>
    </xs:element>
    <!-- COMMON Profile Types -->
    <xs:simpleType name="Common_profile_input">
        <xs:annotation>
            <xs:appinfo>constant-strings</xs:appinfo>
        </xs:annotation>
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="BINORMAL"/>
            <xs:enumeration value="COLOR"/>
            <xs:enumeration value="CONTINUITY"/>
            <xs:enumeration value="IMAGE"/>
            <xs:enumeration value="IN_TANGENT"/>
            <xs:enumeration value="INPUT"/>
            <xs:enumeration value="INTERPOLATION"/>
            <xs:enumeration value="INV_BIND_MATRIX"/>
            <xs:enumeration value="JOINT"/>
            <xs:enumeration value="LINEAR_STEPS"/>
            <xs:enumeration value="MORPH_TARGET"/>
            <xs:enumeration value="MORPH_WEIGHT"/>
            <xs:enumeration value="NORMAL"/>
            <xs:enumeration value="OUTPUT"/>
            <xs:enumeration value="OUT_TANGENT"/>
            <xs:enumeration value="POSITION"/>
            <xs:enumeration value="TANGENT"/>
            <xs:enumeration value="TEXBINORMAL"/>
            <xs:enumeration value="TEXCOORD"/>
            <xs:enumeration value="TEXTANGENT"/>
            <xs:enumeration value="UV"/>
            <xs:enumeration value="VERTEX"/>
            <xs:enumeration value="WEIGHT"/>
        </xs:restriction>
    </xs:simpleType>
    <xs:simpleType name="Common_profile_param">
        <xs:annotation>
            <xs:appinfo>constant-strings</xs:appinfo>
        </xs:annotation>
        <xs:restriction base="xs:NMTOKEN">
            <xs:enumeration value="A"/>
            <xs:enumeration value="ANGLE"/>
            <xs:enumeration value="B"/>
            <xs:enumeration value="DOUBLE_SIDED"/>
            <xs:enumeration value="G"/>
            <xs:enumeration value="P"/>
            <xs:enumeration value="Q"/>
            <xs:enumeration value="R"/>
            <xs:enumeration value="S"/>
            <xs:enumeration value="T"/>
            <xs:enumeration value="TIME"/>
            <xs:enumeration value="U"/>
            <xs:enumeration value="V"/>
            <xs:enumeration value="W"/>
            <xs:enumeration value="X"/>
            <xs:enumeration value="Y"/>
            <xs:enumeration value="Z"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>"""

XML_XSD = """<?xml version='1.0'?>
<!DOCTYPE xs:schema PUBLIC "-//W3C//DTD XMLSCHEMA 200102//EN" "XMLSchema.dtd" >
<xs:schema targetNamespace="http://www.w3.org/XML/1998/namespace" xmlns:xs="http://www.w3.org/2001/XMLSchema" xml:lang="en">

 <xs:annotation>
  <xs:documentation>
   See http://www.w3.org/XML/1998/namespace.html and
   http://www.w3.org/TR/REC-xml for information about this namespace.

    This schema document describes the XML namespace, in a form
    suitable for import by other schema documents.

    Note that local names in this namespace are intended to be defined
    only by the World Wide Web Consortium or its subgroups.  The
    following names are currently defined in this namespace and should
    not be used with conflicting semantics by any Working Group,
    specification, or document instance:

    base (as an attribute name): denotes an attribute whose value
         provides a URI to be used as the base for interpreting any
         relative URIs in the scope of the element on which it
         appears; its value is inherited.  This name is reserved
         by virtue of its definition in the XML Base specification.

    lang (as an attribute name): denotes an attribute whose value
         is a language code for the natural language of the content of
         any element; its value is inherited.  This name is reserved
         by virtue of its definition in the XML specification.

    space (as an attribute name): denotes an attribute whose
         value is a keyword indicating what whitespace processing
         discipline is intended for the content of the element; its
         value is inherited.  This name is reserved by virtue of its
         definition in the XML specification.

    Father (in any context at all): denotes Jon Bosak, the chair of
         the original XML Working Group.  This name is reserved by
         the following decision of the W3C XML Plenary and
         XML Coordination groups:

             In appreciation for his vision, leadership and dedication
             the W3C XML Plenary on this 10th day of February, 2000
             reserves for Jon Bosak in perpetuity the XML name
             xml:Father
  </xs:documentation>
 </xs:annotation>

 <xs:annotation>
  <xs:documentation>This schema defines attributes and an attribute group
        suitable for use by
        schemas wishing to allow xml:base, xml:lang or xml:space attributes
        on elements they define.

        To enable this, such a schema must import this schema
        for the XML namespace, e.g. as follows:
        &lt;schema . . .>
         . . .
         &lt;import namespace="http://www.w3.org/XML/1998/namespace"
                    schemaLocation="http://www.w3.org/2001/03/xml.xsd"/>

        Subsequently, qualified reference to any of the attributes
        or the group defined below will have the desired effect, e.g.

        &lt;type . . .>
         . . .
         &lt;attributeGroup ref="xml:specialAttrs"/>

         will define a type which will schema-validate an instance
         element with any of those attributes</xs:documentation>
 </xs:annotation>

 <xs:annotation>
  <xs:documentation>In keeping with the XML Schema WG's standard versioning
   policy, this schema document will persist at
   http://www.w3.org/2001/03/xml.xsd.
   At the date of issue it can also be found at
   http://www.w3.org/2001/xml.xsd.
   The schema document at that URI may however change in the future,
   in order to remain compatible with the latest version of XML Schema
   itself.  In other words, if the XML Schema namespace changes, the version
   of this document at
   http://www.w3.org/2001/xml.xsd will change
   accordingly; the version at
   http://www.w3.org/2001/03/xml.xsd will not change.
  </xs:documentation>
 </xs:annotation>

 <xs:attribute name="lang" type="xs:language">
  <xs:annotation>
   <xs:documentation>In due course, we should install the relevant ISO 2- and 3-letter
         codes as the enumerated possible values . . .</xs:documentation>
  </xs:annotation>
 </xs:attribute>

 <xs:attribute name="space" default="preserve">
  <xs:simpleType>
   <xs:restriction base="xs:NCName">
    <xs:enumeration value="default"/>
    <xs:enumeration value="preserve"/>
   </xs:restriction>
  </xs:simpleType>
 </xs:attribute>

 <xs:attribute name="base" type="xs:anyURI">
  <xs:annotation>
   <xs:documentation>See http://www.w3.org/TR/xmlbase/ for
                     information about this attribute.</xs:documentation>
  </xs:annotation>
 </xs:attribute>

 <xs:attributeGroup name="specialAttrs">
  <xs:attribute ref="xml:base"/>
  <xs:attribute ref="xml:lang"/>
  <xs:attribute ref="xml:space"/>
 </xs:attributeGroup>

</xs:schema>
"""

class ColladaResolver(lxml.etree.Resolver):
    """COLLADA XML Resolver. If a known URL referenced
    from the COLLADA spec is resolved, a cached local
    copy is returned instead of initiating a network
    request"""
    def resolve(self, url, id, context):
        """Currently Resolves:
         * http://www.w3.org/2001/03/xml.xsd
        """
        if url == 'http://www.w3.org/2001/03/xml.xsd':
            return self.resolve_string(XML_XSD, context)
        else:
            return None


class ColladaValidator(object):
    """Validates a collada lxml document"""

    def __init__(self):
        """Initializes the validator"""
        self.COLLADA_SCHEMA_1_4_1_DOC = None
        self._COLLADA_SCHEMA_1_4_1_INSTANCE = None

    def _getColladaSchemaInstance(self):
        if self._COLLADA_SCHEMA_1_4_1_INSTANCE is None:
            self._parser = lxml.etree.XMLParser()
            self._parser.resolvers.add(ColladaResolver())
            self.COLLADA_SCHEMA_1_4_1_DOC = lxml.etree.parse(
                    BytesIO(bytes(COLLADA_SCHEMA_1_4_1, encoding='utf-8')),
                    self._parser)
            self._COLLADA_SCHEMA_1_4_1_INSTANCE = lxml.etree.XMLSchema(
                    self.COLLADA_SCHEMA_1_4_1_DOC)
        return self._COLLADA_SCHEMA_1_4_1_INSTANCE

    COLLADA_SCHEMA_1_4_1_INSTANCE = property(_getColladaSchemaInstance)
    """An instance of lxml.XMLSchema that can be used to validate"""

    def validate(self, *args, **kwargs):
        """A wrapper for lxml.XMLSchema.validate"""
        return self.COLLADA_SCHEMA_1_4_1_INSTANCE.validate(*args, **kwargs)


########NEW FILE########
__FILENAME__ = source
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module for managing data sources defined in geometry tags."""

import numpy

from collada.common import DaeObject, E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, DaeMalformedError
from collada.xmlutil import etree as ElementTree

class InputList(object):
    """Used for defining input sources to a geometry."""

    class Input:
        def __init__(self, offset, semantic, src, set=None):
            self.offset = offset
            self.semantic = semantic
            self.source = src
            self.set = set

    semantics = ["VERTEX", "NORMAL", "TEXCOORD", "TEXBINORMAL", "TEXTANGENT", "COLOR", "TANGENT", "BINORMAL"]

    def __init__(self):
        """Create an input list"""
        self.inputs = {}
        for s in self.semantics:
            self.inputs[s] = []

    def addInput(self, offset, semantic, src, set=None):
        """Add an input source to this input list.

        :param int offset:
          Offset for this source within the geometry's indices
        :param str semantic:
          The semantic for the input source. Currently supported options are:
            * VERTEX
            * NORMAL
            * TEXCOORD
            * TEXBINORMAL
            * TEXTANGENT
            * COLOR
            * TANGENT
            * BINORMAL
        :param str src:
          A string identifier of the form `#srcid` where `srcid` is a source
          within the geometry's :attr:`~collada.geometry.Geometry.sourceById` array.
        :param str set:
          Indicates a set number for the source. This is used, for example,
          when there are multiple texture coordinate sets.

        """
        if semantic not in self.semantics:
            raise DaeUnsupportedError("Unsupported semantic %s" % semantic)
        self.inputs[semantic].append(self.Input(offset, semantic, src, set))

    def getList(self):
        """Returns a list of tuples of the source in the form (offset, semantic, source, set)"""
        retlist = []
        for inplist in self.inputs.values():
            for inp in inplist:
                 retlist.append((inp.offset, inp.semantic, inp.source, inp.set))
        return retlist

    def __str__(self): return '<InputList>'
    def __repr__(self): return str(self)

class Source(DaeObject):
    """Abstract class for loading source arrays"""

    @staticmethod
    def load(collada, localscope, node):
        sourceid = node.get('id')
        arraynode = node.find(tag('float_array'))
        if not arraynode is None:
            return FloatSource.load(collada, localscope, node)

        arraynode = node.find(tag('IDREF_array'))
        if not arraynode is None:
            return IDRefSource.load(collada, localscope, node)

        arraynode = node.find(tag('Name_array'))
        if not arraynode is None:
            return NameSource.load(collada, localscope, node)

        if arraynode is None: raise DaeIncompleteError('No array found in source %s' % sourceid)


class FloatSource(Source):
    """Contains a source array of floats, as defined in the collada
    <float_array> inside a <source>.

    If ``f`` is an instance of :class:`collada.source.FloatSource`, then
    ``len(f)`` is the length of the shaped source. ``len(f)*len(f.components)``
    would give you the number of values in the source. ``f[i]`` is the i\ :sup:`th`
    item in the source array.
    """

    def __init__(self, id, data, components, xmlnode=None):
        """Create a float source instance.

        :param str id:
          A unique string identifier for the source
        :param numpy.array data:
          Numpy array (unshaped) with the source values
        :param tuple components:
          Tuple of strings describing the semantic of the data,
          e.g. ``('X','Y','Z')`` would cause :attr:`data` to be
          reshaped as ``(-1, 3)``
        :param xmlnode:
          When loaded, the xmlnode it comes from.

        """

        self.id = id
        """The unique string identifier for the source"""
        self.data = data
        """Numpy array with the source values. This will be shaped as ``(-1,N)`` where ``N = len(self.components)``"""
        self.data.shape = (-1, len(components) )
        self.components = components
        """Tuple of strings describing the semantic of the data, e.g. ``('X','Y','Z')``"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the source."""
        else:
            self.data.shape = (-1,)
            txtdata = ' '.join(map(str, self.data.tolist() ))
            rawlen = len( self.data )
            self.data.shape = (-1, len(self.components) )
            acclen = len( self.data )
            stridelen = len(self.components)
            sourcename = "%s-array"%self.id

            self.xmlnode = E.source(
                E.float_array(txtdata, count=str(rawlen), id=sourcename),
                E.technique_common(
                    E.accessor(
                        *[E.param(type='float', name=c) for c in self.components]
                    , **{'count':str(acclen), 'stride':str(stridelen), 'source':"#%s"%sourcename} )
                )
            , id=self.id )

    def __len__(self): return len(self.data)

    def __getitem__(self, i): return self.data[i]

    def save(self):
        """Saves the source back to :attr:`xmlnode`"""
        self.data.shape = (-1,)

        txtdata = ' '.join(map(lambda x: '%.7g'%x , self.data.tolist()))

        rawlen = len( self.data )
        self.data.shape = (-1, len(self.components) )
        acclen = len( self.data )
        node = self.xmlnode.find(tag('float_array'))
        node.text = txtdata
        node.set('count', str(rawlen))
        node.set('id', self.id+'-array' )
        node = self.xmlnode.find('%s/%s'%(tag('technique_common'), tag('accessor')))
        node.clear()
        node.set('count', str(acclen))
        node.set('source', '#'+self.id+'-array')
        node.set('stride', str(len(self.components)))
        for c in self.components:
            node.append(E.param(type='float', name=c))
        self.xmlnode.set('id', self.id )

    @staticmethod
    def load( collada, localscope, node ):
        sourceid = node.get('id')
        arraynode = node.find(tag('float_array'))
        if arraynode is None: raise DaeIncompleteError('No float_array in source node')
        if arraynode.text is None:
            data = numpy.array([], dtype=numpy.float32)
        else:
            try: data = numpy.fromstring(arraynode.text, dtype=numpy.float32, sep=' ')
            except ValueError: raise DaeMalformedError('Corrupted float array')
        data[numpy.isnan(data)] = 0

        paramnodes = node.findall('%s/%s/%s'%(tag('technique_common'), tag('accessor'), tag('param')))
        if not paramnodes: raise DaeIncompleteError('No accessor info in source node')
        components = [ param.get('name') for param in paramnodes ]
        if len(components) == 2 and components[0] == 'U' and components[1] == 'V':
            #U,V is used for "generic" arguments - convert to S,T
            components = ['S', 'T']
        if len(components) == 3 and components[0] == 'S' and components[1] == 'T' and components[2] == 'P':
            components = ['S', 'T']
            data.shape = (-1, 3)
            #remove 3d texcoord dimension because we don't support it
            data = numpy.delete(data, -1, 1)
            data.shape = (-1)
        return FloatSource( sourceid, data, tuple(components), xmlnode=node )

    def __str__(self): return '<FloatSource size=%d>' % (len(self),)
    def __repr__(self): return str(self)

class IDRefSource(Source):
    """Contains a source array of ID references, as defined in the collada
    <IDREF_array> inside a <source>.

    If ``r`` is an instance of :class:`collada.source.IDRefSource`, then
    ``len(r)`` is the length of the shaped source. ``len(r)*len(r.components)``
    would give you the number of values in the source. ``r[i]`` is the i\ :sup:`th`
    item in the source array.

    """

    def __init__(self, id, data, components, xmlnode=None):
        """Create an id ref source instance.

        :param str id:
          A unique string identifier for the source
        :param numpy.array data:
          Numpy array (unshaped) with the source values
        :param tuple components:
          Tuple of strings describing the semantic of the data,
          e.g. ``('MORPH_TARGET')`` would cause :attr:`data` to be
          reshaped as ``(-1, 1)``
        :param xmlnode:
          When loaded, the xmlnode it comes from.

        """

        self.id = id
        """The unique string identifier for the source"""
        self.data = data
        """Numpy array with the source values. This will be shaped as ``(-1,N)`` where ``N = len(self.components)``"""
        self.data.shape = (-1, len(components) )
        self.components = components
        """Tuple of strings describing the semantic of the data, e.g. ``('MORPH_TARGET')``"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the source."""
        else:
            self.data.shape = (-1,)
            txtdata = ' '.join(map(str, self.data.tolist() ))
            rawlen = len( self.data )
            self.data.shape = (-1, len(self.components) )
            acclen = len( self.data )
            stridelen = len(self.components)
            sourcename = "%s-array"%self.id

            self.xmlnode = E.source(
                E.IDREF_array(txtdata, count=str(rawlen), id=sourcename),
                E.technique_common(
                    E.accessor(
                        *[E.param(type='IDREF', name=c) for c in self.components]
                    , **{'count':str(acclen), 'stride':str(stridelen), 'source':sourcename})
                )
            , id=self.id )

    def __len__(self): return len(self.data)

    def __getitem__(self, i): return self.data[i][0] if len(self.data[i])==1 else self.data[i]

    def save(self):
        """Saves the source back to :attr:`xmlnode`"""
        self.data.shape = (-1,)
        txtdata = ' '.join(map(str, self.data.tolist() ))
        rawlen = len( self.data )
        self.data.shape = (-1, len(self.components) )
        acclen = len( self.data )

        node = self.xmlnode.find(tag('IDREF_array'))
        node.text = txtdata
        node.set('count', str(rawlen))
        node.set('id', self.id+'-array' )
        node = self.xmlnode.find('%s/%s'%(tag('technique_common'), tag('accessor')))
        node.clear()
        node.set('count', str(acclen))
        node.set('source', '#'+self.id+'-array')
        node.set('stride', str(len(self.components)))
        for c in self.components:
            node.append(E.param(type='IDREF', name=c))
        self.xmlnode.set('id', self.id )

    @staticmethod
    def load( collada, localscope, node ):
        sourceid = node.get('id')
        arraynode = node.find(tag('IDREF_array'))
        if arraynode is None: raise DaeIncompleteError('No IDREF_array in source node')
        if arraynode.text is None:
            values = []
        else:
            try: values = [v for v in arraynode.text.split()]
            except ValueError: raise DaeMalformedError('Corrupted IDREF array')
        data = numpy.array( values, dtype=numpy.string_ )
        paramnodes = node.findall('%s/%s/%s'%(tag('technique_common'), tag('accessor'), tag('param')))
        if not paramnodes: raise DaeIncompleteError('No accessor info in source node')
        components = [ param.get('name') for param in paramnodes ]
        return IDRefSource( sourceid, data, tuple(components), xmlnode=node )

    def __str__(self): return '<IDRefSource size=%d>' % (len(self),)
    def __repr__(self): return str(self)

class NameSource(Source):
    """Contains a source array of strings, as defined in the collada
    <Name_array> inside a <source>.

    If ``n`` is an instance of :class:`collada.source.NameSource`, then
    ``len(n)`` is the length of the shaped source. ``len(n)*len(n.components)``
    would give you the number of values in the source. ``n[i]`` is the i\ :sup:`th`
    item in the source array.

    """

    def __init__(self, id, data, components, xmlnode=None):
        """Create a name source instance.

        :param str id:
          A unique string identifier for the source
        :param numpy.array data:
          Numpy array (unshaped) with the source values
        :param tuple components:
          Tuple of strings describing the semantic of the data,
          e.g. ``('JOINT')`` would cause :attr:`data` to be
          reshaped as ``(-1, 1)``
        :param xmlnode:
          When loaded, the xmlnode it comes from.

        """

        self.id = id
        """The unique string identifier for the source"""
        self.data = data
        """Numpy array with the source values. This will be shaped as ``(-1,N)`` where ``N = len(self.components)``"""
        self.data.shape = (-1, len(components) )
        self.components = components
        """Tuple of strings describing the semantic of the data, e.g. ``('JOINT')``"""
        if xmlnode != None:
            self.xmlnode = xmlnode
            """ElementTree representation of the source."""
        else:
            self.data.shape = (-1,)
            txtdata = ' '.join(map(str, self.data.tolist() ))
            rawlen = len( self.data )
            self.data.shape = (-1, len(self.components) )
            acclen = len( self.data )
            stridelen = len(self.components)
            sourcename = "%s-array"%self.id

            self.xmlnode = E.source(
                E.Name_array(txtdata, count=str(rawlen), id=sourcename),
                E.technique_common(
                    E.accessor(
                        *[E.param(type='Name', name=c) for c in self.components]
                    , **{'count':str(acclen), 'stride':str(stridelen), 'source':sourcename})
                )
            , id=self.id )

    def __len__(self): return len(self.data)

    def __getitem__(self, i): return self.data[i][0] if len(self.data[i])==1 else self.data[i]

    def save(self):
        """Saves the source back to :attr:`xmlnode`"""
        self.data.shape = (-1,)
        txtdata = ' '.join(map(str, self.data.tolist() ))
        rawlen = len( self.data )
        self.data.shape = (-1, len(self.components) )
        acclen = len( self.data )

        node = self.xmlnode.find(tag('Name_array'))
        node.text = txtdata
        node.set('count', str(rawlen))
        node.set('id', self.id+'-array' )
        node = self.xmlnode.find('%s/%s'%(tag('technique_common'), tag('accessor')))
        node.clear()
        node.set('count', str(acclen))
        node.set('source', '#'+self.id+'-array')
        node.set('stride', str(len(self.components)))
        for c in self.components:
            node.append(E.param(type='IDREF', name=c))
        self.xmlnode.set('id', self.id )

    @staticmethod
    def load( collada, localscope, node ):
        sourceid = node.get('id')
        arraynode = node.find(tag('Name_array'))
        if arraynode is None: raise DaeIncompleteError('No Name_array in source node')
        if arraynode.text is None:
            values = []
        else:
            try: values = [v for v in arraynode.text.split()]
            except ValueError: raise DaeMalformedError('Corrupted Name array')
        data = numpy.array( values, dtype=numpy.string_ )
        paramnodes = node.findall('%s/%s/%s'%(tag('technique_common'), tag('accessor'), tag('param')))
        if not paramnodes: raise DaeIncompleteError('No accessor info in source node')
        components = [ param.get('name') for param in paramnodes ]
        return NameSource( sourceid, data, tuple(components), xmlnode=node )

    def __str__(self): return '<NameSource size=%d>' % (len(self),)
    def __repr__(self): return str(self)

########NEW FILE########
__FILENAME__ = test_asset
import datetime

import collada
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestAsset(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_asset_contributor(self):
        contributor = collada.asset.Contributor()
        self.assertIsNone(contributor.author)
        self.assertIsNone(contributor.authoring_tool)
        self.assertIsNone(contributor.comments)
        self.assertIsNone(contributor.copyright)
        self.assertIsNone(contributor.source_data)

        contributor.save()
        contributor = collada.asset.Contributor.load(self.dummy, {}, fromstring(tostring(contributor.xmlnode)))
        self.assertIsNone(contributor.author)
        self.assertIsNone(contributor.authoring_tool)
        self.assertIsNone(contributor.comments)
        self.assertIsNone(contributor.copyright)
        self.assertIsNone(contributor.source_data)

        contributor.author = "author1"
        contributor.authoring_tool = "tool2"
        contributor.comments = "comments3"
        contributor.copyright = "copyright4"
        contributor.source_data = "data5"

        contributor.save()
        contributor = collada.asset.Contributor.load(self.dummy, {}, fromstring(tostring(contributor.xmlnode)))
        self.assertEqual(contributor.author, "author1")
        self.assertEqual(contributor.authoring_tool, "tool2")
        self.assertEqual(contributor.comments, "comments3")
        self.assertEqual(contributor.copyright, "copyright4")
        self.assertEqual(contributor.source_data, "data5")

    def test_asset(self):
        asset = collada.asset.Asset()

        self.assertIsNone(asset.title)
        self.assertIsNone(asset.subject)
        self.assertIsNone(asset.revision)
        self.assertIsNone(asset.keywords)
        self.assertIsNone(asset.unitname)
        self.assertIsNone(asset.unitmeter)
        self.assertEqual(asset.contributors, [])
        self.assertEqual(asset.upaxis, collada.asset.UP_AXIS.Y_UP)
        self.assertIsInstance(asset.created, datetime.datetime)
        self.assertIsInstance(asset.modified, datetime.datetime)

        asset.save()
        asset = collada.asset.Asset.load(self.dummy, {}, fromstring(tostring(asset.xmlnode)))

        self.assertIsNone(asset.title)
        self.assertIsNone(asset.subject)
        self.assertIsNone(asset.revision)
        self.assertIsNone(asset.keywords)
        self.assertIsNone(asset.unitname)
        self.assertIsNone(asset.unitmeter)
        self.assertEqual(asset.contributors, [])
        self.assertEqual(asset.upaxis, collada.asset.UP_AXIS.Y_UP)
        self.assertIsInstance(asset.created, datetime.datetime)
        self.assertIsInstance(asset.modified, datetime.datetime)

        asset.title = 'title1'
        asset.subject = 'subject2'
        asset.revision = 'revision3'
        asset.keywords = 'keywords4'
        asset.unitname = 'feet'
        asset.unitmeter = 3.1
        contrib1 = collada.asset.Contributor(author="jeff")
        contrib2 = collada.asset.Contributor(author="bob")
        asset.contributors = [contrib1, contrib2]
        asset.upaxis = collada.asset.UP_AXIS.Z_UP
        time1 = datetime.datetime.now()
        asset.created = time1
        time2 = datetime.datetime.now() + datetime.timedelta(hours=5)
        asset.modified = time2

        asset.save()
        asset = collada.asset.Asset.load(self.dummy, {}, fromstring(tostring(asset.xmlnode)))
        self.assertEqual(asset.title, 'title1')
        self.assertEqual(asset.subject, 'subject2')
        self.assertEqual(asset.revision, 'revision3')
        self.assertEqual(asset.keywords, 'keywords4')
        self.assertEqual(asset.unitname, 'feet')
        self.assertEqual(asset.unitmeter, 3.1)
        self.assertEqual(asset.upaxis, collada.asset.UP_AXIS.Z_UP)
        self.assertEqual(asset.created, time1)
        self.assertEqual(asset.modified, time2)
        self.assertEqual(len(asset.contributors), 2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_camera
import collada
from collada.common import DaeMalformedError
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestCamera(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_perspective_camera_xfov_yfov_aspect_ratio(self):
        #test invalid xfov,yfov,aspect_ratio combinations
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=None, yfov=None, aspect_ratio=None)
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=0.2, yfov=30, aspect_ratio=50)
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=None, yfov=None, aspect_ratio=50)

        #xfov alone
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=30, yfov=None, aspect_ratio=None)
        self.assertEqual(cam.xfov, 30)
        self.assertIsNone(cam.yfov)
        self.assertIsNone(cam.aspect_ratio)

        #yfov alone
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=None, yfov=50, aspect_ratio=None)
        self.assertIsNone(cam.xfov)
        self.assertEqual(cam.yfov, 50)
        self.assertIsNone(cam.aspect_ratio)

        #xfov + yfov
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=30, yfov=50, aspect_ratio=None)
        self.assertEqual(cam.xfov, 30)
        self.assertEqual(cam.yfov, 50)
        self.assertIsNone(cam.aspect_ratio)

        #xfov + aspect_ratio
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=30, yfov=None, aspect_ratio=1)
        self.assertEqual(cam.xfov, 30)
        self.assertIsNone(cam.yfov)
        self.assertEqual(cam.aspect_ratio, 1)

        #yfov + aspect_ratio
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=None, yfov=50, aspect_ratio=1)
        self.assertIsNone(cam.xfov)
        self.assertEqual(cam.yfov, 50)
        self.assertEqual(cam.aspect_ratio, 1)

    def test_perspective_camera_saving(self):
        cam = collada.camera.PerspectiveCamera("mycam", 1, 1000, xfov=30)

        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xfov, 30)
        self.assertEqual(cam.yfov, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam.save()
        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xfov, 30)
        self.assertEqual(cam.yfov, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam = collada.camera.PerspectiveCamera.load(self.dummy, {}, fromstring(tostring(cam.xmlnode)))
        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xfov, 30)
        self.assertEqual(cam.yfov, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam.id = "yourcam"
        cam.znear = 5
        cam.zfar = 500
        cam.xfov = None
        cam.yfov = 50
        cam.aspect_ratio = 1.3
        cam.save()
        cam = collada.camera.PerspectiveCamera.load(self.dummy, {}, fromstring(tostring(cam.xmlnode)))
        self.assertEqual(cam.id, "yourcam")
        self.assertEqual(cam.znear, 5)
        self.assertEqual(cam.zfar, 500)
        self.assertEqual(cam.xfov, None)
        self.assertEqual(cam.yfov, 50)
        self.assertEqual(cam.aspect_ratio, 1.3)

        cam.xfov = 20
        with self.assertRaises(DaeMalformedError):
            cam.save()

    def test_orthographic_camera_xmag_ymag_aspect_ratio(self):
        #test invalid xmag,ymag,aspect_ratio combinations
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=None, ymag=None, aspect_ratio=None)
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=0.2, ymag=30, aspect_ratio=50)
        with self.assertRaises(DaeMalformedError):
            cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=None, ymag=None, aspect_ratio=50)

        #xmag alone
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=30, ymag=None, aspect_ratio=None)
        self.assertEqual(cam.xmag, 30)
        self.assertIsNone(cam.ymag)
        self.assertIsNone(cam.aspect_ratio)

        #ymag alone
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=None, ymag=50, aspect_ratio=None)
        self.assertIsNone(cam.xmag)
        self.assertEqual(cam.ymag, 50)
        self.assertIsNone(cam.aspect_ratio)

        #xmag + ymag
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=30, ymag=50, aspect_ratio=None)
        self.assertEqual(cam.xmag, 30)
        self.assertEqual(cam.ymag, 50)
        self.assertIsNone(cam.aspect_ratio)

        #xmag + aspect_ratio
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=30, ymag=None, aspect_ratio=1)
        self.assertEqual(cam.xmag, 30)
        self.assertIsNone(cam.ymag)
        self.assertEqual(cam.aspect_ratio, 1)

        #ymag + aspect_ratio
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=None, ymag=50, aspect_ratio=1)
        self.assertIsNone(cam.xmag)
        self.assertEqual(cam.ymag, 50)
        self.assertEqual(cam.aspect_ratio, 1)

    def test_orthographic_camera_saving(self):
        cam = collada.camera.OrthographicCamera("mycam", 1, 1000, xmag=30)

        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xmag, 30)
        self.assertEqual(cam.ymag, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam.save()
        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xmag, 30)
        self.assertEqual(cam.ymag, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam = collada.camera.OrthographicCamera.load(self.dummy, {}, fromstring(tostring(cam.xmlnode)))
        self.assertEqual(cam.id, "mycam")
        self.assertEqual(cam.znear, 1)
        self.assertEqual(cam.zfar, 1000)
        self.assertEqual(cam.xmag, 30)
        self.assertEqual(cam.ymag, None)
        self.assertEqual(cam.aspect_ratio, None)

        cam.id = "yourcam"
        cam.znear = 5
        cam.zfar = 500
        cam.xmag = None
        cam.ymag = 50
        cam.aspect_ratio = 1.3
        cam.save()
        cam = collada.camera.OrthographicCamera.load(self.dummy, {}, fromstring(tostring(cam.xmlnode)))
        self.assertEqual(cam.id, "yourcam")
        self.assertEqual(cam.znear, 5)
        self.assertEqual(cam.zfar, 500)
        self.assertEqual(cam.xmag, None)
        self.assertEqual(cam.ymag, 50)
        self.assertEqual(cam.aspect_ratio, 1.3)

        cam.xmag = 20
        with self.assertRaises(DaeMalformedError):
            cam.save()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collada
import os
import numpy
import dateutil.parser

import collada
from collada.util import unittest, BytesIO
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestCollada(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)
        self.datadir = os.path.join(os.path.dirname(os.path.realpath( __file__ )), "data")

    def test_collada_duck_tris(self):
        f = os.path.join(self.datadir, "duck_triangles.dae")
        mesh = collada.Collada(f, validate_output=True)

        self.assertEqual(mesh.assetInfo.contributors[0].author, 'gcorson')
        self.assertEqual(mesh.assetInfo.contributors[0].authoring_tool, 'Maya 8.0 | ColladaMaya v3.02 | FCollada v3.2')
        self.assertEqual(mesh.assetInfo.contributors[0].source_data, 'file:///C:/vs2005/sample_data/Complete_Packages/SCEA_Private/Maya_MoonLander/Moonlander/untitled')
        self.assertEqual(len(mesh.assetInfo.contributors[0].copyright), 595)
        self.assertEqual(len(mesh.assetInfo.contributors[0].comments), 449)

        self.assertEqual(mesh.assetInfo.unitmeter, 0.01)
        self.assertEqual(mesh.assetInfo.unitname, 'centimeter')
        self.assertEqual(mesh.assetInfo.upaxis, collada.asset.UP_AXIS.Y_UP)
        self.assertIsNone(mesh.assetInfo.title)
        self.assertIsNone(mesh.assetInfo.subject)
        self.assertIsNone(mesh.assetInfo.revision)
        self.assertIsNone(mesh.assetInfo.keywords)
        self.assertEqual(mesh.assetInfo.created, dateutil.parser.parse('2006-08-23T22:29:59Z'))
        self.assertEqual(mesh.assetInfo.modified, dateutil.parser.parse('2007-02-21T22:52:44Z'))

        self.assertEqual(mesh.scene.id, 'VisualSceneNode')
        self.assertIn('LOD3spShape-lib', mesh.geometries)
        self.assertIn('directionalLightShape1-lib', mesh.lights)
        self.assertIn('cameraShape1', mesh.cameras)
        self.assertIn('file2', mesh.images)
        self.assertIn('blinn3-fx', mesh.effects)
        self.assertIn('blinn3', mesh.materials)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertIn('VisualSceneNode', mesh.scenes)

        self.assertIsNotNone(str(list(mesh.scene.objects('geometry'))))
        self.assertIsNotNone(str(list(mesh.scene.objects('light'))))
        self.assertIsNotNone(str(list(mesh.scene.objects('camera'))))

        s = BytesIO()
        mesh.write(s)
        out = s.getvalue()
        t = BytesIO(out)
        mesh = collada.Collada(t, validate_output=True)

        self.assertEqual(mesh.assetInfo.contributors[0].author, 'gcorson')
        self.assertEqual(mesh.assetInfo.contributors[0].authoring_tool, 'Maya 8.0 | ColladaMaya v3.02 | FCollada v3.2')
        self.assertEqual(mesh.assetInfo.contributors[0].source_data, 'file:///C:/vs2005/sample_data/Complete_Packages/SCEA_Private/Maya_MoonLander/Moonlander/untitled')
        self.assertEqual(len(mesh.assetInfo.contributors[0].copyright), 595)
        self.assertEqual(len(mesh.assetInfo.contributors[0].comments), 449)

        self.assertEqual(mesh.assetInfo.unitmeter, 0.01)
        self.assertEqual(mesh.assetInfo.unitname, 'centimeter')
        self.assertEqual(mesh.assetInfo.upaxis, collada.asset.UP_AXIS.Y_UP)
        self.assertIsNone(mesh.assetInfo.title)
        self.assertIsNone(mesh.assetInfo.subject)
        self.assertIsNone(mesh.assetInfo.revision)
        self.assertIsNone(mesh.assetInfo.keywords)
        self.assertEqual(mesh.assetInfo.created, dateutil.parser.parse('2006-08-23T22:29:59Z'))
        self.assertEqual(mesh.assetInfo.modified, dateutil.parser.parse('2007-02-21T22:52:44Z'))

        self.assertEqual(mesh.scene.id, 'VisualSceneNode')
        self.assertIn('LOD3spShape-lib', mesh.geometries)
        self.assertIn('directionalLightShape1-lib', mesh.lights)
        self.assertIn('cameraShape1', mesh.cameras)
        self.assertIn('file2', mesh.images)
        self.assertIn('blinn3-fx', mesh.effects)
        self.assertIn('blinn3', mesh.materials)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertIn('VisualSceneNode', mesh.scenes)

        self.assertIsNotNone(str(list(mesh.scene.objects('geometry'))))
        self.assertIsNotNone(str(list(mesh.scene.objects('light'))))
        self.assertIsNotNone(str(list(mesh.scene.objects('camera'))))

    def test_collada_duck_poly(self):
        f = os.path.join(self.datadir, "duck_polylist.dae")
        mesh = collada.Collada(f, validate_output=True)
        self.assertEqual(mesh.scene.id, 'VisualSceneNode')
        self.assertIn('LOD3spShape-lib', mesh.geometries)
        self.assertIn('directionalLightShape1-lib', mesh.lights)
        self.assertIn('cameraShape1', mesh.cameras)
        self.assertIn('file2', mesh.images)
        self.assertIn('blinn3-fx', mesh.effects)
        self.assertIn('blinn3', mesh.materials)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertIn('VisualSceneNode', mesh.scenes)

        s = BytesIO()
        mesh.write(s)
        out = s.getvalue()
        t = BytesIO(out)
        mesh = collada.Collada(t, validate_output=True)

        self.assertEqual(mesh.scene.id, 'VisualSceneNode')
        self.assertIn('LOD3spShape-lib', mesh.geometries)
        self.assertIn('directionalLightShape1-lib', mesh.lights)
        self.assertIn('cameraShape1', mesh.cameras)
        self.assertIn('file2', mesh.images)
        self.assertIn('blinn3-fx', mesh.effects)
        self.assertIn('blinn3', mesh.materials)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertIn('VisualSceneNode', mesh.scenes)

    def test_collada_duck_zip(self):
        f = os.path.join(self.datadir, "duck.zip")
        mesh = collada.Collada(f, validate_output=True)
        self.assertEqual(mesh.scene.id, 'VisualSceneNode')
        self.assertIn('LOD3spShape-lib', mesh.geometries)
        self.assertIn('directionalLightShape1-lib', mesh.lights)
        self.assertIn('cameraShape1', mesh.cameras)
        self.assertIn('file2', mesh.images)
        self.assertIn('blinn3-fx', mesh.effects)
        self.assertIn('blinn3', mesh.materials)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertIn('VisualSceneNode', mesh.scenes)

    def test_collada_saving(self):
        mesh = collada.Collada(validate_output=True)

        self.assertEqual(len(mesh.geometries), 0)
        self.assertEqual(len(mesh.controllers), 0)
        self.assertEqual(len(mesh.lights), 0)
        self.assertEqual(len(mesh.cameras), 0)
        self.assertEqual(len(mesh.images), 0)
        self.assertEqual(len(mesh.effects), 0)
        self.assertEqual(len(mesh.materials), 0)
        self.assertEqual(len(mesh.nodes), 0)
        self.assertEqual(len(mesh.scenes), 0)
        self.assertEqual(mesh.scene, None)
        self.assertIsNotNone(str(mesh))

        floatsource = collada.source.FloatSource("myfloatsource", numpy.array([0.1,0.2,0.3]), ('X', 'Y', 'Z'))
        geometry1 = collada.geometry.Geometry(mesh, "geometry1", "mygeometry1", {"myfloatsource":floatsource})
        mesh.geometries.append(geometry1)

        linefloats = [1,1,-1, 1,-1,-1, -1,-0.9999998,-1, -0.9999997,1,-1, 1,0.9999995,1, 0.9999994,-1.000001,1]
        linefloatsrc = collada.source.FloatSource("mylinevertsource", numpy.array(linefloats), ('X', 'Y', 'Z'))
        geometry2 = collada.geometry.Geometry(mesh, "geometry2", "mygeometry2", [linefloatsrc])
        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#mylinevertsource")
        indices = numpy.array([0,1, 1,2, 2,3, 3,4, 4,5])
        lineset1 = geometry2.createLineSet(indices, input_list, "mymaterial2")
        geometry2.primitives.append(lineset1)
        mesh.geometries.append(geometry2)

        ambientlight = collada.light.AmbientLight("myambientlight", (1,1,1))
        pointlight = collada.light.PointLight("mypointlight", (1,1,1))
        mesh.lights.append(ambientlight)
        mesh.lights.append(pointlight)

        camera1 = collada.camera.PerspectiveCamera("mycam1", 45.0, 0.01, 1000.0)
        camera2 = collada.camera.PerspectiveCamera("mycam2", 45.0, 0.01, 1000.0)
        mesh.cameras.append(camera1)
        mesh.cameras.append(camera2)

        cimage1 = collada.material.CImage("mycimage1", "./whatever.tga", mesh)
        cimage2 = collada.material.CImage("mycimage2", "./whatever.tga", mesh)
        mesh.images.append(cimage1)
        mesh.images.append(cimage2)

        effect1 = collada.material.Effect("myeffect1", [], "phong")
        effect2 = collada.material.Effect("myeffect2", [], "phong")
        mesh.effects.append(effect1)
        mesh.effects.append(effect2)

        mat1 = collada.material.Material("mymaterial1", "mymat1", effect1)
        mat2 = collada.material.Material("mymaterial2", "mymat2", effect2)
        mesh.materials.append(mat1)
        mesh.materials.append(mat2)

        rotate = collada.scene.RotateTransform(0.1, 0.2, 0.3, 90)
        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        mynode1 = collada.scene.Node('mynode1', children=[], transforms=[rotate, scale])
        mynode2 = collada.scene.Node('mynode2', children=[], transforms=[])
        mesh.nodes.append(mynode1)
        mesh.nodes.append(mynode2)

        geomnode = collada.scene.GeometryNode(geometry2)
        mynode3 = collada.scene.Node('mynode3', children=[geomnode], transforms=[])
        mynode4 = collada.scene.Node('mynode4', children=[], transforms=[])
        scene1 = collada.scene.Scene('myscene1', [mynode3])
        scene2 = collada.scene.Scene('myscene2', [mynode4])
        mesh.scenes.append(scene1)
        mesh.scenes.append(scene2)

        mesh.scene = scene1

        out = BytesIO()
        mesh.write(out)

        toload = BytesIO(out.getvalue())

        loaded_mesh = collada.Collada(toload, validate_output=True)
        self.assertEqual(len(loaded_mesh.geometries), 2)
        self.assertEqual(len(loaded_mesh.controllers), 0)
        self.assertEqual(len(loaded_mesh.lights), 2)
        self.assertEqual(len(loaded_mesh.cameras), 2)
        self.assertEqual(len(loaded_mesh.images), 2)
        self.assertEqual(len(loaded_mesh.effects), 2)
        self.assertEqual(len(loaded_mesh.materials), 2)
        self.assertEqual(len(loaded_mesh.nodes), 2)
        self.assertEqual(len(loaded_mesh.scenes), 2)
        self.assertEqual(loaded_mesh.scene.id, scene1.id)

        self.assertIn('geometry1', loaded_mesh.geometries)
        self.assertIn('geometry2', loaded_mesh.geometries)
        self.assertIn('mypointlight', loaded_mesh.lights)
        self.assertIn('myambientlight', loaded_mesh.lights)
        self.assertIn('mycam1', loaded_mesh.cameras)
        self.assertIn('mycam2', loaded_mesh.cameras)
        self.assertIn('mycimage1', loaded_mesh.images)
        self.assertIn('mycimage2', loaded_mesh.images)
        self.assertIn('myeffect1', loaded_mesh.effects)
        self.assertIn('myeffect2', loaded_mesh.effects)
        self.assertIn('mymaterial1', loaded_mesh.materials)
        self.assertIn('mymaterial2', loaded_mesh.materials)
        self.assertIn('mynode1', loaded_mesh.nodes)
        self.assertIn('mynode2', loaded_mesh.nodes)
        self.assertIn('myscene1', loaded_mesh.scenes)
        self.assertIn('myscene2', loaded_mesh.scenes)

        linefloatsrc2 = collada.source.FloatSource("mylinevertsource2", numpy.array(linefloats), ('X', 'Y', 'Z'))
        geometry3 = collada.geometry.Geometry(mesh, "geometry3", "mygeometry3", [linefloatsrc2])
        loaded_mesh.geometries.pop(0)
        loaded_mesh.geometries.append(geometry3)

        dirlight = collada.light.DirectionalLight("mydirlight", (1,1,1))
        loaded_mesh.lights.pop(0)
        loaded_mesh.lights.append(dirlight)

        camera3 = collada.camera.PerspectiveCamera("mycam3", 45.0, 0.01, 1000.0)
        loaded_mesh.cameras.pop(0)
        loaded_mesh.cameras.append(camera3)

        cimage3 = collada.material.CImage("mycimage3", "./whatever.tga", loaded_mesh)
        loaded_mesh.images.pop(0)
        loaded_mesh.images.append(cimage3)

        effect3 = collada.material.Effect("myeffect3", [], "phong")
        loaded_mesh.effects.pop(0)
        loaded_mesh.effects.append(effect3)

        mat3 = collada.material.Material("mymaterial3", "mymat3", effect3)
        loaded_mesh.materials.pop(0)
        loaded_mesh.materials.append(mat3)

        mynode5 = collada.scene.Node('mynode5', children=[], transforms=[])
        loaded_mesh.nodes.pop(0)
        loaded_mesh.nodes.append(mynode5)

        mynode6 = collada.scene.Node('mynode6', children=[], transforms=[])
        scene3 = collada.scene.Scene('myscene3', [mynode6])
        loaded_mesh.scenes.pop(0)
        loaded_mesh.scenes.append(scene3)

        loaded_mesh.scene = scene3

        loaded_mesh.save()

        strdata = tostring(loaded_mesh.xmlnode.getroot())
        indata = BytesIO(strdata)
        loaded_mesh2 = collada.Collada(indata, validate_output=True)

        self.assertEqual(loaded_mesh2.scene.id, scene3.id)
        self.assertIn('geometry3', loaded_mesh2.geometries)
        self.assertIn('geometry2', loaded_mesh2.geometries)
        self.assertIn('mydirlight', loaded_mesh2.lights)
        self.assertIn('mypointlight', loaded_mesh2.lights)
        self.assertIn('mycam3', loaded_mesh2.cameras)
        self.assertIn('mycam2', loaded_mesh2.cameras)
        self.assertIn('mycimage3', loaded_mesh2.images)
        self.assertIn('mycimage2', loaded_mesh2.images)
        self.assertIn('myeffect3', loaded_mesh2.effects)
        self.assertIn('myeffect2', loaded_mesh2.effects)
        self.assertIn('mymaterial3', loaded_mesh2.materials)
        self.assertIn('mymaterial2', loaded_mesh2.materials)
        self.assertIn('mynode5', loaded_mesh2.nodes)
        self.assertIn('mynode2', loaded_mesh2.nodes)
        self.assertIn('myscene3', loaded_mesh2.scenes)
        self.assertIn('myscene2', loaded_mesh2.scenes)

    def test_collada_attribute_replace(self):
        mesh = collada.Collada(validate_output=True)
        self.assertIsInstance(mesh.geometries, collada.util.IndexedList)
        self.assertIsInstance(mesh.controllers, collada.util.IndexedList)
        self.assertIsInstance(mesh.animations, collada.util.IndexedList)
        self.assertIsInstance(mesh.lights, collada.util.IndexedList)
        self.assertIsInstance(mesh.cameras, collada.util.IndexedList)
        self.assertIsInstance(mesh.images, collada.util.IndexedList)
        self.assertIsInstance(mesh.effects, collada.util.IndexedList)
        self.assertIsInstance(mesh.materials, collada.util.IndexedList)
        self.assertIsInstance(mesh.nodes, collada.util.IndexedList)
        self.assertIsInstance(mesh.scenes, collada.util.IndexedList)

        mesh.geometries = []
        mesh.controllers = []
        mesh.animations = []
        mesh.lights = []
        mesh.cameras = []
        mesh.images = []
        mesh.effects = []
        mesh.materials = []
        mesh.nodes = []
        mesh.scenes = []

        self.assertIsInstance(mesh.geometries, collada.util.IndexedList)
        self.assertIsInstance(mesh.controllers, collada.util.IndexedList)
        self.assertIsInstance(mesh.animations, collada.util.IndexedList)
        self.assertIsInstance(mesh.lights, collada.util.IndexedList)
        self.assertIsInstance(mesh.cameras, collada.util.IndexedList)
        self.assertIsInstance(mesh.images, collada.util.IndexedList)
        self.assertIsInstance(mesh.effects, collada.util.IndexedList)
        self.assertIsInstance(mesh.materials, collada.util.IndexedList)
        self.assertIsInstance(mesh.nodes, collada.util.IndexedList)
        self.assertIsInstance(mesh.scenes, collada.util.IndexedList)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_geometry
import numpy

import collada
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestGeometry(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_empty_geometry_saving(self):
        floatsource = collada.source.FloatSource("myfloatsource", numpy.array([0.1,0.2,0.3]), ('X', 'Y', 'Z'))
        geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mygeometry", {"myfloatsource":floatsource})
        self.assertEqual(geometry.id, "geometry0")
        self.assertEqual(geometry.name, "mygeometry")
        self.assertEqual(len(geometry.primitives), 0)
        self.assertDictEqual(geometry.sourceById, {"myfloatsource":floatsource})
        self.assertIsNotNone(str(geometry))

        geometry.id = "geometry1"
        geometry.name = "yourgeometry"
        othersource1 = collada.source.FloatSource("yourfloatsource", numpy.array([0.4,0.5,0.6]), ('X', 'Y', 'Z'))
        othersource2 = collada.source.FloatSource("hisfloatsource", numpy.array([0.7,0.8,0.9]), ('X', 'Y', 'Z'))
        geometry.sourceById[othersource1.id] = othersource1
        geometry.sourceById[othersource2.id] = othersource2
        del geometry.sourceById[floatsource.id]
        geometry.save()

        loaded_geometry = collada.geometry.Geometry.load(collada, {}, fromstring(tostring(geometry.xmlnode)))
        self.assertEqual(loaded_geometry.id, "geometry1")
        self.assertEqual(loaded_geometry.name, "yourgeometry")
        self.assertEqual(len(loaded_geometry.primitives), 0)
        self.assertIn(othersource1.id, loaded_geometry.sourceById)
        self.assertIn(othersource2.id, loaded_geometry.sourceById)
        self.assertNotIn(floatsource.id, loaded_geometry.sourceById)

    def test_geometry_lineset_adding(self):
        linefloats = [1,1,-1, 1,-1,-1, -1,-0.9999998,-1, -0.9999997,1,-1, 1,0.9999995,1, 0.9999994,-1.000001,1]
        linefloatsrc = collada.source.FloatSource("mylinevertsource", numpy.array(linefloats), ('X', 'Y', 'Z'))
        geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mygeometry", [linefloatsrc])
        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#mylinevertsource")
        indices = numpy.array([0,1, 1,2, 2,3, 3,4, 4,5])
        lineset1 = geometry.createLineSet(indices, input_list, "mymaterial")
        lineset2 = geometry.createLineSet(indices, input_list, "mymaterial")
        geometry.primitives.append(lineset1)
        geometry.primitives.append(lineset2)
        self.assertEqual(len(geometry.primitives), 2)
        self.assertIsNotNone(str(lineset1))
        self.assertIsNotNone(str(input_list))
        geometry.save()

        loaded_geometry = collada.geometry.Geometry.load(self.dummy, {}, fromstring(tostring(geometry.xmlnode)))
        self.assertEqual(len(loaded_geometry.primitives), 2)

        loaded_geometry.primitives.pop(0)
        lineset3 = loaded_geometry.createLineSet(indices, input_list, "mymaterial")

        loaded_lineset = collada.lineset.LineSet.load(self.dummy, geometry.sourceById, fromstring(tostring(lineset3.xmlnode)))
        self.assertEqual(len(loaded_lineset), 5)

        loaded_geometry.primitives.append(lineset3)
        loaded_geometry.save()
        loaded_geometry2 = collada.geometry.Geometry.load(self.dummy, {}, fromstring(tostring(loaded_geometry.xmlnode)))

        self.assertEqual(len(loaded_geometry2.primitives), 2)
        self.assertEqual(loaded_geometry2.primitives[0].material, lineset2.material)
        self.assertEqual(loaded_geometry2.primitives[1].material, lineset3.material)

    def test_geometry_triangleset_adding(self):
        vert_floats = [-50,50,50,50,50,50,-50,-50,50,50,-50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
        normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
                         -1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,0,0,-1,0,0,-1,0,0,-1]
        vert_src = collada.source.FloatSource("cubeverts-array", numpy.array(vert_floats), ('X', 'Y', 'Z'))
        normal_src = collada.source.FloatSource("cubenormals-array", numpy.array(normal_floats), ('X', 'Y', 'Z'))
        self.assertEqual(len(vert_src), 8)
        self.assertEqual(len(normal_src), 24)

        geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mycube", [vert_src, normal_src], [])

        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#cubeverts-array")
        input_list.addInput(1, 'NORMAL', "#cubenormals-array")

        indices = numpy.array([0,0,2,1,3,2,0,0,3,2,1,3,0,4,1,5,5,6,0,4,5,6,4,7,6,8,7,9,3,10,6,8,3,10,2,11,0,12,
                        4,13,6,14,0,12,6,14,2,15,3,16,7,17,5,18,3,16,5,18,1,19,5,20,7,21,6,22,5,20,6,22,4,23])
        triangleset = geometry.createTriangleSet(indices, input_list, "cubematerial")
        self.assertIsNotNone(str(triangleset))
        geometry.primitives.append(triangleset)
        geometry.save()

        loaded_triangleset = collada.triangleset.TriangleSet.load(self.dummy, geometry.sourceById, fromstring(tostring(triangleset.xmlnode)))
        self.assertEqual(len(loaded_triangleset), 12)

        loaded_geometry = collada.geometry.Geometry.load(self.dummy, {}, fromstring(tostring(geometry.xmlnode)))
        self.assertEqual(len(loaded_geometry.primitives), 1)
        self.assertEqual(len(loaded_geometry.primitives[0]), 12)

    def test_geometry_polylist_adding(self):
        vert_floats = [-50,50,50,50,50,50,-50,-50,50,50,-50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
        normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
                         -1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,0,0,-1,0,0,-1,0,0,-1]
        vert_src = collada.source.FloatSource("cubeverts-array", numpy.array(vert_floats), ('X', 'Y', 'Z'))
        normal_src = collada.source.FloatSource("cubenormals-array", numpy.array(normal_floats), ('X', 'Y', 'Z'))

        geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mycube", [vert_src, normal_src], [])

        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#cubeverts-array")
        input_list.addInput(1, 'NORMAL', "#cubenormals-array")

        vcounts = numpy.array([4,4,4,4,4,4])
        indices = numpy.array([0,0,2,1,3,2,1,3,0,4,1,5,5,6,4,7,6,8,7,9,3,10,2,11,0,12,4,13,6,14,2,
                               15,3,16,7,17,5,18,1,19,5,20,7,21,6,22,4,23])
        polylist = geometry.createPolylist(indices, vcounts, input_list, "cubematerial")
        self.assertIsNotNone(str(polylist))

        loaded_polylist = collada.polylist.Polylist.load(self.dummy, geometry.sourceById, fromstring(tostring(polylist.xmlnode)))
        self.assertEqual(len(loaded_polylist), 6)

        geometry.primitives.append(polylist)
        geometry.save()

        loaded_geometry = collada.geometry.Geometry.load(self.dummy, {}, fromstring(tostring(geometry.xmlnode)))

        self.assertEqual(len(loaded_geometry.primitives), 1)
        self.assertEqual(len(loaded_geometry.primitives[0]), 6)

    def test_geometry_polygons_adding(self):
        vert_floats = [-50,50,50,50,50,50,-50,-50,50,50,-50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
        normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
                         -1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,0,0,-1,0,0,-1,0,0,-1]
        vert_src = collada.source.FloatSource("cubeverts-array", numpy.array(vert_floats), ('X', 'Y', 'Z'))
        normal_src = collada.source.FloatSource("cubenormals-array", numpy.array(normal_floats), ('X', 'Y', 'Z'))

        geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mycube", [vert_src, normal_src], [])

        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#cubeverts-array")
        input_list.addInput(1, 'NORMAL', "#cubenormals-array")

        indices = []
        indices.append(numpy.array([0,0,2,1,3,2,1,3], dtype=numpy.int32))
        indices.append(numpy.array([0,4,1,5,5,6,4,7], dtype=numpy.int32))
        indices.append(numpy.array([6,8,7,9,3,10,2,11], dtype=numpy.int32))
        indices.append(numpy.array([0,12,4,13,6,14,2,15], dtype=numpy.int32))
        indices.append(numpy.array([3,16,7,17,5,18,1,19], dtype=numpy.int32))
        indices.append(numpy.array([5,20,7,21,6,22,4,23], dtype=numpy.int32))

        polygons = geometry.createPolygons(indices, input_list, "cubematerial")
        self.assertIsNotNone(str(polygons))

        loaded_polygons = collada.polygons.Polygons.load(self.dummy, geometry.sourceById, fromstring(tostring(polygons.xmlnode)))
        self.assertEqual(len(loaded_polygons), 6)

        geometry.primitives.append(polygons)
        geometry.save()

        loaded_geometry = collada.geometry.Geometry.load(self.dummy, {}, fromstring(tostring(geometry.xmlnode)))

        self.assertEqual(len(loaded_geometry.primitives), 1)
        self.assertEqual(len(loaded_geometry.primitives[0]), 6)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_iteration
import numpy
from collada.xmlutil import etree
fromstring = etree.fromstring
tostring = etree.tostring

import collada
from collada.util import unittest


class TestIteration(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_triangle_iterator_vert_normals(self):
        mesh = collada.Collada(validate_output=True)

        vert_floats = [-50,50,50,50,50,50,-50,-50,50,50,-50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
        normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
                         -1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,0,0,-1,0,0,-1,0,0,-1]
        vert_src = collada.source.FloatSource("cubeverts-array", numpy.array(vert_floats), ('X', 'Y', 'Z'))
        normal_src = collada.source.FloatSource("cubenormals-array", numpy.array(normal_floats), ('X', 'Y', 'Z'))
        geometry = collada.geometry.Geometry(mesh, "geometry0", "mycube", [vert_src, normal_src], [])

        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#cubeverts-array")
        input_list.addInput(1, 'NORMAL', "#cubenormals-array")

        indices = numpy.array([0,0,2,1,3,2,0,0,3,2,1,3,0,4,1,5,5,6,0,4,5,6,4,7,6,8,7,9,3,10,6,8,3,10,2,11,0,12,
                        4,13,6,14,0,12,6,14,2,15,3,16,7,17,5,18,3,16,5,18,1,19,5,20,7,21,6,22,5,20,6,22,4,23])
        triangleset = geometry.createTriangleSet(indices, input_list, "cubematerial")
        geometry.primitives.append(triangleset)
        mesh.geometries.append(geometry)

        geomnode = collada.scene.GeometryNode(geometry, [])
        mynode = collada.scene.Node('mynode6', children=[geomnode], transforms=[])
        scene = collada.scene.Scene('myscene', [mynode])
        mesh.scenes.append(scene)
        mesh.scene = scene

        mesh.save()

        geoms = list(mesh.scene.objects('geometry'))
        self.assertEqual(len(geoms), 1)

        prims = list(geoms[0].primitives())
        self.assertEqual(len(prims), 1)

        tris = list(prims[0])
        self.assertEqual(len(tris), 12)

        self.assertEqual(list(tris[0].vertices[0]), [-50.0,  50.0,  50.0])
        self.assertEqual(list(tris[0].vertices[1]), [-50.0,  -50.0,  50.0])
        self.assertEqual(list(tris[0].vertices[2]), [50.0,  -50.0,  50.0])
        self.assertEqual(list(tris[0].normals[0]), [0.0, 0.0, 1.0])
        self.assertEqual(list(tris[0].normals[1]), [0.0, 0.0, 1.0])
        self.assertEqual(list(tris[0].normals[2]), [0.0, 0.0, 1.0])
        self.assertEqual(tris[0].texcoords, [])
        self.assertEqual(tris[0].material, None)
        self.assertEqual(list(tris[0].indices), [0, 2, 3])
        self.assertEqual(list(tris[0].normal_indices), [0, 1, 2])
        self.assertEqual(tris[0].texcoord_indices, [])

    def test_polylist_iterator_vert_normals(self):
        mesh = collada.Collada(validate_output=True)


        vert_floats = [-50,50,50,50,50,50,-50,-50,50,50,-50,50,-50,50,-50,50,50,-50,-50,-50,-50,50,-50,-50]
        normal_floats = [0,0,1,0,0,1,0,0,1,0,0,1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,-1,0,0,
                         -1,0,0,-1,0,0,-1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,0,0,-1,0,0,-1,0,0,-1,0,0,-1]
        vert_src = collada.source.FloatSource("cubeverts-array", numpy.array(vert_floats), ('X', 'Y', 'Z'))
        normal_src = collada.source.FloatSource("cubenormals-array", numpy.array(normal_floats), ('X', 'Y', 'Z'))

        geometry = collada.geometry.Geometry(mesh, "geometry0", "mycube", [vert_src, normal_src], [])

        input_list = collada.source.InputList()
        input_list.addInput(0, 'VERTEX', "#cubeverts-array")
        input_list.addInput(1, 'NORMAL', "#cubenormals-array")

        vcounts = numpy.array([4,4,4,4,4,4])
        indices = numpy.array([0,0,2,1,3,2,1,3,0,4,1,5,5,6,4,7,6,8,7,9,3,10,2,11,0,12,4,13,6,14,2,
                               15,3,16,7,17,5,18,1,19,5,20,7,21,6,22,4,23])
        polylist = geometry.createPolylist(indices, vcounts, input_list, "cubematerial")

        geometry.primitives.append(polylist)
        mesh.geometries.append(geometry)

        geomnode = collada.scene.GeometryNode(geometry, [])
        mynode = collada.scene.Node('mynode6', children=[geomnode], transforms=[])
        scene = collada.scene.Scene('myscene', [mynode])
        mesh.scenes.append(scene)
        mesh.scene = scene

        mesh.save()

        geoms = list(mesh.scene.objects('geometry'))
        self.assertEqual(len(geoms), 1)

        prims = list(geoms[0].primitives())
        self.assertEqual(len(prims), 1)

        poly = list(prims[0])
        self.assertEqual(len(poly), 6)

        self.assertEqual(list(poly[0].vertices[0]), [-50.0,  50.0,  50.0])
        self.assertEqual(list(poly[0].vertices[1]), [-50.0,  -50.0,  50.0])
        self.assertEqual(list(poly[0].vertices[2]), [50.0,  -50.0,  50.0])
        self.assertEqual(list(poly[0].normals[0]), [0.0, 0.0, 1.0])
        self.assertEqual(list(poly[0].normals[1]), [0.0, 0.0, 1.0])
        self.assertEqual(list(poly[0].normals[2]), [0.0, 0.0, 1.0])
        self.assertEqual(poly[0].texcoords, [])
        self.assertEqual(poly[0].material, None)
        self.assertEqual(list(poly[0].indices), [0, 2, 3, 1])
        self.assertEqual(list(poly[0].normal_indices), [0, 1, 2, 3])
        self.assertEqual(poly[0].texcoord_indices, [])

        tris = list(poly[0].triangles())

        self.assertEqual(list(tris[0].vertices[0]), [-50.0,  50.0,  50.0])
        self.assertEqual(list(tris[0].vertices[1]), [-50.0,  -50.0,  50.0])
        self.assertEqual(list(tris[0].vertices[2]), [50.0,  -50.0,  50.0])
        self.assertEqual(list(tris[0].normals[0]), [0.0, 0.0, 1.0])
        self.assertEqual(list(tris[0].normals[1]), [0.0, 0.0, 1.0])
        self.assertEqual(list(tris[0].normals[2]), [0.0, 0.0, 1.0])
        self.assertEqual(tris[0].texcoords, [])
        self.assertEqual(tris[0].material, None)
        self.assertEqual(list(tris[0].indices), [0, 2, 3])
        self.assertEqual(list(tris[0].normal_indices), [0, 1, 2])
        self.assertEqual(tris[0].texcoord_indices, [])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_light
import collada
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestLight(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_directional_light_saving(self):
        dirlight = collada.light.DirectionalLight("mydirlight", (1,1,1))
        self.assertEqual(dirlight.id, "mydirlight")
        self.assertTupleEqual(dirlight.color, (1,1,1))
        self.assertTupleEqual(tuple(dirlight.direction), (0,0,-1))
        self.assertIsNotNone(str(dirlight))
        dirlight.color = (0.1, 0.2, 0.3)
        dirlight.id = "yourdirlight"
        dirlight.save()
        loaded_dirlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(dirlight.xmlnode)))
        self.assertTrue(isinstance(loaded_dirlight, collada.light.DirectionalLight))
        self.assertTupleEqual(loaded_dirlight.color, (0.1, 0.2, 0.3))
        self.assertEqual(loaded_dirlight.id, "yourdirlight")

    def test_ambient_light_saving(self):
        ambientlight = collada.light.AmbientLight("myambientlight", (1,1,1))
        self.assertEqual(ambientlight.id, "myambientlight")
        self.assertTupleEqual(ambientlight.color, (1,1,1))
        self.assertIsNotNone(str(ambientlight))
        ambientlight.color = (0.1, 0.2, 0.3)
        ambientlight.id = "yourambientlight"
        ambientlight.save()
        loaded_ambientlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(ambientlight.xmlnode)))
        self.assertTrue(isinstance(loaded_ambientlight, collada.light.AmbientLight))
        self.assertTupleEqual(ambientlight.color, (0.1, 0.2, 0.3))
        self.assertEqual(ambientlight.id, "yourambientlight")

    def test_point_light_saving(self):
        pointlight = collada.light.PointLight("mypointlight", (1,1,1))
        self.assertEqual(pointlight.id, "mypointlight")
        self.assertTupleEqual(pointlight.color, (1,1,1))
        self.assertEqual(pointlight.quad_att, None)
        self.assertEqual(pointlight.constant_att, None)
        self.assertEqual(pointlight.linear_att, None)
        self.assertEqual(pointlight.zfar, None)
        self.assertIsNotNone(str(pointlight))

        pointlight.color = (0.1, 0.2, 0.3)
        pointlight.constant_att = 0.7
        pointlight.linear_att = 0.8
        pointlight.quad_att = 0.9
        pointlight.id = "yourpointlight"
        pointlight.save()
        loaded_pointlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(pointlight.xmlnode)))
        self.assertTrue(isinstance(loaded_pointlight, collada.light.PointLight))
        self.assertTupleEqual(loaded_pointlight.color, (0.1, 0.2, 0.3))
        self.assertEqual(loaded_pointlight.constant_att, 0.7)
        self.assertEqual(loaded_pointlight.linear_att, 0.8)
        self.assertEqual(loaded_pointlight.quad_att, 0.9)
        self.assertEqual(loaded_pointlight.zfar, None)
        self.assertEqual(loaded_pointlight.id, "yourpointlight")

        loaded_pointlight.zfar = 0.2
        loaded_pointlight.save()
        loaded_pointlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(loaded_pointlight.xmlnode)))
        self.assertEqual(loaded_pointlight.zfar, 0.2)

    def test_spot_light_saving(self):
        spotlight = collada.light.SpotLight("myspotlight", (1,1,1))
        self.assertEqual(spotlight.id, "myspotlight")
        self.assertTupleEqual(spotlight.color, (1,1,1))
        self.assertEqual(spotlight.constant_att, None)
        self.assertEqual(spotlight.linear_att, None)
        self.assertEqual(spotlight.quad_att, None)
        self.assertEqual(spotlight.falloff_ang, None)
        self.assertEqual(spotlight.falloff_exp, None)
        self.assertIsNotNone(str(spotlight))

        spotlight.color = (0.1, 0.2, 0.3)
        spotlight.constant_att = 0.7
        spotlight.linear_att = 0.8
        spotlight.quad_att = 0.9
        spotlight.id = "yourspotlight"
        spotlight.save()
        loaded_spotlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(spotlight.xmlnode)))
        self.assertTrue(isinstance(loaded_spotlight, collada.light.SpotLight))
        self.assertTupleEqual(loaded_spotlight.color, (0.1, 0.2, 0.3))
        self.assertEqual(loaded_spotlight.constant_att, 0.7)
        self.assertEqual(loaded_spotlight.linear_att, 0.8)
        self.assertEqual(loaded_spotlight.quad_att, 0.9)
        self.assertEqual(loaded_spotlight.falloff_ang, None)
        self.assertEqual(loaded_spotlight.falloff_exp, None)
        self.assertEqual(loaded_spotlight.id, "yourspotlight")

        loaded_spotlight.falloff_ang = 180
        loaded_spotlight.falloff_exp = 2
        loaded_spotlight.save()
        loaded_spotlight = collada.light.Light.load(self.dummy, {}, fromstring(tostring(loaded_spotlight.xmlnode)))
        self.assertEqual(loaded_spotlight.falloff_ang, 180)
        self.assertEqual(loaded_spotlight.falloff_exp, 2)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_material
import os
import sys

import collada
from collada.util import unittest
from collada.xmlutil import etree
from collada.material import OPAQUE_MODE

fromstring = etree.fromstring
tostring = etree.tostring


class TestMaterial(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(aux_file_loader = self.image_dummy_loader,
                validate_output=True)

        self.dummy_cimage = collada.material.CImage("yourcimage", "./whatever.tga", self.dummy)
        self.cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        self.dummy.images.append(self.dummy_cimage)
        self.dummy.images.append(self.cimage)
        self.othereffect = collada.material.Effect("othereffect", [], "phong")
        self.dummy.effects.append(self.othereffect)

    def test_effect_saving(self):
        effect = collada.material.Effect("myeffect", [], "phong",
                       emission = (0.1, 0.2, 0.3, 1.0),
                       ambient = (0.4, 0.5, 0.6, 1.0),
                       diffuse = (0.7, 0.8, 0.9, 0.5),
                       specular = (0.3, 0.2, 0.1, 1.0),
                       shininess = 0.4,
                       reflective = (0.7, 0.6, 0.5, 1.0),
                       reflectivity = 0.8,
                       transparent = (0.2, 0.4, 0.6, 1.0),
                       transparency = 0.9)

        self.assertEqual(effect.id, "myeffect")
        self.assertEqual(effect.shininess, 0.4)
        self.assertEqual(effect.reflectivity, 0.8)
        self.assertEqual(effect.transparency, 0.9)
        self.assertTupleEqual(effect.emission, (0.1, 0.2, 0.3, 1.0))
        self.assertTupleEqual(effect.ambient, (0.4, 0.5, 0.6, 1.0))
        self.assertTupleEqual(effect.diffuse, (0.7, 0.8, 0.9, 0.5))
        self.assertTupleEqual(effect.specular, (0.3, 0.2, 0.1, 1.0))
        self.assertTupleEqual(effect.reflective, (0.7, 0.6, 0.5, 1.0))
        self.assertTupleEqual(effect.transparent, (0.2, 0.4, 0.6, 1.0))
        self.assertEqual(effect.double_sided, False)
        self.assertEqual(effect.opaque_mode, OPAQUE_MODE.A_ONE)
        self.assertIsNotNone(str(effect))

        effect.id = "youreffect"
        effect.shininess = 7.0
        effect.reflectivity = 2.0
        effect.transparency = 3.0
        effect.emission = (1.1, 1.2, 1.3, 1.0)
        effect.ambient = (1.4, 1.5, 1.6, 1.0)
        effect.diffuse = (1.7, 1.8, 1.9, 1.0)
        effect.specular = (1.3, 1.2, 1.1, 1.0)
        effect.reflective = (1.7, 1.6, 1.5, 0.3)
        effect.transparent = (1.2, 1.4, 1.6, 1.0)
        effect.opaque_mode = OPAQUE_MODE.RGB_ZERO
        effect.double_sided = True
        effect.save()

        loaded_effect = collada.material.Effect.load(self.dummy, {},
                                    fromstring(tostring(effect.xmlnode)))

        self.assertEqual(loaded_effect.id, "youreffect")
        self.assertEqual(loaded_effect.shininess, 7.0)
        self.assertEqual(loaded_effect.reflectivity, 2.0)
        self.assertEqual(loaded_effect.transparency, 3.0)
        self.assertTupleEqual(loaded_effect.emission, (1.1, 1.2, 1.3, 1.0))
        self.assertTupleEqual(loaded_effect.ambient, (1.4, 1.5, 1.6, 1.0))
        self.assertTupleEqual(loaded_effect.diffuse, (1.7, 1.8, 1.9, 1.0))
        self.assertTupleEqual(loaded_effect.specular, (1.3, 1.2, 1.1, 1.0))
        self.assertTupleEqual(loaded_effect.reflective, (1.7, 1.6, 1.5, 0.3))
        self.assertTupleEqual(loaded_effect.transparent, (1.2, 1.4, 1.6, 1.0))
        self.assertEqual(loaded_effect.opaque_mode, OPAQUE_MODE.RGB_ZERO)
        self.assertEqual(loaded_effect.double_sided, True)

    def image_dummy_loader(self, fname):
        return self.image_return

    def test_cimage_saving(self):
        self.image_return = None
        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        self.assertEqual(cimage.id, "mycimage")
        self.assertEqual(cimage.path, "./whatever.tga")
        cimage.id = "yourcimage"
        cimage.path = "./next.tga"
        cimage.save()
        loaded_cimage = collada.material.CImage.load(self.dummy, {}, fromstring(tostring(cimage.xmlnode)))
        self.assertEqual(loaded_cimage.id, "yourcimage")
        self.assertEqual(loaded_cimage.path, "./next.tga")
        with self.assertRaises(collada.DaeBrokenRefError):
            loaded_cimage.data
        self.assertEqual(loaded_cimage.data, '')
        self.assertEqual(loaded_cimage.pilimage, None)
        self.assertEqual(loaded_cimage.uintarray, None)
        self.assertEqual(loaded_cimage.floatarray, None)
        self.assertIsNotNone(str(cimage))

    def test_cimage_data_loading(self):
        data_dir = os.path.join(os.path.dirname(os.path.realpath( __file__ )), "data")
        texture_file_path = os.path.join(data_dir, "duckCM.tga")
        self.failUnless(os.path.isfile(texture_file_path), "Could not find data/duckCM.tga file for testing")

        texdata = open(texture_file_path, 'rb').read()
        self.assertEqual(len(texdata), 786476)

        self.image_return = texdata
        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        image_data = cimage.data
        self.assertEqual(len(image_data), 786476)
        
        try:
            from PIL import Image as pil
        except ImportError:
            pil = None
            
        if pil is not None:
            pil_image = cimage.pilimage
            self.assertTupleEqual(pil_image.size, (512,512))
            self.assertEqual(pil_image.format, "TGA")

            numpy_uints = cimage.uintarray
            self.assertTupleEqual(numpy_uints.shape, (512, 512, 3))
    
            numpy_floats = cimage.floatarray
            self.assertTupleEqual(numpy_uints.shape, (512, 512, 3))

    def test_surface_saving(self):
        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        surface = collada.material.Surface("mysurface", cimage)
        self.assertEqual(surface.id, "mysurface")
        self.assertEqual(surface.image.id, "mycimage")
        self.assertEqual(surface.format, "A8R8G8B8")
        self.assertIsNotNone(str(surface))
        surface.id = "yoursurface"
        surface.image = self.dummy_cimage
        surface.format = "OtherFormat"
        surface.save()
        loaded_surface = collada.material.Surface.load(self.dummy, {}, fromstring(tostring(surface.xmlnode)))
        self.assertEqual(loaded_surface.id, "yoursurface")
        self.assertEqual(loaded_surface.image.id, "yourcimage")
        self.assertEqual(loaded_surface.format, "OtherFormat")

    def test_surface_empty(self):
        surface1 = """
        <surface xmlns="http://www.collada.org/2005/11/COLLADASchema" type="2D">
        <init_from>file1-image</init_from>
        <format>A8R8G8B8</format>
        </surface>
        """
        self.assertRaises(collada.DaeIncompleteError, collada.material.Surface.load, self.dummy, {}, fromstring(surface1))
        
        surface2 = """
        <newparam xmlns="http://www.collada.org/2005/11/COLLADASchema" sid="file1-surface">
        <surface xmlns="http://www.collada.org/2005/11/COLLADASchema" type="2D">
        <init_from>file1-image</init_from>
        <format>A8R8G8B8</format>
        </surface>
        </newparam>
        """
        self.assertRaises(collada.DaeBrokenRefError, collada.material.Surface.load, self.dummy, {}, fromstring(surface2))
        
        surface3 = """
        <newparam xmlns="http://www.collada.org/2005/11/COLLADASchema" sid="file1-surface">
        <surface xmlns="http://www.collada.org/2005/11/COLLADASchema" type="2D">
        <init_from></init_from>
        <format>A8R8G8B8</format>
        </surface>
        </newparam>
        """
        self.assertRaises(collada.DaeBrokenRefError, collada.material.Surface.load, self.dummy, {}, fromstring(surface3))

    def test_sampler2d_saving(self):
        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        surface = collada.material.Surface("mysurface", cimage)
        sampler2d = collada.material.Sampler2D("mysampler2d", surface)
        self.assertEqual(sampler2d.id, "mysampler2d")
        self.assertEqual(sampler2d.minfilter, None)
        self.assertEqual(sampler2d.magfilter, None)
        self.assertEqual(sampler2d.surface.id, "mysurface")
        sampler2d = collada.material.Sampler2D("mysampler2d", surface, "LINEAR_MIPMAP_LINEAR", "LINEAR")
        self.assertEqual(sampler2d.minfilter, "LINEAR_MIPMAP_LINEAR")
        self.assertEqual(sampler2d.magfilter, "LINEAR")
        self.assertIsNotNone(str(sampler2d))

        other_surface = collada.material.Surface("yoursurface", cimage)
        sampler2d.id = "yoursampler2d"
        sampler2d.minfilter = "QUADRATIC_MIPMAP_WHAT"
        sampler2d.magfilter = "QUADRATIC"
        sampler2d.surface = other_surface
        sampler2d.save()

        loaded_sampler2d = collada.material.Sampler2D.load(self.dummy,
                                {'yoursurface':other_surface}, fromstring(tostring(sampler2d.xmlnode)))
        self.assertEqual(loaded_sampler2d.id, "yoursampler2d")
        self.assertEqual(loaded_sampler2d.surface.id, "yoursurface")
        self.assertEqual(loaded_sampler2d.minfilter, "QUADRATIC_MIPMAP_WHAT")
        self.assertEqual(loaded_sampler2d.magfilter, "QUADRATIC")

    def test_map_saving(self):
        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        surface = collada.material.Surface("mysurface", cimage)
        sampler2d = collada.material.Sampler2D("mysampler2d", surface)
        map = collada.material.Map(sampler2d, "TEX0")
        self.assertEqual(map.sampler.id, "mysampler2d")
        self.assertEqual(map.texcoord, "TEX0")
        self.assertIsNotNone(str(map))

        other_sampler2d = collada.material.Sampler2D("yoursampler2d", surface)
        map.sampler = other_sampler2d
        map.texcoord = "TEX1"
        map.save()

        loaded_map = collada.material.Map.load(self.dummy,
                            {'yoursampler2d': other_sampler2d}, fromstring(tostring(map.xmlnode)))
        self.assertEqual(map.sampler.id, "yoursampler2d")
        self.assertEqual(map.texcoord, "TEX1")

    def test_effect_with_params(self):
        surface = collada.material.Surface("mysurface", self.cimage)
        sampler2d = collada.material.Sampler2D("mysampler2d", surface)
        effect = collada.material.Effect("myeffect", [surface, sampler2d], "phong",
                       emission = (0.1, 0.2, 0.3, 1.0),
                       ambient = (0.4, 0.5, 0.6, 1.0),
                       diffuse = (0.7, 0.8, 0.9, 1.0),
                       specular = (0.3, 0.2, 0.1, 1.0),
                       shininess = 0.4,
                       reflective = (0.7, 0.6, 0.5, 1.0),
                       reflectivity = 0.8,
                       transparent = (0.2, 0.4, 0.6, 1.0),
                       transparency = 0.9,
                       opaque_mode = OPAQUE_MODE.A_ONE)

        other_cimage = collada.material.CImage("yourcimage", "./whatever.tga", self.dummy)
        other_surface = collada.material.Surface("yoursurface", other_cimage)
        other_sampler2d = collada.material.Sampler2D("yoursampler2d", other_surface)
        other_map = collada.material.Map(other_sampler2d, "TEX0")
        effect.params.pop()
        effect.params.append(other_surface)
        effect.params.append(other_sampler2d)
        effect.diffuse = other_map
        effect.transparent = other_map
        effect.save()

        self.dummy.images.append(self.dummy_cimage)
        loaded_effect = collada.material.Effect.load(self.dummy, {}, fromstring(tostring(effect.xmlnode)))
        self.assertEqual(type(loaded_effect.diffuse), collada.material.Map)
        self.assertEqual(type(loaded_effect.transparent), collada.material.Map)
        self.assertEqual(len(loaded_effect.params), 3)
        self.assertTrue(type(loaded_effect.params[0]) is collada.material.Surface)
        self.assertEqual(loaded_effect.params[0].id, "mysurface")
        self.assertTrue(type(loaded_effect.params[1]) is collada.material.Surface)
        self.assertEqual(loaded_effect.params[1].id, "yoursurface")
        self.assertTrue(type(loaded_effect.params[2]) is collada.material.Sampler2D)
        self.assertEqual(loaded_effect.params[2].id, "yoursampler2d")
        self.assertEqual(loaded_effect.opaque_mode, OPAQUE_MODE.A_ONE)

    def test_rgbzero(self):
        effect = collada.material.Effect("myeffect", [], "phong",
                       opaque_mode = OPAQUE_MODE.RGB_ZERO)
        
        self.assertEqual(effect.opaque_mode, OPAQUE_MODE.RGB_ZERO)
        self.assertEqual(effect.transparency, 0.0)
        effect.save()
        
        loaded_effect = collada.material.Effect.load(self.dummy, {}, fromstring(tostring(effect.xmlnode)))
        self.assertEqual(loaded_effect.opaque_mode, OPAQUE_MODE.RGB_ZERO)
        
        effect = collada.material.Effect("myeffect", [], "phong")
        
        self.assertEqual(effect.opaque_mode, OPAQUE_MODE.A_ONE)
        self.assertEqual(effect.transparency, 1.0)
        effect.save()

    def test_material_saving(self):
        effect = collada.material.Effect("myeffect", [], "phong")
        mat = collada.material.Material("mymaterial", "mymat", effect)
        self.assertEqual(mat.id, "mymaterial")
        self.assertEqual(mat.name, "mymat")
        self.assertEqual(mat.effect, effect)
        self.assertIsNotNone(str(mat))

        mat.id = "yourmaterial"
        mat.name = "yourmat"
        mat.effect = self.othereffect
        mat.save()

        loaded_mat = collada.material.Material.load(self.dummy, {}, fromstring(tostring(mat.xmlnode)))
        self.assertEqual(loaded_mat.id, "yourmaterial")
        self.assertEqual(loaded_mat.name, "yourmat")
        self.assertEqual(loaded_mat.effect.id, self.othereffect.id)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_scene
import numpy

import collada
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestScene(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

        self.yourcam = collada.camera.PerspectiveCamera("yourcam", 45.0, 0.01, 1000.0)
        self.dummy.cameras.append(self.yourcam)

        self.yourdirlight = collada.light.DirectionalLight("yourdirlight", (1,1,1))
        self.dummy.lights.append(self.yourdirlight)

        cimage = collada.material.CImage("mycimage", "./whatever.tga", self.dummy)
        surface = collada.material.Surface("mysurface", cimage)
        sampler2d = collada.material.Sampler2D("mysampler2d", surface)
        mymap = collada.material.Map(sampler2d, "TEX0")
        self.effect = collada.material.Effect("myeffect", [surface, sampler2d], "phong",
                       emission = (0.1, 0.2, 0.3),
                       ambient = (0.4, 0.5, 0.6),
                       diffuse = mymap,
                       specular = (0.3, 0.2, 0.1))
        self.effect2 = collada.material.Effect("youreffect", [], "phong",
                       emission = (0.1, 0.2, 0.3),
                       ambient = (0.4, 0.5, 0.6),
                       specular = (0.3, 0.2, 0.1))
        self.dummy.materials.append(self.effect)
        self.dummy.materials.append(self.effect2)

        self.floatsource = collada.source.FloatSource("myfloatsource", numpy.array([0.1,0.2,0.3]), ('X', 'Y', 'Z'))
        self.geometry = collada.geometry.Geometry(self.dummy, "geometry0", "mygeometry", {"myfloatsource":self.floatsource})
        self.geometry2 = collada.geometry.Geometry(self.dummy, "geometry1", "yourgeometry", {"myfloatsource":self.floatsource})
        self.dummy.geometries.append(self.geometry)
        self.dummy.geometries.append(self.geometry2)

    def test_scene_light_node_saving(self):
        dirlight = collada.light.DirectionalLight("mydirlight", (1,1,1))
        lightnode = collada.scene.LightNode(dirlight)
        bindtest = list(lightnode.objects('light'))
        self.assertEqual(lightnode.light, dirlight)
        self.assertEqual(len(bindtest), 1)
        self.assertEqual(bindtest[0].original, dirlight)
        self.assertIsNotNone(str(lightnode))

        lightnode.light = self.yourdirlight
        lightnode.save()

        loadedlightnode = collada.scene.LightNode.load(self.dummy, fromstring(tostring(lightnode.xmlnode)))
        self.assertEqual(loadedlightnode.light.id, 'yourdirlight')

    def test_scene_camera_node_saving(self):
        cam = collada.camera.PerspectiveCamera("mycam", 45.0, 0.01, 1000.0)
        camnode = collada.scene.CameraNode(cam)
        bindtest = list(camnode.objects('camera'))
        self.assertEqual(camnode.camera, cam)
        self.assertEqual(len(bindtest), 1)
        self.assertEqual(bindtest[0].original, cam)
        self.assertIsNotNone(str(camnode))

        camnode.camera = self.yourcam
        camnode.save()

        loadedcamnode = collada.scene.CameraNode.load(self.dummy, fromstring(tostring(camnode.xmlnode)))
        self.assertEqual(loadedcamnode.camera.id, 'yourcam')

    def test_scene_translate_node(self):
        translate = collada.scene.TranslateTransform(0.1, 0.2, 0.3)
        self.assertAlmostEqual(translate.x, 0.1)
        self.assertAlmostEqual(translate.y, 0.2)
        self.assertAlmostEqual(translate.z, 0.3)
        self.assertIsNotNone(str(translate))
        loaded_translate = collada.scene.TranslateTransform.load(self.dummy, fromstring(tostring(translate.xmlnode)))
        self.assertAlmostEqual(loaded_translate.x, 0.1)
        self.assertAlmostEqual(loaded_translate.y, 0.2)
        self.assertAlmostEqual(loaded_translate.z, 0.3)

    def test_scene_rotate_node(self):
        rotate = collada.scene.RotateTransform(0.1, 0.2, 0.3, 90)
        self.assertAlmostEqual(rotate.x, 0.1)
        self.assertAlmostEqual(rotate.y, 0.2)
        self.assertAlmostEqual(rotate.z, 0.3)
        self.assertAlmostEqual(rotate.angle, 90)
        self.assertIsNotNone(str(rotate))
        loaded_rotate = collada.scene.RotateTransform.load(self.dummy, fromstring(tostring(rotate.xmlnode)))
        self.assertAlmostEqual(loaded_rotate.x, 0.1)
        self.assertAlmostEqual(loaded_rotate.y, 0.2)
        self.assertAlmostEqual(loaded_rotate.z, 0.3)
        self.assertAlmostEqual(loaded_rotate.angle, 90)

    def test_scene_scale_node(self):
        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        self.assertAlmostEqual(scale.x, 0.1)
        self.assertAlmostEqual(scale.y, 0.2)
        self.assertAlmostEqual(scale.z, 0.3)
        self.assertIsNotNone(str(scale))
        loaded_scale = collada.scene.ScaleTransform.load(self.dummy, fromstring(tostring(scale.xmlnode)))
        self.assertAlmostEqual(loaded_scale.x, 0.1)
        self.assertAlmostEqual(loaded_scale.y, 0.2)
        self.assertAlmostEqual(loaded_scale.z, 0.3)

    def test_scene_matrix_node(self):
        matrix = collada.scene.MatrixTransform(numpy.array([1.0,0,0,2, 0,1,0,3, 0,0,1,4, 0,0,0,1]))
        self.assertAlmostEqual(matrix.matrix[0][0], 1.0)
        self.assertIsNotNone(str(matrix))
        loaded_matrix = collada.scene.MatrixTransform.load(self.dummy, fromstring(tostring(matrix.xmlnode)))
        self.assertAlmostEqual(loaded_matrix.matrix[0][0], 1.0)

    def test_scene_lookat_node(self):
        eye = numpy.array([2.0,0,3])
        interest = numpy.array([0.0,0,0])
        upvector = numpy.array([0.0,1,0])
        lookat = collada.scene.LookAtTransform(eye, interest, upvector)
        self.assertListEqual(list(lookat.eye), list(eye))
        self.assertListEqual(list(lookat.interest), list(interest))
        self.assertListEqual(list(lookat.upvector), list(upvector))
        self.assertIsNotNone(str(lookat))
        loaded_lookat = collada.scene.LookAtTransform.load(self.dummy, fromstring(tostring(lookat.xmlnode)))
        self.assertListEqual(list(loaded_lookat.eye), list(eye))
        self.assertListEqual(list(loaded_lookat.interest), list(interest))
        self.assertListEqual(list(loaded_lookat.upvector), list(upvector))

    def test_scene_node_combos(self):
        emptynode = collada.scene.Node('myemptynode')
        self.assertEqual(len(emptynode.children), 0)
        self.assertEqual(len(emptynode.transforms), 0)
        self.assertIsNotNone(str(emptynode))
        loadedempty = collada.scene.Node.load(self.dummy, fromstring(tostring(emptynode.xmlnode)), {})
        self.assertEqual(len(loadedempty.children), 0)
        self.assertEqual(len(loadedempty.transforms), 0)

        justchildren = collada.scene.Node('myjustchildrennode', children=[emptynode])
        self.assertEqual(len(justchildren.children), 1)
        self.assertEqual(len(justchildren.transforms), 0)
        self.assertEqual(justchildren.children[0], emptynode)
        loadedjustchildren = collada.scene.Node.load(self.dummy, fromstring(tostring(justchildren.xmlnode)), {})
        self.assertEqual(len(loadedjustchildren.children), 1)
        self.assertEqual(len(loadedjustchildren.transforms), 0)

        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        justtransform = collada.scene.Node('myjusttransformnode', transforms=[scale])
        self.assertEqual(len(justtransform.children), 0)
        self.assertEqual(len(justtransform.transforms), 1)
        self.assertEqual(justtransform.transforms[0], scale)
        loadedjusttransform = collada.scene.Node.load(self.dummy, fromstring(tostring(justtransform.xmlnode)), {})
        self.assertEqual(len(loadedjusttransform.children), 0)
        self.assertEqual(len(loadedjusttransform.transforms), 1)

        both = collada.scene.Node('mybothnode', children=[justchildren, justtransform], transforms=[scale])
        self.assertEqual(len(both.children), 2)
        self.assertEqual(len(both.transforms), 1)
        self.assertEqual(both.transforms[0], scale)
        self.assertEqual(both.children[0], justchildren)
        self.assertEqual(both.children[1], justtransform)
        loadedboth = collada.scene.Node.load(self.dummy, fromstring(tostring(both.xmlnode)), {})
        self.assertEqual(len(both.children), 2)
        self.assertEqual(len(both.transforms), 1)

    def test_scene_node_saving(self):
        myemptynode = collada.scene.Node('myemptynode')
        rotate = collada.scene.RotateTransform(0.1, 0.2, 0.3, 90)
        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        mynode = collada.scene.Node('mynode', children=[myemptynode], transforms=[rotate, scale])
        self.assertEqual(mynode.id, 'mynode')
        self.assertEqual(mynode.children[0], myemptynode)
        self.assertEqual(mynode.transforms[0], rotate)
        self.assertEqual(mynode.transforms[1], scale)

        translate = collada.scene.TranslateTransform(0.1, 0.2, 0.3)
        mynode.transforms.append(translate)
        mynode.transforms.pop(0)
        youremptynode = collada.scene.Node('youremptynode')
        mynode.children.append(youremptynode)
        mynode.id = 'yournode'
        mynode.save()

        yournode = collada.scene.Node.load(self.dummy, fromstring(tostring(mynode.xmlnode)), {})
        self.assertEqual(yournode.id, 'yournode')
        self.assertEqual(len(yournode.children), 2)
        self.assertEqual(len(yournode.transforms), 2)
        self.assertEqual(yournode.children[0].id, 'myemptynode')
        self.assertEqual(yournode.children[1].id, 'youremptynode')
        self.assertTrue(type(yournode.transforms[0]) is collada.scene.ScaleTransform)
        self.assertTrue(type(yournode.transforms[1]) is collada.scene.TranslateTransform)

    def test_scene_material_node(self):
        binding1 = ("TEX0", "TEXCOORD", "0")
        binding2 = ("TEX1", "TEXCOORD", "1")
        binding3 = ("TEX2", "TEXCOORD", "2")
        matnode = collada.scene.MaterialNode("mygeommatref", self.effect, [binding1, binding2])

        self.assertEqual(matnode.target, self.effect)
        self.assertEqual(matnode.symbol, "mygeommatref")
        self.assertListEqual(matnode.inputs, [binding1, binding2])
        self.assertIsNotNone(str(matnode))
        matnode.save()
        self.assertEqual(matnode.target, self.effect)
        self.assertEqual(matnode.symbol, "mygeommatref")
        self.assertListEqual(matnode.inputs, [binding1, binding2])

        matnode.symbol = 'yourgeommatref'
        matnode.target = self.effect2
        matnode.inputs.append(binding3)
        matnode.inputs.pop(0)
        matnode.save()

        loaded_matnode = collada.scene.MaterialNode.load(self.dummy, fromstring(tostring(matnode.xmlnode)))
        self.assertEqual(loaded_matnode.target.id, self.effect2.id)
        self.assertEqual(loaded_matnode.symbol, "yourgeommatref")
        self.assertListEqual(loaded_matnode.inputs, [binding2, binding3])

    def test_scene_geometry_node(self):
        binding = ("TEX0", "TEXCOORD", "0")
        matnode = collada.scene.MaterialNode("mygeommatref", self.effect, [binding])
        geomnode = collada.scene.GeometryNode(self.geometry, [matnode])

        bindtest = list(geomnode.objects('geometry'))
        self.assertEqual(len(bindtest), 1)
        self.assertEqual(bindtest[0].original, self.geometry)
        self.assertEqual(geomnode.geometry, self.geometry)
        self.assertListEqual(geomnode.materials, [matnode])
        self.assertIsNotNone(str(geomnode))
        geomnode.save()
        bindtest = list(geomnode.objects('geometry'))
        self.assertEqual(len(bindtest), 1)
        self.assertEqual(bindtest[0].original, self.geometry)
        self.assertEqual(geomnode.geometry, self.geometry)
        self.assertListEqual(geomnode.materials, [matnode])

        matnode2 = collada.scene.MaterialNode("yourgeommatref", self.effect, [binding])
        geomnode.materials.append(matnode2)
        geomnode.materials.pop(0)
        geomnode.geometry = self.geometry2
        geomnode.save()

        loaded_geomnode = collada.scene.loadNode(self.dummy, fromstring(tostring(geomnode.xmlnode)), {})
        self.assertEqual(loaded_geomnode.geometry.id, self.geometry2.id)
        self.assertEqual(len(loaded_geomnode.materials), 1)
        self.assertEqual(loaded_geomnode.materials[0].target, matnode2.target)
        self.assertEqual(loaded_geomnode.materials[0].symbol, "yourgeommatref")
        self.assertListEqual(loaded_geomnode.materials[0].inputs, [binding])

    def test_scene_node_with_instances(self):
        binding = ("TEX0", "TEXCOORD", "0")
        matnode = collada.scene.MaterialNode("mygeommatref", self.effect, [binding])
        geomnode = collada.scene.GeometryNode(self.geometry, [matnode])
        camnode = collada.scene.CameraNode(self.yourcam)
        lightnode = collada.scene.LightNode(self.yourdirlight)
        myemptynode = collada.scene.Node('myemptynode')
        rotate = collada.scene.RotateTransform(0.1, 0.2, 0.3, 90)
        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        mynode = collada.scene.Node('mynode',
                                    children=[myemptynode, geomnode, camnode, lightnode],
                                    transforms=[rotate, scale])

        self.assertEqual(len(mynode.children), 4)
        self.assertEqual(mynode.children[0], myemptynode)
        self.assertEqual(mynode.children[1], geomnode)
        self.assertEqual(mynode.children[2], camnode)
        self.assertEqual(mynode.children[3], lightnode)
        self.assertEqual(mynode.transforms[0], rotate)
        self.assertEqual(mynode.transforms[1], scale)

        mynode.id = 'yournode'
        mynode.children.pop(0)
        mynode.save()

        yournode = collada.scene.Node.load(self.dummy, fromstring(tostring(mynode.xmlnode)), {})
        self.assertEqual(yournode.id, 'yournode')
        self.assertEqual(len(yournode.children), 3)
        self.assertEqual(len(yournode.transforms), 2)
        self.assertEqual(yournode.children[0].geometry.id, self.geometry.id)
        self.assertEqual(yournode.children[1].camera.id, self.yourcam.id)
        self.assertEqual(yournode.children[2].light.id, self.yourdirlight.id)
        self.assertTrue(type(yournode.transforms[0]) is collada.scene.RotateTransform)
        self.assertTrue(type(yournode.transforms[1]) is collada.scene.ScaleTransform)

    def test_scene_with_nodes(self):
        rotate = collada.scene.RotateTransform(0.1, 0.2, 0.3, 90)
        scale = collada.scene.ScaleTransform(0.1, 0.2, 0.3)
        mynode = collada.scene.Node('mynode', children=[], transforms=[rotate, scale])
        yournode = collada.scene.Node('yournode', children=[], transforms=[])
        othernode = collada.scene.Node('othernode', children=[], transforms=[])
        scene = collada.scene.Scene('myscene', [mynode, yournode, othernode])

        self.assertEqual(scene.id, 'myscene')
        self.assertEqual(len(scene.nodes), 3)
        self.assertEqual(scene.nodes[0], mynode)
        self.assertEqual(scene.nodes[1], yournode)
        self.assertEqual(scene.nodes[2], othernode)

        scene.id = 'yourscene'
        scene.nodes.pop(1)
        anothernode = collada.scene.Node('anothernode')
        scene.nodes.append(anothernode)
        scene.save()

        loaded_scene = collada.scene.Scene.load(self.dummy, fromstring(tostring(scene.xmlnode)))

        self.assertEqual(loaded_scene.id, 'yourscene')
        self.assertEqual(len(loaded_scene.nodes), 3)
        self.assertEqual(loaded_scene.nodes[0].id, 'mynode')
        self.assertEqual(loaded_scene.nodes[1].id, 'othernode')
        self.assertEqual(loaded_scene.nodes[2].id, 'anothernode')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_source
import numpy

import collada
from collada.util import unittest
from collada.xmlutil import etree

fromstring = etree.fromstring
tostring = etree.tostring


class TestSource(unittest.TestCase):

    def setUp(self):
        self.dummy = collada.Collada(validate_output=True)

    def test_float_source_saving(self):
        floatsource = collada.source.FloatSource("myfloatsource", numpy.array([0.1,0.2,0.3]), ('X', 'Y', 'X'))
        self.assertEqual(floatsource.id, "myfloatsource")
        self.assertEqual(len(floatsource), 1)
        self.assertTupleEqual(floatsource.components, ('X', 'Y', 'X'))
        self.assertIsNotNone(str(floatsource))
        floatsource.id = "yourfloatsource"
        floatsource.components = ('S', 'T')
        floatsource.data = numpy.array([0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        floatsource.save()
        loaded_floatsource = collada.source.Source.load(self.dummy, {}, fromstring(tostring(floatsource.xmlnode)))
        self.assertTrue(isinstance(loaded_floatsource, collada.source.FloatSource))
        self.assertEqual(floatsource.id, "yourfloatsource")
        self.assertEqual(len(floatsource), 3)
        self.assertTupleEqual(floatsource.components, ('S', 'T'))

    def test_idref_source_saving(self):
        idrefsource = collada.source.IDRefSource("myidrefsource",
                                numpy.array(['Ref1', 'Ref2'], dtype=numpy.string_),
                                ('MORPH_TARGET',))
        self.assertEqual(idrefsource.id, "myidrefsource")
        self.assertEqual(len(idrefsource), 2)
        self.assertTupleEqual(idrefsource.components, ('MORPH_TARGET',))
        self.assertIsNotNone(str(idrefsource))
        idrefsource.id = "youridrefsource"
        idrefsource.components = ('JOINT_TARGET', 'WHATEVER_TARGET')
        idrefsource.data = numpy.array(['Ref5', 'Ref6', 'Ref7', 'Ref8', 'Ref9', 'Ref10'], dtype=numpy.string_)
        idrefsource.save()
        loaded_idrefsource = collada.source.Source.load(self.dummy, {}, fromstring(tostring(idrefsource.xmlnode)))
        self.assertTrue(isinstance(loaded_idrefsource, collada.source.IDRefSource))
        self.assertEqual(loaded_idrefsource.id, "youridrefsource")
        self.assertEqual(len(loaded_idrefsource), 3)
        self.assertTupleEqual(loaded_idrefsource.components, ('JOINT_TARGET', 'WHATEVER_TARGET'))

    def test_name_source_saving(self):
        namesource = collada.source.NameSource("mynamesource",
                                numpy.array(['Name1', 'Name2'], dtype=numpy.string_),
                                ('JOINT',))
        self.assertEqual(namesource.id, "mynamesource")
        self.assertEqual(len(namesource), 2)
        self.assertTupleEqual(namesource.components, ('JOINT',))
        self.assertIsNotNone(str(namesource))
        namesource.id = "yournamesource"
        namesource.components = ('WEIGHT', 'WHATEVER')
        namesource.data = numpy.array(['Name1', 'Name2', 'Name3', 'Name4', 'Name5', 'Name6'], dtype=numpy.string_)
        namesource.save()
        loaded_namesource = collada.source.Source.load(self.dummy, {}, fromstring(tostring(namesource.xmlnode)))
        self.assertTrue(isinstance(loaded_namesource, collada.source.NameSource))
        self.assertEqual(loaded_namesource.id, "yournamesource")
        self.assertEqual(len(loaded_namesource), 3)
        self.assertTupleEqual(loaded_namesource.components, ('WEIGHT', 'WHATEVER'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = triangleset
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""Module containing classes and functions for the <triangles> primitive."""

import numpy

from collada import primitive
from collada.common import E, tag
from collada.common import DaeIncompleteError, DaeBrokenRefError, \
        DaeMalformedError, DaeUnsupportedError
from collada.util import toUnitVec, checkSource, normalize_v3, dot_v3, xrange
from collada.xmlutil import etree as ElementTree


class Triangle(object):
    """Single triangle representation."""
    def __init__(self, indices, vertices, normal_indices, normals,
            texcoord_indices, texcoords, material):
        """A triangle should not be created manually."""

        self.vertices = vertices
        """A (3, 3) float array for points in the triangle"""
        self.normals = normals
        """A (3, 3) float array with the normals for points in the triangle.
        If the triangle didn't have normals, they will be computed."""
        self.texcoords = texcoords
        """A tuple with (3, 2) float arrays with the texture coordinates
          for the points in the triangle"""
        self.material = material
        """If coming from an unbound :class:`collada.triangleset.TriangleSet`, contains a
          string with the material symbol. If coming from a bound
          :class:`collada.triangleset.BoundTriangleSet`, contains the actual
          :class:`collada.material.Effect` the triangle is bound to."""
        self.indices = indices
        """A (3,) int array with vertex indexes of the 3 vertices in
           the vertex array"""
        self.normal_indices = normal_indices
        """A (3,) int array with normal indexes of the 3 vertices in
           the normal array"""
        self.texcoord_indices = texcoord_indices
        """A (3,2) int array with texture coordinate indexes of the 3
           vertices in the texcoord array."""

        if self.normals is None:
            #generate normals
            vec1 = numpy.subtract(vertices[0], vertices[1])
            vec2 = numpy.subtract(vertices[2], vertices[0])
            vec3 = toUnitVec(numpy.cross(toUnitVec(vec2), toUnitVec(vec1)))
            self.normals = numpy.array([vec3, vec3, vec3])

    def __repr__(self):
        return '<Triangle (%s, %s, %s, "%s")>' % (str(self.vertices[0]),
                str(self.vertices[1]), str(self.vertices[2]),
                str(self.material))
    def __str__(self):
        return repr(self)


class TriangleSet(primitive.Primitive):
    """Class containing the data COLLADA puts in a <triangles> tag, a collection of
    triangles.

    * The TriangleSet object is read-only. To modify a TriangleSet, create a new
      instance using :meth:`collada.geometry.Geometry.createTriangleSet`.
    * If ``T`` is an instance of :class:`collada.triangleset.TriangleSet`, then ``len(T)``
      returns the number of triangles in the set. ``T[i]`` returns the i\ :sup:`th`
      triangle in the set.
    """

    def __init__(self, sources, material, index, xmlnode=None):
        """A TriangleSet should not be created manually. Instead, call the
        :meth:`collada.geometry.Geometry.createTriangleSet` method after
        creating a geometry instance.
        """

        if len(sources) == 0: raise DaeIncompleteError('A triangle set needs at least one input for vertex positions')
        if not 'VERTEX' in sources: raise DaeIncompleteError('Triangle set requires vertex input')

        max_offset = max([ max([input[0] for input in input_type_array])
                          for input_type_array in sources.values()
                          if len(input_type_array) > 0])

        self.material = material
        self.index = index
        self.indices = self.index
        self.nindices = max_offset + 1
        self.index.shape = (-1, 3, self.nindices)
        self.ntriangles = len(self.index)
        self.sources = sources

        if len(self.index) > 0:
            self._vertex = sources['VERTEX'][0][4].data
            self._vertex_index = self.index[:,:, sources['VERTEX'][0][0]]
            self.maxvertexindex = numpy.max( self._vertex_index )
            checkSource(sources['VERTEX'][0][4], ('X', 'Y', 'Z'), self.maxvertexindex)
        else:
            self._vertex = None
            self._vertex_index = None
            self.maxvertexindex = -1

        if 'NORMAL' in sources and len(sources['NORMAL']) > 0 and len(self.index) > 0:
            self._normal = sources['NORMAL'][0][4].data
            self._normal_index = self.index[:,:, sources['NORMAL'][0][0]]
            self.maxnormalindex = numpy.max( self._normal_index )
            checkSource(sources['NORMAL'][0][4], ('X', 'Y', 'Z'), self.maxnormalindex)
        else:
            self._normal = None
            self._normal_index = None
            self.maxnormalindex = -1

        if 'TEXCOORD' in sources and len(sources['TEXCOORD']) > 0 and len(self.index) > 0:
            self._texcoordset = tuple([texinput[4].data for texinput in sources['TEXCOORD']])
            self._texcoord_indexset = tuple([ self.index[:,:, sources['TEXCOORD'][i][0]]
                                             for i in xrange(len(sources['TEXCOORD'])) ])
            self.maxtexcoordsetindex = [ numpy.max( tex_index ) for tex_index in self._texcoord_indexset ]
            for i, texinput in enumerate(sources['TEXCOORD']):
                checkSource(texinput[4], ('S', 'T'), self.maxtexcoordsetindex[i])
        else:
            self._texcoordset = tuple()
            self._texcoord_indexset = tuple()
            self.maxtexcoordsetindex = -1

        if 'TEXTANGENT' in sources and len(sources['TEXTANGENT']) > 0 and len(self.index) > 0:
            self._textangentset = tuple([texinput[4].data for texinput in sources['TEXTANGENT']])
            self._textangent_indexset = tuple([ self.index[:,:, sources['TEXTANGENT'][i][0]]
                                             for i in xrange(len(sources['TEXTANGENT'])) ])
            self.maxtextangentsetindex = [ numpy.max( tex_index ) for tex_index in self._textangent_indexset ]
            for i, texinput in enumerate(sources['TEXTANGENT']):
                checkSource(texinput[4], ('X', 'Y', 'Z'), self.maxtextangentsetindex[i])
        else:
            self._textangentset = tuple()
            self._textangent_indexset = tuple()
            self.maxtextangentsetindex = -1

        if 'TEXBINORMAL' in sources and len(sources['TEXBINORMAL']) > 0 and len(self.index) > 0:
            self._texbinormalset = tuple([texinput[4].data for texinput in sources['TEXBINORMAL']])
            self._texbinormal_indexset = tuple([ self.index[:,:, sources['TEXBINORMAL'][i][0]]
                                             for i in xrange(len(sources['TEXBINORMAL'])) ])
            self.maxtexbinormalsetindex = [ numpy.max( tex_index ) for tex_index in self._texbinormal_indexset ]
            for i, texinput in enumerate(sources['TEXBINORMAL']):
                checkSource(texinput[4], ('X', 'Y', 'Z'), self.maxtexbinormalsetindex[i])
        else:
            self._texbinormalset = tuple()
            self._texbinormal_indexset = tuple()
            self.maxtexbinormalsetindex = -1

        if xmlnode is not None: self.xmlnode = xmlnode
        else:
            self._recreateXmlNode()

    def __len__(self):
        return len(self.index)

    def _recreateXmlNode(self):
        self.index.shape = (-1)
        acclen = len(self.index)
        txtindices = ' '.join(map(str, self.index.tolist()))
        self.index.shape = (-1, 3, self.nindices)

        self.xmlnode = E.triangles(count=str(self.ntriangles))
        if self.material is not None:
            self.xmlnode.set('material', self.material)

        all_inputs = []
        for semantic_list in self.sources.values():
            all_inputs.extend(semantic_list)
        for offset, semantic, sourceid, set, src in all_inputs:
            inpnode = E.input(offset=str(offset), semantic=semantic, source=sourceid)
            if set is not None:
                inpnode.set('set', str(set))
            self.xmlnode.append(inpnode)

        self.xmlnode.append(E.p(txtindices))

    def __getitem__(self, i):
        v = self._vertex[ self._vertex_index[i] ]
        n = self._normal[ self._normal_index[i] ] if self._normal is not None else None
        uvindices = []
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uvindices.append( uvindex[i] )
            uv.append( self._texcoordset[j][ uvindex[i] ] )
        return Triangle(self._vertex_index[i], v, self._normal_index[i] if self._normal_index is not None else 0, n, uvindices, uv, self.material)

    @staticmethod
    def load( collada, localscope, node ):
        indexnode = node.find(tag('p'))
        if indexnode is None: raise DaeIncompleteError('Missing index in triangle set')

        source_array = primitive.Primitive._getInputs(collada, localscope, node.findall(tag('input')))

        try:
            if indexnode.text is None:
                index = numpy.array([], dtype=numpy.int32)
            else:
                index = numpy.fromstring(indexnode.text, dtype=numpy.int32, sep=' ')
            index[numpy.isnan(index)] = 0
        except:
            raise DaeMalformedError('Corrupted index in triangleset')

        triset = TriangleSet(source_array, node.get('material'), index, node)
        triset.xmlnode = node
        return triset

    def bind(self, matrix, materialnodebysymbol):
        """Create a bound triangle set from this triangle set, transform and material mapping"""
        return BoundTriangleSet( self, matrix, materialnodebysymbol)

    def generateNormals(self):
        """If :attr:`normals` is `None` or you wish for normals to be
        recomputed, call this method to recompute them."""
        norms = numpy.zeros( self._vertex.shape, dtype=self._vertex.dtype )
        tris = self._vertex[self._vertex_index]
        n = numpy.cross( tris[::,1] - tris[::,0], tris[::,2] - tris[::,0] )
        normalize_v3(n)
        norms[ self._vertex_index[:,0] ] += n
        norms[ self._vertex_index[:,1] ] += n
        norms[ self._vertex_index[:,2] ] += n
        normalize_v3(norms)

        self._normal = norms
        self._normal_index = self._vertex_index

    def generateTexTangentsAndBinormals(self):
        """If there are no texture tangents, this method will compute them.
        Texture coordinates must exist and it uses the first texture coordinate set."""

        #The following is taken from:
        # http://www.terathon.com/code/tangent.html
        # It's pretty much a direct translation, using numpy arrays

        tris = self._vertex[self._vertex_index]
        uvs = self._texcoordset[0][self._texcoord_indexset[0]]

        x1 = tris[:,1,0]-tris[:,0,0]
        x2 = tris[:,2,0]-tris[:,1,0]
        y1 = tris[:,1,1]-tris[:,0,1]
        y2 = tris[:,2,1]-tris[:,1,1]
        z1 = tris[:,1,2]-tris[:,0,2]
        z2 = tris[:,2,2]-tris[:,1,2]

        s1 = uvs[:,1,0]-uvs[:,0,0]
        s2 = uvs[:,2,0]-uvs[:,1,0]
        t1 = uvs[:,1,1]-uvs[:,0,1]
        t2 = uvs[:,2,1]-uvs[:,1,1]

        r = 1.0 / (s1 * t2 - s2 * t1)

        sdirx = (t2 * x1 - t1 * x2) * r
        sdiry = (t2 * y1 - t1 * y2) * r
        sdirz = (t2 * z1 - t1 * z2) * r
        sdir = numpy.vstack((sdirx, sdiry, sdirz)).T

        tans1 = numpy.zeros( self._vertex.shape, dtype=self._vertex.dtype )
        tans1[ self._vertex_index[:,0] ] += sdir
        tans1[ self._vertex_index[:,1] ] += sdir
        tans1[ self._vertex_index[:,2] ] += sdir

        norm = self._normal[self._normal_index]
        norm.shape = (-1, 3)
        tan1 = tans1[self._vertex_index]
        tan1.shape = (-1, 3)

        tangent = normalize_v3(tan1 - norm * dot_v3(norm, tan1)[:,numpy.newaxis])

        self._textangentset = (tangent,)
        self._textangent_indexset = (numpy.arange(len(self._vertex_index)*3, dtype=self._vertex_index.dtype),)
        self._textangent_indexset[0].shape = (len(self._vertex_index), 3)

        tdirx = (s1 * x2 - s2 * x1) * r
        tdiry = (s1 * y2 - s2 * y1) * r
        tdirz = (s1 * z2 - s2 * z1) * r
        tdir = numpy.vstack((tdirx, tdiry, tdirz)).T

        tans2 = numpy.zeros( self._vertex.shape, dtype=self._vertex.dtype )
        tans2[ self._vertex_index[:,0] ] += tdir
        tans2[ self._vertex_index[:,1] ] += tdir
        tans2[ self._vertex_index[:,2] ] += tdir

        tan2 = tans2[self._vertex_index]
        tan2.shape = (-1, 3)

        tanw = dot_v3(numpy.cross(norm, tan1), tan2)
        tanw = numpy.sign(tanw)

        binorm = numpy.cross(norm, tangent).flatten()
        binorm.shape = (-1, 3)
        binorm = binorm * tanw[:,numpy.newaxis]

        self._texbinormalset = (binorm,)
        self._texbinormal_indexset = (numpy.arange(len(self._vertex_index) * 3,
            dtype=self._vertex_index.dtype),)
        self._texbinormal_indexset[0].shape = (len(self._vertex_index), 3)

    def __str__(self):
        return '<TriangleSet length=%d>' % len(self)

    def __repr__(self):
        return str(self)


class BoundTriangleSet(primitive.BoundPrimitive):
    """A triangle set bound to a transform matrix and materials mapping.

    * If ``T`` is an instance of :class:`collada.triangleset.BoundTriangleSet`, then ``len(T)``
      returns the number of triangles in the set. ``T[i]`` returns the i\ :sup:`th`
      triangle in the set.
    """

    def __init__(self, ts, matrix, materialnodebysymbol):
        """Create a bound triangle set from a triangle set, transform and material mapping.
        This gets created when a triangle set is instantiated in a scene. Do not create this manually."""
        M = numpy.asmatrix(matrix).transpose()
        self._vertex = None if ts.vertex is None else numpy.asarray(ts._vertex * M[:3,:3]) + matrix[:3,3]
        self._normal = None if ts._normal is None else numpy.asarray(ts._normal * M[:3,:3])
        self._texcoordset = ts._texcoordset
        self._textangentset = ts._textangentset
        self._texbinormalset = ts._texbinormalset
        matnode = materialnodebysymbol.get( ts.material )
        if matnode:
            self.material = matnode.target
            self.inputmap = dict([ (sem, (input_sem, set)) for sem, input_sem, set in matnode.inputs ])
        else: self.inputmap = self.material = None
        self.index = ts.index
        self._vertex_index = ts._vertex_index
        self._normal_index = ts._normal_index
        self._texcoord_indexset = ts._texcoord_indexset
        self._textangent_indexset = ts._textangent_indexset
        self._texbinormal_indexset = ts._texbinormal_indexset
        self.ntriangles = ts.ntriangles
        self.original = ts

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        vindex = self._vertex_index[i]
        v = self._vertex[vindex]

        if self._normal is None:
            n = None
            nindex = None
        else:
            nindex = self._normal_index[i]
            n = self._normal[nindex]

        uvindices = []
        uv = []
        for j, uvindex in enumerate(self._texcoord_indexset):
            uvindices.append(uvindex[i])
            uv.append(self._texcoordset[j][uvindex[i]])

        return Triangle(vindex, v, nindex, n, uvindices, uv, self.material)

    def triangles(self):
        """Iterate through all the triangles contained in the set.

        :rtype: generator of :class:`collada.triangleset.Triangle`
        """
        for i in xrange(self.ntriangles): yield self[i]

    def shapes(self):
        """Iterate through all the triangles contained in the set.

        :rtype: generator of :class:`collada.triangleset.Triangle`
        """
        return self.triangles()

    def generateNormals(self):
        """If :attr:`normals` is `None` or you wish for normals to be
        recomputed, call this method to recompute them."""
        norms = numpy.zeros( self._vertex.shape, dtype=self._vertex.dtype )
        tris = self._vertex[self._vertex_index]
        n = numpy.cross( tris[::,1] - tris[::,0], tris[::,2] - tris[::,0] )
        normalize_v3(n)
        norms[ self._vertex_index[:,0] ] += n
        norms[ self._vertex_index[:,1] ] += n
        norms[ self._vertex_index[:,2] ] += n
        normalize_v3(norms)

        self._normal = norms
        self._normal_index = self._vertex_index

    def __str__(self):
        return '<BoundTriangleSet length=%d>' % len(self)

    def __repr__(self):
        return str(self)


########NEW FILE########
__FILENAME__ = util
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

"""This module contains utility functions"""

import numpy
import math
import sys

if sys.version_info[0] > 2:
    import unittest
    from io import StringIO, BytesIO

    bytes = bytes
    basestring = (str,bytes)
    xrange = range
else:
    import unittest
    if not hasattr(unittest.TestCase, "assertIsNone"):
        # external dependency unittest2 required for Python <= 2.6
        import unittest2 as unittest
    from StringIO import StringIO

    BytesIO = StringIO
    def bytes(s, encoding='utf-8'):
        return s
    basestring = basestring
    xrange = xrange

from collada.common import DaeMalformedError, E, tag


def falmostEqual(a, b, rtol=1.0000000000000001e-05, atol=1e-08):
    """Checks if the given floats are almost equal. Uses the algorithm
    from numpy.allclose.

    :param float a:
      First float to compare
    :param float b:
      Second float to compare
    :param float rtol:
      The relative tolerance parameter
    :param float atol:
      The absolute tolerance parameter

    :rtype: bool

    """

    return math.fabs(a - b) <= (atol + rtol * math.fabs(b))

def toUnitVec(vec):
    """Converts the given vector to a unit vector

    :param numpy.array vec:
      The vector to transform to unit length

    :rtype: numpy.array

    """
    return vec / numpy.sqrt(numpy.vdot(vec, vec))

def checkSource( source, components, maxindex):
    """Check if a source objects complies with the needed `components` and has the needed length

    :param collada.source.Source source:
      A source instance to check
    :param tuple components:
      A tuple describing the needed channels, e.g. ``('X','Y','Z')``
    :param int maxindex:
      The maximum index that refers to this source

    """
    if len(source.data) <= maxindex:
        raise DaeMalformedError(
            "Indexes (maxindex=%d) for source '%s' (len=%d) go beyond the limits of the source"
            % (maxindex, source.id, len(source.data)) )

    #some files will write sources with no named parameters
    #by spec, these params should just be skipped, but we need to
    #adapt to the failed output of others...
    if len(source.components) == len(components):
        source.components = components

    if source.components != components:
        raise DaeMalformedError('Wrong format in source %s'%source.id)
    return source

def normalize_v3(arr):
    """Normalize a numpy array of 3 component vectors with shape (N,3)

    :param numpy.array arr:
      The numpy array to normalize

    :rtype: numpy.array

    """
    lens = numpy.sqrt( arr[:,0]**2 + arr[:,1]**2 + arr[:,2]**2 )
    lens[numpy.equal(lens, 0)] = 1
    arr[:,0] /= lens
    arr[:,1] /= lens
    arr[:,2] /= lens
    return arr

def dot_v3(arr1, arr2):
    """Calculates the dot product for each vector in two arrays

    :param numpy.array arr1:
      The first array, shape Nx3
    :param numpy.array arr2:
      The second array, shape Nx3

    :rtype: numpy.array

    """
    return arr1[:,0]*arr2[:,0] + arr1[:,1]*arr2[:,1] + arr2[:,2]*arr1[:,2]

class IndexedList(list):
    """
    Class that combines a list and a dict into a single class
     - Written by Hugh Bothwell (http://stackoverflow.com/users/33258/hugh-bothwell)
     - Original source available at:
          http://stackoverflow.com/questions/5332841/python-list-dict-property-best-practice/5334686#5334686
     - Modifications by Jeff Terrace
    Given an object, obj, that has a property x, this allows you to create an IndexedList like so:
       L = IndexedList([], ('x'))
       o = obj()
       o.x = 'test'
       L.append(o)
       L[0] # = o
       L['test'] # = o
    """
    def __init__(self, items, attrs):
        super(IndexedList, self).__init__(items)
        # do indexing
        self._attrs = tuple(attrs)
        self._index = {}
        _add = self._addindex
        for obj in self:
            _add(obj)

    def _addindex(self, obj):
        _idx = self._index
        for attr in self._attrs:
            _idx[getattr(obj, attr)] = obj

    def _delindex(self, obj):
        _idx = self._index
        for attr in self._attrs:
            try:
                del _idx[getattr(obj, attr)]
            except KeyError:
                pass

    def __delitem__(self, ind):
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        return list.__delitem__(self, ind)

    def __delslice__(self, i, j):
        return list.__delslice__(self, i, j)

    def __getitem__(self, ind):
        try:
            return self._index[ind]
        except KeyError:
            if isinstance(ind, str):
                raise
            return list.__getitem__(self, ind)

    def get(self, key, default=None):
        try:
            return self._index[key]
        except KeyError:
            return default

    def __contains__(self, item):
        if item in self._index:
            return True
        return list.__contains__(self, item)

    def __getslice__(self, i, j):
        return IndexedList(list.__getslice__(self, i, j), self._attrs)

    def __setitem__(self, ind, new_obj):
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        self._addindex(new_obj)
        return list.__setitem__(ind, new_obj)

    def __setslice__(self, i, j, newItems):
        _get = self.__getitem__
        _add = self._addindex
        _del = self._delindex
        newItems = list(newItems)
        # remove indexing of items to remove
        for ind in xrange(i, j):
            _del(_get(ind))
        # add new indexing
        if isinstance(newList, IndexedList):
            self._index.update(newList._index)
        else:
            for obj in newList:
                _add(obj)
        # replace items
        return list.__setslice__(self, i, j, newList)

    def append(self, obj):
        self._addindex(obj)
        return list.append(self, obj)

    def extend(self, newList):
        newList = list(newList)
        if isinstance(newList, IndexedList):
            self._index.update(newList._index)
        else:
            _add = self._addindex
            for obj in newList:
                _add(obj)
        return list.extend(self, newList)

    def insert(self, ind, new_obj):
        # ensure that ind is a numeric index
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._addindex(new_obj)
        return list.insert(self, ind, new_obj)

    def pop(self, ind= -1):
        # ensure that ind is a numeric index
        try:
            obj = list.__getitem__(self, ind)
        except (IndexError, TypeError):
            obj = self._index[ind]
            ind = list.index(self, obj)
        self._delindex(obj)
        return list.pop(self, ind)

    def remove(self, ind_or_obj):
        try:
            obj = self._index[ind_or_obj]
            ind = list.index(self, obj)
        except KeyError:
            ind = list.index(self, ind_or_obj)
            obj = list.__getitem__(self, ind)
        self._delindex(obj)
        return list.remove(self, ind)

def _correctValInNode(outernode, tagname, value):
    innernode = outernode.find( tag(tagname) )
    if value is None and innernode is not None:
        outernode.remove(innernode)
    elif innernode is not None:
        innernode.text = str(value)
    elif value is not None:
        outernode.append(E(tagname, str(value)))


########NEW FILE########
__FILENAME__ = xmlutil
import sys
import functools

COLLADA_NS = 'http://www.collada.org/2005/11/COLLADASchema'
HAVE_LXML = False

try:
    from lxml import etree
    HAVE_LXML = True
except ImportError:
    from xml.etree import ElementTree as etree

ET = etree

try:
    from functools import partial
except ImportError:
    # fake it for pre-2.5 releases
    def partial(func, tag):
        return lambda *args, **kwargs: func(tag, *args, **kwargs)

try:
    callable
except NameError:
    # Python 3
    def callable(f):
        return hasattr(f, '__call__')

try:
    basestring
except (NameError, KeyError):
    basestring = str

try:
    unicode
except (NameError, KeyError):
    unicode = str

if HAVE_LXML:
    from lxml.builder import E, ElementMaker
    
    def writeXML(xmlnode, fp):
        xmlnode.write(fp, pretty_print=True)
else:    
    class ElementMaker(object):
        def __init__(self, namespace=None, nsmap=None):
            if namespace is not None:
                self._namespace = '{' + namespace + '}'
            else:
                self._namespace = None
        
        def __call__(self, tag, *children, **attrib):
            if self._namespace is not None and tag[0] != '{':
                tag = self._namespace + tag
            
            elem = etree.Element(tag, attrib)
            for item in children:
                if isinstance(item, dict):
                    elem.attrib.update(item)
                elif isinstance(item, basestring):
                    if len(elem):
                        elem[-1].tail = (elem[-1].tail or "") + item
                    else:
                        elem.text = (elem.text or "") + item
                elif etree.iselement(item):
                    elem.append(item)
                else:
                    raise TypeError("bad argument: %r" % item)
            return elem
    
        def __getattr__(self, tag):
            return functools.partial(self, tag)

    E = ElementMaker()
    
    if etree.VERSION[0:3] == '1.2':
        #in etree < 1.3, this is a workaround for supressing prefixes
        
        def fixtag(tag, namespaces):
            import string
            # given a decorated tag (of the form {uri}tag), return prefixed
            # tag and namespace declaration, if any
            if isinstance(tag, etree.QName):
                tag = tag.text
            namespace_uri, tag = string.split(tag[1:], "}", 1)
            prefix = namespaces.get(namespace_uri)
            if namespace_uri not in namespaces:
                prefix = etree._namespace_map.get(namespace_uri)
                if namespace_uri not in etree._namespace_map:
                    prefix = "ns%d" % len(namespaces)
                namespaces[namespace_uri] = prefix
                if prefix == "xml":
                    xmlns = None
                else:
                    if prefix is not None:
                        nsprefix = ':' + prefix
                    else:
                        nsprefix = ''
                    xmlns = ("xmlns%s" % nsprefix, namespace_uri)
            else:
                xmlns = None
            if prefix is not None:
                prefix += ":"
            else:
                prefix = ''
                
            return "%s%s" % (prefix, tag), xmlns
    
        etree.fixtag = fixtag
        etree._namespace_map[COLLADA_NS] = None
    else:
        #For etree > 1.3, use register_namespace function
        etree.register_namespace('', COLLADA_NS)

    def indent(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def writeXML(xmlnode, fp):
        indent(xmlnode.getroot())
        xmlnode.write(fp)

########NEW FILE########
__FILENAME__ = __main__
####################################################################
#                                                                  #
# THIS FILE IS PART OF THE pycollada LIBRARY SOURCE CODE.          #
# USE, DISTRIBUTION AND REPRODUCTION OF THIS LIBRARY SOURCE IS     #
# GOVERNED BY A BSD-STYLE SOURCE LICENSE INCLUDED WITH THIS SOURCE #
# IN 'COPYING'. PLEASE READ THESE TERMS BEFORE DISTRIBUTING.       #
#                                                                  #
# THE pycollada SOURCE CODE IS (C) COPYRIGHT 2011                  #
# by Jeff Terrace and contributors                                 #
#                                                                  #
####################################################################

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from collada.util import unittest

if __name__ == '__main__':
    suite = unittest.TestLoader().discover("tests")
    ret = unittest.TextTestRunner(verbosity=2).run(suite)
    if ret.wasSuccessful():
        sys.exit(0)
    sys.exit(1)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pycollada documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 14 16:59:13 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.graphviz',
              'sphinx.ext.inheritance_diagram']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'pycollada'
copyright = u'2011, Jeff Terrace and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.4'
# The full version, including alpha/beta/rc tags.
release = '0.4'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'pycolladadoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pycollada.tex', u'pycollada Documentation',
   u'Jeff Terrace', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

autoclass_content = 'class'
autodoc_default_flags = ['members', 'show-inheritance', 'inherited-members']
autodoc_member_order = 'bysource'
#autosummary_generate = True

########NEW FILE########
__FILENAME__ = check_collada
import collada
import sys
import traceback

print 'Attempting to load file %s' % sys.argv[1]

try:
    col = collada.Collada(sys.argv[1], \
            ignore=[collada.DaeUnsupportedError, collada.DaeBrokenRefError])
except:
    traceback.print_exc()
    print
    print "Failed to load collada file."
    sys.exit(1)

print
print 'Successfully loaded collada file.'
print 'There were %d errors' % len(col.errors)

for e in col.errors:
    print e

########NEW FILE########
__FILENAME__ = daeview
#!/usr/bin/env python
import collada
import sys
import os
import renderer

import pyglet
from pyglet.gl import *


try:
    # Try and create a window with multisampling (antialiasing)
    config = Config(sample_buffers=1, samples=4,
                    depth_size=16, double_buffer=True)
    window = pyglet.window.Window(resizable=False, config=config, vsync=True)
except pyglet.window.NoSuchConfigException:
    # Fall back to no multisampling for old hardware
    window = pyglet.window.Window(resizable=False)

window.rotate_x  = 0.0
window.rotate_y = 0.0
window.rotate_z = 0.0


@window.event
def on_draw():
    daerender.render(window.rotate_x, window.rotate_y, window.rotate_z)


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if abs(dx) > 2:
        if dx > 0:
            window.rotate_y += 2
        else:
            window.rotate_y -= 2
		
    if abs(dy) > 1:
        if dy > 0:
            window.rotate_x -= 2
        else:
            window.rotate_x += 2

    
@window.event
def on_resize(width, height):
    if height==0: height=1
    # Override the default on_resize handler to create a 3D projection
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60., width / float(height), .1, 1000.)
    glMatrixMode(GL_MODELVIEW)
    return pyglet.event.EVENT_HANDLED


if __name__ == '__main__':
    filename = sys.argv[1] if  len(sys.argv) > 1 else os.path.dirname(__file__) + '/data/cockpit.zip'

    # open COLLADA file ignoring some errors in case they appear
    collada_file = collada.Collada(filename, ignore=[collada.DaeUnsupportedError,
                                            collada.DaeBrokenRefError])

    daerender = renderer.GLSLRenderer(collada_file)
    #daerender = renderer.OldStyleRenderer(collada_file, window)
	
    window.width = 1024
    window.height = 768
    
    pyglet.app.run()

    daerender.cleanup()

########NEW FILE########
__FILENAME__ = GLSLRenderer
#!/usr/bin/env python
import collada
import numpy

import pyglet
from pyglet.gl import *

import ctypes

import glutils
from glutils import VecF
import shader
from shader import Shader
import shaders


class GLSLRenderer: 

    def __init__(self, dae):
        self.dae = dae
        # To calculate model boundary along Z axis
        self.z_max = -100000.0
        self.z_min = 100000.0
        self.textures = {}
        self.shaders = {}
        self.batch_list = []

        # Initialize OpenGL
        glClearColor(0.0, 0.0, 0.0, 0.5) # Black Background
        glEnable(GL_DEPTH_TEST) # Enables Depth Testing
        glEnable(GL_CULL_FACE)
        glEnable(GL_MULTISAMPLE);

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnable(GL_LIGHTING)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, VecF(0.9, 0.9, 0.9, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, VecF(1.0, 1.0, 1.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, VecF(0.3, 0.3, 0.3, 1.0))

        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, VecF(0.1, 0.1, 0.1, 1.0))
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, VecF(0.1, 0.1, 0.1, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)

        print 'Running with OpenGL version:', glutils.getOpenGLVersion()
        print 'Initializing shaders...'
        #(vert, frag) = shaders.ADSPhong
        (vert, frag) = shaders.simplePhong
        prog = Shader(vert, frag)
        print '  phong'
        self.shaders['phong'] = prog
        (vert, frag) = shaders.pointLightDiff
        prog = Shader(vert, frag)
        self.shaders['lambert'] = prog
        print '  lambert'
        self.shaders['blinn'] = prog
        print '  blinn'
        (vert, frag) = shaders.flatShader
        prog = Shader(vert, frag)
        self.shaders['constant'] = prog
        print '  constant'
        (vert, frag) = shaders.texturePhong
        prog = Shader(vert, frag)
        self.shaders['texture'] = prog
        print '  texture'
        print '  done.'

        print 'Creating GL buffer objects for geometry...'
        if self.dae.scene is not None:
            for geom in self.dae.scene.objects('geometry'):
                for prim in geom.primitives():
                    mat = prim.material
                    diff_color = VecF(0.3,0.3,0.3,1.0)
                    spec_color = None 
                    shininess = None
                    amb_color = None
                    tex_id = None
                    shader_prog = self.shaders[mat.effect.shadingtype]
                    for prop in mat.effect.supported:
                        value = getattr(mat.effect, prop)
                        # it can be a float, a color (tuple) or a Map
                        # ( a texture )
                        if isinstance(value, collada.material.Map):
                            colladaimage = value.sampler.surface.image

                            # Accessing this attribute forces the
                            # loading of the image using PIL if
                            # available. Unless it is already loaded.
                            img = colladaimage.pilimage
                            if img: # can read and PIL available
                                shader_prog = self.shaders['texture']
                                # See if we already have texture for this image
                                if self.textures.has_key(colladaimage.id):
                                    tex_id = self.textures[colladaimage.id]
                                else:
                                    # If not - create new texture
                                    try:
                                        # get image meta-data
                                        # (dimensions) and data
                                        (ix, iy, tex_data) = (img.size[0], img.size[1], img.tostring("raw", "RGBA", 0, -1))
                                    except SystemError:
                                        # has no alpha channel,
                                        # synthesize one
                                        (ix, iy, tex_data) = (img.size[0], img.size[1], img.tostring("raw", "RGBX", 0, -1))
                                    # generate a texture ID
                                    tid = GLuint()
                                    glGenTextures(1, ctypes.byref(tid))
                                    tex_id = tid.value
                                    # make it current
                                    glBindTexture(GL_TEXTURE_2D, tex_id)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                                    # copy the texture into the
                                    # current texture ID
                                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)

                                    self.textures[colladaimage.id] = tex_id
                            else:
                                print '  %s = Texture %s: (not available)'%(
                                    prop, colladaimage.id)
                        else:
                            if prop == 'diffuse' and value is not None:
                                diff_color = value
                            elif prop == 'specular' and value is not None:
                                spec_color = value
                            elif prop == 'ambient' and value is not None:
                                amb_color = value
                            elif prop == 'shininess' and value is not None:
                                shininess = value

                    # use primitive-specific ways to get triangles
                    prim_type = type(prim).__name__
                    if prim_type == 'BoundTriangleSet':
                        triangles = prim
                    elif prim_type == 'BoundPolylist':
                        triangles = prim.triangleset()
                    else:
                        print 'Unsupported mesh used:', prim_type
                        triangles = None

                    if triangles is not None:
                        triangles.generateNormals()
                        # We will need flat lists for VBO (batch) initialization
                        vertices = triangles.vertex.flatten().tolist()
                        batch_len = len(vertices)//3
                        indices = triangles.vertex_index.flatten().tolist()
                        normals = triangles.normal.flatten().tolist()

                        batch = pyglet.graphics.Batch()

                        # Track maximum and minimum Z coordinates
                        # (every third element) in the flattened
                        # vertex list
                        ma = max(vertices[2::3])
                        if ma > self.z_max:
                            self.z_max = ma

                        mi = min(vertices[2::3])
                        if mi < self.z_min:
                            self.z_min = mi

                        if tex_id is not None:

                            # This is probably the most inefficient
                            # way to get correct texture coordinate
                            # list (uv). I am sure that I just do not
                            # understand enough how texture
                            # coordinates and corresponding indexes
                            # are related to the vertices and vertex
                            # indicies here, but this is what I found
                            # to work. Feel free to improve the way
                            # texture coordinates (uv) are collected
                            # for batch.add_indexed() invocation.
                            uv = [[0.0,0.0]] * batch_len
                            for t in triangles:
                                nidx = 0
                                texcoords = t.texcoords[0]
                                for vidx in t.indices:
                                    uv[vidx] = texcoords[nidx].tolist()
                                    nidx += 1
                            # Flatten the uv list
                            uv = [item for sublist in uv for item in sublist]

                            # Create textured batch
                            batch.add_indexed(batch_len, 
                                              GL_TRIANGLES,
                                              None,
                                              indices,
                                              ('v3f/static', vertices),
                                              ('n3f/static', normals),
                                              ('t2f/static', uv))
                        else:
                            # Create colored batch
                            batch.add_indexed(batch_len, 
                                              GL_TRIANGLES,
                                              None,
                                              indices,
                                              ('v3f/static', vertices),
                                              ('n3f/static', normals))

                        # Append the batch with supplimentary
                        # information to the batch list
                        self.batch_list.append(
                            (batch, shader_prog, tex_id, diff_color, 
                             spec_color, amb_color, shininess))
        print 'done. Ready to render.'

    def render(self, rotate_x, rotate_y, rotate_z):
        """Render batches created during class initialization"""

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        # Place the light far behind our object
        z_offset = self.z_min - (self.z_max - self.z_min) * 3
        light_pos = VecF(100.0, 100.0, 10.0 * -z_offset)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        
        # Move the object deeper to the screen and rotate
        glTranslatef(0, 0, z_offset)
        glRotatef(rotate_x, 1.0, 0.0, 0.0)
        glRotatef(rotate_y, 0.0, 1.0, 0.0)
        glRotatef(rotate_z, 0.0, 0.0, 1.0)

        prev_shader_prog = None
        # Draw batches (VBOs)
        for (batch, shader_prog, tex_id, diff_color, spec_color, amb_color, shininess) in self.batch_list:
            # Optimization to not make unnecessary bind/unbind for the
            # shader. Most of the time there will be same shaders for
            # geometries.
            if shader_prog != prev_shader_prog:
                if prev_shader_prog is not None:
                    prev_shader_prog.unbind()
                prev_shader_prog = shader_prog
                shader_prog.bind()

            if diff_color is not None:
                shader_prog.uniformf('diffuse', *diff_color)
            if spec_color is not None:
                shader_prog.uniformf('specular', *spec_color)
            if amb_color is not None:
                shader_prog.uniformf('ambient', *amb_color)
            if shininess is not None:
                shader_prog.uniformf('shininess', shininess)

            if tex_id is not None:
                # We assume that the shader here is 'texture'
                glActiveTexture(GL_TEXTURE0)
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, tex_id)
                shader_prog.uniformi('my_color_texture[0]', 0)

            batch.draw()
        if prev_shader_prog is not None:
            prev_shader_prog.unbind()


    def cleanup(self):
        print 'Renderer cleaning up'

########NEW FILE########
__FILENAME__ = glutils
import pyglet
from pyglet.gl import *
import ctypes


def VecF(*args):
    """Simple function to create ctypes arrays of floats"""
    return (GLfloat * len(args))(*args)

def getOpenGLVersion():
    """Get the OpenGL minor and major version number"""
    versionString = glGetString(GL_VERSION)
    return ctypes.cast(versionString, ctypes.c_char_p).value

def getGLError():
    e = glGetError()
    if e != 0:
        errstr = gluErrorString(e)
        print 'GL ERROR:', errstr
        return errstr
    else:
        return None

########NEW FILE########
__FILENAME__ = OldStyleRenderer
#!/usr/bin/env python
import collada
import numpy
import pyglet
from pyglet.gl import *
import ctypes
import glutils


class OldStyleRenderer: 

    def __init__(self, dae, window):
        self.dae = dae
        self.window = window
        # to calculate model boundary
        self.z_max = -100000.0
        self.z_min = 100000.0
        self.textures = {}

        glShadeModel(GL_SMOOTH) # Enable Smooth Shading
        glClearColor(0.0, 0.0, 0.0, 0.5) # Black Background
        glClearDepth(1.0) # Depth Buffer Setup
        glEnable(GL_DEPTH_TEST) # Enables Depth Testing
        glDepthFunc(GL_LEQUAL) # The Type Of Depth Testing To Do
        
        glEnable(GL_MULTISAMPLE);

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glCullFace(GL_BACK)

        glEnable(GL_TEXTURE_2D) # Enable Texture Mapping
        # glEnable(GL_TEXTURE_RECTANGLE_ARB) # Enable Texture Mapping
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        # create one display list
        print 'Creating display list...'
        print 'It could take some time. Please be patient :-) .'
        self.displist = glGenLists(1)
        # compile the display list, store a triangle in it
        glNewList(self.displist, GL_COMPILE)
        self.drawPrimitives()
        glEndList()
        print 'done. Ready to render.'

    def drawPrimitives(self):
        glBegin(GL_TRIANGLES)
        
        if self.dae.scene is not None:
            for geom in self.dae.scene.objects('geometry'):
                for prim in geom.primitives():
                    mat = prim.material
                    diff_color = (GLfloat * 4)(*(0.3,0.3,0.3,0.0))
                    spec_color = None 
                    shininess = None
                    amb_color = None
                    tex_id = None
                    for prop in mat.effect.supported:
                        value = getattr(mat.effect, prop)
                        # it can be a float, a color (tuple) or a Map
                        # ( a texture )
                        if isinstance(value, collada.material.Map):
                            colladaimage = value.sampler.surface.image
                            # Accessing this attribute forces the
                            # loading of the image using PIL if
                            # available. Unless it is already loaded.
                            img = colladaimage.pilimage
                            if img: # can read and PIL available
                                # See if we already have texture for this image
                                if self.textures.has_key(colladaimage.id):
                                    tex_id = self.textures[colladaimage.id]
                                else:
                                    # If not - create new texture
                                    try:
                                        # get image meta-data
                                        # (dimensions) and data
                                        (ix, iy, tex_data) = (img.size[0], img.size[1], img.tostring("raw", "RGBA", 0, -1))
                                    except SystemError:
                                        # has no alpha channel,
                                        # synthesize one
                                        (ix, iy, tex_data) = (img.size[0], img.size[1], img.tostring("raw", "RGBX", 0, -1))
                                    # generate a texture ID
                                    tid = GLuint()
                                    glGenTextures(1, ctypes.byref(tid))
                                    tex_id = tid.value
                                    # make it current
                                    glBindTexture(GL_TEXTURE_2D, tex_id)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                                    #glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
                                    # copy the texture into the
                                    # current texture ID
                                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)

                                    self.textures[colladaimage.id] = tex_id
                            else:
                                print '  %s = Texture %s: (not available)'%(
                                    prop, colladaimage.id)
                        else:
                            if prop == 'diffuse' and value is not None:
                                diff_color = (GLfloat * 4)(*value)
                            elif prop == 'specular' and value is not None:
                                spec_color = (GLfloat * 4)(*value)
                            elif prop == 'ambient' and value is not None:
                                amb_color = (GLfloat * 4)(*value)
                            elif prop == 'shininess' and value is not None:
                                shininess = value

                    # use primitive-specific ways to get triangles
                    prim_type = type(prim).__name__
                    if prim_type == 'BoundTriangleSet':
                        triangles = prim
                    elif prim_type == 'BoundPolylist':
                        triangles = prim.triangleset()
                    else:
                        print 'Unsupported mesh used:', prim_type
                        triangles = []

                    if tex_id is not None:
                        glBindTexture(GL_TEXTURE_2D, tex_id)
                    else:
                        glBindTexture(GL_TEXTURE_2D, 0)


                    # add triangles to the display list
                    for t in triangles:
                        nidx = 0
                        if tex_id is not None and len(t.texcoords) > 0:
                            texcoords = t.texcoords[0]
                        else:
                            texcoords = None

                        for vidx in t.indices:
                            if diff_color is not None:
                                glMaterialfv(GL_FRONT, GL_DIFFUSE, diff_color)
                            if spec_color is not None:
                                glMaterialfv(GL_FRONT, GL_SPECULAR, spec_color)
                            if amb_color is not None:
                                glMaterialfv(GL_FRONT, GL_AMBIENT, amb_color)
                            if shininess is not None:
                                glMaterialfv(GL_FRONT, GL_SHININESS, (GLfloat * 1)(shininess))

                            # if not t.normals is None:
                            glNormal3fv((GLfloat * 3)(*t.normals[nidx]))
                            if texcoords is not None:
                                glTexCoord2fv((GLfloat * 2)(*texcoords[nidx]))

                            nidx += 1

                            v = prim.vertex[vidx]
                            glVertex3fv((GLfloat * 3)(*v))

                            # calculate max and min Z coordinate
                            if v[2] > self.z_max:
                                self.z_max = v[2]
                            elif v[2] < self.z_min:
                                self.z_min = v[2]
        glutils.getGLError()
        glEnd()


    def render(self, rotate_x, rotate_y, rotate_z):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION) # Select The Projection Matrix
        glLoadIdentity() # Reset The Projection Matrix
        if self.window.height == 0: # Calculate The Aspect Ratio Of The Window
            gluPerspective(100, self.window.width, 1.0, 5000.0)
        else:
            gluPerspective(100, self.window.width / self.window.height, 1.0, 5000.0)
        glMatrixMode(GL_MODELVIEW) # Select The Model View Matrix
        glLoadIdentity()
        z_offset = self.z_min - (self.z_max - self.z_min) * 3
        light_pos = (GLfloat * 3)(100.0, 100.0, 100.0 * -z_offset)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glTranslatef(0, 0, z_offset)
        glRotatef(rotate_x, 1.0, 0.0, 0.0)
        glRotatef(rotate_y, 0.0, 1.0, 0.0)
        glRotatef(rotate_z, 0.0, 0.0, 1.0)
        
        # draw the display list
        glCallList(self.displist)


    def cleanup(self):
        print 'Renderer cleaning up'
        glDeleteLists(self.displist, 1)

########NEW FILE########
__FILENAME__ = shader
#
# Copyright Tristam Macdonald 2008.
#
# Distributed under the Boost Software License, Version 1.0
# (see http://www.boost.org/LICENSE_1_0.txt)
#

from pyglet.gl import *
import ctypes

class Shader:
	# vert, frag and geom take arrays of source strings
	# the arrays will be concattenated into one string by OpenGL
	def __init__(self, vert = [], frag = [], geom = []):
		# create the program handle
		self.handle = glCreateProgram()
		# we are not linked yet
		self.linked = False

		# create the vertex shader
		self.createShader(vert, GL_VERTEX_SHADER)
		# create the fragment shader
		self.createShader(frag, GL_FRAGMENT_SHADER)
		# the geometry shader will be the same, once pyglet supports the extension
		# self.createShader(frag, GL_GEOMETRY_SHADER_EXT)

		# attempt to link the program
		self.link()

	def createShader(self, strings, type):
		count = len(strings)
		# if we have no source code, ignore this shader
		if count < 1:
			return

		# create the shader handle
		shader = glCreateShader(type)

		# convert the source strings into a ctypes pointer-to-char array, and upload them
		# this is deep, dark, dangerous black magick - don't try stuff like this at home!
		src = (ctypes.c_char_p * count)(*strings)
		glShaderSource(shader, count, ctypes.cast(ctypes.pointer(src),
			       ctypes.POINTER(ctypes.POINTER(ctypes.c_char))), None)

		# compile the shader
		glCompileShader(shader)

		temp = ctypes.c_int(0)
		# retrieve the compile status
		glGetShaderiv(shader, GL_COMPILE_STATUS, ctypes.byref(temp))

		# if compilation failed, print the log
		if not temp:
			# retrieve the log length
			glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(temp))
			# create a buffer for the log
			buffer = ctypes.create_string_buffer(temp.value)
			# retrieve the log text
			glGetShaderInfoLog(shader, temp, None, buffer)
			# print the log to the console
			print buffer.value
		else:
			# all is well, so attach the shader to the program
			glAttachShader(self.handle, shader);

	def link(self):
		# link the program
		glLinkProgram(self.handle)

		temp = ctypes.c_int(0)
		# retrieve the link status
		glGetProgramiv(self.handle, GL_LINK_STATUS, ctypes.byref(temp))

		# if linking failed, print the log
		if not temp:
			#	retrieve the log length
			glGetProgramiv(self.handle, GL_INFO_LOG_LENGTH, ctypes.byref(temp))
			# create a buffer for the log
			buffer = create_string_buffer(temp.value)
			# retrieve the log text
			glGetProgramInfoLog(self.handle, temp, None, buffer)
			# print the log to the console
			print buffer.value
		else:
			# all is well, so we are linked
			self.linked = True

	def bind(self):
		# bind the program
		glUseProgram(self.handle)

	def unbind(self):
		# unbind whatever program is currently bound - not necessarily this program,
		# so this should probably be a class method instead
		glUseProgram(0)

	# upload a floating point uniform
	# this program must be currently bound
	def uniformf(self, name, *vals):
		# check there are 1-4 values
		if len(vals) in range(1, 5):
			# select the correct function
			{ 1 : glUniform1f,
				2 : glUniform2f,
				3 : glUniform3f,
				4 : glUniform4f
				# retrieve the uniform location, and set
			}[len(vals)](glGetUniformLocation(self.handle, name), *vals)

	# upload an integer uniform
	# this program must be currently bound
	def uniformi(self, name, *vals):
		# check there are 1-4 values
		if len(vals) in range(1, 5):
			# select the correct function
			{ 1 : glUniform1i,
				2 : glUniform2i,
				3 : glUniform3i,
				4 : glUniform4i
				# retrieve the uniform location, and set
			}[len(vals)](glGetUniformLocation(self.handle, name), *vals)

	# upload a uniform matrix
	# works with matrices stored as lists,
	# as well as euclid matrices
	def uniform_matrixf(self, name, mat):
		# obtian the uniform location
		loc = glGetUniformLocation(self.Handle, name)
		# uplaod the 4x4 floating point matrix
		glUniformMatrix4fv(loc, 1, False, (c_float * 16)(*mat))


########NEW FILE########
__FILENAME__ = shaders
######################################################################
# Flat Shader
# This shader applies the given model view matrix to the verticies, 
# and uses a uniform color value.
flatShader = (['''
uniform mat4 mvpMatrix;
attribute vec4 vVertex;
void main(void)
{
  gl_Position = mvpMatrix * vVertex; 
}'''],
['''
//precision mediump float;
uniform vec4 vColor;
void main(void) 
{
  gl_FragColor = vColor;
}'''])

######################################################################
# Point light, diffuse lighting only
pointLightDiff = (['''
uniform mat4 mvMatrix;
uniform mat4 pMatrix;
uniform vec3 vLightPos;
uniform vec4 vColor;
attribute vec4 vVertex;
attribute vec3 vNormal;
varying vec4 vFragColor;
void main(void)
{
  mat3 mNormalMatrix;
  mNormalMatrix[0] = normalize(mvMatrix[0].xyz);
  mNormalMatrix[1] = normalize(mvMatrix[1].xyz);
  mNormalMatrix[2] = normalize(mvMatrix[2].xyz);
  vec3 vNorm = normalize(mNormalMatrix * vNormal);
  vec4 ecPosition;
  vec3 ecPosition3;
  ecPosition = mvMatrix * vVertex;
  ecPosition3 = ecPosition.xyz /ecPosition.w;
  vec3 vLightDir = normalize(vLightPos - ecPosition3);
  float fDot = max(0.0, dot(vNorm, vLightDir)); 
  vFragColor.rgb = vColor.rgb * fDot;
  vFragColor.a = vColor.a;
//  vFragColor = vColor;
  mat4 mvpMatrix;
  mvpMatrix = pMatrix * mvMatrix;
  gl_Position = mvpMatrix * vVertex; 
}'''],
['''
//precision mediump float;
varying vec4 vFragColor; 
void main(void) 
{
  gl_FragColor = vFragColor;
}'''])


######################################################################
# ADS Gouraud shader
ADSGouraud = (['''
uniform mat4 mvMatrix;
uniform mat4 pMatrix;
uniform vec3 vLightPos;
uniform vec4 ambientColor;
uniform vec4 diffuseColor;
uniform vec4 specularColor;
uniform float shininess;
uniform vec4 lightColor;
uniform float fConstantAttenuation;
uniform float fLinearAttenuation;
uniform float fQuadraticAttenuation;
attribute vec4 vVertex;
attribute vec3 vNormal;
varying vec4 vVaryingColor;
void main(void)
{
  mat3 mNormalMatrix;
  mNormalMatrix[0] = normalize(mvMatrix[0].xyz);
  mNormalMatrix[1] = normalize(mvMatrix[1].xyz);
  mNormalMatrix[2] = normalize(mvMatrix[2].xyz);
// Get surface normal in eye coordinates
  vec3 vEyeNormal = mNormalMatrix * vNormal;
// Get vertex position in eye coordinates
  vec4 vPosition4 = mvMatrix * vVertex;
  vec3 vPosition3 = vPosition4.xyz /vPosition4.w;
// Get vector to light source
  vec3 vLightDir = normalize(vLightPos - vPosition3);
// Get distance to light source
  float distanceToLight = length(vLightPos-vPosition3);
//  float attenuation = fConstantAttenuation / ((1.0 + fLinearAttenuation * distanceToLight) * (1.0 + fQuadraticAttenuation * distanceToLight * distanceToLight));
  float attenuation = 1.0 / (fConstantAttenuation + fLinearAttenuation * distanceToLight + fQuadraticAttenuation * distanceToLight * distanceToLight);
  vec4 attenuatedLight = lightColor * attenuation;
//  float attenuation = 1.0f;
// Dot product gives us diffuse intensity
  float diff = max(0.0, dot(vEyeNormal, vLightDir)); 
// Multiply intensity by diffuse color, force alpha to 1.0
  vVaryingColor = attenuatedLight * diffuseColor * diff;
// Add in ambient light
  vVaryingColor += ambientColor;
// Specular light
  vec3 vReflection = normalize(reflect(-vLightDir, vEyeNormal));
  float spec = max(0.0, dot(vEyeNormal, vReflection));
  if(diff != 0.0) {
    float fSpec = pow(spec, shininess);
    vVaryingColor.rgb += attenuatedLight.rgb * vec3(fSpec, fSpec, fSpec);
  }
// Don't forget to transform the geometry
  mat4 mvpMatrix = pMatrix * mvMatrix;
  gl_Position = mvpMatrix * vVertex; 
}'''],
['''
//precision mediump float;
varying vec4 vVaryingColor; 
void main(void) 
{
  gl_FragColor = vVaryingColor;
}'''])


##############################################################################
# Simple phong shader by Jerome GUINOT aka 'JeGX' - jegx [at] ozone3d
# [dot] net see
# http://www.ozone3d.net/tutorials/glsl_lighting_phong.php

simplePhong = (['''
varying vec3 normal, lightDir0, eyeVec;
void main()
{
  normal = gl_NormalMatrix * gl_Normal;
  vec3 vVertex = vec3(gl_ModelViewMatrix * gl_Vertex);
  lightDir0 = vec3(gl_LightSource[0].position.xyz - vVertex);
  eyeVec = -vVertex;
  gl_Position = ftransform();
}
'''], 
['''
uniform vec4 diffuse, specular, ambient;
uniform float shininess;
varying vec3 normal, lightDir0, eyeVec;
void main (void)
{
  vec4 final_color =
    (gl_FrontLightModelProduct.sceneColor * ambient)
    + (gl_LightSource[0].ambient * ambient);
  vec3 N = normalize(normal);
  vec3 L0 = normalize(lightDir0);
  float lambertTerm0 = dot(N,L0);
  if(lambertTerm0 > 0.0)
  {
    final_color += gl_LightSource[0].diffuse * diffuse * lambertTerm0;
    vec3 E = normalize(eyeVec);
    vec3 R = reflect(-L0, N);
    float spec = pow(max(dot(R, E), 0.0), shininess);
    final_color += gl_LightSource[0].specular * specular * spec;
  }
  gl_FragColor = final_color;
}
'''])

##############################################################################
# ADS Phong shader
ADSPhong = (['''
attribute vec4 vVertex;
attribute vec3 vNormal;
uniform mat4 mvMatrix;
uniform mat4 pMatrix;
uniform vec3 vLightPos;
// Color to fragment program
varying vec3 vVaryingNormal;
varying vec3 vVaryingLightDir;
varying float distanceToLight;
//varying float spotEffect;
void main(void)
{
  mat3 normalMatrix;
  normalMatrix[0] = normalize(mvMatrix[0].xyz);
  normalMatrix[1] = normalize(mvMatrix[1].xyz);
  normalMatrix[2] = normalize(mvMatrix[2].xyz);
// Get surface normal in eye coordinates
  vVaryingNormal = normalMatrix * vNormal;
// Get vertex position in eye coordinates
  vec4 vPosition4 = mvMatrix * vVertex;
  vec3 vPosition3 = vPosition4.xyz /vPosition4.w;
// Get vector to light source
  vVaryingLightDir = normalize(vLightPos - vPosition3);
// Get distance to light source
  distanceToLight = length(vLightPos-vPosition3);

//  spotEffect = dot(normalize(gl_LightSource[0].spotDirection), normalize(-lightDir));
//  spotEffect = dot(vec3(0.0, 0.0, -1.0), normalize(-vVaryingLightDir));

// Don't forget to transform the geometry
  mat4 mvpMatrix = pMatrix * mvMatrix;
  gl_Position = mvpMatrix * vVertex; 
}'''],
['''
precision mediump float;
uniform vec4 ambientColor;
uniform vec4 diffuseColor;
uniform vec4 specularColor;
uniform float shininess;
uniform vec4 lightColor;
uniform float fConstantAttenuation;
uniform float fLinearAttenuation;
uniform float fQuadraticAttenuation;
varying vec3 vVaryingNormal;
varying vec3 vVaryingLightDir;
varying float distanceToLight;
//varying float spotEffect;
void main(void) 
{
//  float attenuation = 1.0 / (fConstantAttenuation + fLinearAttenuation * distanceToLight + fQuadraticAttenuation * distanceToLight * distanceToLight);
  float attenuation = fConstantAttenuation / ((1.0 + fLinearAttenuation * distanceToLight) * (1.0 + fQuadraticAttenuation * distanceToLight * distanceToLight));
//  attenuation *= pow(spotEffect, 0.15);
//  float attenuation = 1.0;
  vec4 attenuatedLight = lightColor * attenuation;
  attenuatedLight.a = 1.0;
// Dot product gives us diffuse intensity
  float diff = max(0.0, dot(normalize(vVaryingNormal), normalize(vVaryingLightDir)));
// Multiply intensity by diffuse color, force alpha to 1.0
  gl_FragColor = attenuatedLight * (diffuseColor * diff + ambientColor);
// Specular light
  vec3 vReflection = normalize(reflect(-normalize(vVaryingLightDir), normalize(vVaryingNormal)));
  float spec = max(0.0, dot(normalize(vVaryingNormal), vReflection));
// If diffuse light is zero, do not even bother with the pow function
  if(diff != 0.0) {
    float fSpec = pow(spec, shininess);
    gl_FragColor.rgb += attenuatedLight.rgb * vec3(fSpec, fSpec, fSpec);
  }
// For some reaseons, without following multiplications, all scenes exported from Blender are dark. 
// Need to investigate the real reason. For now, it is just workaround to make scene brighter.
//  gl_FragColor.rgb *= vec3(5.5, 5.5, 5.5);
//  gl_FragColor.rgb *= vec3(2.5, 2.5, 2.5);
//  gl_FragColor.rgb += vec3(0.3, 0.3, 0.3);
//  gl_FragColor = diffuseColor + ambientColor;
}'''])

######################################################################
# Point light (Diffuse only), with texture (modulated)
texturePointLightDiff = (['''
uniform mat4 mvMatrix;
uniform mat4 pMatrix;
uniform vec3 vLightPos;
uniform vec4 vColor;
attribute vec4 vVertex;
attribute vec3 vNormal;
varying vec4 vFragColor;
attribute vec2 vTexCoord0;
varying vec2 vTex;
void main(void)
{ 
 mat3 mNormalMatrix;
 mNormalMatrix[0] = normalize(mvMatrix[0].xyz);
 mNormalMatrix[1] = normalize(mvMatrix[1].xyz);
 mNormalMatrix[2] = normalize(mvMatrix[2].xyz);
 vec3 vNorm = normalize(mNormalMatrix * vNormal);
 vec4 ecPosition;
 vec3 ecPosition3;
 ecPosition = mvMatrix * vVertex;
 ecPosition3 = ecPosition.xyz /ecPosition.w;
 vec3 vLightDir = normalize(vLightPos - ecPosition3);
 float fDot = max(0.0, dot(vNorm, vLightDir)); 
 vFragColor.rgb = vColor.rgb * fDot;
 vFragColor.a = vColor.a;
 vTex = vTexCoord0;
 mat4 mvpMatrix;
 mvpMatrix = pMatrix * mvMatrix;
 gl_Position = mvpMatrix * vVertex; 
}'''],
['''
precision mediump float;
varying vec4 vFragColor;
varying vec2 vTex;
uniform sampler2D textureUnit0;
void main(void)
{
 gl_FragColor = texture2D(textureUnit0, vTex);
 if(gl_FragColor.a < 0.1)
  discard;
/* if(gl_FragColor.a < 1.0)
 {
  gl_FragColor.r = 1.0 - gl_FragColor.a;
  gl_FragColor.g = 0;
  gl_FragColor.b = 0;
  gl_FragColor.a = 1.0;
 }*/
// if(vFragColor.a != 0.0)
//  gl_FragColor *= vFragColor;
// else
//  discard;
// gl_FragColor = texture2D(textureUnit0, vTex);
// gl_FragColor = vFragColor;
}'''])


######################################################################
# Phong with textures
texturePhong = (['''
varying vec3 normal, lightDir0, eyeVec;

void main()
{
	normal = gl_NormalMatrix * gl_Normal;

	vec3 vVertex = vec3(gl_ModelViewMatrix * gl_Vertex);

	lightDir0 = vec3(gl_LightSource[0].position.xyz - vVertex);
	eyeVec = -vVertex;

	gl_Position = ftransform();
        gl_TexCoord[0]  = gl_TextureMatrix[0] * gl_MultiTexCoord0;
}
'''], 
['''
varying vec3 normal, lightDir0, eyeVec;
uniform sampler2D my_color_texture[1]; //0 = ColorMap

void main (void)
{
        vec4 texColor = texture2D(my_color_texture[0], gl_TexCoord[0].st);
	vec4 final_color;

/*	final_color = (gl_FrontLightModelProduct.sceneColor * vec4(texColor.rgb,1.0)) +
		      gl_LightSource[0].ambient * vec4(texColor.rgb,1.0);*/
	final_color = (gl_FrontLightModelProduct.sceneColor * vec4(texColor.rgb,1.0)) + 
		       vec4(texColor.rgb,1.0);

	vec3 N = normalize(normal);
	vec3 L0 = normalize(lightDir0);

	float lambertTerm0 = dot(N,L0);

	if(lambertTerm0 > 0.0)
	{
		final_color += gl_LightSource[0].diffuse *
		               gl_FrontMaterial.diffuse *
					   lambertTerm0;

		vec3 E = normalize(eyeVec);
		vec3 R = reflect(-L0, N);
		float specular = pow( max(dot(R, E), 0.0),
		                 gl_FrontMaterial.shininess );
		final_color += gl_LightSource[0].specular *
		               gl_FrontMaterial.specular *
					   specular;
	}
	gl_FragColor = final_color;
}
'''])

########NEW FILE########
__FILENAME__ = print_collada_info
#!/usr/bin/env python

import collada
import numpy
import sys

def inspectController(controller):
    """Display contents of a controller object found in the scene."""
    print '    Controller (id=%s) (type=%s)' % (controller.skin.id, type(controller).__name__)
    print '       Vertex weights:%d, joints:%d' % (len(controller), len(controller.joint_matrices))
    for controlled_prim in controller.primitives():
        print '       Primitive', type(controlled_prim.primitive).__name__

def inspectGeometry(obj):
    """Display contents of a geometry object found in the scene."""
    materials = set()
    for prim in obj.primitives():
        materials.add( prim.material )

    print '    Geometry (id=%s): %d primitives'%(obj.original.id, len(obj))
    for prim in obj.primitives():
        print '        Primitive (type=%s): len=%d vertices=%d' % (type(prim).__name__, len(prim), len(prim.vertex))
    for mat in materials:
        if mat: inspectMaterial( mat )

def inspectMaterial(mat):
    """Display material contents."""
    print '        Material %s: shading %s'%(mat.effect.id, mat.effect.shadingtype)
    for prop in mat.effect.supported:
        value = getattr(mat.effect, prop)
        # it can be a float, a color (tuple) or a Map ( a texture )
        if isinstance(value, collada.material.Map):
            colladaimage = value.sampler.surface.image
            # Accessing this attribute forces the loading of the image
            # using PIL if available. Unless it is already loaded.
            img = colladaimage.pilimage
            if img: # can read and PIL available
                print '            %s = Texture %s:'%(prop, colladaimage.id),\
                      img.format, img.mode, img.size
            else:
                print '            %s = Texture %s: (not available)'%(
                                   prop, colladaimage.id)
        else:
            print '            %s ='%(prop), value

def inspectCollada(col):
    # Display the file contents
    print 'File Contents:'
    print '  Geometry:'
    if col.scene is not None:
        for geom in col.scene.objects('geometry'):
            inspectGeometry( geom )
    print '  Controllers:'
    if col.scene is not None:
        for controller in col.scene.objects('controller'):
            inspectController( controller )
    print '  Cameras:'
    if col.scene is not None:
        for cam in col.scene.objects('camera'):
            print '    Camera %s: '%cam.original.id
    print '  Lights:'
    if col.scene is not None:
        for light in col.scene.objects('light'):
            print '    Light %s: color =' % light.original.id, light.color

    if not col.errors: print 'File read without errors'
    else:
        print 'Errors:'
        for error in col.errors:
            print ' ', error

if __name__ == '__main__':
    filename = sys.argv[1] if  len(sys.argv) > 1 else 'misc/base.zip'

    # open COLLADA file ignoring some errors in case they appear
    col = collada.Collada(filename, ignore=[collada.DaeUnsupportedError,
                                            collada.DaeBrokenRefError])
    inspectCollada(col)
    
########NEW FILE########
__FILENAME__ = recurse_check
import sys
import os, os.path
import traceback
import time
import argparse

try:
    import collada
except:
    sys.exit("Could not find pycollada library.")
        
def main():

    parser = argparse.ArgumentParser(
        description='Recursively scans a directory, loading any .dae file found.')
    parser.add_argument('directory', help='Directory to scan')
    parser.add_argument('--show-time', '-t', default=False, action='store_true',
                        help='Show how much time (in seconds) it took to load file')
    parser.add_argument('--show-warnings', '-w', default=False, action='store_true',
                        help='If warnings present, print warning type')
    parser.add_argument('--show-errors', '-e', default=False, action='store_true',
                        help='If errors present, print error and traceback')
    parser.add_argument('--show-summary', '-s', default=False, action='store_true',
                        help='Print a summary at the end of how many files had warnings and errors')
    parser.add_argument('--zip', '-z', default=False, action='store_true',
                        help='Include .zip files when searching for files to load')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        sys.exit("Given path '%s' is not a directory." % args.directory)
    
    directories = [args.directory]
    collada_files = []
    while len(directories) > 0:
        directory = directories.pop()
        for name in os.listdir(directory):
            fullpath = os.path.join(directory,name)
            (root, ext) = os.path.splitext(fullpath)
            if os.path.isfile(fullpath) and ext.lower() == ".dae":
                collada_files.append(fullpath)
            elif os.path.isfile(fullpath) and ext.lower() == ".zip":
                collada_files.append(fullpath)
            elif os.path.isdir(fullpath):
                directories.append(fullpath)
    
    collada_files.sort()
    
    file_success_count = 0
    file_warning_count = 0
    file_error_count = 0
    
    for c in collada_files:
        (root, leaf) = os.path.split(c)
        print "'%s'..." % leaf,
        sys.stdout.flush()
     
        start_time = time.time()
     
        try:
            col = collada.Collada(c, \
                ignore=[collada.DaeUnsupportedError, collada.DaeBrokenRefError])
            
            if len(col.errors) > 0:
                print "WARNINGS:", len(col.errors)
                file_warning_count += 1
                err_names = [type(e).__name__ for e in col.errors]
                unique = set(err_names)
                type_cts = [(e, err_names.count(e)) for e in unique]
                if args.show_warnings:
                    for e, ct in type_cts:
                        for err in col.errors:
                            if type(err).__name__ == e:
                                print "   %s" % str(err)
                                break
                        if ct > 1:
                            print "   %s: %d additional warnings of this type" % (e, ct-1)
            else:
                print "SUCCESS"
                file_success_count += 1
                
            #do some sanity checks looping through result
            if not col.scene is None:
                for geom in col.scene.objects('geometry'):
                    for prim in geom.primitives():
                        assert(len(prim) >= 0)
                for cam in col.scene.objects('camera'):
                    assert(cam.original.id)
        except (KeyboardInterrupt, SystemExit):
            print
            sys.exit("Keyboard interrupt. Exiting.")
        except:
            print "ERROR"
            file_error_count += 1
            if args.show_errors:
                print
                traceback.print_exc()
                print
            
        end_time = time.time()
        if args.show_time:
            print "   Loaded in %.3f seconds" % (end_time-start_time)

    if args.show_summary:
        print
        print
        print "Summary"
        print "======="
        print "Files loaded successfully: %d" % file_success_count
        print "Files with warnings: %d" % file_warning_count
        print "Files with errors: %d" % file_error_count
            
if __name__ == "__main__":
    main()

########NEW FILE########
