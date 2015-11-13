__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from avatar.models import Avatar
from avatar.signals import avatar_updated
from avatar.templatetags.avatar_tags import avatar
from avatar.util import get_user_model


class AvatarAdmin(admin.ModelAdmin):
    list_display = ('get_avatar', 'user', 'primary', "date_uploaded")
    list_filter = ('primary',)
    search_fields = ('user__%s' % getattr(get_user_model(), 'USERNAME_FIELD', 'username'),)
    list_per_page = 50

    def get_avatar(self, avatar_in):
        return avatar(avatar_in.user, 80)

    get_avatar.short_description = _('Avatar')
    get_avatar.allow_tags = True

    def save_model(self, request, obj, form, change):
        super(AvatarAdmin, self).save_model(request, obj, form, change)
        avatar_updated.send(sender=Avatar, user=request.user, avatar=obj)


admin.site.register(Avatar, AvatarAdmin)

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings
from PIL import Image

from appconf import AppConf


class AvatarConf(AppConf):
    DEFAULT_SIZE = 80
    RESIZE_METHOD = Image.ANTIALIAS
    STORAGE_DIR = 'avatars'
    GRAVATAR_BASE_URL = 'http://www.gravatar.com/avatar/'
    GRAVATAR_BACKUP = True
    GRAVATAR_DEFAULT = None
    DEFAULT_URL = 'avatar/img/default.jpg'
    MAX_AVATARS_PER_USER = 42
    MAX_SIZE = 1024 * 1024
    THUMB_FORMAT = 'JPEG'
    THUMB_QUALITY = 85
    HASH_FILENAMES = False
    HASH_USERDIRNAMES = False
    ALLOWED_FILE_EXTS = None
    CACHE_TIMEOUT = 60 * 60
    STORAGE = settings.DEFAULT_FILE_STORAGE
    CLEANUP_DELETED = False
    AUTO_GENERATE_SIZES = (DEFAULT_SIZE,)

    def configure_auto_generate_avatar_sizes(self, value):
        return value or getattr(settings, 'AUTO_GENERATE_AVATAR_SIZES',
                                (self.DEFAULT_SIZE,))

########NEW FILE########
__FILENAME__ = forms
import os

from django import forms
from django.forms import widgets
from django.utils import six
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import filesizeformat

from avatar.conf import settings
from avatar.models import Avatar


def avatar_img(avatar, size):
    if not avatar.thumbnail_exists(size):
        avatar.create_thumbnail(size)
    return mark_safe('<img src="%s" alt="%s" width="%s" height="%s" />' %
                     (avatar.avatar_url(size), six.text_type(avatar),
                      size, size))


class UploadAvatarForm(forms.Form):

    avatar = forms.ImageField(label=_("avatar"))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(UploadAvatarForm, self).__init__(*args, **kwargs)

    def clean_avatar(self):
        data = self.cleaned_data['avatar']

        if settings.AVATAR_ALLOWED_FILE_EXTS:
            root, ext = os.path.splitext(data.name.lower())
            if ext not in settings.AVATAR_ALLOWED_FILE_EXTS:
                valid_exts = ", ".join(settings.AVATAR_ALLOWED_FILE_EXTS)
                error = _("%(ext)s is an invalid file extension. "
                          "Authorized extensions are : %(valid_exts_list)s")
                raise forms.ValidationError(error %
                                            {'ext': ext,
                                             'valid_exts_list': valid_exts})

        if data.size > settings.AVATAR_MAX_SIZE:
            error = _("Your file is too big (%(size)s), "
                      "the maximum allowed size is %(max_valid_size)s")
            raise forms.ValidationError(error % {
                'size': filesizeformat(data.size),
                'max_valid_size': filesizeformat(settings.AVATAR_MAX_SIZE)
            })

        count = Avatar.objects.filter(user=self.user).count()
        if (settings.AVATAR_MAX_AVATARS_PER_USER > 1 and
                count >= settings.AVATAR_MAX_AVATARS_PER_USER):
            error = _("You already have %(nb_avatars)d avatars, "
                      "and the maximum allowed is %(nb_max_avatars)d.")
            raise forms.ValidationError(error % {
                'nb_avatars': count,
                'nb_max_avatars': settings.AVATAR_MAX_AVATARS_PER_USER,
            })
        return


