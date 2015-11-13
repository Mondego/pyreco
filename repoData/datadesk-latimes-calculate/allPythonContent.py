__FILENAME__ = adjusted_monthly_value
import six
import calendar
import datetime


def adjusted_monthly_value(value, dt):
    """
    Accepts a value and a datetime object, and then prorates the value to a
    30-day figure depending on how many days are in the month.

    This can be useful for month-to-month comparisons in circumstances where
    fluctuations in the number of days per month may skew the analysis.

    For instance, February typically has only 28 days, in comparison to March,
    which has 31.

    h3. Example usage

        >> import calculate
        >> calculate.adjusted_monthly_value(10, datetime.datetime(2009, 4, 1))
        10.0
        >> calculate.adjusted_monthly_value(10, datetime.datetime(2009, 2, 17))
        10.714285714285714
        >> calculate.adjusted_monthly_value(
            10,
            datetime.datetime(2009, 12, 31)
        )
        9.67741935483871

    h3. Documentation

        "calendar module":http://docs.python.org/library/calendar.html
    """
    # Test to make sure the first input is a number
    if not isinstance(value, six.integer_types):
        raise TypeError('Input values should be a number')

    # Test to make sure the second input is a date
    if not isinstance(dt, (datetime.datetime, datetime.date)):
        raise TypeError('You must submit a date or datetime value')

    # Get the length of the month
    length_of_month = calendar.monthrange(dt.year, dt.month)[1]

    # Determine the adjustment necessary to pro-rate the value to 30 days.
    adjustment = 30.0 / length_of_month

    # Multiply the value against the adjustment and return the result
    return value * adjustment

########NEW FILE########
__FILENAME__ = age
from datetime import date, datetime


def age(born, as_of=None):
    """
    Returns the current age, in years, of a person born on the provided date.

    First argument should be the birthdate and can be a datetime.date or
    datetime.datetime object, although datetimes will be converted to a
    date object and hours, minutes and seconds will not be part of the
    calculation.

    The second argument is the `as of` date that the person's age will be
    calculate at. By default, it is not provided and the age is returned as
    of the current date. But if you wanted to calculate someone's age at a
    past or future date, you could do that by providing the `as_of` date
    as the second argument

    Example usage:

        >>> import calculate
        >>> from datetime import datetime
        >>> dob = datetime(1982, 7, 22)
        >>> calculate.age(dob)
        31 # As of this commit!

    Based on code released by Mark at http://stackoverflow.com/a/2259711
    """
    # Set as_of today if it doesn't exist already
    if not as_of:
        as_of = date.today()
    # Get everything into date format
    if isinstance(born, datetime):
        born = born.date()
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    try:
        # raised when birth date is February 29 and the current year
        # is not a leap year
        tmp = born.replace(year=as_of.year)
    except ValueError:
        tmp = born.replace(year=as_of.year, day=born.day - 1)
    if tmp > as_of:
        return as_of.year - born.year - 1
    else:
        return as_of.year - born.year

########NEW FILE########
__FILENAME__ = at_percentile
import math


def at_percentile(data_list, value, interpolation='fraction'):
    """
    Accepts a list of values and a percentile for which to return the value.

    A percentile of, for example, 80 means that 80 percent of the
    scores in the sequence are below the given score.

    If the requested percentile falls between two values, the result can be
    interpolated using one of the following methods. The default is "fraction".

        1. "fraction"

            The value proportionally between the pair of bordering values.

        2. "lower"

            The lower of the two bordering values.

        3. "higher"

            The higher of the two bordering values.

    h3. Example usage

        >>> import calculate
        >>> calculate.at_percentile([1, 2, 3, 4], 75)
        3.25
        >>> calculate.at_percentile([1, 2, 3, 4], 75, interpolation='lower')
        3.0
        >>> calculate.at_percentile([1, 2, 3, 4], 75, interpolation='higher')
        4.0

    h3. Documentation

        * "Percentile rank":http://en.wikipedia.org/wiki/Percentile_rank

    h3. Credits

        This function is a modification of scipy.stats.scoreatpercentile. The
        only major difference is that I eliminated the numpy dependency.
    """
    # Convert all the values to floats and test to make sure there aren't
    # any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values should contain numbers')

    # Sort the list
    data_list.sort()

    # Find the number of values in the sample
    n = float(len(data_list))

    # Find the index of the provided percentile
    i = ((n - 1) / float(100)) * float(value)

    # Test if that index has a remainder after the decimal point
    remainder = str(i - int(i))[1:]

    # If it doesn't just pull the number at the index
    if remainder == '.0':
        return data_list[int(i)]

    # If it does, interpolate a result using the method provided
    l = data_list[int(math.floor(i))]
    h = data_list[int(math.ceil(i))]
    if interpolation == 'fraction':
        return l + ((h - l) * float(remainder))
    elif interpolation == 'lower':
        return l
    elif interpolation == 'higher':
        return h
    else:
        raise ValueError("The interpolation kwarg must be 'fraction', 'lower' \
or 'higher'. You can also opt to leave it out and rely on the default method.")

########NEW FILE########
__FILENAME__ = benfords_law
from __future__ import print_function
import math
import calculate


def benfords_law(number_list, method='first_digit', verbose=True):
    """
    Accepts a list of numbers and applies a quick-and-dirty run
    against Benford's Law.

    Benford's Law makes statements about the occurance of leading digits in a
    dataset. It claims that a leading digit of 1 will occur about 30 percent
    of the time, and each number after it a little bit less, with the number
    9 occuring the least.

    Datasets that greatly vary from the law are sometimes suspected of fraud.

    The function returns the Pearson correlation coefficient, also known as
    Pearson's r,  which reports how closely the two datasets are related.

    This function also includes a variation on the classic Benford analysis
    popularized by blogger Nate Silver, who conducted an analysis of the final
    digits of polling data. To use Silver's variation, provide the keyward
    argument `method` with the value 'last_digit'.

    To prevent the function from printing, set the optional keyword argument
    `verbose` to False.

    This function is based upon code from a variety of sources around the web,
    but owes a particular debt to the work of Christian S. Perone.

    h3. Example usage

        >> import calculate
        >> calculate.benfords_law([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        BENFORD'S LAW: FIRST_DIGIT

        Pearson's R: 0.86412304649

        | Number | Count | Expected Percentage | Actual Percentage |
        ------------------------------------------------------------
        | 1      | 2     | 30.1029995664       | 20.0              |
        | 2      | 1     | 17.6091259056       | 10.0              |
        | 3      | 1     | 12.4938736608       | 10.0              |
        | 4      | 1     | 9.69100130081       | 10.0              |
        | 5      | 1     | 7.91812460476       | 10.0              |
        | 6      | 1     | 6.69467896306       | 10.0              |
        | 7      | 1     | 5.79919469777       | 10.0              |
        | 8      | 1     | 5.11525224474       | 10.0              |
        | 9      | 1     | 4.57574905607       | 10.0              |

        >> calculate.benfords_law([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            verbose=False)
        -0.863801937698704

    h3. A Warning

    Not all datasets should be expected to conform to Benford's rules.
    I lifted the following guidance from an academic paper linked
    below.

    Durtschi, Hillison, and Pacini (2004) said Benford "compliance"
    should be expected in the following circumstances:

        1. Numbers that result from mathematical combination of numbers

        2. Transaction-level data (e.g., disbursements, sales)

        3. Large datasets

        4. Mean is greater than median and skew is positive

    And not to expect Benford distributions when:

        1. Numbers are assigned (e.g., check numbers, invoice numbers)

        2. Numbers influence by human thought (e.g. $1.99)

        3. Accounts with a large number of firm-specific numbers

        4. Accounts with a built-in minimum or maximum

        5. Where no transaction is recorded.

    h3. Sources

        "Benford's Law":http://en.wikipedia.org/wiki/Benford%27s_law
        "Applying Benford's Law to CAR":http://www.chasedavis.com/2008/sep/\
28/applying-benfords-law-car/
        "Breaking the (Benford) Law: Statistical Fraud Detection in Campaign \
Finance (pdf)":http://cho.pol.uiuc.edu/wendy/papers/tas.pdf
        "Benford's Law meets Python and Apple Stock Prices":http://pyevolve.\
sourceforge.net/wordpress/?p=457
        "Strategic Vision Polls Exhibit Unusual Patterns, Possibly Indicating \
Fraud":http://www.fivethirtyeight.com/2009/09/strategic-vision-polls-\
exhibit-unusual.html
        "Nate Silver: pollster may be fraud":http://blogs.tampabay.com/buzz/\
2009/09/nate-silver-pollster-may-be-fraud.html
    """
    # Select the appropriate retrieval method
    if method not in ['last_digit', 'first_digit']:
        raise ValueError('The method you\'ve requested is not supported.')

    def _get_first_digit(number):
        return int(str(number)[0])

    def _get_last_digit(number):
        return int(str(number)[-1])

    method_name = '_get_%s' % method
    method_obj = locals()[method_name]

    # Set the typical distributions we expect to find
    typical_distributions = {
        'first_digit': {},
        'last_digit': {}
    }
    for number in range(1, 10):
        log10 = math.log10(1 + 1 / float(number)) * 100.0
        typical_distributions['first_digit'].update({number: log10})

    typical_distributions['last_digit'].update({
        0: 10.0, 1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0,
        5: 10.0, 6: 10.0, 7: 10.0, 8: 10.0, 9: 10.0,
    })

    # Fetch the digits we want to analyze
    digit_list = []
    for number in number_list:
        digit = method_obj(number)
        digit_list.append(digit)

    # Loop through the data set and grab all the applicable numbers
    results = []
    for number in range(0, 10):
        count = digit_list.count(number)
        try:
            expected_percentage = typical_distributions[method][number]
        except KeyError:
            continue
        actual_percentage = count / float(len(digit_list)) * 100.0
        results.append([number, count, expected_percentage, actual_percentage])

    # Run the two percentage figures through
    # Pearson's correlation coefficient to
    # see how closely related they are.
    list_one = [i[2] for i in results]
    list_two = typical_distributions[method]
    pearsons_r = calculate.pearson(list_one, list_two)

    # If the user has asked for verbosity,
    # print out this cutsey table with all
    # of the data.
    if verbose:
        from calculate import ptable
        # Convert results to strings
        results = [list(map(str, i)) for i in results]
        # Print everything out using our pretty table module
        labels = [
            'Number', 'Count', 'Expected Percentage', 'Actual Percentage'
        ]
        print("BENFORD'S LAW: %s" % method.upper().replace('_', ' '))
        print("")
        print("Pearson's r: %s" % (pearsons_r))
        print("")
        print(ptable.indent(
            [labels] + results,
            hasHeader=True,
            separateRows=False,
            prefix='| ', postfix=' |',
        ))

    return pearsons_r

