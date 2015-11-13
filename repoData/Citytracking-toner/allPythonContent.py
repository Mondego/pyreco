__FILENAME__ = mapping
from imposm.mapping import Options, Polygons, LineStrings, PseudoArea, GeneralizedTable, meter_to_mapunit

def zoom_threshold(zoom):
    return meter_to_mapunit(20037508.0 * 2 / (2**(8 + zoom)))

db_conf = Options(
    db='toner',
    host='localhost',
    port=5432,
    user='osm',
    password='',
    sslmode='allow',
    prefix='osm_new_',
    proj='epsg:900913',
)



# WHERE leisure IN ('park', 'water_park', 'marina', 'nature_reserve',
# 	                                   'playground', 'garden', 'common')
# 	                    OR amenity IN ('graveyard')
# 	                    OR landuse IN ('cemetery')
# 	                    OR leisure IN ('sports_centre', 'golf_course', 'stadium',
# 	                                   'track', 'pitch')
# 	                    OR landuse IN ('recreation_ground')
# 	                    OR landuse IN ('forest', 'wood')
# 	                 
# 	                 ORDER BY ST_Area(way) DESC

green_areas = Polygons(
    name = 'green_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'leisure': ('park', 'water_park', 'marina', 'nature_reserve', 'playground', 'garden', 'common', 'sports_centre', 'golf_course', 'stadium', 'track', 'pitch'),
        'landuse': ('cemetery', 'park', 'water_park', 'marina', 'nature_reserve', 'playground', 'garden', 'common', 'forest', 'wood'),
        'amenity': ('graveyard')
    }
)

green_areas_z13 = GeneralizedTable(
    name = 'green_areas_z13',
    tolerance = zoom_threshold(13),
    origin = green_areas,
)

green_areas_z10 = GeneralizedTable(
    name = 'green_areas_z10',
    tolerance = zoom_threshold(10),
    origin = green_areas_z13,
)



# WHERE amenity IN ('school', 'college', 'university', 'bus_station',
#                   'ferry_terminal', 'hospital', 'kindergarten',
#                   'place_of_worship', 'public_building', 'townhall')
#    OR landuse IN ('industrial', 'commercial')

grey_areas = Polygons(
    name = 'grey_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'amenity': ('school', 'college', 'university', 'bus_station', 'ferry_terminal', 'hospital', 'kindergarten', 'place_of_worship', 'public_building', 'townhall'),
        'landuse': ('industrial', 'commercial')
    }
)

grey_areas_z13 = GeneralizedTable(
    name = 'grey_areas_z13',
    tolerance = zoom_threshold(13),
    origin = grey_areas,
)

grey_areas_z10 = GeneralizedTable(
    name = 'grey_areas_z10',
    tolerance = zoom_threshold(10),
    origin = grey_areas_z13,
)



# WHERE building IS NOT NULL

buildings = Polygons(
    name = 'buildings',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'building': ('__any__',)
    }
)

buildings_z13 = GeneralizedTable(
    name = 'buildings_z13',
    tolerance = zoom_threshold(13),
    origin = buildings,
)

buildings_z10 = GeneralizedTable(
    name = 'buildings_z10',
    tolerance = zoom_threshold(10),
    origin = buildings_z13,
)



# WHERE aeroway IS NOT NULL

aeroways = LineStrings(
    name = 'aeroways',
    mapping = {
        'aeroway': ('__any__',)
    }
)

aeroways_z13 = GeneralizedTable(
    name = 'aeroways_z13',
    tolerance = zoom_threshold(13),
    origin = aeroways,
)

aeroways_z10 = GeneralizedTable(
    name = 'aeroways_z10',
    tolerance = zoom_threshold(10),
    origin = aeroways_z13,
)



# WHERE waterway IS NOT NULL

waterways = LineStrings(
    name = 'waterways',
    mapping = {
        'waterway': ('__any__',)
    }
)

waterways_z13 = GeneralizedTable(
    name = 'waterways_z13',
    tolerance = zoom_threshold(13),
    origin = waterways,
)

waterways_z10 = GeneralizedTable(
    name = 'waterways_z10',
    tolerance = zoom_threshold(10),
    origin = waterways_z13,
)



# WHERE "natural" IN ('water', 'bay')
# 	 OR waterway = 'riverbank'
# 	 OR landuse = 'reservoir'

water_areas = Polygons(
    name = 'water_areas',
    fields = (
        ('area', PseudoArea()),
    ),
    mapping = {
        'natural': ('water', 'bay'),
        'waterway': ('riverbank',),
        'landuse': ('reservoir',)
    }
)

water_areas_z13 = GeneralizedTable(
    name = 'water_areas_z13',
    tolerance = zoom_threshold(13),
    origin = water_areas,
)

water_areas_z10 = GeneralizedTable(
    name = 'water_areas_z10',
    tolerance = zoom_threshold(10),
    origin = water_areas_z13,
)

########NEW FILE########
__FILENAME__ = anneal
#!/usr/bin/env python

# Python module for simulated annealing - anneal.py - v1.0 - 2 Sep 2009
# 
# Copyright (c) 2009, Richard J. Wagner <wagnerr@umich.edu>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This module performs simulated annealing to find a state of a system that
minimizes its energy.