class PrimaryAvatarForm(forms.Form):

    def __init__(self, *args, **kwargs):
        kwargs.pop('user')
        size = kwargs.pop('size', settings.AVATAR_DEFAULT_SIZE)
        avatars = kwargs.pop('avatars')
        super(PrimaryAvatarForm, self).__init__(*args, **kwargs)
        choices = [(avatar.id, avatar_img(avatar, size)) for avatar in avatars]
        self.fields['choice'] = forms.ChoiceField(label=_("Choices"),
                                                  choices=choices,
                                                  widget=widgets.RadioSelect)


class DeleteAvatarForm(forms.Form):

    def __init__(self, *args, **kwargs):
        kwargs.pop('user')
        size = kwargs.pop('size', settings.AVATAR_DEFAULT_SIZE)
        avatars = kwargs.pop('avatars')
        super(DeleteAvatarForm, self).__init__(*args, **kwargs)
        choices = [(avatar.id, avatar_img(avatar, size)) for avatar in avatars]
        self.fields['choices'] = forms.MultipleChoiceField(label=_("Choices"),
                                                           choices=choices,
                                                           widget=widgets.CheckboxSelectMultiple)

########NEW FILE########
__FILENAME__ = rebuild_avatars
from django.core.management.base import NoArgsCommand

from avatar.conf import settings
from avatar.models import Avatar


class Command(NoArgsCommand):
    help = ("Regenerates avatar thumbnails for the sizes specified in "
            "settings.AVATAR_AUTO_GENERATE_SIZES.")

    def handle_noargs(self, **options):
        for avatar in Avatar.objects.all():
            for size in settings.AVATAR_AUTO_GENERATE_SIZES:
                print("Rebuilding Avatar id=%s at size %s." % (avatar.id, size))
                avatar.create_thumbnail(size)

########NEW FILE########
__FILENAME__ = models
import datetime
import os
import hashlib
from PIL import Image

from django.db import models
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.utils.translation import ugettext as _
from django.utils import six
from django.db.models import signals

from avatar.conf import settings
from avatar.util import get_username, force_bytes, invalidate_cache

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.datetime.now


avatar_storage = get_storage_class(settings.AVATAR_STORAGE)()


def avatar_file_path(instance=None, filename=None, size=None, ext=None):
    tmppath = [settings.AVATAR_STORAGE_DIR]
    if settings.AVATAR_HASH_USERDIRNAMES:
        tmp = hashlib.md5(get_username(instance.user)).hexdigest()
        tmppath.extend([tmp[0], tmp[1], get_username(instance.user)])
    else:
        tmppath.append(get_username(instance.user))
    if not filename:
        # Filename already stored in database
        filename = instance.avatar.name
        if ext and settings.AVATAR_HASH_FILENAMES:
            # An extension was provided, probably because the thumbnail
            # is in a different format than the file. Use it. Because it's
            # only enabled if AVATAR_HASH_FILENAMES is true, we can trust
            # it won't conflict with another filename
            (root, oldext) = os.path.splitext(filename)
            filename = root + "." + ext
    else:
        # File doesn't exist yet
        if settings.AVATAR_HASH_FILENAMES:
            (root, ext) = os.path.splitext(filename)
            filename = hashlib.md5(force_bytes(filename)).hexdigest()
            filename = filename + ext
    if size:
        tmppath.extend(['resized', str(size)])
    tmppath.append(os.path.basename(filename))
    return os.path.join(*tmppath)


def find_extension(format):
    format = format.lower()

    if format == 'jpeg':
        format = 'jpg'

    return format


