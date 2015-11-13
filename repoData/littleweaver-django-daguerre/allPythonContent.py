__FILENAME__ = adjustments
from __future__ import division
from six.moves import xrange

from daguerre.utils import exif_aware_resize, exif_aware_size

try:
    from PIL import Image
except ImportError:
    import Image


class AdjustmentRegistry(object):
    def __init__(self):
        self._registry = {}
        self._default = None

    def register(self, cls):
        self._registry[cls.__name__.lower()] = cls
        return cls

    def __getitem__(self, key):
        return self._registry[key]

    def get(self, key, default=None):
        return self._registry.get(key, default)

    def __contains__(self, item):
        return item in self._registry

    def items(self):
        return self._registry.items()


registry = AdjustmentRegistry()


class Adjustment(object):
    """
    Base class for all adjustments which can be carried out on an image. The
    adjustment itself represents a set of parameters, which can then be
    applied to images (taking areas into account if applicable).

    Adjustment subclasses need to define two methods: :meth:`calculate` and
    :meth:`adjust`. If the method doesn't use areas, you can set the
    ``uses_areas`` attribute on the method to ``False`` to optimize
    adjustment.

    :param kwargs: The requested kwargs for the adjustment. The keys must
                   be in :attr:`parameters` or the adjustment is invalid.

    """
    #: Accepted parameters for this adjustment - for example, ``"width"``,
    #: ``"height"``, ``"color"``, ``"unicorns"``, etc.
    parameters = ()

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for key in kwargs:
            if key not in self.parameters:
                raise ValueError('Parameter "{0}" not accepted by {1}.'
                                 ''.format(key, self.__class__.__name__))

    def calculate(self, dims, areas=None):
        """
        Calculates the dimensions of the adjusted image without actually
        manipulating the image. By default, just returns the given dimensions.

        :param dims: ``(width, height)`` tuple of the current image
                     dimensions.
        :param areas: iterable of :class:`.Area` instances to be considered in
                      calculating the adjustment.

        """
        return dims
    calculate.uses_areas = False

    def adjust(self, image, areas=None):
        """
        Manipulates and returns the image. Must be implemented by subclasses.

        :param image: PIL Image which will be adjusted.
        :param areas: iterable of :class:`.Area` instances to be considered in
                      performing the adjustment.

        """
        raise NotImplementedError


@registry.register
class Fit(Adjustment):
    """
    Resizes an image to fit entirely within the given dimensions
    without cropping and maintaining the width/height ratio.

    If neither width nor height is specified, this adjustment will simply
    return a copy of the image.

    """
    parameters = ('width', 'height')

    def calculate(self, dims, areas=None):
        image_width, image_height = dims
        width, height = self.kwargs.get('width'), self.kwargs.get('height')

        if width is None and height is None:
            return image_width, image_height

        image_ratio = float(image_width) / image_height

        if height is None:
            # Constrain first by width, then by max_height.
            new_width = int(width)
            new_height = int(new_width / image_ratio)
        elif width is None:
            # Constrain first by height, then by max_width.
            new_height = int(height)
            new_width = int(new_height * image_ratio)
        else:
            # Constrain strictly by both dimensions.
            width, height = int(width), int(height)
            new_width = int(min(width, height * image_ratio))
            new_height = int(min(height, width / image_ratio))

        return new_width, new_height
    calculate.uses_areas = False

    def adjust(self, image, areas=None):
        image_width, image_height = exif_aware_size(image)
        new_width, new_height = self.calculate((image_width, image_height))

        if (new_width, new_height) == (image_width, image_height):
            return image.copy()

        # Choose a resize filter based on whether
        # we're upscaling or downscaling.
        if new_width < image_width:
            f = Image.ANTIALIAS
        else:
            f = Image.BICUBIC

        return exif_aware_resize(image, (new_width, new_height), f)
    adjust.uses_areas = False


@registry.register
class Crop(Adjustment):
    """
    Crops an image to the given width and height, without scaling it.
    :class:`~daguerre.models.Area` instances which are passed in will be
    protected as much as possible during the crop.

    """
    parameters = ('width', 'height')

    def calculate(self, dims, areas=None):
        image_width, image_height = dims
        width, height = self.kwargs.get('width'), self.kwargs.get('height')
        # image_width and image_height are known to be defined.
        new_width = int(width) if width is not None else image_width
        new_height = int(height) if height is not None else image_height

        new_width = min(new_width, image_width)
        new_height = min(new_height, image_height)

        return new_width, new_height
    calculate.uses_areas = False

    def adjust(self, image, areas=None):
        image_width, image_height = exif_aware_size(image)
        new_width, new_height = self.calculate((image_width, image_height))

        if (new_width, new_height) == (image_width, image_height):
            return image.copy()

        if not areas:
            x1 = int((image_width - new_width) / 2)
            y1 = int((image_height - new_height) / 2)
        else:
            min_penalty = None
            optimal_coords = None

            for x in xrange(image_width - new_width + 1):
                for y in xrange(image_height - new_height + 1):
                    penalty = 0
                    for area in areas:
                        penalty += self._get_penalty(area, x, y,
                                                     new_width, new_height)
                        if min_penalty is not None and penalty > min_penalty:
                            break

                    if min_penalty is None or penalty < min_penalty:
                        min_penalty = penalty
                        optimal_coords = [(x, y)]
                    elif penalty == min_penalty:
                        optimal_coords.append((x, y))
            x1, y1 = optimal_coords[0]

        x2 = x1 + new_width
        y2 = y1 + new_height

        return image.crop((x1, y1, x2, y2))

    def _get_penalty(self, area, x1, y1, new_width, new_height):
        x2 = x1 + new_width
        y2 = y1 + new_height
        if area.x1 >= x1 and area.x2 <= x2 and area.y1 >= y1 and area.y2 <= y2:
            # The area is enclosed. No penalty
            penalty_area = 0
        elif area.x2 < x1 or area.x1 > x2 or area.y2 < y1 or area.y1 > y2:
            # The area is excluded. Penalty for the whole thing.
            penalty_area = area.area
        else:
            # Partial penalty.
            non_penalty_area = (min(area.x2 - x1, x2 - area.x1, area.width) *
                                min(area.y2 - y1, y2 - area.y1, area.height))
            penalty_area = area.area - non_penalty_area
        return penalty_area / area.priority


@registry.register
class RatioCrop(Crop):
    """
    Crops an image to the given aspect ratio, without scaling it.
    :class:`~daguerre.models.Area` instances which are passed in will be
    protected as much as possible during the crop.

    """
    #: ``ratio`` should be formatted as ``"<width>:<height>"``
    parameters = ('ratio',)

    def calculate(self, dims, areas=None):
        image_width, image_height = dims
        image_ratio = float(image_width) / image_height
        ratio_str = self.kwargs.get('ratio')

        if ratio_str is None:
            return image_width, image_height

        width, height = ratio_str.split(':')
        ratio = float(width) / float(height)

        if ratio > image_ratio:
            # New ratio is wider. Cut the height.
            new_width = image_width
            new_height = int(image_width / ratio)
        else:
            new_width = int(image_height * ratio)
            new_height = image_height

        return new_width, new_height
    calculate.uses_areas = False


@registry.register
class NamedCrop(Adjustment):
    """
    Crops an image to the given named area, without scaling it.
    :class:`~daguerre.models.Area` instances which are passed in will be
    protected as much as possible during the crop.

    If no area with the given name exists, this adjustment is a no-op.

    """
    parameters = ('name',)

    def calculate(self, dims, areas=None):
        image_width, image_height = dims

        if not areas:
            return image_width, image_height

        for area in areas:
            if area.name == self.kwargs['name']:
                break
        else:
            return image_width, image_height

        return area.width, area.height

    def adjust(self, image, areas=None):
        image_width, image_height = exif_aware_size(image)

        if not areas:
            return image.copy()

        for area in areas:
            if area.name == self.kwargs['name']:
                break
        else:
            return image.copy()

        return image.crop((area.x1, area.y1,
                           area.x2, area.y2))


@registry.register
class Fill(Adjustment):
    """
    Crops the image to the requested ratio (using the same logic as
    :class:`.Crop` to protect :class:`~daguerre.models.Area` instances which
    are passed in), then resizes it to the actual requested dimensions. If
    ``width`` or ``height`` is not given, then the unspecified dimension will
    be allowed to expand up to ``max_width`` or ``max_height``, respectively.

    """
    parameters = ('width', 'height', 'max_width', 'max_height')

    def calculate(self, dims, areas=None):
        image_width, image_height = dims
        width, height = self.kwargs.get('width'), self.kwargs.get('height')

        if width is None and height is None:
            # No restrictions: return original dimensions.
            return image_width, image_height

        max_width = self.kwargs.get('max_width')
        max_height = self.kwargs.get('max_height')
        image_ratio = float(image_width) / image_height

        if width is None:
            new_height = int(height)
            new_width = int(new_height * image_ratio)
            if max_width is not None:
                new_width = min(new_width, int(max_width))
        elif height is None:
            new_width = int(width)
            new_height = int(new_width / image_ratio)
            if max_height is not None:
                new_height = min(new_height, int(max_height))
        else:
            new_width = int(width)
            new_height = int(height)

        return new_width, new_height
    calculate.uses_areas = False

    def adjust(self, image, areas=None):
        image_width, image_height = exif_aware_size(image)
        new_width, new_height = self.calculate((image_width, image_height))

        if (new_width, new_height) == (image_width, image_height):
            return image.copy()

        ratiocrop = RatioCrop(ratio="{0}:{1}".format(new_width, new_height))
        new_image = ratiocrop.adjust(image, areas=areas)

        fit = Fit(width=new_width, height=new_height)
        return fit.adjust(new_image)

########NEW FILE########
__FILENAME__ = helpers
import datetime
import itertools
import ssl

from django.conf import settings
from django.core.files.images import ImageFile
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.template import Variable, VariableDoesNotExist, TemplateSyntaxError
from django.utils.datastructures import SortedDict
import six
from six.moves import http_client
try:
    from PIL import Image
except ImportError:
    import Image

from daguerre.adjustments import registry
from daguerre.models import Area, AdjustedImage
from daguerre.utils import make_hash, save_image, get_image_dimensions, KEEP_FORMATS, DEFAULT_FORMAT

# If any of the following errors appear during file manipulations, we will
# treat them as IOErrors.
# See http://code.larlet.fr/django-storages/issue/162/reraise-boto-httplib-errors-as-ioerrors
IOERRORS = (IOError, http_client.IncompleteRead, ssl.SSLError)

try:
    import boto.exception
except ImportError:
    pass
else:
    IOERRORS = IOERRORS + (boto.exception.BotoServerError,
                           boto.exception.S3ResponseError)


class AdjustmentInfoDict(dict):
    "A simple dict subclass for making image data more usable in templates."

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return six.text_type(self.get('url', ''))


