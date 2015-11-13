__FILENAME__ = admin
from django.http import HttpResponse

from django.contrib import admin

from adminfiles.models import FileUpload
from adminfiles.settings import JQUERY_URL
from adminfiles.listeners import register_listeners

class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['title', 'description', 'upload_date', 'upload', 'mime_type']
    list_editable = ['description']
    prepopulated_fields = {'slug': ('title',)}
# uncomment for snipshot photo editing feature
#    class Media:
#        js = (JQUERY_URL, 'photo-edit.js')
    def response_change(self, request, obj):
        if request.POST.has_key("_popup"):
            return HttpResponse('<script type="text/javascript">'
                                'opener.dismissEditPopup(window);'
                                '</script>')
        return super(FileUploadAdmin, self).response_change(request, obj)

    def delete_view(self, request, *args, **kwargs):
        response = super(FileUploadAdmin, self).delete_view(request,
                                                            *args,
                                                            **kwargs)
        if request.POST.has_key("post") and request.GET.has_key("_popup"):
            return HttpResponse('<script type="text/javascript">'
                                'opener.dismissEditPopup(window);'
                                '</script>')
        return response

    def response_add(self, request, *args, **kwargs):
        if request.POST.has_key('_popup'):
            return HttpResponse('<script type="text/javascript">'
                                'opener.dismissAddUploadPopup(window);'
                                '</script>')
        return super(FileUploadAdmin, self).response_add(request,
                                                         *args,
                                                         **kwargs)


class FilePickerAdmin(admin.ModelAdmin):
    adminfiles_fields = []

    def __init__(self, *args, **kwargs):
        super(FilePickerAdmin, self).__init__(*args, **kwargs)
        register_listeners(self.model, self.adminfiles_fields)

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super(FilePickerAdmin, self).formfield_for_dbfield(
            db_field, **kwargs)
        if db_field.name in self.adminfiles_fields:
            try:
                field.widget.attrs['class'] += " adminfilespicker"
            except KeyError:
                field.widget.attrs['class'] = 'adminfilespicker'
        return field

    class Media:
        js = [JQUERY_URL, 'adminfiles/model.js']

admin.site.register(FileUpload, FileUploadAdmin)

########NEW FILE########
__FILENAME__ = flickr
"""
    flickr.py
    Copyright 2004-6 James Clarke <james@jamesclarke.info>

THIS SOFTWARE IS SUPPLIED WITHOUT WARRANTY OF ANY KIND, AND MAY BE
COPIED, MODIFIED OR DISTRIBUTED IN ANY WAY, AS LONG AS THIS NOTICE
AND ACKNOWLEDGEMENT OF AUTHORSHIP REMAIN.

2006-12-19
Applied patches from Berco Beute and Wolfram Kriesing.
TODO list below is out of date!

2005-06-10
TOOD list:
* flickr.blogs.*
* flickr.contacts.getList
* flickr.groups.browse
* flickr.groups.getActiveList
* flickr.people.getOnlineList
* flickr.photos.getContactsPhotos
* flickr.photos.getContactsPublicPhotos
* flickr.photos.getContext
* flickr.photos.getCounts
* flickr.photos.getExif
* flickr.photos.getNotInSet
* flickr.photos.getPerms
* flickr.photos.getRecent
* flickr.photos.getUntagged
* flickr.photos.setDates
* flickr.photos.setPerms
* flickr.photos.licenses.*
* flickr.photos.notes.*
* flickr.photos.transform.*
* flickr.photosets.getContext
* flickr.photosets.orderSets
* flickr.reflection.* (not important)
* flickr.tags.getListPhoto
* flickr.urls.*
"""

__author__ = "James Clarke <james@jamesclarke.info>"
__version__ = "$Rev$"
__date__ = "$Date$"
__copyright__ = "Copyright 2004-6 James Clarke"

from urllib import urlencode, urlopen
from xml.dom import minidom

HOST = 'http://flickr.com'
API = '/services/rest'

#set these here or using flickr.API_KEY in your application
API_KEY = ''
email = None
password = None

class FlickrError(Exception): pass

class Photo(object):
    """Represents a Flickr Photo."""

    __readonly = ['id', 'secret', 'server', 'isfavorite', 'license', 'rotation', 
                  'owner', 'dateposted', 'datetaken', 'takengranularity', 
                  'title', 'description', 'ispublic', 'isfriend', 'isfamily', 
                  'cancomment', 'canaddmeta', 'comments', 'tags', 'permcomment', 
                  'permaddmeta']

    #XXX: Hopefully None won't cause problems
    def __init__(self, id, owner=None, dateuploaded=None, \
                 title=None, description=None, ispublic=None, \
                 isfriend=None, isfamily=None, cancomment=None, \
                 canaddmeta=None, comments=None, tags=None, secret=None, \
                 isfavorite=None, server=None, license=None, rotation=None):
        """Must specify id, rest is optional."""
        self.__loaded = False
        self.__cancomment = cancomment
        self.__canaddmeta = canaddmeta
        self.__comments = comments
        self.__dateuploaded = dateuploaded
        self.__description = description
        self.__id = id
        self.__license = license
        self.__isfamily = isfamily
        self.__isfavorite = isfavorite
        self.__isfriend = isfriend
        self.__ispublic = ispublic
        self.__owner = owner
        self.__rotation = rotation
        self.__secret = secret
        self.__server = server
        self.__tags = tags
        self.__title = title
        
        self.__dateposted = None
        self.__datetaken = None
        self.__takengranularity = None
        self.__permcomment = None
        self.__permaddmeta = None
    
    def __setattr__(self, key, value):
        if key in self.__class__.__readonly:
            raise AttributeError("The attribute %s is read-only." % key)
        else:
            super(Photo, self).__setattr__(key, value)

    def __getattr__(self, key):
        if not self.__loaded:
            self._load_properties()
        if key in self.__class__.__readonly:
            return super(Photo, self).__getattribute__("_%s__%s" % (self.__class__.__name__, key))
        else:
            return super(Photo, self).__getattribute__(key)

    def _load_properties(self):
        """Loads the properties from Flickr."""
        self.__loaded = True
        
        method = 'flickr.photos.getInfo'
        data = _doget(method, photo_id=self.id)
        
        photo = data.rsp.photo

        self.__secret = photo.secret
        self.__server = photo.server
        self.__isfavorite = photo.isfavorite
        self.__license = photo.license
        self.__rotation = photo.rotation
        


        owner = photo.owner
        self.__owner = User(owner.nsid, username=owner.username,\
                          realname=owner.realname,\
                          location=owner.location)

        self.__title = photo.title.text
        self.__description = photo.description.text
        self.__ispublic = photo.visibility.ispublic
        self.__isfriend = photo.visibility.isfriend
        self.__isfamily = photo.visibility.isfamily

        self.__dateposted = photo.dates.posted
        self.__datetaken = photo.dates.taken
        self.__takengranularity = photo.dates.takengranularity
        
        self.__cancomment = photo.editability.cancomment
        self.__canaddmeta = photo.editability.canaddmeta
        self.__comments = photo.comments.text

        try:
            self.__permcomment = photo.permissions.permcomment
            self.__permaddmeta = photo.permissions.permaddmeta
        except AttributeError:
            self.__permcomment = None
            self.__permaddmeta = None

        #TODO: Implement Notes?
        if hasattr(photo.tags, "tag"):
            if isinstance(photo.tags.tag, list):
                self.__tags = [Tag(tag.id, User(tag.author), tag.raw, tag.text) \
                               for tag in photo.tags.tag]
            else:
                tag = photo.tags.tag
                self.__tags = [Tag(tag.id, User(tag.author), tag.raw, tag.text)]


    def __str__(self):
        return '<Flickr Photo %s>' % self.id
    

    def setTags(self, tags):
        """Set the tags for current photo to list tags.
        (flickr.photos.settags)
        """
        method = 'flickr.photos.setTags'
        tags = uniq(tags)
        _dopost(method, auth=True, photo_id=self.id, tags=tags)
        self._load_properties()


    def addTags(self, tags):
        """Adds the list of tags to current tags. (flickr.photos.addtags)
        """
        method = 'flickr.photos.addTags'
        if isinstance(tags, list):
            tags = uniq(tags)

        _dopost(method, auth=True, photo_id=self.id, tags=tags)
        #load properties again
        self._load_properties()

    def removeTag(self, tag):
        """Remove the tag from the photo must be a Tag object.
        (flickr.photos.removeTag)
        """
        method = 'flickr.photos.removeTag'
        tag_id = ''
        try:
            tag_id = tag.id
        except AttributeError:
            raise FlickrError, "Tag object expected"
        _dopost(method, auth=True, photo_id=self.id, tag_id=tag_id)
        self._load_properties()


    def setMeta(self, title=None, description=None):
        """Set metadata for photo. (flickr.photos.setMeta)"""
        method = 'flickr.photos.setMeta'

        if title is None:
            title = self.title
        if description is None:
            description = self.description
            
        _dopost(method, auth=True, title=title, \
               description=description, photo_id=self.id)
        
        self.__title = title
        self.__description = description

    
    def getURL(self, size='Medium', urlType='url'):
        """Retrieves a url for the photo.  (flickr.photos.getSizes)

        urlType - 'url' or 'source'
        'url' - flickr page of photo
        'source' - image file
        """
        method = 'flickr.photos.getSizes'
        data = _doget(method, photo_id=self.id)
        for psize in data.rsp.sizes.size:
            if psize.label == size:
                return getattr(psize, urlType)
        raise FlickrError, "No URL found"

    def getSizes(self):
        """
        Get all the available sizes of the current image, and all available
        data about them.
        Returns: A list of dicts with the size data.
        """
        method = 'flickr.photos.getSizes'
        data = _doget(method, photo_id=self.id)
        ret = []
        # The given props are those that we return and the according types, since
        # return width and height as string would make "75">"100" be True, which 
        # is just error prone.
        props = {'url':str,'width':int,'height':int,'label':str,'source':str,'text':str}
        for psize in data.rsp.sizes.size:
            d = {}
            for prop,convert_to_type in props.items():
                d[prop] = convert_to_type(getattr(psize, prop))
            ret.append(d)
        return ret
    
    #def getExif(self):
        #method = 'flickr.photos.getExif'
        #data = _doget(method, photo_id=self.id)
        #ret = []
        #for exif in data.rsp.photo.exif:
            #print exif.label, dir(exif)
            ##ret.append({exif.label:exif.})
        #return ret
        ##raise FlickrError, "No URL found"
        
    def getLocation(self):
        """
        Return the latitude+longitutde of the picture.
        Returns None if no location given for this pic.
        """
        method = 'flickr.photos.geo.getLocation'
        try:
            data = _doget(method, photo_id=self.id)
        except FlickrError: # Some other error might have occured too!?
            return None
        loc = data.rsp.photo.location
        return [loc.latitude, loc.longitude]
        
                