class Avatar(models.Model):
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'))
    primary = models.BooleanField(default=False)
    avatar = models.ImageField(max_length=1024,
                               upload_to=avatar_file_path,
                               storage=avatar_storage,
                               blank=True)
    date_uploaded = models.DateTimeField(default=now)

    def __unicode__(self):
        return _(six.u('Avatar for %s')) % self.user

    def save(self, *args, **kwargs):
        avatars = Avatar.objects.filter(user=self.user)
        if self.pk:
            avatars = avatars.exclude(pk=self.pk)
        if settings.AVATAR_MAX_AVATARS_PER_USER > 1:
            if self.primary:
                avatars = avatars.filter(primary=True)
                avatars.update(primary=False)
        else:
            avatars.delete()
        super(Avatar, self).save(*args, **kwargs)

    def thumbnail_exists(self, size):
        return self.avatar.storage.exists(self.avatar_name(size))

    def create_thumbnail(self, size, quality=None):
        # invalidate the cache of the thumbnail with the given size first
        invalidate_cache(self.user, size)
        try:
            orig = self.avatar.storage.open(self.avatar.name, 'rb')
            image = Image.open(orig)
            quality = quality or settings.AVATAR_THUMB_QUALITY
            w, h = image.size
            if w != size or h != size:
                if w > h:
                    diff = int((w - h) / 2)
                    image = image.crop((diff, 0, w - diff, h))
                else:
                    diff = int((h - w) / 2)
                    image = image.crop((0, diff, w, h - diff))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image = image.resize((size, size), settings.AVATAR_RESIZE_METHOD)
                thumb = six.BytesIO()
                image.save(thumb, settings.AVATAR_THUMB_FORMAT, quality=quality)
                thumb_file = ContentFile(thumb.getvalue())
            else:
                thumb_file = File(orig)
            thumb = self.avatar.storage.save(self.avatar_name(size), thumb_file)
        except IOError:
            return  # What should we do here?  Render a "sorry, didn't work" img?

    def avatar_url(self, size):
        return self.avatar.storage.url(self.avatar_name(size))

    def get_absolute_url(self):
        return self.avatar_url(settings.AVATAR_DEFAULT_SIZE)

    def avatar_name(self, size):
        ext = find_extension(settings.AVATAR_THUMB_FORMAT)
        return avatar_file_path(
            instance=self,
            size=size,
            ext=ext
        )


def invalidate_avatar_cache(sender, instance, **kwargs):
    invalidate_cache(instance.user)


def create_default_thumbnails(sender, instance, created=False, **kwargs):
    invalidate_avatar_cache(sender, instance)
    if created:
        for size in settings.AVATAR_AUTO_GENERATE_SIZES:
            instance.create_thumbnail(size)


def remove_avatar_images(instance=None, **kwargs):
    for size in settings.AVATAR_AUTO_GENERATE_SIZES:
        if instance.thumbnail_exists(size):
            instance.avatar.storage.delete(instance.avatar_name(size))
    instance.avatar.storage.delete(instance.avatar.name)


signals.post_save.connect(create_default_thumbnails, sender=Avatar)
signals.post_delete.connect(invalidate_avatar_cache, sender=Avatar)

if settings.AVATAR_CLEANUP_DELETED:
    signals.post_delete.connect(remove_avatar_images, sender=Avatar)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


avatar_updated = django.dispatch.Signal(providing_args=["user", "avatar"])

########NEW FILE########
__FILENAME__ = avatar_tags
import hashlib

try:
    from urllib.parse import urljoin, urlencode
except ImportError:
    from urlparse import urljoin
    from urllib import urlencode

from django import template
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import six
from django.utils.translation import ugettext as _

from avatar.conf import settings
from avatar.util import (get_primary_avatar, get_default_avatar_url,
                         cache_result, get_user_model, get_user, force_bytes)
from avatar.models import Avatar

register = template.Library()