class AdjustmentHelper(object):
    query_map = {
        'requested': 'r',
        'security': 's',
    }
    param_sep = '|'
    adjustment_sep = '>'

    def __init__(self, iterable, adjustments, lookup=None):
        adjustments = list(adjustments)
        if not adjustments:
            raise ValueError("At least one adjustment must be provided.")
        self.adjustments = adjustments
        self.adjust_uses_areas = any([getattr(adj.adjust, 'uses_areas', True)
                                      for adj in adjustments])
        self.calc_uses_areas = any([getattr(adj.calculate, 'uses_areas', True)
                                    for adj in adjustments])
        self.requested = self._serialize_requested(adjustments)

        self.iterable = list(iterable)
        self.lookup = lookup
        self.remaining = {}
        self.adjusted = {}

        if lookup is None:
            lookup_func = lambda obj, default=None: obj
        else:
            try:
                lookup_var = Variable("item.{0}".format(lookup))
            except TemplateSyntaxError:
                lookup_func = lambda *args, **kwargs: None
            else:
                def lookup_func(obj, default=None):
                    try:
                        return lookup_var.resolve({'item': obj})
                    except VariableDoesNotExist:
                        return default

        self.lookup_func = lookup_func

        for item in iterable:
            path = self.lookup_func(item, None)
            if isinstance(path, ImageFile):
                path = path.name
            # Skip empty paths (such as from an ImageFieldFile with no image.)
            if path and isinstance(path, six.string_types):
                self.remaining.setdefault(path, []).append(item)
            else:
                self.adjusted[item] = AdjustmentInfoDict()

    @classmethod
    def _serialize_requested(cls, adjustments):
        adj_strings = []
        for adj in adjustments:
            bits = [adj.__class__.__name__.lower()]
            bits += [str(adj.kwargs.get(key) or '')
                     for key in adj.parameters]
            adj_strings.append(cls.param_sep.join(bits))
        return cls.adjustment_sep.join(adj_strings)

    @classmethod
    def _deserialize_requested(cls, requested):
        adj_list = []
        for adj_string in requested.split(cls.adjustment_sep):
            bits = adj_string.split(cls.param_sep)
            adj_cls = registry[bits[0]]
            kwargs = {}
            for i, bit in enumerate(bits[1:]):
                kwargs[adj_cls.parameters[i]] = bit or None
            adj_list.append(adj_cls(**kwargs))
        return adj_list

    def get_query_kwargs(self):
        kwargs = {
            'requested': self.requested
        }
        if len(self.remaining) == 1:
            kwargs['storage_path'] = list(self.remaining.keys())[0]
        else:
            kwargs['storage_path__in'] = self.remaining
        return kwargs

    def get_areas(self, storage_path):
        if not hasattr(self, '_areas'):
            self._areas = {}
            areas = Area.objects.filter(storage_path__in=self.remaining)
            for area in areas:
                self._areas.setdefault(area.storage_path, []).append(area)
        return self._areas.get(storage_path, [])

    @classmethod
    def make_security_hash(cls, kwargs):
        kwargs = SortedDict(kwargs)
        kwargs.keyOrder.sort()
        args = list(itertools.chain(kwargs.keys(), kwargs.values()))
        return make_hash(settings.SECRET_KEY, step=2, *args)

    @classmethod
    def check_security_hash(cls, sec_hash, kwargs):
        return sec_hash == cls.make_security_hash(kwargs)

    def to_querydict(self, secure=False):
        qd = QueryDict('', mutable=True)
        kwargs = {
            'requested': self.requested
        }

        if secure:
            kwargs['security'] = self.make_security_hash(kwargs)

        for k, v in six.iteritems(kwargs):
            qd[self.query_map[k]] = v

        return qd

    @classmethod
    def from_querydict(cls, image_or_storage_path, querydict, secure=False):
        kwargs = SortedDict()
        for verbose, short in six.iteritems(cls.query_map):
            if short in querydict:
                kwargs[verbose] = querydict[short]

        if 'security' in kwargs:
            if not cls.check_security_hash(kwargs.pop('security'), kwargs):
                raise ValueError("Security check failed.")
        elif secure:
            raise ValueError("Security hash missing.")

        adjustments = cls._deserialize_requested(kwargs['requested'])
        return cls([image_or_storage_path], adjustments)

    def _adjusted_image_info_dict(self, adjusted_image):
        try:
            width, height = adjusted_image.adjusted._get_image_dimensions()
        except IOERRORS:
            return AdjustmentInfoDict()

        return AdjustmentInfoDict({
            'width': width,
            'height': height,
            'url': adjusted_image.adjusted.url,
        })

    def _path_info_dict(self, storage_path):
        try:
            with default_storage.open(storage_path, 'rb') as im_file:
                width, height = get_image_dimensions(im_file)
        except IOERRORS:
            return AdjustmentInfoDict()

        if self.calc_uses_areas:
            areas = self.get_areas(storage_path)
        else:
            areas = None

        for adjustment in self.adjustments:
            width, height = adjustment.calculate((width, height), areas=areas)

        url = u"{0}?{1}".format(
            reverse('daguerre_adjusted_image_redirect',
                    kwargs={'storage_path': storage_path}),
            self.to_querydict(secure=True).urlencode()
        )
        ajax_url = u"{0}?{1}".format(
            reverse('daguerre_ajax_adjustment_info',
                    kwargs={'storage_path': storage_path}),
            self.to_querydict(secure=False).urlencode()
        )
        return AdjustmentInfoDict({
            'width': width,
            'height': height,
            'url': url,
            'ajax_url': ajax_url,
        })

    def _fetch_adjusted(self):
        if self.remaining:
            query_kwargs = self.get_query_kwargs()
            adjusted_images = AdjustedImage.objects.filter(**query_kwargs
                                                           ).defer('requested')
            for adjusted_image in adjusted_images:
                path = adjusted_image.storage_path
                if path not in self.remaining:
                    continue
                info_dict = self._adjusted_image_info_dict(adjusted_image)
                for item in self.remaining[path]:
                    self.adjusted[item] = info_dict
                del self.remaining[path]

    def info_dicts(self):
        self._fetch_adjusted()

        # And then make adjustment dicts for any remaining paths.
        if self.remaining:
            for path, items in six.iteritems(self.remaining.copy()):
                info_dict = self._path_info_dict(path)
                for item in items:
                    self.adjusted[item] = info_dict
                del self.remaining[path]

        return [(item, self.adjusted[item]) for item in self.iterable]

    def adjust(self):
        self._fetch_adjusted()

        if self.remaining:
            for path, items in six.iteritems(self.remaining.copy()):
                try:
                    adjusted_image = self._adjust(path)
                except IOERRORS:
                    info_dict = AdjustmentInfoDict()
                else:
                    info_dict = self._adjusted_image_info_dict(adjusted_image)
                for item in items:
                    self.adjusted[item] = info_dict
                del self.remaining[path]

    def _adjust(self, storage_path):
        # May raise IOError if the file doesn't exist or isn't a valid image.

        # If we're here, we can assume that the adjustment doesn't already
        # exist. Try to create one from the storage path. Raises IOError if
        # something goes wrong.
        kwargs = {
            'requested': self.requested,
            'storage_path': storage_path
        }

        with default_storage.open(storage_path, 'rb') as im_file:
            im = Image.open(im_file)
            try:
                im.verify()
            except Exception:
                # Raise an IOError if the image isn't valid.
                raise IOError
            im_file.seek(0)
            im = Image.open(im_file)
            im.load()
        format = im.format if im.format in KEEP_FORMATS else DEFAULT_FORMAT

        if self.adjust_uses_areas:
            areas = self.get_areas(storage_path)
        else:
            areas = None

        for adjustment in self.adjustments:
            im = adjustment.adjust(im, areas=areas)

        adjusted = AdjustedImage(**kwargs)
        f = adjusted._meta.get_field('adjusted')

        args = (six.text_type(kwargs), datetime.datetime.now().isoformat())
        filename = '.'.join((make_hash(*args, step=2), format.lower()))
        storage_path = f.generate_filename(adjusted, filename)

        final_path = save_image(im, storage_path, format=format,
                                storage=default_storage)
        # Try to handle race conditions gracefully.
        try:
            adjusted = AdjustedImage.objects.filter(**kwargs
                                                    ).only('adjusted')[:1][0]
        except IndexError:
            adjusted.adjusted = final_path
            adjusted.save()
        else:
            default_storage.delete(final_path)
        return adjusted

########NEW FILE########
__FILENAME__ = daguerre
import os
import sys

from django.core.management import load_command_class, find_management_module
from django.core.management.base import BaseCommand
from django.utils.encoding import smart_str


NO_ARGS = """The daguerre management command requires a subcommand.

"""


class Command(BaseCommand):
    def _find_commands(self):
        command_dir = os.path.join(find_management_module('daguerre'),
                                   'commands')
        try:
            return dict((f[10:-3], f[:-3]) for f in os.listdir(command_dir)
                        if f.startswith('_daguerre_') and f.endswith('.py'))
        except OSError:
            return {}

    def _error(self, msg):
        sys.stderr.write(smart_str(self.style.ERROR(msg)))
        sys.exit(1)

    def _valid_commands(self):
        commands = self._find_commands()
        return "Valid daguerre subcommands are:\n\n{0}".format(
            "\n".join(commands)) + "\n\n"

    def _get_command(self, command, *args, **options):
        commands = self._find_commands()
        if command not in commands:
            self._error("Unknown command: {0}\n\n".format(command) +
                        self._valid_commands())
        return load_command_class('daguerre', commands[command])

    def run_from_argv(self, argv):
        if len(argv) < 3:
            self._error(NO_ARGS + self._valid_commands())
        command = self._get_command(argv[2])
        new_argv = [argv[0], "{0} {1}".format(*argv[1:3])] + argv[3:]
        command.run_from_argv(new_argv)

    def execute(self, *args, **options):
        if not args:
            self.stderr.write()
            self._error(NO_ARGS + self._valid_commands())
        command = self._get_command(args[0])
        command.execute(*args[1:], **options)

########NEW FILE########
__FILENAME__ = _daguerre_clean
from __future__ import absolute_import
import os

from django.core.files.storage import default_storage
from django.core.management.base import NoArgsCommand
from django.db import models
from django.template.defaultfilters import pluralize
import six

from daguerre.helpers import IOERRORS
from daguerre.models import AdjustedImage, Area


class Command(NoArgsCommand):
    def _delete_queryset(
            self,
            queryset,
            reason='reference nonexistant paths',
            reason_plural=None):
        count = queryset.count()
        if count == 1:
            name = six.text_type(queryset.model._meta.verbose_name)
            reason = reason
        else:
            name = six.text_type(queryset.model._meta.verbose_name_plural)
            reason = reason_plural or reason
        if count == 0:
            self.stdout.write(u"No {0} {1}.\n".format(name, reason))
        else:
            self.stdout.write(u"Deleting {0} {1} which {2}... ".format(
                count, name, reason))
            self.stdout.flush()
            queryset.delete()
            self.stdout.write("Done.\n")

    def _walk(self, dirpath, topdown=True):
        """
        Recursively walks the dir with default_storage.
        Yields (dirpath, dirnames, filenames) tuples.
        """
        try:
            dirnames, filenames = default_storage.listdir(dirpath)
        except (NotImplementedError, OSError):
            # default_storage can't listdir, or dir doesn't exist
            # (local filesystem.)
            dirnames, filenames = [], []

        if topdown:
            yield dirpath, dirnames, filenames

        for dirname in dirnames:
            for value in self._walk(os.path.join(dirpath, dirname), topdown):
                yield value

        if not topdown:
            yield dirpath, dirnames, filenames

    def _old_adjustments(self):
        """
        Returns a queryset of AdjustedImages whose storage_paths no longer
        exist in storage.

        """
        paths = AdjustedImage.objects.values_list(
            'storage_path', flat=True).distinct()
        missing = [
            path for path in paths
            if not default_storage.exists(path)
        ]
        return AdjustedImage.objects.filter(storage_path__in=missing)

    def _old_areas(self):
        """
        Returns a queryset of Areas whose storage_paths no longer exist in
        storage.

        """
        paths = Area.objects.values_list(
            'storage_path', flat=True).distinct()
        missing = [
            path for path in paths
            if not default_storage.exists(path)
        ]
        return Area.objects.filter(storage_path__in=missing)

    def _missing_adjustments(self):
        """
        Returns a queryset of AdjustedImages whose adjusted image files no
        longer exist in storage.

        """
        paths = AdjustedImage.objects.values_list(
            'adjusted', flat=True).distinct()
        missing = [
            path for path in paths
            if not default_storage.exists(path)
        ]
        return AdjustedImage.objects.filter(adjusted__in=missing)

    def _duplicate_adjustments(self):
        """
        Returns a queryset of AdjustedImages which are duplicates - i.e. have
        the same requested adjustment and storage path as another
        AdjustedImage. This excludes one adjusted image as the canonical
        version.

        """
        fields = (
            'storage_path',
            'requested'
        )
        kwargs_list = AdjustedImage.objects.values(
            *fields).annotate(
                count=models.Count('id')).filter(
                    count__gt=1).values(
                        *fields)
        duplicate_pks = []
        for kwargs in kwargs_list:
            pks = AdjustedImage.objects.filter(
                **kwargs).values_list('pk', flat=True)
            duplicate_pks.extend(list(pks)[1:])
        return AdjustedImage.objects.filter(pk__in=duplicate_pks)

    def _orphaned_files(self):
        """
        Returns a list of files which aren't referenced by any adjusted images
        in the database.

        """
        known_paths = set(
            AdjustedImage.objects.values_list('adjusted', flat=True).distinct()
        )
        orphans = []
        for dirpath, dirnames, filenames in self._walk(
                'daguerre', topdown=False):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if filepath not in known_paths:
                    orphans.append(filepath)
        return orphans

    def handle_noargs(self, **options):
        # Clear all adjusted images that reference nonexistant
        # storage paths.
        self._delete_queryset(self._old_adjustments())

        # Clear all areas that reference nonexistant storage paths.
        self._delete_queryset(self._old_areas())

        # Clear all adjusted images that reference nonexistant adjustments.
        self._delete_queryset(self._missing_adjustments(),
                              'reference missing adjustments')

        # Clear all duplicate adjusted images.
        self._delete_queryset(self._duplicate_adjustments(),
                              reason='is a duplicate',
                              reason_plural='are duplicates')

        # Clean up files that aren't referenced by any adjusted images.
        orphans = self._orphaned_files()
        if not orphans:
            self.stdout.write("No orphaned files found.\n")
        else:
            self.stdout.write(
                "Deleting {0} orphaned file{1}... ".format(
                    len(orphans),
                    pluralize(len(orphans))))
            self.stdout.flush()
            for filepath in orphans:
                try:
                    default_storage.delete(filepath)
                except IOERRORS:
                    pass
            self.stdout.write("Done.\n")

        self.stdout.write("\n")