########NEW FILE########
__FILENAME__ = competition_rank
from types import FunctionType


def competition_rank(obj_list, obj, order_by, direction='desc'):
    """
    Accepts a list, an item plus the value and direction
    to order by. Then returns the supplied object's competition rank
    as an integer.

    In competition ranking equal numbers receive the same ranking and a gap
    is left before the next value (i.e. "1224").

    h3. Example usage

        >> import calculate
        >> qs = list(Player.objects.all().order_by("-career_home_runs"))
        >> ernie = Player.objects.get(name='Ernie Banks')
        >> eddie = Player.objects.get(name='Eddie Matthews')
        >> calculate.competition_rank(
            qs,
            ernie,
            'career_home_runs',
            direction='desc'
        )
        21
        >> calculate.competition_rank(
            qs,
            eddie,
            'career_home_runs',
            direction='desc'
        )
        21

    h3. Documentation

        * "standard competition rank":http://en.wikipedia.org/wiki/Ranking#\
Standard_competition_ranking_.28.221224.22_ranking.29
    """
    # Convert the object list to a list type, in case it's a Django queryset
    obj_list = list(obj_list)

    # Validate the direction
    if direction not in ['desc', 'asc']:
        raise ValueError('Direction kwarg should be either asc or desc.')

    # Figure out what type of objects we're dealing with
    # and assign the proper way of accessing them.

    # If we've passed in a lambda or function as
    # our order_by, we need to act accordingly.
    if isinstance(order_by, FunctionType):
        def getfunc(obj, func):
            return func(obj)
        gettr = getfunc
    # If the objects are dicts we'll need to pull keys
    elif isinstance(obj_list[0], type({})):
        def getkey(obj, key):
            return obj.get(key)
        gettr = getkey
    # ... otherwise just assume the list is full of objects with attributes
    else:
        gettr = getattr

    # Reorder list
    if direction == 'desc':
        obj_list.sort(key=lambda x: gettr(x, order_by), reverse=True)
    elif direction == 'asc':
        obj_list.sort(key=lambda x: gettr(x, order_by))

    # Set up some globals
    rank = 0
    tie_count = 1

    # Loop through the list
    for i, x in enumerate(obj_list):
        # And keep counting ...
        if (i != 0 and
                gettr(obj_list[i], order_by) ==
                gettr(obj_list[i - 1], order_by)):
            tie_count += 1
        else:
            rank = rank + tie_count
            tie_count = 1
        # ... Until we hit the submitted object
        if obj == x:
            return rank

########NEW FILE########
__FILENAME__ = date_range
import datetime