class Photoset(object):
    """A Flickr photoset."""

    def __init__(self, id, title, primary, photos=0, description='', \
                 secret='', server=''):
        self.__id = id
        self.__title = title
        self.__primary = primary
        self.__description = description
        self.__count = photos
        self.__secret = secret
        self.__server = server
        
    id = property(lambda self: self.__id)
    title = property(lambda self: self.__title)
    description = property(lambda self: self.__description)
    primary = property(lambda self: self.__primary)

    def __len__(self):
        return self.__count

    def __str__(self):
        return '<Flickr Photoset %s>' % self.id
    
    def getPhotos(self):
        """Returns list of Photos."""
        method = 'flickr.photosets.getPhotos'
        data = _doget(method, photoset_id=self.id)
        photos = data.rsp.photoset.photo
        p = []
        for photo in photos:
            p.append(Photo(photo.id, title=photo.title, secret=photo.secret, \
                           server=photo.server))
        return p    

    def editPhotos(self, photos, primary=None):
        """Edit the photos in this set.

        photos - photos for set
        primary - primary photo (if None will used current)
        """
        method = 'flickr.photosets.editPhotos'

        if primary is None:
            primary = self.primary
            
        ids = [photo.id for photo in photos]
        if primary.id not in ids:
            ids.append(primary.id)

        _dopost(method, auth=True, photoset_id=self.id,\
                primary_photo_id=primary.id,
                photo_ids=ids)
        self.__count = len(ids)
        return True

    def addPhoto(self, photo):
        """Add a photo to this set.

        photo - the photo
        """
        method = 'flickr.photosets.addPhoto'

        _dopost(method, auth=True, photoset_id=self.id, photo_id=photo.id)

        self.__count += 1
        return True

    def removePhoto(self, photo):
        """Remove the photo from this set.

        photo - the photo
        """
        method = 'flickr.photosets.removePhoto'

        _dopost(method, auth=True, photoset_id=self.id, photo_id=photo.id)
        self.__count = self.__count - 1
        return True
        
    def editMeta(self, title=None, description=None):
        """Set metadata for photo. (flickr.photos.setMeta)"""
        method = 'flickr.photosets.editMeta'

        if title is None:
            title = self.title
        if description is None:
            description = self.description
            
        _dopost(method, auth=True, title=title, \
               description=description, photoset_id=self.id)
        
        self.__title = title
        self.__description = description
        return True

    #XXX: Delete isn't handled well as the python object will still exist
    def delete(self):
        """Deletes the photoset.
        """
        method = 'flickr.photosets.delete'

        _dopost(method, auth=True, photoset_id=self.id)
        return True

    def create(cls, photo, title, description=''):
        """Create a new photoset.

        photo - primary photo
        """
        if not isinstance(photo, Photo):
            raise TypeError, "Photo expected"
        
        method = 'flickr.photosets.create'
        data = _dopost(method, auth=True, title=title,\
                       description=description,\
                       primary_photo_id=photo.id)
        
        set = Photoset(data.rsp.photoset.id, title, Photo(photo.id),
                       photos=1, description=description)
        return set
    create = classmethod(create)
                      
        
class User(object):
    """A Flickr user."""

    def __init__(self, id, username=None, isadmin=None, ispro=None, \
                 realname=None, location=None, firstdate=None, count=None):
        """id required, rest optional."""
        self.__loaded = False #so we don't keep loading data
        self.__id = id
        self.__username = username
        self.__isadmin = isadmin
        self.__ispro = ispro
        self.__realname = realname
        self.__location = location
        self.__photos_firstdate = firstdate
        self.__photos_count = count

    #property fu
    id = property(lambda self: self._general_getattr('id'))
    username = property(lambda self: self._general_getattr('username'))
    isadmin = property(lambda self: self._general_getattr('isadmin'))
    ispro = property(lambda self: self._general_getattr('ispro'))
    realname = property(lambda self: self._general_getattr('realname'))
    location = property(lambda self: self._general_getattr('location'))
    photos_firstdate = property(lambda self: \
                                self._general_getattr('photos_firstdate'))
    photos_firstdatetaken = property(lambda self: \
                                     self._general_getattr\
                                     ('photos_firstdatetaken'))
    photos_count = property(lambda self: \
                            self._general_getattr('photos_count'))
    icon_server= property(lambda self: self._general_getattr('icon_server'))
    icon_url= property(lambda self: self._general_getattr('icon_url'))
 
    def _general_getattr(self, var):
        """Generic get attribute function."""
        if getattr(self, "_%s__%s" % (self.__class__.__name__, var)) is None \
           and not self.__loaded:
            self._load_properties()
        return getattr(self, "_%s__%s" % (self.__class__.__name__, var))
            
    def _load_properties(self):
        """Load User properties from Flickr."""
        method = 'flickr.people.getInfo'
        data = _doget(method, user_id=self.__id)

        self.__loaded = True
        
        person = data.rsp.person

        self.__isadmin = person.isadmin
        self.__ispro = person.ispro
        self.__icon_server = person.iconserver
        if int(person.iconserver) > 0:
            self.__icon_url = 'http://photos%s.flickr.com/buddyicons/%s.jpg' \
                              % (person.iconserver, self.__id)
        else:
            self.__icon_url = 'http://www.flickr.com/images/buddyicon.jpg'
        
        self.__username = person.username.text
        self.__realname = person.realname.text
        self.__location = person.location.text
        self.__photos_firstdate = person.photos.firstdate.text
        self.__photos_firstdatetaken = person.photos.firstdatetaken.text
        self.__photos_count = person.photos.count.text

    def __str__(self):
        return '<Flickr User %s>' % self.id
    
    def getPhotosets(self):
        """Returns a list of Photosets."""
        method = 'flickr.photosets.getList'
        data = _doget(method, user_id=self.id)
        sets = []
        if isinstance(data.rsp.photosets.photoset, list):
            for photoset in data.rsp.photosets.photoset:
                sets.append(Photoset(photoset.id, photoset.title.text,\
                                     Photo(photoset.primary),\
                                     secret=photoset.secret, \
                                     server=photoset.server, \
                                     description=photoset.description.text,
                                     photos=photoset.photos))
        else:
            photoset = data.rsp.photosets.photoset
            sets.append(Photoset(photoset.id, photoset.title.text,\
                                     Photo(photoset.primary),\
                                     secret=photoset.secret, \
                                     server=photoset.server, \
                                     description=photoset.description.text,
                                     photos=photoset.photos))
        return sets

    def getPublicFavorites(self, per_page='', page=''):
        return favorites_getPublicList(user_id=self.id, per_page=per_page, \
                                       page=page)

    def getFavorites(self, per_page='', page=''):
        return favorites_getList(user_id=self.id, per_page=per_page, \
                                 page=page)