########NEW FILE########
__FILENAME__ = _daguerre_preadjust
from __future__ import absolute_import

from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError
from django.db.models import Model, get_model
from django.db.models.query import QuerySet
from django.template.defaultfilters import pluralize
import six

from daguerre.models import AdjustedImage
from daguerre.helpers import AdjustmentHelper


NO_ADJUSTMENTS = """No adjustments were defined.
You'll need to add a DAGUERRE_PREADJUSTMENTS setting.
See the django-daguerre documentation for more details.
"""

BAD_STRUCTURE = """DAGUERRE_PREADJUSTMENTS should be an iterable of
tuples, where each tuple contains three items:

1. "<applabel>.<model>", a model class, a queryset, or any iterable.
2. A non-empty iterable of adjustment instances to be applied to each image.
3. A template-style lookup (or None).

See the django-daguerre documentation for more details.

"""


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option(
            '--remove',
            action='store_true',
            dest='remove',
            default=False,
            help="Remove all adjustments that aren't "
                 "listed in DAGUERRE_PREADJUSTMENTS",
        ),
        make_option(
            '--nocreate',
            action='store_true',
            dest='nocreate',
            default=False,
            help="Don't create any new adjustments."
        ),
    )

    def _get_helpers(self):
        if not hasattr(settings, 'DAGUERRE_PREADJUSTMENTS'):
            raise CommandError(NO_ADJUSTMENTS)
        dp = settings.DAGUERRE_PREADJUSTMENTS
        helpers = []
        try:
            for (model_or_iterable, adjustments, lookup) in dp:
                if isinstance(model_or_iterable, six.string_types):
                    app_label, model_name = model_or_iterable.split('.')
                    model_or_iterable = get_model(app_label, model_name)
                if (isinstance(model_or_iterable, six.class_types) and
                        issubclass(model_or_iterable, Model)):
                    iterable = model_or_iterable.objects.all()
                elif isinstance(model_or_iterable, QuerySet):
                    iterable = model_or_iterable._clone()
                else:
                    iterable = model_or_iterable

                helpers.append(
                    AdjustmentHelper(iterable, adjustments, lookup))
        except (ValueError, TypeError, LookupError):
            raise CommandError(BAD_STRUCTURE)

        return helpers

    def _preadjust(self):
        empty_count = 0
        skipped_count = 0
        remaining_count = 0
        helpers = self._get_helpers()
        for helper in helpers:
            helper.empty_count = len(helper.adjusted)
            empty_count += helper.empty_count
            helper._fetch_adjusted()
            skipped_count += len(helper.adjusted) - helper.empty_count
            remaining_count += len(helper.remaining)

        self.stdout.write(
            "Skipped {0} empty path{1}.\n".format(
                empty_count,
                pluralize(skipped_count)))

        self.stdout.write(
            "Skipped {0} path{1} which have already been adjusted.\n".format(
                skipped_count,
                pluralize(skipped_count)))

        if remaining_count == 0:
            self.stdout.write("No paths remaining to adjust.\n")
        else:
            self.stdout.write("Adjusting {0} path{1}... ".format(
                remaining_count,
                pluralize(remaining_count)))
            self.stdout.flush()

            failed_count = 0
            for helper in helpers:
                helper.adjust()
                empty_count = len([info_dict
                                   for info_dict in helper.adjusted.values()
                                   if not info_dict])
                failed_count += empty_count - helper.empty_count
            self.stdout.write("Done.\n")
            if failed_count:
                self.stdout.write(
                    "{0} path{1} failed due to I/O errors.".format(
                        failed_count,
                        pluralize(failed_count)))

    def _prune(self):
        queryset = AdjustedImage.objects.all()
        helpers = self._get_helpers()
        for helper in helpers:
            query_kwargs = helper.get_query_kwargs()
            queryset = queryset.exclude(**query_kwargs)

        count = queryset.count()
        if count == 0:
            self.stdout.write("No adjusted images found to remove.\n")
        else:
            self.stdout.write("Removing {0} adjusted image{1}... ".format(
                count,
                pluralize(count)))
            self.stdout.flush()
            queryset.delete()
            self.stdout.write("Done.\n")

    def handle_noargs(self, **options):
        if options['nocreate'] and not options['remove']:
            self.stdout.write("Doing nothing.\n")

        if not options['nocreate']:
            self._preadjust()

        if options['remove']:
            self._prune()

        # For pre-1.5: add an extra newline.
        self.stdout.write("\n")

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf8
from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdjustedImage',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('storage_path', models.CharField(max_length=200)),
                ('adjusted', models.ImageField(upload_to='daguerre/%Y/%m/%d/')),
                ('requested', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                (u'id', models.AutoField(verbose_name=u'ID', serialize=False, auto_created=True, primary_key=True)),
                ('storage_path', models.CharField(max_length=300)),
                ('x1', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('y1', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('x2', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('y2', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('name', models.CharField(max_length=20, blank=True)),
                ('priority', models.PositiveIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)])),
            ],
            options={
                u'ordering': ('priority',),
            },
            bases=(models.Model,),
        ),
    ]

########NEW FILE########
__FILENAME__ = models
import operator

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from six.moves import reduce

from daguerre.adjustments import registry


class Area(models.Model):
    """
    Represents an area of an image. Can be used to specify a crop. Also used
    for priority-aware automated image cropping.

    """
    storage_path = models.CharField(max_length=300)

    x1 = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    y1 = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    x2 = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    y2 = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    name = models.CharField(max_length=20, blank=True)
    priority = models.PositiveIntegerField(validators=[MinValueValidator(1)],
                                           default=3)

    @property
    def area(self):
        if None in (self.x1, self.y1, self.x2, self.y2):
            return None
        return self.width * self.height

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def clean_fields(self, exclude=None):
        errors = {}

        if exclude is None:
            exclude = []

        try:
            super(Area, self).clean_fields(exclude)
        except ValidationError as e:
            errors.update(e.message_dict)

        if errors:
            raise ValidationError(errors)

    def clean(self):
        errors = []
        if self.x1 and self.x2 and self.x1 >= self.x2:
            errors.append("X1 must be less than X2.")
        if self.y1 and self.y2 and self.y1 >= self.y2:
            errors.append("Y1 must be less than Y2.")
        if errors:
            raise ValidationError(errors)

    def serialize(self):
        return dict((f.name, getattr(self, f.name))
                    for f in self._meta.fields)

    def __unicode__(self):
        if self.name:
            name = self.name
        else:
            name = u"(%d, %d, %d, %d / %d)" % (self.x1, self.y1, self.x2,
                                               self.y2, self.priority)
        return u"%s for %s" % (name, self.storage_path)

    class Meta:
        ordering = ('priority',)


@receiver(post_save, sender=Area)
@receiver(post_delete, sender=Area)
def delete_adjusted_images(sender, **kwargs):
    """
    If an Area is deleted or changed, delete all AdjustedImages for the
    Area's storage_path which have area-using adjustments.

    """
    storage_path = kwargs['instance'].storage_path
    qs = AdjustedImage.objects.filter(storage_path=storage_path)
    slug_qs = [models.Q(requested__contains=slug)
               for slug, adjustment in registry.items()
               if getattr(adjustment.adjust, 'uses_areas', True)]
    if slug_qs:
        qs = qs.filter(reduce(operator.or_, slug_qs))

    qs.delete()


class AdjustedImage(models.Model):
    """Represents a managed image adjustment."""
    storage_path = models.CharField(max_length=200)
    # The image name is a 20-character hash, so the max length with a 4-char
    # extension (jpeg) is 45.
    adjusted = models.ImageField(upload_to='daguerre/%Y/%m/%d/',
                                 max_length=45)

    requested = models.CharField(max_length=100)

    def __unicode__(self):
        return u"{0}: {1}".format(self.storage_path, self.requested)

########NEW FILE########
__FILENAME__ = daguerre
from __future__ import absolute_import
import re

from django import template
from django.conf import settings
from django.template.defaultfilters import escape
import six

from daguerre.adjustments import registry
from daguerre.helpers import AdjustmentHelper, AdjustmentInfoDict


register = template.Library()
kwarg_re = re.compile("(\w+)=(.+)")


class AdjustmentNode(template.Node):
    def __init__(self, image, adjustments, asvar=None):
        self.image = image
        self.adjustments = adjustments
        self.asvar = asvar

    def render(self, context):
        image = self.image.resolve(context)

        adj_instances = []
        for adj_to_resolve, kwargs_to_resolve in self.adjustments:
            adj = adj_to_resolve.resolve(context)
            kwargs = dict((k, v.resolve(context))
                          for k, v in six.iteritems(kwargs_to_resolve))
            try:
                adj_cls = registry[adj]
                adj_instances.append(adj_cls(**kwargs))
            except (KeyError, ValueError):
                if settings.TEMPLATE_DEBUG:
                    raise
                if self.asvar is not None:
                    context[self.asvar] = AdjustmentInfoDict()
                return ''

        helper = AdjustmentHelper([image], adj_instances)
        info_dict = helper.info_dicts()[0][1]

        if self.asvar is not None:
            context[self.asvar] = info_dict
            return ''
        return escape(info_dict.get('url', ''))


class BulkAdjustmentNode(template.Node):
    def __init__(self, iterable, adjustments, asvar):
        self.iterable = iterable
        self.adjustments = adjustments
        self.asvar = asvar

    def render(self, context):
        iterable = self.iterable.resolve(context)

        adj_list = []
        for adj, kwargs in self.adjustments:
            adj_list.append((adj.resolve(context),
                             dict((k, v.resolve(context))
                             for k, v in six.iteritems(kwargs))))

        # First adjustment *might* be a lookup.
        # We consider it a lookup if it is not an adjustment name.
        if adj_list and adj_list[0][0] in registry:
            lookup = None
        else:
            lookup = adj_list[0][0]
            adj_list = adj_list[1:]

        adj_instances = []
        for adj, kwargs in adj_list:
            try:
                adj_cls = registry[adj]
                adj_instances.append(adj_cls(**kwargs))
            except (KeyError, ValueError):
                if settings.TEMPLATE_DEBUG:
                    raise
                context[self.asvar] = []
                return ''

        helper = AdjustmentHelper(iterable, adj_instances, lookup)
        context[self.asvar] = helper.info_dicts()
        return ''


def _get_adjustments(parser, tag_name, bits):
    """Helper function to get adjustment defs from a list of bits."""
    adjustments = []
    current_kwargs = None

    for bit in bits:
        match = kwarg_re.match(bit)
        if not match:
            current_kwargs = {}
            adjustments.append((parser.compile_filter(bit), current_kwargs))
        else:
            if current_kwargs is None:
                raise template.TemplateSyntaxError(
                    "Malformed arguments to `%s` tag" % tag_name)
            key, value = match.groups()
            current_kwargs[str(key)] = parser.compile_filter(value)

    return adjustments