@cache_result()
@register.simple_tag
def avatar_url(user, size=settings.AVATAR_DEFAULT_SIZE):
    avatar = get_primary_avatar(user, size=size)
    if avatar:
        return avatar.avatar_url(size)

    if settings.AVATAR_GRAVATAR_BACKUP:
        params = {'s': str(size)}
        if settings.AVATAR_GRAVATAR_DEFAULT:
            params['d'] = settings.AVATAR_GRAVATAR_DEFAULT
        path = "%s/?%s" % (hashlib.md5(force_bytes(user.email)).hexdigest(),
                           urlencode(params))
        return urljoin(settings.AVATAR_GRAVATAR_BASE_URL, path)

    return get_default_avatar_url()


@cache_result()
@register.simple_tag
def avatar(user, size=settings.AVATAR_DEFAULT_SIZE, **kwargs):
    if not isinstance(user, get_user_model()):
        try:
            user = get_user(user)
            alt = six.text_type(user)
            url = avatar_url(user, size)
        except get_user_model().DoesNotExist:
            url = get_default_avatar_url()
            alt = _("Default Avatar")
    else:
        alt = six.text_type(user)
        url = avatar_url(user, size)
    context = dict(kwargs, **{
        'user': user,
        'url': url,
        'alt': alt,
        'size': size,
    })
    return render_to_string('avatar/avatar_tag.html', context)


@register.filter
def has_avatar(user):
    if not isinstance(user, get_user_model()):
        return False
    return Avatar.objects.filter(user=user, primary=True).exists()


@cache_result()
@register.simple_tag
def primary_avatar(user, size=settings.AVATAR_DEFAULT_SIZE):
    """
    This tag tries to get the default avatar for a user without doing any db
    requests. It achieve this by linking to a special view that will do all the
    work for us. If that special view is then cached by a CDN for instance,
    we will avoid many db calls.
    """
    alt = six.text_type(user)
    url = reverse('avatar_render_primary', kwargs={'user': user, 'size': size})
    return ("""<img src="%s" alt="%s" width="%s" height="%s" />""" %
            (url, alt, size, size))


@cache_result()
@register.simple_tag
def render_avatar(avatar, size=settings.AVATAR_DEFAULT_SIZE):
    if not avatar.thumbnail_exists(size):
        avatar.create_thumbnail(size)
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (
        avatar.avatar_url(size), six.text_type(avatar), size, size)


@register.tag
def primary_avatar_object(parser, token):
    split = token.split_contents()
    if len(split) == 4:
        return UsersAvatarObjectNode(split[1], split[3])
    raise template.TemplateSyntaxError('%r tag takes three arguments.' %
                                       split[0])


class UsersAvatarObjectNode(template.Node):
    def __init__(self, user, key):
        self.user = template.Variable(user)
        self.key = key

    def render(self, context):
        user = self.user.resolve(context)
        key = self.key
        avatar = Avatar.objects.filter(user=user, primary=True)
        if avatar:
            context[key] = avatar[0]
        else:
            context[key] = None
        return six.text_type()

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    # Django < 1.4
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('avatar.views',
    url(r'^add/$', 'add', name='avatar_add'),
    url(r'^change/$', 'change', name='avatar_change'),
    url(r'^delete/$', 'delete', name='avatar_delete'),
    url(r'^render_primary/(?P<user>[\w\d\.\-_]{3,30})/(?P<size>[\d]+)/$', 'render_primary', name='avatar_render_primary'),
    url(r'^list/(?P<username>[\+\w\@\.]+)/$', 'avatar_gallery', name='avatar_gallery'),
    url(r'^list/(?P<username>[\+\w\@\.]+)/(?P<id>[\d]+)/$', 'avatar', name='avatar'),
)

########NEW FILE########
__FILENAME__ = util
import hashlib

from django.core.cache import cache
from django.utils import six
from django.template.defaultfilters import slugify

try:
    from django.utils.encoding import force_bytes
except ImportError:
    force_bytes = str

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User

    def get_user_model():
        return User

    custom_user_model = False
else:
    custom_user_model = True

from avatar.conf import settings


cached_funcs = set()