class Group(object):
    """Flickr Group Pool"""
    def __init__(self, id, name=None, members=None, online=None,\
                 privacy=None, chatid=None, chatcount=None):
        self.__loaded = False
        self.__id = id
        self.__name = name
        self.__members = members
        self.__online = online
        self.__privacy = privacy
        self.__chatid = chatid
        self.__chatcount = chatcount
        self.__url = None

    id = property(lambda self: self._general_getattr('id'))
    name = property(lambda self: self._general_getattr('name'))
    members = property(lambda self: self._general_getattr('members'))
    online = property(lambda self: self._general_getattr('online'))
    privacy = property(lambda self: self._general_getattr('privacy'))
    chatid = property(lambda self: self._general_getattr('chatid'))
    chatcount = property(lambda self: self._general_getattr('chatcount'))

    def _general_getattr(self, var):
        """Generic get attribute function."""
        if getattr(self, "_%s__%s" % (self.__class__.__name__, var)) is None \
           and not self.__loaded:
            self._load_properties()
        return getattr(self, "_%s__%s" % (self.__class__.__name__, var))

    def _load_properties(self):
        """Loads the properties from Flickr."""
        method = 'flickr.groups.getInfo'
        data = _doget(method, group_id=self.id)

        self.__loaded = True
        
        group = data.rsp.group

        self.__name = photo.name.text
        self.__members = photo.members.text
        self.__online = photo.online.text
        self.__privacy = photo.privacy.text
        self.__chatid = photo.chatid.text
        self.__chatcount = photo.chatcount.text

    def __str__(self):
        return '<Flickr Group %s>' % self.id
    
    def getPhotos(self, tags='', per_page='', page=''):
        """Get a list of photo objects for this group"""
        method = 'flickr.groups.pools.getPhotos'
        data = _doget(method, group_id=self.id, tags=tags,\
                      per_page=per_page, page=page)
        photos = []
        for photo in data.rsp.photos.photo:
            photos.append(_parse_photo(photo))
        return photos

    def add(self, photo):
        """Adds a Photo to the group"""
        method = 'flickr.groups.pools.add'
        _dopost(method, auth=True, photo_id=photo.id, group_id=self.id)
        return True

    def remove(self, photo):
        """Remove a Photo from the group"""
        method = 'flickr.groups.pools.remove'
        _dopost(method, auth=True, photo_id=photo.id, group_id=self.id)
        return True
    
class Tag(object):
    def __init__(self, id, author, raw, text):
        self.id = id
        self.author = author
        self.raw = raw
        self.text = text

    def __str__(self):
        return '<Flickr Tag %s (%s)>' % (self.id, self.text)

    
#Flickr API methods
#see api docs http://www.flickr.com/services/api/
#for details of each param

#XXX: Could be Photo.search(cls)
def photos_search(user_id='', auth=False,  tags='', tag_mode='', text='',\
                  min_upload_date='', max_upload_date='',\
                  min_taken_date='', max_taken_date='', \
                  license='', per_page='', page='', sort=''):
    """Returns a list of Photo objects.

    If auth=True then will auth the user.  Can see private etc
    """
    method = 'flickr.photos.search'

    data = _doget(method, auth=auth, user_id=user_id, tags=tags, text=text,\
                  min_upload_date=min_upload_date,\
                  max_upload_date=max_upload_date, \
                  min_taken_date=min_taken_date, \
                  max_taken_date=max_taken_date, \
                  license=license, per_page=per_page,\
                  page=page, sort=sort)
    photos = []
    if isinstance(data.rsp.photos.photo, list):
        for photo in data.rsp.photos.photo:
            photos.append(_parse_photo(photo))
    else:
        photos = [_parse_photo(data.rsp.photos.photo)]
    return photos

#XXX: Could be class method in User
def people_findByEmail(email):
    """Returns User object."""
    method = 'flickr.people.findByEmail'
    data = _doget(method, find_email=email)
    user = User(data.rsp.user.id, username=data.rsp.user.username.text)
    return user

def people_findByUsername(username):
    """Returns User object."""
    method = 'flickr.people.findByUsername'
    data = _doget(method, username=username)
    user = User(data.rsp.user.id, username=data.rsp.user.username.text)
    return user

#XXX: Should probably be in User as a list User.public
def people_getPublicPhotos(user_id, per_page='', page=''):
    """Returns list of Photo objects."""
    method = 'flickr.people.getPublicPhotos'
    data = _doget(method, user_id=user_id, per_page=per_page, page=page)
    photos = []
    if hasattr(data.rsp.photos, "photo"): # Check if there are photos at all (may be been paging too far).
        if isinstance(data.rsp.photos.photo, list):
            for photo in data.rsp.photos.photo:
                photos.append(_parse_photo(photo))
        else:
            photos = [_parse_photo(data.rsp.photos.photo)]
    return photos

#XXX: These are also called from User
def favorites_getList(user_id='', per_page='', page=''):
    """Returns list of Photo objects."""
    method = 'flickr.favorites.getList'
    data = _doget(method, auth=True, user_id=user_id, per_page=per_page,\
                  page=page)
    photos = []
    if isinstance(data.rsp.photos.photo, list):
        for photo in data.rsp.photos.photo:
            photos.append(_parse_photo(photo))
    else:
        photos = [_parse_photo(data.rsp.photos.photo)]
    return photos

def favorites_getPublicList(user_id, per_page='', page=''):
    """Returns list of Photo objects."""
    method = 'flickr.favorites.getPublicList'
    data = _doget(method, auth=False, user_id=user_id, per_page=per_page,\
                  page=page)
    photos = []
    if isinstance(data.rsp.photos.photo, list):
        for photo in data.rsp.photos.photo:
            photos.append(_parse_photo(photo))
    else:
        photos = [_parse_photo(data.rsp.photos.photo)]
    return photos

def favorites_add(photo_id):
    """Add a photo to the user's favorites."""
    method = 'flickr.favorites.add'
    _dopost(method, auth=True, photo_id=photo_id)
    return True

def favorites_remove(photo_id):
    """Remove a photo from the user's favorites."""
    method = 'flickr.favorites.remove'
    _dopost(method, auth=True, photo_id=photo_id)
    return True

def groups_getPublicGroups():
    """Get a list of groups the auth'd user is a member of."""
    method = 'flickr.groups.getPublicGroups'
    data = _doget(method, auth=True)
    groups = []
    if isinstance(data.rsp.groups.group, list):
        for group in data.rsp.groups.group:
            groups.append(Group(group.id, name=group.name))
    else:
        group = data.rsp.groups.group
        groups = [Group(group.id, name=group.name)]
    return groups

def groups_pools_getGroups():
    """Get a list of groups the auth'd user can post photos to."""
    method = 'flickr.groups.pools.getGroups'
    data = _doget(method, auth=True)
    groups = []
    if isinstance(data.rsp.groups.group, list):
        for group in data.rsp.groups.group:
            groups.append(Group(group.id, name=group.name, \
                                privacy=group.privacy))
    else:
        group = data.rsp.groups.group
        groups = [Group(group.id, name=group.name, privacy=group.privacy)]
    return groups
    

def tags_getListUser(user_id=''):
    """Returns a list of tags for the given user (in string format)"""
    method = 'flickr.tags.getListUser'
    auth = user_id == ''
    data = _doget(method, auth=auth, user_id=user_id)
    if isinstance(data.rsp.tags.tag, list):
        return [tag.text for tag in data.rsp.tags.tag]
    else:
        return [data.rsp.tags.tag.text]

def tags_getListUserPopular(user_id='', count=''):
    """Gets the popular tags for a user in dictionary form tag=>count"""
    method = 'flickr.tags.getListUserPopular'
    auth = user_id == ''
    data = _doget(method, auth=auth, user_id=user_id)
    result = {}
    if isinstance(data.rsp.tags.tag, list):
        for tag in data.rsp.tags.tag:
            result[tag.text] = tag.count
    else:
        result[data.rsp.tags.tag.text] = data.rsp.tags.tag.count
    return result

def tags_getrelated(tag):
    """Gets the related tags for given tag."""
    method = 'flickr.tags.getRelated'
    data = _doget(method, auth=False, tag=tag)
    if isinstance(data.rsp.tags.tag, list):
        return [tag.text for tag in data.rsp.tags.tag]
    else:
        return [data.rsp.tags.tag.text]