@register.tag
def adjust(parser, token):
    """
    Returns a url to the adjusted image, or (with ``as``) stores a dictionary
    in the context with ``width``, ``height``, and ``url`` keys for the
    adjusted image.

    Syntax::

        {% adjust <image> <adj> <key>=<val> ... <adj> <key>=<val> [as <varname>] %}

    ``<image>`` should resolve to an image file (like you would get as an
    ImageField's value) or a direct storage path for an image.

    Each ``<adj>`` should resolve to a string which corresponds to a
    registered adjustment. The key/value pairs following each ``<adj>`` will
    be passed into it on instantiation. If no matching adjustment is
    registered or the arguments are invalid, the adjustment will fail.

    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            '"{0}" template tag requires at'
            ' least two arguments'.format(tag_name))

    image = parser.compile_filter(bits[1])
    bits = bits[2:]
    asvar = None

    if len(bits) > 1:
        if bits[-2] == 'as':
            asvar = bits[-1]
            bits = bits[:-2]

    return AdjustmentNode(
        image,
        _get_adjustments(parser, tag_name, bits),
        asvar=asvar)


@register.tag
def adjust_bulk(parser, token):
    """
    Stores a variable in the context mapping items from the iterable
    with adjusted images for those items.

    Syntax::

        {% adjust_bulk <iterable> [<lookup>] <adj> <key>=<val> ... as varname %}

    The keyword arguments have the same meaning as for :ttag:`{% adjust %}`.

    ``<lookup>`` is a string with the same format as a template variable (for
    example, ``"get_profile.image"``). The lookup will be performed on each
    item in the ``iterable`` to get the image or path which will be adjusted.

    Each ``<adj>`` should resolve to a string which corresponds to a
    registered adjustment. The key/value pairs following each ``<adj>`` will
    be passed into it on instantiation. If no matching adjustment is
    registered or the arguments are invalid, the adjustment will fail.

    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) < 4:
        raise template.TemplateSyntaxError(
            '"{0}" template tag requires at'
            ' least four arguments'.format(tag_name))

    if bits[-2] != 'as':
        raise template.TemplateSyntaxError(
            'The second to last argument to'
            ' {0} must be "as".'.format(tag_name))

    iterable = parser.compile_filter(bits[1])
    asvar = bits[-1]
    adjustments = _get_adjustments(parser, tag_name, bits[2:-2])

    return BulkAdjustmentNode(iterable, adjustments, asvar)

########NEW FILE########
__FILENAME__ = base
import os

from django.contrib.auth.models import User, Permission
from django.test import TestCase
try:
    from PIL import ImageChops, Image
except ImportError:
    import Image
    import ImageChops

import daguerre
from daguerre.models import Area
from daguerre.utils import save_image


TEST_DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(daguerre.__file__), 'tests', 'data')
)


class BaseTestCase(TestCase):
    @classmethod
    def _data_path(cls, test_path):
        """Given a path relative to daguerre/tests/data/,
        returns an absolute path."""
        return os.path.join(TEST_DATA_DIR, test_path)

    @classmethod
    def _data_file(cls, test_path, mode='r'):
        """Given a path relative to daguerre/tests/data/,
        returns an open file."""
        return open(cls._data_path(test_path), mode)

    def assertImageEqual(self, im1, im2):
        # First check that they're the same size. A difference
        # comparison could pass for images of different sizes.
        self.assertEqual(im1.size, im2.size)
        # Image comparisons according to
        # http://effbot.org/zone/pil-comparing-images.htm
        self.assertTrue(ImageChops.difference(im1, im2).getbbox() is None)

    def create_image(self, test_path):
        image = Image.open(self._data_path(test_path))
        return save_image(image, 'daguerre/test/{0}'.format(test_path))

    def create_area(
            self,
            test_path='100x100.png',
            x1=0,
            y1=0,
            x2=100,
            y2=100,
            **kwargs):
        if 'storage_path' not in kwargs:
            kwargs['storage_path'] = self.create_image(test_path)
        kwargs.update({
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2
        })
        return Area.objects.create(**kwargs)

    def create_user(
            self,
            username='test',
            password='test',
            permissions=None,
            **kwargs):
        user = User(username=username, **kwargs)
        user.set_password(password)
        user.save()

        if permissions:
            for permission in permissions:
                app_label, codename = permission.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename)
                user.user_permissions.add(permission)

        return user

########NEW FILE########
__FILENAME__ = test_adjustments
from daguerre.adjustments import Crop
from daguerre.helpers import AdjustmentHelper
from daguerre.tests.base import BaseTestCase


class RequestResponseTestCase(BaseTestCase):
    def test_unprepped(self):
        image = self.create_image('100x100.png')

        crop = Crop(width=50, height=50)

        with self.assertNumQueries(1):
            info_dict = AdjustmentHelper([image], [crop]).info_dicts()[0][1]
        with self.assertNumQueries(4):
            response = self.client.get(info_dict['url'])
        self.assertEqual(response.status_code, 302)

    def test_prepped(self):
        image = self.create_image('100x100.png')

        crop = Crop(width=50, height=50)

        with self.assertNumQueries(1):
            info_dict = AdjustmentHelper([image], [crop]).info_dicts()[0][1]
        with self.assertNumQueries(4):
            AdjustmentHelper([image], [crop]).adjust()
        with self.assertNumQueries(1):
            response = self.client.get(info_dict['url'])
        self.assertEqual(response.status_code, 302)

    def test_preprepped(self):
        image = self.create_image('100x100.png')

        crop = Crop(width=50, height=50)

        helper = AdjustmentHelper([image], [crop])
        with self.assertNumQueries(4):
            helper.adjust()
        adjusted = list(helper.adjusted.values())[0]

        with self.assertNumQueries(1):
            info_dict = AdjustmentHelper([image], [crop]
                                         ).info_dicts()[0][1]
        self.assertEqual(info_dict['url'], adjusted['url'])

########NEW FILE########
__FILENAME__ = test_templatetags
from django.template import Template, Context
from django.utils.html import escape

from daguerre.adjustments import Fit, Crop
from daguerre.helpers import AdjustmentHelper
from daguerre.models import AdjustedImage
from daguerre.tests.base import BaseTestCase


class AdjustTemplatetagTestCase(BaseTestCase):
    def test_path(self):
        # Tag should accept a path as its argument.
        storage_path = self.create_image('100x100.png')
        helper = AdjustmentHelper([storage_path], [Fit(width=50, height=50)])
        t = Template("{% load daguerre %}{% adjust image 'fit' width=50 "
                     "height=50 %}")
        c = Context({'image': storage_path})
        self.assertEqual(t.render(c), escape(helper.info_dicts()[0][1]['url']))

    def test_file(self):
        # Tag should accept an :class:`ImageFieldFile` as its argument.
        storage_path = self.create_image('100x100.png')
        adjusted = AdjustedImage()
        adjusted.adjusted = storage_path
        helper = AdjustmentHelper([storage_path], [Fit(width=50, height=50)])
        t = Template("{% load daguerre %}{% adjust image 'fit' width=50 "
                     "height=50 as adj %}{{ adj }}")
        c = Context({'image': adjusted.adjusted})
        self.assertEqual(t.render(c), escape(helper.info_dicts()[0][1]['url']))

    def test_invalid(self):
        t = Template("{% load daguerre %}{% adjust image 'fit' width=50 "
                     "height=50 %}")
        c = Context({'image': 23})
        self.assertEqual(t.render(c), '')

    def test_multiple(self):
        # Tag should allow multiple adjustments to be passed in.
        storage_path = self.create_image('100x100.png')
        helper = AdjustmentHelper([storage_path], [Crop(width=50, height=50),
                                                   Fit(width=25)])
        t = Template("{% load daguerre %}{% adjust image 'crop' width=50 "
                     "height=50 'fit' width=25 %}")
        c = Context({'image': storage_path})
        self.assertEqual(t.render(c), escape(helper.info_dicts()[0][1]['url']))


class BulkTestObject(object):
    def __init__(self, storage_path):
        self.storage_path = storage_path


class AdjustBulkTemplatetagTestCase(BaseTestCase):
    def test_paths(self):
        # Tag should accept an iterable of objects with paths.
        objs = [
            BulkTestObject(self.create_image('100x100.png'))
        ]
        helper = AdjustmentHelper(objs, [Fit(width=50, height=50)],
                                  'storage_path')
        t = Template("{% load daguerre %}{% adjust_bulk objs 'storage_path' "
                     "'fit' width=50 height=50 as bulk %}"
                     "{{ bulk.0.1 }}")
        c = Context({'objs': objs})
        self.assertEqual(t.render(c),
                         escape(helper.info_dicts()[0][1]['url']))

    def test_multiple(self):
        # Tag should accept multiple adjustments.
        objs = [
            BulkTestObject(self.create_image('100x100.png'))
        ]
        helper = AdjustmentHelper(objs,
                                  [Crop(width=50, height=50),
                                   Fit(width=25)],
                                  'storage_path')
        t = Template("{% load daguerre %}{% adjust_bulk objs 'storage_path' "
                     "'crop' width=50 height=50 'fit' width=25 as bulk %}"
                     "{{ bulk.0.1 }}")
        c = Context({'objs': objs})
        self.assertEqual(t.render(c),
                         escape(helper.info_dicts()[0][1]['url']))

    def test_no_lookups(self):
        # Tag should accept an iterable of paths.
        paths = [
            self.create_image('100x100.png')
        ]
        helper = AdjustmentHelper(paths,
                                  [Fit(width=50, height=50)])
        t = Template("{% load daguerre %}{% adjust_bulk paths 'fit' "
                     "width=50 height=50 as bulk %}{{ bulk.0.1 }}")
        c = Context({'paths': paths})
        self.assertEqual(t.render(c),
                         escape(helper.info_dicts()[0][1]['url']))

########NEW FILE########
__FILENAME__ = test_adjustments
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
try:
    from PIL import Image
except ImportError:
    import Image

from daguerre.adjustments import Fit, Crop, Fill, NamedCrop
from daguerre.helpers import AdjustmentHelper
from daguerre.models import AdjustedImage, Area
from daguerre.tests.base import BaseTestCase


class FitTestCase(BaseTestCase):
    def test_calculate__both(self):
        fit = Fit(width=50, height=50)
        self.assertEqual(fit.calculate((100, 100)), (50, 50))

    def test_calculate__width(self):
        fit = Fit(width=50)
        self.assertEqual(fit.calculate((100, 100)), (50, 50))

    def test_calculate__height(self):
        fit = Fit(height=50)
        self.assertEqual(fit.calculate((100, 100)), (50, 50))

    def test_calculate__smallest(self):
        fit = Fit(width=60, height=50)
        self.assertEqual(fit.calculate((100, 100)), (50, 50))

    def test_adjust__both(self):
        im = Image.open(self._data_path('100x100.png'))
        fit = Fit(width=50, height=50)
        adjusted = fit.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__width(self):
        im = Image.open(self._data_path('100x100.png'))
        fit = Fit(width=50)
        adjusted = fit.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__height(self):
        im = Image.open(self._data_path('100x100.png'))
        fit = Fit(height=50)
        adjusted = fit.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__smallest(self):
        im = Image.open(self._data_path('100x100.png'))
        fit = Fit(width=60, height=50)
        adjusted = fit.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)