def get_username(user):
    """ Return username of a User instance """
    if hasattr(user, 'get_username'):
        return user.get_username()
    else:
        return user.username


def get_user(username):
    """ Return user from a username/ish identifier """
    if custom_user_model:
        return get_user_model().objects.get_by_natural_key(username)
    else:
        return get_user_model().objects.get(username=username)


def get_cache_key(user_or_username, size, prefix):
    """
    Returns a cache key consisten of a username and image size.
    """
    if isinstance(user_or_username, get_user_model()):
        user_or_username = get_username(user_or_username)
    key = six.u('%s_%s_%s') % (prefix, user_or_username, size)
    return six.u('%s_%s') % (slugify(key)[:100],
                             hashlib.md5(force_bytes(key)).hexdigest())


def cache_set(key, value):
    cache.set(key, value, settings.AVATAR_CACHE_TIMEOUT)
    return value


def cache_result(default_size=settings.AVATAR_DEFAULT_SIZE):
    """
    Decorator to cache the result of functions that take a ``user`` and a
    ``size`` value.
    """
    def decorator(func):
        def cached_func(user, size=None):
            prefix = func.__name__
            cached_funcs.add(prefix)
            key = get_cache_key(user, size or default_size, prefix=prefix)
            result = cache.get(key)
            if result is None:
                result = func(user, size or default_size)
                cache_set(key, result)
            return result
        return cached_func
    return decorator


def invalidate_cache(user, size=None):
    """
    Function to be called when saving or changing an user's avatars.
    """
    sizes = set(settings.AVATAR_AUTO_GENERATE_SIZES)
    if size is not None:
        sizes.add(size)
    for prefix in cached_funcs:
        for size in sizes:
            cache.delete(get_cache_key(user, size, prefix))


def get_default_avatar_url():
    base_url = getattr(settings, 'STATIC_URL', None)
    if not base_url:
        base_url = getattr(settings, 'MEDIA_URL', '')

    # Don't use base_url if the default url starts with http:// of https://
    if settings.AVATAR_DEFAULT_URL.startswith(('http://', 'https://')):
        return settings.AVATAR_DEFAULT_URL
    # We'll be nice and make sure there are no duplicated forward slashes
    ends = base_url.endswith('/')

    begins = settings.AVATAR_DEFAULT_URL.startswith('/')
    if ends and begins:
        base_url = base_url[:-1]
    elif not ends and not begins:
        return '%s/%s' % (base_url, settings.AVATAR_DEFAULT_URL)

    return '%s%s' % (base_url, settings.AVATAR_DEFAULT_URL)


def get_primary_avatar(user, size=settings.AVATAR_DEFAULT_SIZE):
    User = get_user_model()
    if not isinstance(user, User):
        try:
            user = get_user(user)
        except User.DoesNotExist:
            return None
    try:
        # Order by -primary first; this means if a primary=True avatar exists
        # it will be first, and then ordered by date uploaded, otherwise a
        # primary=False avatar will be first.  Exactly the fallback behavior we
        # want.
        avatar = user.avatar_set.order_by("-primary", "-date_uploaded")[0]
    except IndexError:
        avatar = None
    if avatar:
        if not avatar.thumbnail_exists(size):
            avatar.create_thumbnail(size)
    return avatar

########NEW FILE########
__FILENAME__ = views
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import six
from django.utils.translation import ugettext as _

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from avatar.conf import settings
from avatar.forms import PrimaryAvatarForm, DeleteAvatarForm, UploadAvatarForm
from avatar.models import Avatar
from avatar.signals import avatar_updated
from avatar.util import (get_primary_avatar, get_default_avatar_url,
                         get_user_model, get_user)