def contacts_getPublicList(user_id):
    """Gets the contacts (Users) for the user_id"""
    method = 'flickr.contacts.getPublicList'
    data = _doget(method, auth=False, user_id=user_id)
    if isinstance(data.rsp.contacts.contact, list):
        return [User(user.nsid, username=user.username) \
                for user in data.rsp.contacts.contact]
    else:
        user = data.rsp.contacts.contact
        return [User(user.nsid, username=user.username)]

def interestingness():
    method = 'flickr.interestingness.getList'
    data = _doget(method)
    photos = []
    if isinstance(data.rsp.photos.photo , list):
        for photo in data.rsp.photos.photo:
            photos.append(_parse_photo(photo))
    else:
        photos = [_parse_photo(data.rsp.photos.photo)]
    return photos    
    
def test_login():
    method = 'flickr.test.login'
    data = _doget(method, auth=True)
    user = User(data.rsp.user.id, username=data.rsp.user.username.text)
    return user

def test_echo():
    method = 'flickr.test.echo'
    data = _doget(method)
    return data.rsp.stat


#useful methods

def _doget(method, auth=False, **params):
    #uncomment to check you aren't killing the flickr server
    #print "***** do get %s" % method

    #convert lists to strings with ',' between items
    for (key, value) in params.items():
        if isinstance(value, list):
            params[key] = ','.join([item for item in value])
        
    url = '%s%s/?api_key=%s&method=%s&%s'% \
          (HOST, API, API_KEY, method, urlencode(params))
    if auth:
        url = url + '&email=%s&password=%s' % (email, password)

    #another useful debug print statement
    #print url
    
    xml = minidom.parse(urlopen(url))
    data = unmarshal(xml)
    if not data.rsp.stat == 'ok':
        msg = "ERROR [%s]: %s" % (data.rsp.err.code, data.rsp.err.msg)
        raise FlickrError, msg
    return data

def _dopost(method, auth=False, **params):
    #uncomment to check you aren't killing the flickr server
    #print "***** do post %s" % method

    #convert lists to strings with ',' between items
    for (key, value) in params.items():
        if isinstance(value, list):
            params[key] = ','.join([item for item in value])

    url = '%s%s/' % (HOST, API)

    payload = 'api_key=%s&method=%s&%s'% \
          (API_KEY, method, urlencode(params))
    if auth:
        payload = payload + '&email=%s&password=%s' % (email, password)

    #another useful debug print statement
    #print url
    #print payload
    
    xml = minidom.parse(urlopen(url, payload))
    data = unmarshal(xml)
    if not data.rsp.stat == 'ok':
        msg = "ERROR [%s]: %s" % (data.rsp.err.code, data.rsp.err.msg)
        raise FlickrError, msg
    return data

def _parse_photo(photo):
    """Create a Photo object from photo data."""
    owner = User(photo.owner)
    title = photo.title
    ispublic = photo.ispublic
    isfriend = photo.isfriend
    isfamily = photo.isfamily
    secret = photo.secret
    server = photo.server
    p = Photo(photo.id, owner=owner, title=title, ispublic=ispublic,\
              isfriend=isfriend, isfamily=isfamily, secret=secret, \
              server=server)        
    return p

#stolen methods

class Bag: pass

#unmarshal taken and modified from pyamazon.py
#makes the xml easy to work with
def unmarshal(element):
    rc = Bag()
    if isinstance(element, minidom.Element):
        for key in element.attributes.keys():
            setattr(rc, key, element.attributes[key].value)
            
    childElements = [e for e in element.childNodes \
                     if isinstance(e, minidom.Element)]
    if childElements:
        for child in childElements:
            key = child.tagName
            if hasattr(rc, key):
                if type(getattr(rc, key)) <> type([]):
                    setattr(rc, key, [getattr(rc, key)])
                setattr(rc, key, getattr(rc, key) + [unmarshal(child)])
            elif isinstance(child, minidom.Element) and \
                     (child.tagName == 'Details'):
                # make the first Details element a key
                setattr(rc,key,[unmarshal(child)])
                #dbg: because otherwise 'hasattr' only tests
                #dbg: on the second occurence: if there's a
                #dbg: single return to a query, it's not a
                #dbg: list. This module should always
                #dbg: return a list of Details objects.
            else:
                setattr(rc, key, unmarshal(child))
    else:
        #jec: we'll have the main part of the element stored in .text
        #jec: will break if tag <text> is also present
        text = "".join([e.data for e in element.childNodes \
                        if isinstance(e, minidom.Text)])
        setattr(rc, 'text', text)
    return rc

#unique items from a list from the cookbook
def uniq(alist):    # Fastest without order preserving
    set = {}
    map(set.__setitem__, alist, [])
    return set.keys()

if __name__ == '__main__':
    print test_echo()

########NEW FILE########
__FILENAME__ = listeners
from itertools import chain

from django.db.models.signals import pre_save, post_save, pre_delete

from django.contrib.contenttypes.models import ContentType

from adminfiles.models import FileUpload, FileUploadReference
from adminfiles.parse import get_uploads
from adminfiles import settings

def get_ctype_kwargs(obj):
    return {'content_type': ContentType.objects.get_for_model(obj),
            'object_id': obj.id}

def _get_field(instance, field):
    """
    This is here to support ``MarkupField``. It's a little ugly to
    have that support baked-in; other option would be to have a
    generic way (via setting?) to override how attribute values are
    fetched from content model instances.

    """
    
    value = getattr(instance, field)
    if hasattr(value, 'raw'):
        value = value.raw
    return value

referring_models = set()
            
def register_listeners(model, fields):

    def _update_references(sender, instance, **kwargs):
        ref_kwargs = get_ctype_kwargs(instance)
        for upload in chain(*[get_uploads(_get_field(instance, field))
                              for field in fields]):
            FileUploadReference.objects.get_or_create(**dict(ref_kwargs,
                                                             upload=upload))

    def _delete_references(sender, instance, **kwargs):
        ref_kwargs = get_ctype_kwargs(instance)
        FileUploadReference.objects.filter(**ref_kwargs).delete()

    if settings.ADMINFILES_USE_SIGNALS:
        referring_models.add(model)
        post_save.connect(_update_references, sender=model, weak=False)
        pre_delete.connect(_delete_references, sender=model, weak=False)


def _update_content(sender, instance, created=None, **kwargs):
    """
    Re-save any content models referencing the just-modified
    ``FileUpload``.

    We don't do anything special to the content model, we just re-save
    it. If signals are in use, we assume that the content model has
    incorporated ``render_uploads`` into some kind of rendering that
    happens automatically at save-time.

    """
    if created: # a brand new FileUpload won't be referenced
        return
    for ref in FileUploadReference.objects.filter(upload=instance):
        try:
            obj = ref.content_object
            if obj:
                obj.save()
        except AttributeError:
            pass

def _register_upload_listener():
    if settings.ADMINFILES_USE_SIGNALS:
        post_save.connect(_update_content, sender=FileUpload)
_register_upload_listener()

def _disconnect_upload_listener():
    post_save.disconnect(_update_content)

########NEW FILE########
__FILENAME__ = adminfiles_browser_views
from django.core.management.base import NoArgsCommand, CommandError

from adminfiles.settings import ADMINFILES_BROWSER_VIEWS
from adminfiles.views import import_browser, DisableView, BaseView

class Command(NoArgsCommand):
    """
    List all browser views from ADMINFILES_BROWSER_VIEWS and display
    whether each one is enabled or disabled, and why.

    """
    def handle_noargs(self, **options):
        print "Adminfiles browser views available:"
        print
        for browser_path in ADMINFILES_BROWSER_VIEWS:
            try:
                view_class = import_browser(browser_path)
                view_class().check()
                message = 'enabled'
            except (DisableView, ImportError), e:
                message = 'disabled (%s)' % e.args[0]
            if not issubclass(view_class, BaseView):
                message = 'disabled (not subclass of adminfiles.views.BaseView)'
            print " * %s: %s" % (browser_path, message)
            

########NEW FILE########
__FILENAME__ = sync_upload_refs
from django.core.management.base import NoArgsCommand, CommandError
from adminfiles.settings import ADMINFILES_USE_SIGNALS

from django.contrib import admin

from adminfiles.models import FileUploadReference
from adminfiles.listeners import referring_models

class Command(NoArgsCommand):
    """
    Delete all ``FileUploadReference`` instances, then re-save all
    instances of all models which might contain references to uploaded
    files. This ensures that file upload references are in a
    consistent state, and renderings of uploads are brought
    up-to-date.

    Should only be necessary in unusual circumstances (such as just
    after loading a fixture on a different deployment, where
    e.g. MEDIA_URL might differ, which would affect the rendering of
    links to file uploads).

    Likely to be quite slow if used on a large data set.

    """
    def handle_noargs(self, **options):
        if not ADMINFILES_USE_SIGNALS:
            raise CommandError('This command has no effect if '
                               'ADMINFILES_USE_SIGNALS setting is False.')

        FileUploadReference.objects.all().delete()

        # apps register themselves as referencing file uploads by
        # inheriting their admin options from FilePickerAdmin
        admin.autodiscover()
        for model in referring_models:
            print "Syncing %s" % model.__name__
            for obj in model._default_manager.all():
                obj.save()