class CropTestCase(BaseTestCase):
    def test_calculate__both(self):
        crop = Crop(width=50, height=50)
        self.assertEqual(crop.calculate((100, 100)), (50, 50))

    def test_calculate__width(self):
        crop = Crop(width=50)
        self.assertEqual(crop.calculate((100, 100)), (50, 100))

    def test_calculate__height(self):
        crop = Crop(height=50)
        self.assertEqual(crop.calculate((100, 100)), (100, 50))

    def test_adjust__both(self):
        im = Image.open(self._data_path('100x100.png'))
        crop = Crop(width=50, height=50)
        adjusted = crop.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_crop.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__width(self):
        im = Image.open(self._data_path('100x100.png'))
        crop = Crop(width=50)
        adjusted = crop.adjust(im)
        self.assertEqual(adjusted.size, (50, 100))
        expected = Image.open(self._data_path('50x100_crop.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__height(self):
        im = Image.open(self._data_path('100x100.png'))
        crop = Crop(height=50)
        adjusted = crop.adjust(im)
        self.assertEqual(adjusted.size, (100, 50))
        expected = Image.open(self._data_path('100x50_crop.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__area(self):
        im = Image.open(self._data_path('100x100.png'))
        crop = Crop(width=50, height=50)
        areas = [Area(x1=21, y1=46, x2=70, y2=95)]
        adjusted = crop.adjust(im, areas=areas)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_crop_area.png'))
        self.assertImageEqual(adjusted, expected)


class FillTestCase(BaseTestCase):
    def test_calculate__both(self):
        fill = Fill(width=50, height=50)
        self.assertEqual(fill.calculate((100, 100)), (50, 50))

    def test_calculate__unequal(self):
        fill = Fill(width=50, height=40)
        self.assertEqual(fill.calculate((100, 100)), (50, 40))

    def test_calculate__width(self):
        fill = Fill(width=50)
        self.assertEqual(fill.calculate((100, 100)), (50, 50))

    def test_calculate__height(self):
        fill = Fill(height=50)
        self.assertEqual(fill.calculate((100, 100)), (50, 50))

    def test_calculate__max_height(self):
        fill = Fill(width=50, max_height=200)
        self.assertEqual(fill.calculate((100, 100)), (50, 50))

    def test_calculate__max_width(self):
        fill = Fill(height=50, max_width=200)
        self.assertEqual(fill.calculate((100, 100)), (50, 50))

    def test_calculate__max_height__smaller(self):
        fill = Fill(width=100, max_height=50)
        self.assertEqual(fill.calculate((100, 100)), (100, 50))

    def test_calculate__max_width__smaller(self):
        fill = Fill(height=100, max_width=50)
        self.assertEqual(fill.calculate((100, 100)), (50, 100))

    def test_calculate__strings(self):
        fill = Fill(height='100', max_width='50')
        self.assertEqual(fill.calculate((100, 100)), (50, 100))

    def test_adjust__both(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(width=50, height=50)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__width(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(width=50)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__height(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(height=50)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__max_height(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(width=50, max_height=200)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__max_width(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(height=50, max_width=200)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 50))
        expected = Image.open(self._data_path('50x50_fit.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__unequal(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(width=50, height=40)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 40))
        expected = Image.open(self._data_path('50x40_fill.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__max_height__smaller(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(width=100, max_height=50)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (100, 50))
        expected = Image.open(self._data_path('100x50_crop.png'))
        self.assertImageEqual(adjusted, expected)

    def test_adjust__max_width__smaller(self):
        im = Image.open(self._data_path('100x100.png'))
        fill = Fill(height=100, max_width=50)
        adjusted = fill.adjust(im)
        self.assertEqual(adjusted.size, (50, 100))
        expected = Image.open(self._data_path('50x100_crop.png'))
        self.assertImageEqual(adjusted, expected)


class AdjustmentHelperTestCase(BaseTestCase):
    def setUp(self):
        self.base_image = self.create_image('100x100.png')
        super(AdjustmentHelperTestCase, self).setUp()

    def test_adjust_crop__50x100(self):
        expected = Image.open(self._data_path('50x100_crop.png'))
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [Crop(width=50, height=100)]
                             ).adjust()
        adjusted = AdjustedImage.objects.get()
        self.assertImageEqual(Image.open(adjusted.adjusted.path), expected)
        # Make sure that the path is properly formatted.
        self.assertTrue(adjusted.adjusted.path.endswith('.png'))

    def test_adjust_crop__100x50(self):
        expected = Image.open(self._data_path('100x50_crop.png'))
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [Crop(width=100, height=50)]
                             ).adjust()
        adjusted = AdjustedImage.objects.get()
        self.assertImageEqual(Image.open(adjusted.adjusted.path), expected)

    def test_adjust_crop__50x50_area(self):
        self.create_area(storage_path=self.base_image, x1=21, x2=70, y1=46,
                         y2=95)
        expected = Image.open(self._data_path('50x50_crop_area.png'))
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [Crop(width=50, height=50)]
                             ).adjust()
        adjusted = AdjustedImage.objects.get()
        self.assertImageEqual(Image.open(adjusted.adjusted.path), expected)

    def test_named_crop(self):
        self.create_area(storage_path=self.base_image, x1=21, x2=70, y1=46,
                         y2=95, name='area')
        expected = Image.open(self._data_path('25x25_fit_named_crop.png'))
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [NamedCrop(name='area'),
                              Fit(width=25, height=25)]
                             ).adjust()
        adjusted = AdjustedImage.objects.get()
        self.assertImageEqual(Image.open(adjusted.adjusted.path), expected)

    def test_readjust(self):
        """
        Adjusting a previously-adjusted image should return the previous
        adjustment.

        """
        new_im = Image.open(self._data_path('50x100_crop.png'))
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [Crop(width=50, height=100)]
                             ).adjust()
        adjusted = AdjustedImage.objects.get()
        self.assertImageEqual(Image.open(adjusted.adjusted.path), new_im)

        with self.assertNumQueries(1):
            AdjustmentHelper([self.base_image],
                             [Crop(width=50, height=100)]
                             ).adjust()
        self.assertEqual(AdjustedImage.objects.count(), 1)

    def test_readjust_multiple(self):
        """
        If there are multiple adjusted versions of the image with the same
        parameters, one of them should be returned rather than erroring out.

        """
        with self.assertNumQueries(4):
            AdjustmentHelper([self.base_image],
                             [Crop(width=50, height=100)]
                             ).adjust()
        adjusted1 = AdjustedImage.objects.get()
        adjusted2 = AdjustedImage.objects.get()
        adjusted2.pk = None
        adjusted2.save()
        self.assertNotEqual(adjusted1.pk, adjusted2.pk)

        helper = AdjustmentHelper([self.base_image],
                                  [Crop(width=50, height=100)])
        with self.assertNumQueries(1):
            helper.adjust()
        url = list(helper.adjusted.values())[0]['url']
        self.assertEqual(url, adjusted1.adjusted.url)
        self.assertEqual(url, adjusted2.adjusted.url)

    def test_adjust__nonexistant(self):
        """
        Adjusting a path that doesn't exist should raise an IOError.

        """
        storage_path = 'nonexistant.png'
        self.assertFalse(default_storage.exists(storage_path))
        helper = AdjustmentHelper([storage_path], [Fit(width=50, height=50)])
        # We still do get one query because the first try is always for
        # an AdjustedImage, whether or not the original file exists.
        # This is for historic reasons and doesn't necessarily need to
        # continue to be the case.
        with self.assertNumQueries(1):
            helper.adjust()
        self.assertEqual(helper.adjusted, {helper.iterable[0]: {}})
        self.assertEqual(helper.remaining, {})

    def test_adjust__broken(self):
        broken_file = self._data_file('broken.png', 'rb')
        storage_path = default_storage.save('daguerre/test/broken.png',
                                            ContentFile(broken_file.read()))
        broken_file = default_storage.open(storage_path, 'rb')
        image = Image.open(broken_file)
        self.assertRaises(IndexError, image.verify)

        helper = AdjustmentHelper([storage_path],
                                  [Fill(width=50, height=50)])
        with self.assertNumQueries(1):
            helper.adjust()
        self.assertEqual(helper.adjusted, {helper.iterable[0]: {}})
        self.assertEqual(helper.remaining, {})

    def test_serialize(self):
        adjustments = [Fit(width=25, height=50), Crop(width=25)]
        requested = AdjustmentHelper._serialize_requested(adjustments)
        self.assertEqual(requested, 'fit|25|50>crop|25|')

    def test_deserialize(self):
        requested = 'fit|25|50>crop|25|'
        fit, crop = AdjustmentHelper._deserialize_requested(requested)
        self.assertIsInstance(fit, Fit)
        self.assertEqual(fit.kwargs, {'width': '25', 'height': '50'})
        self.assertIsInstance(crop, Crop)
        self.assertEqual(crop.kwargs, {'width': '25', 'height': None})


class BulkTestObject(object):
    def __init__(self, storage_path):
        self.storage_path = storage_path


class BulkAdjustmentHelperTestCase(BaseTestCase):
    def test_info_dicts__non_bulk(self):
        images = [
            self.create_image('100x100.png'),
            self.create_image('100x100.png'),
            self.create_image('100x50_crop.png'),
            self.create_image('50x100_crop.png'),
        ]

        adj = Crop(width=50, height=50)
        with self.assertNumQueries(4):
            for image in images:
                AdjustmentHelper([image], [adj]).info_dicts()

    def test_info_dicts__unprepped(self):
        images = [
            self.create_image('100x100.png'),
            self.create_image('100x100.png'),
            self.create_image('100x50_crop.png'),
            self.create_image('50x100_crop.png'),
        ]
        iterable = [BulkTestObject(image) for image in images]

        adj = Crop(width=50, height=50)

        helper = AdjustmentHelper(iterable, [adj], 'storage_path')
        with self.assertNumQueries(1):
            helper.info_dicts()

    def test_info_dicts__semiprepped(self):
        images = [
            self.create_image('100x100.png'),
            self.create_image('100x100.png'),
            self.create_image('100x50_crop.png'),
            self.create_image('50x100_crop.png'),
        ]
        iterable = [BulkTestObject(image) for image in images]

        adj = Crop(width=50, height=50)

        helper = AdjustmentHelper(iterable, [adj], 'storage_path')
        with self.assertNumQueries(1):
            helper.info_dicts()

    def test_info_dicts__prepped(self):
        images = [
            self.create_image('100x100.png'),
            self.create_image('100x100.png'),
            self.create_image('100x50_crop.png'),
            self.create_image('50x100_crop.png'),
        ]
        iterable = [BulkTestObject(image) for image in images]

        adj = Crop(width=50, height=50)

        helper = AdjustmentHelper(iterable, [adj], 'storage_path')
        helper.adjust()

        helper = AdjustmentHelper(iterable, [adj], 'storage_path')
        with self.assertNumQueries(1):
            helper.info_dicts()

    def test_lookup(self):
        storage_path = 'path/to/somewhe.re'
        iterable = [
            BulkTestObject({'bar': storage_path})
        ]
        helper = AdjustmentHelper(iterable,
                                  [Fit(width=50, height=50)],
                                  "storage_path.bar")
        self.assertEqual(helper.adjusted, {})
        self.assertEqual(helper.remaining, {storage_path: [iterable[0]]})

    def test_lookup__invalid(self):
        storage_path = 'path/to/somewhe.re'
        iterable = [
            BulkTestObject({'_bar': storage_path})
        ]
        helper = AdjustmentHelper(iterable,
                                  [Fit(width=50, height=50)],
                                  "storage_path._bar")
        self.assertEqual(helper.adjusted, {iterable[0]: {}})
        self.assertEqual(helper.remaining, {})

########NEW FILE########
__FILENAME__ = test_management
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import CommandError
from django.test.utils import override_settings
import mock

from daguerre.adjustments import Fit
from daguerre.management.commands._daguerre_clean import Command as Clean
from daguerre.management.commands._daguerre_preadjust import (NO_ADJUSTMENTS,
    BAD_STRUCTURE, Command as Preadjust)
from daguerre.models import AdjustedImage, Area
from daguerre.tests.base import BaseTestCase


class CleanTestCase(BaseTestCase):
    def test_old_adjustments(self):
        """
        _old_adjustments should return AdjustedImages whose storage_path
        no longer exists.

        """
        nonexistant = 'daguerre/test/nonexistant.png'
        if default_storage.exists(nonexistant):
            default_storage.delete(nonexistant)

        adjusted = self.create_image('100x100.png')
        adjusted1 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=nonexistant,
                                                 adjusted=adjusted)
        adjusted2 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=adjusted,
                                                 adjusted=adjusted)
        clean = Clean()
        self.assertEqual(list(clean._old_adjustments()), [adjusted1])
        default_storage.delete(adjusted)

    def test_old_areas(self):
        """
        _old_areas should return Areas whose storage_path no longer exists.

        """
        nonexistant = 'daguerre/test/nonexistant.png'
        if default_storage.exists(nonexistant):
            default_storage.delete(nonexistant)

        storage_path = self.create_image('100x100.png')
        kwargs = {
            'x1': 0,
            'x2': 10,
            'y1': 0,
            'y2': 10
        }
        area1 = Area.objects.create(storage_path=nonexistant,
                                    **kwargs)
        area2 = Area.objects.create(storage_path=storage_path,
                                    **kwargs)
        clean = Clean()
        self.assertEqual(list(clean._old_areas()), [area1])
        default_storage.delete(storage_path)

    def test_missing_adjustments(self):
        """
        _missing_adjustments should return AdjustedImages whose adjusted
        no longer exists.

        """
        nonexistant = 'daguerre/test/nonexistant.png'
        if default_storage.exists(nonexistant):
            default_storage.delete(nonexistant)

        storage_path = self.create_image('100x100.png')
        adjusted1 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=storage_path,
                                                 adjusted=nonexistant)
        adjusted2 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=storage_path,
                                                 adjusted=storage_path)
        clean = Clean()
        self.assertEqual(list(clean._missing_adjustments()), [adjusted1])
        default_storage.delete(storage_path)

    def test_duplicate_adjustments(self):
        path1 = self.create_image('100x100.png')
        path2 = self.create_image('100x100.png')
        adjusted1 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=path1,
                                                 adjusted=path1)
        adjusted2 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=path1,
                                                 adjusted=path1)
        adjusted3 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 storage_path=path2,
                                                 adjusted=path1)
        clean = Clean()
        duplicates = clean._duplicate_adjustments()
        self.assertNotIn(adjusted3, duplicates)
        self.assertTrue(list(duplicates) == [adjusted1] or
                        list(duplicates) == [adjusted2])

    def test_orphaned_files(self):
        clean = Clean()
        walk_ret = (
            ('daguerre', ['test'], []),
            ('daguerre/test', [], ['fake1.png', 'fake2.png', 'fake3.png'])
        )
        AdjustedImage.objects.create(requested='fit|50|50',
                                     storage_path='whatever.png',
                                     adjusted='daguerre/test/fake2.png')
        with mock.patch.object(clean, '_walk', return_value=walk_ret) as walk:
            self.assertEqual(clean._orphaned_files(),
                             ['daguerre/test/fake1.png',
                              'daguerre/test/fake3.png'])
            walk.assert_called_once_with('daguerre', topdown=False)