An example program demonstrates simulated annealing with a traveling
salesman problem to find the shortest route to visit the twenty largest
cities in the United States.
"""

# How to optimize a system with simulated annealing:
# 
# 1) Define a format for describing the state of the system.
# 
# 2) Define a function to calculate the energy of a state.
# 
# 3) Define a function to make a random change to a state.
# 
# 4) Choose a maximum temperature, minimum temperature, and number of steps.
# 
# 5) Set the annealer to work with your state and functions.
# 
# 6) Study the variation in energy with temperature and duration to find a
# productive annealing schedule.
# 
# Or,
# 
# 4) Run the automatic annealer which will attempt to choose reasonable values
# for maximum and minimum temperatures and then anneal for the allotted time.

import copy, math, random, sys, time

def round_figures(x, n):
	"""Returns x rounded to n significant figures."""
	return round(x, int(n - math.ceil(math.log10(abs(x)))))

def time_string(seconds):
	"""Returns time in seconds as a string formatted HHHH:MM:SS."""
	s = int(round(seconds))  # round to nearest second
	h, s = divmod(s, 3600)   # get hours and remainder
	m, s = divmod(s, 60)     # split remainder into minutes and seconds
	return '%4i:%02i:%02i' % (h, m, s)

class Annealer:
	"""Performs simulated annealing by calling functions to calculate
	energy and make moves on a state.  The temperature schedule for
	annealing may be provided manually or estimated automatically.
	"""
	def __init__(self, energy, move):
		self.energy = energy  # function to calculate energy of a state
		self.move = move      # function to make a random change to a state
	
	def anneal(self, state, Tmax, Tmin, steps, updates=0):
		"""Minimizes the energy of a system by simulated annealing.
		
		Keyword arguments:
		state -- an initial arrangement of the system
		Tmax -- maximum temperature (in units of energy)
		Tmin -- minimum temperature (must be greater than zero)
		steps -- the number of steps requested
		updates -- the number of updates to print during annealing
		
		Returns the best state and energy found."""
		
		step = 0
		start = time.time()
		
		def update(T, E, acceptance, improvement):
			"""Prints the current temperature, energy, acceptance rate,
			improvement rate, elapsed time, and remaining time.
			
			The acceptance rate indicates the percentage of moves since the last
			update that were accepted by the Metropolis algorithm.  It includes
			moves that decreased the energy, moves that left the energy
			unchanged, and moves that increased the energy yet were reached by
			thermal excitation.
			
			The improvement rate indicates the percentage of moves since the
			last update that strictly decreased the energy.  At high
			temperatures it will include both moves that improved the overall
			state and moves that simply undid previously accepted moves that
			increased the energy by thermal excititation.  At low temperatures
			it will tend toward zero as the moves that can decrease the energy
			are exhausted and moves that would increase the energy are no longer
			thermally accessible."""
			
			elapsed = time.time() - start
			if step == 0:
				print ' Temperature        Energy    Accept   Improve     Elapsed   Remaining'
				print '%12.2f  %12.2f                      %s            ' % \
					(T, E, time_string(elapsed) )
			else:
				remain = ( steps - step ) * ( elapsed / step )
				print '%12.2f  %12.2f  %7.2f%%  %7.2f%%  %s  %s' % \
					(T, E, 100.0*acceptance, 100.0*improvement,
						time_string(elapsed), time_string(remain))
		
		# Precompute factor for exponential cooling from Tmax to Tmin
		if Tmin <= 0.0:
			print 'Exponential cooling requires a minimum temperature greater than zero.'
			sys.exit()
		Tfactor = -math.log( float(Tmax) / Tmin )
		
		# Note initial state
		T = Tmax
		E = self.energy(state)
		prevState = copy.deepcopy(state)
		prevEnergy = E
		bestState = copy.deepcopy(state)
		bestEnergy = E
		trials, accepts, improves = 0, 0, 0
		if updates > 0:
			updateWavelength = float(steps) / updates
			update(T, E, None, None)
		
		# Attempt moves to new states
		while step < steps:
			step += 1
			T = Tmax * math.exp( Tfactor * step / steps )
			self.move(state)
			E = self.energy(state)
			dE = E - prevEnergy
			trials += 1
			if dE > 0.0 and math.exp(-dE/T) < random.random():
				# Restore previous state
				state = copy.deepcopy(prevState)
				E = prevEnergy
			else:
				# Accept new state and compare to best state
				accepts += 1
				if dE < 0.0:
					improves += 1
				prevState = copy.deepcopy(state)
				prevEnergy = E
				if E < bestEnergy:
					bestState = copy.deepcopy(state)
					bestEnergy = E
			if updates > 1:
				if step // updateWavelength > (step-1) // updateWavelength:
					update(T, E, float(accepts)/trials, float(improves)/trials)
					trials, accepts, improves = 0, 0, 0
		
		# Return best state and energy
		return bestState, bestEnergy
	
	def auto(self, state, minutes, steps=2000):
		"""Minimizes the energy of a system by simulated annealing with
		automatic selection of the temperature schedule.
		
		Keyword arguments:
		state -- an initial arrangement of the system
		minutes -- time to spend annealing (after exploring temperatures)
		steps -- number of steps to spend on each stage of exploration
		
		Returns the best state and energy found."""
		
		def run(state, T, steps):
			"""Anneals a system at constant temperature and returns the state,
			energy, rate of acceptance, and rate of improvement."""
			E = self.energy(state)
			prevState = copy.deepcopy(state)
			prevEnergy = E
			accepts, improves = 0, 0
			for step in range(steps):
				self.move(state)
				E = self.energy(state)
				dE = E - prevEnergy
				if dE > 0.0 and math.exp(-dE/T) < random.random():
					state = copy.deepcopy(prevState)
					E = prevEnergy
				else:
					accepts += 1
					if dE < 0.0:
						improves += 1
					prevState = copy.deepcopy(state)
					prevEnergy = E
			return state, E, float(accepts)/steps, float(improves)/steps
		
		step = 0
		start = time.time()
		
		print 'Attempting automatic simulated anneal...'
		
		# Find an initial guess for temperature
		T = 0.0
		E = self.energy(state)
		while T == 0.0:
			step += 1
			self.move(state)
			T = abs( self.energy(state) - E )
		
		print 'Exploring temperature landscape:'
		print ' Temperature        Energy    Accept   Improve     Elapsed'
		def update(T, E, acceptance, improvement):
			"""Prints the current temperature, energy, acceptance rate,
			improvement rate, and elapsed time."""
			elapsed = time.time() - start
			print '%12.2f  %12.2f  %7.2f%%  %7.2f%%  %s' % \
				(T, E, 100.0*acceptance, 100.0*improvement, time_string(elapsed))
		
		# Search for Tmax - a temperature that gives 98% acceptance
		state, E, acceptance, improvement = run(state, T, steps)
		step += steps
		while acceptance > 0.98:
			T = round_figures(T/1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		while acceptance < 0.98:
			T = round_figures(T*1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		Tmax = T
		
		# Search for Tmin - a temperature that gives 0% improvement
		while improvement > 0.0:
			T = round_figures(T/1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		Tmin = T
		
		# Calculate anneal duration
		elapsed = time.time() - start
		duration = round_figures(int(60.0 * minutes * step / elapsed), 2)
		
		# Perform anneal
		print 'Annealing from %.6f to %.6f over %i steps:' % (Tmax, Tmin, duration)
		return self.anneal(state, Tmax, Tmin, duration, 20)

if __name__ == '__main__':
	"""Test annealer with a traveling salesman problem."""
	
	# List latitude and longitude (degrees) for the twenty largest U.S. cities
	cities = { 'New York City': (40.72,74.00), 'Los Angeles': (34.05,118.25),
	'Chicago': (41.88,87.63), 'Houston': (29.77,95.38),
	'Phoenix': (33.45,112.07), 'Philadelphia': (39.95,75.17),
	'San Antonio': (29.53,98.47), 'Dallas': (32.78,96.80),
	'San Diego': (32.78,117.15), 'San Jose': (37.30,121.87),
	'Detroit': (42.33,83.05), 'San Francisco': (37.78,122.42),
	'Jacksonville': (30.32,81.70), 'Indianapolis': (39.78,86.15),
	'Austin': (30.27,97.77), 'Columbus': (39.98,82.98),
	'Fort Worth': (32.75,97.33), 'Charlotte': (35.23,80.85),
	'Memphis': (35.12,89.97), 'Baltimore': (39.28,76.62) }
	
	def distance(a, b):
		"""Calculates distance between two latitude-longitude coordinates."""
		R = 3963  # radius of Earth (miles)
		lat1, lon1 = math.radians(a[0]), math.radians(a[1])
		lat2, lon2 = math.radians(b[0]), math.radians(b[1])
		return math.acos( math.sin(lat1)*math.sin(lat2) +
			math.cos(lat1)*math.cos(lat2)*math.cos(lon1-lon2) ) * R
	
	def route_move(state):
		"""Swaps two cities in the route."""
		a = random.randint( 0, len(state)-1 )
		b = random.randint( 0, len(state)-1 )
		state[a], state[b] = state[b], state[a]
	
	def route_energy(state):
		"""Calculates the length of the route."""
		e = 0
		for i in range(len(state)):
			e += distance( cities[state[i-1]], cities[state[i]] )
		return e
	
	# Start with the cities listed in random order
	state = cities.keys()
	random.shuffle(state)
	
	# Minimize the distance to be traveled by simulated annealing with a
	# manually chosen temperature schedule
	annealer = Annealer(route_energy, route_move)
	state, e = annealer.anneal(state, 10000000, 0.01, 18000*len(state), 9)
	while state[0] != 'New York City':
		state = state[1:] + state[:1]  # rotate NYC to start
	print "%i mile route:" % route_energy(state)
	for city in state:
		print "\t", city
	
	# Minimize the distance to be traveled by simulated annealing with an
	# automatically chosen temperature schedule
	state, e = annealer.auto(state, 4)
	while state[0] != 'New York City':
		state = state[1:] + state[:1]  # rotate NYC to start
	print "%i mile route:" % route_energy(state)
	for city in state:
		print "\t", city
	
	sys.exit()

########NEW FILE########
__FILENAME__ = index
from math import ceil, log

from shapely.geometry import Point

from ModestMaps.OpenStreetMap import Provider
from ModestMaps.Core import Coordinate

class PointIndex:
    """ Primitive quadtree for checking collisions based on a known radius.
    """
    def __init__(self, zoom, radius):
        """ Zoom is the base zoom level we're annealing to, radius is
            the pixel radius around each place to check for collisions.
        """
        self.zpixel = zoom + 8
        self.zgroup = zoom + 8 - ceil(log(radius * 2) / log(2))
        self.radius = radius
        self.quads = {}
        
        self.locationCoordinate = Provider().locationCoordinate
    
    def add(self, name, location):
        """ Add a new place name and location to the index.
        """
        coord = self.locationCoordinate(location).zoomTo(self.zpixel)
        point = Point(coord.column, coord.row)
        
        # buffer the location by radius and get its bbox
        area = point.buffer(self.radius, 4)
        xmin, ymin, xmax, ymax = area.bounds

        # a list of quads that the buffered location overlaps
        quads = [quadkey(Coordinate(y, x, self.zpixel).zoomTo(self.zgroup))
                 for (x, y) in ((xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin))]
        
        # store name + area shape
        for quad in set(quads):
            if quad in self.quads:
                self.quads[quad].append((name, area))
            else:
                self.quads[quad] = [(name, area)]
    
    def blocks(self, location):
        """ If the location is blocked by some other location
            in the index, return the blocker's name or False.
        """
        coord = self.locationCoordinate(location).zoomTo(self.zpixel)
        point = Point(coord.column, coord.row)
        
        # figure out which quad the point is in
        key = quadkey(coord.zoomTo(self.zgroup))
        
        # first try the easy hash check
        if key not in self.quads:
            return False

        # then do the expensive shape check
        for (name, area) in self.quads[key]:
            if point.intersects(area):
                # ensure name evals to true
                return name or True
        
        return False

class FootprintIndex:
    """ Primitive quadtree for checking collisions based on footprints.
    """
    def __init__(self, zoom):
        """ Zoom is the base zoom level we're annealing to.
        """
        self.zpixel = zoom + 8
        self.zgroup = zoom
        self.quads = {}
        
        self.locationCoordinate = Provider().locationCoordinate
    
    def _areaQuads(self, area):
        """
        """
        xmin, ymin, xmax, ymax = area.bounds
        
        ul = Coordinate(ymin, xmin, self.zpixel).zoomTo(self.zgroup).container()
        lr = Coordinate(ymax, xmax, self.zpixel).zoomTo(self.zgroup).container()
        
        quads = set()
        
        for x in range(int(1 + lr.column - ul.column)):
            for y in range(int(1 + lr.row - ul.row)):
                coord = ul.right(x).down(y)
                quads.add(quadkey(coord))
        
        return quads
        
    def add(self, place):
        """ Add a new place to the index.
        """
        for quad in self._areaQuads(place.footprint()):
            if quad in self.quads:
                self.quads[quad].append(place)
            else:
                self.quads[quad] = [place]
    
    def blocks(self, place):
        """ If the place is blocked by some other place in
            the index, return the blocking place or False.
        """
        # figure out which quads the area covers
        quads = self._areaQuads(place.footprint())
        
        # now just the quads we already know about
        quads = [key for key in quads if key in self.quads]
        
        for key in quads:
            for other in self.quads[key]:
                if place.overlaps(other):
                    return other
        
        return False

def quadkey(coord):
    return '%(row)d-%(column)d-%(zoom)d' % coord.container().__dict__

########NEW FILE########
__FILENAME__ = places
from math import pi, sin, cos
from random import choice
from copy import deepcopy

try:
    from PIL.ImageFont import truetype
except ImportError:
    from ImageFont import truetype

from shapely.geometry import Point, Polygon

NE, ENE, ESE, SE, SSE, S, SSW, SW, WSW, WNW, NW, NNW, N, NNE = range(14)

#
#          NNW   N   NNE
#        NW             NE
#       WNW      .      ENE
#       WSW             ESE
#        SW             SE
#          SSW   S   SSE
#
# slide 13 of http://www.cs.uu.nl/docs/vakken/gd/steven2.pdf
#
placements = {NE: 0.000, ENE: 0.070, ESE: 0.100, SE: 0.175, SSE: 0.200,
              S: 0.900, SSW: 1.000, SW: 0.600, WSW: 0.500, WNW: 0.470,
              NW: 0.400, NNW: 0.575, N: 0.800, NNE: 0.150}

class Place:

    def __init__(self, name, fontfile, fontsize, location, position, radius, properties, rank=1, preferred=None, **extras):
        
        if location.lon < -360 or 360 < location.lon:
            raise Exception('Silly human trying to pass an invalid longitude of %.3f for "%s"' % (location.lon, name))
    
        if location.lat < -90 or 90 < location.lat:
            raise Exception('Silly human trying to pass an invalid latitude of %.3f for "%s"' % (location.lat, name))
    
        self.name = name
        self.location = location
        self.position = position
        self.rank = rank
        
        self.fontfile = fontfile
        self.fontsize = fontsize
        self.properties = properties
    
        self.placement = NE
        self.radius = radius
        self.buffer = 2
        
        self._label_shapes = {}      # dictionary of label bounds by placement
        self._mask_shapes = {}       # dictionary of mask shapes by placement
        self._label_footprint = None # all possible label shapes, together
        self._mask_footprint = None  # all possible mask shapes, together
        self._point_shape = None     # point shape for current placement
        
        full_extras = 'placement' in extras \
                  and '_label_shapes' in extras \
                  and '_mask_shapes' in extras \
                  and '_label_footprint' in extras \
                  and '_mask_footprint' in extras \
                  and '_point_shape' in extras \
                  and '_placements' in extras \
                  and '_baseline' in extras
        
        if full_extras:
            # use the provided extras
            self.placement = extras['placement']
            self._label_shapes = extras['_label_shapes']
            self._mask_shapes = extras['_mask_shapes']
            self._label_footprint = extras['_label_footprint']
            self._mask_footprint = extras['_mask_footprint']
            self._point_shape = extras['_point_shape']
            self._placements = extras['_placements']
            self._baseline = extras['_baseline']

        else:
            # fill out the shapes above
            self._populate_placements(preferred)
            self._populate_shapes()

        # label bounds for current placement
        self._label_shape = self._label_shapes[self.placement]

        # mask shape for current placement
        self._mask_shape = self._mask_shapes[self.placement]

    def __repr__(self):
        return '<Place: %s>' % self.name
    
    def __hash__(self):
        return id(self)
    
    def __deepcopy__(self, memo_dict):
        """ Override deep copy to spend less time copying.
        
            Profiling showed that a significant percentage of time was spent
            deep-copying annealer state from step to step, and testing with
            z5 U.S. data shows a 4000% speed increase, so yay.
        """
        extras = dict(placement = self.placement,
                      _label_shapes = self._label_shapes,
                      _mask_shapes = self._mask_shapes,
                      _label_footprint = self._label_footprint,
                      _mask_footprint = self._mask_footprint,
                      _point_shape = self._point_shape,
                      _placements = self._placements,
                      _baseline = self._baseline)
        
        return Place(self.name, self.fontfile, self.fontsize, self.location,
                     self.position, self.radius, self.properties, self.rank, **extras)
    
    def _populate_shapes(self):
        """ Set values for self._label_shapes, _footprint_shape, and others.
        """
        point = Point(self.position.x, self.position.y)
        point_buffered = point.buffer(self.radius + self.buffer, 3)
        self._point_shape = point.buffer(self.radius, 3)
        
        scale = 10.0
        font = truetype(self.fontfile, int(self.fontsize * scale), encoding='unic')

        x, y = self.position.x, self.position.y
        w, h = font.getsize(self.name)
        w, h = w/scale, h/scale
        
        for placement in placements:
            label_shape = point_label_bounds(x, y, w, h, self.radius, placement)
            mask_shape = label_shape.buffer(self.buffer, 2).union(point_buffered)
            
            self._label_shapes[placement] = label_shape
            self._mask_shapes[placement] = mask_shape
    
        unionize = lambda a, b: a.union(b)
        self._label_footprint = reduce(unionize, self._label_shapes.values())
        self._mask_footprint = reduce(unionize, self._mask_shapes.values())
        
        # number of pixels from the top of the label based on the bottom of a "."
        self._baseline = font.getmask('.').getbbox()[3] / scale
    
    def _populate_placements(self, preferred):
        """ Set values for self._placements.
        """
        # local copy of placement energies
        self._placements = deepcopy(placements)
        
        # top right is the Imhof-approved default
        if preferred == 'top right' or not preferred:
            return
        
        # bump up the cost of every placement artificially to leave room for new preferences
        self._placements = dict([ (key, .4 + v*.6) for (key, v) in self._placements.items() ])
        
        if preferred == 'top':
            self.placement = N
            self._placements.update({ N: .0, NNW: .3, NNE: .3 })
        
        elif preferred == 'top left':
            self.placement = NW
            self._placements.update({ NW: .0, WNW: .1, NNW: .1 })
        
        elif preferred == 'bottom':
            self.placement = S
            self._placements.update({ S: .0, SSW: .3, SSE: .3 })
        
        elif preferred == 'bottom right':
            self.placement = SE
            self._placements.update({ SE: .0, ESE: .1, SSE: .1 })
        
        elif preferred == 'bottom left':
            self.placement = SW
            self._placements.update({ SW: .0, WSW: .1, SSW: .1 })
        
        else:
            raise Exception('Unknown preferred placement "%s"' % preferred)
    
    def text(self):
        """ Return text content, font file and size.
        """
        return self.name, self.fontfile, self.fontsize
    
    def label(self):
        """ Return a label polygon, the bounds of the current label shape.
        """
        return self._label_shape
    
    def registration(self):
        """ Return a registration point and text justification.
        """
        xmin, ymin, xmax, ymax = self._label_shape.bounds
        y = ymin + self._baseline
        
        if self.placement in (NNE, NE, ENE, ESE, SE, SSE):
            x, justification = xmin, 'left'

        elif self.placement in (S, N):
            x, justification = xmin/2 + xmax/2, 'center'

        elif self.placement in (SSW, SW, WSW, WNW, NW, NNW):
            x, justification = xmax, 'right'
        
        return Point(x, y), justification
    
    def footprint(self):
        """ Return a footprint polygon, the total coverage of all placements.
        """
        return self._label_footprint
    
    def move(self):
        self.placement = choice(self._placements.keys())
        self._label_shape = self._label_shapes[self.placement]
        self._mask_shape = self._mask_shapes[self.placement]
    
    def placement_energy(self):
        return self._placements[self.placement]
    
    def overlaps(self, other, reflexive=True):
        overlaps = self._mask_shape.intersects(other.label())
        
        if reflexive:
            overlaps |= other.overlaps(self, False)

        return overlaps

    def can_overlap(self, other, reflexive=True):
        can_overlap = self._mask_footprint.intersects(other.footprint())
        
        if reflexive:
            can_overlap |= other.can_overlap(self, False)

        return can_overlap

def point_label_bounds(x, y, width, height, radius, placement):
    """ Rectangular area occupied by a label placed by a point with radius.
    """
    if placement in (NE, ENE, ESE, SE):
        # to the right
        x += radius + width/2
    
    if placement in (NW, WNW, WSW, SW):
        # to the left
        x -= radius + width/2

    if placement in (NW, NE):
        # way up high
        y -= height/2

    if placement in (SW, SE):
        # way down low
        y += height/2

    if placement in (ENE, WNW):
        # just a little above
        y -= height/6

    if placement in (ESE, WSW):
        # just a little below
        y += height/6
    
    if placement in (NNE, SSE, SSW, NNW):
        _x = radius * cos(pi/4) + width/2
        _y = radius * sin(pi/4) + height/2
        
        if placement in (NNE, SSE):
            x += _x
        else:
            x -= _x
        
        if placement in (SSE, SSW):
            y += _y
        else:
            y -= _y
    
    if placement == N:
        # right on top
        y -= radius + height / 2
    
    if placement == S:
        # right on the bottom
        y += radius + height / 2
    
    x1, y1 = x - width/2, y - height/2
    x2, y2 = x + width/2, y + height/2
    
    return Polygon(((x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)))

class NothingToDo (Exception):
    pass

class Places:

    def __init__(self, keep_chain=False, **extras):
        self.keep_chain = keep_chain
    
        full_extras = 'energy' in extras \
                  and 'previous' in extras \
                  and '_places' in extras \
                  and '_neighbors' in extras \
                  and '_moveable' in extras
        
        if full_extras:
            # use the provided extras
            self.energy = extras['energy']
            self.previous = extras['previous']
            self._places = extras['_places']
            self._neighbors = extras['_neighbors']
            self._moveable = extras['_moveable']

        else:
            self.energy = 0.0
            self.previous = None

            self._places = []    # core list of places
            self._neighbors = {} # dictionary of neighbor sets
            self._moveable = []  # list of only this places that should be moved

    def __iter__(self):
        return iter(self._places)
    
    def __deepcopy__(self, memo_dict):
        """
        """
        extras = dict(energy = self.energy,
                      previous = (self.keep_chain and self or None),
                      _places = deepcopy(self._places, memo_dict),
                      _neighbors = deepcopy(self._neighbors, memo_dict),
                      _moveable = deepcopy(self._moveable, memo_dict))
        
        return Places(self.keep_chain, **extras)

    def add(self, place):
        self._neighbors[place] = set()
    
        # calculate neighbors
        for other in self._places:
            if not place.can_overlap(other):
                continue

            self.energy += self._overlap_energy(place, other)

            self._moveable.append(place)
            self._neighbors[place].add(other)
            self._neighbors[other].add(place)
            
            if other not in self._moveable:
                self._moveable.append(other)

        self.energy += place.placement_energy()
        self._places.append(place)
        
        return self._neighbors[place]

    def _overlap_energy(self, this, that):
        """ Energy of an overlap between two places, if it exists.
        """
        if not this.overlaps(that):
            return 0.0

        return min(10.0 / this.rank, 10.0 / that.rank)
    
    def move(self):
        if len(self._moveable) == 0:
            raise NothingToDo('Zero places')
    
        place = choice(self._moveable)
        
        for other in self._neighbors[place]:
            self.energy -= self._overlap_energy(place, other)

        self.energy -= place.placement_energy()

        place.move()
        
        for other in self._neighbors[place]:
            self.energy += self._overlap_energy(place, other)

        self.energy += place.placement_energy()

########NEW FILE########
__FILENAME__ = dymo-label
from optparse import OptionParser
from copy import copy, deepcopy
import cPickle
import json

from Dymo.anneal import Annealer
from Dymo.index import FootprintIndex
from Dymo.places import Places, NothingToDo
from Dymo import load_places, point_lonlat

optparser = OptionParser(usage="""%prog [options] --labels-file <label output file> --places-file <point output file> --registrations-file <registration output file> <input file 1> [<input file 2>, ...]