########NEW FILE########
__FILENAME__ = models
import os
import mimetypes

from django.conf import settings as django_settings
from django.db import models
from django.template.defaultfilters import slugify
from django.core.files.images import get_image_dimensions
from django.utils.translation import ugettext_lazy as _

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from adminfiles import settings

if 'tagging' in django_settings.INSTALLED_APPS:
    from tagging.fields import TagField
else:
    TagField = None

class FileUpload(models.Model):
    upload_date = models.DateTimeField(_('upload date'), auto_now_add=True)
    upload = models.FileField(_('file'), upload_to=settings.ADMINFILES_UPLOAD_TO)
    title = models.CharField(_('title'), max_length=100)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)
    description = models.CharField(_('description'), blank=True, max_length=200)
    content_type = models.CharField(editable=False, max_length=100)
    sub_type = models.CharField(editable=False, max_length=100)

    if TagField:
        tags = TagField(_('tags'))
    
    class Meta:
        ordering = ['upload_date', 'title']
        verbose_name = _('file upload')
        verbose_name_plural = _('file uploads')

    def __unicode__(self):
        return self.title

    def mime_type(self):
        return '%s/%s' % (self.content_type, self.sub_type)
    mime_type.short_description = _('mime type')

    def type_slug(self):
        return slugify(self.sub_type)

    def is_image(self):
        return self.content_type == 'image'

    def _get_dimensions(self):
        try:
            return self._dimensions_cache
        except AttributeError:
            if self.is_image():
                self._dimensions_cache = get_image_dimensions(self.upload.path)
            else:
                self._dimensions_cache = (None, None)
        return self._dimensions_cache
    
    def width(self):
        return self._get_dimensions()[0]
    
    def height(self):
        return self._get_dimensions()[1]
    
    def save(self, *args, **kwargs):
        try:
            uri = self.upload.path
        except NotImplementedError:
            uri = self.upload.url
        (mime_type, encoding) = mimetypes.guess_type(uri)
        try:
            [self.content_type, self.sub_type] = mime_type.split('/')
        except:
            self.content_type = 'text'
            self.sub_type = 'plain'
        super(FileUpload, self).save()

    def insert_links(self):
        links = []
        for key in [self.mime_type(), self.content_type, '']:
            if key in settings.ADMINFILES_INSERT_LINKS:
                links = settings.ADMINFILES_INSERT_LINKS[key]
                break
        for link in links:
            ref = self.slug
            opts = ':'.join(['%s=%s' % (k,v) for k,v in link[1].items()])
            if opts:
                ref += ':' + opts
            yield {'desc': link[0],
                   'ref': ref}

    def mime_image(self):
        if not settings.ADMINFILES_STDICON_SET:
            return None
        return ('http://www.stdicon.com/%s/%s?size=64'
                % (settings.ADMINFILES_STDICON_SET, self.mime_type()))



class FileUploadReference(models.Model):
    """
    Tracks which ``FileUpload``s are referenced by which content models.

    """
    upload = models.ForeignKey(FileUpload)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('upload', 'content_type', 'object_id')

########NEW FILE########
__FILENAME__ = parse
import re

from adminfiles import settings
from adminfiles.models import FileUpload

# Upload references look like: <<< upload-slug : key=val : key2=val2 >>>
# Spaces are optional, key-val opts are optional, can be any number
# extra indirection is for testability
def _get_upload_re():
    return re.compile(r'%s\s*([\w-]+)((\s*:\s*\w+\s*=\s*.+?)*)\s*%s'
                      % (re.escape(settings.ADMINFILES_REF_START),
                         re.escape(settings.ADMINFILES_REF_END)))
UPLOAD_RE = _get_upload_re()

def get_uploads(text):
    """
    Return a generator yielding uploads referenced in the given text.

    """
    uploads = []
    for match in UPLOAD_RE.finditer(text):
        try:
            upload = FileUpload.objects.get(slug=match.group(1))
        except FileUpload.DoesNotExist:
            continue
        yield upload

def substitute_uploads(text, sub_callback):
    """
    Return text with all upload references substituted using
    sub_callback, which must accept an re match object and return the
    replacement string.

    """
    return UPLOAD_RE.sub(sub_callback, text)

def parse_match(match):
    """
    Accept an re match object resulting from an ``UPLOAD_RE`` match
    and return a two-tuple where the first element is the
    corresponding ``FileUpload`` and the second is a dictionary of the
    key=value options.

    If there is no ``FileUpload`` object corresponding to the match,
    the first element of the returned tuple is None.

    """
    try:
        upload = FileUpload.objects.get(slug=match.group(1))
    except FileUpload.DoesNotExist:
        upload = None
    options = parse_options(match.group(2))
    return (upload, options)

def parse_options(s):
    """
    Expects a string in the form "key=val:key2=val2" and returns a
    dictionary.

    """
    options = {}
    for option in s.split(':'):
        if '=' in option:
            key, val = option.split('=')
            options[str(key).strip()] = val.strip()
    return options

########NEW FILE########
__FILENAME__ = settings
import posixpath

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

JQUERY_URL = getattr(settings, 'JQUERY_URL',
                     'http://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.min.js')

if JQUERY_URL and not ((':' in JQUERY_URL) or (JQUERY_URL.startswith('/'))):
    JQUERY_URL = posixpath.join(settings.STATIC_URL, JQUERY_URL)

ADMINFILES_UPLOAD_TO = getattr(settings, 'ADMINFILES_UPLOAD_TO', 'adminfiles')

ADMINFILES_THUMB_ORDER = getattr(settings, 'ADMINFILES_THUMB_ORDER',
                                 ('-upload_date',))

ADMINFILES_USE_SIGNALS = getattr(settings, 'ADMINFILES_USE_SIGNALS', False)

ADMINFILES_REF_START = getattr(settings, 'ADMINFILES_REF_START', '<<<')

ADMINFILES_REF_END = getattr(settings, 'ADMINFILES_REF_END', '>>>')

ADMINFILES_STRING_IF_NOT_FOUND = getattr(settings,
                                         'ADMINFILES_STRING_IF_NOT_FOUND',
                                         u'')

ADMINFILES_INSERT_LINKS = getattr(
    settings,
    'ADMINFILES_INSERT_LINKS',
    {'': [(_('Insert Link'), {})],
     'image': [(_('Insert'), {}),
               (_('Insert (align left)'), {'class': 'left'}),
               (_('Insert (align right)'), {'class': 'right'})]
     },
    )

ADMINFILES_STDICON_SET = getattr(settings, 'ADMINFILES_STDICON_SET', None)

ADMINFILES_BROWSER_VIEWS = getattr(settings, 'ADMINFILES_BROWSER_VIEWS',
                                   ['adminfiles.views.AllView',
                                    'adminfiles.views.ImagesView',
                                    'adminfiles.views.AudioView',
                                    'adminfiles.views.FilesView',
                                    'adminfiles.views.FlickrView',
                                    'adminfiles.views.YouTubeView',
                                    'adminfiles.views.VimeoView'])

########NEW FILE########
__FILENAME__ = adminfiles_tags
from django import template

from adminfiles.parse import parse_options
from adminfiles import utils

register = template.Library()

@register.filter
def render_uploads(content,
                   template_path="adminfiles/render/"):
    """
    Render uploaded file references in a content string
    (i.e. translate "<<<my-uploaded-file>>>" to '<a
    href="/path/to/my/uploaded/file">My uploaded file</a>').
    
    Just wraps ``adminfiles.utils.render_uploads``.

    """
    return utils.render_uploads(content, template_path)
render_uploads.is_safe = True

@register.filter
def render_upload(upload, opts_str=''):
    """
    Render a single ``FileUpload`` model instance using the
    appropriate render template for its mime type.

    Expects options to be in the format "key=val:key2=val2", just like
    the embed syntax. Options are parsed into a dictionary and passed
    to ``render_upload``. (A ``template_path`` option can be passed
    and it will be used as the search path for rendering templates.)

    Just wraps ``adminfiles.utils.render_upload``.

    """
    return utils.render_upload(upload, **parse_options(opts_str))
render_upload.is_safe = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from django.contrib.admin.views.decorators import staff_member_required

from adminfiles.views import download, get_enabled_browsers