class PreadjustTestCase(BaseTestCase):
    @override_settings()
    def test_get_helpers__no_setting(self):
        try:
            del settings.DAGUERRE_PREADJUSTMENTS
        except AttributeError:
            pass
        preadjust = Preadjust()
        self.assertRaisesMessage(CommandError,
                                 NO_ADJUSTMENTS,
                                 preadjust._get_helpers)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(
        ('model', [Fit(width=50)], None),))
    def test_get_helpers__bad_string(self):
        preadjust = Preadjust()
        self.assertRaisesMessage(CommandError,
                                 BAD_STRUCTURE,
                                 preadjust._get_helpers)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(
        ('app.model', [Fit(width=50)], None),))
    def test_get_helpers__bad_model(self):
        preadjust = Preadjust()
        self.assertRaisesMessage(CommandError,
                                 BAD_STRUCTURE,
                                 preadjust._get_helpers)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(1, 2, 3))
    def test_get_helpers__not_tuples(self):
        preadjust = Preadjust()
        self.assertRaisesMessage(CommandError,
                                 BAD_STRUCTURE,
                                 preadjust._get_helpers)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(
        ('daguerre.adjustedimage', [], 'storage_path'),))
    def test_get_helpers__no_adjustments(self):
        preadjust = Preadjust()
        self.assertRaisesMessage(CommandError,
                                 BAD_STRUCTURE,
                                 preadjust._get_helpers)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(
        ('daguerre.adjustedimage', [Fit(width=50)], 'storage_path'),))
    def test_get_helpers__good_string(self):
        preadjust = Preadjust()
        helpers = preadjust._get_helpers()
        self.assertEqual(len(helpers), 1)

    @override_settings(DAGUERRE_PREADJUSTMENTS=(
        (AdjustedImage, [Fit(width=50)], 'storage_path'),))
    def test_get_helpers__model(self):
        preadjust = Preadjust()
        helpers = preadjust._get_helpers()
        self.assertEqual(len(helpers), 1)

    def test_get_helpers__queryset(self):
        preadjust = Preadjust()
        qs = AdjustedImage.objects.all()
        dp = ((qs, [Fit(width=50)], 'storage_path'),)
        with override_settings(DAGUERRE_PREADJUSTMENTS=dp):
            helpers = preadjust._get_helpers()
        self.assertEqual(len(helpers), 1)
        self.assertTrue(qs._result_cache is None)

    def test_get_helpers__iterable(self):
        preadjust = Preadjust()
        storage_path = self.create_image('100x100.png')
        adjusted = AdjustedImage.objects.create(storage_path=storage_path,
                                                adjusted=storage_path)

        def _iter():
            yield adjusted

        dp = ((_iter(), [Fit(width=50)], 'storage_path'),)

        with override_settings(DAGUERRE_PREADJUSTMENTS=dp):
            helpers = preadjust._get_helpers()
        self.assertEqual(len(helpers), 1)

########NEW FILE########
__FILENAME__ = test_models
from daguerre.models import AdjustedImage
from daguerre.tests.base import BaseTestCase


class AreaTestCase(BaseTestCase):
    def test_delete_adjusted_images__save(self):
        """
        Saving an adjusted image should delete "related" adjusted images
        that use areas.

        """
        storage_path = self.create_image('100x100.png')
        kwargs = {
            'storage_path': storage_path,
            'adjusted': storage_path,
        }
        area = self.create_area(storage_path=storage_path)
        adjusted1 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 **kwargs)
        adjusted2 = AdjustedImage.objects.create(requested='crop|50|50',
                                                 **kwargs)

        area.save()

        self.assertRaises(AdjustedImage.DoesNotExist,
                          AdjustedImage.objects.get,
                          pk=adjusted2.pk)
        AdjustedImage.objects.get(pk=adjusted1.pk)

    def test_delete_adjusted_images__delete(self):
        """
        Deleting an adjusted image should delete "related" adjusted images that
        use areas.

        """
        storage_path = self.create_image('100x100.png')
        kwargs = {
            'storage_path': storage_path,
            'adjusted': storage_path,
        }
        area = self.create_area(storage_path=storage_path)
        adjusted1 = AdjustedImage.objects.create(requested='fit|50|50',
                                                 **kwargs)
        adjusted2 = AdjustedImage.objects.create(requested='crop|50|50',
                                                 **kwargs)

        area.delete()

        self.assertRaises(AdjustedImage.DoesNotExist,
                          AdjustedImage.objects.get,
                          pk=adjusted2.pk)
        AdjustedImage.objects.get(pk=adjusted1.pk)

########NEW FILE########
__FILENAME__ = test_utils
from django.test import TestCase
from django.core.files.storage import default_storage
try:
    from PIL import Image
except ImportError:
    import Image

from daguerre.tests.base import BaseTestCase
from daguerre.utils import (make_hash, save_image, get_exif_orientation,
    get_image_dimensions, apply_exif_orientation, exif_aware_size,
    DEFAULT_FORMAT, KEEP_FORMATS)


class MakeHashTestCase(TestCase):
    def test_unicode(self):
        """
        Make sure that sha1 isn't choking on unicode characters.

        """
        hash_arg = u'banni\xe8re'
        make_hash(hash_arg)


class SaveImageTestCase(BaseTestCase):
    def test_keeper(self):
        """
        If the format is in KEEP_FORMATS, it should be preserved.

        """
        image = Image.open(self._data_path('100x100.png'))
        self.assertIn(image.format, KEEP_FORMATS)

        storage_path = save_image(image, 'daguerre/test/keeper.png',
                                  format=image.format)
        with default_storage.open(storage_path, 'rb') as f:
            new_image = Image.open(f)

        self.assertEqual(new_image.format, image.format)

    def test_non_keeper(self):
        """
        If the format is a weird one, such as a .psd, then the image should
        be saved as the default format rather than the original.

        """
        image = Image.open(self._data_path('100x50.psd'))
        self.assertNotIn(image.format, KEEP_FORMATS)

        storage_path = save_image(image, 'daguerre/test/nonkeeper.png',
                                  format=image.format)
        with default_storage.open(storage_path, 'rb') as f:
            new_image = Image.open(f)

        self.assertEqual(new_image.format, DEFAULT_FORMAT)


class GetExifOrientationTestCase(BaseTestCase):
    def test_exif(self):
        image = Image.open(self._data_path('20x7_exif_rotated.jpg'))
        orientation = get_exif_orientation(image)
        self.assertEqual(orientation, 6)

    def test_non_exif(self):
        "get_exif_orientation should return None if there is no Exif data."
        image = Image.open(self._data_path('20x7_no_exif.png'))
        orientation = get_exif_orientation(image)
        self.assertIsNone(orientation)


class ApplyExifOrientationTestCase(BaseTestCase):
    ORIGINAL_ORIENTATION = (20, 7)
    ROTATED_ORIENTATION = (7, 20)

    def test_exif_rotated(self):
        image = Image.open(self._data_path('20x7_exif_rotated.jpg'))
        image = apply_exif_orientation(image)
        self.assertEqual(image.size, self.ROTATED_ORIENTATION)

    def test_exif_not_rotated(self):
        "If rotation tag is 0, no rotation should be applied."
        image = Image.open(self._data_path('20x7_exif_not_rotated.jpg'))
        image = apply_exif_orientation(image)
        self.assertEqual(image.size, self.ORIGINAL_ORIENTATION)

    def test_non_exif(self):
        "If no exif data is present the original image should be left intact."
        original_image = Image.open(self._data_path('20x7_no_exif.png'))
        image = apply_exif_orientation(original_image)
        self.assertImageEqual(image, original_image)


class ExifAwareSizeTestCase(BaseTestCase):
    ORIGINAL_ORIENTATION = (20, 7)
    ROTATED_ORIENTATION = (7, 20)

    def test_exif_rotated(self):
        image = Image.open(self._data_path('20x7_exif_rotated.jpg'))
        self.assertEqual(exif_aware_size(image), self.ROTATED_ORIENTATION)

    def test_exif_not_rotated(self):
        image = Image.open(self._data_path('20x7_exif_not_rotated.jpg'))
        self.assertEqual(exif_aware_size(image), self.ORIGINAL_ORIENTATION)


    def test_non_exif(self):
        image = Image.open(self._data_path('20x7_no_exif.png'))
        self.assertEqual(exif_aware_size(image), self.ORIGINAL_ORIENTATION)


class GetImageDimensionsTestCase(BaseTestCase):
    ORIGINAL_ORIENTATION = (20, 7)
    ROTATED_ORIENTATION = (7, 20)

    def test_exif_rotated(self):
        dim = get_image_dimensions(self._data_path('20x7_exif_rotated.jpg'))
        self.assertEqual(dim, self.ROTATED_ORIENTATION)

    def test_exif_not_rotated(self):
        dim = get_image_dimensions(self._data_path('20x7_exif_not_rotated.jpg'))
        self.assertEqual(dim, self.ORIGINAL_ORIENTATION)

    def test_non_exif(self):
        dim = get_image_dimensions(self._data_path('20x7_no_exif.png'))
        self.assertEqual(dim, self.ORIGINAL_ORIENTATION)

########NEW FILE########
__FILENAME__ = test_views
import json

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory
from django.utils.encoding import force_text

from daguerre.adjustments import NamedCrop, Fill
from daguerre.helpers import AdjustmentHelper
from daguerre.models import Area
from daguerre.tests.base import BaseTestCase
from daguerre.views import (AdjustedImageRedirectView, AjaxAdjustmentInfoView,
                            AjaxUpdateAreaView)


class AdjustedImageRedirectViewTestCase(BaseTestCase):
    def setUp(self):
        self.view = AdjustedImageRedirectView()
        super(AdjustedImageRedirectViewTestCase, self).setUp()

    def test_check_security(self):
        """
        A 404 should be raised if the security hash is missing or incorrect.

        """
        storage_path = 'path/to/thing.jpg'
        adj1 = NamedCrop(name='face')
        adj2 = Fill(width=10, height=5)
        helper = AdjustmentHelper([storage_path], [adj1, adj2])
        factory = RequestFactory()
        self.view.kwargs = {'storage_path': storage_path}

        get_params = {}
        self.view.request = factory.get('/', get_params)
        self.assertRaises(Http404, self.view.get_helper)

        get_params = {AdjustmentHelper.query_map['security']: 'fake!'}
        self.view.request = factory.get('/', get_params)
        self.assertRaises(Http404, self.view.get_helper)

        get_params = helper.to_querydict(secure=True)
        self.view.request = factory.get('/', get_params)

    def test_nonexistant(self):
        """
        A 404 should be raised if the original image doesn't exist.

        """
        factory = RequestFactory()
        storage_path = 'nonexistant.png'
        helper = AdjustmentHelper([storage_path], [Fill(width=10, height=10)])
        self.view.kwargs = {'storage_path': storage_path}
        self.view.request = factory.get('/', helper.to_querydict(secure=True))
        self.assertRaises(Http404, self.view.get, self.view.request)