There are two ways to run the label placer. The slow, default way performs a
test to figure out the best parameters for the simulated annealing algorithm
before running it. The faster, more advanced way required that you know what
your minimum and maximum temperatures and appropriate number of steps are before
you start, which usually means that you've run the annealer once the slow way
and now want to redo your results on the same data the fast way.

Input fields:

  preferred placement
    Optional preference for point placement, one of "top right" (the default),
    "top", "top left", "bottom left", "bottom", or "bottom right".

Examples:

  Place U.S. city labels at zoom 6 for two minutes:
  > python dymo-label.py -z 6 --minutes 2 --labels-file labels.json --places-file points.json data/US-z6.csv.gz

  Place U.S. city labels at zoom 5 over a 10000-iteration 10.0 - 0.01 temperature range:
  > python dymo-label.py -z 5 --steps 10000 --max-temp 10 --min-temp 0.01 -l labels.json -p points.json data/US-z5.csv""")

defaults = dict(minutes=2, zoom=18, dump_skip=100, include_overlaps=False)

optparser.set_defaults(**defaults)

optparser.add_option('-m', '--minutes', dest='minutes',
                     type='float', help='Number of minutes to run annealer. Default value is %(minutes).1f.' % defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Map zoom level. Default value is %(zoom)d.' % defaults)

optparser.add_option('-l', '--labels-file', dest='labels_file',
                     help='Optional name of labels file to generate.')

optparser.add_option('-p', '--places-file', dest='places_file',
                     help='Optional name of place points file to generate.')

optparser.add_option('-r', '--registrations-file', dest='registrations_file',
                     help='Optional name of registration points file to generate. This file will have an additional "justified" property with values "left", "center", or "right".')

optparser.add_option('--min-temp', dest='temp_min',
                     type='float', help='Minimum annealing temperature, for more precise control than specifying --minutes.')

optparser.add_option('--max-temp', dest='temp_max',
                     type='float', help='Maximum annealing temperature, for more precise control than specifying --minutes.')

optparser.add_option('--steps', dest='steps',
                     type='int', help='Number of annealing steps, for more precise control than specifying --minutes.')

optparser.add_option('--include-overlaps', dest='include_overlaps',
                     action='store_true', help='Include lower-priority places when they overlap higher-priority places. Default behavior is to skip the overlapping cities.')

optparser.add_option('--dump-file', dest='dump_file',
                     help='Optional filename for a sequential dump of pickled annealer states. This all has to be stored in memory, so for a large job specifying this option could use up all available RAM.')

optparser.add_option('--dump-skip', dest='dump_skip',
                     type='int', help='Optional number of states to skip for each state in the dump file.')

if __name__ == '__main__':
    
    options, input_files = optparser.parse_args()
    
    if not input_files:
        print 'Missing input file(s).\n'
        optparser.print_usage()
        exit(1)
    elif not (options.labels_file or options.places_file or options.registrations_file):
        print 'Missing output file(s): labels, place points, or registration points.\n'
        optparser.print_usage()
        exit(1)
    
    places = Places(bool(options.dump_file))
    
    for place in load_places(input_files, options.zoom):
        places.add(place)
    
    def state_energy(places):
        return places.energy

    def state_move(places):
        places.move()

    try:
        annealer = Annealer(state_energy, state_move)
        
        if options.temp_min and options.temp_max and options.steps:
            places, e = annealer.anneal(places, options.temp_max, options.temp_min, options.steps, 30)
        else:
            places, e = annealer.auto(places, options.minutes, 500)

    except NothingToDo:
        pass
    
    label_data = {'type': 'FeatureCollection', 'features': []}
    place_data = {'type': 'FeatureCollection', 'features': []}
    rgstr_data = {'type': 'FeatureCollection', 'features': []}
    
    placed = FootprintIndex(options.zoom)
    
    for place in places:
        blocker = placed.blocks(place)
        overlaps = bool(blocker)
        
        if blocker:
            print blocker.name, 'blocks', place.name
        else:
            placed.add(place)
        
        properties = copy(place.properties)
        
        if options.include_overlaps:
            properties['overlaps'] = int(overlaps) # 1 or 0
        elif overlaps:
            continue
        
        lonlat = lambda xy: point_lonlat(xy[0], xy[1], options.zoom)
        label_coords = [map(lonlat, place.label().envelope.exterior.coords)]

        label_feature = {'type': 'Feature', 'properties': properties}
        label_feature['geometry'] = {'type': 'Polygon', 'coordinates': label_coords}

        label_data['features'].append(label_feature)

        point_feature = {'type': 'Feature', 'properties': properties}
        point_feature['geometry'] = {'type': 'Point', 'coordinates': [place.location.lon, place.location.lat]}
        place_data['features'].append(deepcopy(point_feature))
        
        reg_point, justification = place.registration()
        point_feature['geometry']['coordinates'] = lonlat((reg_point.x, reg_point.y))
        point_feature['properties']['justified'] = justification
        
        rgstr_data['features'].append(point_feature)
    
    if options.labels_file:
        json.dump(label_data, open(options.labels_file, 'w'), indent=2)

    if options.places_file:
        json.dump(place_data, open(options.places_file, 'w'), indent=2)
    
    if options.registrations_file:
        json.dump(rgstr_data, open(options.registrations_file, 'w'), indent=2)
    
    if options.dump_file:
        frames = []
        
        while places.previous:
            current, places = places, places.previous
            current.previous = None # don't pickle too much per state
            frames.append(current)
        
        frames = [frames[i] for i in range(0, len(frames), options.dump_skip)]
        frames.reverse()
        
        print 'Pickling', len(frames), 'states to', options.dump_file
        
        cPickle.dump(frames, open(options.dump_file, 'w'))

########NEW FILE########
__FILENAME__ = dymo-prepare-places
from gzip import GzipFile
from sys import argv, stderr
from os.path import splitext
from csv import DictReader, writer
from optparse import OptionParser

from ModestMaps.Geo import Location

from Dymo.index import PointIndex

optparser = OptionParser(usage="""%prog [options] <input file> <output file>