urlpatterns = patterns('',
    url(r'download/$', staff_member_required(download),
        name="adminfiles_download")
)

for browser in get_enabled_browsers():
    slug = browser.slug()
    urlpatterns += patterns('',
        url('%s/$' % slug, browser.as_view(),
            name='adminfiles_%s' % slug))

########NEW FILE########
__FILENAME__ = utils
from os.path import join

from django import template
from django.conf import settings

if 'oembed' in settings.INSTALLED_APPS:
    try:
        # djangoembed
        from oembed.consumer import OEmbedConsumer
        def oembed_replace(text):
            consumer = OEmbedConsumer()
            return consumer.parse(text)
    except ImportError:
        # django-oembed
        from oembed.core import replace as oembed_replace
else:
    oembed_replace = lambda s: s

from adminfiles.parse import parse_match, substitute_uploads
from adminfiles import settings

def render_uploads(content, template_path="adminfiles/render/"):
    """
    Replace all uploaded file references in a content string with the
    results of rendering a template found under ``template_path`` with
    the ``FileUpload`` instance and the key=value options found in the
    file reference.

    So if "<<<my-uploaded-file:key=val:key2=val2>>>" is found in the
    content string, it will be replaced with the results of rendering
    the selected template with ``upload`` set to the ``FileUpload``
    instance with slug "my-uploaded-file" and ``options`` set to
    {'key': 'val', 'key2': 'val2'}.

    If the given slug is not found, the reference is replaced with the
    empty string.

    If ``djangoembed`` or ``django-oembed`` is installed, also replaces OEmbed
    URLs with the appropriate embed markup.
    
    """
    def _replace(match):
        upload, options = parse_match(match)
        return render_upload(upload, template_path, **options)
    return oembed_replace(substitute_uploads(content, _replace))


def render_upload(upload, template_path="adminfiles/render/", **options):
    """
    Render a single ``FileUpload`` model instance using the
    appropriate rendering template and the given keyword options, and
    return the rendered HTML.
    
    The template used to render each upload is selected based on the
    mime-type of the upload. For an upload with mime-type
    "image/jpeg", assuming the default ``template_path`` of
    "adminfiles/render", the template used would be the first one
    found of the following: ``adminfiles/render/image/jpeg.html``,
    ``adminfiles/render/image/default.html``, and
    ``adminfiles/render/default.html``
    
    """
    if upload is None:
        return settings.ADMINFILES_STRING_IF_NOT_FOUND
    template_name = options.pop('as', None)
    if template_name:
        templates = [template_name,
                     "%s/default" % template_name.split('/')[0],
                     "default"]
    else:
        templates = [join(upload.content_type, upload.sub_type),
                     join(upload.content_type, "default"),
                     "default"]
    tpl = template.loader.select_template(
        ["%s.html" % join(template_path, p) for p in templates])
    return tpl.render(template.Context({'upload': upload,
                                        'options': options}))

########NEW FILE########
__FILENAME__ = views
import urllib

from django.http import HttpResponse
from django.conf import settings as django_settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from adminfiles.models import FileUpload
from adminfiles import settings

class DisableView(Exception):
    pass

class BaseView(TemplateView):
    template_name = 'adminfiles/uploader/base.html'

    def get_context_data(self, **kwargs):
        context = super(BaseView, self).get_context_data(**kwargs)
        context.update({
            'browsers': get_enabled_browsers(),
            'field_id': self.request.GET['field'],
            'field_type': self.request.GET.get('field_type', 'textarea'),
            'ADMINFILES_REF_START': settings.ADMINFILES_REF_START,
            'ADMINFILES_REF_END': settings.ADMINFILES_REF_END,
            'JQUERY_URL': settings.JQUERY_URL
        })

        return context

    @classmethod
    def slug(cls):
        """
        Return slug suitable for accessing this view in a URLconf.

        """
        slug = cls.__name__.lower()
        if slug.endswith('view'):
            slug = slug[:-4]
        return slug

    @classmethod
    def link_text(cls):
        """
        Return link text for this view.

        """
        link = cls.__name__
        if link.endswith('View'):
            link = link[:-4]
        return link

    @classmethod
    def url(cls):
        """
        Return URL for this view.

        """
        return reverse('adminfiles_%s' % cls.slug())

    @classmethod
    def check(cls):
        """
        Raise ``DisableView`` if the configuration necessary for this
        view is not active.

        """
        pass


class AllView(BaseView):
    link_text = _('All Uploads')

    def files(self):
        return FileUpload.objects.all()

    def get_context_data(self, **kwargs):
        context = super(AllView, self).get_context_data(**kwargs)
        context.update({
            'files': self.files().order_by(*settings.ADMINFILES_THUMB_ORDER)
        })
        return context


class ImagesView(AllView):
    link_text = _('Images')

    def files(self):
        return super(ImagesView, self).files().filter(content_type='image')


class AudioView(AllView):
    link_text = _('Audio')

    def files(self):
        return super(AudioView, self).files().filter(content_type='audio')


class FilesView(AllView):
    link_text = _('Files')

    def files(self):
        not_files = ['video', 'image', 'audio']
        return super(FilesView, self).files().exclude(content_type__in=not_files)

class OEmbedView(BaseView):
    @classmethod
    def check(cls):
        if 'oembed' not in django_settings.INSTALLED_APPS:
            raise DisableView('OEmbed views require django-oembed or djangoembed. '
                              '(http://pypi.python.org/pypi/django-oembed, '
                              'http://pypi.python.org/pypi/djangoembed)')

class YouTubeView(OEmbedView):
    template_name = 'adminfiles/uploader/video.html'

    @classmethod
    def check(cls):
        super(YouTubeView, cls).check()
        try:
            from gdata.youtube.service import YouTubeService
        except ImportError:
            raise DisableView('YouTubeView requires "gdata" library '
                              '(http://pypi.python.org/pypi/gdata)')
        try:
            django_settings.ADMINFILES_YOUTUBE_USER
        except AttributeError:
            raise DisableView('YouTubeView requires '
                              'ADMINFILES_YOUTUBE_USER setting')

    def get_context_data(self, **kwargs):
        context = super(YouTubeView, self).get_context_data(**kwargs)
        context.update({
            'videos': self.videos()
        })
        return context

    def videos(self):
        from gdata.youtube.service import YouTubeService
        feed = YouTubeService().GetYouTubeVideoFeed(
            "http://gdata.youtube.com/feeds/videos?author=%s&orderby=updated"
            % django_settings.ADMINFILES_YOUTUBE_USER)
        videos = []
        for entry in feed.entry:
            videos.append({
                    'title': entry.media.title.text,
                    'upload_date': entry.published.text.split('T')[0],
                    'description': entry.media.description.text,
                    'thumb': entry.media.thumbnail[0].url,
                    'url': entry.media.player.url.split('&')[0],
                    })
        return videos


class FlickrView(OEmbedView):
    template_name = 'adminfiles/uploader/flickr.html'

    @classmethod
    def check(cls):
        super(FlickrView, cls).check()
        try:
            import flickrapi
        except ImportError:
            raise DisableView('FlickrView requires the "flickrapi" library '
                              '(http://pypi.python.org/pypi/flickrapi)')
        try:
            django_settings.ADMINFILES_FLICKR_USER
            django_settings.ADMINFILES_FLICKR_API_KEY
        except AttributeError:
            raise DisableView('FlickrView requires '
                              'ADMINFILES_FLICKR_USER and '
                              'ADMINFILES_FLICKR_API_KEY settings')

    def get_context_data(self, **kwargs):
        context = super(FlickrView, self).get_context_data(**kwargs)
        page = int(request.GET.get('page', 1))
        base_path = '%s?field=%s&page=' % (request.path, request.GET['field'])
        context['next_page'] = base_path + str(page + 1)
        if page > 1:
            context['prev_page'] = base_path + str(page - 1)
        else:
            context['prev_page'] = None
        context['photos'] = self.photos(page)
        return context

    def photos(self, page=1):
        import flickrapi
        user = django_settings.ADMINFILES_FLICKR_USER
        flickr = flickrapi.FlickrAPI(django_settings.ADMINFILES_FLICKR_API_KEY)
        # Get the user's NSID
        nsid = flickr.people_findByUsername(
            username=user).find('user').attrib['nsid']
        # Get 12 photos for the user
        flickr_photos = flickr.people_getPublicPhotos(
            user_id=nsid, per_page=12, page=page).find('photos').findall('photo')
        photos = []
        for f in flickr_photos:
            photo = {}
            photo['url'] = 'http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s_m.jpg' % f.attrib
            photo['link'] = 'http://www.flickr.com/photos/%s/%s' % (
                nsid, f.attrib['id'])
            photo['title'] = f.attrib['title']
            photos.append(photo)
        return photos