class AjaxAdjustmentInfoViewTestCase(BaseTestCase):
    def setUp(self):
        self.view = AjaxAdjustmentInfoView()
        super(AjaxAdjustmentInfoViewTestCase, self).setUp()

    def test_nonexistant(self):
        """
        A 404 should be raised if the original image doesn't exist.

        """
        factory = RequestFactory()
        storage_path = 'nonexistant.png'
        helper = AdjustmentHelper([storage_path], [Fill(width=10, height=5)])
        self.view.kwargs = {'storage_path': storage_path}
        get_params = helper.to_querydict()
        self.view.request = factory.get('/', get_params,
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertRaises(Http404, self.view.get, self.view.request)


class AjaxUpdateAreaViewTestCase(BaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        super(AjaxUpdateAreaViewTestCase, self).setUp()

    def test_not_ajax(self):
        request = self.factory.get('/')
        view = AjaxUpdateAreaView()
        self.assertRaises(Http404, view.get, request)
        self.assertRaises(Http404, view.post, request)
        self.assertRaises(Http404, view.delete, request)

    def test_get__pk(self):
        area = self.create_area(x2=50, y2=50)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        with self.assertNumQueries(1):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/json")
        data = json.loads(force_text(response.content))
        self.assertEqual(data, area.serialize())

    def test_get__pk__wrong(self):
        area = self.create_area(x2=50, y2=50)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk + 1,
        }
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        with self.assertNumQueries(1):
            self.assertRaises(Http404, view.get, request)

    def test_get__no_pk(self):
        area1 = self.create_area(x2=50, y2=50)
        area2 = self.create_area(x2=50, y2=50, storage_path=area1.storage_path)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area1.storage_path,
            'pk': None
        }
        request = self.factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        with self.assertNumQueries(1):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/json")
        data = json.loads(force_text(response.content))
        self.assertEqual(data, [area1.serialize(), area2.serialize()])

    def test_post__no_change_perms(self):
        view = AjaxUpdateAreaView()
        request = self.factory.post('/',
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousUser()
        self.assertFalse(request.user.has_perm('daguerre.change_area'))
        with self.assertNumQueries(0):
            response = view.post(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(force_text(response.content), '')

    def test_post__invalid_params(self):
        area = self.create_area(x2=50, y2=50)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }

        params = {
            'x1': 0,
            'y1': 0,
            'x2': 50,
            'y2': 50,
            'priority': 3,
        }
        user = self.create_user(permissions=['daguerre.change_area'])
        self.assertTrue(user.has_perm('daguerre.change_area'))
        for key in params:
            params_copy = params.copy()
            params_copy[key] = 'hi'
            request = self.factory.post('/', params_copy,
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            request.user = user
            with self.assertNumQueries(0):
                self.assertRaises(Http404, view.post, request)

    def test_post__update(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        old_serialize = area.serialize()
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }

        params = {
            'x1': 50,
            'y1': 50,
            'x2': 100,
            'y2': 100,
            'priority': 1,
            'name': 'fun'
        }
        request = self.factory.post('/', params,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.change_area'])
        self.assertTrue(request.user.has_perm('daguerre.change_area'))
        # SB: Used to assert 4 - don't remember why.
        # Three queries expected: get the area, update the area,
        # and clear the adjustment cache.
        with self.assertNumQueries(3):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/json")
        self.assertEqual(Area.objects.count(), 1)
        data = json.loads(force_text(response.content))
        new_area = Area.objects.get(pk=area.pk, storage_path=area.storage_path)
        self.assertEqual(data, new_area.serialize())
        self.assertNotEqual(data, old_serialize)
        del data['storage_path']
        del data['id']
        self.assertEqual(data, params)

    def test_post__update__invalid(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }

        params = {
            'x1': 100,
            'y1': 50,
            'x2': 50,
            'y2': 100,
            'priority': 1,
            'name': 'fun'
        }
        request = self.factory.post('/', params,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.change_area'])
        self.assertTrue(request.user.has_perm('daguerre.change_area'))
        with self.assertNumQueries(1):
            response = view.post(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Area.objects.count(), 1)
        data = json.loads(force_text(response.content))
        self.assertEqual(list(data.keys()), ['error'])

    def test_post__add(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': None,
        }

        params = {
            'x1': 50,
            'y1': 50,
            'x2': 100,
            'y2': 100,
            'priority': 1,
            'name': 'fun'
        }
        request = self.factory.post('/', params,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.change_area',
                                                     'daguerre.add_area'])
        self.assertTrue(request.user.has_perm('daguerre.change_area'))
        self.assertTrue(request.user.has_perm('daguerre.add_area'))
        with self.assertNumQueries(3):
            response = view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], "application/json")
        self.assertEqual(Area.objects.count(), 2)
        data = json.loads(force_text(response.content))
        new_area = Area.objects.exclude(pk=area.pk).get()
        self.assertEqual(data, new_area.serialize())
        del data['storage_path']
        del data['id']
        self.assertEqual(data, params)

    def test_post__add__no_perms(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': None,
        }

        params = {
            'x1': 50,
            'y1': 50,
            'x2': 100,
            'y2': 100,
            'priority': 1,
            'name': 'fun'
        }
        request = self.factory.post('/', params,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.change_area'])
        self.assertTrue(request.user.has_perm('daguerre.change_area'))
        with self.assertNumQueries(1):
            response = view.post(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Area.objects.count(), 1)
        self.assertEqual(force_text(response.content), '')

    def test_delete__no_perms(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }

        request = self.factory.delete('/',
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = AnonymousUser()
        self.assertFalse(request.user.has_perm('daguerre.delete_area'))
        with self.assertNumQueries(0):
            response = view.delete(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Area.objects.count(), 1)
        self.assertEqual(force_text(response.content), '')

    def test_delete__no_pk(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': None,
        }

        request = self.factory.delete('/',
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.delete_area'])
        self.assertTrue(request.user.has_perm('daguerre.delete_area'))
        with self.assertNumQueries(0):
            self.assertRaises(Http404, view.delete, request)

        self.assertEqual(Area.objects.count(), 1)

    def test_delete(self):
        area = self.create_area(x2=50, y2=50)
        self.assertEqual(Area.objects.count(), 1)
        view = AjaxUpdateAreaView()
        view.kwargs = {
            'storage_path': area.storage_path,
            'pk': area.pk,
        }

        request = self.factory.delete('/',
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.create_user(permissions=['daguerre.delete_area'])
        self.assertTrue(request.user.has_perm('daguerre.delete_area'))
        with self.assertNumQueries(3):
            response = view.delete(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(force_text(response.content), '')
        self.assertEqual(Area.objects.count(), 0)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from daguerre.views import (AdjustedImageRedirectView, AjaxAdjustmentInfoView,
                            AjaxUpdateAreaView)


urlpatterns = patterns(
    '',
    url(r'^adjust/(?P<storage_path>.+)$',
        AdjustedImageRedirectView.as_view(),
        name="daguerre_adjusted_image_redirect"),
    url(r'^info/(?P<storage_path>.+)$',
        AjaxAdjustmentInfoView.as_view(),
        name="daguerre_ajax_adjustment_info"),
    url(r'^area/(?P<storage_path>.+?)(?:/(?P<pk>\d+))?$',
        AjaxUpdateAreaView.as_view(),
        name="daguerre_ajax_update_area"),
)

########NEW FILE########
__FILENAME__ = utils
import zlib

from hashlib import sha1

from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.files.temp import NamedTemporaryFile
from django.utils.encoding import smart_bytes
import six
try:
    from PIL import Image, ImageFile, ExifTags
except ImportError:
    import Image, ImageFile, ExifTags

#: Formats that we trust to be able to handle gracefully.
KEEP_FORMATS = ('PNG', 'JPEG', 'GIF')
#: Default format to convert other file types to.
DEFAULT_FORMAT = 'PNG'
#: Map Exif orientation data to corresponding PIL image transpose values
ORIENTATION_TO_TRANSPOSE = {
    1: None,
    2: (Image.FLIP_LEFT_RIGHT,),
    3: (Image.ROTATE_180,),
    4: (Image.ROTATE_180, Image.FLIP_LEFT_RIGHT,),
    5: (Image.ROTATE_270, Image.FLIP_LEFT_RIGHT,),
    6: (Image.ROTATE_270,),
    7: (Image.ROTATE_90, Image.FLIP_LEFT_RIGHT,),
    8: (Image.ROTATE_90,),
}
#: Which Exif orientation tags correspond to a 90deg or 270deg rotation.
ROTATION_TAGS = (5, 6, 7, 8)
#: Map human-readable Exif tag names to their markers.
EXIF_TAGS = {y:x for x,y in ExifTags.TAGS.items()}


def make_hash(*args, **kwargs):
    start = kwargs.get('start', None)
    stop = kwargs.get('stop', None)
    step = kwargs.get('step', None)
    return sha1(smart_bytes(u''.join([
        six.text_type(arg) for arg in args])
    )).hexdigest()[start:stop:step]


def get_exif_orientation(image):
    # Extract the orientation tag
    try:
        exif_data = image._getexif() # should be careful with that _method
    except AttributeError:
        # No Exif data, return None
        return None
    if exif_data is not None and EXIF_TAGS['Orientation'] in exif_data: 
        orientation = exif_data[EXIF_TAGS['Orientation']]
        return orientation
    # No Exif orientation tag, return None
    return None


def apply_exif_orientation(image):
    """
    Reads an image Exif data for orientation information. Applies the
    appropriate rotation with PIL transposition. Use before performing a PIL
    .resize() in order to retain correct image rotation. (.resize() discards
    Exif tags.)

    Accepts a PIL image and returns a PIL image.

    """
    orientation = get_exif_orientation(image)
    if orientation is not None:
        # Apply corresponding transpositions
        transpositions = ORIENTATION_TO_TRANSPOSE[orientation]
        if transpositions:
            for t in transpositions:
                image = image.transpose(t)
    return image


def exif_aware_size(image):
    """
    Intelligently get an image size, flipping width and height if the Exif
    orientation tag includes a 90deg or 270deg rotation.

    :param image: A PIL Image.

    :returns: A 2-tuple (width, height).

    """
    # Extract the orientation tag
    orientation = get_exif_orientation(image)
    if orientation in ROTATION_TAGS:
        # Exif data indicates image should be rotated. Flip dimensions.
        return image.size[::-1]
    return image.size


def exif_aware_resize(image, *args, **kwargs):
    """
    Intelligently resize an image, taking Exif orientation into account. Takes
    the same arguments as the PIL Image ``.resize()`` method.

    :param image: A PIL Image.

    :returns: An PIL Image object.

    """

    image = apply_exif_orientation(image)
    return image.resize(*args, **kwargs)


def get_image_dimensions(file_or_path, close=False):
    """
    A modified version of ``django.core.files.images.get_image_dimensions``
    which accounts for Exif orientation.

    """

    p = ImageFile.Parser()
    if hasattr(file_or_path, 'read'):
        file = file_or_path
        file_pos = file.tell()
        file.seek(0)
    else:
        file = open(file_or_path, 'rb')
        close = True
    try:
        # Most of the time PIL only needs a small chunk to parse the image and
        # get the dimensions, but with some TIFF files PIL needs to parse the
        # whole file.
        chunk_size = 1024
        while 1:
            data = file.read(chunk_size)
            if not data:
                break
            try:
                p.feed(data)
            except zlib.error as e:
                # ignore zlib complaining on truncated stream, just feed more
                # data to parser (ticket #19457).
                if e.args[0].startswith("Error -5"):
                    pass
                else:
                    raise
            if p.image:
                return exif_aware_size(p.image)
            chunk_size *= 2
        return None
    finally:
        if close:
            file.close()
        else:
            file.seek(file_pos)


def save_image(
        image,
        storage_path,
        format=DEFAULT_FORMAT,
        storage=default_storage):
    """
    Saves a PIL image file to the given storage_path using the given storage.
    Returns the final storage path of the saved file.

    """
    if format not in KEEP_FORMATS:
        format = DEFAULT_FORMAT

    with NamedTemporaryFile() as temp:
        image.save(temp, format=format)
        return storage.save(storage_path, File(temp))

########NEW FILE########
__FILENAME__ = views
import json

from django.contrib.auth import get_permission_codename
from django.core.exceptions import ValidationError
from django.http import (HttpResponse, Http404, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.views.generic import View
import six

from daguerre.helpers import AdjustmentHelper
from daguerre.models import Area


class AdjustedImageRedirectView(View):
    """
    Returns a redirect to an :attr:`~AdjustedImage.adjusted` file,
    first creating the :class:`~AdjustedImage` if necessary.

    :param storage_path: The path to the original image file,
    relative to the default storage.
    """
    secure = True

    def get_helper(self):
        try:
            return AdjustmentHelper.from_querydict(
                self.kwargs['storage_path'],
                self.request.GET,
                secure=self.secure)
        except ValueError as e:
            raise Http404(six.text_type(e))

    def get(self, request, *args, **kwargs):
        helper = self.get_helper()
        helper.adjust()
        try:
            adjusted = list(helper.adjusted.values())[0]
            url = adjusted['url']
        except (IndexError, KeyError):
            raise Http404("Adjustment failed.")
        return HttpResponseRedirect(url)


class AjaxAdjustmentInfoView(AdjustedImageRedirectView):
    """Returns a JSON response containing the results of a call to
    :meth:`.Adjustment.info_dict` for the given parameters."""
    secure = False

    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404("Request is not AJAX.")

        helper = self.get_helper()
        info_dict = helper.info_dicts()[0][1]

        if not info_dict:
            # Something went wrong. The image probably doesn't exist.
            raise Http404

        return HttpResponse(
            json.dumps(info_dict),
            content_type="application/json")


class AjaxUpdateAreaView(View):
    def has_permission(self, user, action, model):
        opts = model._meta
        codename = get_permission_codename(action, opts)
        return user.has_perm('.'.join((opts.app_label, codename)))

    def has_add_permission(self, request):
        return self.has_permission(request.user, 'add', Area)

    def has_change_permission(self, request):
        return self.has_permission(request.user, 'change', Area)

    def has_delete_permission(self, request):
        return self.has_permission(request.user, 'delete', Area)

    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404("Request is not AJAX.")

        storage_path = self.kwargs['storage_path']

        if self.kwargs['pk'] is not None:
            try:
                area = Area.objects.get(storage_path=storage_path,
                                        pk=self.kwargs['pk'])
            except Area.DoesNotExist:
                raise Http404

            data = area.serialize()
        else:
            areas = Area.objects.filter(storage_path=storage_path)
            data = [area.serialize() for area in areas]
        return HttpResponse(json.dumps(data), content_type="application/json")

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404("Request is not AJAX.")

        if not self.has_change_permission(request):
            return HttpResponseForbidden('')

        storage_path = self.kwargs['storage_path']
        data = {
            'name': request.POST.get('name') or '',
        }
        for int_field in ('x1', 'x2', 'y1', 'y2', 'priority'):
            try:
                data[int_field] = int(request.POST.get(int_field))
            except (ValueError, TypeError):
                raise Http404

        try:
            area = Area.objects.get(storage_path=storage_path,
                                    pk=self.kwargs['pk'])
        except Area.DoesNotExist:
            if not self.has_add_permission(request):
                return HttpResponseForbidden('')
            area = Area(storage_path=storage_path, **data)
        else:
            for fname, value in six.iteritems(data):
                setattr(area, fname, value)

        status = 200
        try:
            area.full_clean()
        except ValidationError as e:
            data = {'error': e.message_dict}
            status = 400
        else:
            area.save()
            data = area.serialize()

        return HttpResponse(json.dumps(data),
                            content_type="application/json",
                            status=status)

    def delete(self, request, *args, **kwargs):
        if not request.is_ajax():
            raise Http404("Request is not AJAX.")

        if self.kwargs['pk'] is None:
            raise Http404("No pk was provided.")

        if not self.has_delete_permission(request):
            return HttpResponseForbidden('')

        Area.objects.filter(storage_path=self.kwargs['storage_path'],
                            pk=self.kwargs['pk']).delete()

        return HttpResponse('')

########NEW FILE########
__FILENAME__ = widgets
from django.contrib.admin.widgets import AdminFileWidget
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe


class AreaWidget(AdminFileWidget):
    class Media:
        css = {
            'all': ('imgareaselect/css/imgareaselect-animated.css',
                    'daguerre/css/areawidget.css',)
        }
        js = (
            'imgareaselect/scripts/jquery.imgareaselect.js',
            'daguerre/js/areawidget.daguerre.js',
        )

    def render(self, name, value, attrs=None):
        content = super(AreaWidget, self).render(name, value, attrs)
        if value and hasattr(value, 'url'):
            content += (
                "<div class='daguerre-areas' id='{0}-areas'"
                " data-storage-path='{1}' data-width='{2}' data-height='{3}'"
                " data-url='{4}' data-area-url='{5}'></div>").format(
                    name,
                    value.name,
                    value.width,
                    value.height,
                    reverse(
                        'daguerre_ajax_adjustment_info',
                        kwargs={'storage_path': value.name}),
                    reverse(
                        'daguerre_ajax_update_area',
                        kwargs={'storage_path': value.name}))
        return mark_safe(content)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Daguerre documentation build configuration file, created by
# sphinx-quickstart on Tue Jul 31 14:54:31 2012.
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
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "_ext")))
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

os.environ['DJANGO_SETTINGS_MODULE'] = 'dummy-settings'

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['djangodocs', 'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
# templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Daguerre'
copyright = u'2010-2014, Little Weaver Web Collective, LLC'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.1'
# The full version, including alpha/beta/rc tags.
release = '2.1.1'

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


# -- Options for HTML output ---------------------------------------------------

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# otherwise, readthedocs.org uses their theme by default, so no need to specify it

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
htmlhelp_basename = 'DjangoDaguerredoc'


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
  ('index', 'DjangoDaguerre.tex', u'Django Daguerre Documentation',
   u'Stephen Burrows, Harris Lapiroff', 'manual'),
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
    ('index', 'djangodaguerre', u'Django Daguerre Documentation',
     [u'Stephen Burrows, Harris Lapiroff'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DjangoDaguerre', u'Django Daguerre Documentation',
   u'Stephen Burrows, Harris Lapiroff', 'DjangoDaguerre', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = dummy-settings
DATABASES = {
	"default": {
		"NAME": ":memory:",
		"ENGINE": "django.db.backends.sqlite3",
	}
}

SECRET_KEY = "NOT SECRET"
########NEW FILE########
__FILENAME__ = djangodocs
"""
Sphinx plugins for Django documentation.
"""
import os
import re

from docutils import nodes, transforms
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        try:
            from django.utils import simplejson as json
        except ImportError:
            json = None

from sphinx import addnodes, roles
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import SmartyPantsHTMLTranslator
from sphinx.util.console import bold
from sphinx.util.compat import Directive

# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
    r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')

def setup(app):
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s; field lookup type",
    )
    app.add_description_unit(
        directivename = "django-admin",
        rolename      = "djadmin",
        indextemplate = "pair: %s; django-admin command",
        parse_node    = parse_django_admin_node,
    )
    app.add_description_unit(
        directivename = "django-admin-option",
        rolename      = "djadminopt",
        indextemplate = "pair: %s; django-admin command-line option",
        parse_node    = parse_django_adminopt_node,
    )
    app.add_config_value('django_next_version', '0.0', True)
    app.add_directive('versionadded', VersionDirective)
    app.add_directive('versionchanged', VersionDirective)
    app.add_transform(SuppressBlockquotes)
    app.add_builder(DjangoStandaloneHTMLBuilder)


class VersionDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        arg0 = self.arguments[0]
        is_nextversion = env.config.django_next_version == arg0
        ret = []
        node = addnodes.versionmodified()
        ret.append(node)
        if not is_nextversion:
            if len(self.arguments) == 1:
                linktext = 'Please, see the release notes </releases/%s>' % (arg0)
                xrefs = roles.XRefRole()('doc', linktext, linktext, self.lineno, self.state)
                node.extend(xrefs[0])
            node['version'] = arg0
        else:
            node['version'] = "Development version"
        node['type'] = self.name
        if len(self.arguments) == 2:
            inodes, messages = self.state.inline_text(self.arguments[1], self.lineno+1)
            node.extend(inodes)
            if self.content:
                self.state.nested_parse(self.content, self.content_offset, node)
            ret = ret + messages
        env.note_versionchange(node['type'], node['version'], node, self.lineno)
        return ret


class SuppressBlockquotes(transforms.Transform):
    """
    Remove the default blockquotes that encase indented list, tables, etc.
    """
    default_priority = 300

    suppress_blockquote_child_nodes = (
        nodes.bullet_list,
        nodes.enumerated_list,
        nodes.definition_list,
        nodes.literal_block,
        nodes.doctest_block,
        nodes.line_block,
        nodes.table
    )

    def apply(self):
        for node in self.document.traverse(nodes.block_quote):
            if len(node.children) == 1 and isinstance(node.children[0], self.suppress_blockquote_child_nodes):
                node.replace_self(node.children[0])

class DjangoHTMLTranslator(SmartyPantsHTMLTranslator):
    """
    Django-specific reST to HTML tweaks.
    """

    # Don't use border=1, which docutils does by default.
    def visit_table(self, node):
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

    # <big>? Really?
    def visit_desc_parameterlist(self, node):
        self.body.append('(')
        self.first_param = 1

    def depart_desc_parameterlist(self, node):
        self.body.append(')')

    #
    # Don't apply smartypants to literal blocks
    #
    def visit_literal_block(self, node):
        self.no_smarty += 1
        SmartyPantsHTMLTranslator.visit_literal_block(self, node)

    def depart_literal_block(self, node):
        SmartyPantsHTMLTranslator.depart_literal_block(self, node)
        self.no_smarty -= 1

    #
    # Turn the "new in version" stuff (versionadded/versionchanged) into a
    # better callout -- the Sphinx default is just a little span,
    # which is a bit less obvious that I'd like.
    #
    # FIXME: these messages are all hardcoded in English. We need to change
    # that to accomodate other language docs, but I can't work out how to make
    # that work.
    #
    version_text = {
        'deprecated':       'Deprecated in Django %s',
        'versionchanged':   'Changed in Django %s',
        'versionadded':     'New in Django %s',
    }

    def visit_versionmodified(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS=node['type'])
        )
        title = "%s%s" % (
            self.version_text[node['type']] % node['version'],
            len(node) and ":" or "."
        )
        self.body.append('<span class="title">%s</span> ' % title)

    def depart_versionmodified(self, node):
        self.body.append("</div>\n")

    # Give each section a unique ID -- nice for custom CSS hooks
    def visit_section(self, node):
        old_ids = node.get('ids', [])
        node['ids'] = ['s-' + i for i in old_ids]
        node['ids'].extend(old_ids)
        SmartyPantsHTMLTranslator.visit_section(self, node)
        node['ids'] = old_ids

def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += addnodes.desc_name(title, title)
    return sig

def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx.domains.std import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not count:
        for m in simple_option_desc_re.finditer(sig):
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
            count += 1
    if not firstname:
        raise ValueError
    return firstname


class DjangoStandaloneHTMLBuilder(StandaloneHTMLBuilder):
    """
    Subclass to add some extra things we need.
    """

    name = 'djangohtml'

    def finish(self):
        super(DjangoStandaloneHTMLBuilder, self).finish()
        if json is None:
            self.warn("cannot create templatebuiltins.js due to missing simplejson dependency")
            return
        self.info(bold("writing templatebuiltins.js..."))
        xrefs = self.env.domaindata["std"]["objects"]
        templatebuiltins = {
            "ttags": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatetag" and l == "ref/templates/builtins"],
            "tfilters": [n for ((t, n), (l, a)) in xrefs.items()
                        if t == "templatefilter" and l == "ref/templates/builtins"],
        }
        outfilename = os.path.join(self.outdir, "templatebuiltins.js")
        f = open(outfilename, 'wb')
        f.write('var django_template_builtins = ')
        json.dump(templatebuiltins, f)
        f.write(';\n')
        f.close();
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Settings for testing django-daguerre.

import os

PROJECT_DIR = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

DB = os.environ.get('DB')
if DB == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'daguerre_test',
            'USER': 'root',
            'TEST_CHARSET': 'utf8',
            'TEST_COLLATION': 'utf8_general_ci',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(PROJECT_DIR, 'db.sl3'),
        }
    }

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = False
USE_TZ = True

MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media/')
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(PROJECT_DIR, 'static/')
STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

SECRET_KEY = 'test_key'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'test_project.urls'
WSGI_APPLICATION = 'test_project.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'daguerre',
)

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +
    patterns('', url(r'^', include('daguerre.urls')))
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
