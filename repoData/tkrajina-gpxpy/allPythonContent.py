__FILENAME__ = geo
# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pdb

import logging as mod_logging
import math as mod_math

from . import utils as mod_utils

# Generic geo related function and class(es)

# One degree in meters:
ONE_DEGREE = 1000. * 10000.8 / 90.

EARTH_RADIUS = 6371 * 1000


def to_rad(x):
    return x / 180. * mod_math.pi


def haversine_distance(latitude_1, longitude_1, latitude_2, longitude_2):
    """
    Haversine distance between two points, expressed in meters.

    Implemented from http://www.movable-type.co.uk/scripts/latlong.html
    """
    d_lat = to_rad(latitude_1 - latitude_2)
    d_lon = to_rad(longitude_1 - longitude_2)
    lat1 = to_rad(latitude_1)
    lat2 = to_rad(latitude_2)

    a = mod_math.sin(d_lat/2) * mod_math.sin(d_lat/2) + \
        mod_math.sin(d_lon/2) * mod_math.sin(d_lon/2) * mod_math.cos(lat1) * mod_math.cos(lat2)
    c = 2 * mod_math.atan2(mod_math.sqrt(a), mod_math.sqrt(1-a))
    d = EARTH_RADIUS * c

    return d


def length(locations=None, _3d=None):
    locations = locations or []
    if not locations:
        return 0
    length = 0
    for i in range(len(locations)):
        if i > 0:
            previous_location = locations[i - 1]
            location = locations[i]

            if _3d:
                d = location.distance_3d(previous_location)
            else:
                d = location.distance_2d(previous_location)
            if d != 0 and not d:
                pass
            else:
                length += d
    return length


def length_2d(locations=None):
    """ 2-dimensional length (meters) of locations (only latitude and longitude, no elevation). """
    locations = locations or []
    return length(locations, False)


def length_3d(locations=None):
    """ 3-dimensional length (meters) of locations (it uses latitude, longitude, and elevation). """
    locations = locations or []
    return length(locations, True)


def calculate_max_speed(speeds_and_distances):
    """
    Compute average distance and standard deviation for distance. Extremes
    in distances are usually extremes in speeds, so we will ignore them,
    here.

    speeds_and_distances must be a list containing pairs of (speed, distance)
    for every point in a track segment.
    """
    assert speeds_and_distances
    if len(speeds_and_distances) > 0:
        assert len(speeds_and_distances[0]) == 2
        # ...
        assert len(speeds_and_distances[-1]) == 2

    size = float(len(speeds_and_distances))

    if size < 20:
        mod_logging.debug('Segment too small to compute speed, size=%s', size)
        return None

    distances = list(map(lambda x: x[1], speeds_and_distances))
    average_distance = sum(distances) / float(size)
    standard_distance_deviation = mod_math.sqrt(sum(map(lambda distance: (distance-average_distance)**2, distances))/size)

    # Ignore items where the distance is too big:
    filtered_speeds_and_distances = filter(lambda speed_and_distance: abs(speed_and_distance[1] - average_distance) <= standard_distance_deviation * 1.5, speeds_and_distances)

    # sort by speed:
    speeds = list(map(lambda speed_and_distance: speed_and_distance[0], filtered_speeds_and_distances))
    if not isinstance(speeds, list):  # python3
        speeds = list(speeds)
    if not speeds:
        return None
    speeds.sort()

    # Even here there may be some extremes => ignore the last 5%:
    index = int(len(speeds) * 0.95)
    if index >= len(speeds):
        index = -1

    return speeds[index]


def calculate_uphill_downhill(elevations):
    if not elevations:
        return 0, 0

    size = len(elevations)

    def __filter(n):
        current_ele = elevations[n]
        if current_ele is None:
            return False
        if 0 < n < size - 1:
            previous_ele = elevations[n-1]
            next_ele = elevations[n+1]
            if previous_ele is not None and current_ele is not None and next_ele is not None:
                return previous_ele*.3 + current_ele*.4 + next_ele*.3
        return current_ele

    smoothed_elevations = list(map(__filter, range(size)))

    uphill, downhill = 0., 0.

    for n, elevation in enumerate(smoothed_elevations):
        if n > 0 and elevation is not None and smoothed_elevations is not None:
            d = elevation - smoothed_elevations[n-1]
            if d > 0:
                uphill += d
            else:
                downhill -= d

    return uphill, downhill


def distance(latitude_1, longitude_1, elevation_1, latitude_2, longitude_2, elevation_2,
             haversine=None):
    """
    Distance between two points. If elevation is None compute a 2d distance

    if haversine==True -- haversine will be used for every computations,
    otherwise...

    Haversine distance will be used for distant points where elevation makes a
    small difference, so it is ignored. That's because haversine is 5-6 times
    slower than the dummy distance algorithm (which is OK for most GPS tracks).
    """

    # If points too distant -- compute haversine distance:
    if haversine or (abs(latitude_1 - latitude_2) > .2 or abs(longitude_1 - longitude_2) > .2):
        return haversine_distance(latitude_1, longitude_1, latitude_2, longitude_2)

    coef = mod_math.cos(latitude_1 / 180. * mod_math.pi)
    x = latitude_1 - latitude_2
    y = (longitude_1 - longitude_2) * coef

    distance_2d = mod_math.sqrt(x * x + y * y) * ONE_DEGREE

    if elevation_1 is None or elevation_2 is None or elevation_1 == elevation_2:
        return distance_2d

    return mod_math.sqrt(distance_2d ** 2 + (elevation_1 - elevation_2) ** 2)


def elevation_angle(location1, location2, radians=False):
    """ Uphill/downhill angle between two locations. """
    if location1.elevation is None or location2.elevation is None:
        return None

    b = float(location2.elevation - location1.elevation)
    a = location2.distance_2d(location1)

    if a == 0:
        return 0

    angle = mod_math.atan(b / a)

    if radians:
        return angle

    return 180 * angle / mod_math.pi


def distance_from_line(point, line_point_1, line_point_2):
    """ Distance of point from a line given with two points. """
    assert point, point
    assert line_point_1, line_point_1
    assert line_point_2, line_point_2

    a = line_point_1.distance_2d(line_point_2)

    if a == 0:
        return line_point_1.distance_2d(point)

    b = line_point_1.distance_2d(point)
    c = line_point_2.distance_2d(point)

    s = (a + b + c) / 2.

    return 2. * mod_math.sqrt(abs(s * (s - a) * (s - b) * (s - c))) / a


def get_line_equation_coefficients(location1, location2):
    """
    Get line equation coefficients for:
        latitude * a + longitude * b + c = 0

    This is a normal cartesian line (not spherical!)
    """
    if location1.longitude == location2.longitude:
        # Vertical line:
        return float(0), float(1), float(-location1.longitude)
    else:
        a = float(location1.latitude - location2.latitude) / (location1.longitude - location2.longitude)
        b = location1.latitude - location1.longitude * a
        return float(1), float(-a), float(-b)


def simplify_polyline(points, max_distance):
    """Does Ramer-Douglas-Peucker algorithm for simplification of polyline """

    if len(points) < 3:
        return points

    begin, end = points[0], points[-1]

    # Use a "normal" line just to detect the most distant point (not its real distance)
    # this is because this is faster to compute than calling distance_from_line() for
    # every point.
    #
    # This is an approximation and may have some errors near the poles and if
    # the points are too distant, but it should be good enough for most use
    # cases...
    a, b, c = get_line_equation_coefficients(begin, end)

    tmp_max_distance = -1000000
    tmp_max_distance_position = None
    for point_no in range(len(points[1:-1])):
        point = points[point_no]
        d = abs(a * point.latitude + b * point.longitude + c)
        if d > tmp_max_distance:
            tmp_max_distance = d
            tmp_max_distance_position = point_no

    # Now that we have the most distance point, compute its real distance:
    real_max_distance = distance_from_line(points[tmp_max_distance_position], begin, end)

    if real_max_distance < max_distance:
        return [begin, end]

    return (simplify_polyline(points[:tmp_max_distance_position + 2], max_distance) +
            simplify_polyline(points[tmp_max_distance_position + 1:], max_distance)[1:])


class Location:
    """ Generic geographical location """

    latitude = None
    longitude = None
    elevation = None

    def __init__(self, latitude, longitude, elevation=None):
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation

    def has_elevation(self):
        return self.elevation or self.elevation == 0

    def remove_elevation(self):
        self.elevation = None

    def distance_2d(self, location):
        if not location:
            return None

        return distance(self.latitude, self.longitude, None, location.latitude, location.longitude, None)

    def distance_3d(self, location):
        if not location:
            return None

        return distance(self.latitude, self.longitude, self.elevation, location.latitude, location.longitude, location.elevation)

    def elevation_angle(self, location, radians=False):
        return elevation_angle(self, location, radians)

    def move(self, location_delta):
        self.latitude, self.longitude = location_delta.move(self)

    def __add__(self, location_delta):
        latitude, longitude = location_delta.move(self)
        return Location(latitude, longitude)

    def __str__(self):
        return '[loc:%s,%s@%s]' % (self.latitude, self.longitude, self.elevation)

    def __repr__(self):
        if self.elevation is None:
            return 'Location(%s, %s)' % (self.latitude, self.longitude)
        else:
            return 'Location(%s, %s, %s)' % (self.latitude, self.longitude, self.elevation)

    def __hash__(self):
        return mod_utils.hash_object(self, 'latitude', 'longitude', 'elevation')


class LocationDelta:
    """
    Intended to use similar to timestamp.timedelta, but for Locations.
    """

    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270

    def __init__(self, distance=None, angle=None, latitude_diff=None, longitude_diff=None):
        """
        Version 1:
            Distance (in meters).
            angle_from_north *clockwise*. 
            ...must be given
        Version 2:
            latitude_diff and longitude_diff
            ...must be given
        """
        if (distance is not None) and (angle is not None):
            if (latitude_diff is not None) or (longitude_diff is not None):
                raise Exception('No lat/lon diff if using distance and angle!')
            self.distance = distance
            self.angle_from_north = angle
            self.move_function = self.move_by_angle_and_distance
        elif (latitude_diff is not None) and (longitude_diff is not None):
            if (distance is not None) or (angle is not None):
                raise Exception('No distance/angle if using lat/lon diff!')
            this.latitude_diff  = latitude_diff
            this.longitude_diff = longitude_diff
            self.move_function = self.move_by_lat_lon_diff

    def move(self, location):
        """
        Move location by this timedelta.
        """
        return self.move_function(location)

    def move_by_angle_and_distance(self, location):
        coef = mod_math.cos(location.latitude / 180. * mod_math.pi)
        vertical_distance_diff   = mod_math.sin((90 - self.angle_from_north) / 180. * mod_math.pi) / ONE_DEGREE
        horizontal_distance_diff = mod_math.cos((90 - self.angle_from_north) / 180. * mod_math.pi) / ONE_DEGREE
        lat_diff = self.distance * vertical_distance_diff
        lon_diff = self.distance * horizontal_distance_diff / coef
        return location.latitude + lat_diff, location.longitude + lon_diff

    def move_by_lat_lon_diff(self, location):
        return location.latitude  + self.latitude_diff, location.longitude + self.longitude_diff