class VimeoView(OEmbedView):
    template_name = 'adminfiles/uploader/video.html'

    @classmethod
    def check(cls):
        super(VimeoView, cls).check()
        try:
            django_settings.ADMINFILES_VIMEO_USER
        except AttributeError:
            raise DisableView('VimeoView requires '
                              'ADMINFILES_VIMEO_USER setting')
        try:
            cls.pages = django_settings.ADMINFILES_VIMEO_PAGES
        except AttributeError:
            cls.pages = 1
        if cls.pages > 3:
            cls.pages = 3

    def get_context_data(self, **kwargs):
        context = super(VimeoView, self).get_context_data(**kwargs)
        context.update({
            'videos':self.videos()
        })
        return context

    def _get_videos(self, url):
        import urllib2
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            import elementtree.ElementTree as ET
        request = urllib2.Request(url)
        request.add_header('User-Agent', 'django-adminfiles/0.x')
        root = ET.parse(urllib2.build_opener().open(request)).getroot()
        videos = []
        for v in root.findall('video'):
            videos.append({
                    'title': v.find('title').text,
                    'upload_date': v.find('upload_date').text.split()[0],
                    'description': v.find('description').text,
                    'thumb': v.find('thumbnail_small').text,
                    'url': v.find('url').text,
                    })
        return videos

    def videos(self):
        url = ('http://vimeo.com/api/v2/%s/videos.xml'
               % django_settings.ADMINFILES_VIMEO_USER)
        videos = self._get_videos(url)
        for page in range(2, self.pages + 1):
            page_url = "%s?page=%s" % (url, page)
            page_videos = self._get_videos(page_url)
            if not page_videos:
                break
            videos += page_videos
        return videos


def download(request):
    '''Saves image from URL and returns ID for use with AJAX script'''
    f = FileUpload()
    f.title = request.GET['title'] or 'untitled'
    f.description = request.GET['description']
    url = urllib.unquote(request.GET['photo'])
    file_content = urllib.urlopen(url).read()
    file_name = url.split('/')[-1]
    f.save_upload_file(file_name, file_content)
    f.save()
    return HttpResponse('%s' % (f.id))


_enabled_browsers_cache = None

def get_enabled_browsers():
    """
    Check the ADMINFILES_BROWSER_VIEWS setting and return a list of
    instantiated browser views that have the necessary
    dependencies/configuration to run.

    """
    global _enabled_browsers_cache
    if _enabled_browsers_cache is not None:
        return _enabled_browsers_cache
    enabled = []
    for browser_path in settings.ADMINFILES_BROWSER_VIEWS:
        try:
            view_class = import_browser(browser_path)
        except ImportError:
            continue
        if not issubclass(view_class, BaseView):
            continue
        browser = view_class
        try:
            browser.check()
        except DisableView:
            continue
        enabled.append(browser)
    _enabled_browsers_cache = enabled
    return enabled

def import_browser(path):
    module, classname = path.rsplit('.', 1)
    return getattr(__import__(module, {}, {}, [classname]), classname)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=50)
    content = models.TextField()

    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os, sys

parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'