def date_range(start_date, end_date):
    """
    Returns a generator of all the days between two date objects.

    Results include the start and end dates.

    Arguments can be either datetime.datetime or date type objects.

    h3. Example usage

        >>> import datetime
        >>> import calculate
        >>> dr = calculate.date_range(
        ...   datetime.date(2009, 1, 1),
        ...   datetime.date(2009, 1, 3),
        ... )
        >>> dr
        <generator object _make at 0x7f5a58437d20>
        >>> list(dr)
        [datetime.date(2009, 1, 1), datetime.date(2009, 1, 2),
            datetime.date(2009, 1, 3)]
    """
    # If a datetime object gets passed in,
    # change it to a date so we can do comparisons.
    if isinstance(start_date, datetime.datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.date()

    def _make(start_date, end_date):
        # Jump forward from the start_date...
        while True:
            yield start_date
            # ... one day at a time ...
            start_date = start_date + datetime.timedelta(days=1)
            # ... until you reach the end date.
            if start_date > end_date:
                break

    # Verify that the start_date comes after the end_date.
    if start_date > end_date:
        raise ValueError('Provided start_date must come before end_date.')
    else:
        return _make(start_date, end_date)

########NEW FILE########
__FILENAME__ = decile
import calculate


def decile(data_list, score, kind='weak'):
    """
    Accepts a sample of values and a single number to add to it
    and determine the decile equivilent of its percentile rank.

    By default, the method used to negotiate gaps and ties
    is "weak" because it returns the percentile of all values
    at or below the provided value. For an explanation of
    alternative methods, refer to the calculate.percentile
    function.

    h3. Example usage

        >> import calculate
        >> calculate.decile([1, 2, 3, 3, 4], 3)
        9

    h3. Documentation

        * "percentile rank":http://en.wikipedia.org/wiki/Percentile_rank
        * "decile":http://en.wikipedia.org/wiki/Decile

    """
    # Use calculate.percentile to fetch the precise percentile
    # ranking of the desired value
    percentile_score = calculate.percentile(data_list, score, kind=kind)

    # Now translate that value to a decile value
    if percentile_score == 100.0:
        # If the value is 100, it's easy, return 10
        return 10
    else:
        # Otherwise, reduce the value to single digits,
        # shave off the decimal by converting it to an
        # integer, and then add one, so that, for example,
        # 0.X numbers are in the first decile, and 9.X
        # numbers are in the 10th. - where we want them.
        decile = int(percentile_score * 0.1) + 1
        return decile

########NEW FILE########
__FILENAME__ = elfi
import math


def elfi(data_list):
    """
    The ELFI is a simplified method for calculating the Ethnolinguistic
    Fractionalization Index (ELFI) This is one form of what is commonly called
    a "diversity index."

    Accepts a list of decimal percentages, which are used to
    calculate the index.

    Returns a decimal value as a floating point number.

    h3. Example usage

        >>> import calculate
        >>> calculate.elfi([0.2, 0.5, 0.05, 0.25])
        0.64500000000000002

    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values should contain numbers')
    # Calculate the ELFI
    return 1 - sum([math.pow(i, 2) for i in data_list])

########NEW FILE########
__FILENAME__ = equal_sized_breakpoints
def equal_sized_breakpoints(data_list, classes):
    """
    Returns break points for groups of equal size, known as quartiles,
    quintiles, etc.

    Provide a list of data values and the number of classes you'd like the list
    broken up into.

    No flashy math, just sorts them in order and makes the cuts.

    h3. Example usage

        >>> import calculate
        >>> calculate.equal_sized_breakpoints(range(1,101), 5)
        [1.0, 21.0, 41.0, 61.0, 81.0, 100.0]

    """
    # Sort the list
    data_list.sort()

    # Get the total number of values
    n = len(data_list)

    # List where we will stash the break points
    breaks = []

    # Loop through the classes
    for i in range(classes):
        # Get the percentile where this class will cut
        q = i / float(classes)
        # Multiply that by the 'n'
        a = q * n
        # Get the integer version of that number
        aa = int(q * n)
        # Calc the reminder between the two
        r = a - aa
        # Find the value
        breakpoint = (1 - r) * data_list[aa] + r * data_list[aa + 1]
        # Add it to the list
        breaks.append(breakpoint)

    # Tack the final number to the end of the list
    breaks.append(float(data_list[n - 1]))

    # Pass it all out
    return breaks

########NEW FILE########
__FILENAME__ = margin_of_victory
def margin_of_victory(value_list):
    """
    Accepts a list of numbers and returns the difference between
    the first place and second place values.

    This can be useful for covering elections as an easy to way to figure out
    the margin of victory for a leading candidate.

    h3. Example usage

        >> import calculate
        >> calculate.margin_of_victory([3285, 2804, 7170])
        3885
    """
    # Sort from biggest to smallest
    value_list.sort(reverse=True)

    # Return the difference between the top two values
    return value_list[0] - value_list[1]

########NEW FILE########
__FILENAME__ = mean
def mean(data_list):
    """
    Accepts a sample of values and returns their mean.

    The mean is the sum of all values in the sample divided by
    the number of members. It is also known as the average.

    Since the value is strongly influenced by outliers, median
    is generally a better indicator of central tendency.

    h3. Example usage

        >> import calculate
        >> calculate.mean([1,2,3])
        2.0
        >> calculate.mean([1, 99])
        50.0

    h3. Documentation

        "mean":http://en.wikipedia.org/wiki/Arithmetic_mean
    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values should contain numbers')
    # Count the number of values in the sample
    n = len(data_list)
    # Sum up the values in the sample
    sum_ = sum(data_list)
    # Divide them to find the mean
    return sum_ / n

########NEW FILE########
__FILENAME__ = mean_center
from django.contrib.gis.geos import MultiPoint


def mean_center(obj_list, point_attribute_name='point'):
    """
    Accepts a geoqueryset, list of objects or list of dictionaries, expected
    to contain GeoDjango Point objects as one of their attributes.

    Returns a Point object with the mean center of the provided points.

    The mean center is the average x and y of all those points.

    By default, the function expects the Point field on your model
    to be called 'point'.

    If the point field is called something else, change the kwarg
    'point_attribute_name' to whatever your field might be called.

    h3. Example usage

        >> import calculate
        >> calculate.mean_center(qs)
        <Point object at 0x77a1694>

    h3. Dependencies

        * "django":http://www.djangoproject.com/
        * "geodjango":http://www.geodjango.org/

    h3. Documentation

        * "mean center":http://help.arcgis.com/en/arcgisdesktop/10.0/help/\
index.html#//005p00000018000000.htm

    """
    # Figure out what type of objects we're dealing with
    if isinstance(obj_list[0], type({})):
        def getkey(obj, key):
            return obj.get(key)
        gettr = getkey
    else:
        gettr = getattr
    # Crunch it
    multipoint = MultiPoint([gettr(p, point_attribute_name) for p in obj_list])
    return multipoint.centroid

########NEW FILE########
__FILENAME__ = median
def median(data_list):
    """
    Accepts a list of numbers and returns the median value.

    The median is the number in the middle of a sequence,
    with 50 percent of the values above, and 50 percent below.

    In cases where the sequence contains an even number of values -- and
    therefore no exact middle -- the two values nearest the middle
    are averaged and the mean returned.

    h3. Example usage

        >> import calculate
        >> seq1 = [1,2,3]
        >> calculate.median(seq1)
        2.0
        >> seq2 = (1,4,3,2)
        >> calculate.median(seq2)
        2.5

    h3. Documentation

        * "median":http://en.wikipedia.org/wiki/Median

    """
    # Convert all the values to floats and test to make sure there aren't
    # any strings in there
    try:
        data_list = list(map(float, data_list))
    except TypeError:
        raise TypeError('Input values should be a number')
    # Fetch the total number of values
    n = len(data_list)
    # Sort the values from top to bottom
    data_list.sort()
    # Test whether the n is odd
    if n & 1:
        # If is is, get the index simply by dividing it in half
        index = n / 2
        median = data_list[int(index)]
    else:
        # If the n is even, average the two values at the center
        low_index = (n / 2) - 1
        high_index = n / 2
        median = (data_list[int(low_index)] + data_list[int(high_index)]) / 2.0
    return median

########NEW FILE########
__FILENAME__ = mode
def mode(data_list):
    """
    Accepts a sample of numbers and returns the mode value.

    The mode is the most common value in a data set.

    If there is a tie for the highest count, no value is
    returned. The function could be modified to identify
    bimodal results to handle such situations, but I don't
    have a need for it right now so I'm going to leave it
    behind.

    h3. Example usage

        >> import calculate
        >> calculate.mode([1,2,2,3])
        2.0
        >> calculate.mode([1,2,3])
        >>

    h3. Documentation

        "mode":http://en.wikipedia.org/wiki/Mode_(statistics)
    """
    # Convert all the values to floats and test to make sure there
    # aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except TypeError:
        raise TypeError('Input values must contain numbers')

    # Create a dictionary to store the counts for each value
    counts = {}
    # Loop through the data_list
    for value in data_list:
        if value not in counts:
            # If the value isn't already in the dictionary
            # add it and set it to one.
            counts[value] = 1
        else:
            # And if it is already there, increase the count
            # by one.
            counts[value] += 1

    # Now repurpose the dictionary as a list of tuples so it can be sorted
    sortable_list = [(count, value) for value, count in list(counts.items())]

    # And flip it around...
    sortable_list.sort()

    # ...so that the highest count should appear first
    sortable_list.reverse()

    # If there's only one number, just pass that out
    if len(sortable_list) == 1:
        return sortable_list[0][1]

    # Test to make sure the first and second counts aren't the same
    first_count = sortable_list[0][0]
    second_count = sortable_list[1][0]
    if first_count == second_count:
        # If they are, return None
        return None
    else:
        # If the first count stands above the rest,
        # return it as the mode
        mode = sortable_list[0][1]
        return mode

########NEW FILE########
__FILENAME__ = models
# An empty models file so we can use django's testing library

########NEW FILE########
__FILENAME__ = nudge_points
import math
import random
from operator import attrgetter
from django.contrib.gis.geos import Point


def nudge_points(geoqueryset, point_attribute_name='point', radius=0.0001):
    """
    A utility that accepts a list of objects with a GeoDjango Point attribute
    and nudges slightly apart any identical points.

    Returns the modified input as a list.

    By default it looks for the point in an attribute named "point." If
    your point data attribute has a different name, submit it as a string
    to the "point_attribute_name" kwarg.

    By default, the distance of the move is 0.0001 decimal degrees. You can
    mofied it by submitting a "radius" kwarg.

    I'm not sure if this will go wrong if your data is in a different unit
    of measurement.

    This can be useful for running certain geospatial statistics, or even
    for presentation issues, like spacing out markers on a Google Map for
    instance.

    h3. Example usage

        >>> import calculate
        >>> from models import FakePoint
        >>> qs = FakePoint.objects.all()
        >>> qs = calculate.nudge_points(qs)

    h3. Dependencies

        * "django":http://www.djangoproject.com/
        * "geodjango":http://www.geodjango.org/
        * "math":http://docs.python.org/library/math.html

    h3. Documentation

        * "This code is translated from SQL by Francis Dupont":http://postgis.\
refractions.net/pipermail/postgis-users/2008-June/020354.html
    """
    previous_x = None
    previous_y = None
    r = radius
    pan = point_attribute_name
    sorted_gqs = sorted(list(geoqueryset), key=attrgetter(pan))

    out_list = []
    for obj in sorted_gqs:
        x = getattr(obj, pan).x
        y = getattr(obj, pan).y
        if (x == previous_x and y == previous_y
                and previous_x is not None and previous_y is not None):
            # angle value in radian between 0 and 2pi
            theta = random.random() * 2 * math.pi
            new_point = Point(
                x + (math.cos(theta) * r),
                y + (math.sin(theta) * r)
            )
            setattr(obj, pan, new_point)
        else:
            previous_x = x
            previous_y = y
        out_list.append(obj)
    return out_list

########NEW FILE########
__FILENAME__ = ordinal_rank
def ordinal_rank(sequence, item, order_by=None, direction='desc'):
    """
    Accepts a list and an object. Returns the object's ordinal rank
    as an integer.

    h3. Example usage

        >> import calculate
        >> qs = Player.objects.all().order_by("-career_home_runs")
        >> barry = Player.objects.get(
            first_name__iexact='Barry',
            last_name__iexact='Bonds'
        )
        >> calculate.ordinal_rank(list(qs), barry)
        1

    h3. Documentation

        * "ordinal rank":http://en.wikipedia.org/wiki/Ranking#Ordinal_ranking\
_.28.221234.22_ranking.29
    """
    seq_list = list(sequence)
    if order_by:
        # Figure out what type of objects we're dealing with
        if isinstance(seq_list[0], type({})):
            def getkey(obj, key):
                return obj.get(key)
            gettr = getkey
        else:
            gettr = getattr
        if direction == 'desc':
            seq_list.sort(key=lambda x: gettr(x, order_by), reverse=True)
        elif direction == 'asc':
            seq_list.sort(key=lambda x: gettr(x, order_by))
        else:
            raise ValueError('Direction kwarg should be either asc or desc.')
    index = seq_list.index(item)
    return index + 1

########NEW FILE########
__FILENAME__ = pearson
import math


def pearson(list_one, list_two):
    """
    Accepts paired lists and returns a number between -1 and 1,
    known as Pearson's r, that indicates of how closely correlated
    the two datasets are.

    A score of close to one indicates a high positive correlation.
    That means that X tends to be big when Y is big.

    A score close to negative one indicates a high negative correlation.
    That means X tends to be small when Y is big.

    A score close to zero indicates little correlation between the two
    datasets.

    This script is cobbled together from a variety of sources, linked
    in the sources section below.

    h3. Example usage

        >> import calculate
        >> calculate.pearson([6,5,2], [2,5,6])
        -0.8461538461538467

    h3. A Warning

        Correlation does not equal causation. Just because the two
        datasets are closely related doesn't not mean that one causes
        the other to be the way it is.

    h3. Sources

        http://en.wikipedia.org/wiki/Pearson_product-moment_correlation_\
coefficient
        http://davidmlane.com/hyperstat/A56626.html
        http://www.cmh.edu/stats/definitions/correlation.htm
        http://www.amazon.com/Programming-Collective-Intelligence-Building-\
Applications/dp/0596529325
    """
    if len(list_one) != len(list_two):
        raise ValueError('The two lists you provided do not have the same \
number of entries. Pearson\'s r can only be calculated with paired data.')

    n = len(list_one)

    # Convert all of the data to floats
    list_one = list(map(float, list_one))
    list_two = list(map(float, list_two))

    # Add up the total for each
    sum_one = sum(list_one)
    sum_two = sum(list_two)

    # Sum the squares of each
    sum_of_squares_one = sum([pow(i, 2) for i in list_one])
    sum_of_squares_two = sum([pow(i, 2) for i in list_two])

    # Sum up the product of each element multiplied against its pair
    product_sum = sum([
        item_one * item_two for item_one, item_two in zip(list_one, list_two)
    ])

    # Use the raw materials above to assemble the equation
    pearson_numerator = product_sum - (sum_one * sum_two / n)
    pearson_denominator = math.sqrt(
        (sum_of_squares_one - pow(sum_one, 2) / n) *
        (sum_of_squares_two - pow(sum_two, 2) / n)
    )

    # To avoid avoid dividing by zero,
    # catch it early on and drop out
    if pearson_denominator == 0:
        return 0

    # Divide the equation to return the r value
    return pearson_numerator / pearson_denominator

########NEW FILE########
__FILENAME__ = percentage
def percentage(value, total, multiply=True, fail_silently=True):
    """
    Accepts two integers, a value and a total.

    The value is divided into the total and then multiplied by 100,
    returning its percentage as a float.

    If you don't want the number multiplied by 100, set the 'multiply'
    kwarg to False.

    If you divide into zero -- an illegal operation -- a null value
    is returned by default. If you prefer for an error to be raised,
    set the kwarg 'fail_silently' to False.

    h3. Example usage

        >>> import calculate
        >>> calculate.percentage(2, 10)
        20.0
        >>> calculate.percentage(2,0, multiply=False)
        0.20000000000000001
        >>> calculate.percentage(2,0)
        >>> calculate.percentage(2,0, fail_silently=False)
        ZeroDivisionError

    h3. Documentation

        * "percentage":http://en.wikipedia.org/wiki/Percentage
    """
    try:
        # Divide one into the other
        percent = (value / float(total))
        if multiply:
            # If specified, multiply by 100
            percent = percent * 100
        return percent
    except ZeroDivisionError:
        # If there's a zero involved return null if set to fail silent
        if fail_silently:
            return None
        # but otherwise shout it all out
        else:
            raise ZeroDivisionError("Sorry. You can't divide into zero.")

########NEW FILE########
__FILENAME__ = percentage_change
def percentage_change(old_value, new_value, multiply=True, fail_silently=True):
    """
    Accepts two integers, an old and a new number,
    and then measures the percent change between them.

    The change between the two numbers is determined
    and then divided into the original figure.

    By default, it is then multiplied by 100, and
    returning as a float.

    If you don't want the number multiplied by 100,
    set the 'multiply' kwarg to False.

    If you divide into zero -- an illegal operation -- a null value
    is returned by default. If you prefer for an error to be raised,
    set the kwarg 'fail_silently' to False.

    h3. Example usage

        >> import calculate
        >> calculate.percentage_change(2, 10)
        400.0

    h3. Documentation

        * "percentage_change":http://en.wikipedia.org/wiki/Percentage_change
    """
    change = new_value - old_value
    try:
        percentage_change = (change / float(old_value))
        if multiply:
            percentage_change = percentage_change * 100
        return percentage_change
    except ZeroDivisionError:
        # If there's a zero involved return null if set to fail silent
        if fail_silently:
            return None
        # but otherwise shout it all out
        else:
            raise ZeroDivisionError("Sorry. You can't divide into zero.")

########NEW FILE########
__FILENAME__ = percentile
import calculate


def percentile(data_list, value, kind='weak'):
    """
    Accepts a sample of values and a single number to compare to it
    and determine its percentile rank.

    A percentile of, for example, 80 means that 80 percent of the
    scores in the sequence are below the given score.

    In the case of gaps or ties, the exact definition depends on the type
    of the calculation stipulated by the "kind" keyword argument.

    There are three kinds of percentile calculations provided here. The
    default is "weak".

        1. "weak"

            Corresponds to the definition of a cumulative
            distribution function, with the result generated
            by returning the percentage of values at or equal
            to the the provided value.

        2. "strict"

            Similar to "weak", except that only values that are
            less than the given score are counted. This can often
            produce a result much lower than "weak" when the provided
            score is occurs many times in the sample.

        3. "mean"

            The average of the "weak" and "strict" scores.

    h3. Example usage

        >> import calculate
        >> calculate.percentile([1, 2, 3, 4], 3)
        75.0
        >> calculate.percentile([1, 2, 3, 3, 4], 3, kind='strict')
        40.0
        >> calculate.percentile([1, 2, 3, 3, 4], 3, kind='weak')
        80.0
        >> calculate.percentile([1, 2, 3, 3, 4], 3, kind='mean')
        60.0

    h3. Documentation

        * "Percentile rank":http://en.wikipedia.org/wiki/Percentile_rank

    h3. Credits

        This function is a modification of scipy.stats.percentileofscore. The
        only major difference is that I eliminated the numpy dependency, and
        omitted the rank kwarg option until I can find time to translate
        the numpy parts out.
    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values should contain numbers, your first \
input contains something else')

    # Find the number of values in the sample
    n = float(len(data_list))

    if kind == 'strict':
        # If the selected method is strict, count the number of values
        # below the provided one and then divide it into the n
        return len([i for i in data_list if i < value]) / n * 100

    elif kind == 'weak':
        # If the selected method is weak, count the number of values
        # equal to or below the provided on and then divide it into n
        return len([i for i in data_list if i <= value]) / n * 100

    elif kind == 'mean':
        # If the selected method is mean, take the weak and strong
        # methods and average them.
        strict = len([i for i in data_list if i < value]) / n * 100
        weak = len([i for i in data_list if i <= value]) / n * 100
        return calculate.mean([strict, weak])
    else:
        raise ValueError("The kind kwarg must be 'strict', 'weak' or 'mean'. \
You can also opt to leave it out and rely on the default method.")

########NEW FILE########
__FILENAME__ = per_capita
def per_capita(value, population, per=10000, fail_silently=True):
    """
    Accepts two numbers, a value and population total, and returns
    the per capita rate.

    By default, the result is returned as a per 10,000 person figure.

    If you divide into zero -- an illegal operation -- a null value
    is returned by default. If you prefer for an error to be raised,
    set the kwarg 'fail_silently' to False.

    h3. Example usage

        >> import calculate
        >> calculate.per_capita(12, 100000)
        1.2

    h3. Documentation

        * "per capita":http://en.wikipedia.org/wiki/Per_capita
    """
    try:
        return (float(value) / population) * per
    except ZeroDivisionError:
        # If there's a zero involved return null if set to fail silent
        if fail_silently:
            return None
        # but otherwise shout it all out
        else:
            raise ZeroDivisionError("Sorry. You can't divide into zero.")

########NEW FILE########
__FILENAME__ = per_sqmi
def per_sqmi(value, square_miles, fail_silently=True):
    """
    Accepts two numbers, a value and an area, and returns the
    per square mile rate.

    Not much more going on here than a simple bit of division.

    If you divide into zero -- an illegal operation -- a null value
    is returned by default. If you prefer for an error to be raised,
    set the kwarg 'fail_silently' to False.

    h3. Example usage

        >> import calculate
        >> calculate.per_sqmi(20, 10)
        2.0
    """
    try:
        return float(value) / square_miles
    except ZeroDivisionError:
        # If there's a zero involved return null if set to fail silent
        if fail_silently:
            return None
        # but otherwise shout it all out
        else:
            raise ZeroDivisionError("Sorry. You can't divide into zero.")

########NEW FILE########
__FILENAME__ = ptable
"""
A table printer lifted from ActiveState and slightly modified
to be PEP8 compliant. It's ain't pretty, but it does work.

Source: http://code.activestate.com/recipes/267662/
"""
from __future__ import print_function

import re
import math
import operator
from functools import reduce
try:
    import cStringIO as io
except:
    import io


def indent(rows, hasHeader=False, headerChar='-', delim=' | ', justify='left',
           separateRows=False, prefix='', postfix='', wrapfunc=lambda x: x):
    """Indents a table by column.
       - rows: A sequence of sequences of items, one sequence per row.
       - hasHeader: True if the first row consists of the columns' names.
       - headerChar: Character to be used for the row separator line
         (if hasHeader==True or separateRows==True).
       - delim: The column delimiter.
       - justify: Determines how are data justified in their column.
         Valid values are 'left','right' and 'center'.
       - separateRows: True if rows are to be separated by a line
         of 'headerChar's.
       - prefix: A string prepended to each printed row.
       - postfix: A string appended to each printed row.
       - wrapfunc: A function f(text) for wrapping text; each element in
         the table is first wrapped by this function."""
    # closure for breaking logical rows to physical, using wrapfunc
    def rowWrapper(row):
        newRows = [wrapfunc(item).split('\n') for item in row]
        return [
            [substr or '' for substr in item]
            for item in list(map(lambda *a: a, *newRows))
        ]
    # break each logical row into one or more physical ones
    logicalRows = [rowWrapper(row) for row in rows]
    # columns of physical rows
    columns = list(map(lambda *a: a, *reduce(operator.add, logicalRows)))
    # get the maximum of each column by the string length of its items
    maxWidths = [
        max([len(str(item)) for item in column]) for column in columns
    ]
    rowSeparator = headerChar * (len(prefix) + len(postfix) + sum(maxWidths) +
                                 len(delim) * (len(maxWidths) - 1))
    # select the appropriate justify method
    justify = {
        'center': str.center,
        'right': str.rjust,
        'left': str.ljust
    }[justify.lower()]
    output = io.StringIO()
    if separateRows:
        print >> output, rowSeparator
    for physicalRows in logicalRows:
        for row in physicalRows:
            print(
                prefix +
                delim.join([
                    justify(str(item), width)
                    for (item, width) in zip(row, maxWidths)
                ])
                + postfix, file=output
            )
        if separateRows or hasHeader:
            print(rowSeparator, file=output)
            hasHeader = False
    return output.getvalue()


def wrap_onspace(text, width):
    """
    A word-wrap function that preserves existing line breaks
    and most spaces in the text. Expects that existing line
    breaks are posix newlines (\n).

    By Mike Brown
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
    """
    return reduce(
        lambda line, word, width=width: '%s%s%s' %
        (
            line,
            ' \n'
            [
                (
                    len(line[line.rfind('\n') + 1:]) +
                    len(word.split('\n', 1)[0]) >= width
                )
            ],
            word
        ),
        text.split(' ')
    )


def wrap_onspace_strict(text, width):
    """
    Similar to wrap_onspace, but enforces the width constraint:
    words longer than width are split.
    """
    wordRegex = re.compile(r'\S{' + str(width) + r',}')
    return wrap_onspace(
        wordRegex.sub(lambda m: wrap_always(m.group(), width), text),
        width
    )


def wrap_always(text, width):
    """
    A simple word-wrap function that wraps text on exactly width characters.

    It doesn't split the text in words.
    """
    return '\n'.join([
        text[width * i:width * (i + 1)]
        for i in range(
            int(math.ceil(1.0 * len(text) / width))
        )
    ])

########NEW FILE########
__FILENAME__ = random_point
import random
from django.contrib.gis.geos import Point


def random_point(extent):
    """
    A utility that accepts the extent of a polygon and returns a random
    point from within its boundaries.

    The extent is a four-point tuple with (xmin, ymin, xmax, ymax).

    h3. Example usage

        >> polygon = Model.objects.get(pk=1).polygon
        >> import calculate
        >> calculate.random_point(polygon.extent)

    h3. Dependencies

        * "django":http://www.djangoproject.com/
        * "geodjango":http://www.geodjango.org/
        * "random":http://docs.python.org/library/random.html

    h3. Documentation

        * "extent":http://geodjango.org/docs/geos.html#extent
        * "Code lifted from Joost at DjangoDays":http://djangodays.com/\
2009/03/04/geodjango-getting-a-random-point-within-a-multipolygon/
    """
    xmin, ymin, xmax, ymax = extent
    xrange = xmax - xmin
    yrange = ymax - ymin
    randx = xrange * random.random() + xmin
    randy = yrange * random.random() + ymin
    return Point(randx, randy)

########NEW FILE########
__FILENAME__ = range
def range(data_list):
    """
    Accepts a sample of values and return the range.

    The range is the difference between the maximum and
    minimum values of a data set.

    h3. Example usage

        >> import calculate
        >> calculate.range([1,2,3])
        2
        >> calculate.range([2,2])
        0

    h3. Documentation

        "range":http://en.wikipedia.org/wiki/Range_(statistics)
    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values should contain numbers, your first \
            input contains something else')

    # Make sure the sample has more than one entry
    if len(data_list) < 2:
        raise ValueError('Input must contain at least two values. \
            You provided a list with %s values' % len(data_list))

    # Find the maximum value in the list
    max_ = max(data_list)

    # Find the minimum value in the list
    min_ = min(data_list)

    # Find the range by calculating the difference
    return max_ - min_

########NEW FILE########
__FILENAME__ = split_at_breakpoints
def split_at_breakpoints(data_list, breakpoint_list):
    """
    Splits up a list at the provided breakpoints.

    First argument is a list of data values. Second is a list
    of the breakpoints you'd like it to be split up with.

    Returns a list of lists, in order by breakpoint.

    Useful for splitting up a list after you've determined breakpoints using
    another method like calculate.equal_sized_breakpoints.

    h3. Example usage

        >>> import calculate
        >>> l = range(1,31)
        >>> bp = calculate.equal_sized_breakpoints(l, 5)
        >>> bp
        [1.0, 7.0, 13.0, 19.0, 25.0, 30.0]
        >>> calculate.split_at_breakpoints(l, bp)
        [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12], [13, 14, 15, 16, 17, 18],
        [19, 20, 21, 22, 23, 24], [25, 26, 27, 28, 29, 30]]
    """
    # Sort the lists
    data_list.sort()
    breakpoint_list.sort()

    # Create a list of empty lists that we'll
    # fill in with values as we go along.
    split_list = [[] for i in range(len(breakpoint_list) - 1)]

    # Loop through the data list
    for value in data_list:

        # Start off by assuming it's in the last break
        group = len(breakpoint_list) - 1

        # Then loop through all the breaks from first to last
        for i in range(len(breakpoint_list) - 1):
            # If the value is falls between this break and the next one up...
            if value >= breakpoint_list[i] and value <= breakpoint_list[i + 1]:
                # ...set it as a member of that break
                group = i

        # Then add it to the proper list
        split_list[group].append(value)

    # Return the list of lists
    return split_list

########NEW FILE########
__FILENAME__ = standard_deviation
import math
import calculate


def standard_deviation(data_list):
    """
    Accepts a list of values and returns the standard deviation.

    Standard deviation measures how widely dispersed the values are
    from the mean. A lower value means the data tend to be bunched
    close to the averge. A higher value means they tend to be further
    away.

    This is a "population" calculation that assumes that you are submitting
    all of the values, not a sample.

    h3. Example usage

        >> import calculate
        >>> calculate.standard_deviation([2,3,3,4])
        0.70710678118654757
        >>> calculate.standard_deviation([-2,3,3,40])
        16.867127793432999

    h3. Documentation

        "standard deviation":http://en.wikipedia.org/wiki/Standard_deviation

    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values must contain numbers')

    # Find the mean
    mean = calculate.mean(data_list)

    # Create a new list containing the distance from mean
    # for each value in the sample
    deviations = [i - mean for i in data_list]

    # Square the distances
    deviations_squared = [math.pow(i, 2) for i in deviations]

    # Take the average of those squares
    mean_deviation = calculate.mean(deviations_squared)

    # And then take the square root of the mean to find the standard deviation
    return math.sqrt(mean_deviation)

########NEW FILE########
__FILENAME__ = standard_deviation_distance
import calculate


def standard_deviation_distance(obj_list, point_attribute_name='point'):
    """
    Accepts a geoqueryset, list of objects or list of dictionaries, expected
    to contain objects with Point properties, and returns a float with the
    standard deviation distance of the provided points.

    The standard deviation distance is the average variation in the distance
    of points from the mean center.

    Unlike a standard deviation ellipse, it does not have a direction.

    By default, the function expects the Point field on your model to be
    called 'point'.

    If the point field is called something else, change the kwarg
    'point_attribute_name' to whatever your field might be called.

    h3. Example usage

        >> import calculate
        >> calculate.standard_deviation_distance(qs)
        0.046301584704149731

    h3. Dependencies

        * "django":http://www.djangoproject.com/
        * "geodjango":http://www.geodjango.org/

    h3. Documentation

        * "standard deviation distance":http://www.spatialanalysisonline.com/\
output/html/Directionalanalysisofpointdatasets.html
    """
    # Figure out what type of objects we're dealing with
    if isinstance(obj_list[0], type({})):
        def getkey(obj, key):
            return obj.get(key)
        gettr = getkey
    else:
        gettr = getattr
    mean = calculate.mean_center(
        obj_list,
        point_attribute_name=point_attribute_name
    )
    distances = [
        gettr(p, point_attribute_name).distance(mean)
        for p in obj_list
    ]
    return calculate.standard_deviation(distances)

########NEW FILE########
__FILENAME__ = summary_stats
from __future__ import print_function
import calculate
from calculate import ptable


def summary_stats(data_list):
    """
    Accepts a sample of numbers and returns a pretty
    print out of a variety of descriptive statistics.
    """
    mean = calculate.mean(data_list)
    median = calculate.median(data_list)
    mode = calculate.mode(data_list)
    n = len(data_list)
    max_ = max(data_list)
    min_ = min(data_list)
    range_ = calculate.range(data_list)
    standard_deviation = calculate.standard_deviation(data_list)
    variation_coefficient = calculate.variation_coefficient(data_list)

    table = ptable.indent(
        [
            ['Statistic', 'Value'],
            ['n', str(n)],
            ['mean', str(mean)],
            ['median', str(median)],
            ['mode', str(mode)],
            ['maximum', str(max_)],
            ['minimum', str(min_)],
            ['range', str(range_)],
            ['standard deviation', str(standard_deviation)],
            ['variation coefficient', str(variation_coefficient)],
        ],
        hasHeader=True,
        separateRows=False,
        prefix="| ", postfix=" |",
    )
    print(table)

########NEW FILE########
__FILENAME__ = tests
import sys
import unittest
import calculate
from datetime import datetime, date
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
try:
    import cStringIO as io
except:
    import io


class BaseTest(unittest.TestCase):

    def setUp(self):
        pass


class CalculateTest(BaseTest):

    def test_adjusted_monthly_value(self):
        self.assertEqual(
            calculate.adjusted_monthly_value(
                10,
                datetime(2009, 4, 1, 0, 10, 10)
            ),
            10.0
        )
        self.assertEqual(
            calculate.adjusted_monthly_value(10, datetime(2009, 2, 17)),
            10.714285714285714
        )
        self.assertEqual(
            calculate.adjusted_monthly_value(10, date(2009, 12, 31)),
            9.67741935483871
        )
        self.assertRaises(
            TypeError,
            calculate.adjusted_monthly_value,
            'a',
            date(2009, 12, 31)
        )
        self.assertRaises(
            TypeError,
            calculate.adjusted_monthly_value,
            10,
            '2010-01-01'
        )
        self.assertRaises(
            TypeError,
            calculate.adjusted_monthly_value,
            10,
            2
        )

    def test_age(self):
        # All the data types
        self.assertEqual(
            calculate.age(datetime(1982, 7, 22), date(2011, 12, 3)),
            29
        )
        self.assertEqual(
            calculate.age(datetime(1982, 7, 22)),
            calculate.age(datetime(1982, 7, 22))
        )
        self.assertEqual(
            calculate.age(date(1982, 7, 22), date(2011, 12, 3)),
            29
        )
        self.assertEqual(
            calculate.age(datetime(1982, 7, 22), datetime(2011, 12, 3)),
            29
        )
        self.assertEqual(
            calculate.age(date(1982, 7, 22), datetime(2011, 12, 3)),
            29
        )
        # Leap Day
        self.assertEqual(
            calculate.age(date(1984, 2, 29), date(2011, 12, 3)),
            27
        )
        # Tomorrow bday
        self.assertEqual(
            calculate.age(date(2010, 12, 4), date(2011, 12, 3)),
            0
        )

    def test_at_percentile(self):
        self.assertEqual(calculate.at_percentile([1, 2, 3, 4], 75), 3.25)
        self.assertEqual(calculate.at_percentile([1, 2, 3, 4], 100), 4)
        self.assertEqual(
            calculate.at_percentile([1, 2, 3, 4], 75, interpolation='lower'),
            3.0
        )
        self.assertEqual(
            calculate.at_percentile([1, 2, 3, 4], 75, interpolation='higher'),
            4.0
        )
        self.assertRaises(ValueError, calculate.at_percentile, ['a', 2, 3], 75)
        self.assertRaises(
            ValueError,
            calculate.at_percentile,
            [1, 2, 3, 4],
            75,
            interpolation='mystery-meat'
        )

    def test_benfords_law(self):
        self.assertEqual(
            calculate.benfords_law(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                verbose=False
            ),
            -0.8638019376987044
        )
        self.assertEqual(
            calculate.benfords_law(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                verbose=True
            ),
            -0.8638019376987044
        )
        self.assertEqual(
            calculate.benfords_law(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                method="last_digit",
                verbose=False
            ),
            0
        )
        self.assertRaises(
            ValueError,
            calculate.benfords_law,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            method='magic'
        )
        self.assertRaises(TypeError, calculate.benfords_law, 10.0)

    def test_competition_rank(self):
        dict_list = [
            {'name': 'Joan', 'value': 1},
            {'name': 'Jane', 'value': 2},
            {'name': 'Mary', 'value': 2},
            {'name': 'Josh', 'value': 3},
        ]
        self.assertEqual(
            calculate.competition_rank(
                dict_list, dict_list[0], 'value', 'desc'
            ),
            4
        )
        self.assertEqual(
            calculate.competition_rank(
                dict_list, dict_list[1], 'value', 'desc'
            ),
            2
        )
        self.assertEqual(
            calculate.competition_rank(
                dict_list, dict_list[2], 'value', 'desc'
            ),
            2
        )
        self.assertEqual(
            calculate.competition_rank(dict_list, dict_list[3], 'value'), 1
        )

        def sortFunc(obj):
            return 3

        self.assertEqual(
            calculate.competition_rank(
                dict_list, dict_list[2], sortFunc, 'desc'
            ),
            1
        )

        class DummyObj():
            def __init__(self, **entries):
                self.__dict__.update(entries)

        obj_list = [DummyObj(**d) for d in dict_list]
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[0], 'value', 'asc'),
            1
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[1], 'value', 'asc'),
            2
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[2], 'value', 'asc'),
            2
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[3], 'value', 'asc'),
            4
        )

        class DummyDjangoObj(models.Model):
            fake_id = models.IntegerField(primary_key=True)
            name = models.TextField()
            value = models.IntegerField()

            def __unicode__(self):
                return '%s (%s)' % (self.name, self.value)

        obj_list = [
            DummyDjangoObj(fake_id=i + 1, **d)
            for i, d in enumerate(dict_list)
        ]
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[0], 'value', 'asc'),
            1
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[1], 'value', 'asc'),
            2
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[2], 'value', 'asc'),
            2
        )
        self.assertEqual(
            calculate.competition_rank(obj_list, obj_list[3], 'value', 'asc'),
            4
        )

        self.assertRaises(
            ValueError,
            calculate.competition_rank,
            obj_list,
            obj_list[3],
            'value',
            'foobar'
        )

    def test_date_range(self):
        dr = calculate.date_range(
            datetime(2009, 1, 1, 12, 31, 0),
            date(2009, 1, 3)
        )
        self.assertEqual(
            list(dr),
            [date(2009, 1, 1), date(2009, 1, 2), date(2009, 1, 3)]
        )
        self.assertRaises(
            ValueError,
            calculate.date_range,
            date(2011, 1, 1),
            date(2010, 12, 31)
        )
        dr2 = calculate.date_range(
            datetime(2009, 1, 1, 12, 31, 0),
            datetime(2009, 1, 3, 0, 0, 1)
        )
        self.assertEqual(
            list(dr2),
            [date(2009, 1, 1), date(2009, 1, 2), date(2009, 1, 3)]
        )

    def test_decile(self):
        self.assertEqual(calculate.decile([1, 2, 3, 4], 3), 8)
        self.assertEqual(
            calculate.decile([1, 2, 3, 3, 4], 3, kind='strict'),
            5
        )
        self.assertEqual(calculate.decile([1, 2, 3, 3, 4], 3, kind='weak'), 9)
        self.assertEqual(calculate.decile([1, 2, 3, 3, 4], 3, kind='mean'), 7)
        self.assertEqual(calculate.decile([1, 2, 3, 4], 4), 10)

    def test_elfi(self):
        self.assertEqual(
            calculate.elfi([0.2, 0.5, 0.05, 0.25]),
            0.64500000000000002
        )
        self.assertEqual(calculate.elfi([1]), 0)
        self.assertEqual(calculate.elfi([0.5, 0.5]), 0.5)
        self.assertRaises(ValueError, calculate.elfi, ['a', 0.2, 3])

    def test_equal_sized_breakpoints(self):
        self.assertEqual(
            calculate.equal_sized_breakpoints(list(range(1, 101)), 5),
            [1.0, 21.0, 41.0, 61.0, 81.0, 100.0]
        )
        self.assertEqual(
            calculate.equal_sized_breakpoints([1, 2, 3, 4, 5], 2),
            [1.0, 3.5, 5.0]
        )
        self.assertEqual(
            calculate.equal_sized_breakpoints([1, 2, 3, 4, 5, 6], 2),
            [1.0, 4.0, 6.0]
        )
        self.assertRaises(
            TypeError,
            calculate.equal_sized_breakpoints,
            ['foo', 'bar', 'baz'],
            2
        )
        self.assertRaises(
            TypeError,
            calculate.equal_sized_breakpoints,
            list(range(1, 101)),
            'a'
        )

    def test_margin_of_victory(self):
        self.assertEqual(
            calculate.margin_of_victory([3285, 2804, 7170]),
            3885
        )
        self.assertEqual(
            calculate.margin_of_victory([50708, 20639]),
            50708 - 20639
        )

    def test_mean(self):
        self.assertEqual(calculate.mean([1, 2, 3]), 2.0)
        self.assertEqual(calculate.mean([1, 99]), 50.0)
        self.assertEqual(calculate.mean([2, 3, 3]), 2.6666666666666665)
        self.assertRaises(ValueError, calculate.mean, ['a', 0.2, 3])

    def test_mean_center(self):
        dict_list = [
            {
                'name': 'The Los Angeles Times',
                'point': Point(-118.245517015, 34.0525260849, srid=4326)
            },
            {
                'name': 'The Higgins Building',
                'point': Point(-118.245015, 34.051007, srid=4326)
            },
            {
                'name': 'Los Angeles City Hall',
                'point': Point(-118.2430171966, 34.0535749927, srid=4326)
            },
        ]
        self.assertEqual(type(calculate.mean_center(dict_list)), Point)
        self.assertEqual(
            calculate.mean_center(dict_list).wkt,
            'POINT (-118.2445164038666690 34.0523693591999930)'
        )

        class DummyObj():
            def __init__(self, **entries):
                self.__dict__.update(entries)

        obj_list = [DummyObj(**d) for d in dict_list]
        self.assertEqual(type(calculate.mean_center(obj_list)), Point)
        self.assertEqual(
            calculate.mean_center(obj_list).wkt,
            'POINT (-118.2445164038666690 34.0523693591999930)'
        )

        class FakePoint(models.Model):
            fake_id = models.IntegerField(primary_key=True)
            name = models.TextField()
            point = models.PointField(srid=4326)

        obj_list = [
            FakePoint(fake_id=i + 1, **d)
            for i, d in enumerate(dict_list)
        ]
        self.assertEqual(type(calculate.mean_center(obj_list)), Point)
        self.assertEqual(
            calculate.mean_center(obj_list).wkt,
            'POINT (-118.2445164038666690 34.0523693591999930)'
        )

    def test_median(self):
        self.assertEqual(calculate.median([1, 3, 2]), 2.0)
        self.assertEqual(calculate.median([1, 2, 3, 4]), 2.5)
        self.assertRaises(TypeError, calculate.median, [None, 1, 2])
        self.assertRaises(ValueError, calculate.median, ['a', 1, 2])

    def test_mode(self):
        self.assertEqual(calculate.mode([1, 2, 3, 2]), 2.0)
        self.assertEqual(calculate.mode([1, 2, 3]), None)
        self.assertEqual(calculate.mode([2, 2, 2]), 2.0)
        self.assertRaises(TypeError, calculate.mode, [None, 1, 2])
        self.assertRaises(ValueError, calculate.mode, ['a', 1, 2])

    def test_nudge_points(self):

        class FakePoint(models.Model):
            name = models.CharField(max_length=30)
            point = models.PointField()
            objects = models.GeoManager()

        c1 = FakePoint(name='One', point=Point(0, 0))
        c2 = FakePoint(name='Two', point=Point(0, 0))
        c3 = FakePoint(name='Three', point=Point(1, 1))

        l = [c1, c2, c3]
        self.assertTrue(l[0].point == l[1].point)

        l2 = calculate.nudge_points(l)
        self.assertTrue(l2[0].point != l2[1].point)
        self.assertTrue(l[2].point == l2[2].point)

    def test_ordinal_rank(self):
        dict_list = [
            {'name': 'Joan', 'value': 1},
            {'name': 'Jane', 'value': 2},
            {'name': 'Mary', 'value': 3},
            {'name': 'Josh', 'value': 4},
        ]
        self.assertEqual(calculate.ordinal_rank(dict_list, dict_list[0]), 1)
        self.assertEqual(calculate.ordinal_rank(dict_list, dict_list[1]), 2)
        self.assertEqual(calculate.ordinal_rank(dict_list, dict_list[2]), 3)
        self.assertEqual(calculate.ordinal_rank(dict_list, dict_list[3]), 4)
        self.assertEqual(
            calculate.ordinal_rank(dict_list, dict_list[3], 'value', 'desc'),
            1
        )

        class DummyObj():
            def __init__(self, **entries):
                self.__dict__.update(entries)

        obj_list = [DummyObj(**d) for d in dict_list]
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[0], 'value', 'asc'),
            1
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[1], 'value', 'asc'),
            2
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[2], 'value', 'asc'),
            3
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[3], 'value', 'asc'),
            4
        )

        class DummyDjangoObj(models.Model):
            fake_id = models.IntegerField(primary_key=True)
            name = models.TextField()
            value = models.IntegerField()

            def __unicode__(self):
                return '%s (%s)' % (self.name, self.value)

        obj_list = [
            DummyDjangoObj(fake_id=i + 1, **d)
            for i, d in enumerate(dict_list)
        ]
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[0], 'value'),
            4
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[1], 'value'),
            3
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[2], 'value'),
            2
        )
        self.assertEqual(
            calculate.ordinal_rank(obj_list, obj_list[3], 'value'),
            1
        )

        self.assertRaises(
            ValueError,
            calculate.ordinal_rank,
            obj_list,
            obj_list[3],
            order_by='value',
            direction='foobar',
        )

    def test_pearson(self):
        students = [
            dict(sat=1200, gpa=3.6, drinks_per_day=0.3),
            dict(sat=1400, gpa=3.9, drinks_per_day=0.1),
            dict(sat=1100, gpa=3.0, drinks_per_day=0.5),
            dict(sat=800, gpa=2.5,  drinks_per_day=2.0),
        ]
        self.assertEqual(
            calculate.pearson(
                [i.get("sat") for i in students],
                [i.get("gpa") for i in students],
            ),
            0.9714441330841945
        )
        self.assertEqual(
            calculate.pearson(
                [i.get("sat") for i in students],
                [i.get("drinks_per_day") for i in students],
            ),
            -0.9435297685685435
        )
        self.assertRaises(ValueError, calculate.pearson, [1], [1, 2, 3])

    def test_per_capita(self):
        self.assertEqual(calculate.per_capita(12, 100000), 1.2)
        self.assertEqual(calculate.per_capita(12, 0), None)
        self.assertRaises(
            ZeroDivisionError,
            calculate.per_capita,
            12,
            0,
            fail_silently=False
        )

    def test_percentage(self):
        self.assertEqual(calculate.percentage(12, 60), 20)
        self.assertEqual(calculate.percentage(12, 60, multiply=False), 0.2)
        self.assertEqual(calculate.percentage(12, 0), None)
        self.assertRaises(
            ZeroDivisionError,
            calculate.percentage,
            12,
            0,
            fail_silently=False
        )

    def test_percentage_change(self):
        self.assertEqual(calculate.percentage_change(12, 60), 400)
        self.assertEqual(
            calculate.percentage_change(12, 60, multiply=False),
            4.0
        )
        self.assertEqual(calculate.percentage_change(12, 0), -100)
        self.assertEqual(calculate.percentage_change(0, 12), None)
        self.assertRaises(
            ZeroDivisionError,
            calculate.percentage_change,
            0,
            12,
            fail_silently=False
        )

    def test_percentile(self):
        self.assertEqual(calculate.percentile([1, 2, 3, 4], 3), 75)
        self.assertEqual(
            calculate.percentile([1, 2, 3, 3, 4], 3, kind='strict'),
            40
        )
        self.assertEqual(
            calculate.percentile([1, 2, 3, 3, 4], 3, kind='weak'),
            80
        )
        self.assertEqual(
            calculate.percentile([1, 2, 3, 3, 4], 3, kind='mean'),
            60
        )
        self.assertRaises(ValueError, calculate.percentile, ['a', 2, 3], 3)
        self.assertRaises(
            ValueError,
            calculate.percentile,
            [1, 2, 3, 4],
            3,
            kind='mystery-meat'
        )

    def test_per_sqmi(self):
        self.assertEqual(calculate.per_sqmi(12, 60), 0.2)
        self.assertEqual(calculate.per_sqmi(12, 0), None)
        self.assertRaises(
            ZeroDivisionError,
            calculate.per_sqmi,
            12,
            0,
            fail_silently=False
        )

    def test_ptable(self):
        from calculate import ptable
        ptable.indent(['foo', 'bar'])

    def test_random_point(self):
        ymin, xmin = 34.03743993275203, -118.27177047729492
        ymax, xmax = 34.0525171958097, -118.22404861450195
        random_point = calculate.random_point((xmin, ymin, xmax, ymax))
        self.assertEqual(random_point.x < xmax, True)
        self.assertEqual(random_point.x > xmin, True)
        self.assertEqual(random_point.y < ymax, True)
        self.assertEqual(random_point.y > ymin, True)

    def test_range(self):
        self.assertEqual(calculate.range([1, 2, 3]), 2)
        self.assertRaises(ValueError, calculate.range, ['a', 1, 2])
        self.assertRaises(ValueError, calculate.range, [1])

    def test_split_at_breakpoints(self):
        l = list(range(1, 31))
        bp = calculate.equal_sized_breakpoints(l, 5)
        self.assertEqual(bp, [1.0, 7.0, 13.0, 19.0, 25.0, 30.0])
        self.assertEqual(
            calculate.split_at_breakpoints(l, bp),
            [
                [1, 2, 3, 4, 5, 6],
                [7, 8, 9, 10, 11, 12],
                [13, 14, 15, 16, 17, 18],
                [19, 20, 21, 22, 23, 24],
                [25, 26, 27, 28, 29, 30]
            ]
        )
        self.assertRaises(
            Exception,
            calculate.split_at_breakpoints,
            ['foo', 'bar', 'baz'],
            bp,
        )
        self.assertRaises(
            Exception,
            calculate.split_at_breakpoints,
            l,
            ['foo', 'bar', 'baz'],
        )

    def test_standard_deviation(self):
        self.assertEqual(
            calculate.standard_deviation([2, 3, 3, 4]),
            0.70710678118654757
        )
        self.assertEqual(
            calculate.standard_deviation([-2, 3, 3, 40]),
            16.867127793432999
        )
        self.assertRaises(
            ValueError,
            calculate.standard_deviation,
            ['a', 2, 3, 3, 4]
        )

    def test_standard_deviation_distance(self):
        dict_list = [
            {
                'name': 'The Los Angeles Times',
                'point': Point(-118.2455170154, 34.0525260849, srid=4326)
            },
            {
                'name': 'The Higgins Building',
                'point': Point(-118.245015, 34.051007, srid=4326)
            },
            {
                'name': 'Los Angeles City Hall',
                'point': Point(-118.2430171966, 34.0535749927, srid=4326)
            },
        ]

        self.assertEqual(
            calculate.standard_deviation_distance(dict_list),
            0.0003720200725858596
        )

        class DummyObj():
            def __init__(self, **entries):
                self.__dict__.update(entries)

        obj_list = [DummyObj(**d) for d in dict_list]
        self.assertEqual(
            calculate.standard_deviation_distance(obj_list),
            0.0003720200725858596
        )

        class FakePoint(models.Model):
            fake_id = models.IntegerField(primary_key=True)
            name = models.TextField()
            point = models.PointField(srid=4326)

        obj_list = [
            FakePoint(fake_id=i + 1, **d)
            for i, d in enumerate(dict_list)
        ]
        self.assertEqual(
            calculate.standard_deviation_distance(obj_list),
            0.0003720200725858596
        )

    def test_variation_coefficient(self):
        self.assertEqual(
            calculate.variation_coefficient([1, 2, -2, 4, -3]),
            6.442049363362563
        )
        self.assertEqual(
            calculate.variation_coefficient(range(1, 100000)),
            0.5773444956580661
        )
        self.assertRaises(
            ValueError,
            calculate.variation_coefficient,
            ['a', 2, 3, 3, 4]
        )

    def test_summary_stats(self):
        _stdout = sys.stdout
        sys.stdout = io.StringIO()
        calculate.summary_stats(list(range(1, 101)))
        sys.stdout = _stdout


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = variation_coefficient
import calculate


def variation_coefficient(data_list):
    """
    Accepts a list of values and returns the variation coefficient,
    which is a normalized measure of the distribution.

    This is the sort of thing you can use to compare the standard deviation
    of sets that are measured in different units.

    Note that it uses our "population" standard deviation as part of the
    calculation, not a "sample standard deviation.

    h3. Example usage

        >>> import calculate
        >>> calculate.variation_coefficient([1, 2, -2, 4, -3])
        6.442049363362563

    h3. Documentation

        * "coefficient of variation":http://en.wikipedia.org/wiki/\
Coefficient_of_variation
    """
    # Convert all the values to floats and test to make sure
    # there aren't any strings in there
    try:
        data_list = list(map(float, data_list))
    except ValueError:
        raise ValueError('Input values must contain numbers')
    std = calculate.standard_deviation(data_list)
    mean = calculate.mean(data_list)
    return std / mean

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# latimes-calculate documentation build configuration file, created by
# sphinx-quickstart on Sat Mar 15 21:50:26 2014.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'latimes-calculate'
copyright = u'2014, Los Angeles Times Data Desk'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2'
# The full version, including alpha/beta/rc tags.
release = '0.2'

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
htmlhelp_basename = 'latimes-calculatedoc'


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
  ('index', 'latimes-calculate.tex', u'latimes-calculate Documentation',
   u'Los Angeles Times Data Desk', 'manual'),
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
    ('index', 'latimes-calculate', u'latimes-calculate Documentation',
     [u'Los Angeles Times Data Desk'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'latimes-calculate', u'latimes-calculate Documentation',
   u'Los Angeles Times Data Desk', 'latimes-calculate', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = quicktest
import os
import sys
import argparse
from django.conf import settings


class QuickDjangoTest(object):
    """
    A quick way to run the Django test suite without a fully-configured project.
    
    Example usage:
    
        >>> QuickDjangoTest('app1', 'app2')
    
    Based on a script published by Lukasz Dziedzia at: 
    http://stackoverflow.com/questions/3841725/how-to-launch-tests-for-django-reusable-app
    """
    DIRNAME = os.path.dirname(__file__)
    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'django.contrib.gis',
    )
    
    def __init__(self, *args, **kwargs):
        self.apps = args
        # Get the version of the test suite
        self.version = self.get_test_version()
        # Call the appropriate one
        if self.version == 'new':
            self._new_tests()
        else:
            self._old_tests()
    
    def get_test_version(self):
        """
        Figure out which version of Django's test suite we have to play with.
        """
        from django import VERSION
        if VERSION[0] == 1 and VERSION[1] >= 2:
            return 'new'
        else:
            return 'old'
    
    def _old_tests(self):
        """
        Fire up the Django test suite from before version 1.2
        """
        settings.configure(DEBUG = True,
           DATABASE_ENGINE = 'sqlite3',
           DATABASE_NAME = os.path.join(self.DIRNAME, 'database.db'),
           INSTALLED_APPS = self.INSTALLED_APPS + self.apps,
           TEST_RUNNER = 'django.contrib.gis.tests.run_tests'
        )
        from django.test.simple import run_tests
        failures = run_tests(self.apps, verbosity=1)
        if failures:
            sys.exit(failures)
    
    def _new_tests(self):
        """
        Fire up the Django test suite developed for version 1.2
        """
        settings.configure(
            DEBUG = True,
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': 'foobar',
                    'USER': '',
                    'PASSWORD': '',
                    'HOST': '',
                    'PORT': '',
                }
            },
            INSTALLED_APPS = self.INSTALLED_APPS + self.apps
        )
        from django.test.simple import DjangoTestSuiteRunner
        failures = DjangoTestSuiteRunner().run_tests(self.apps, verbosity=1)
        if failures:
            sys.exit(failures)

if __name__ == '__main__':
    """
    What do when the user hits this file from the shell.
    
    Example usage:
    
        $ python quicktest.py app1 app2
    
    """
    parser = argparse.ArgumentParser(
        usage="[args]",
        description="Run Django tests on the provided applications."
    )
    parser.add_argument('apps', nargs='+', type=str)
    args = parser.parse_args()
    QuickDjangoTest(*args.apps)

########NEW FILE########