Convert files with complete city lists to files with zoom-dependent lists.

Input columns must include zoom start and population.
Output columns will add point size, font size, and font file.

Example input columns:
  zoom start, geonameid, name, asciiname, latitude, longitude, country code,
  capital, admin1 code, population.

Example output columns:
  zoom start, geonameid, name, asciiname, latitude, longitude, country code,
  capital, admin1 code, population, point size, font size, font file.

Optional pixel buffer radius option (--radius) defines a minimum distance
between places that can be used to cull the list prior to annealing.""")

defaults = dict(fonts=[(-1, 'fonts/DejaVuSans.ttf', 12)], zoom=4, radius=0, font_field='population')

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Maximum zoom level. Default value is %(zoom)d.' % defaults)

optparser.add_option('-f', '--font', dest='fonts', action='append', nargs=3,
                     help='Additional font, in the form of three values: minimum population (or other font field), font file, font size. Can be specified multiple times.')

optparser.add_option('-r', '--radius', dest='radius',
                     type='float', help='Pixel buffer around each place. Default value is %(radius)d.' % defaults)

optparser.add_option('--font-field', dest='font_field',
                     help='Field to use for font selection. Default field is %(font_field)s.' % defaults)

def prepare_file(name, mode):
    """
    """
    base, ext = splitext(name)
    
    if ext == '.gz':
        file = GzipFile(name, mode)
        name = base
    elif ext in ('.csv', '.txt', '.tsv'):
        file = open(name, mode)
    else:
        raise Exception('Bad extension "%(ext)s" in "%(name)s"' % locals())
    
    base, ext = splitext(name)
    
    if ext == '.csv':
        dialect = 'excel'
    elif ext in ('.txt', '.tsv'):
        dialect = 'excel-tab'
    else:
        raise Exception('Bad extension "%(ext)s" in "%(name)s"' % locals())

    if mode == 'r':
        return DictReader(file, dialect=dialect)
    elif mode == 'w':
        return writer(file, dialect=dialect)

if __name__ == '__main__':

    options, (input, output) = optparser.parse_args()

    fonts = [(int(min), font, size) for (min, font, size) in options.fonts]
    fonts.sort()
    
    #
    # prepare input/output files
    #
    input = prepare_file(input, 'r')
    output = prepare_file(output, 'w')
    
    #
    # prepare columns
    #
    fields = input.fieldnames[:]
    
    fields.append('point size')
    fields.append('font size')
    fields.append('font file')
    
    #
    # get cracking
    #
    output.writerow(fields)
    
    if options.radius > 0:
        others = PointIndex(options.zoom, options.radius)
    
    for place in input:
        if 'point size' not in place:
            place['point size'] = '8'
        
        if int(place['zoom start']) > options.zoom:
            continue
        
        if options.radius > 0:
            try:
                loc = Location(float(place['latitude']), float(place['longitude']))
            except KeyError:
                try:
                    loc = Location(float(place['lat']), float(place['long']))
                except KeyError:
                    loc = Location(float(place['lat']), float(place['lon']))
            other = others.blocks(loc)
            
            if other:
                print >> stderr, place['name'], 'blocked by', other
                continue
        
            others.add(place['name'], loc)
        
        try:
            value = int(place[options.font_field])
        except ValueError:
            value = place[options.font_field]
    
        for (min_value, font, size) in fonts:
            if value > min_value:
                place['font file'] = font
                place['font size'] = size
    
        output.writerow([place.get(field, None) for field in fields])

########NEW FILE########
__FILENAME__ = anneal
#!/usr/bin/env python

# Python module for simulated annealing - anneal.py - v1.0 - 2 Sep 2009
# 
# Copyright (c) 2009, Richard J. Wagner <wagnerr@umich.edu>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This module performs simulated annealing to find a state of a system that
minimizes its energy.

An example program demonstrates simulated annealing with a traveling
salesman problem to find the shortest route to visit the twenty largest
cities in the United States.
"""

# How to optimize a system with simulated annealing:
# 
# 1) Define a format for describing the state of the system.
# 
# 2) Define a function to calculate the energy of a state.
# 
# 3) Define a function to make a random change to a state.
# 
# 4) Choose a maximum temperature, minimum temperature, and number of steps.
# 
# 5) Set the annealer to work with your state and functions.
# 
# 6) Study the variation in energy with temperature and duration to find a
# productive annealing schedule.
# 
# Or,
# 
# 4) Run the automatic annealer which will attempt to choose reasonable values
# for maximum and minimum temperatures and then anneal for the allotted time.

import copy, math, random, sys, time

def round_figures(x, n):
	"""Returns x rounded to n significant figures."""
	return round(x, int(n - math.ceil(math.log10(abs(x)))))