########NEW FILE########
__FILENAME__ = gpx
# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
GPX related stuff
"""

import pdb

import logging as mod_logging
import math as mod_math
import collections as mod_collections
import copy as mod_copy
import datetime as mod_datetime

from . import utils as mod_utils
from . import geo as mod_geo

# GPX date format to be used when writing the GPX output:
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# GPX date format(s) used for parsing. The T between date and time and Z after
# time are allowed, too:
DATE_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    #'%Y-%m-%d %H:%M:%S%z',
    #'%Y-%m-%d %H:%M:%S.%f%z',
]
# Used in smoothing, sum must be 1:
SMOOTHING_RATIO = (0.4, 0.2, 0.4)

# When computing stopped time -- this is the minimum speed between two points,
# if speed is less than this value -- we'll assume it is zero
DEFAULT_STOPPED_SPEED_THRESHOLD = 1

# When possible, the result of various methods are named tuples defined here:
Bounds = mod_collections.namedtuple(
    'Bounds',
    ('min_latitude', 'max_latitude', 'min_longitude', 'max_longitude'))
TimeBounds = mod_collections.namedtuple(
    'TimeBounds',
    ('start_time', 'end_time'))
MovingData = mod_collections.namedtuple(
    'MovingData',
    ('moving_time', 'stopped_time', 'moving_distance', 'stopped_distance', 'max_speed'))
UphillDownhill = mod_collections.namedtuple(
    'UphillDownhill',
    ('uphill', 'downhill'))
MinimumMaximum = mod_collections.namedtuple(
    'MinimumMaximum',
    ('minimum', 'maximum'))
NearestLocationData = mod_collections.namedtuple(
    'NearestLocationData',
    ('location', 'track_no', 'segment_no', 'point_no'))
PointData = mod_collections.namedtuple(
    'PointData',
    ('point', 'distance_from_start', 'track_no', 'segment_no', 'point_no'))


class GPXException(Exception):
    """
    Exception used for invalid GPX files. Is is used when the XML file is
    valid but something is wrong with the GPX data.
    """
    pass


class GPXXMLSyntaxException(GPXException):
    """
    Exception used when the the XML syntax is invalid.

    The __cause__ can be a minidom or lxml exception (See http://www.python.org/dev/peps/pep-3134/).
    """
    def __init__(self, message, original_exception):
        GPXException.__init__(self, message)
        self.__cause__ = original_exception


class GPXWaypoint(mod_geo.Location):
    time = None
    name = None
    description = None
    symbol = None
    type = None
    comment = None

    # Horizontal dilution of precision
    horizontal_dilution = None
    # Vertical dilution of precision
    vertical_dilution = None
    # Position dilution of precision
    position_dilution = None

    def __init__(self, latitude, longitude, elevation=None, time=None,
                 name=None, description=None, symbol=None, type=None,
                 comment=None, horizontal_dilution=None, vertical_dilution=None,
                 position_dilution=None):
        mod_geo.Location.__init__(self, latitude, longitude, elevation)

        self.time = time
        self.name = name
        self.description = description
        self.symbol = symbol
        self.type = type
        self.comment = comment

        self.horizontal_dilution = horizontal_dilution
        self.vertical_dilution = vertical_dilution
        self.position_dilution = position_dilution

    def __str__(self):
        return '[wpt{%s}:%s,%s@%s]' % (self.name, self.latitude, self.longitude, self.elevation)

    def __repr__(self):
        representation = '%s, %s' % (self.latitude, self.longitude)
        for attribute in 'elevation', 'time', 'name', 'description', 'symbol', 'type', 'comment', \
                'horizontal_dilution', 'vertical_dilution', 'position_dilution':
            value = getattr(self, attribute)
            if value is not None:
                representation += ', %s=%s' % (attribute, repr(value))
        return 'GPXWaypoint(%s)' % representation

    def to_xml(self, version=None):
        content = ''
        if self.elevation is not None:
            content += mod_utils.to_xml('ele', content=self.elevation)
        if self.time:
            content += mod_utils.to_xml('time', content=self.time.strftime(DATE_FORMAT))
        if self.name:
            content += mod_utils.to_xml('name', content=self.name, escape=True)
        if self.description:
            content += mod_utils.to_xml('desc', content=self.description, escape=True)
        if self.symbol:
            content += mod_utils.to_xml('sym', content=self.symbol, escape=True)
        if self.type:
            content += mod_utils.to_xml('type', content=self.type, escape=True)

        if version == '1.1':  # TODO
            content += mod_utils.to_xml('cmt', content=self.comment, escape=True)

        if self.horizontal_dilution:
            content += mod_utils.to_xml('hdop', content=self.horizontal_dilution)
        if self.vertical_dilution:
            content += mod_utils.to_xml('vdop', content=self.vertical_dilution)
        if self.position_dilution:
            content += mod_utils.to_xml('pdop', content=self.position_dilution)

        return mod_utils.to_xml('wpt', attributes={'lat': self.latitude, 'lon': self.longitude}, content=content)

    def get_max_dilution_of_precision(self):
        """
        Only care about the max dop for filtering, no need to go into too much detail
        """
        return max(self.horizontal_dilution, self.vertical_dilution, self.position_dilution)

    def __hash__(self):
        return mod_utils.hash_object(self, 'time', 'name', 'description', 'symbol', 'type',
                                     'comment', 'horizontal_dilution', 'vertical_dilution', 'position_dilution')


class GPXRoute:
    def __init__(self, name=None, description=None, number=None):
        self.name = name
        self.description = description
        self.number = number

        self.points = []

    def remove_elevation(self):
        """ Removes elevation data from route """
        for point in self.points:
            point.remove_elevation()

    def length(self):
        """ 
        Computes length (2-dimensional) of route. 
         
        Returns:
        -----------
        length: float
            Length returned in meters
         """
        return mod_geo.length_2d(self.points)

    def get_center(self):
        """
        Get the center of the route.

        Returns
        -------
        center: Location
            latitude: latitude of center in degrees
            longitude: longitude of center in degrees
            elevation: not calculated here
        """
        if not self.points:
            return None

        if not self.points:
            return None

        sum_lat = 0.
        sum_lon = 0.
        n = 0.

        for point in self.points:
            n += 1.
            sum_lat += point.latitude
            sum_lon += point.longitude

        if not n:
            return mod_geo.Location(float(0), float(0))

        return mod_geo.Location(latitude=sum_lat / n, longitude=sum_lon / n)

    def walk(self, only_points=False):
        """
        Generator for iterating over route points

        Parameters
        ----------
        only_points: boolean
            Only yield points (no index yielded)

        Yields
        ------
        point: GPXRoutePoint
            A point in the GPXRoute
        point_no: int 
            Not included in yield if only_points is true
        """
        for point_no, point in enumerate(self.points):
            if only_points:
                yield point
            else:
                yield point, point_no

    def get_points_no(self):
        """
        Get the number of points in route.

        Returns
        ----------
        num_points : integer
            Number of points in route
        """
        return len(self.points)

    def move(self, location_delta):
        """
        Moves each point in the route.

        Parameters
        ----------
        location_delta: LocationDelta
            LocationDelta to move each point
        """
        for route_point in self.points:
            route_point.move(location_delta)

    def to_xml(self, version=None):
        content = ''
        if self.name:
            content += mod_utils.to_xml('name', content=self.name, escape=True)
        if self.description:
            content += mod_utils.to_xml('desc', content=self.description, escape=True)
        if self.number:
            content += mod_utils.to_xml('number', content=self.number)
        for route_point in self.points:
            content += route_point.to_xml(version)

        return mod_utils.to_xml('rte', content=content)

    def __hash__(self):
        return mod_utils.hash_object(self, 'name', 'description', 'number', 'points')

    def __repr__(self):
        representation = ''
        for attribute in 'name', 'description', 'number':
            value = getattr(self, attribute)
            if value is not None:
                representation += '%s%s=%s' % (', ' if representation else '', attribute, repr(value))
        representation += '%spoints=[%s])' % (', ' if representation else '', '...' if self.points else '')
        return 'GPXRoute(%s)' % representation


class GPXRoutePoint(mod_geo.Location):
    def __init__(self, latitude, longitude, elevation=None, time=None, name=None,
                 description=None, symbol=None, type=None, comment=None,
                 horizontal_dilution=None, vertical_dilution=None,
                 position_dilution=None):

        mod_geo.Location.__init__(self, latitude, longitude, elevation)

        self.time = time
        self.name = name
        self.description = description
        self.symbol = symbol
        self.type = type
        self.comment = comment

        self.horizontal_dilution = horizontal_dilution  # Horizontal dilution of precision
        self.vertical_dilution = vertical_dilution      # Vertical dilution of precision
        self.position_dilution = position_dilution      # Position dilution of precision

    def __str__(self):
        return '[rtept{%s}:%s,%s@%s]' % (self.name, self.latitude, self.longitude, self.elevation)

    def __repr__(self):
        representation = '%s, %s' % (self.latitude, self.longitude)
        for attribute in 'elevation', 'time', 'name', 'description', 'symbol', 'type', 'comment', \
                'horizontal_dilution', 'vertical_dilution', 'position_dilution':
            value = getattr(self, attribute)
            if value is not None:
                representation += ', %s=%s' % (attribute, repr(value))
        return 'GPXRoutePoint(%s)' % representation

    def to_xml(self, version=None):
        content = ''
        if self.elevation is not None:
            content += mod_utils.to_xml('ele', content=self.elevation)
        if self.time:
            content += mod_utils.to_xml('time', content=self.time.strftime(DATE_FORMAT))
        if self.name:
            content += mod_utils.to_xml('name', content=self.name, escape=True)
        if self.comment:
            content += mod_utils.to_xml('cmt', content=self.comment, escape=True)
        if self.description:
            content += mod_utils.to_xml('desc', content=self.description, escape=True)
        if self.symbol:
            content += mod_utils.to_xml('sym', content=self.symbol, escape=True)
        if self.type:
            content += mod_utils.to_xml('type', content=self.type, escape=True)

        if self.horizontal_dilution:
            content += mod_utils.to_xml('hdop', content=self.horizontal_dilution)
        if self.vertical_dilution:
            content += mod_utils.to_xml('vdop', content=self.vertical_dilution)
        if self.position_dilution:
            content += mod_utils.to_xml('pdop', content=self.position_dilution)

        return mod_utils.to_xml('rtept', attributes={'lat': self.latitude, 'lon': self.longitude}, content=content)

    def __hash__(self):
        return mod_utils.hash_object(self, 'time', 'name', 'description', 'symbol', 'type', 'comment',
                                     'horizontal_dilution', 'vertical_dilution', 'position_dilution')


class GPXTrackPoint(mod_geo.Location):
    def __init__(self, latitude, longitude, elevation=None, time=None, symbol=None, comment=None,
                 horizontal_dilution=None, vertical_dilution=None, position_dilution=None, speed=None,
                 name=None):
        mod_geo.Location.__init__(self, latitude, longitude, elevation)

        self.time = time
        self.symbol = symbol
        self.comment = comment
        self.name = name

        self.horizontal_dilution = horizontal_dilution  # Horizontal dilution of precision
        self.vertical_dilution = vertical_dilution      # Vertical dilution of precision
        self.position_dilution = position_dilution      # Position dilution of precision

        self.speed = speed

    def __repr__(self):
        representation = '%s, %s' % (self.latitude, self.longitude)
        for attribute in 'elevation', 'time', 'symbol', 'comment', 'horizontal_dilution', \
                'vertical_dilution', 'position_dilution', 'speed', 'name':
            value = getattr(self, attribute)
            if value is not None:
                representation += ', %s=%s' % (attribute, repr(value))
        return 'GPXTrackPoint(%s)' % representation

    def adjust_time(self, delta):
        """
        Adjusts the time of the point by the specified delta

        Parameters
        ----------
        delta : datetime.timedelta
            Positive time delta will adjust time into the future
            Negative time delta will adjust time into the past
        """

        if self.time:
            self.time += delta

    def remove_time(self):
        """ Will remove time metadata. """
        self.time = None

    def to_xml(self, version=None):
        content = ''

        if self.elevation is not None:
            content += mod_utils.to_xml('ele', content=self.elevation)
        if self.time:
            content += mod_utils.to_xml('time', content=self.time.strftime(DATE_FORMAT))
        if self.comment:
            content += mod_utils.to_xml('cmt', content=self.comment, escape=True)
        if self.name:
            content += mod_utils.to_xml('name', content=self.name, escape=True)
        if self.symbol:
            content += mod_utils.to_xml('sym', content=self.symbol, escape=True)

        if self.horizontal_dilution:
            content += mod_utils.to_xml('hdop', content=self.horizontal_dilution)
        if self.vertical_dilution:
            content += mod_utils.to_xml('vdop', content=self.vertical_dilution)
        if self.position_dilution:
            content += mod_utils.to_xml('pdop', content=self.position_dilution)

        if self.speed:
            content += mod_utils.to_xml('speed', content=self.speed)

        return mod_utils.to_xml('trkpt', {'lat': self.latitude, 'lon': self.longitude}, content=content)

    def time_difference(self, track_point):
        """
        Get time difference between specified point and this point.

        Parameters
        ----------
        track_point : GPXTrackPoint

        Returns
        ----------
        time_difference : float
            Time difference returned in seconds
        """
        if not self.time or not track_point or not track_point.time:
            return None

        time_1 = self.time
        time_2 = track_point.time

        if time_1 == time_2:
            return 0

        if time_1 > time_2:
            delta = time_1 - time_2
        else:
            delta = time_2 - time_1

        return mod_utils.total_seconds(delta)

    def speed_between(self, track_point):
        """
        Compute the speed between specified point and this point.

        NOTE: This is a computed speed, not the GPXTrackPoint speed that comes
              the GPX file.

        Parameters
        ----------
        track_point : GPXTrackPoint

        Returns
        ----------
        speed : float
            Speed returned in meters/second
        """
        if not track_point:
            return None

        seconds = self.time_difference(track_point)
        length = self.distance_3d(track_point)
        if not length:
            length = self.distance_2d(track_point)

        if not seconds or length is None:
            return None

        return length / float(seconds)

    def __str__(self):
        return '[trkpt:%s,%s@%s@%s]' % (self.latitude, self.longitude, self.elevation, self.time)

    def __hash__(self):
        return mod_utils.hash_object(self, 'latitude', 'longitude', 'elevation', 'time', 'symbol', 'comment',
                                     'horizontal_dilution', 'vertical_dilution', 'position_dilution', 'speed')


class GPXTrack:
    def __init__(self, name=None, description=None, number=None):
        self.name = name
        self.description = description
        self.number = number
        # Type is not exactly part of the standard but a is "proposed" and a 
        # lot of application use it:
        self.type = None

        self.segments = []

    def simplify(self, max_distance=None):
        """
        Simplify using the Ramer-Douglas-Peucker algorithm: http://en.wikipedia.org/wiki/Ramer-Douglas-Peucker_algorithm
        """
        for segment in self.segments:
            segment.simplify(max_distance=max_distance)

    def reduce_points(self, min_distance):
        """
        Reduces the number of points in the track. Segment points will be 
        updated in place.

        Parameters
        ----------
        min_distance : float
            The minimum separation in meters between points
        """
        for segment in self.segments:
            segment.reduce_points(min_distance)

    def adjust_time(self, delta):
        """
        Adjusts the time of all segments in the track by the specified delta

        Parameters
        ----------
        delta : datetime.timedelta
            Positive time delta will adjust time into the future
            Negative time delta will adjust time into the past
        """
        for segment in self.segments:
            segment.adjust_time(delta)

    def remove_time(self):
        """ Removes time data for all points in all segments of track. """
        for segment in self.segments:
            segment.remove_time()

    def remove_elevation(self):
        """ Removes elevation data for all points in all segments of track. """
        for segment in self.segments:
            segment.remove_elevation()

    def remove_empty(self):
        """ Removes empty segments in track """
        result = []

        for segment in self.segments:
            if len(segment.points) > 0:
                result.append(segment)

        self.segments = result

    def length_2d(self):
        """ 
        Computes 2-dimensional length (meters) of track (only latitude and
        longitude, no elevation). This is the sum of the 2D length of all
        segments.

        Returns
        ----------
        length : float
            Length returned in meters
        """
        length = 0
        for track_segment in self.segments:
            d = track_segment.length_2d()
            if d:
                length += d
        return length

    def get_time_bounds(self):
        """
        Gets the time bound (start and end) of the track.

        Returns
        ----------
        time_bounds : TimeBounds named tuple
            start_time : datetime
                Start time of the first segment in track
            end time : datetime
                End time of the last segment in track
        """
        start_time = None
        end_time = None

        for track_segment in self.segments:
            point_start_time, point_end_time = track_segment.get_time_bounds()
            if not start_time and point_start_time:
                start_time = point_start_time
            if point_end_time:
                end_time = point_end_time

        return TimeBounds(start_time, end_time)

    def get_bounds(self):
        """
        Gets the latitude and longitude bounds of the track.

        Returns
        ----------
        bounds : Bounds named tuple 
            min_latitude : float
                Minimum latitude of track in decimal degrees [-90, 90]
            max_latitude : float
                Maxium latitude of track in decimal degrees [-90, 90]
            min_longitude : float
                Minium longitude of track in decimal degrees [-180, 180]
            max_longitude : float
                Maxium longitude of track in decimal degrees [-180, 180]
        """
        min_lat = None
        max_lat = None
        min_lon = None
        max_lon = None
        for track_segment in self.segments:
            bounds = track_segment.get_bounds()

            if not mod_utils.is_numeric(min_lat) or (bounds.min_latitude and bounds.min_latitude < min_lat):
                min_lat = bounds.min_latitude
            if not mod_utils.is_numeric(max_lat) or (bounds.max_latitude and bounds.max_latitude > max_lat):
                max_lat = bounds.max_latitude
            if not mod_utils.is_numeric(min_lon) or (bounds.min_longitude and bounds.min_longitude < min_lon):
                min_lon = bounds.min_longitude
            if not mod_utils.is_numeric(max_lon) or (bounds.max_longitude and bounds.max_longitude > max_lon):
                max_lon = bounds.max_longitude

        return Bounds(min_lat, max_lat, min_lon, max_lon)

    def walk(self, only_points=False):
        """
        Generator used to iterates through track

        Parameters
        ----------
        only_point s: boolean
            Only yield points while walking

        Yields
        ----------
        point : GPXTrackPoint
            Point in the track
        segment_no : integer
            Index of segment containint point. This is suppressed if only_points
            is True.
        point_no : integer
            Index of point. This is suppressed if only_points is True.
        """
        for segment_no, segment in enumerate(self.segments):
            for point_no, point in enumerate(segment.points):
                if only_points:
                    yield point
                else:
                    yield point, segment_no, point_no

    def get_points_no(self):
        """
        Get the number of points in all segments in the track.

        Returns
        ----------
        num_points : integer
            Number of points in track
        """
        result = 0

        for track_segment in self.segments:
            result += track_segment.get_points_no()

        return result

    def length_3d(self):
        """ 
        Computes 3-dimensional length of track (latitude, longitude, and
        elevation). This is the sum of the 3D length of all segments.

        Returns
        ----------
        length : float
            Length returned in meters
        """
        length = 0
        for track_segment in self.segments:
            d = track_segment.length_3d()
            if d:
                length += d
        return length

    def split(self, track_segment_no, track_point_no):
        """ 
        Splits one of the segments in the track in two parts. If one of the 
        split segments is empty it will not be added in the result. The 
        segments will be split in place.

        Parameters
        ----------
        track_segment_no : integer
            The index of the segment to split
        track_point_no : integer
            The index of the track point in the segment to split
        """
        new_segments = []
        for i in range(len(self.segments)):
            segment = self.segments[i]
            if i == track_segment_no:
                segment_1, segment_2 = segment.split(track_point_no)
                if segment_1:
                    new_segments.append(segment_1)
                if segment_2:
                    new_segments.append(segment_2)
            else:
                new_segments.append(segment)
        self.segments = new_segments

    def join(self, track_segment_no, track_segment_no_2=None):
        """ 
        Joins two segments of this track. The segments will be split in place.

        Parameters
        ----------
        track_segment_no : integer
            The index of the first segment to join
        track_segment_no_2 : integer
            The index of second segment to join. If track_segment_no_2 is not 
            provided,the join will be with the next segment after 
            track_segment_no.
        """
        if not track_segment_no_2:
            track_segment_no_2 = track_segment_no + 1

        if track_segment_no_2 >= len(self.segments):
            return

        new_segments = []
        for i in range(len(self.segments)):
            segment = self.segments[i]
            if i == track_segment_no:
                second_segment = self.segments[track_segment_no_2]
                segment.join(second_segment)

                new_segments.append(segment)
            elif i == track_segment_no_2:
                # Nothing, it is already joined
                pass
            else:
                new_segments.append(segment)
        self.segments = new_segments

    def get_moving_data(self, stopped_speed_threshold=None):
        """
        Return a tuple of (moving_time, stopped_time, moving_distance, 
        stopped_distance, max_speed) that may be used for detecting the time 
        stopped, and max speed. Not that those values are not absolutely true, 
        because the "stopped" or "moving" information aren't saved in the track.

        Because of errors in the GPS recording, it may be good to calculate 
        them on a reduced and smoothed version of the track.

        Parameters
        ----------
        stopped_speed_threshold : float
            speeds (km/h) below this threshold are treated as if having no
            movement. Default is 1 km/h.

        Returns
        ----------
        moving_data : MovingData : named tuple
            moving_time : float
                time (seconds) of track in which movement was occuring
            stopped_time : float
                time (seconds) of track in which no movement was occuring
            stopped_distance : float
                distance (meters) travelled during stopped times
            moving_distance : float
                distance (meters) travelled during moving times
            max_speed : float
                Maximum speed (m/s) during the track.
        """
        moving_time = 0.
        stopped_time = 0.

        moving_distance = 0.
        stopped_distance = 0.

        max_speed = 0.

        for segment in self.segments:
            track_moving_time, track_stopped_time, track_moving_distance, track_stopped_distance, track_max_speed = segment.get_moving_data(stopped_speed_threshold)
            moving_time += track_moving_time
            stopped_time += track_stopped_time
            moving_distance += track_moving_distance
            stopped_distance += track_stopped_distance

            if track_max_speed is not None and track_max_speed > max_speed:
                max_speed = track_max_speed

        return MovingData(moving_time, stopped_time, moving_distance, stopped_distance, max_speed)

    def add_elevation(self, delta):
        """
        Adjusts elevation data for track.

        Parameters
        ----------
        delta : float
            Elevation delta in meters to apply to track
        """
        for track_segment in self.segments:
            track_segment.add_elevation(delta)

    def add_missing_data(self, get_data_function, add_missing_function):
        for track_segment in self.segments:
            track_segment.add_missing_data(get_data_function, add_missing_function)

    def move(self, location_delta):
        """
        Moves each point in the track.

        Parameters
        ----------
        location_delta: LocationDelta object
            Delta (distance/angle or lat/lon offset to apply each point in each 
            segment of the track
        """
        for track_segment in self.segments:
            track_segment.move(location_delta)

    def get_duration(self):
        """
        Calculates duration or track
        
        Returns
        -------
        duration: float
            Duration in seconds or None if any time data is missing
        """
        if not self.segments:
            return 0

        result = 0
        for track_segment in self.segments:
            duration = track_segment.get_duration()
            if duration or duration == 0:
                result += duration
            elif duration is None:
                return None

        return result

    def get_uphill_downhill(self):
        """
        Calculates the uphill and downhill elevation climbs for the track. 
        If elevation for some points is not found those are simply ignored.

        Returns
        -------
        uphill_downhill: UphillDownhill named tuple
            uphill: float
                Uphill elevation climbs in meters
            downhill: float
                Downhill elevation descent in meters
        """
        if not self.segments:
            return UphillDownhill(0, 0)

        uphill = 0
        downhill = 0

        for track_segment in self.segments:
            current_uphill, current_downhill = track_segment.get_uphill_downhill()

            uphill += current_uphill
            downhill += current_downhill

        return UphillDownhill(uphill, downhill)

    def get_location_at(self, time):
        """
        Gets approx. location at given time. Note that, at the moment this 
        method returns an instance of GPXTrackPoint in the future -- this may
        be a mod_geo.Location instance with approximated latitude, longitude 
        and elevation!
        """
        result = []
        for track_segment in self.segments:
            location = track_segment.get_location_at(time)
            if location:
                result.append(location)

        return result

    def get_elevation_extremes(self):
        """ 
        Calculate elevation extremes of track

        Returns
        -------
        min_max_elevation: MinimumMaximum named tuple
            minimum: float
                Minimum elevation in meters
            maximum: float
                Maximum elevation in meters
        """
        if not self.segments:
            return MinimumMaximum(None, None)

        elevations = []

        for track_segment in self.segments:
            (_min, _max) = track_segment.get_elevation_extremes()
            if _min is not None:
                elevations.append(_min)
            if _max is not None:
                elevations.append(_max)

        if len(elevations) == 0:
            return MinimumMaximum(None, None)

        return MinimumMaximum(min(elevations), max(elevations))

    def to_xml(self, version=None):
        content = mod_utils.to_xml('name', content=self.name, escape=True)
        content += mod_utils.to_xml('type', content=self.type, escape=True)
        content += mod_utils.to_xml('desc', content=self.description, escape=True)
        if self.number:
            content += mod_utils.to_xml('number', content=self.number)
        for track_segment in self.segments:
            content += track_segment.to_xml(version)

        return mod_utils.to_xml('trk', content=content)

    def get_center(self):
        """
        Get the center of the route.

        Returns
        -------
        center: Location
            latitude: latitude of center in degrees
            longitude: longitude of center in degrees
            elevation: not calculated here
        """
        if not self.segments:
            return None
        sum_lat = 0
        sum_lon = 0
        n = 0
        for track_segment in self.segments:
            for point in track_segment.points:
                n += 1.
                sum_lat += point.latitude
                sum_lon += point.longitude

        if not n:
            return mod_geo.Location(float(0), float(0))

        return mod_geo.Location(latitude=sum_lat / n, longitude=sum_lon / n)

    def smooth(self, vertical=True, horizontal=False, remove_extremes=False):
        """ See: GPXTrackSegment.smooth() """
        for track_segment in self.segments:
            track_segment.smooth(vertical, horizontal, remove_extremes)

    def has_times(self):
        """ See GPXTrackSegment.has_times() """
        if not self.segments:
            return None

        result = True
        for track_segment in self.segments:
            result = result and track_segment.has_times()

        return result

    def has_elevations(self):
        """ Returns true if track data has elevation for all segments """
        if not self.segments:
            return None

        result = True
        for track_segment in self.segments:
            result = result and track_segment.has_elevations()

        return result

    def get_nearest_location(self, location):
        """ Returns (location, track_segment_no, track_point_no) for nearest location on track """
        if not self.segments:
            return None

        result = None
        distance = None
        result_track_segment_no = None
        result_track_point_no = None

        for i in range(len(self.segments)):
            track_segment = self.segments[i]
            nearest_location, track_point_no = track_segment.get_nearest_location(location)
            nearest_location_distance = None
            if nearest_location:
                nearest_location_distance = nearest_location.distance_2d(location)

            if not distance or nearest_location_distance < distance:
                if nearest_location:
                    distance = nearest_location_distance
                    result = nearest_location
                    result_track_segment_no = i
                    result_track_point_no = track_point_no

        return result, result_track_segment_no, result_track_point_no

    def clone(self):
        return mod_copy.deepcopy(self)

    def __hash__(self):
        return mod_utils.hash_object(self, 'name', 'description', 'number', 'segments')

    def __repr__(self):
        representation = ''
        for attribute in 'name', 'description', 'number':
            value = getattr(self, attribute)
            if value is not None:
                representation += '%s%s=%s' % (', ' if representation else '', attribute, repr(value))
        representation += '%ssegments=%s' % (', ' if representation else '', repr(self.segments))
        return 'GPXTrack(%s)' % representation

class GPXTrackSegment:
    def __init__(self, points=None):
        self.points = points if points else []

    def simplify(self, max_distance=None):
        """
        Simplify using the Ramer-Douglas-Peucker algorithm: http://en.wikipedia.org/wiki/Ramer-Douglas-Peucker_algorithm
        """
        if not max_distance:
            max_distance = 10

        self.points = mod_geo.simplify_polyline(self.points, max_distance)

    def reduce_points(self, min_distance):
        """
        Reduces the number of points in the track segment. Segment points will
        be updated in place.

        Parameters
        ----------
        min_distance : float
            The minimum separation in meters between points
        """

        reduced_points = []
        for point in self.points:
            if reduced_points:
                distance = reduced_points[-1].distance_3d(point)
                if distance >= min_distance:
                    reduced_points.append(point)
            else:
                # Leave first point:
                reduced_points.append(point)

        self.points = reduced_points

    def _find_next_simplified_point(self, pos, max_distance):
        for candidate in range(pos + 1, len(self.points) - 1):
            for i in range(pos + 1, candidate):
                d = mod_geo.distance_from_line(self.points[i],
                                               self.points[pos],
                                               self.points[candidate])
                if d > max_distance:
                    return candidate - 1
        return None

    def adjust_time(self, delta):
        """
        Adjusts the time of all points in the segment by the specified delta

        Parameters
        ----------
        delta : datetime.timedelta
            Positive time delta will adjust point times into the future
            Negative time delta will adjust point times into the past
        """
        for track_point in self.points:
            track_point.adjust_time(delta)

    def remove_time(self):
        """ Removes time data for all points in the segment. """
        for track_point in self.points:
            track_point.remove_time()

    def remove_elevation(self):
        """ Removes elevation data for all points in the segment. """
        for track_point in self.points:
            track_point.remove_elevation()

    def length_2d(self):
        """ 
        Computes 2-dimensional length (meters) of segment (only latitude and
        longitude, no elevation).

        Returns
        ----------
        length : float
            Length returned in meters
        """
        return mod_geo.length_2d(self.points)

    def length_3d(self):
        """ 
        Computes 3-dimensional length of segment (latitude, longitude, and 
        elevation).

        Returns
        ----------
        length : float
            Length returned in meters
        """
        return mod_geo.length_3d(self.points)

    def move(self, location_delta):
        """
        Moves each point in the segment.

        Parameters
        ----------
        location_delta: LocationDelta object
            Delta (distance/angle or lat/lon offset to apply each point in the 
            segment
        """
        for track_point in self.points:
            track_point.move(location_delta)

    def walk(self, only_points=False):
        """
        Generator for iterating over segment points

        Parameters
        ----------
        only_points: boolean
            Only yield points (no index yielded)

        Yields
        ------
        point: GPXTrackPoint
            A point in the sement
        point_no: int 
            Not included in yield if only_points is true
        """
        for point_no, point in enumerate(self.points):
            if only_points:
                yield point
            else:
                yield point, point_no

    def get_points_no(self):
        """
        Gets the number of points in segment.

        Returns
        ----------
        num_points : integer
            Number of points in segment
        """
        if not self.points:
            return 0
        return len(self.points)

    def split(self, point_no):
        """ 
        Splits the segment into two parts. If one of the split segments is 
        empty it will not be added in the result. The segments will be split 
        in place.

        Parameters
        ----------
        point_no : integer
            The index of the track point in the segment to split
        """
        part_1 = self.points[:point_no + 1]
        part_2 = self.points[point_no + 1:]
        return GPXTrackSegment(part_1), GPXTrackSegment(part_2)

    def join(self, track_segment):
        """ Joins with another segment """
        self.points += track_segment.points

    def remove_point(self, point_no):
        """ Removes a point specificed by index from the segment """
        if point_no < 0 or point_no >= len(self.points):
            return

        part_1 = self.points[:point_no]
        part_2 = self.points[point_no + 1:]

        self.points = part_1 + part_2

    def get_moving_data(self, stopped_speed_threshold=None):
        """
        Return a tuple of (moving_time, stopped_time, moving_distance, 
        stopped_distance, max_speed) that may be used for detecting the time 
        stopped, and max speed. Not that those values are not absolutely true, 
        because the "stopped" or "moving" information aren't saved in the segment.

        Because of errors in the GPS recording, it may be good to calculate 
        them on a reduced and smoothed version of the track.

        Parameters
        ----------
        stopped_speed_threshold : float
            speeds (km/h) below this threshold are treated as if having no
            movement. Default is 1 km/h.

        Returns
        ----------
        moving_data : MovingData : named tuple
            moving_time : float
                time (seconds) of segment in which movement was occuring
            stopped_time : float
                time (seconds) of segment in which no movement was occuring
            stopped_distance : float
                distance (meters) travelled during stopped times
            moving_distance : float
                distance (meters) travelled during moving times
            max_speed : float
                Maximum speed (m/s) during the segment.
        """
        if not stopped_speed_threshold:
            stopped_speed_threshold = DEFAULT_STOPPED_SPEED_THRESHOLD

        moving_time = 0.
        stopped_time = 0.

        moving_distance = 0.
        stopped_distance = 0.

        speeds_and_distances = []

        for i in range(1, len(self.points)):

            previous = self.points[i - 1]
            point = self.points[i]

            # Won't compute max_speed for first and last because of common GPS
            # recording errors, and because smoothing don't work well for those
            # points:
            first_or_last = i in [0, 1, len(self.points) - 1]
            if point.time and previous.time:
                timedelta = point.time - previous.time

                if point.elevation and previous.elevation:
                    distance = point.distance_3d(previous)
                else:
                    distance = point.distance_2d(previous)

                seconds = mod_utils.total_seconds(timedelta)
                speed_kmh = 0
                if seconds > 0:
                    # TODO: compute treshold in m/s instead this to kmh every time:
                    speed_kmh = (distance / 1000.) / (mod_utils.total_seconds(timedelta) / 60. ** 2)

                #print speed, stopped_speed_threshold
                if speed_kmh <= stopped_speed_threshold:
                    stopped_time += mod_utils.total_seconds(timedelta)
                    stopped_distance += distance
                else:
                    moving_time += mod_utils.total_seconds(timedelta)
                    moving_distance += distance

                    if distance and moving_time:
                        speeds_and_distances.append((distance / mod_utils.total_seconds(timedelta), distance, ))

        max_speed = None
        if speeds_and_distances:
            max_speed = mod_geo.calculate_max_speed(speeds_and_distances)

        return MovingData(moving_time, stopped_time, moving_distance, stopped_distance, max_speed)

    def get_time_bounds(self):
        """
        Gets the time bound (start and end) of the segment.

        returns
        ----------
        time_bounds : TimeBounds named tuple
            start_time : datetime
                Start time of the first segment in track
            end time : datetime
                End time of the last segment in track
        """
        start_time = None
        end_time = None

        for point in self.points:
            if point.time:
                if not start_time:
                    start_time = point.time
                if point.time:
                    end_time = point.time

        return TimeBounds(start_time, end_time)

    def get_bounds(self):
        """
        Gets the latitude and longitude bounds of the segment.

        Returns
        ----------
        bounds : Bounds named tuple 
            min_latitude : float
                Minimum latitude of segment in decimal degrees [-90, 90]
            max_latitude : float
                Maxium latitude of segment in decimal degrees [-90, 90]
            min_longitude : float
                Minium longitude of segment in decimal degrees [-180, 180]
            max_longitude : float
                Maxium longitude of segment in decimal degrees [-180, 180]
        """
        min_lat = None
        max_lat = None
        min_lon = None
        max_lon = None

        for point in self.points:
            if min_lat is None or point.latitude < min_lat:
                min_lat = point.latitude
            if max_lat is None or point.latitude > max_lat:
                max_lat = point.latitude
            if min_lon is None or point.longitude < min_lon:
                min_lon = point.longitude
            if max_lon is None or point.longitude > max_lon:
                max_lon = point.longitude

        return Bounds(min_lat, max_lat, min_lon, max_lon)

    def get_speed(self, point_no):
        """
        Computes the speed at the specified point index.

        Parameters
        ----------
        point_no : integer
            index of the point used to compute speed

        Returns
        ----------
        speed : float 
            Speed returned in m/s
        """
        point = self.points[point_no]

        previous_point = None
        next_point = None

        if 0 < point_no < len(self.points):
            previous_point = self.points[point_no - 1]
        if 0 < point_no < len(self.points) - 1:
            next_point = self.points[point_no + 1]

        #mod_logging.debug('previous: %s' % previous_point)
        #mod_logging.debug('next: %s' % next_point)

        speed_1 = point.speed_between(previous_point)
        speed_2 = point.speed_between(next_point)

        if speed_1:
            speed_1 = abs(speed_1)
        if speed_2:
            speed_2 = abs(speed_2)

        if speed_1 and speed_2:
            return (speed_1 + speed_2) / 2.

        if speed_1:
            return speed_1

        return speed_2

    def add_elevation(self, delta):
        """
        Adjusts elevation data for segment.

        Parameters
        ----------
        delta : float
            Elevation delta in meters to apply to track
        """
        mod_logging.debug('delta = %s' % delta)

        if not delta:
            return

        for track_point in self.points:
            if track_point.elevation is not None:
                track_point.elevation += delta

    def add_missing_data(self, get_data_function, add_missing_function):
        if not get_data_function:
            raise GPXException('Invalid get_data_function: %s' % get_data_function)
        if not add_missing_function:
            raise GPXException('Invalid add_missing_function: %s' % add_missing_function)

        # Points between two points *without* data:
        interval = []
        # Points before and after the interval *with* data:
        start_point = None

        previous_point = None
        for track_point in self.points:
            data = get_data_function(track_point)
            if data is None and previous_point:
                if not start_point:
                    start_point = previous_point
                interval.append(track_point)
            else:
                if interval:
                    distances_ratios = self._get_interval_distances_ratios(interval,
                                                                           start_point, track_point)
                    add_missing_function(interval, start_point, track_point,
                                         distances_ratios)
                    start_point = None
                    interval = []
            previous_point = track_point

    def _get_interval_distances_ratios(self, interval, start, end):
        assert start, start
        assert end, end
        assert interval, interval
        assert len(interval) > 0, interval

        distances = []
        distance_from_start = 0
        previous_point = start
        for point in interval:
            distance_from_start += float(point.distance_3d(previous_point))
            distances.append(distance_from_start)
            previous_point = point

        from_start_to_end = distances[-1] + interval[-1].distance_3d(end)

        assert len(interval) == len(distances)

        return list(map(
                lambda distance: (distance / from_start_to_end) if from_start_to_end else 0,
                distances))

    def get_duration(self):
        """
        Calculates duration or track segment
        
        Returns
        -------
        duration: float
            Duration in seconds
        """
        if not self.points or len(self.points) < 2:
            return 0

        # Search for start:
        first = self.points[0]
        if not first.time:
            first = self.points[1]

        last = self.points[-1]
        if not last.time:
            last = self.points[-2]

        if not last.time or not first.time:
            mod_logging.debug('Can\'t find time')
            return None

        if last.time < first.time:
            mod_logging.debug('Not enough time data')
            return None

        return mod_utils.total_seconds(last.time - first.time)

    def get_uphill_downhill(self):
        """
        Calculates the uphill and downhill elevation climbs for the track
        segment. If elevation for some points is not found those are simply
        ignored.

        Returns
        -------
        uphill_downhill: UphillDownhill named tuple
            uphill: float
                Uphill elevation climbs in meters
            downhill: float
                Downhill elevation descent in meters
        """
        if not self.points:
            return UphillDownhill(0, 0)

        elevations = list(map(lambda point: point.elevation, self.points))
        uphill, downhill = mod_geo.calculate_uphill_downhill(elevations)

        return UphillDownhill(uphill, downhill)

    def get_elevation_extremes(self):
        """ 
        Calculate elevation extremes of track segment

        Returns
        -------
        min_max_elevation: MinimumMaximum named tuple
            minimum: float
                Minimum elevation in meters
            maximum: float
                Maximum elevation in meters
        """

        if not self.points:
            return MinimumMaximum(None, None)

        elevations = map(lambda location: location.elevation, self.points)
        elevations = filter(lambda elevation: elevation is not None, elevations)
        elevations = list(elevations)

        if len(elevations) == 0:
            return MinimumMaximum(None, None)

        return MinimumMaximum(min(elevations), max(elevations))

    def get_location_at(self, time):
        """
        Gets approx. location at given time. Note that, at the moment this 
        method returns an instance of GPXTrackPoint in the future -- this may
        be a mod_geo.Location instance with approximated latitude, longitude 
        and elevation!
        """
        if not self.points:
            return None

        if not time:
            return None

        first_time = self.points[0].time
        last_time = self.points[-1].time

        if not first_time and not last_time:
            mod_logging.debug('No times for track segment')
            return None

        if not first_time <= time <= last_time:
            mod_logging.debug('Not in track (search for:%s, start:%s, end:%s)' % (time, first_time, last_time))
            return None

        for point in self.points:
            if point.time and time <= point.time:
                # TODO: If between two points -- approx position!
                # return mod_geo.Location(point.latitude, point.longitude)
                return point

    def to_xml(self, version=None):
        content = ''
        for track_point in self.points:
            content += track_point.to_xml(version)
        return mod_utils.to_xml('trkseg', content=content)

    def get_nearest_location(self, location):
        """ Return the (location, track_point_no) on this track segment """
        if not self.points:
            return None, None

        result = None
        current_distance = None
        result_track_point_no = None
        for i in range(len(self.points)):
            track_point = self.points[i]
            if not result:
                result = track_point
            else:
                distance = track_point.distance_2d(location)
                #print current_distance, distance
                if not current_distance or distance < current_distance:
                    current_distance = distance
                    result = track_point
                    result_track_point_no = i

        return result, result_track_point_no

    def smooth(self, vertical=True, horizontal=False, remove_extremes=False):
        """ "Smooths" the elevation graph. Can be called multiple times. """
        if len(self.points) <= 3:
            return

        elevations = []
        latitudes = []
        longitudes = []

        for point in self.points:
            elevations.append(point.elevation)
            latitudes.append(point.latitude)
            longitudes.append(point.longitude)

        avg_distance = 0
        avg_elevation_delta = 1
        if remove_extremes:
            # compute the average distance between two points:
            distances = []
            elevations_delta = []
            for i in range(len(self.points))[1:]:
                distances.append(self.points[i].distance_2d(self.points[i - 1]))
                elevation_1 = self.points[i].elevation
                elevation_2 = self.points[i - 1].elevation
                if elevation_1 is not None and elevation_2 is not None:
                    elevations_delta.append(abs(elevation_1 - elevation_2))
            if distances:
                avg_distance = 1.0 * sum(distances) / len(distances)
            if elevations_delta:
                avg_elevation_delta = 1.0 * sum(elevations_delta) / len(elevations_delta)

        # If The point moved more than this number * the average distance between two
        # points -- then is a candidate for deletion:
        # TODO: Make this a method parameter
        remove_2d_extremes_threshold = 1.75 * avg_distance
        remove_elevation_extremes_threshold = avg_elevation_delta * 5  # TODO: Param

        new_track_points = [self.points[0]]

        for i in range(len(self.points))[1:-1]:
            new_point = None
            point_removed = False
            if vertical and elevations[i - 1] and elevations[i] and elevations[i + 1]:
                old_elevation = self.points[i].elevation
                new_elevation = SMOOTHING_RATIO[0] * elevations[i - 1] + \
                    SMOOTHING_RATIO[1] * elevations[i] + \
                    SMOOTHING_RATIO[2] * elevations[i + 1]

                if not remove_extremes:
                    self.points[i].elevation = new_elevation

                if remove_extremes:
                    # The point must be enough distant to *both* neighbours:
                    d1 = abs(old_elevation - elevations[i - 1])
                    d2 = abs(old_elevation - elevations[i + 1])
                    #print d1, d2, remove_2d_extremes_threshold

                    # TODO: Remove extremes threshold is meant only for 2D, elevation must be
                    # computed in different way!
                    if min(d1, d2) < remove_elevation_extremes_threshold and abs(old_elevation - new_elevation) < remove_2d_extremes_threshold:
                        new_point = self.points[i]
                    else:
                        #print 'removed elevation'
                        point_removed = True
                else:
                    new_point = self.points[i]
            else:
                new_point = self.points[i]

            if horizontal:
                old_latitude = self.points[i].latitude
                new_latitude = SMOOTHING_RATIO[0] * latitudes[i - 1] + \
                    SMOOTHING_RATIO[1] * latitudes[i] + \
                    SMOOTHING_RATIO[2] * latitudes[i + 1]
                old_longitude = self.points[i].longitude
                new_longitude = SMOOTHING_RATIO[0] * longitudes[i - 1] + \
                    SMOOTHING_RATIO[1] * longitudes[i] + \
                    SMOOTHING_RATIO[2] * longitudes[i + 1]

                if not remove_extremes:
                    self.points[i].latitude = new_latitude
                    self.points[i].longitude = new_longitude

                # TODO: This is not ideal.. Because if there are points A, B and C on the same
                # line but B is very close to C... This would remove B (and possibly) A even though
                # it is not an extreme. This is the reason for this algorithm:
                d1 = mod_geo.distance(latitudes[i - 1], longitudes[i - 1], None, latitudes[i], longitudes[i], None)
                d2 = mod_geo.distance(latitudes[i + 1], longitudes[i + 1], None, latitudes[i], longitudes[i], None)
                d = mod_geo.distance(latitudes[i - 1], longitudes[i - 1], None, latitudes[i + 1], longitudes[i + 1], None)

                #print d1, d2, d, remove_extremes

                if d1 + d2 > d * 1.5 and remove_extremes:
                    d = mod_geo.distance(old_latitude, old_longitude, None, new_latitude, new_longitude, None)
                    #print "d, threshold = ", d, remove_2d_extremes_threshold
                    if d < remove_2d_extremes_threshold:
                        new_point = self.points[i]
                    else:
                        #print 'removed 2d'
                        point_removed = True
                else:
                    new_point = self.points[i]

            if new_point and not point_removed:
                new_track_points.append(new_point)

        new_track_points.append(self.points[- 1])

        #print 'len=', len(new_track_points)

        self.points = new_track_points

    def has_times(self):
        """
        Returns if points in this segment contains timestamps.

        The first point, the last point, and 75% of the points must have times 
        for this method to return true.
        """
        if not self.points:
            return True
            # ... or otherwise one empty track segment would change the entire
            # track's "has_times" status!

        found = 0
        for track_point in self.points:
            if track_point.time:
                found += 1

        return len(self.points) > 2 and float(found) / float(len(self.points)) > .75

    def has_elevations(self):
        """
        Returns if points in this segment contains elevation.

        The first point, the last point, and at least 75% of the points must 
        have elevation for this method to return true.
        """
        if not self.points:
            return True
            # ... or otherwise one empty track segment would change the entire
            # track's "has_times" status!

        found = 0
        for track_point in self.points:
            if track_point.elevation:
                found += 1

        return len(self.points) > 2 and float(found) / float(len(self.points)) > .75

    def __hash__(self):
        return mod_utils.hash_object(self, 'points')

    def __repr__(self):
        return 'GPXTrackSegment(points=[%s])' % ('...' if self.points else '')

    def clone(self):
        return mod_copy.deepcopy(self)


class GPX:
    def __init__(self, waypoints=None, routes=None, tracks=None):
        if waypoints:
            self.waypoints = waypoints
        else:
            self.waypoints = []

        if routes:
            self.routes = routes
        else:
            self.routes = []

        if tracks:
            self.tracks = tracks
        else:
            self.tracks = []

        self.name = None
        self.description = None
        self.author = None
        self.email = None
        self.url = None
        self.urlname = None
        self.time = None
        self.keywords = None
        self.creator = None

        self.min_latitude = None
        self.max_latitude = None
        self.min_longitude = None
        self.max_longitude = None

    def simplify(self, max_distance=None):
        """
        Simplify using the Ramer-Douglas-Peucker algorithm: http://en.wikipedia.org/wiki/Ramer-Douglas-Peucker_algorithm
        """
        for track in self.tracks:
            track.simplify(max_distance=max_distance)

    def reduce_points(self, max_points_no=None, min_distance=None):
        """
        Reduces the number of points. Points will be updated in place.

        Parameters
        ----------

        max_points : int
            The maximum number of points to include in the GPX
        min_distance : float
            The minimum separation in meters between points
        """

        if max_points_no is None and min_distance is None:
            raise ValueError("Either max_point_no or min_distance must be supplied")

        if max_points_no is not None and max_points_no < 2:
            raise ValueError("max_points_no must be greater than or equal to 2")

        points_no = len(list(self.walk()))
        if max_points_no is not None and points_no <= max_points_no:
            # No need to reduce points only if no min_distance is specified:
            if not min_distance:
                return

        length = self.length_3d()

        min_distance = min_distance or 0
        max_points_no = max_points_no or 1000000000

        min_distance = max(min_distance, mod_math.ceil(length / float(max_points_no)))

        for track in self.tracks:
            track.reduce_points(min_distance)

        # TODO
        mod_logging.debug('Track reduced to %s points' % self.get_track_points_no())

    def adjust_time(self, delta):
        """
        Adjusts the time of all points in all of the segments of all tracks by 
        the specified delta.

        Parameters
        ----------
        delta : datetime.timedelta
            Positive time delta will adjust times into the future
            Negative time delta will adjust times into the past
        """
        for track in self.tracks:
            track.adjust_time(delta)

    def remove_time(self):
        """ Removes time data. """
        for track in self.tracks:
            track.remove_time()

    def remove_elevation(self, tracks=True, routes=False, waypoints=False):
        """ Removes elevation data. """
        if tracks:
            for track in self.tracks:
                track.remove_elevation()
        if routes:
            for route in self.routes:
                route.remove_elevation()
        if waypoints:
            for waypoint in self.waypoints:
                waypoint.remove_elevation()

    def get_time_bounds(self):
        """
        Gets the time bounds (start and end) of the GPX file.

        Returns
        ----------
        time_bounds : TimeBounds named tuple
            start_time : datetime
                Start time of the first segment in track
            end time : datetime
                End time of the last segment in track
        """
        start_time = None
        end_time = None

        for track in self.tracks:
            track_start_time, track_end_time = track.get_time_bounds()
            if not start_time:
                start_time = track_start_time
            if track_end_time:
                end_time = track_end_time

        return TimeBounds(start_time, end_time)

    def get_bounds(self):
        """
        Gets the latitude and longitude bounds of the GPX file.

        Returns
        ----------
        bounds : Bounds named tuple 
            min_latitude : float
                Minimum latitude of track in decimal degrees [-90, 90]
            max_latitude : float
                Maxium latitude of track in decimal degrees [-90, 90]
            min_longitude : float
                Minium longitude of track in decimal degrees [-180, 180]
            max_longitude : float
                Maxium longitude of track in decimal degrees [-180, 180]
        """
        min_lat = None
        max_lat = None
        min_lon = None
        max_lon = None
        for track in self.tracks:
            bounds = track.get_bounds()

            if not mod_utils.is_numeric(min_lat) or bounds.min_latitude < min_lat:
                min_lat = bounds.min_latitude
            if not mod_utils.is_numeric(max_lat) or bounds.max_latitude > max_lat:
                max_lat = bounds.max_latitude
            if not mod_utils.is_numeric(min_lon) or bounds.min_longitude < min_lon:
                min_lon = bounds.min_longitude
            if not mod_utils.is_numeric(max_lon) or bounds.max_longitude > max_lon:
                max_lon = bounds.max_longitude

        return Bounds(min_lat, max_lat, min_lon, max_lon)

    def get_points_no(self):
        """
        Get the number of points in all segments of all track.

        Returns
        ----------
        num_points : integer
            Number of points in GPX
        """
        result = 0
        for track in self.tracks:
            result += track.get_points_no()
        return result

    def refresh_bounds(self):
        """
        Compute bounds and reload min_latitude, max_latitude, min_longitude 
        and max_longitude properties of this object
        """

        bounds = self.get_bounds()

        self.min_latitude = bounds.min_latitude
        self.max_latitude = bounds.max_latitude
        self.min_longitude = bounds.min_longitude
        self.max_longitude = bounds.max_longitude

    def smooth(self, vertical=True, horizontal=False, remove_extremes=False):
        """ See GPXTrackSegment.smooth(...) """
        for track in self.tracks:
            track.smooth(vertical=vertical, horizontal=horizontal, remove_extremes=remove_extremes)

    def remove_empty(self):
        """ Removes segments, routes """

        routes = []

        for route in self.routes:
            if len(route.points) > 0:
                routes.append(route)

        self.routes = routes

        for track in self.tracks:
            track.remove_empty()

    def get_moving_data(self, stopped_speed_threshold=None):
        """
        Return a tuple of (moving_time, stopped_time, moving_distance, stopped_distance, max_speed)
        that may be used for detecting the time stopped, and max speed. Not that those values are not
        absolutely true, because the "stopped" or "moving" information aren't saved in the track.

        Because of errors in the GPS recording, it may be good to calculate them on a reduced and
        smoothed version of the track. Something like this:

        cloned_gpx = gpx.clone()
        cloned_gpx.reduce_points(2000, min_distance=10)
        cloned_gpx.smooth(vertical=True, horizontal=True)
        cloned_gpx.smooth(vertical=True, horizontal=False)
        moving_time, stopped_time, moving_distance, stopped_distance, max_speed_ms = cloned_gpx.get_moving_data
        max_speed_kmh = max_speed_ms * 60. ** 2 / 1000.

        Experiment with your own variations to get the values you expect.

        Max speed is in m/s.
        """
        moving_time = 0.
        stopped_time = 0.

        moving_distance = 0.
        stopped_distance = 0.

        max_speed = 0.

        for track in self.tracks:
            track_moving_time, track_stopped_time, track_moving_distance, track_stopped_distance, track_max_speed = track.get_moving_data(stopped_speed_threshold)
            moving_time += track_moving_time
            stopped_time += track_stopped_time
            moving_distance += track_moving_distance
            stopped_distance += track_stopped_distance

            if track_max_speed > max_speed:
                max_speed = track_max_speed

        return MovingData(moving_time, stopped_time, moving_distance, stopped_distance, max_speed)

    def split(self, track_no, track_segment_no, track_point_no):
        """ 
        Splits one of the segments of a track in two parts. If one of the 
        split segments is empty it will not be added in the result. The 
        segments will be split in place.

        Parameters
        ----------
        track_no : integer
            The index of the track to split
        track_segment_no : integer
            The index of the segment to split
        track_point_no : integer
            The index of the track point in the segment to split
        """
        track = self.tracks[track_no]

        track.split(track_segment_no=track_segment_no, track_point_no=track_point_no)

    def length_2d(self):
        """ 
        Computes 2-dimensional length of the GPX file (only latitude and 
        longitude, no elevation). This is the sum of 3D length of all segments
        in all tracks.

        Returns
        ----------
        length : float
            Length returned in meters
        """
        result = 0
        for track in self.tracks:
            length = track.length_2d()
            if length or length == 0:
                result += length
        return result

    def length_3d(self):
        """ 
        Computes 3-dimensional length of the GPX file (latitude, longitude, and 
        elevation). This is the sum of 3D length of all segments in all tracks.

        Returns
        ----------
        length : float
            Length returned in meters
        """
        result = 0
        for track in self.tracks:
            length = track.length_3d()
            if length or length == 0:
                result += length
        return result

    def walk(self, only_points=False):
        """
        Generator used to iterates through points in GPX file

        Parameters
        ----------
        only_point s: boolean
            Only yield points while walking

        Yields
        ----------
        point : GPXTrackPoint
            Point in the track
        track_no : integer
            Index of track containint point. This is suppressed if only_points
            is True.
        segment_no : integer
            Index of segment containint point. This is suppressed if only_points
            is True.
        point_no : integer
            Index of point. This is suppressed if only_points is True.
        """
        for track_no, track in enumerate(self.tracks):
            for segment_no, segment in enumerate(track.segments):
                for point_no, point in enumerate(segment.points):
                    if only_points:
                        yield point
                    else:
                        yield point, track_no, segment_no, point_no

    def get_track_points_no(self):
        """ Number of track points, *without* route and waypoints """
        result = 0

        for track in self.tracks:
            for segment in track.segments:
                result += len(segment.points)

        return result

    def get_duration(self):
        """
        Calculates duration of GPX file
        
        Returns
        -------
        duration: float
            Duration in seconds or None if time data is not fully populated.
        """
        if not self.tracks:
            return 0

        result = 0
        for track in self.tracks:
            duration = track.get_duration()
            if duration or duration == 0:
                result += duration
            elif duration is None:
                return None

        return result

    def get_uphill_downhill(self):
        """
        Calculates the uphill and downhill elevation climbs for the gpx file. 
        If elevation for some points is not found those are simply ignored.

        Returns
        -------
        uphill_downhill: UphillDownhill named tuple
            uphill: float
                Uphill elevation climbs in meters
            downhill: float
                Downhill elevation descent in meters
        """
        if not self.tracks:
            return UphillDownhill(0, 0)

        uphill = 0
        downhill = 0

        for track in self.tracks:
            current_uphill, current_downhill = track.get_uphill_downhill()

            uphill += current_uphill
            downhill += current_downhill

        return UphillDownhill(uphill, downhill)

    def get_location_at(self, time):
        """
        Gets approx. location at given time. Note that, at the moment this 
        method returns an instance of GPXTrackPoint in the future -- this may
        be a mod_geo.Location instance with approximated latitude, longitude 
        and elevation!
        """
        result = []
        for track in self.tracks:
            locations = track.get_location_at(time)
            for location in locations:
                result.append(location)

        return result

    def get_elevation_extremes(self):
        """ 
        Calculate elevation extremes of GPX file

        Returns
        -------
        min_max_elevation: MinimumMaximum named tuple
            minimum: float
                Minimum elevation in meters
            maximum: float
                Maximum elevation in meters
        """
        if not self.tracks:
            return MinimumMaximum(None, None)

        elevations = []

        for track in self.tracks:
            (_min, _max) = track.get_elevation_extremes()
            if _min is not None:
                elevations.append(_min)
            if _max is not None:
                elevations.append(_max)

        if len(elevations) == 0:
            return MinimumMaximum(None, None)

        return MinimumMaximum(min(elevations), max(elevations))

    def get_points_data(self, distance_2d=False):
        """
        Returns a list of tuples containing the actual point, its distance from the start,
        track_no, segment_no, and segment_point_no
        """
        distance_from_start = 0
        previous_point = None

        # (point, distance_from_start) pairs:
        points = []

        for track_no in range(len(self.tracks)):
            track = self.tracks[track_no]
            for segment_no in range(len(track.segments)):
                segment = track.segments[segment_no]
                for point_no in range(len(segment.points)):
                    point = segment.points[point_no]
                    if previous_point and point_no > 0:
                        if distance_2d:
                            distance = point.distance_2d(previous_point)
                        else:
                            distance = point.distance_3d(previous_point)

                        distance_from_start += distance

                    points.append(PointData(point, distance_from_start, track_no, segment_no, point_no))

                    previous_point = point

        return points

    def get_nearest_locations(self, location, threshold_distance=0.01):
        """
        Returns a list of locations of elements like
        consisting of points where the location may be on the track

        threshold_distance is the the minimum distance from the track
        so that the point *may* be counted as to be "on the track".
        For example 0.01 means 1% of the track distance.
        """

        assert location
        assert threshold_distance

        result = []

        points = self.get_points_data()

        if not points:
            return ()

        distance = points[- 1][1]

        threshold = distance * threshold_distance

        min_distance_candidate = None
        distance_from_start_candidate = None
        track_no_candidate = None
        segment_no_candidate = None
        point_no_candidate = None

        for point, distance_from_start, track_no, segment_no, point_no in points:
            distance = location.distance_3d(point)
            if distance < threshold:
                if min_distance_candidate is None or distance < min_distance_candidate:
                    min_distance_candidate = distance
                    distance_from_start_candidate = distance_from_start
                    track_no_candidate = track_no
                    segment_no_candidate = segment_no
                    point_no_candidate = point_no
            else:
                if distance_from_start_candidate is not None:
                    result.append((distance_from_start_candidate, track_no_candidate, segment_no_candidate, point_no_candidate))
                min_distance_candidate = None
                distance_from_start_candidate = None
                track_no_candidate = None
                segment_no_candidate = None
                point_no_candidate = None

        if distance_from_start_candidate is not None:
            result.append(NearestLocationData(distance_from_start_candidate, track_no_candidate, segment_no_candidate, point_no_candidate))

        return result

    def get_nearest_location(self, location):
        """ Returns (location, track_no, track_segment_no, track_point_no) for the
        nearest location on map """
        if not self.tracks:
            return None

        result = None
        distance = None
        result_track_no = None
        result_segment_no = None
        result_point_no = None
        for i in range(len(self.tracks)):
            track = self.tracks[i]
            nearest_location, track_segment_no, track_point_no = track.get_nearest_location(location)
            nearest_location_distance = None
            if nearest_location:
                nearest_location_distance = nearest_location.distance_2d(location)
            if not distance or nearest_location_distance < distance:
                result = nearest_location
                distance = nearest_location_distance
                result_track_no = i
                result_segment_no = track_segment_no
                result_point_no = track_point_no

        return NearestLocationData(result, result_track_no, result_segment_no, result_point_no)

    def add_elevation(self, delta):
        """
        Adjusts elevation data of GPX data.

        Parameters
        ----------
        delta : float
            Elevation delta in meters to apply to GPX data
        """
        for track in self.tracks:
            track.add_elevation(delta)

    def add_missing_data(self, get_data_function, add_missing_function):
        for track in self.tracks:
            track.add_missing_data(get_data_function, add_missing_function)

    def add_missing_elevations(self):
        def _add(interval, start, end, distances_ratios):
            assert start
            assert end
            assert start.elevation is not None
            assert end.elevation is not None
            assert interval
            assert len(interval) == len(distances_ratios)
            for i in range(len(interval)):
                interval[i].elevation = start.elevation + distances_ratios[i] * (end.elevation - start.elevation)

        self.add_missing_data(get_data_function=lambda point: point.elevation,
                              add_missing_function=_add)

    def add_missing_times(self):
        def _add(interval, start, end, distances_ratios):
            assert start
            assert end
            assert start.time is not None
            assert end.time is not None
            assert interval
            assert len(interval) == len(distances_ratios)

            seconds_between = float(mod_utils.total_seconds(end.time - start.time))

            for i in range(len(interval)):
                point = interval[i]
                ratio = distances_ratios[i]
                point.time = start.time + mod_datetime.timedelta(
                    seconds=ratio * seconds_between)

        self.add_missing_data(get_data_function=lambda point: point.time,
                              add_missing_function=_add)

    def move(self, location_delta):
        """
        Moves each point in the gpx file (routes, waypoints, tracks).

        Parameters
        ----------
        location_delta: LocationDelta
            LocationDelta to move each point
        """
        for route in self.routes:
            route.move(location_delta)

        for waypoint in self.waypoints:
            waypoint.move(location_delta)

        for track in self.tracks:
            track.move(location_delta)

    def to_xml(self):

        # TODO: Implement other versions
        version = '1.0'

        content = ''
        if self.name:
            content += mod_utils.to_xml('name', content=self.name, default=' ', escape=True)
        if self.description:
            content += mod_utils.to_xml('desc', content=self.description, default=' ', escape=True)
        if self.author:
            content += mod_utils.to_xml('author', content=self.author, default=' ', escape=True)
        if self.email:
            content += mod_utils.to_xml('email', content=self.email, escape=True)
        if self.url:
            content += mod_utils.to_xml('url', content=self.url, escape=True)
        if self.urlname:
            content += mod_utils.to_xml('urlname', content=self.urlname, escape=True)
        if self.time:
            content += mod_utils.to_xml('time', content=self.time.strftime(DATE_FORMAT))
        if self.keywords:
            content += mod_utils.to_xml('keywords', content=self.keywords, default=' ', escape=True)

        # TODO: bounds

        for waypoint in self.waypoints:
            content += waypoint.to_xml(version)

        for route in self.routes:
            content += route.to_xml(version)

        for track in self.tracks:
            content += track.to_xml(version)

        xml_attributes = {
            'version': '1.0',
            'creator': 'gpx.py -- https://github.com/tkrajina/gpxpy',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xmlns': 'http://www.topografix.com/GPX/1/0',
            'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd',
        }
        if self.creator:
            xml_attributes['creator'] = self.creator

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + mod_utils.to_xml('gpx', attributes=xml_attributes, content=content).strip()

    def smooth(self, vertical=True, horizontal=False, remove_extremes=False):
        for track in self.tracks:
            track.smooth(vertical, horizontal, remove_extremes)

    def has_times(self):
        """ See GPXTrackSegment.has_times() """
        if not self.tracks:
            return None

        result = True
        for track in self.tracks:
            result = result and track.has_times()

        return result

    def has_elevations(self):
        """ See GPXTrackSegment.has_elevations()) """
        if not self.tracks:
            return None

        result = True
        for track in self.tracks:
            result = result and track.has_elevations()

        return result

    def __hash__(self):
        return mod_utils.hash_object(self, 'time', 'name', 'description', 'author', 'email', 'url', 'urlname', 'keywords', 'waypoints', 'routes', 'tracks', 'min_latitude', 'max_latitude', 'min_longitude', 'max_longitude')

    def __repr__(self):
        representation = ''
        for attribute in 'waypoints', 'routes', 'tracks':
            value = getattr(self, attribute)
            if value:
                representation += '%s%s=%s' % (', ' if representation else '', attribute, repr(value))
        return 'GPX(%s)' % representation

    def clone(self):
        return mod_copy.deepcopy(self)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import pdb

import re as mod_re
import logging as mod_logging
import datetime as mod_datetime
import xml.dom.minidom as mod_minidom

try:
    import lxml.etree as mod_etree
except:
    mod_etree = None
    pass  # LXML not available

from . import gpx as mod_gpx
from . import utils as mod_utils


class XMLParser:
    """
    Used when lxml is not available. Uses standard minidom.
    """

    def __init__(self, xml):
        self.xml = xml
        self.dom = mod_minidom.parseString(xml)

    def get_first_child(self, node=None, name=None):
        # TODO: Remove find_first_node from utils!
        if not node:
            node = self.dom

        children = node.childNodes
        if not children:
            return None

        if not name:
            return children[0]

        for tmp_node in children:
            if tmp_node.nodeName == name:
                return tmp_node

        return None

    def get_node_name(self, node):
        if not node:
            return None
        return node.nodeName

    def get_children(self, node=None):
        if not node:
            node = self.dom

        return node.childNodes

    def get_node_data(self, node):
        if node is None:
            return None

        child_nodes = self.get_children(node)
        if not child_nodes or len(child_nodes) == 0:
            return None

        return child_nodes[0].nodeValue

    def get_node_attribute(self, node, attribute):
        if attribute in node.attributes.keys():
            return node.attributes[attribute].nodeValue
        return None


class LXMLParser:
    """
    Used when lxml is available.
    """

    def __init__(self, xml):
        if not mod_etree:
            raise Exception('Cannot use LXMLParser without lxml installed')

        if mod_utils.PYTHON_VERSION[0] == '3':
            # In python 3 all strings are unicode and for some reason lxml
            # don't like unicode strings with XMLs declared as UTF-8:
            self.xml = xml.encode('utf-8')
        else:
            self.xml = xml

        self.dom = mod_etree.XML(self.xml)
        # get the namespace
        self.ns = self.dom.nsmap.get(None)

    def get_first_child(self, node=None, name=None):
        if node is None:
            if name:
                if self.get_node_name(self.dom) == name:
                    return self.dom
            return self.dom

        children = node.getchildren()

        if not children:
            return None

        if name:
            for node in children:
                if self.get_node_name(node) == name:
                    return node
            return None

        return children[0]

    def get_node_name(self, node):
        if '}' in node.tag:
            return node.tag.split('}')[1]
        return node.tag

    def get_children(self, node=None):
        if node is None:
            node = self.dom
        return node.getchildren()

    def get_node_data(self, node):
        if node is None:
            return None

        return node.text

    def get_node_attribute(self, node, attribute):
        return node.attrib.get(attribute)


def parse_time(string):
    if not string:
        return None
    if 'T' in string:
        string = string.replace('T', ' ')
    if 'Z' in string:
        string = string.replace('Z', '')
    for date_format in mod_gpx.DATE_FORMATS:
        try:
            return mod_datetime.datetime.strptime(string, date_format)
        except ValueError as e:
            pass
    return None


class GPXParser:
    def __init__(self, xml_or_file=None, parser=None):
        """
        Parser may be lxml of minidom. If you set to None then lxml will be used if installed
        otherwise minidom.
        """
        self.init(xml_or_file)
        self.gpx = mod_gpx.GPX()
        self.xml_parser_type = parser
        self.xml_parser = None

    def init(self, xml_or_file):
        text = xml_or_file.read() if hasattr(xml_or_file, 'read') else xml_or_file
        self.xml = mod_utils.make_str(text)
        self.gpx = mod_gpx.GPX()

    def get_gpx(self):
        return self.gpx

    def parse(self):
        """
        Parses the XML file and returns a GPX object.

        It will throw GPXXMLSyntaxException if the XML file is invalid or
        GPXException if the XML file is valid but something is wrong with the
        GPX data.
        """
        try:
            if self.xml_parser_type is None:
                if mod_etree:
                    self.xml_parser = LXMLParser(self.xml)
                else:
                    self.xml_parser = XMLParser(self.xml)
            elif self.xml_parser_type == 'lxml':
                self.xml_parser = LXMLParser(self.xml)
            elif self.xml_parser_type == 'minidom':
                self.xml_parser = XMLParser(self.xml)
            else:
                raise mod_gpx.GPXException('Invalid parser type: %s' % self.xml_parser_type)

            self.__parse_dom()

            return self.gpx
        except Exception as e:
            # The exception here can be a lxml or minidom exception.
            mod_logging.debug('Error in:\n%s\n-----------\n' % self.xml)
            mod_logging.exception(e)

            # The library should work in the same way regardless of the
            # underlying XML parser that's why the exception thrown
            # here is GPXXMLSyntaxException (instead of simply throwing the
            # original minidom or lxml exception e).
            #
            # But, if the user need the original exception (lxml or minidom)
            # it is available with GPXXMLSyntaxException.original_exception:
            raise mod_gpx.GPXXMLSyntaxException('Error parsing XML: %s' % str(e), e)

    def __parse_dom(self):
        node = self.xml_parser.get_first_child(name='gpx')
        if node is None:
            raise mod_gpx.GPXException('Document must have a `gpx` root node.')
        if self.xml_parser.get_node_attribute(node, "creator"):
            self.gpx.creator = self.xml_parser.get_node_attribute(node, "creator")

        for node in self.xml_parser.get_children(node):
            node_name = self.xml_parser.get_node_name(node)
            if node_name == 'time':
                time_str = self.xml_parser.get_node_data(node)
                self.gpx.time = parse_time(time_str)
            elif node_name == 'name':
                self.gpx.name = self.xml_parser.get_node_data(node)
            elif node_name == 'desc':
                self.gpx.description = self.xml_parser.get_node_data(node)
            elif node_name == 'author':
                self.gpx.author = self.xml_parser.get_node_data(node)
            elif node_name == 'email':
                self.gpx.email = self.xml_parser.get_node_data(node)
            elif node_name == 'url':
                self.gpx.url = self.xml_parser.get_node_data(node)
            elif node_name == 'urlname':
                self.gpx.urlname = self.xml_parser.get_node_data(node)
            elif node_name == 'keywords':
                self.gpx.keywords = self.xml_parser.get_node_data(node)
            elif node_name == 'bounds':
                self._parse_bounds(node)
            elif node_name == 'wpt':
                self.gpx.waypoints.append(self._parse_waypoint(node))
            elif node_name == 'rte':
                self.gpx.routes.append(self._parse_route(node))
            elif node_name == 'trk':
                self.gpx.tracks.append(self.__parse_track(node))
            else:
                #print 'unknown %s' % node
                pass

        self.valid = True

    def _parse_bounds(self, node):
        minlat = self.xml_parser.get_node_attribute(node, 'minlat')
        if minlat:
            self.gpx.min_latitude = mod_utils.to_number(minlat)

        maxlat = self.xml_parser.get_node_attribute(node, 'maxlat')
        if maxlat:
            self.gpx.min_latitude = mod_utils.to_number(maxlat)

        minlon = self.xml_parser.get_node_attribute(node, 'minlon')
        if minlon:
            self.gpx.min_longitude = mod_utils.to_number(minlon)

        maxlon = self.xml_parser.get_node_attribute(node, 'maxlon')
        if maxlon:
            self.gpx.min_longitude = mod_utils.to_number(maxlon)

    def _parse_waypoint(self, node):
        lat = self.xml_parser.get_node_attribute(node, 'lat')
        if not lat:
            raise mod_gpx.GPXException('Waypoint without latitude')

        lon = self.xml_parser.get_node_attribute(node, 'lon')
        if not lon:
            raise mod_gpx.GPXException('Waypoint without longitude')

        lat = mod_utils.to_number(lat)
        lon = mod_utils.to_number(lon)

        elevation_node = self.xml_parser.get_first_child(node, 'ele')
        elevation = mod_utils.to_number(self.xml_parser.get_node_data(elevation_node),
                                        default=None, nan_value=None)

        time_node = self.xml_parser.get_first_child(node, 'time')
        time_str = self.xml_parser.get_node_data(time_node)
        time = parse_time(time_str)

        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        desc_node = self.xml_parser.get_first_child(node, 'desc')
        desc = self.xml_parser.get_node_data(desc_node)

        sym_node = self.xml_parser.get_first_child(node, 'sym')
        sym = self.xml_parser.get_node_data(sym_node)

        type_node = self.xml_parser.get_first_child(node, 'type')
        type = self.xml_parser.get_node_data(type_node)

        comment_node = self.xml_parser.get_first_child(node, 'cmt')
        comment = self.xml_parser.get_node_data(comment_node)

        hdop_node = self.xml_parser.get_first_child(node, 'hdop')
        hdop = mod_utils.to_number(self.xml_parser.get_node_data(hdop_node))

        vdop_node = self.xml_parser.get_first_child(node, 'vdop')
        vdop = mod_utils.to_number(self.xml_parser.get_node_data(vdop_node))

        pdop_node = self.xml_parser.get_first_child(node, 'pdop')
        pdop = mod_utils.to_number(self.xml_parser.get_node_data(pdop_node))

        return mod_gpx.GPXWaypoint(latitude=lat, longitude=lon, elevation=elevation,
                                   time=time, name=name, description=desc, symbol=sym,
                                   type=type, comment=comment, horizontal_dilution=hdop,
                                   vertical_dilution=vdop, position_dilution=pdop)

    def _parse_route(self, node):
        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        description_node = self.xml_parser.get_first_child(node, 'desc')
        description = self.xml_parser.get_node_data(description_node)

        number_node = self.xml_parser.get_first_child(node, 'number')
        number = mod_utils.to_number(self.xml_parser.get_node_data(number_node))

        route = mod_gpx.GPXRoute(name, description, number)

        child_nodes = self.xml_parser.get_children(node)
        for child_node in child_nodes:
            if self.xml_parser.get_node_name(child_node) == 'rtept':
                route_point = self._parse_route_point(child_node)
                route.points.append(route_point)

        return route

    def _parse_route_point(self, node):
        lat = self.xml_parser.get_node_attribute(node, 'lat')
        if not lat:
            raise mod_gpx.GPXException('Waypoint without latitude')

        lon = self.xml_parser.get_node_attribute(node, 'lon')
        if not lon:
            raise mod_gpx.GPXException('Waypoint without longitude')

        lat = mod_utils.to_number(lat)
        lon = mod_utils.to_number(lon)

        elevation_node = self.xml_parser.get_first_child(node, 'ele')
        elevation = mod_utils.to_number(self.xml_parser.get_node_data(elevation_node),
                                        default=None, nan_value=None)

        time_node = self.xml_parser.get_first_child(node, 'time')
        time_str = self.xml_parser.get_node_data(time_node)
        time = parse_time(time_str)

        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        desc_node = self.xml_parser.get_first_child(node, 'desc')
        desc = self.xml_parser.get_node_data(desc_node)

        sym_node = self.xml_parser.get_first_child(node, 'sym')
        sym = self.xml_parser.get_node_data(sym_node)

        type_node = self.xml_parser.get_first_child(node, 'type')
        type = self.xml_parser.get_node_data(type_node)

        comment_node = self.xml_parser.get_first_child(node, 'cmt')
        comment = self.xml_parser.get_node_data(comment_node)

        hdop_node = self.xml_parser.get_first_child(node, 'hdop')
        hdop = mod_utils.to_number(self.xml_parser.get_node_data(hdop_node))

        vdop_node = self.xml_parser.get_first_child(node, 'vdop')
        vdop = mod_utils.to_number(self.xml_parser.get_node_data(vdop_node))

        pdop_node = self.xml_parser.get_first_child(node, 'pdop')
        pdop = mod_utils.to_number(self.xml_parser.get_node_data(pdop_node))

        return mod_gpx.GPXRoutePoint(lat, lon, elevation, time, name, desc, sym, type, comment,
                                     horizontal_dilution=hdop, vertical_dilution=vdop, position_dilution=pdop)

    def __parse_track(self, node):
        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        type_node = self.xml_parser.get_first_child(node, 'type')
        type = self.xml_parser.get_node_data(type_node)

        description_node = self.xml_parser.get_first_child(node, 'desc')
        description = self.xml_parser.get_node_data(description_node)

        number_node = self.xml_parser.get_first_child(node, 'number')
        number = mod_utils.to_number(self.xml_parser.get_node_data(number_node))

        track = mod_gpx.GPXTrack(name, description, number)
        track.type = type

        child_nodes = self.xml_parser.get_children(node)
        for child_node in child_nodes:
            if self.xml_parser.get_node_name(child_node) == 'trkseg':
                track_segment = self.__parse_track_segment(child_node)
                track.segments.append(track_segment)

        return track

    def __parse_track_segment(self, node):
        track_segment = mod_gpx.GPXTrackSegment()
        child_nodes = self.xml_parser.get_children(node)
        n = 0
        for child_node in child_nodes:
            if self.xml_parser.get_node_name(child_node) == 'trkpt':
                track_point = self.__parse_track_point(child_node)
                track_segment.points.append(track_point)
                n += 1

        return track_segment

    def __parse_track_point(self, node):
        latitude = self.xml_parser.get_node_attribute(node, 'lat')
        if latitude:
            latitude = mod_utils.to_number(latitude)

        longitude = self.xml_parser.get_node_attribute(node, 'lon')
        if longitude:
            longitude = mod_utils.to_number(longitude)

        time_node = self.xml_parser.get_first_child(node, 'time')
        time_str = self.xml_parser.get_node_data(time_node)
        time = parse_time(time_str)

        elevation_node = self.xml_parser.get_first_child(node, 'ele')
        elevation = mod_utils.to_number(self.xml_parser.get_node_data(elevation_node),
                                        default=None, nan_value=None)

        sym_node = self.xml_parser.get_first_child(node, 'sym')
        symbol = self.xml_parser.get_node_data(sym_node)

        comment_node = self.xml_parser.get_first_child(node, 'cmt')
        comment = self.xml_parser.get_node_data(comment_node)

        name_node = self.xml_parser.get_first_child(node, 'name')
        name = self.xml_parser.get_node_data(name_node)

        hdop_node = self.xml_parser.get_first_child(node, 'hdop')
        hdop = mod_utils.to_number(self.xml_parser.get_node_data(hdop_node))

        vdop_node = self.xml_parser.get_first_child(node, 'vdop')
        vdop = mod_utils.to_number(self.xml_parser.get_node_data(vdop_node))

        pdop_node = self.xml_parser.get_first_child(node, 'pdop')
        pdop = mod_utils.to_number(self.xml_parser.get_node_data(pdop_node))

        speed_node = self.xml_parser.get_first_child(node, 'speed')
        speed = mod_utils.to_number(self.xml_parser.get_node_data(speed_node))

        return mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=elevation, time=time,
                                     symbol=symbol, comment=comment, horizontal_dilution=hdop, vertical_dilution=vdop,
                                     position_dilution=pdop, speed=speed, name=name)


if __name__ == '__main__':

    file_name = 'test_files/aaa.gpx'
    #file_name = 'test_files/blue_hills.gpx'
    #file_name = 'test_files/test.gpx'
    file = open(file_name, 'r')
    gpx_xml = file.read()
    file.close()

    parser = GPXParser(gpx_xml)
    gpx = parser.parse()

    print(gpx.to_xml())

    print('TRACKS:')
    for track in gpx.tracks:
        print('name%s, 2d:%s, 3d:%s' % (track.name, track.length_2d(), track.length_3d()))
        print('\tTRACK SEGMENTS:')
        for track_segment in track.segments:
            print('\t2d:%s, 3d:%s' % (track_segment.length_2d(), track_segment.length_3d()))

    print('ROUTES:')
    for route in gpx.routes:
        print(route.name)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys as mod_sys
import math as mod_math
import xml.sax.saxutils as mod_saxutils

PYTHON_VERSION = mod_sys.version.split(' ')[0]


def to_xml(tag, attributes=None, content=None, default=None, escape=False):
    attributes = attributes or {}
    result = '\n<%s' % tag

    if content is None and default:
        content = default

    if attributes:
        for attribute in attributes.keys():
            result += make_str(' %s="%s"' % (attribute, attributes[attribute]))

    if content is None:
        result += '/>'
    else:
        if escape:
            result += make_str('>%s</%s>' % (mod_saxutils.escape(content), tag))
        else:
            result += make_str('>%s</%s>' % (content, tag))

    result = make_str(result)

    return result


def is_numeric(object):
    try:
        float(object)
        return True
    except TypeError:
        return False
    except ValueError:
        return False


def to_number(s, default=0, nan_value=None):
    try:
        result = float(s)
        if mod_math.isnan(result):
            return nan_value
        return result
    except TypeError:
        pass
    except ValueError:
        pass
    return default


def total_seconds(timedelta):
    """ Some versions of python dont have timedelta.total_seconds() method. """
    if timedelta is None:
        return None
    return (timedelta.days * 86400) + timedelta.seconds

# Hash utilities:


def __hash(obj):
    result = 0

    if obj is None:
        return result
    elif isinstance(obj, dict):
        raise RuntimeError('__hash_single_object for dict not yet implemented')
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return hash_list_or_tuple(obj)

    return hash(obj)


def hash_list_or_tuple(iteration):
    result = 17

    for obj in iteration:
        result = result * 31 + __hash(obj)

    return result


def hash_object(obj, *attributes):
    result = 19

    for attribute in attributes:
        result = result * 31 + __hash(getattr(obj, attribute))

    return result


def make_str(s):
    """ Convert a str or unicode object into a str type. """
    if PYTHON_VERSION[0] == '2':
        if isinstance(s, unicode):
            return s.encode("utf-8")
    return str(s)

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-

# Copyright 2011 Tomo Krajina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Run all tests with:
    $ python -m unittest test

Run minidom parser tests with:
    $ python -m unittest test.MinidomTests

Run lxml parser tests with:
    $ python -m unittest test.LxmlTests

Run single test with:
    $ python -m unittest test.LxmlTests.test_method
"""

from __future__ import print_function

import pdb

import logging as mod_logging
import os as mod_os
import unittest as mod_unittest
import time as mod_time
import copy as mod_copy
import datetime as mod_datetime
import random as mod_random
import math as mod_math
import sys as mod_sys

import gpxpy as mod_gpxpy
import gpxpy.gpx as mod_gpx
import gpxpy.parser as mod_parser
import gpxpy.geo as mod_geo

from gpxpy.utils import make_str

PYTHON_VERSION = mod_sys.version.split(' ')[0]

mod_logging.basicConfig(level=mod_logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')


def equals(object1, object2, ignore=None):
    """ Testing purposes only """

    if not object1 and not object2:
        return True

    if not object1 or not object2:
        print('Not obj2')
        return False

    if not object1.__class__ == object2.__class__:
        print('Not obj1')
        return False

    attributes = []
    for attr in dir(object1):
        if not ignore or not attr in ignore:
            if not hasattr(object1, '__call__') and not attr.startswith('_'):
                if not attr in attributes:
                    attributes.append(attr)

    for attr in attributes:
        attr1 = getattr(object1, attr)
        attr2 = getattr(object2, attr)

        if attr1 == attr2:
            return True

        if not attr1 and not attr2:
            return True
        if not attr1 or not attr2:
            print('Object differs in attribute %s (%s - %s)' % (attr, attr1, attr2))
            return False

        if not equals(attr1, attr2):
            print('Object differs in attribute %s (%s - %s)' % (attr, attr1, attr2))
            return None

    return True

def cca(number1, number2):
    return 1 - number1 / number2 < 0.999

# TODO: Track segment speed in point test


class AbstractTests:
    """
    Add tests here.

    Tests will be run twice (once with Lxml and once with Minidom Parser).

    If you run 'make test' then all tests will be run with python2 and python3

    To be even more sure that everything works as expected -- try...
        python -m unittest test.MinidomTests
    ...with python-lxml and without python-lxml installed.
    """

    def get_parser_type(self):
        raise Exception('Implement this in subclasses')

    def parse(self, file, encoding=None):
        if PYTHON_VERSION[0] == '3':
            f = open('test_files/%s' % file, encoding=encoding)
        else:
            f = open('test_files/%s' % file)

        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        if not gpx:
            print('Parser error: %s' % parser.get_error())

        return gpx

    def reparse(self, gpx):
        xml = gpx.to_xml()

        parser = mod_parser.GPXParser(xml, parser=self.get_parser_type())
        gpx = parser.parse()

        if not gpx:
            print('Parser error while reparsing: %s' % parser.get_error())

        return gpx

    def test_parse_with_all_parser_types(self):
        self.assertTrue(mod_gpxpy.parse(open('test_files/cerknicko-jezero.gpx')))
        self.assertTrue(mod_gpxpy.parse(open('test_files/cerknicko-jezero.gpx'), parser='minidom'))
        #self.assertTrue(mod_gpxpy.parse(open('test_files/cerknicko-jezero.gpx'), parser='lxml'))

    def test_simple_parse_function(self):
        # Must not throw any exception:
        mod_gpxpy.parse(open('test_files/korita-zbevnica.gpx'), parser=self.get_parser_type())

    def test_simple_parse_function_invalid_xml(self):
        try:
            mod_gpxpy.parse('<gpx></gpx', parser=self.get_parser_type())
            self.fail()
        except mod_gpx.GPXException as e:
            self.assertTrue(('unclosed token: line 1, column 5' in str(e)) or ('expected \'>\'' in str(e)))
            self.assertTrue(isinstance(e, mod_gpx.GPXXMLSyntaxException))
            self.assertTrue(e.__cause__)

            try:
                # more checks if lxml:
                import lxml.etree as mod_etree
                import xml.parsers.expat as mod_expat
                self.assertTrue(isinstance(e.__cause__, mod_etree.XMLSyntaxError)
                                or isinstance(e.__cause__, mod_expat.ExpatError))
            except:
                pass

    def test_creator_field(self):
        gpx = self.parse('cerknicko-jezero.gpx')
        self.assertEquals(gpx.creator, "GPSBabel - http://www.gpsbabel.org")

    def test_no_creator_field(self):
        gpx = self.parse('cerknicko-jezero-no-creator.gpx')
        self.assertEquals(gpx.creator, None)

    def test_to_xml_creator(self):
        gpx = self.parse('cerknicko-jezero.gpx')
        xml = gpx.to_xml()
        self.assertTrue('creator="GPSBabel - http://www.gpsbabel.org"' in xml)

        gpx2 = self.reparse(gpx)
        self.assertEquals(gpx2.creator, "GPSBabel - http://www.gpsbabel.org")

    def test_waypoints_equality_after_reparse(self):
        gpx = self.parse('cerknicko-jezero.gpx')
        gpx2 = self.reparse(gpx)

        self.assertTrue(equals(gpx.waypoints, gpx2.waypoints))
        self.assertTrue(equals(gpx.routes, gpx2.routes))
        self.assertTrue(equals(gpx.tracks, gpx2.tracks))
        self.assertTrue(equals(gpx, gpx2))

    def test_waypoint_time(self):
        gpx = self.parse('cerknicko-jezero.gpx')

        self.assertTrue(gpx.waypoints[0].time)
        self.assertTrue(isinstance(gpx.waypoints[0].time, mod_datetime.datetime))

    def test_add_elevation(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())
        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13, elevation=100))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13))

        gpx.add_elevation(10)
        self.assertEqual(gpx.tracks[0].segments[0].points[0].elevation, 110)
        self.assertEqual(gpx.tracks[0].segments[0].points[1].elevation, None)

        gpx.add_elevation(-20)
        self.assertEqual(gpx.tracks[0].segments[0].points[0].elevation, 90)
        self.assertEqual(gpx.tracks[0].segments[0].points[1].elevation, None)

    def test_get_duration(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      time=mod_datetime.datetime(2013, 1, 1, 12, 30)))
        self.assertEqual(gpx.get_duration(), 0)

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[1].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13))
        self.assertEqual(gpx.get_duration(), 0)

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[2].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      time=mod_datetime.datetime(2013, 1, 1, 12, 30)))
        gpx.tracks[0].segments[2].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      time=mod_datetime.datetime(2013, 1, 1, 12, 31)))
        self.assertEqual(gpx.get_duration(), 60)

    def test_remove_elevation(self):
        gpx = self.parse('cerknicko-jezero.gpx')

        for point, track_no, segment_no, point_no in gpx.walk():
            self.assertTrue(point.elevation is not None)

        gpx.remove_elevation(tracks=True, waypoints=True, routes=True)

        for point, track_no, segment_no, point_no in gpx.walk():
            self.assertTrue(point.elevation is None)

        xml = gpx.to_xml()

        self.assertFalse('<ele>' in xml)

    def test_remove_time(self):
        gpx = self.parse('cerknicko-jezero.gpx')

        for point, track_no, segment_no, point_no in gpx.walk():
            self.assertTrue(point.time is not None)

        gpx.remove_time()

        for point, track_no, segment_no, point_no in gpx.walk():
            self.assertTrue(point.time is None)

    def test_has_times_false(self):
        gpx = self.parse('cerknicko-without-times.gpx')
        self.assertFalse(gpx.has_times())

    def test_has_times(self):
        gpx = self.parse('korita-zbevnica.gpx')
        self.assertTrue(len(gpx.tracks) == 4)
        # Empty -- True
        self.assertTrue(gpx.tracks[0].has_times())
        # Not times ...
        self.assertTrue(not gpx.tracks[1].has_times())

        # Times OK
        self.assertTrue(gpx.tracks[2].has_times())
        self.assertTrue(gpx.tracks[3].has_times())

    def test_unicode(self):
        gpx = self.parse('unicode.gpx', encoding='utf-8')

        name = gpx.waypoints[0].name

        self.assertTrue(make_str(name) == 'šđčćž')

    def test_nearest_location_1(self):
        gpx = self.parse('korita-zbevnica.gpx')

        location = mod_geo.Location(45.451058791, 14.027903696)
        nearest_location, track_no, track_segment_no, track_point_no = gpx.get_nearest_location(location)
        point = gpx.tracks[track_no].segments[track_segment_no].points[track_point_no]
        self.assertTrue(point.distance_2d(location) < 0.001)
        self.assertTrue(point.distance_2d(nearest_location) < 0.001)

        location = mod_geo.Location(1, 1)
        nearest_location, track_no, track_segment_no, track_point_no = gpx.get_nearest_location(location)
        point = gpx.tracks[track_no].segments[track_segment_no].points[track_point_no]
        self.assertTrue(point.distance_2d(nearest_location) < 0.001)

        location = mod_geo.Location(50, 50)
        nearest_location, track_no, track_segment_no, track_point_no = gpx.get_nearest_location(location)
        point = gpx.tracks[track_no].segments[track_segment_no].points[track_point_no]
        self.assertTrue(point.distance_2d(nearest_location) < 0.001)

    def test_long_timestamps(self):
        # Check if timestamps in format: 1901-12-13T20:45:52.2073437Z work
        gpx = self.parse('Mojstrovka.gpx')

        # %Y-%m-%dT%H:%M:%SZ'

    def test_reduce_gpx_file(self):
        f = open('test_files/Mojstrovka.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        max_reduced_points_no = 50

        started = mod_time.time()
        points_original = gpx.get_track_points_no()
        time_original = mod_time.time() - started

        gpx.reduce_points(max_reduced_points_no)

        points_reduced = gpx.get_track_points_no()

        result = gpx.to_xml()
        if mod_sys.version_info[0] != 3:
            result = result.encode('utf-8')

        started = mod_time.time()
        parser = mod_parser.GPXParser(result, parser=self.get_parser_type())
        parser.parse()
        time_reduced = mod_time.time() - started

        print(time_original)
        print(points_original)

        print(time_reduced)
        print(points_reduced)

        self.assertTrue(points_reduced < points_original)
        self.assertTrue(points_reduced < max_reduced_points_no)

    def test_smooth_without_removing_extreemes_preserves_point_count(self):
        gpx = self.parse('first_and_last_elevation.gpx')
        l = len(list(gpx.walk()))
        gpx.smooth(vertical=True, horizontal=False)
        self.assertEquals(l, len(list(gpx.walk())))

    def test_smooth_without_removing_extreemes_preserves_point_count_2(self):
        gpx = self.parse('first_and_last_elevation.gpx')
        l = len(list(gpx.walk()))
        gpx.smooth(vertical=False, horizontal=True)
        self.assertEquals(l, len(list(gpx.walk())))

    def test_smooth_without_removing_extreemes_preserves_point_count_3(self):
        gpx = self.parse('first_and_last_elevation.gpx')
        l = len(list(gpx.walk()))
        gpx.smooth(vertical=True, horizontal=True)
        self.assertEquals(l, len(list(gpx.walk())))

    def test_clone_and_smooth(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        original_2d = gpx.length_2d()
        original_3d = gpx.length_3d()

        cloned_gpx = gpx.clone()

        self.assertTrue(hash(gpx) == hash(cloned_gpx))

        cloned_gpx.reduce_points(2000, min_distance=10)
        cloned_gpx.smooth(vertical=True, horizontal=True)
        cloned_gpx.smooth(vertical=True, horizontal=False)

        print('2d:', gpx.length_2d())
        print('2d cloned and smoothed:', cloned_gpx.length_2d())

        print('3d:', gpx.length_3d())
        print('3d cloned and smoothed:', cloned_gpx.length_3d())

        self.assertTrue(gpx.length_3d() == original_3d)
        self.assertTrue(gpx.length_2d() == original_2d)

        self.assertTrue(gpx.length_3d() > cloned_gpx.length_3d())
        self.assertTrue(gpx.length_2d() > cloned_gpx.length_2d())

    def test_reduce_by_min_distance(self):
        gpx = mod_gpxpy.parse(open('test_files/cerknicko-jezero.gpx'), parser=self.get_parser_type())

        min_distance_before_reduce = 1000000
        for point, track_no, segment_no, point_no in gpx.walk():
            if point_no > 0:
                previous_point = gpx.tracks[track_no].segments[segment_no].points[point_no - 1]
                print(point.distance_3d(previous_point))
                if point.distance_3d(previous_point) < min_distance_before_reduce:
                    min_distance_before_reduce = point.distance_3d(previous_point)

        gpx.reduce_points(min_distance=10)

        min_distance_after_reduce = 1000000
        for point, track_no, segment_no, point_no in gpx.walk():
            if point_no > 0:
                previous_point = gpx.tracks[track_no].segments[segment_no].points[point_no - 1]
                d = point.distance_3d(previous_point)
                if point.distance_3d(previous_point) < min_distance_after_reduce:
                    min_distance_after_reduce = point.distance_3d(previous_point)

        self.assertTrue(min_distance_before_reduce < min_distance_after_reduce)
        self.assertTrue(min_distance_before_reduce < 10)
        self.assertTrue(10 < min_distance_after_reduce)

    def test_moving_stopped_times(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        print(gpx.get_track_points_no())

        #gpx.reduce_points(1000, min_distance=5)

        print(gpx.get_track_points_no())

        length = gpx.length_3d()
        print('Distance: %s' % length)

        gpx.reduce_points(2000, min_distance=10)

        gpx.smooth(vertical=True, horizontal=True)
        gpx.smooth(vertical=True, horizontal=False)

        moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx.get_moving_data(stopped_speed_threshold=0.1)
        print('-----')
        print('Length: %s' % length)
        print('Moving time: %s (%smin)' % (moving_time, moving_time / 60.))
        print('Stopped time: %s (%smin)' % (stopped_time, stopped_time / 60.))
        print('Moving distance: %s' % moving_distance)
        print('Stopped distance: %s' % stopped_distance)
        print('Max speed: %sm/s' % max_speed)
        print('-----')

        # TODO: More tests and checks
        self.assertTrue(moving_distance < length)
        print('Dakle:', moving_distance, length)
        self.assertTrue(moving_distance > 0.75 * length)
        self.assertTrue(stopped_distance < 0.1 * length)

    def test_split_on_impossible_index(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        track = gpx.tracks[0]

        before = len(track.segments)
        track.split(1000, 10)
        after = len(track.segments)

        self.assertTrue(before == after)

    def test_split(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        track = gpx.tracks[1]

        track_points_no = track.get_points_no()

        before = len(track.segments)
        track.split(0, 10)
        after = len(track.segments)

        self.assertTrue(before + 1 == after)
        print('Points in first (splitted) part:', len(track.segments[0].points))

        # From 0 to 10th point == 11 points:
        self.assertTrue(len(track.segments[0].points) == 11)
        self.assertTrue(len(track.segments[0].points) + len(track.segments[1].points) == track_points_no)

        # Now split the second track
        track.split(1, 20)
        self.assertTrue(len(track.segments[1].points) == 21)
        self.assertTrue(len(track.segments[0].points) + len(track.segments[1].points) + len(track.segments[2].points) == track_points_no)

    def test_split_and_join(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        track = gpx.tracks[1]

        original_track = track.clone()

        track.split(0, 10)
        track.split(1, 20)

        self.assertTrue(len(track.segments) == 3)
        track.join(1)
        self.assertTrue(len(track.segments) == 2)
        track.join(0)
        self.assertTrue(len(track.segments) == 1)

        # Check that this splitted and joined track is the same as the original one:
        self.assertTrue(equals(track, original_track))

    def test_remove_point_from_segment(self):
        f = open('test_files/cerknicko-jezero.gpx')
        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())
        gpx = parser.parse()
        f.close()

        track = gpx.tracks[1]
        segment = track.segments[0]
        original_segment = segment.clone()

        segment.remove_point(3)
        print(segment.points[0])
        print(original_segment.points[0])
        self.assertTrue(equals(segment.points[0], original_segment.points[0]))
        self.assertTrue(equals(segment.points[1], original_segment.points[1]))
        self.assertTrue(equals(segment.points[2], original_segment.points[2]))
        # ...but:
        self.assertTrue(equals(segment.points[3], original_segment.points[4]))

        self.assertTrue(len(segment.points) + 1 == len(original_segment.points))

    def test_distance(self):
        distance = mod_geo.distance(48.56806, 21.43467, None, 48.599214, 21.430878, None)
        print(distance)
        self.assertTrue(distance > 3450 and distance < 3500)

    def test_haversine_distance(self):
        loc1 = mod_geo.Location(1, 2)
        loc2 = mod_geo.Location(2, 3)

        self.assertEqual(loc1.distance_2d(loc2),
                         mod_geo.distance(loc1.latitude, loc1.longitude, None, loc2.latitude, loc2.longitude, None))

        loc1 = mod_geo.Location(1, 2)
        loc2 = mod_geo.Location(3, 4)

        self.assertEqual(loc1.distance_2d(loc2),
                         mod_geo.distance(loc1.latitude, loc1.longitude, None, loc2.latitude, loc2.longitude, None))

        loc1 = mod_geo.Location(1, 2)
        loc2 = mod_geo.Location(3.1, 4)

        self.assertEqual(loc1.distance_2d(loc2),
                         mod_geo.haversine_distance(loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude))

        loc1 = mod_geo.Location(1, 2)
        loc2 = mod_geo.Location(2, 4.1)

        self.assertEqual(loc1.distance_2d(loc2),
                         mod_geo.haversine_distance(loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude))

    def test_horizontal_smooth_remove_extremes(self):
        f = open('test_files/track-with-extremes.gpx', 'r')

        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())

        gpx = parser.parse()

        points_before = gpx.get_track_points_no()
        gpx.smooth(vertical=False, horizontal=True, remove_extremes=True)
        points_after = gpx.get_track_points_no()

        print(points_before)
        print(points_after)

        self.assertTrue(points_before - 2 == points_after)

    def test_vertical_smooth_remove_extremes(self):
        f = open('test_files/track-with-extremes.gpx', 'r')

        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())

        gpx = parser.parse()

        points_before = gpx.get_track_points_no()
        gpx.smooth(vertical=True, horizontal=False, remove_extremes=True)
        points_after = gpx.get_track_points_no()

        print(points_before)
        print(points_after)

        self.assertTrue(points_before - 1 == points_after)

    def test_horizontal_and_vertical_smooth_remove_extremes(self):
        f = open('test_files/track-with-extremes.gpx', 'r')

        parser = mod_parser.GPXParser(f, parser=self.get_parser_type())

        gpx = parser.parse()

        points_before = gpx.get_track_points_no()
        gpx.smooth(vertical=True, horizontal=True, remove_extremes=True)
        points_after = gpx.get_track_points_no()

        print(points_before)
        print(points_after)

        self.assertTrue(points_before - 3 == points_after)

    def test_positions_on_track(self):
        gpx = mod_gpx.GPX()
        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)
        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)

        location_to_find_on_track = None

        for i in range(1000):
            latitude = 45 + i * 0.001
            longitude = 45 + i * 0.001
            elevation = 100 + i * 2
            point = mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=elevation)
            segment.points.append(point)

            if i == 500:
                location_to_find_on_track = mod_gpx.GPXWaypoint(latitude=latitude, longitude=longitude)

        result = gpx.get_nearest_locations(location_to_find_on_track)

        self.assertTrue(len(result) == 1)

    def test_positions_on_track_2(self):
        gpx = mod_gpx.GPX()
        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)

        location_to_find_on_track = None

        # first segment:
        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)
        for i in range(1000):
            latitude = 45 + i * 0.001
            longitude = 45 + i * 0.001
            elevation = 100 + i * 2
            point = mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=elevation)
            segment.points.append(point)

            if i == 500:
                location_to_find_on_track = mod_gpx.GPXWaypoint(latitude=latitude, longitude=longitude)

        # second segment
        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)
        for i in range(1000):
            latitude = 45.0000001 + i * 0.001
            longitude = 45.0000001 + i * 0.001
            elevation = 100 + i * 2
            point = mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=elevation)
            segment.points.append(point)

        result = gpx.get_nearest_locations(location_to_find_on_track)

        print('Found', result)

        self.assertTrue(len(result) == 2)

    def test_hash_location(self):
        location_1 = mod_geo.Location(latitude=12, longitude=13, elevation=19)
        location_2 = mod_geo.Location(latitude=12, longitude=13, elevation=19)

        self.assertTrue(hash(location_1) == hash(location_2))

        location_2.elevation *= 2.0
        location_2.latitude *= 2.0
        location_2.longitude *= 2.0

        self.assertTrue(hash(location_1) != hash(location_2))

        location_2.elevation /= 2.0
        location_2.latitude /= 2.0
        location_2.longitude /= 2.0

        self.assertTrue(hash(location_1) == hash(location_2))

    def test_hash_gpx_track_point(self):
        point_1 = mod_gpx.GPXTrackPoint(latitude=12, longitude=13, elevation=19)
        point_2 = mod_gpx.GPXTrackPoint(latitude=12, longitude=13, elevation=19)

        self.assertTrue(hash(point_1) == hash(point_2))

        point_2.elevation *= 2.0
        point_2.latitude *= 2.0
        point_2.longitude *= 2.0

        self.assertTrue(hash(point_1) != hash(point_2))

        point_2.elevation /= 2.0
        point_2.latitude /= 2.0
        point_2.longitude /= 2.0

        self.assertTrue(hash(point_1) == hash(point_2))

    def test_hash_track(self):
        gpx = mod_gpx.GPX()
        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)

        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)
        for i in range(1000):
            latitude = 45 + i * 0.001
            longitude = 45 + i * 0.001
            elevation = 100 + i * 2.
            point = mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=elevation)
            segment.points.append(point)

        self.assertTrue(hash(gpx))
        self.assertTrue(len(gpx.tracks) == 1)
        self.assertTrue(len(gpx.tracks[0].segments) == 1)
        self.assertTrue(len(gpx.tracks[0].segments[0].points) == 1000)

        cloned_gpx = mod_copy.deepcopy(gpx)

        self.assertTrue(hash(gpx) == hash(cloned_gpx))

        gpx.tracks[0].segments[0].points[17].elevation *= 2.
        self.assertTrue(hash(gpx) != hash(cloned_gpx))

        gpx.tracks[0].segments[0].points[17].elevation /= 2.
        self.assertTrue(hash(gpx) == hash(cloned_gpx))

        gpx.tracks[0].segments[0].points[17].latitude /= 2.
        self.assertTrue(hash(gpx) != hash(cloned_gpx))

        gpx.tracks[0].segments[0].points[17].latitude *= 2.
        self.assertTrue(hash(gpx) == hash(cloned_gpx))

        del gpx.tracks[0].segments[0].points[17]
        self.assertTrue(hash(gpx) != hash(cloned_gpx))

    def test_bounds(self):
        gpx = mod_gpx.GPX()

        track = mod_gpx.GPXTrack()

        segment_1 = mod_gpx.GPXTrackSegment()
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=-12, longitude=13))
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=-100, longitude=-5))
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=100, longitude=-13))
        track.segments.append(segment_1)

        segment_2 = mod_gpx.GPXTrackSegment()
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=-12, longitude=100))
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=-10, longitude=-5))
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=10, longitude=-100))
        track.segments.append(segment_2)

        gpx.tracks.append(track)

        bounds = gpx.get_bounds()

        self.assertEqual(bounds.min_latitude, -100)
        self.assertEqual(bounds.max_latitude, 100)
        self.assertEqual(bounds.min_longitude, -100)
        self.assertEqual(bounds.max_longitude, 100)

        # Test refresh bounds:

        gpx.refresh_bounds()
        self.assertEqual(gpx.min_latitude, -100)
        self.assertEqual(gpx.max_latitude, 100)
        self.assertEqual(gpx.min_longitude, -100)
        self.assertEqual(gpx.max_longitude, 100)

    def test_time_bounds(self):
        gpx = mod_gpx.GPX()

        track = mod_gpx.GPXTrack()

        segment_1 = mod_gpx.GPXTrackSegment()
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=-12, longitude=13))
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=-100, longitude=-5, time=mod_datetime.datetime(2001, 1, 12)))
        segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=100, longitude=-13, time=mod_datetime.datetime(2003, 1, 12)))
        track.segments.append(segment_1)

        segment_2 = mod_gpx.GPXTrackSegment()
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=-12, longitude=100, time=mod_datetime.datetime(2010, 1, 12)))
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=-10, longitude=-5, time=mod_datetime.datetime(2011, 1, 12)))
        segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=10, longitude=-100))
        track.segments.append(segment_2)

        gpx.tracks.append(track)

        bounds = gpx.get_time_bounds()

        self.assertEqual(bounds.start_time, mod_datetime.datetime(2001, 1, 12))
        self.assertEqual(bounds.end_time, mod_datetime.datetime(2011, 1, 12))

    def test_speed(self):
        gpx = self.parse('track_with_speed.gpx')
        gpx2 = self.reparse(gpx)

        self.assertTrue(equals(gpx.waypoints, gpx2.waypoints))
        self.assertTrue(equals(gpx.routes, gpx2.routes))
        self.assertTrue(equals(gpx.tracks, gpx2.tracks))
        self.assertTrue(equals(gpx, gpx2))

        self.assertEqual(gpx.tracks[0].segments[0].points[0].speed, 1.2)
        self.assertEqual(gpx.tracks[0].segments[0].points[1].speed, 2.2)
        self.assertEqual(gpx.tracks[0].segments[0].points[2].speed, 3.2)

    def test_dilutions(self):
        gpx = self.parse('track_with_dilution_errors.gpx')
        gpx2 = self.reparse(gpx)

        self.assertTrue(equals(gpx.waypoints, gpx2.waypoints))
        self.assertTrue(equals(gpx.routes, gpx2.routes))
        self.assertTrue(equals(gpx.tracks, gpx2.tracks))
        self.assertTrue(equals(gpx, gpx2))

        self.assertTrue(hash(gpx) == hash(gpx2))

        for test_gpx in (gpx, gpx2):
            self.assertTrue(test_gpx.waypoints[0].horizontal_dilution == 100.1)
            self.assertTrue(test_gpx.waypoints[0].vertical_dilution == 101.1)
            self.assertTrue(test_gpx.waypoints[0].position_dilution == 102.1)

            self.assertTrue(test_gpx.routes[0].points[0].horizontal_dilution == 200.1)
            self.assertTrue(test_gpx.routes[0].points[0].vertical_dilution == 201.1)
            self.assertTrue(test_gpx.routes[0].points[0].position_dilution == 202.1)

            self.assertTrue(test_gpx.tracks[0].segments[0].points[0].horizontal_dilution == 300.1)
            self.assertTrue(test_gpx.tracks[0].segments[0].points[0].vertical_dilution == 301.1)
            self.assertTrue(test_gpx.tracks[0].segments[0].points[0].position_dilution == 302.1)

    def test_name_comment_and_symbol(self):
        gpx = mod_gpx.GPX()
        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)
        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)
        point = mod_gpx.GPXTrackPoint(12, 13, name='aaa', comment='ccc', symbol='sss')
        segment.points.append(point)

        xml = gpx.to_xml()

        self.assertTrue('<name>aaa' in xml)

        gpx2 = self.reparse(gpx)

        self.assertEquals(gpx.tracks[0].segments[0].points[0].name, 'aaa')
        self.assertEquals(gpx.tracks[0].segments[0].points[0].comment, 'ccc')
        self.assertEquals(gpx.tracks[0].segments[0].points[0].symbol, 'sss')

    def test_get_bounds_and_refresh_bounds(self):
        gpx = mod_gpx.GPX()

        latitudes = []
        longitudes = []

        for i in range(2):
            track = mod_gpx.GPXTrack()
            for i in range(2):
                segment = mod_gpx.GPXTrackSegment()
                for i in range(10):
                    latitude = 50. * (mod_random.random() - 0.5)
                    longitude = 50. * (mod_random.random() - 0.5)
                    point = mod_gpx.GPXTrackPoint(latitude=latitude, longitude=longitude)
                    segment.points.append(point)
                    latitudes.append(latitude)
                    longitudes.append(longitude)
                track.segments.append(segment)
            gpx.tracks.append(track)

        bounds = gpx.get_bounds()

        print(latitudes)
        print(longitudes)

        self.assertEqual(bounds.min_latitude, min(latitudes))
        self.assertEqual(bounds.max_latitude, max(latitudes))
        self.assertEqual(bounds.min_longitude, min(longitudes))
        self.assertEqual(bounds.max_longitude, max(longitudes))

        gpx.refresh_bounds()

        self.assertEqual(gpx.min_latitude, min(latitudes))
        self.assertEqual(gpx.max_latitude, max(latitudes))
        self.assertEqual(gpx.min_longitude, min(longitudes))
        self.assertEqual(gpx.max_longitude, max(longitudes))

    def test_named_tuples_values_bounds(self):
        gpx = self.parse('korita-zbevnica.gpx')

        bounds = gpx.get_bounds()
        min_lat, max_lat, min_lon, max_lon = gpx.get_bounds()

        self.assertEqual(min_lat, bounds.min_latitude)
        self.assertEqual(min_lon, bounds.min_longitude)
        self.assertEqual(max_lat, bounds.max_latitude)
        self.assertEqual(max_lon, bounds.max_longitude)

    def test_named_tuples_values_time_bounds(self):
        gpx = self.parse('korita-zbevnica.gpx')

        time_bounds = gpx.get_time_bounds()
        start_time, end_time = gpx.get_time_bounds()

        self.assertEqual(start_time, time_bounds.start_time)
        self.assertEqual(end_time, time_bounds.end_time)

    def test_named_tuples_values_moving_data(self):
        gpx = self.parse('korita-zbevnica.gpx')

        moving_data = gpx.get_moving_data()
        moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx.get_moving_data()
        self.assertEqual(moving_time, moving_data.moving_time)
        self.assertEqual(stopped_time, moving_data.stopped_time)
        self.assertEqual(moving_distance, moving_data.moving_distance)
        self.assertEqual(stopped_distance, moving_data.stopped_distance)
        self.assertEqual(max_speed, moving_data.max_speed)

    def test_named_tuples_values_uphill_downhill(self):
        gpx = self.parse('korita-zbevnica.gpx')

        uphill_downhill = gpx.get_uphill_downhill()
        uphill, downhill = gpx.get_uphill_downhill()
        self.assertEqual(uphill, uphill_downhill.uphill)
        self.assertEqual(downhill, uphill_downhill.downhill)

    def test_named_tuples_values_elevation_extremes(self):
        gpx = self.parse('korita-zbevnica.gpx')

        elevation_extremes = gpx.get_elevation_extremes()
        minimum, maximum = gpx.get_elevation_extremes()
        self.assertEqual(minimum, elevation_extremes.minimum)
        self.assertEqual(maximum, elevation_extremes.maximum)

    def test_named_tuples_values_nearest_location_data(self):
        gpx = self.parse('korita-zbevnica.gpx')

        location = gpx.tracks[1].segments[0].points[2]
        location.latitude *= 1.00001
        location.longitude *= 0.99999
        nearest_location_data = gpx.get_nearest_location(location)
        found_location, track_no, segment_no, point_no = gpx.get_nearest_location(location)
        self.assertEqual(found_location, nearest_location_data.location)
        self.assertEqual(track_no, nearest_location_data.track_no)
        self.assertEqual(segment_no, nearest_location_data.segment_no)
        self.assertEqual(point_no, nearest_location_data.point_no)

    def test_named_tuples_values_point_data(self):
        gpx = self.parse('korita-zbevnica.gpx')

        points_datas = gpx.get_points_data()

        for point_data in points_datas:
            point, distance_from_start, track_no, segment_no, point_no = point_data
            self.assertEqual(point, point_data.point)
            self.assertEqual(distance_from_start, point_data.distance_from_start)
            self.assertEqual(track_no, point_data.track_no)
            self.assertEqual(segment_no, point_data.segment_no)
            self.assertEqual(point_no, point_data.point_no)

    def test_track_points_data(self):
        gpx = self.parse('korita-zbevnica.gpx')

        points_data_2d = gpx.get_points_data(distance_2d=True)

        point, distance_from_start, track_no, segment_no, point_no = points_data_2d[-1]
        self.assertEqual(track_no, len(gpx.tracks) - 1)
        self.assertEqual(segment_no, len(gpx.tracks[-1].segments) - 1)
        self.assertEqual(point_no, len(gpx.tracks[-1].segments[-1].points) - 1)
        self.assertTrue(abs(distance_from_start - gpx.length_2d()) < 0.0001)

        points_data_3d = gpx.get_points_data(distance_2d=False)
        point, distance_from_start, track_no, segment_no, point_no = points_data_3d[-1]
        self.assertEqual(track_no, len(gpx.tracks) - 1)
        self.assertEqual(segment_no, len(gpx.tracks[-1].segments) - 1)
        self.assertEqual(point_no, len(gpx.tracks[-1].segments[-1].points) - 1)
        self.assertTrue(abs(distance_from_start - gpx.length_3d()) < 0.0001)

        self.assertTrue(gpx.length_2d() != gpx.length_3d())

    def test_walk_route_points(self):
        gpx = mod_gpxpy.parse(open('test_files/route.gpx'), parser=self.get_parser_type())

        for point in gpx.routes[0].walk(only_points=True):
            self.assertTrue(point)

        for point, point_no in gpx.routes[0].walk():
            self.assertTrue(point)

        self.assertEqual(point_no, len(gpx.routes[0].points) - 1)

    def test_walk_gpx_points(self):
        gpx = self.parse('korita-zbevnica.gpx')

        for point in gpx.walk():
            self.assertTrue(point)

        for point, track_no, segment_no, point_no in gpx.walk():
            self.assertTrue(point)

        self.assertEqual(track_no, len(gpx.tracks) - 1)
        self.assertEqual(segment_no, len(gpx.tracks[-1].segments) - 1)
        self.assertEqual(point_no, len(gpx.tracks[-1].segments[-1].points) - 1)

    def test_walk_gpx_points(self):
        gpx = self.parse('korita-zbevnica.gpx')
        track = gpx.tracks[1]

        for point in track.walk():
            self.assertTrue(point)

        for point, segment_no, point_no in track.walk():
            self.assertTrue(point)

        self.assertEqual(segment_no, len(track.segments) - 1)
        self.assertEqual(point_no, len(track.segments[-1].points) - 1)

    def test_walk_segment_points(self):
        gpx = self.parse('korita-zbevnica.gpx')
        track = gpx.tracks[1]
        segment = track.segments[0]

        assert len(segment.points) > 0

        for point in segment.walk():
            self.assertTrue(point)

        """
        for point, segment_no, point_no in track.walk():
            self.assertTrue(point)

        self.assertEqual(segment_no, len(track.segments) - 1)
        self.assertEqual(point_no, len(track.segments[-1].points) - 1)
        """

    def test_angle_0(self):
        loc1 = mod_geo.Location(0, 0)
        loc2 = mod_geo.Location(0, 1)

        loc1.elevation = 100
        loc2.elevation = 100

        angle_radians = mod_geo.elevation_angle(loc1, loc2, radians=True)
        angle_degrees = mod_geo.elevation_angle(loc1, loc2, radians=False)

        self.assertEqual(angle_radians, 0)
        self.assertEqual(angle_degrees, 0)

    def test_angle(self):
        loc1 = mod_geo.Location(0, 0)
        loc2 = mod_geo.Location(0, 1)

        loc1.elevation = 100
        loc2.elevation = loc1.elevation + loc1.distance_2d(loc2)

        angle_radians = mod_geo.elevation_angle(loc1, loc2, radians=True)
        angle_degrees = mod_geo.elevation_angle(loc1, loc2, radians=False)

        self.assertEqual(angle_radians, mod_math.pi / 4)
        self.assertEqual(angle_degrees, 45)

    def test_angle_2(self):
        loc1 = mod_geo.Location(45, 45)
        loc2 = mod_geo.Location(46, 45)

        loc1.elevation = 100
        loc2.elevation = loc1.elevation + 0.5 * loc1.distance_2d(loc2)

        angle_radians = mod_geo.elevation_angle(loc1, loc2, radians=True)
        angle_degrees = mod_geo.elevation_angle(loc1, loc2, radians=False)

        self.assertTrue(angle_radians < mod_math.pi / 4)
        self.assertTrue(angle_degrees < 45)

    def test_angle_2(self):
        loc1 = mod_geo.Location(45, 45)
        loc2 = mod_geo.Location(46, 45)

        loc1.elevation = 100
        loc2.elevation = loc1.elevation + 1.5 * loc1.distance_2d(loc2)

        angle_radians = mod_geo.elevation_angle(loc1, loc2, radians=True)
        angle_degrees = mod_geo.elevation_angle(loc1, loc2, radians=False)

        self.assertTrue(angle_radians > mod_math.pi / 4)
        self.assertTrue(angle_degrees > 45)

    def test_angle_3(self):
        loc1 = mod_geo.Location(45, 45)
        loc2 = mod_geo.Location(46, 45)

        loc1.elevation = 100
        loc2.elevation = loc1.elevation - loc1.distance_2d(loc2)

        angle_radians = mod_geo.elevation_angle(loc1, loc2, radians=True)
        angle_degrees = mod_geo.elevation_angle(loc1, loc2, radians=False)

        self.assertEqual(angle_radians, - mod_math.pi / 4)
        self.assertEqual(angle_degrees, - 45)

    def test_angle_loc(self):
        loc1 = mod_geo.Location(45, 45)
        loc2 = mod_geo.Location(46, 45)

        self.assertEqual(loc1.elevation_angle(loc2), mod_geo.elevation_angle(loc1, loc2))
        self.assertEqual(loc1.elevation_angle(loc2, radians=True), mod_geo.elevation_angle(loc1, loc2, radians=True))
        self.assertEqual(loc1.elevation_angle(loc2, radians=False), mod_geo.elevation_angle(loc1, loc2, radians=False))

    def test_ignore_maximums_for_max_speed(self):
        gpx = mod_gpx.GPX()

        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)

        tmp_time = mod_datetime.datetime.now()

        tmp_longitude = 0
        segment_1 = mod_gpx.GPXTrackSegment()
        for i in range(4):
            segment_1.points.append(mod_gpx.GPXTrackPoint(latitude=0, longitude=tmp_longitude, time=tmp_time))
            tmp_longitude += 0.01
            tmp_time += mod_datetime.timedelta(hours=1)
        track.segments.append(segment_1)

        moving_time, stopped_time, moving_distance, stopped_distance, max_speed_with_too_small_segment = gpx.get_moving_data()

        # Too few points:
        mod_logging.debug('max_speed = %s', max_speed_with_too_small_segment)
        self.assertFalse(max_speed_with_too_small_segment)

        tmp_longitude = 0.
        segment_2 = mod_gpx.GPXTrackSegment()
        for i in range(55):
            segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=0, longitude=tmp_longitude, time=tmp_time))
            tmp_longitude += 0.01
            tmp_time += mod_datetime.timedelta(hours=1)
        track.segments.append(segment_2)

        moving_time, stopped_time, moving_distance, stopped_distance, max_speed_with_equal_speeds = gpx.get_moving_data()

        mod_logging.debug('max_speed = %s', max_speed_with_equal_speeds)
        self.assertTrue(max_speed_with_equal_speeds > 0)

        # When we add to few extreemes, they should be ignored:
        for i in range(10):
            segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=0, longitude=tmp_longitude, time=tmp_time))
            tmp_longitude += 0.7
            tmp_time += mod_datetime.timedelta(hours=1)
        moving_time, stopped_time, moving_distance, stopped_distance, max_speed_with_extreemes = gpx.get_moving_data()

        self.assertTrue(abs(max_speed_with_extreemes - max_speed_with_equal_speeds) < 0.001)

        # But if there are many extreemes (they are no more extreemes):
        for i in range(100):
            # Sometimes add on start, sometimes on end:
            if i % 2 == 0:
                segment_2.points.append(mod_gpx.GPXTrackPoint(latitude=0, longitude=tmp_longitude, time=tmp_time))
            else:
                segment_2.points.insert(0, mod_gpx.GPXTrackPoint(latitude=0, longitude=tmp_longitude, time=tmp_time))
            tmp_longitude += 0.5
            tmp_time += mod_datetime.timedelta(hours=1)
        moving_time, stopped_time, moving_distance, stopped_distance, max_speed_with_more_extreemes = gpx.get_moving_data()

        mod_logging.debug('max_speed_with_more_extreemes = %s', max_speed_with_more_extreemes)
        mod_logging.debug('max_speed_with_extreemes = %s', max_speed_with_extreemes)
        self.assertTrue(max_speed_with_more_extreemes - max_speed_with_extreemes > 10)

    def test_track_with_elevation_zero(self):
        with open('test_files/cerknicko-jezero-with-elevations-zero.gpx') as f:
            gpx = mod_gpxpy.parse(f, parser=self.get_parser_type())

            minimum, maximum = gpx.get_elevation_extremes()
            self.assertEqual(minimum, 0)
            self.assertEqual(maximum, 0)

            uphill, downhill = gpx.get_uphill_downhill()
            self.assertEqual(uphill, 0)
            self.assertEqual(downhill, 0)

    def test_track_without_elevation(self):
        with open('test_files/cerknicko-jezero-without-elevations.gpx') as f:
            gpx = mod_gpxpy.parse(f, parser=self.get_parser_type())

            minimum, maximum = gpx.get_elevation_extremes()
            self.assertEqual(minimum, None)
            self.assertEqual(maximum, None)

            uphill, downhill = gpx.get_uphill_downhill()
            self.assertEqual(uphill, 0)
            self.assertEqual(downhill, 0)

    def test_has_elevation_false(self):
        with open('test_files/cerknicko-jezero-without-elevations.gpx') as f:
            gpx = mod_gpxpy.parse(f, parser=self.get_parser_type())
            self.assertFalse(gpx.has_elevations())

    def test_has_elevation_true(self):
        with open('test_files/cerknicko-jezero.gpx') as f:
            gpx = mod_gpxpy.parse(f, parser=self.get_parser_type())
            self.assertFalse(gpx.has_elevations())

    def test_track_with_some_points_are_without_elevations(self):
        gpx = mod_gpx.GPX()

        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)

        tmp_latlong = 0
        segment_1 = mod_gpx.GPXTrackSegment()
        for i in range(4):
            point = mod_gpx.GPXTrackPoint(latitude=tmp_latlong, longitude=tmp_latlong)
            segment_1.points.append(point)
            if i % 3 == 0:
                point.elevation = None
            else:
                point.elevation = 100 / (i + 1)

        track.segments.append(segment_1)

        minimum, maximum = gpx.get_elevation_extremes()
        self.assertTrue(minimum is not None)
        self.assertTrue(maximum is not None)

        uphill, downhill = gpx.get_uphill_downhill()
        self.assertTrue(uphill is not None)
        self.assertTrue(downhill is not None)

    def test_track_with_empty_segment(self):
        with open('test_files/track-with-empty-segment.gpx') as f:
            gpx = mod_gpxpy.parse(f, parser=self.get_parser_type())
            self.assertIsNotNone(gpx.tracks[0].get_bounds().min_latitude)
            self.assertIsNotNone(gpx.tracks[0].get_bounds().min_longitude)

    def test_add_missing_data_no_intervals(self):
        # Test only that the add_missing_function is called with the right data
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      elevation=10))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=14,
                                                                      elevation=100))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=15,
                                                                      elevation=20))

        # Shouldn't be called because all points have elevation
        def _add_missing_function(interval, start_point, end_point, ratios):
            raise Error()

        gpx.add_missing_data(get_data_function=lambda point: point.elevation,
                             add_missing_function=_add_missing_function)

    def test_add_missing_data_one_interval(self):
        # Test only that the add_missing_function is called with the right data
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      elevation=10))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=14,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=15,
                                                                      elevation=20))

        # Shouldn't be called because all points have elevation
        def _add_missing_function(interval, start_point, end_point, ratios):
            assert start_point
            assert start_point.latitude == 12 and start_point.longitude == 13
            assert end_point
            assert end_point.latitude == 12 and end_point.longitude == 15
            assert len(interval) == 1
            assert interval[0].latitude == 12 and interval[0].longitude == 14
            assert ratios
            interval[0].elevation = 314

        gpx.add_missing_data(get_data_function=lambda point: point.elevation,
                             add_missing_function=_add_missing_function)

        self.assertEquals(314, gpx.tracks[0].segments[0].points[1].elevation)

    def test_add_missing_data_one_interval_and_empty_points_on_start_and_end(self):
        # Test only that the add_missing_function is called with the right data
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      elevation=10))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=14,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=15,
                                                                      elevation=20))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=12, longitude=13,
                                                                      elevation=None))

        # Shouldn't be called because all points have elevation
        def _add_missing_function(interval, start_point, end_point, ratios):
            assert start_point
            assert start_point.latitude == 12 and start_point.longitude == 13
            assert end_point
            assert end_point.latitude == 12 and end_point.longitude == 15
            assert len(interval) == 1
            assert interval[0].latitude == 12 and interval[0].longitude == 14
            assert ratios
            interval[0].elevation = 314

        gpx.add_missing_data(get_data_function=lambda point: point.elevation,
                             add_missing_function=_add_missing_function)

        # Points at start and end should not have elevation 314 because have
        # no two bounding points with elevations:
        self.assertEquals(None, gpx.tracks[0].segments[0].points[0].elevation)
        self.assertEquals(None, gpx.tracks[0].segments[0].points[-1].elevation)

        self.assertEquals(314, gpx.tracks[0].segments[0].points[2].elevation)

    def test_add_missing_elevations(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13, longitude=12,
                                                                      elevation=10))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.25, longitude=12,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.5, longitude=12,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.9, longitude=12,
                                                                      elevation=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=14, longitude=12,
                                                                      elevation=20))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=15, longitude=12,
                                                                      elevation=None))

        gpx.add_missing_elevations()

        self.assertTrue(abs(12.5 - gpx.tracks[0].segments[0].points[1].elevation) < 0.01)
        self.assertTrue(abs(15 - gpx.tracks[0].segments[0].points[2].elevation) < 0.01)
        self.assertTrue(abs(19 - gpx.tracks[0].segments[0].points[3].elevation) < 0.01)

    def test_add_missing_times(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13, longitude=12,
                                                                      time=mod_datetime.datetime(2013, 1, 2, 12, 0)))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.25, longitude=12,
                                                                      time=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.5, longitude=12,
                                                                      time=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.75, longitude=12,
                                                                      time=None))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=14, longitude=12,
                                                                      time=mod_datetime.datetime(2013, 1, 2, 13, 0)))

        gpx.add_missing_times()

        time_1 = gpx.tracks[0].segments[0].points[1].time
        time_2 = gpx.tracks[0].segments[0].points[2].time
        time_3 = gpx.tracks[0].segments[0].points[3].time

        self.assertEqual(2013, time_1.year)
        self.assertEqual(1, time_1.month)
        self.assertEqual(2, time_1.day)
        self.assertEqual(12, time_1.hour)
        self.assertEqual(15, time_1.minute)

        self.assertEqual(2013, time_2.year)
        self.assertEqual(1, time_2.month)
        self.assertEqual(2, time_2.day)
        self.assertEqual(12, time_2.hour)
        self.assertEqual(30, time_2.minute)

        self.assertEqual(2013, time_3.year)
        self.assertEqual(1, time_3.month)
        self.assertEqual(2, time_3.day)
        self.assertEqual(12, time_3.hour)
        self.assertEqual(45, time_3.minute)

    def test_add_missing_times_2(self):
        xml = ''
        xml += '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<gpx>\n'
        xml += '<trk>\n'
        xml += '<trkseg>\n'
        xml += '<trkpt lat="35.794159" lon="-5.832745"><time>2014-02-02T10:23:18Z</time></trkpt>\n'
        xml += '<trkpt lat="35.7941046982" lon="-5.83285637909"></trkpt>\n'
        xml += '<trkpt lat="35.7914309254" lon="-5.83378314972"></trkpt>\n'
        xml += '<trkpt lat="35.791014" lon="-5.833826"><time>2014-02-02T10:25:30Z</time><ele>18</ele></trkpt>\n'
        xml += '</trkseg></trk></gpx>\n'
        gpx = mod_gpxpy.parse(xml)

        gpx.add_missing_times()

        previous_time = None
        for point in gpx.walk(only_points=True):
            if point.time:
                if previous_time:
                    print('point.time=', point.time, 'previous_time=', previous_time)
                    self.assertTrue(point.time > previous_time)
            previous_time = point.time

    def test_distance_from_line(self):
        d = mod_geo.distance_from_line(mod_geo.Location(1, 1),
                                       mod_geo.Location(0, -1),
                                       mod_geo.Location(0, 1))
        self.assertTrue(abs(d - mod_geo.ONE_DEGREE) < 100)

    def test_simplify(self):
        for gpx_file in mod_os.listdir('test_files'):
            print('Parsing:', gpx_file)
            gpx = mod_gpxpy.parse(open('test_files/%s' % gpx_file), parser=self.get_parser_type())

            length_2d_original = gpx.length_2d()

            gpx = mod_gpxpy.parse(open('test_files/%s' % gpx_file))
            gpx.simplify(max_distance=50)
            length_2d_after_distance_50 = gpx.length_2d()

            gpx = mod_gpxpy.parse(open('test_files/%s' % gpx_file))
            gpx.simplify(max_distance=10)
            length_2d_after_distance_10 = gpx.length_2d()

            print(length_2d_original, length_2d_after_distance_10, length_2d_after_distance_50)

            # When simplifying the resulting disnatce should alway be less than the original:
            self.assertTrue(length_2d_original >= length_2d_after_distance_10)
            self.assertTrue(length_2d_original >= length_2d_after_distance_50)

            # Simplify with bigger max_distance and => bigger error from original
            self.assertTrue(length_2d_after_distance_10 >= length_2d_after_distance_50)

            # The resulting distance usually shouldn't be too different from
            # the orignial (here check for 80% and 70%)
            self.assertTrue(length_2d_after_distance_10 >= length_2d_original * .6)
            self.assertTrue(length_2d_after_distance_50 >= length_2d_original * .5)

    def test_simplify_circular_gpx(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13, longitude=12))
        gpx.tracks[0].segments[0].points.append(mod_gpx.GPXTrackPoint(latitude=13.25, longitude=12))

        # Then the first point again:
        gpx.tracks[0].segments[0].points.append(gpx.tracks[0].segments[0].points[0])

        gpx.simplify()

    def test_nan_elevation(self):
        xml = '<?xml version="1.0" encoding="UTF-8"?><gpx> <wpt lat="12" lon="13"> <ele>nan</ele></wpt> <rte> <rtept lat="12" lon="13"> <ele>nan</ele></rtept></rte> <trk> <name/> <desc/> <trkseg> <trkpt lat="12" lon="13"> <ele>nan</ele></trkpt></trkseg></trk></gpx>'
        gpx = mod_gpxpy.parse(xml)

        self.assertTrue(gpx.tracks[0].segments[0].points[0].elevation is None)
        self.assertTrue(gpx.routes[0].points[0].elevation is None)
        self.assertTrue(gpx.waypoints[0].elevation is None)

    def test_time_difference(self):
        point_1 = mod_gpx.GPXTrackPoint(latitude=13, longitude=12,
                                        time=mod_datetime.datetime(2013, 1, 2, 12, 31))
        point_2 = mod_gpx.GPXTrackPoint(latitude=13, longitude=12,
                                        time=mod_datetime.datetime(2013, 1, 3, 12, 32))

        seconds = point_1.time_difference(point_2)
        self.assertEquals(seconds, 60 * 60 * 24 + 60)

    def test_parse_time(self):
        timestamps = [
            '2001-10-26T21:32:52',
            #'2001-10-26T21:32:52+0200',
            '2001-10-26T19:32:52Z',
            #'2001-10-26T19:32:52+00:00',
            #'-2001-10-26T21:32:52',
            '2001-10-26T21:32:52.12679',
            '2001-10-26T21:32:52',
            #'2001-10-26T21:32:52+02:00',
            '2001-10-26T19:32:52Z',
            #'2001-10-26T19:32:52+00:00',
            #'-2001-10-26T21:32:52',
            '2001-10-26T21:32:52.12679',
        ]
        timestamps_without_tz = list(map(lambda x: x.replace('T', ' ').replace('Z', ''), timestamps))
        for t in timestamps_without_tz:
            timestamps.append(t)
        for timestamp in timestamps:
            print('Parsing: %s' % timestamp)
            self.assertTrue(mod_parser.parse_time(timestamp) is not None)

    def test_get_location_at(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())
        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        p0 = mod_gpx.GPXTrackPoint(latitude=13.0, longitude=13.0, time=mod_datetime.datetime(2013, 1, 2, 12, 30, 0))
        p1 = mod_gpx.GPXTrackPoint(latitude=13.1, longitude=13.1, time=mod_datetime.datetime(2013, 1, 2, 12, 31, 0))
        gpx.tracks[0].segments[0].points.append(p0)
        gpx.tracks[0].segments[0].points.append(p1)

        self.assertEquals(gpx.tracks[0].get_location_at(mod_datetime.datetime(2013, 1, 2, 12, 29, 30)), [])
        self.assertEquals(gpx.tracks[0].get_location_at(mod_datetime.datetime(2013, 1, 2, 12, 30, 0))[0], p0)
        self.assertEquals(gpx.tracks[0].get_location_at(mod_datetime.datetime(2013, 1, 2, 12, 30, 30))[0], p1)
        self.assertEquals(gpx.tracks[0].get_location_at(mod_datetime.datetime(2013, 1, 2, 12, 31, 0))[0], p1)
        self.assertEquals(gpx.tracks[0].get_location_at(mod_datetime.datetime(2013, 1, 2, 12, 31, 30)), [])

    def test_adjust_time(self):
        gpx = mod_gpx.GPX()
        gpx.tracks.append(mod_gpx.GPXTrack())
        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        p0 = mod_gpx.GPXTrackPoint(latitude=13.0, longitude=13.0)
        p1 = mod_gpx.GPXTrackPoint(latitude=13.1, longitude=13.1)
        gpx.tracks[0].segments[0].points.append(p0)
        gpx.tracks[0].segments[0].points.append(p1)

        gpx.tracks[0].segments.append(mod_gpx.GPXTrackSegment())
        p0 = mod_gpx.GPXTrackPoint(latitude=13.0, longitude=13.0, time=mod_datetime.datetime(2013, 1, 2, 12, 30, 0))
        p1 = mod_gpx.GPXTrackPoint(latitude=13.1, longitude=13.1, time=mod_datetime.datetime(2013, 1, 2, 12, 31, 0))
        gpx.tracks[0].segments[1].points.append(p0)
        gpx.tracks[0].segments[1].points.append(p1)

        d1 = mod_datetime.timedelta(-1, -1)
        d2 = mod_datetime.timedelta(1, 2)
        # move back and forward to add a total of 1 second
        gpx.adjust_time(d1)
        gpx.adjust_time(d2)

        self.assertEquals(gpx.tracks[0].segments[0].points[0].time, None)
        self.assertEquals(gpx.tracks[0].segments[0].points[1].time, None)
        self.assertEquals(gpx.tracks[0].segments[1].points[0].time, mod_datetime.datetime(2013, 1, 2, 12, 30, 1))
        self.assertEquals(gpx.tracks[0].segments[1].points[1].time, mod_datetime.datetime(2013, 1, 2, 12, 31, 1))

    def test_unicode(self):
        parser = mod_parser.GPXParser(open('test_files/unicode2.gpx'))
        gpx = parser.parse()
        gpx.to_xml()

    def test_location_delta(self):
        location = mod_geo.Location(-20, -50)

        location_2 = location + mod_geo.LocationDelta(angle=45, distance=100)
        self.assertTrue(cca(location_2.latitude  - location.latitude, location_2.longitude - location.longitude))

    def test_location_equator_delta_distance_111120(self):
        self.__test_location_delta(mod_geo.Location(0, 13), 111120)

    def test_location_equator_delta_distance_50(self):
        self.__test_location_delta(mod_geo.Location(0, -50), 50)

    def test_location_nonequator_delta_distance_111120(self):
        self.__test_location_delta(mod_geo.Location(45, 13), 111120)

    def test_location_nonequator_delta_distance_50(self):
        self.__test_location_delta(mod_geo.Location(-20, -50), 50)

    def test_delta_add_and_move(self):
        location = mod_geo.Location(45.1, 13.2)
        delta = mod_geo.LocationDelta(angle=20, distance=1000)
        location_2 = location + delta
        location.move(delta)

        self.assertTrue(cca(location.latitude, location_2.latitude))
        self.assertTrue(cca(location.longitude, location_2.longitude))

    def __test_location_delta(self, location, distance):
        angles = [ x * 15 for x in range(int(360 / 15)) ]
        print(angles)

        distance_from_previous_location = None
        previous_location               = None

        distances_between_points = []

        for angle in angles:
            new_location = location + mod_geo.LocationDelta(angle=angle, distance=distance)
            # All locations same distance from center
            self.assertTrue(cca(location.distance_2d(new_location), distance))
            if previous_location:
                distances_between_points.append(new_location.distance_2d(previous_location))
            previous_location = new_location

        print(distances_between_points)
        # All points should be equidistant on a circle:
        for i in range(1, len(distances_between_points)):
            self.assertTrue(cca(distances_between_points[0], distances_between_points[i]))

    def test_min_max(self):
        gpx = mod_gpx.GPX()
        
        track = mod_gpx.GPXTrack()
        gpx.tracks.append(track)

        segment = mod_gpx.GPXTrackSegment()
        track.segments.append(segment)

        segment.points.append(mod_gpx.GPXTrackPoint(12, 13, elevation=100))
        segment.points.append(mod_gpx.GPXTrackPoint(12, 13, elevation=200))

        # Check for segment:
        elevation_min, elevation_max = segment.get_elevation_extremes()
        self.assertEquals(100, elevation_min)
        self.assertEquals(200, elevation_max)

        # Check for track:
        elevation_min, elevation_max = track.get_elevation_extremes()
        self.assertEquals(100, elevation_min)
        self.assertEquals(200, elevation_max)

        # Check for gpx:
        elevation_min, elevation_max = gpx.get_elevation_extremes()
        self.assertEquals(100, elevation_min)
        self.assertEquals(200, elevation_max)

class LxmlTests(mod_unittest.TestCase, AbstractTests):
    def get_parser_type(self):
        return 'lxml'


class MinidomTests(LxmlTests, AbstractTests):
    def get_parser_type(self):
        return 'minidom'

if __name__ == '__main__':
    mod_unittest.main()

########NEW FILE########