def _get_next(request):
    """
    The part that's the least straightforward about views in this module is
    how they determine their redirects after they have finished computation.

    In short, they will try and determine the next place to go in the
    following order:

    1. If there is a variable named ``next`` in the *POST* parameters, the
       view will redirect to that variable's value.
    2. If there is a variable named ``next`` in the *GET* parameters,
       the view will redirect to that variable's value.
    3. If Django can determine the previous page from the HTTP headers,
       the view will redirect to that previous page.
    """
    next = request.POST.get('next', request.GET.get('next',
                            request.META.get('HTTP_REFERER', None)))
    if not next:
        next = request.path
    return next


def _get_avatars(user):
    # Default set. Needs to be sliced, but that's it. Keep the natural order.
    avatars = user.avatar_set.all()

    # Current avatar
    primary_avatar = avatars.order_by('-primary')[:1]
    if primary_avatar:
        avatar = primary_avatar[0]
    else:
        avatar = None

    if settings.AVATAR_MAX_AVATARS_PER_USER == 1:
        avatars = primary_avatar
    else:
        # Slice the default set now that we used
        # the queryset for the primary avatar
        avatars = avatars[:settings.AVATAR_MAX_AVATARS_PER_USER]
    return (avatar, avatars)


@login_required
def add(request, extra_context=None, next_override=None,
        upload_form=UploadAvatarForm, *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    avatar, avatars = _get_avatars(request.user)
    upload_avatar_form = upload_form(request.POST or None,
                                     request.FILES or None,
                                     user=request.user)
    if request.method == "POST" and 'avatar' in request.FILES:
        if upload_avatar_form.is_valid():
            avatar = Avatar(user=request.user, primary=True)
            image_file = request.FILES['avatar']
            avatar.avatar.save(image_file.name, image_file)
            avatar.save()
            messages.success(request, _("Successfully uploaded a new avatar."))
            avatar_updated.send(sender=Avatar, user=request.user, avatar=avatar)
            return redirect(next_override or _get_next(request))
    context = {
        'avatar': avatar,
        'avatars': avatars,
        'upload_avatar_form': upload_avatar_form,
        'next': next_override or _get_next(request),
    }
    context.update(extra_context)
    return render(request, 'avatar/add.html', context)


@login_required
def change(request, extra_context=None, next_override=None,
           upload_form=UploadAvatarForm, primary_form=PrimaryAvatarForm,
           *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    avatar, avatars = _get_avatars(request.user)
    if avatar:
        kwargs = {'initial': {'choice': avatar.id}}
    else:
        kwargs = {}
    upload_avatar_form = upload_form(user=request.user, **kwargs)
    primary_avatar_form = primary_form(request.POST or None,
                                       user=request.user,
                                       avatars=avatars, **kwargs)
    if request.method == "POST":
        updated = False
        if 'choice' in request.POST and primary_avatar_form.is_valid():
            avatar = Avatar.objects.get(
                id=primary_avatar_form.cleaned_data['choice'])
            avatar.primary = True
            avatar.save()
            updated = True
            messages.success(request, _("Successfully updated your avatar."))
        if updated:
            avatar_updated.send(sender=Avatar, user=request.user, avatar=avatar)
        return redirect(next_override or _get_next(request))

    context = {
        'avatar': avatar,
        'avatars': avatars,
        'upload_avatar_form': upload_avatar_form,
        'primary_avatar_form': primary_avatar_form,
        'next': next_override or _get_next(request)
    }
    context.update(extra_context)
    return render(request, 'avatar/change.html', context)


@login_required
def delete(request, extra_context=None, next_override=None, *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    avatar, avatars = _get_avatars(request.user)
    delete_avatar_form = DeleteAvatarForm(request.POST or None,
                                          user=request.user,
                                          avatars=avatars)
    if request.method == 'POST':
        if delete_avatar_form.is_valid():
            ids = delete_avatar_form.cleaned_data['choices']
            if six.text_type(avatar.id) in ids and avatars.count() > len(ids):
                # Find the next best avatar, and set it as the new primary
                for a in avatars:
                    if six.text_type(a.id) not in ids:
                        a.primary = True
                        a.save()
                        avatar_updated.send(sender=Avatar, user=request.user,
                                            avatar=avatar)
                        break
            Avatar.objects.filter(id__in=ids).delete()
            messages.success(request,
                             _("Successfully deleted the requested avatars."))
            return redirect(next_override or _get_next(request))

    context = {
        'avatar': avatar,
        'avatars': avatars,
        'delete_avatar_form': delete_avatar_form,
        'next': next_override or _get_next(request),
    }
    context.update(extra_context)

    return render(request, 'avatar/confirm_delete.html', context)


def avatar_gallery(request, username, template_name="avatar/gallery.html"):
    try:
        user = get_user(username)
    except get_user_model().DoesNotExist:
        raise Http404

    context = {
        "other_user": user,
        "avatars": user.avatar_set.all(),
    }

    return render(request, template_name, context)


def avatar(request, username, id, template_name="avatar/avatar.html"):
    try:
        user = get_user(username)
    except get_user_model().DoesNotExist:
        raise Http404
    avatars = user.avatar_set.order_by("-date_uploaded")
    index = None
    avatar = None
    if avatars:
        avatar = avatars.get(pk=id)
        if not avatar:
            return Http404

        index = avatars.filter(date_uploaded__gt=avatar.date_uploaded).count()
        count = avatars.count()

        if index == 0:
            prev = avatars.reverse()[0]
            if count <= 1:
                next = avatars[0]
            else:
                next = avatars[1]
        else:
            prev = avatars[index - 1]

        if (index + 1) >= count:
            next = avatars[0]
            prev_index = index - 1
            if prev_index < 0:
                prev_index = 0
            prev = avatars[prev_index]
        else:
            next = avatars[index + 1]

    return render(request, template_name, {
        "other_user": user,
        "avatar": avatar,
        "index": index + 1,
        "avatars": avatars,
        "next": next,
        "prev": prev,
        "count": count,
    })


def render_primary(request, user=None, size=settings.AVATAR_DEFAULT_SIZE):
    size = int(size)
    avatar = get_primary_avatar(user, size=size)
    if avatar:
        # FIXME: later, add an option to render the resized avatar dynamically
        # instead of redirecting to an already created static file. This could
        # be useful in certain situations, particulary if there is a CDN and
        # we want to minimize the storage usage on our static server, letting
        # the CDN store those files instead
        url = avatar.avatar_url(size)
    else:
        url = get_default_avatar_url()

    return redirect(url)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-avatar documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 13 17:26:12 2013.
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
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-avatar'
copyright = u'2013, django-avatar developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-avatardoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-avatar.tex', u'django-avatar Documentation',
   u'django-avatar developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-avatar', u'django-avatar Documentation',
     [u'django-avatar developers'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-avatar', u'django-avatar Documentation',
   u'django-avatar developers', 'django-avatar', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = settings
import django

DATABASE_ENGINE = 'sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.comments',
    'avatar',
]

ROOT_URLCONF = 'tests.urls'

SITE_ID = 1

SECRET_KEY = 'something-something'

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

ROOT_URLCONF = 'tests.urls'

STATIC_URL = '/site_media/static/'

AVATAR_ALLOWED_FILE_EXTS = ('.jpg', '.png')
AVATAR_MAX_SIZE = 1024 * 1024
AVATAR_MAX_AVATARS_PER_USER = 20

########NEW FILE########
__FILENAME__ = tests
import os.path

from django.test import TestCase
from django.core.urlresolvers import reverse

from avatar.conf import settings
from avatar.util import get_primary_avatar, get_user_model
from avatar.models import Avatar
from PIL import Image


def upload_helper(o, filename):
    f = open(os.path.join(o.testdatapath, filename), "rb")
    response = o.client.post(reverse('avatar_add'), {
        'avatar': f,
    }, follow=True)
    f.close()
    return response


class AvatarUploadTests(TestCase):

    def setUp(self):
        self.testdatapath = os.path.join(os.path.dirname(__file__), "data")
        self.user = get_user_model().objects.create_user('test', 'lennon@thebeatles.com', 'testpassword')
        self.user.save()
        self.client.login(username='test', password='testpassword')
        Image.init()

    def testNonImageUpload(self):
        response = upload_helper(self, "nonimagefile")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.context['upload_avatar_form'].errors, {})

    def testNormalImageUpload(self):
        response = upload_helper(self, "test.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.context['upload_avatar_form'].errors, {})
        avatar = get_primary_avatar(self.user)
        self.assertNotEqual(avatar, None)

    def testImageWithoutExtension(self):
        # use with AVATAR_ALLOWED_FILE_EXTS = ('.jpg', '.png')
        response = upload_helper(self, "imagefilewithoutext")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 0)  # Redirect only if it worked
        self.assertNotEqual(response.context['upload_avatar_form'].errors, {})

    def testImageWithWrongExtension(self):
        # use with AVATAR_ALLOWED_FILE_EXTS = ('.jpg', '.png')
        response = upload_helper(self, "imagefilewithwrongext.ogg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 0)  # Redirect only if it worked
        self.assertNotEqual(response.context['upload_avatar_form'].errors, {})

    def testImageTooBig(self):
        # use with AVATAR_MAX_SIZE = 1024 * 1024
        response = upload_helper(self, "testbig.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 0)  # Redirect only if it worked
        self.assertNotEqual(response.context['upload_avatar_form'].errors, {})

    def testDefaultUrl(self):
        response = self.client.get(reverse('avatar_render_primary', kwargs={
            'user': self.user.username,
            'size': 80,
        }))
        loc = response['Location']
        base_url = getattr(settings, 'STATIC_URL', None)
        if not base_url:
            base_url = settings.MEDIA_URL
        self.assertTrue(base_url in loc)
        self.assertTrue(loc.endswith(settings.AVATAR_DEFAULT_URL))

    def testNonExistingUser(self):
        a = get_primary_avatar("nonexistinguser")
        self.assertEqual(a, None)

    def testThereCanBeOnlyOnePrimaryAvatar(self):
        for i in range(1, 10):
            self.testNormalImageUpload()
        count = Avatar.objects.filter(user=self.user, primary=True).count()
        self.assertEqual(count, 1)

    def testDeleteAvatar(self):
        self.testNormalImageUpload()
        avatar = Avatar.objects.filter(user=self.user)
        self.assertEqual(len(avatar), 1)
        response = self.client.post(reverse('avatar_delete'), {
            'choices': [avatar[0].id],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        count = Avatar.objects.filter(user=self.user).count()
        self.assertEqual(count, 0)

    def testDeletePrimaryAvatarAndNewPrimary(self):
        self.testThereCanBeOnlyOnePrimaryAvatar()
        primary = get_primary_avatar(self.user)
        oid = primary.id
        self.client.post(reverse('avatar_delete'), {
            'choices': [oid],
        })
        primaries = Avatar.objects.filter(user=self.user, primary=True)
        self.assertEqual(len(primaries), 1)
        self.assertNotEqual(oid, primaries[0].id)
        avatars = Avatar.objects.filter(user=self.user)
        self.assertEqual(avatars[0].id, primaries[0].id)

    def testTooManyAvatars(self):
        for i in range(0, settings.AVATAR_MAX_AVATARS_PER_USER):
            self.testNormalImageUpload()
        count_before = Avatar.objects.filter(user=self.user).count()
        response = upload_helper(self, "test.png")
        count_after = Avatar.objects.filter(user=self.user).count()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 0)  # Redirect only if it worked
        self.assertNotEqual(response.context['upload_avatar_form'].errors, {})
        self.assertEqual(count_before, count_after)

    # def testAvatarOrder
    # def testReplaceAvatarWhenMaxIsOne
    # def testHashFileName
    # def testHashUserName
    # def testChangePrimaryAvatar
    # def testDeleteThumbnailAndRecreation
    # def testAutomaticThumbnailCreation

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include


urlpatterns = patterns('',
    (r'^avatar/', include('avatar.urls')),
)

########NEW FILE########