def time_string(seconds):
	"""Returns time in seconds as a string formatted HHHH:MM:SS."""
	s = int(round(seconds))  # round to nearest second
	h, s = divmod(s, 3600)   # get hours and remainder
	m, s = divmod(s, 60)     # split remainder into minutes and seconds
	return '%4i:%02i:%02i' % (h, m, s)

class Annealer:
	"""Performs simulated annealing by calling functions to calculate
	energy and make moves on a state.  The temperature schedule for
	annealing may be provided manually or estimated automatically.
	"""
	def __init__(self, energy, move):
		self.energy = energy  # function to calculate energy of a state
		self.move = move      # function to make a random change to a state
	
	def anneal(self, state, Tmax, Tmin, steps, updates=0):
		"""Minimizes the energy of a system by simulated annealing.
		
		Keyword arguments:
		state -- an initial arrangement of the system
		Tmax -- maximum temperature (in units of energy)
		Tmin -- minimum temperature (must be greater than zero)
		steps -- the number of steps requested
		updates -- the number of updates to print during annealing
		
		Returns the best state and energy found."""
		
		step = 0
		start = time.time()
		
		def update(T, E, acceptance, improvement):
			"""Prints the current temperature, energy, acceptance rate,
			improvement rate, elapsed time, and remaining time.
			
			The acceptance rate indicates the percentage of moves since the last
			update that were accepted by the Metropolis algorithm.  It includes
			moves that decreased the energy, moves that left the energy
			unchanged, and moves that increased the energy yet were reached by
			thermal excitation.
			
			The improvement rate indicates the percentage of moves since the
			last update that strictly decreased the energy.  At high
			temperatures it will include both moves that improved the overall
			state and moves that simply undid previously accepted moves that
			increased the energy by thermal excititation.  At low temperatures
			it will tend toward zero as the moves that can decrease the energy
			are exhausted and moves that would increase the energy are no longer
			thermally accessible."""
			
			elapsed = time.time() - start
			if step == 0:
				print ' Temperature        Energy    Accept   Improve     Elapsed   Remaining'
				print '%12.2f  %12.2f                      %s            ' % \
					(T, E, time_string(elapsed) )
			else:
				remain = ( steps - step ) * ( elapsed / step )
				print '%12.2f  %12.2f  %7.2f%%  %7.2f%%  %s  %s' % \
					(T, E, 100.0*acceptance, 100.0*improvement,
						time_string(elapsed), time_string(remain))
		
		# Precompute factor for exponential cooling from Tmax to Tmin
		if Tmin <= 0.0:
			print 'Exponential cooling requires a minimum temperature greater than zero.'
			sys.exit()
		Tfactor = -math.log( float(Tmax) / Tmin )
		
		# Note initial state
		T = Tmax
		E = self.energy(state)
		prevState = copy.deepcopy(state)
		prevEnergy = E
		bestState = copy.deepcopy(state)
		bestEnergy = E
		trials, accepts, improves = 0, 0, 0
		if updates > 0:
			updateWavelength = float(steps) / updates
			update(T, E, None, None)
		
		# Attempt moves to new states
		while step < steps:
			step += 1
			T = Tmax * math.exp( Tfactor * step / steps )
			self.move(state)
			E = self.energy(state)
			dE = E - prevEnergy
			trials += 1
			if dE > 0.0 and math.exp(-dE/T) < random.random():
				# Restore previous state
				state = copy.deepcopy(prevState)
				E = prevEnergy
			else:
				# Accept new state and compare to best state
				accepts += 1
				if dE < 0.0:
					improves += 1
				prevState = copy.deepcopy(state)
				prevEnergy = E
				if E < bestEnergy:
					bestState = copy.deepcopy(state)
					bestEnergy = E
			if updates > 1:
				if step // updateWavelength > (step-1) // updateWavelength:
					update(T, E, float(accepts)/trials, float(improves)/trials)
					trials, accepts, improves = 0, 0, 0
		
		# Return best state and energy
		return bestState, bestEnergy
	
	def auto(self, state, minutes, steps=2000):
		"""Minimizes the energy of a system by simulated annealing with
		automatic selection of the temperature schedule.
		
		Keyword arguments:
		state -- an initial arrangement of the system
		minutes -- time to spend annealing (after exploring temperatures)
		steps -- number of steps to spend on each stage of exploration
		
		Returns the best state and energy found."""
		
		def run(state, T, steps):
			"""Anneals a system at constant temperature and returns the state,
			energy, rate of acceptance, and rate of improvement."""
			E = self.energy(state)
			prevState = copy.deepcopy(state)
			prevEnergy = E
			accepts, improves = 0, 0
			for step in range(steps):
				self.move(state)
				E = self.energy(state)
				dE = E - prevEnergy
				if dE > 0.0 and math.exp(-dE/T) < random.random():
					state = copy.deepcopy(prevState)
					E = prevEnergy
				else:
					accepts += 1
					if dE < 0.0:
						improves += 1
					prevState = copy.deepcopy(state)
					prevEnergy = E
			return state, E, float(accepts)/steps, float(improves)/steps
		
		step = 0
		start = time.time()
		
		print 'Attempting automatic simulated anneal...'
		
		# Find an initial guess for temperature
		T = 0.0
		E = self.energy(state)
		while T == 0.0:
			step += 1
			self.move(state)
			T = abs( self.energy(state) - E )
		
		print 'Exploring temperature landscape:'
		print ' Temperature        Energy    Accept   Improve     Elapsed'
		def update(T, E, acceptance, improvement):
			"""Prints the current temperature, energy, acceptance rate,
			improvement rate, and elapsed time."""
			elapsed = time.time() - start
			print '%12.2f  %12.2f  %7.2f%%  %7.2f%%  %s' % \
				(T, E, 100.0*acceptance, 100.0*improvement, time_string(elapsed))
		
		# Search for Tmax - a temperature that gives 98% acceptance
		state, E, acceptance, improvement = run(state, T, steps)
		step += steps
		while acceptance > 0.98:
			T = round_figures(T/1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		while acceptance < 0.98:
			T = round_figures(T*1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		Tmax = T
		
		# Search for Tmin - a temperature that gives 0% improvement
		while improvement > 0.0:
			T = round_figures(T/1.5, 2)
			state, E, acceptance, improvement = run(state, T, steps)
			step += steps
			update(T, E, acceptance, improvement)
		Tmin = T
		
		# Calculate anneal duration
		elapsed = time.time() - start
		duration = round_figures(int(60.0 * minutes * step / elapsed), 2)
		
		# Perform anneal
		print 'Annealing from %.6f to %.6f over %i steps:' % (Tmax, Tmin, duration)
		return self.anneal(state, Tmax, Tmin, duration, 20)

if __name__ == '__main__':
	"""Test annealer with a traveling salesman problem."""
	
	# List latitude and longitude (degrees) for the twenty largest U.S. cities
	cities = { 'New York City': (40.72,74.00), 'Los Angeles': (34.05,118.25),
	'Chicago': (41.88,87.63), 'Houston': (29.77,95.38),
	'Phoenix': (33.45,112.07), 'Philadelphia': (39.95,75.17),
	'San Antonio': (29.53,98.47), 'Dallas': (32.78,96.80),
	'San Diego': (32.78,117.15), 'San Jose': (37.30,121.87),
	'Detroit': (42.33,83.05), 'San Francisco': (37.78,122.42),
	'Jacksonville': (30.32,81.70), 'Indianapolis': (39.78,86.15),
	'Austin': (30.27,97.77), 'Columbus': (39.98,82.98),
	'Fort Worth': (32.75,97.33), 'Charlotte': (35.23,80.85),
	'Memphis': (35.12,89.97), 'Baltimore': (39.28,76.62) }
	
	def distance(a, b):
		"""Calculates distance between two latitude-longitude coordinates."""
		R = 3963  # radius of Earth (miles)
		lat1, lon1 = math.radians(a[0]), math.radians(a[1])
		lat2, lon2 = math.radians(b[0]), math.radians(b[1])
		return math.acos( math.sin(lat1)*math.sin(lat2) +
			math.cos(lat1)*math.cos(lat2)*math.cos(lon1-lon2) ) * R
	
	def route_move(state):
		"""Swaps two cities in the route."""
		a = random.randint( 0, len(state)-1 )
		b = random.randint( 0, len(state)-1 )
		state[a], state[b] = state[b], state[a]
	
	def route_energy(state):
		"""Calculates the length of the route."""
		e = 0
		for i in range(len(state)):
			e += distance( cities[state[i-1]], cities[state[i]] )
		return e
	
	# Start with the cities listed in random order
	state = cities.keys()
	random.shuffle(state)
	
	# Minimize the distance to be traveled by simulated annealing with a
	# manually chosen temperature schedule
	annealer = Annealer(route_energy, route_move)
	state, e = annealer.anneal(state, 10000000, 0.01, 18000*len(state), 9)
	while state[0] != 'New York City':
		state = state[1:] + state[:1]  # rotate NYC to start
	print "%i mile route:" % route_energy(state)
	for city in state:
		print "\t", city
	
	# Minimize the distance to be traveled by simulated annealing with an
	# automatically chosen temperature schedule
	state, e = annealer.auto(state, 4)
	while state[0] != 'New York City':
		state = state[1:] + state[:1]  # rotate NYC to start
	print "%i mile route:" % route_energy(state)
	for city in state:
		print "\t", city
	
	sys.exit()

########NEW FILE########
__FILENAME__ = index
from math import ceil, log
from itertools import product

from shapely.geometry import Point

from ModestMaps.OpenStreetMap import Provider
from ModestMaps.Core import Coordinate

class PointIndex:
    """ Primitive quadtree for checking collisions based on a known radius.
    """
    def __init__(self, zoom, radius):
        """ Zoom is the base zoom level we're annealing to, radius is
            the pixel radius around each place to check for collisions.
        """
        self.zpixel = zoom + 8
        self.zgroup = zoom + 8 - ceil(log(radius * 2) / log(2))
        self.radius = radius
        self.quads = {}
        
        self.locationCoordinate = Provider().locationCoordinate
    
    def add(self, name, location):
        """ Add a new place name and location to the index.
        """
        coord = self.locationCoordinate(location).zoomTo(self.zpixel)
        point = Point(coord.column, coord.row)
        
        # buffer the location by radius and get its bbox
        area = point.buffer(self.radius, 4)
        xmin, ymin, xmax, ymax = area.bounds

        # a list of quads that the buffered location overlaps
        quads = [quadkey(Coordinate(y, x, self.zpixel).zoomTo(self.zgroup))
                 for (x, y) in ((xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin))]
        
        # store name + area shape
        for quad in set(quads):
            if quad in self.quads:
                self.quads[quad].append((name, area))
            else:
                self.quads[quad] = [(name, area)]
    
    def blocks(self, location):
        """ If the location is blocked by some other location
            in the index, return the blocker's name or False.
        """
        coord = self.locationCoordinate(location).zoomTo(self.zpixel)
        point = Point(coord.column, coord.row)
        
        # figure out which quad the point is in
        key = quadkey(coord.zoomTo(self.zgroup))
        
        # first try the easy hash check
        if key not in self.quads:
            return False

        # then do the expensive shape check
        for (name, area) in self.quads[key]:
            if point.intersects(area):
                # ensure name evals to true
                return name or True
        
        return False

class FootprintIndex:
    """ Primitive quadtree for checking collisions based on footprints.
    """
    def __init__(self, geometry):
        """ Geometry is one of GeometryCustom or GeometryWebmercator.
        """
        self.geometry = geometry
        self.quads = {}
    
    def _areaQuads(self, area):
        """
        """
        xmin, ymin, xmax, ymax = area.bounds
        
        xs = range(int(xmin / 100.0), 1 + int(ceil(xmax / 100.0)))
        ys = range(int(ymin / 100.0), 1 + int(ceil(ymax / 100.0)))
        
        quads = set()
        
        for (x, y) in product(xs, ys):
            quads.add((x, y))
        
        return quads
        
    def add(self, place):
        """ Add a new place to the index.
        """
        for quad in self._areaQuads(place.footprint()):
            if quad in self.quads:
                self.quads[quad].append(place)
            else:
                self.quads[quad] = [place]
    
    def blocks(self, place):
        """ If the place is blocked by some other place in
            the index, return the blocking place or False.
        """
        # figure out which quads the area covers
        quads = self._areaQuads(place.footprint())
        
        # now just the quads we already know about
        quads = [key for key in quads if key in self.quads]
        
        for key in quads:
            for other in self.quads[key]:
                if place.overlaps(other):
                    return other
        
        return False

def quadkey(coord):
    return '%(row)d-%(column)d-%(zoom)d' % coord.container().__dict__

########NEW FILE########
__FILENAME__ = places
from math import pi, sin, cos
from random import choice
from copy import deepcopy

try:
    from PIL.ImageFont import truetype
except ImportError:
    from ImageFont import truetype

from shapely.geometry import Point, Polygon

NE, ENE, ESE, SE, SSE, S, SSW, SW, WSW, WNW, NW, NNW, N, NNE = range(14)

#
#          NNW   N   NNE
#        NW             NE
#       WNW      .      ENE
#       WSW             ESE
#        SW             SE
#          SSW   S   SSE
#
# slide 13 of http://www.cs.uu.nl/docs/vakken/gd/steven2.pdf
#
placements = {NE: 0.000, ENE: 0.070, ESE: 0.100, SE: 0.175, SSE: 0.200,
              S: 0.900, SSW: 1.000, SW: 0.600, WSW: 0.500, WNW: 0.470,
              NW: 0.400, NNW: 0.575, N: 0.800, NNE: 0.150}

class Place:

    def __init__(self, name, fontfile, fontsize, location, position, radius, properties, rank=1, preferred=None, **extras):
        
        if location.lon < -360 or 360 < location.lon:
            raise Exception('Silly human trying to pass an invalid longitude of %.3f for "%s"' % (location.lon, name))
    
        if location.lat < -90 or 90 < location.lat:
            raise Exception('Silly human trying to pass an invalid latitude of %.3f for "%s"' % (location.lat, name))
    
        self.name = name
        self.location = location
        self.position = position
        self.rank = rank
        
        self.fontfile = fontfile
        self.fontsize = fontsize
        self.properties = properties
    
        self.placement = NE
        self.radius = radius
        self.buffer = 2
        
        self._label_shapes = {}      # dictionary of label bounds by placement
        self._mask_shapes = {}       # dictionary of mask shapes by placement
        self._label_footprint = None # all possible label shapes, together
        self._mask_footprint = None  # all possible mask shapes, together
        self._point_shape = None     # point shape for current placement
        
        full_extras = 'placement' in extras \
                  and '_label_shapes' in extras \
                  and '_mask_shapes' in extras \
                  and '_label_footprint' in extras \
                  and '_mask_footprint' in extras \
                  and '_point_shape' in extras \
                  and '_placements' in extras \
                  and '_baseline' in extras
        
        if full_extras:
            # use the provided extras
            self.placement = extras['placement']
            self._label_shapes = extras['_label_shapes']
            self._mask_shapes = extras['_mask_shapes']
            self._label_footprint = extras['_label_footprint']
            self._mask_footprint = extras['_mask_footprint']
            self._point_shape = extras['_point_shape']
            self._placements = extras['_placements']
            self._baseline = extras['_baseline']

        else:
            # fill out the shapes above
            self._populate_placements(preferred)
            self._populate_shapes()

        # label bounds for current placement
        self._label_shape = self._label_shapes[self.placement]

        # mask shape for current placement
        self._mask_shape = self._mask_shapes[self.placement]

    def __repr__(self):
        return '<Place: %s>' % self.name
    
    def __hash__(self):
        return id(self)
    
    def __deepcopy__(self, memo_dict):
        """ Override deep copy to spend less time copying.
        
            Profiling showed that a significant percentage of time was spent
            deep-copying annealer state from step to step, and testing with
            z5 U.S. data shows a 4000% speed increase, so yay.
        """
        extras = dict(placement = self.placement,
                      _label_shapes = self._label_shapes,
                      _mask_shapes = self._mask_shapes,
                      _label_footprint = self._label_footprint,
                      _mask_footprint = self._mask_footprint,
                      _point_shape = self._point_shape,
                      _placements = self._placements,
                      _baseline = self._baseline)
        
        return Place(self.name, self.fontfile, self.fontsize, self.location,
                     self.position, self.radius, self.properties, self.rank, **extras)
    
    def _populate_shapes(self):
        """ Set values for self._label_shapes, _footprint_shape, and others.
        """
        point = Point(self.position.x, self.position.y)
        point_buffered = point.buffer(self.radius + self.buffer, 3)
        self._point_shape = point.buffer(self.radius, 3)
        
        scale = 10.0
        font = truetype(self.fontfile, int(self.fontsize * scale), encoding='unic')

        x, y = self.position.x, self.position.y
        w, h = font.getsize(self.name)
        w, h = w/scale, h/scale
        
        for placement in placements:
            label_shape = point_label_bounds(x, y, w, h, self.radius, placement)
            mask_shape = label_shape.buffer(self.buffer, 2).union(point_buffered)
            
            self._label_shapes[placement] = label_shape
            self._mask_shapes[placement] = mask_shape
    
        unionize = lambda a, b: a.union(b)
        self._label_footprint = reduce(unionize, self._label_shapes.values())
        self._mask_footprint = reduce(unionize, self._mask_shapes.values())
        
        # number of pixels from the top of the label based on the bottom of a "."
        self._baseline = font.getmask('.').getbbox()[3] / scale
    
    def _populate_placements(self, preferred):
        """ Set values for self._placements.
        """
        # local copy of placement energies
        self._placements = deepcopy(placements)
        
        # top right is the Imhof-approved default
        if preferred == 'top right' or not preferred:
            return
        
        # bump up the cost of every placement artificially to leave room for new preferences
        self._placements = dict([ (key, .4 + v*.6) for (key, v) in self._placements.items() ])
        
        if preferred == 'top':
            self.placement = N
            self._placements.update({ N: .0, NNW: .3, NNE: .3 })
        
        elif preferred == 'top left':
            self.placement = NW
            self._placements.update({ NW: .0, WNW: .1, NNW: .1 })
        
        elif preferred == 'bottom':
            self.placement = S
            self._placements.update({ S: .0, SSW: .3, SSE: .3 })
        
        elif preferred == 'bottom right':
            self.placement = SE
            self._placements.update({ SE: .0, ESE: .1, SSE: .1 })
        
        elif preferred == 'bottom left':
            self.placement = SW
            self._placements.update({ SW: .0, WSW: .1, SSW: .1 })
        
        else:
            raise Exception('Unknown preferred placement "%s"' % preferred)
    
    def text(self):
        """ Return text content, font file and size.
        """
        return self.name, self.fontfile, self.fontsize
    
    def label(self):
        """ Return a label polygon, the bounds of the current label shape.
        """
        return self._label_shape
    
    def registration(self):
        """ Return a registration point and text justification.
        """
        xmin, ymin, xmax, ymax = self._label_shape.bounds
        y = ymin + self._baseline
        
        if self.placement in (NNE, NE, ENE, ESE, SE, SSE):
            x, justification = xmin, 'left'

        elif self.placement in (S, N):
            x, justification = xmin/2 + xmax/2, 'center'

        elif self.placement in (SSW, SW, WSW, WNW, NW, NNW):
            x, justification = xmax, 'right'
        
        return Point(x, y), justification
    
    def footprint(self):
        """ Return a footprint polygon, the total coverage of all placements.
        """
        return self._label_footprint
    
    def move(self):
        self.placement = choice(self._placements.keys())
        self._label_shape = self._label_shapes[self.placement]
        self._mask_shape = self._mask_shapes[self.placement]
    
    def placement_energy(self):
        return self._placements[self.placement]
    
    def overlaps(self, other, reflexive=True):
        overlaps = self._mask_shape.intersects(other.label())
        
        if reflexive:
            overlaps |= other.overlaps(self, False)

        return overlaps

    def can_overlap(self, other, reflexive=True):
        can_overlap = self._mask_footprint.intersects(other.footprint())
        
        if reflexive:
            can_overlap |= other.can_overlap(self, False)

        return can_overlap

def point_label_bounds(x, y, width, height, radius, placement):
    """ Rectangular area occupied by a label placed by a point with radius.
    """
    if placement in (NE, ENE, ESE, SE):
        # to the right
        x += radius + width/2
    
    if placement in (NW, WNW, WSW, SW):
        # to the left
        x -= radius + width/2

    if placement in (NW, NE):
        # way up high
        y += height/2

    if placement in (SW, SE):
        # way down low
        y -= height/2

    if placement in (ENE, WNW):
        # just a little above
        y += height/6

    if placement in (ESE, WSW):
        # just a little below
        y -= height/6
    
    if placement in (NNE, SSE, SSW, NNW):
        _x = radius * cos(pi/4) + width/2
        _y = radius * sin(pi/4) + height/2
        
        if placement in (NNE, SSE):
            x += _x
        else:
            x -= _x
        
        if placement in (SSE, SSW):
            y -= _y
        else:
            y += _y
    
    if placement == N:
        # right on top
        y += radius + height / 2
    
    if placement == S:
        # right on the bottom
        y -= radius + height / 2
    
    x1, y1 = x - width/2, y + height/2
    x2, y2 = x + width/2, y - height/2
    
    return Polygon(((x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)))

class NothingToDo (Exception):
    pass

class Places:

    def __init__(self, keep_chain=False, **extras):
        self.keep_chain = keep_chain
    
        full_extras = 'energy' in extras \
                  and 'previous' in extras \
                  and '_places' in extras \
                  and '_neighbors' in extras \
                  and '_moveable' in extras
        
        if full_extras:
            # use the provided extras
            self.energy = extras['energy']
            self.previous = extras['previous']
            self._places = extras['_places']
            self._neighbors = extras['_neighbors']
            self._moveable = extras['_moveable']

        else:
            self.energy = 0.0
            self.previous = None

            self._places = []    # core list of places
            self._neighbors = {} # dictionary of neighbor sets
            self._moveable = []  # list of only this places that should be moved

    def __iter__(self):
        return iter(self._places)
    
    def __deepcopy__(self, memo_dict):
        """
        """
        extras = dict(energy = self.energy,
                      previous = (self.keep_chain and self or None),
                      _places = deepcopy(self._places, memo_dict),
                      _neighbors = deepcopy(self._neighbors, memo_dict),
                      _moveable = deepcopy(self._moveable, memo_dict))
        
        return Places(self.keep_chain, **extras)

    def add(self, place):
        self._neighbors[place] = set()
    
        # calculate neighbors
        for other in self._places:
            if not place.can_overlap(other):
                continue

            self.energy += self._overlap_energy(place, other)

            self._moveable.append(place)
            self._neighbors[place].add(other)
            self._neighbors[other].add(place)
            
            if other not in self._moveable:
                self._moveable.append(other)

        self.energy += place.placement_energy()
        self._places.append(place)
        
        return self._neighbors[place]

    def _overlap_energy(self, this, that):
        """ Energy of an overlap between two places, if it exists.
        """
        if not this.overlaps(that):
            return 0.0

        return min(10.0 / this.rank, 10.0 / that.rank)
    
    def move(self):
        if len(self._moveable) == 0:
            raise NothingToDo('Zero places')
    
        place = choice(self._moveable)
        
        for other in self._neighbors[place]:
            self.energy -= self._overlap_energy(place, other)

        self.energy -= place.placement_energy()

        place.move()
        
        for other in self._neighbors[place]:
            self.energy += self._overlap_energy(place, other)

        self.energy += place.placement_energy()

########NEW FILE########
__FILENAME__ = dymo-label
from optparse import OptionParser
from copy import copy, deepcopy
import cPickle
import json

from Dymo.anneal import Annealer
from Dymo.index import FootprintIndex
from Dymo.places import Places, NothingToDo
from Dymo import load_places, get_geometry

optparser = OptionParser(usage="""%prog [options] --labels-file <label output file> --places-file <point output file> --registrations-file <registration output file> <input file 1> [<input file 2>, ...]

There are two ways to run the label placer. The slow, default way performs a
test to figure out the best parameters for the simulated annealing algorithm
before running it. The faster, more advanced way required that you know what
your minimum and maximum temperatures and appropriate number of steps are before
you start, which usually means that you've run the annealer once the slow way
and now want to redo your results on the same data the fast way.

Input fields:

  preferred placement
    Optional preference for point placement, one of "top right" (the default),
    "top", "top left", "bottom left", "bottom", or "bottom right".

Examples:

  Place U.S. city labels at zoom 6 for two minutes:
  > python dymo-label.py -z 6 --minutes 2 --labels-file labels.json --places-file points.json data/US-z6.csv.gz

  Place U.S. city labels at zoom 5 over a 10000-iteration 10.0 - 0.01 temperature range:
  > python dymo-label.py -z 5 --steps 10000 --max-temp 10 --min-temp 0.01 -l labels.json -p points.json data/US-z5.csv""")

defaults = dict(minutes=2, dump_skip=100, include_overlaps=False, output_projected=False, name_field='name')

optparser.set_defaults(**defaults)

optparser.add_option('-m', '--minutes', dest='minutes',
                     type='float', help='Number of minutes to run annealer. Default value is %(minutes).1f.' % defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Map zoom level. Conflicts with --scale and --projection options. Default value is 18.' % defaults)

optparser.add_option('-l', '--labels-file', dest='labels_file',
                     help='Optional name of labels file to generate.')

optparser.add_option('-p', '--places-file', dest='places_file',
                     help='Optional name of place points file to generate.')

optparser.add_option('-r', '--registrations-file', dest='registrations_file',
                     help='Optional name of registration points file to generate. This file will have an additional "justified" property with values "left", "center", or "right".')

optparser.add_option('--min-temp', dest='temp_min',
                     type='float', help='Minimum annealing temperature, for more precise control than specifying --minutes.')

optparser.add_option('--max-temp', dest='temp_max',
                     type='float', help='Maximum annealing temperature, for more precise control than specifying --minutes.')

optparser.add_option('--steps', dest='steps',
                     type='int', help='Number of annealing steps, for more precise control than specifying --minutes.')

optparser.add_option('--include-overlaps', dest='include_overlaps',
                     action='store_true', help='Include lower-priority places when they overlap higher-priority places. Default behavior is to skip the overlapping cities.')

optparser.add_option('--output-projected', dest='output_projected',
                     action='store_true', help='Optionally output projected coordinates.')

optparser.add_option('--projection', dest='projection',
                     help='Optional PROJ.4 string to use instead of default web spherical mercator.')

optparser.add_option('--scale', dest='scale',
                     type='float', help='Optional scale to use with --projection. Equivalent to +to_meter PROJ.4 parameter, which is not used internally due to not quite working in pyproj. Conflicts with --zoom option. Default value is 1.')

optparser.add_option('--dump-file', dest='dump_file',
                     help='Optional filename for a sequential dump of pickled annealer states. This all has to be stored in memory, so for a large job specifying this option could use up all available RAM.')

optparser.add_option('--dump-skip', dest='dump_skip',
                     type='int', help='Optional number of states to skip for each state in the dump file.')

optparser.add_option('--name-field', dest='name_field',
                     help='Optional name of column for labels to name themselves. Default value is ||name||.' % defaults)


if __name__ == '__main__':
    
    options, input_files = optparser.parse_args()
    
    #
    # Geographic projections
    #
    
    if options.zoom is not None and options.scale is not None:
        print 'Conflicting input: --scale and --zoom can not be used together.\n'
        exit(1)
    
    if options.zoom is not None and options.projection is not None:
        print 'Conflicting input: --projection and --zoom can not be used together.\n'
        exit(1)
    
    if options.zoom is None and options.projection is None and options.scale is None:
        print 'Bad geometry input: need at least one of --zoom, --scale, or --projection.\n'
        exit(1)
    
    geometry = get_geometry(options.projection, options.zoom, options.scale)
    
    #
    # Input and output files.
    #
    
    if not input_files:
        print 'Missing input file(s).\n'
        optparser.print_usage()
        exit(1)
    
    if not (options.labels_file or options.places_file or options.registrations_file):
        print 'Missing output file(s): labels, place points, or registration points.\n'
        optparser.print_usage()
        exit(1)
    
    #
    # Load places.
    #
    
    places = Places(bool(options.dump_file))
    
    for place in load_places(input_files, geometry, options.name_field):
        places.add(place)
    
    def state_energy(places):
        return places.energy

    def state_move(places):
        places.move()

    try:
        annealer = Annealer(state_energy, state_move)
        
        if options.temp_min and options.temp_max and options.steps:
            places, e = annealer.anneal(places, options.temp_max, options.temp_min, options.steps, 30)
        else:
            places, e = annealer.auto(places, options.minutes, 500)

    except NothingToDo:
        pass
    
    label_data = {'type': 'FeatureCollection', 'features': []}
    place_data = {'type': 'FeatureCollection', 'features': []}
    rgstr_data = {'type': 'FeatureCollection', 'features': []}
    
    placed = FootprintIndex(geometry)
    
    for place in places:
        blocker = placed.blocks(place)
        overlaps = bool(blocker)
        
        if blocker:
            print place.name, 'blocked by', blocker.name
            #print place[options.name_field], 'blocked by', blocker[options.name_field]
        else:
            placed.add(place)
        
        properties = copy(place.properties)
        
        if options.include_overlaps:
            properties['overlaps'] = int(overlaps) # 1 or 0
        elif overlaps:
            continue
        
        #
        # Output slightly different geometries depending
        # on whether we want projected or geographic output.
        #
        
        label_feature = {'type': 'Feature', 'properties': properties}
        point_feature = {'type': 'Feature', 'properties': properties}

        label_feature['geometry'] = {'type': 'Polygon', 'coordinates': None}
        point_feature['geometry'] = {'type': 'Point', 'coordinates': None}

        reg_point, justification = place.registration()

        if options.output_projected:
            label_coords = list(place.label().envelope.exterior.coords)
    
            label_feature['geometry']['coordinates'] = label_coords
            label_data['features'].append(label_feature)
    
            point_feature['geometry']['coordinates'] = [place.position.x, place.position.y]
            place_data['features'].append(deepcopy(point_feature))
            
            point_feature['geometry']['coordinates'] = (reg_point.x, reg_point.y)
            
        else:
            lonlat = lambda xy: geometry.point_lonlat(xy[0], xy[1])
            label_coords = [map(lonlat, place.label().envelope.exterior.coords)]
    
            label_feature['geometry']['coordinates'] = label_coords
            label_data['features'].append(label_feature)
    
            point_feature['geometry']['coordinates'] = [place.location.lon, place.location.lat]
            place_data['features'].append(deepcopy(point_feature))
            
            point_feature['geometry']['coordinates'] = lonlat((reg_point.x, reg_point.y))

        point_feature['properties']['justified'] = justification
        rgstr_data['features'].append(point_feature)
    
    if options.labels_file:
        json.dump(label_data, open(options.labels_file, 'w'), indent=2)

    if options.places_file:
        json.dump(place_data, open(options.places_file, 'w'), indent=2)
    
    if options.registrations_file:
        json.dump(rgstr_data, open(options.registrations_file, 'w'), indent=2)
    
    if options.dump_file:
        frames = []
        
        while places.previous:
            current, places = places, places.previous
            current.previous = None # don't pickle too much per state
            frames.append(current)
        
        frames = [frames[i] for i in range(0, len(frames), options.dump_skip)]
        frames.reverse()
        
        print 'Pickling', len(frames), 'states to', options.dump_file
        
        cPickle.dump(frames, open(options.dump_file, 'w'))

########NEW FILE########
__FILENAME__ = dymo-prepare-places
from gzip import GzipFile
from sys import argv, stderr
from os.path import splitext
from csv import DictReader, writer
from optparse import OptionParser

from ModestMaps.Geo import Location

from Dymo import row_location
from Dymo.index import PointIndex

optparser = OptionParser(usage="""%prog [options] <input file> <output file>

Convert files with complete city lists to files with zoom-dependent lists.

Input columns must include zoom start and population.
Output columns will add point size, font size, and font file.

Example input columns:
  zoom start, geonameid, name, asciiname, latitude, longitude, country code,
  capital, admin1 code, population.

Example output columns:
  zoom start, geonameid, name, asciiname, latitude, longitude, country code,
  capital, admin1 code, population, point size, font size, font file.

Optional pixel buffer radius option (--radius) defines a minimum distance
between places that can be used to cull the list prior to annealing.""")

defaults = dict(fonts=[(-1, 'fonts/DejaVuSans.ttf', 12)], zoom=4, radius=0, font_field='population', zoom_field='zoom start', symbol_size=8)

optparser.set_defaults(**defaults)

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Maximum zoom level. Default value is %(zoom)d.' % defaults)

optparser.add_option('--zoom-field', dest='zoom_field', 
                     help='Field to use for limiting selection by zoom. Default field is %(zoom_field)s' % defaults)

optparser.add_option('-f', '--font', dest='fonts', action='append', nargs=3,
                     help='Additional font, in the form of three values: minimum population (or other font field), font file, font size. Can be specified multiple times.')

optparser.add_option('-r', '--radius', dest='radius',
                     type='float', help='Pixel buffer around each place. Default value is %(radius)d.' % defaults)

optparser.add_option('--font-field', dest='font_field',
                     help='Field to use for font selection. Default field is %(font_field)s.' % defaults)

optparser.add_option('--filter-field', dest='filter_field', action='append', nargs=2,
                     help='Field to use for limiting selection by theme and the value to limit by. Default is no filter.')

optparser.add_option('--symbol-size', dest='symbol_size',
                     type='int', help='Size in pixels for implied townspot symbol width/height in pixels. Default size is %(symbol_size)d' % defaults)

optparser.add_option('--symbol-size-field', dest='symbol_size_field',
                     help='Field to use for sizing the implied townspot symbol width/height in pixels. No default.')


def prepare_file(name, mode):
    """
    """
    base, ext = splitext(name)
    
    if ext == '.gz':
        file = GzipFile(name, mode)
        name = base
    elif ext in ('.csv', '.txt', '.tsv'):
        file = open(name, mode)
    else:
        raise Exception('Bad extension "%(ext)s" in "%(name)s"' % locals())
    
    base, ext = splitext(name)
    
    if ext == '.csv':
        dialect = 'excel'
    elif ext in ('.txt', '.tsv'):
        dialect = 'excel-tab'
    else:
        raise Exception('Bad extension "%(ext)s" in "%(name)s"' % locals())

    if mode == 'r':
        return DictReader(file, dialect=dialect)
    elif mode == 'w':
        return writer(file, dialect=dialect)

if __name__ == '__main__':

    options, (input, output) = optparser.parse_args()

    fonts = [(int(min), font, size) for (min, font, size) in options.fonts]
    fonts.sort()
    
    #
    # prepare input/output files
    #
    input = prepare_file(input, 'r')
    output = prepare_file(output, 'w')
    
    #
    # prepare columns
    #
    fields = input.fieldnames[:]
    
    fields.append('point size')
    fields.append('font size')
    fields.append('font file')
    
    #
    # get cracking
    #
    output.writerow(fields)
    
    if options.radius > 0:
        others = PointIndex(options.zoom, options.radius)
        
    for place in input:
        place = dict( [ (key.lower(), value) for (key, value) in place.items() ] )
        
        if options.filter_field: 
            if place[ options.filter_field[0][0] ] != options.filter_field[0][1] :
                continue

        #
        # determine the point size using three pieces of information: the default size,
        # the user-specified value from options, and the value given in the data file.
        #
        
        if options.symbol_size:
            symbol_size = options.symbol_size
        
        if 'point size' in place:
            symbol_size = int(place['symbol size']) or symbol_size
        
        if options.symbol_size_field and options.symbol_size_field in place:
            symbol_size = int(place[options.symbol_size_field]) or symbol_size
        
        #
        # internally Dymo uses "point size" to mean townspot "symbol size", 
        # as measured in points/pixels.
        #
        
        place['point size'] = symbol_size
        
        if int(place[ options.zoom_field ]) > options.zoom:
            continue
        
        if options.radius > 0:
            loc = Location(*row_location(place))
            other = others.blocks(loc)
            
            if other:
                print >> stderr, place['name'], 'blocked by', other
                continue
        
            others.add(place['name'], loc)
        
        try:
            value = int(place[options.font_field.lower()])
        except ValueError:
            value = place[options.font_field.lower()]
    
        for (min_value, font, size) in fonts:
            if value > min_value:
                place['font file'] = font
                place['font size'] = size
    
        output.writerow([place.get(field, None) for field in fields])

########NEW FILE########
__FILENAME__ = mapnik-render
import sys
import glob
import os.path
import cairo
import pyproj
import PIL.Image
import ModestMaps
import optparse

try:
    import mapnik
except ImportError:
    import mapnik2 as mapnik

optparser = optparse.OptionParser(usage="""%prog [options]
""")

defaults = {
    'fonts': 'fonts',
    'stylesheet': 'style.xml',
    'location': (37.804325, -122.271169),
    'zoom': 10,
    'size': (1024, 768),
    'output': 'out.png'
}

optparser.set_defaults(**defaults)

optparser.add_option('-f', '--fonts', dest='fonts',
                     type='string', help='Directory name for fonts. Default value is "%(fonts)s".' % defaults)

optparser.add_option('-s', '--stylesheet', dest='stylesheet',
                     type='string', help='File name of mapnik XML file. Default value is "%(stylesheet)s".' % defaults)

optparser.add_option('-l', '--location', dest='location',
                     nargs=2, type='float', help='Latitude and longitude of map center. Default value is %.6f, %.6f.' % defaults['location'])

optparser.add_option('-z', '--zoom', dest='zoom',
                     type='int', help='Zoom level of rendered map. Default value is %(zoom)d.' % defaults)

optparser.add_option('-d', '--dimensions', dest='size',
                     nargs=2, type='int', help='Width and height of rendered map. Default value is %d, %d.' % defaults['size'])

optparser.add_option('-o', '--output', dest='output',
                     type='string', help='File name of rendered map. Default value is "%(output)s".' % defaults)

if __name__ == '__main__':

    opts, args = optparser.parse_args()

    try:
        fonts = opts.fonts
        stylesheet = opts.stylesheet
        zoom = opts.zoom
        output = opts.output
    
        center = ModestMaps.Geo.Location(*opts.location)
        dimensions = ModestMaps.Core.Point(*opts.size)
        format = output.split(".").pop().lower()
        
        assert zoom >= 0 and zoom <= 19
        assert format in ('png', 'jpg', 'svg', 'pdf', 'ps')
    
        for ttf in glob.glob(os.path.join(fonts, '*.ttf')):
            mapnik.FontEngine.register_font(ttf)

    except Exception, e:
        print >> sys.stderr, e
        print >> sys.stderr, 'Usage: python mapnik-render.py <fonts dir> <stylesheet> <lat> <lon> <zoom> <width> <height> <output jpg/png/svg/pdf/ps>'
        sys.exit(1)

    osm = ModestMaps.OpenStreetMap.Provider()
    map = ModestMaps.mapByCenterZoom(osm, center, zoom, dimensions)
    
    srs = {'proj': 'merc', 'a': 6378137, 'b': 6378137, 'lat_0': 0, 'lon_0': 0, 'k': 1.0, 'units': 'm', 'nadgrids': '@null', 'no_defs': True}
    gym = pyproj.Proj(srs)

    northwest = map.pointLocation(ModestMaps.Core.Point(0, 0))
    southeast = map.pointLocation(dimensions)
    
    left, top = gym(northwest.lon, northwest.lat)
    right, bottom = gym(southeast.lon, southeast.lat)
    
    map = mapnik.Map(dimensions.x, dimensions.y)
    mapnik.load_map(map, stylesheet)
    map.zoom_to_box(mapnik.Envelope(left, top, right, bottom))
    
    img = mapnik.Image(dimensions.x, dimensions.y)
    
    # http://brehaut.net/blog/2010/svg_maps_with_cairo_and_mapnik
    # http://trac.mapnik.org/wiki/MapnikRenderers
    if format in ('svg', 'pdf', 'ps' ) :
        f = open(output, 'w')
        if format == 'svg' :
            surface = cairo.SVGSurface(f.name, dimensions.x, dimensions.y)
        elif format == 'pdf' :
            surface = cairo.PDFSurface(f.name, dimensions.x, dimensions.y)
        else :
            surface = cairo.PSSurface(f.name, dimensions.x, dimensions.y)
        context = cairo.Context(surface)
        mapnik.render(map, context)
        surface.finish()
    else :
        mapnik.render(map, img)
    
    	img = PIL.Image.fromstring('RGBA', (dimensions.x, dimensions.y), img.tostring())    	
    
        if format == 'jpg':
            img.save(output, quality=85)
        else :
            img.save(output)
########NEW FILE########