def runtests():
    from django.test.simple import DjangoTestSuiteRunner
    runner = DjangoTestSuiteRunner(
        verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(['tests'])
    sys.exit(failures)

if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase, Client
from django.conf import settings as django_settings
from django.test.utils import ContextList
from django.test.signals import template_rendered
from django import template
from django.db.models.signals import pre_save

from django.contrib import admin
from django.contrib.auth.models import User

from adminfiles import settings, parse
from adminfiles.utils import render_uploads
from adminfiles.models import FileUpload, FileUploadReference
from adminfiles.listeners import _register_upload_listener, \
    _disconnect_upload_listener
from adminfiles.admin import FilePickerAdmin

from models import Post

class PostAdmin(FilePickerAdmin):
    adminfiles_fields = ('content',)

class FileUploadTestCase(TestCase):
    """
    Test case with a populate() method to save a couple FileUpload instances.

    """
    def populate(self):
        self.animage = FileUpload.objects.create(
            upload='adminfiles/tiny.png',
            title='An image',
            slug='an-image')
        self.somefile = FileUpload.objects.create(
            upload='adminfiles/somefile.txt',
            title='Some file',
            slug='some-file')

class FilePickerTests(FileUploadTestCase):
    def setUp(self):
        self.populate()
        self.client = Client()
        admin.site.register(Post, PostAdmin)
        self.admin = User.objects.create_user('admin', 'admin@example.com',
                                              'testpw')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.is_active = True
        self.admin.save()
        self.assertTrue(self.client.login(username='admin', password='testpw'))

    def tearDown(self):
        admin.site.unregister(Post)

    def test_picker_class_applied(self):
        response = self.client.get('/admin/tests/post/add/')
        self.assertContains(response, 'class="vLargeTextField adminfilespicker"')

    def test_picker_loads(self):
        """
        Very basic smoke test for file picker.

        """
        response = self.client.get('/adminfiles/all/?field=test')
        self.assertContains(response, 'href="/media/adminfiles/tiny.png"')
        self.assertContains(response, 'href="/media/adminfiles/somefile.txt')

    def test_browser_links(self):
        """
        Test correct rendering of browser links.

        """
        response = self.client.get('/adminfiles/all/?field=test')
        self.assertContains(response, 'href="/adminfiles/images/?field=test')

    def test_images_picker_loads(self):
        response = self.client.get('/adminfiles/images/?field=test')
        self.assertContains(response, 'href="/media/adminfiles/tiny.png"')
        self.assertNotContains(response, 'href="/media/adminfiles/somefile.txt')

    def test_files_picker_loads(self):
        response = self.client.get('/adminfiles/files/?field=test')
        self.assertNotContains(response, 'href="/media/adminfiles/tiny.png"')
        self.assertContains(response, 'href="/media/adminfiles/somefile.txt')

    def test_custom_links(self):
        _old_links = settings.ADMINFILES_INSERT_LINKS.copy()
        settings.ADMINFILES_INSERT_LINKS['text/plain'] = [('Crazy insert', {'yo': 'thing'})]

        response = self.client.get('/adminfiles/all/?field=test')
        self.assertContains(response, 'rel="some-file:yo=thing"')

        settings.ADMINFILES_INSERT_LINKS = _old_links

    def test_thumb_order(self):
        _old_order = settings.ADMINFILES_THUMB_ORDER
        settings.ADMINFILES_THUMB_ORDER = ('title',)

        response = self.client.get('/adminfiles/all/?field=test')
        image_index = response.content.find('tiny.png')
        file_index = response.content.find('somefile.txt')
        self.assertTrue(image_index > 0)
        self.assertTrue(image_index < file_index)

        settings.ADMINFILES_THUMB_ORDER = _old_order

class SignalTests(FileUploadTestCase):
    """
    Test tracking of uploaded file references, and auto-resave of
    content models when referenced uploaded file changes.

    """
    def setUp(self):
        self._old_use_signals = settings.ADMINFILES_USE_SIGNALS
        settings.ADMINFILES_USE_SIGNALS = True
        if not self._old_use_signals:
            _register_upload_listener()

        PostAdmin(Post, admin.site)

        self.populate()

    def tearDown(self):
        if not self._old_use_signals:
            _disconnect_upload_listener()
        settings.ADMINFILES_USE_SIGNALS = self._old_use_signals

    def test_track_references(self):
        Post.objects.create(title='Some title',
                            content='This has a reference to'
                            '<<<some-file>>>')

        self.assertEquals(FileUploadReference.objects.count(), 1)

    def test_track_multiple_references(self):
        Post.objects.create(title='Some title',
                            content='This has a reference to'
                            '<<<some-file>>> and <<<an-image>>>')

        self.assertEquals(FileUploadReference.objects.count(), 2)

    def test_track_no_dupe_references(self):
        post = Post.objects.create(title='Some title',
                                   content='This has a reference to'
                                   '<<<an-image>>> and <<<an-image>>>')

        post.save()

        self.assertEquals(FileUploadReference.objects.count(), 1)

    def test_update_reference(self):
        post = Post.objects.create(title='Some title',
                                   content='This has a reference to'
                                   '<<<some-file>>>')

        def _render_on_save(sender, instance, **kwargs):
            instance.content = render_uploads(instance.content)
        pre_save.connect(_render_on_save, sender=Post)

        self.somefile.title = 'A New Title'
        self.somefile.save()

        reloaded_post = Post.objects.get(title='Some title')

        self.assertTrue('A New Title' in reloaded_post.content)

class TemplateTestCase(TestCase):
    """
    A TestCase that stores information about rendered templates, much
    like the Django test client.

    """
    def store_rendered_template(self, signal, sender, template, context,
                                **kwargs):
        self.templates.append(template)
        self.contexts.append(context)

    def setUp(self):
        self.templates = []
        self.contexts = ContextList()
        template_rendered.connect(self.store_rendered_template)

    def tearDown(self):
        template_rendered.disconnect(self.store_rendered_template)

class RenderTests(TemplateTestCase, FileUploadTestCase):
    """
    Test rendering of uploaded file references.

    """
    def setUp(self):
        super(RenderTests, self).setUp()
        self.populate()

    def test_render_template_used(self):
        render_uploads('<<<some-file>>>')
        self.assertEquals(self.templates[0].name,
                          'adminfiles/render/default.html')

    def test_render_mimetype_template_used(self):
        render_uploads('<<<an-image>>>')
        self.assertEquals(self.templates[0].name,
                          'adminfiles/render/image/default.html')

    def test_render_subtype_template_used(self):
        render_uploads('<<<an-image>>>', 'alt')
        self.assertEquals(self.templates[0].name,
                          'alt/image/png.html')

    def test_render_whitespace(self):
        render_uploads('<<< some-file \n>>>')
        self.assertEquals(len(self.templates), 1)

    def test_render_amidst_content(self):
        render_uploads('Some test here<<< some-file \n>>>and more here')
        self.assertEquals(len(self.templates), 1)

    def test_render_upload_in_context(self):
        render_uploads('<<<some-file>>>')
        self.assertEquals(self.contexts['upload'].upload.name,
                          'adminfiles/somefile.txt')

    def test_render_options_in_context(self):
        render_uploads('<<<some-file:class=left:key=val>>>')
        self.assertEquals(self.contexts['options'], {'class': 'left',
                                                     'key': 'val'})

    def test_render_alternate_markers(self):
        old_start = settings.ADMINFILES_REF_START
        old_end = settings.ADMINFILES_REF_END
        settings.ADMINFILES_REF_START = '[[['
        settings.ADMINFILES_REF_END = ']]]'
        parse.UPLOAD_RE = parse._get_upload_re()

        render_uploads('[[[some-file]]]')
        self.assertEquals(len(self.templates), 1)

        settings.ADMINFILES_REF_START = old_start
        settings.ADMINFILES_REF_END = old_end
        parse.UPLOAD_RE = parse._get_upload_re()

    def test_render_invalid(self):
        old_nf = settings.ADMINFILES_STRING_IF_NOT_FOUND
        settings.ADMINFILES_STRING_IF_NOT_FOUND = u'not found'

        html = render_uploads('<<<invalid-slug>>>')
        self.assertEquals(html, u'not found')

        settings.ADMINFILES_STRING_IF_NOT_FOUND = old_nf

    def test_default_template_renders_image(self):
        html = render_uploads('<<<an-image>>>')
        self.assertTrue('<img src="/media/adminfiles/tiny.png"' in html)

    def test_default_template_renders_image_class(self):
        html = render_uploads('<<<an-image:class=some classes>>>')
        self.assertTrue('class="some classes"' in html)

    def test_default_template_renders_image_alt(self):
        html = render_uploads('<<<an-image:alt=the alt text>>>')
        self.assertTrue('alt="the alt text"' in html)

    def test_default_template_renders_image_title_as_alt(self):
        html = render_uploads('<<<an-image>>>')
        self.assertTrue('alt="An image"' in html)

    def test_default_template_renders_link(self):
        html = render_uploads('<<<some-file>>>')
        self.assertTrue('<a href="/media/adminfiles/somefile.txt"' in html)

    def test_default_template_renders_link_class(self):
        html = render_uploads(u'<<<some-file:class=other classes>>>')
        self.assertTrue('class="other classes"' in html)

    def test_default_template_renders_link_title(self):
        html = render_uploads('<<<some-file>>>')
        self.assertTrue('Some file' in html)

    def test_default_template_renders_link_title(self):
        html = render_uploads('<<<some-file:title=Other name>>>')
        self.assertTrue('Other name' in html)

    def test_template_override(self):
        html = render_uploads('<<<an-image:as=default>>>')
        self.assertTrue('<a href="/media/adminfiles/tiny.png"' in html)

    def test_template_override_fallback(self):
        html = render_uploads('<<<some-file:as=image/jpeg>>>')
        self.assertTrue('<img src="/media/adminfiles/somefile.txt"' in html)

    def test_template_override_with_nonexisting(self):
        html = render_uploads('<<<an-image:as=some/wonky>>>')
        self.assertTrue('<a href="/media/adminfiles/tiny.png"' in html)

    def test_render_uploads_template_filter(self):
        tpl = template.Template(u'{% load adminfiles_tags %}'
                                u'{{ post.content|render_uploads|safe }}')
        html = tpl.render(template.Context({
                    'post': Post(title=u'a post',
                                 content=u'<<<some-file>>>')}))
        self.assertEquals(self.templates[1].name,
                          'adminfiles/render/default.html')
        self.assertTrue('<a href' in html)

    def test_render_uploads_template_filter_alt_template(self):
        tpl = template.Template(
            u'{% load adminfiles_tags %}'
            u'{{ post.content|render_uploads:"alt" }}')
        html = tpl.render(template.Context({
                    'post': Post(title=u'a post',
                                 content=u'<<<some-file>>>')}))
        self.assertEquals(self.templates[1].name, 'alt/default.html')

    def test_render_upload_template_filter(self):
        tpl = template.Template(u'{% load adminfiles_tags %}'
                                u'{{ img|render_upload }}')
        html = tpl.render(template.Context({'img': self.animage}))
        self.assertEquals(self.templates[1].name,
                          'adminfiles/render/image/default.html')
        self.assertTrue('<img src' in html)

    def test_render_upload_template_filter_options(self):
        tpl = template.Template('{% load adminfiles_tags %}'
                                '{{ img|render_upload:"alt=blah" }}')
        html = tpl.render(template.Context({'img': self.animage}))
        self.assertTrue('alt="blah"' in html)

    def test_render_upload_template_filter_alt_template(self):
        tpl = template.Template(
            u'{% load adminfiles_tags %}'
            u'{{ f|render_upload:"template_path=alt" }}')
        html = tpl.render(template.Context({'f': self.somefile}))
        self.assertEquals(self.templates[1].name, 'alt/default.html')

    def test_render_upload_template_filter_alt_template_options(self):
        tpl = template.Template(
            u'{% load adminfiles_tags %}'
            u'{{ f|render_upload:"template_path=alt:class=yo" }}')
        html = tpl.render(template.Context({'f': self.somefile}))
        self.assertEquals(self.templates[1].name, 'alt/default.html')
        self.assertTrue('class="yo"' in html)


########NEW FILE########
__FILENAME__ = test_settings
from os.path import dirname, join
TEST_ROOT = dirname(__file__)

INSTALLED_APPS = ('adminfiles', 'tests',
                  'django.contrib.contenttypes',
                  'django.contrib.admin',
                  'django.contrib.sites',
                  'django.contrib.auth',
                  'django.contrib.sessions',
                  'sorl.thumbnail')
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        }
    }

SITE_ID = 1

MEDIA_URL = '/media/'
MEDIA_ROOT = join(TEST_ROOT, 'media')

STATIC_URL = '/static/'
STATIC_ROOT = MEDIA_ROOT

ROOT_URLCONF = 'tests.urls'

TEMPLATE_DIRS = (join(TEST_ROOT, 'templates'),)

SECRET_KEY = 'not empty'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include

from django.contrib import admin

urlpatterns = patterns('',
    url(r'^adminfiles/', include('adminfiles.urls')),
    url(r'^admin/', include(admin.site.urls))
    )

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os
BASE = os.path.dirname(os.path.abspath(__file__))

DEBUG = True

SITE_ID = 1

DATABASES = {
    "default": {
        "ENGINE": 'django.db.backends.sqlite3',
        "NAME":os.path.join(BASE, 'adminfiles-test.db'),
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE, 'static')
MEDIA_ROOT = os.path.join(BASE, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
SECRET_KEY = '6wk#pb((9+oudihdco6m@#1hmr1qp#k+7a=p7c@#z91_^=en-!'

ROOT_URLCONF = 'test_project.urls'

FIXTURE_DIRS = [
    os.path.join(BASE, 'fixtures')
    ]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'adminfiles',
    'sorl.thumbnail',
    'testapp',
    'oembed',
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from adminfiles.admin import FilePickerAdmin

from test_project.testapp.models import Article

class ArticleAdmin(FilePickerAdmin):
    adminfiles_fields = ['content']

admin.site.register(Article, ArticleAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    
    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'', include(admin.site.urls)),
    url(r'^adminfiles/', include('adminfiles.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
