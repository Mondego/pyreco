__FILENAME__ = chartdata
import copy
from collections import defaultdict
from itertools import groupby, chain, islice
from operator import itemgetter
# use SortedDict instead of native OrderedDict for Python 2.6 compatibility
from django.utils.datastructures import SortedDict
from validation import clean_dps, clean_pdps
from chartit.validation import clean_sortf_mapf_mts

class DataPool(object):
    """DataPool holds the data retrieved from various models (tables)."""
    
    def __init__(self, series):
        """Create a DataPool object as specified by the ``series``.
        
        :Arguments: 
        
        - **series** *(list of dict)* - specifies the what data to retrieve 
          and where to retrieve it from. It is of the form ::
          
            [{'options': {
               'source': a django model, Manager or QuerySet,
               },
             'terms': [
               'a_valid_field_name', ... ,
               {'any_name': 'a_valid_field_name', ... },
               ]
            },
            ... 
            ]
        
          Where 
          
          - **options** (**required**) - a ``dict``. Any of the `series 
            options <http://www.highcharts.com/ref/#series>`_ for the 
            Highcharts ``options`` object are valid. 
              
          - **terms** - is a list. Each element in ``terms`` is either 
            
            1. a ``str`` - needs to be a valid model field for the 
               corresponding ``source``, or 
            2. a ``dict`` - need to be of the form 
               ``{'any_name': 'a_valid_field_name', ...}``. 
          
          To retrieve data from multiple models or QuerySets, just add more 
          dictionaries with the corresponding ``options`` and terms.
          
        :Raises:
          
        - **APIInputError** - sif the ``series`` argument has any invalid 
          parameters.
        
         
        .. warning:: All elements in ``terms`` **must be unique** across all 
           the dictionaries in the ``series`` list. If there are two terms 
           with same ``name``, the latter one is going to overwrite the one 
           before it.
        
        For example, the following is **wrong**: ::
        
          [{'options': {
              'source': SomeModel},
            'terms':[
              'foo', 
              'bar']},
           {'options': {
              'source': OtherModel},
            'terms':[
              'foo']}]
              
        In this case, the term ``foo`` from ``OtherModel`` is going to 
        **overwrite** ``foo`` from ``SomeModel``. 
        
        Here is the **right** way of retrieving data from two different models 
        both of which have the same field name. ::
        
          [{'options': {
             'source': SomeModel},
            'terms':[
              'foo', 
              'bar']},
           {'options': {
             'source': OtherModel},
            'terms':[
              {'foo_2': 'foo'}]}]
         """
        # Save user input to a separate dict. Can be used for debugging.
        self.user_input = {}
        self.user_input['series'] = copy.deepcopy(series)
        self.series = clean_dps(series)
        self.query_groups = self._group_terms_by_query()
        # Now get data
        self._get_data()
    
    def _group_terms_by_query(self, sort_by_term=None, *addl_grp_terms):
        """Groups all the terms that can be extracted in a single query. This 
        reduces the number of database calls. 
        
        :returns: 
        
        - a list of sub-lists where each sub-list has items that can 
          all be retrieved with the same query (i.e. terms from the same source 
          and any additional criteria as specified in addl_grp_terms).
        """
        # TODO: using str(source.query) was the only way that I could think of
        # to compare whether two sources are exactly same. Need to figure out
        # if there is a better way. - PG
        sort_grp_fn = lambda (tk, td): tuple(chain(str(td['source'].query), 
                                              [td[t] for t in addl_grp_terms]))
        s = sorted(self.series.items(), key=sort_grp_fn)
        # The following groupby will create an iterator which returns 
        # <(grp-1, <(tk, td), ...>), (grp-2, <(tk, td), ...>), ...>
        # where sclt is a source, category, legend_by tuple
        qg = groupby(s, sort_grp_fn)
        if sort_by_term is not None:
            sort_by_fn = lambda (tk, td): -1*(abs(td[sort_by_term]))
        else:
            sort_by_fn = None
        qg = [sorted(itr, key=sort_by_fn) for (grp, itr) in qg]
        return qg

    def _generate_vqs(self):
        # query_groups is a list of lists.
        for tk_td_tuples in self.query_groups:
            src = tk_td_tuples[0][1]['source']
            vqs = src.values(*(td['field'] for (tk, td) in tk_td_tuples))
            yield tk_td_tuples, vqs
    
    def _get_data(self):
        for tk_td_tuples, vqs in self._generate_vqs():
            vqs_list = list(vqs)
            for tk, td in tk_td_tuples:
                # everything has a reference to the same list
                self.series[tk]['_data'] = vqs_list

class PivotDataPool(DataPool):
    """PivotDataPool holds the data retrieved from various tables (models) and 
    then *pivoted* against the category fields."""
    
    def __init__(self, series, top_n_term=None, top_n=None, pareto_term=None, 
                 sortf_mapf_mts=None):
        """ Creates a PivotDataPool object. 
        
        :Arguments: 
        
        - **series** (**required**) - a list of dicts that specifies the what 
          data to retrieve, where to retrieve it from and how to pivot the 
          data. It is of the form ::
           
            [{'options': {
                'source': django Model, Manager or QuerySet ,
                'categories': ['a_valid_field', ...],
                'legend_by': ['a_valid_field', ...] (optional),
                'top_n_per_cat': a number (optional),
              },
              'terms': {
                'any_name_here': django Aggregate,
                'some_other_name':{
                  'func': django Aggregate,
                  #any options to override
                  ...
                },
              ...
              }
             },
             ... #repeat dicts with 'options' & 'terms'
            ]
        
          Where 
        
          - **options** - is a dict that specifies the common options for all 
            the terms. 
            
            + **source** (**required**) - is either a ``Model``, ``Manager`` 
              or a ``QuerySet``.
            + **categories** (**required**) - is a list of model fields by 
              which the data needs to be pivoted by. If there is only a single 
              item, ``categories`` can just be a string instead of a list with 
              single element.  
              
              For example if you have a model with ``country``, ``state``, 
              ``county``, ``city``, ``date``, ``rainfall``, ``temperature`` 
              and you want to pivot the data by ``country`` and ``state``, 
              then ``categories = ['country', 'state']`` .
              
              .. note:: Order of elements in the ``categories`` list matters!
              
              ``categories = ['country', 'state']`` groups your data first by 
              ``country`` and then by ``state`` when running the SQL query. 
              This obviously is not the same as grouping by ``state`` first 
              and then by ``country``.
                  
            + **legend_by** (*optional*) - is a list of model fields by which 
              the data needs to be legended by. For example, in the above case, 
              if you want to legend by ``county`` and ``city``, then 
              ``legend_by = ['county', 'city']``
              
              .. note:: Order of elements in the ``legend_by`` list matters!
              
              See the note in ``categories`` above.
              
            + **top_n_per_cat** (*optional*) - The number of top items that 
              the legended entries need to be limited to in each category. For 
              example, in the above case, if you wanted only the top 3 
              ``county/cities`` with highest rainfall for each of the 
              ``country/state``, then ``top_n_per_cat = 3``.
            
          - **terms** - is a ``dict``. The keys can be any strings (but helps 
            if they are meaningful aliases for the field). The values can 
            either be  
          
            + a django ``Aggregate`` : of a valid field in corresponding model. 
              For example, ``Avg('temperature')``, ``Sum('price')``, etc. or 
            + a ``dict``: In this case the ``func`` must specify relevant 
              django aggregate to retrieve. For example 
              ``'func': Avg('price')``. The dict can also have any additional 
              entries from the options dict. Any entries here will override 
              the entries in the ``options`` dict.
        
        - **top_n_term** (*optional*) - a string. Must be one of the keys in 
          the corresponding ``terms`` in the ``series`` argument.
         
        - **top_n** (*optional*) - an integer. The number of items for the 
          corresponding ``top_n_term`` that need to be retained. 
         
          If ``top_n_term`` and ``top_n`` are present, only the ``top_n`` 
          numberof items are going to displayed in the pivot chart. For 
          example, if you want to plot only the top 5 states with highest 
          average rainfall, you can do something like this. ::
            
            PivotDataPool(
              series = [
                 {'options': {
                    'source': RainfallData.objects.all(),
                    'categories': 'state'},
                  'terms': { 
                    'avg_rain': Avg('rainfall')}}],
              top_n_term = 'avg_rain',
              top_n = 5)
          
          Note that the ``top_n_term`` is ``'avg_rain'`` and **not** ``state``; 
          because we want to limit by the average rainfall.
        
        - **pareto_term** (*optional*) - the term with respect to which the 
          pivot chart needs to be paretoed by. 
          
          For example, if you want to plot the average rainfall on the y-axis 
          w.r.t the state on the x-axis and want to pareto by the average 
          rainfall, you can do something like this. ::
          
            PivotDataPool(
              series = [
                 {'options': {
                    'source': RainfallData.objects.all(),
                    'categories': 'state'},
                  'terms': { 
                    'avg_rain': Avg('rainfall')}}],
              pareto_term = 'avg_rain')
                
        - **sortf_mapf_mts** (*optional*) - a ``tuple`` with three elements of
          the form ``(sortf, mapf, mts)`` where 
          
          + **sortf** - is a function (or a callable) that is used as a `key`
            when sorting the category values. 
             
            For example, if ``categories = 'month_num'`` and if the months
            need to be sorted in reverse order, then ``sortf`` can be :: 
              
              sortf = lambda *x: (-1*x[0],) 
          
            .. note:: ``sortf`` is passed the category values as tuples and 
               must return tuples! 
              
            If ``categories`` is ``['city', 'state']`` and if the category 
            values returned need to be sorted with state first and then city, 
            then ``sortf`` can be :: 
              
              sortf = lambda *x: (x[1], x[0])
              
            The above ``sortf`` is passed tuples like 
            ``('San Francisco', 'CA')``, ``('New York', 'NY')``, ``...`` and 
            it returns tuples like ``('CA', 'San Francisco')``, 
            ``('NY', 'New York')``, ``...`` which when used as keys to sort the 
            category values will obviously first sort by state and then by 
            city.
                  
          + **mapf** - is a function (or a callable) that defines how the 
            category values need to be mapped.
            
            For example, let's say ``categories`` is ``'month_num'`` and that 
            the category values that are retrieved from your database are 
            ``1``, ``2``, ``3``, etc. If you want month *names* as the 
            category values instead of month numbers, you can define a 
            ``mapf`` to transform the month numbers to month names like so ::
              
              def month_name(*t):
                  names ={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 
                          5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 
                          9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
                  month_num = t[0]
                  return (names[month_num], )
              
              mapf = month_name
            
            .. note:: ``mapf`` like ``sortf`` is passed the category values 
               as tuples and must return tuples.
               
          + **mts** - *map then sort* ; a ``bool``. If ``True``, the 
            category values are mapped first and then sorted, and if 
            ``False`` category values are sorted first and then mapped.
            
            In the above example of month names, we ``mts`` must be ``False``
            because the months must first be sorted based on their number 
            and then mapped to their names. If ``mts`` is ``True``, the 
            month numbers would be transformed to the month names, and then 
            sorted, which would yield an order like ``Apr``, ``Aug``, 
            ``Dec``, etc. (not what we want).
        
        :Raises:    
          
        - **APIInputError** - if the ``series`` argument has any invalid 
          parameters.

        Here is a full example of a ``series`` term that retrieves the 
        average temperature of the top 3 cities in each country/state and 
        the average rainfall of the top 2 cities in each country/state. ::
        
          [{'options': {
              'source': Weather.objects.all(),
              'categories': ['country', 'state'],
              'legend_by': 'city', 
              'top_n_per_cat': 3}, 
            'terms': {
              'avg_temp': Avg('temperature'),
              'avg_rain': {
                'func': Avg('rainfall'),
                'top_n_per_cat': 2}}}]
        
        The ``'top_n_per_cat': 2`` term in ``avg_rain`` dict overrides 
        ``'top_n_per_cat': 5`` from the comon options dict. Effectively, 
        the above ``series`` retrieves the *top 2*  ``cities`` with 
        highest ``avg_rain`` in each ``country/state`` and *top 3* ``cities`` 
        with highest ``avg_temp`` in each ``country/state``.
             
        A single ``PivotDataPool`` can hold data from multiple Models. 
        If there are more models or QuerySets to retrieve the data from, 
        just add more dicts to the series list with different ``source`` 
        values.
        
        .. warning:: The ``keys`` for the ``terms`` must be **unique across 
           all the dictionaries** in the ``series`` list! If there are 
           multiple terms with same ``key``, the latter ones will just 
           overwrite the previous ones.
        
        For instance, the following example is **wrong**. ::
        
          [{'options': {
              'source': EuropeWeather.objects.all(),
              'categories': ['country', 'state']}, 
            'terms': {
              'avg_temp': Avg('temperature')}},
           {'options': {
               'source': AsiaWeather.objects.all(),
               'categories': ['country', 'state']},
            'terms': {
              'avg_temp': Avg('temperature')}}]
        
        The second ``avg_temp`` will overwrite the first one. Instead just 
        use different names for each of the keys in all the dictionaries. 
        Here is the **right** format. ::
          
          [{'options': {
              'source': EuropeWeather.objects.all(),
              'categories': ['country', 'state']}, 
            'terms': {
              'europe_avg_temp': Avg('temperature')}},
           {'options': {
               'source': AsiaWeather.objects.all(),
               'categories': ['country', 'state']},
            'terms': {
              'asia_avg_temp': Avg('temperature')}}]
        """
        # Save user input to a separate dict. Can be used for debugging.
        self.user_input = locals()
        self.user_input['series'] = copy.deepcopy(series)
        
        self.series = clean_pdps(series)
        self.top_n_term = (top_n_term if top_n_term 
                           in self.series.keys() else None)
        self.top_n = (top_n if (self.top_n_term is not None 
                                and isinstance(top_n, int)) else 0)   
        self.pareto_term = (pareto_term if pareto_term in 
                            self.series.keys() else None)
        self.sortf, self.mapf, self.mts = clean_sortf_mapf_mts(sortf_mapf_mts)
        # query groups and data
        self.query_groups = \
          self._group_terms_by_query('top_n_per_cat','categories','legend_by')
        self._get_data()

    def _generate_vqs(self):
        """Generates and yields the value query set for each query in the  
        query group."""
        # query_groups is a list of lists.
        for tk_td_tuples in self.query_groups:
            # tk: term key, td: term dict
            # All (tk, td) tuples within the list tk_td_tuples, share the same 
            # source, categories and legend_by. So we can extract these three 
            # from the first tuple in the list.
            tk, td = tk_td_tuples[0]
            qs = td['source']
            categories = td['categories']
            legend_by = td['legend_by']
            #vqs = values queryset
            values_terms = chain(categories, legend_by)
            vqs = qs.values(*values_terms)
            # NOTE: Order of annotation is important!!!
            # So need an SortedDict. Can't use a regular dict.
            ann_terms = SortedDict((k, d['func']) for k, d in tk_td_tuples)
            vqs = vqs.annotate(**ann_terms)
            # Now order by
            top_n_per_cat = td['top_n_per_cat']
            if top_n_per_cat > 0:
                order_by = ('-' + tk,)
            elif top_n_per_cat < 0:
                order_by = (tk,)
            else:
                order_by = ()
            order_by_terms = chain(categories, order_by)
            vqs = vqs.order_by(*order_by_terms)
            yield tk_td_tuples, vqs

    def _get_data(self):
        # These are some of the attributes that will used to store some
        # temporarily generated data.
        self.cv_raw = set([])
        _pareto_by_cv = defaultdict(int)
        _cum_dfv_by_cv = defaultdict(int)
        for tk_td_tuples, vqs in self._generate_vqs():
            # tk: term key, td: term dict
            # All (tk, td) tuples within the list tk_td_tuples, share the same 
            # source, categories and legend_by. So we can extract these three 
            # from the first tuple in the list.
            tk, td = tk_td_tuples[0]
            categories = td['categories']
            legend_by = td['legend_by']
            for i, (tk, td) in enumerate(tk_td_tuples):
                # cv_lv_dfv: dict with category value, legend value as keys 
                # and datafunc-values as values.
                # For example, if
                # category = ['continent'], legend_by = ['country'] and
                # func = Sum('population_millions')
                # cv_lv_dfv = {'Asia': {'India': 1001, 'China': 1300},
                #              'Europe': {'UK': 61.8, 'France': 62.6},
                #              ... }
                cv_lv_dfv = defaultdict(dict)
                # lv_set is the set of legend_values
                # For instance, lv_set for the above example is
                # set(['India', 'China', 'UK', 'France'])
                lv_set = set()
                # cv: category value. For example, 
                # if categories = ('continent', 'country'), then
                # cv = ('NA', 'USA'), ('Asia', 'India'), etc.
                # g_vqs_by_cv = grouped ValueQuerySet (grouped by cv)
                # i.e. grouped by ('NA', 'USA'), ('Asia', 'India'), etc.
                #
                # vqs is a list of dicts. For example
                # [{'continent': 'NA', 'country': 'USA', 'pop__sum': 300}]
                for cv, g_vqs_by_cv in groupby(vqs, itemgetter(*categories)):
                    if not isinstance(cv, tuple):
                        cv = (cv,)
                    cv = tuple(map(str, cv))
                    self.cv_raw |= set([cv])
                    # For the first loop (i==0), the queryset is already 
                    # pre-sorted by value of the data func alias (for example 
                    # pop__sum) when retrieved from the DB. So don't
                    # sort it again. If we need to retrieve all the 
                    # elements (not just top n) per category 
                    # (fd['top_n_per_group'] == 0), we don't care about the 
                    # sort order. Don't sort in this case.
                    if i != 0 and td['top_n_per_cat'] != 0:
                        g_vqs_by_cv.sort(key=itemgetter(tk), 
                                         reverse=(td['top_n_per_cat']> 0))
                    # g_vqs_by_cv_dfv: Grouped Value QuerySet (grouped by 
                    # category and then by datafunc value.
                    # alias = 'population__sum'
                    # itemgetter('pop__sum') = 10 etc.
                    # So grouped by pop__sum = 10, 9, etc.
                    # NOTE: Need this step to make sure we retain duplicates 
                    # in the top n if there are multiple entries. For example
                    # if pop__sum is 10, 10, 9, 9, 7, 3, 2, 1 and we want
                    # top 3, then the result should we 10, 10, 9, 9, 7 and 
                    # not just 10, 10, 9. A simple list slice will only retain
                    # 10, 10, 9. So it is not useful. An alternative is to 
                    # group_by and then slice.
                    g_vqs_by_cv_dfv = groupby(g_vqs_by_cv,itemgetter(tk))
                    # Now that this is grouped by datafunc value, slice off
                    # if we only need the top few per each category
                    if td['top_n_per_cat'] != 0:
                        g_vqs_by_cv_dfv = islice(g_vqs_by_cv_dfv,0, 
                                               abs(td['top_n_per_cat']))
                    # Now build the result dictionary
                    # dfv = datafunc value
                    # vqs_by_c_dfv =  ValuesQuerySet by cat. and datafunc value
                    for dfv, vqs_by_cv_dfv in g_vqs_by_cv_dfv:
                        if tk == self.top_n_term:
                            _cum_dfv_by_cv[cv] += dfv
                        if tk == self.pareto_term:
                            _pareto_by_cv[cv] += dfv
                        for vd in vqs_by_cv_dfv:
                            # vd: values dict
                            # vd: {'continent': 'NA', 'country': 'USA', 
                            #      'year': 2010, 'quarter': 2,
                            #      'population__avg': 301,
                            #      'gdp__avg': 14.12}
                            # category = ('continent', 'country',)
                            # legend = ('year', 'quarter')
                            # lv = (2010, 2)
                            # dfa = 'price__max'
                            # cv_lv_dfv[('NA', 'USA')][(2010, 2)] = 301
                            try:
                                lv = itemgetter(*legend_by)(vd)
                                if not isinstance(lv, tuple):
                                    lv = (lv,)
                                lv = tuple(map(str, lv))
                            # If there is nothing to legend by i.e. 
                            # legend_by=() then itemgetter raises a TypeError. 
                            # Handle it.
                            except TypeError:
                                lv = ()
                            cv_lv_dfv[cv][lv] = vd[tk]
                            lv_set |= set([lv])
                td['_cv_lv_dfv'] = cv_lv_dfv
                td['_lv_set'] = lv_set
        # If we only need top n items, remove the other items from self.cv_raw
        if self.top_n_term:
            cum_cv_dfv_items = sorted(_cum_dfv_by_cv.items(), 
                                      key = itemgetter(1),
                                      reverse = self.top_n > 0)
            cv_dfv_top_n_items = cum_cv_dfv_items[0:abs(self.top_n)]
            self.cv_raw = [cv_dfv[0] for cv_dfv in cv_dfv_top_n_items]
        else:
            self.cv_raw = list(self.cv_raw)
        # If we need to pareto, order the category values in pareto order.
        if self.pareto_term:
            pareto_cv_dfv_items = sorted(_pareto_by_cv.items(), 
                                         key = itemgetter(1) ,
                                         reverse = True)
            pareto_cv = [cv_dfv[0] for cv_dfv in pareto_cv_dfv_items]
            if self.top_n_term:
                self.cv_raw = [cv for cv in pareto_cv if cv in self.cv_raw]
            else:
                self.cv_raw = pareto_cv
            
            if self.mapf is None:
                self.cv = self.cv_raw
            else:
                self.cv = [self.mapf(cv) for cv in self.cv_raw]
        else:
            # otherwise, order them by sortf if there is one.
            if self.mapf is None:
                self.cv_raw.sort(key=self.sortf)
                self.cv = self.cv_raw
            else:
                self.cv = [self.mapf(cv) for cv in self.cv_raw]
                if self.mts: 
                    combined = sorted(zip(self.cv, self.cv_raw),key=self.sortf)
                    self.cv, self.cv_raw = zip(*combined)
########NEW FILE########
__FILENAME__ = charts
import copy
from collections import defaultdict
from itertools import groupby, izip
# use SortedDict instead of native OrderedDict for Python 2.6 compatibility
from django.utils.datastructures import SortedDict

from highcharts import HCOptions
from validation import clean_pcso, clean_cso, clean_x_sortf_mapf_mts
from exceptions import APIInputError
from chartdata import PivotDataPool, DataPool

class Chart(object):
    
    def __init__(self, datasource, series_options, chart_options=None,
                 x_sortf_mapf_mts=None):
        """Chart accept the datasource and some options to create the chart and
        creates it. 
        
        **Arguments**:
        
        - **datasource** (**required**) - a ``DataPool`` object that holds the 
          terms and other information to plot the chart from.
          
        - **series_options** (**required**) - specifies the options to plot 
          the terms on the chart. It is of the form ::
           
            [{'options': {
                #any items from HighChart series. For ex.,
                'type': 'column'
               },
               'terms': {
                 'x_name': ['y_name', 
                            {'other_y_name': {
                               #overriding options}}, 
                            ...],
                 ...
                 },
               },
              ... #repeat dicts with 'options' & 'terms'
              ]
            
          Where - 
          
          - **options** (**required**) - a ``dict``. Any of the parameters 
            from the `Highcharts options object - series array
            <http://www.highcharts.com/ref/#series>`_ are valid as entries in 
            the ``options`` dict except ``data`` (because data array is 
            generated from your datasource by chartit). For example, ``type``, 
            ``xAxis``, etc. are all valid entries here. 
            
            .. note:: The items supplied in the options dict are not validated 
               to make sure that Highcharts actually supports them. Any 
               invalid options are just passed to Highcharts JS which silently 
               ignores them.
               
          - **terms** (**required**) - a ``dict``. keys are the x-axis terms
            and the values are lists of y-axis terms for that particular 
            x-axis term. Both x-axis and y-axis terms must be present in the 
            corresponding datasource, otherwise an APIInputError is raised.
            
            The entries in the y-axis terms list must either be a ``str`` or 
            a ``dict``. If entries are dicts, the keys need to be valid y-term 
            names and the values need to be any options to override the 
            default options. For example, ::
            
              [{'options': {
                  'type': 'column',
                  'yAxis': 0},
                'terms': {
                  'city': [
                    'temperature',
                   {'rainfall': {
                      'type': 'line',
                      'yAxis': 1}}]}}]
            
            plots a column chart of city vs. temperature as a line chart on 
            yAxis: 0 and city vs. rainfall as a line chart on yAxis: 1. This 
            can alternatively be expressed as two separate entries: ::
            
              [{'options': {
                  'type': 'column',
                  'yAxis': 0},
                'terms': {
                  'city': [
                    'temperature']}},
               {'options': {
                  'type': 'line',
                  'yAxis': 1},
                'terms': {
                  'city': [
                    'rainfall']}}]
                    
        - **chart_options** (*optional*) - a ``dict``. Any of the options from 
          the `Highcharts options object <http://www.highcharts.com/ref/>`_ 
          are valid (except the options in the ``series`` array which are 
          passed in the ``series_options`` argument. The following 
          ``chart_options`` for example, set the chart title and the axes 
          titles. :: 
          
              {'chart': {
                 'title': { 
                   'text': 'Weather Chart'}},
               'xAxis': {
                 'title': 'month'},
               'yAxis': {
                 'title': 'temperature'}}
                 
          .. note:: The items supplied in the ``chart_options`` dict are not 
             validated to make sure that Highcharts actually supports them. 
             Any invalid options are just passed to Highcharts JS which 
             silently ignores them.
             
        **Raises**: 
        
        - ``APIInputError`` if any of the terms are not present in the 
          corresponding datasource or if the ``series_options`` cannot be 
          parsed.
        """
        
        self.user_input = locals()
        if not isinstance(datasource, DataPool):
            raise APIInputError("%s must be an instance of DataPool." 
                                %datasource)
        self.datasource = datasource
        self.series_options = clean_cso(series_options, self.datasource)
        self.x_sortf_mapf_mts = clean_x_sortf_mapf_mts(x_sortf_mapf_mts)
        self.x_axis_vqs_groups = self._groupby_x_axis_and_vqs()
        self._set_default_hcoptions(chart_options)
        self.generate_plot()
    
    def _groupby_x_axis_and_vqs(self):
        """Returns a list of list of lists where each list has the term and 
        option dict with the same xAxis and within each list with same xAxis,
        all items in same sub-list have items with same ValueQuerySet.
        
        Here is an example of what this function would return. ::
        
        [
         [[(term-1-A-1, opts-1-A-1), (term-1-A-2, opts-1-A-2), ...],
          [(term-1-B-1, opts-1-B-1), (term-1-B-2, opts-1-B-2), ...],
          ...],
         [[term-2-A-1, opts-2-A-1), (term-2-A-2, opts-2-A-2), ...],
          [term-2-B-2, opts-2-B-2), (term-2-B-2, opts-2-B-2), ...],
          ...],
          ...
          ]
          
        In the above example,
        
        - term-1-*-* all have same xAxis.
        - term-*-A-* all are from same ValueQuerySet (table)
        """
        dss = self.datasource.series
        x_axis_vqs_groups = defaultdict(dict)
        sort_fn = lambda (tk, td): td.get('xAxis', 0)
        so = sorted(self.series_options.items(), key=sort_fn)
        x_axis_groups = groupby(so, sort_fn)
        for (x_axis, itr1) in x_axis_groups:
            sort_fn = lambda (tk, td): dss[td['_x_axis_term']]['_data']
            itr1 = sorted(itr1, key=sort_fn)
            for _vqs_num, (_data, itr2) in enumerate(groupby(itr1, sort_fn)):
                x_axis_vqs_groups[x_axis][_vqs_num] = _x_vqs = {}
                for tk, td in itr2:
                    _x_vqs.setdefault(td['_x_axis_term'], []).append(tk)
        return x_axis_vqs_groups
        
    def _set_default_hcoptions(self, chart_options):
        """Set some default options, like xAxis title, yAxis title, chart 
        title, etc.
        """
        so = self.series_options
        dss = self.datasource.series
        self.hcoptions = HCOptions({})
        if chart_options is not None:
            self.hcoptions.update(chart_options)
        self.hcoptions['series'] = []
        # Set title
        title = ''
        for x_axis_num, vqs_group in self.x_axis_vqs_groups.items():
            for vqs_num, x_y_terms in  vqs_group.items():
                for x_term, y_terms in x_y_terms.items():
                    title += ', '.join([dss[y_term]['field_alias'].title() 
                              for y_term in y_terms])
                    title += ' vs. '
                    title += dss[x_term]['field_alias'].title()
                title += ' & '
        if not self.hcoptions['title']['text']:
            self.hcoptions['title']['text'] = title[:-3]
        # if xAxis and yAxis are supplied as a dict, embed it in a list
        # (needed for multiple axes) 
        xAxis, yAxis = self.hcoptions['xAxis'], self.hcoptions['yAxis']
        if isinstance(xAxis, dict):
            self.hcoptions['xAxis'] = [xAxis]
        if isinstance(yAxis, dict):
            self.hcoptions['yAxis'] = [yAxis]
        # set renderTo
        if not self.hcoptions['chart']['renderTo']:
            self.hcoptions['chart']['renderTo'] = 'container'
        
        term_x_axis = [(dss[d['_x_axis_term']]['field_alias'].title(), 
                        d.get('xAxis', 0)) 
                       for (k, d) in so.items()]
        term_y_axis = [(dss[k]['field_alias'].title(), d.get('xAxis', 0)) 
                       for (k, d) in so.items()]
        max_x_axis = max(t[1] for t in term_x_axis)
        max_y_axis = max(t[1] for t in term_y_axis)
        x_axis_len = len(self.hcoptions['xAxis'])
        y_axis_len = len(self.hcoptions['yAxis'])
        if max_x_axis >= x_axis_len:
            self.hcoptions['xAxis']\
              .extend([HCOptions({})]*(max_x_axis+1-x_axis_len))
        for i, x_axis in enumerate(self.hcoptions['xAxis']):
            if not x_axis['title']['text']:
                axis_title = set(t[0] for t in term_x_axis if t[1] == i)
                x_axis['title']['text'] = ' & '.join(axis_title)
        if max_x_axis == 1:
            if self.hcoptions['xAxis'][1]['opposite'] != False:
                self.hcoptions['xAxis'][1]['opposite'] = True
                
        if max_y_axis >= y_axis_len:
            self.hcoptions['yAxis']\
              .extend([HCOptions({})]*(max_y_axis+1-y_axis_len))
        for i, y_axis in enumerate(self.hcoptions['yAxis']):
            if not y_axis['title']['text']:
                axis_title = set(t[0] for t in term_y_axis if t[1] == i)
                y_axis['title']['text'] = ' & '.join(axis_title)
        if max_y_axis == 1:
            if self.hcoptions['yAxis'][1]['opposite'] != False:
                self.hcoptions['yAxis'][1]['opposite'] = True
    
    def generate_plot(self):
        # reset the series
        self.hcoptions['series'] = []
        dss = self.datasource.series
        # find all x's from different datasources that need to be plotted on 
        # same xAxis and also find their corresponding y's
        cht_typ_grp = lambda y_term: ('scatter' if 
                                      self.series_options[y_term]['type'] 
                                      in ['scatter', 'pie'] else 'line')
        for x_axis_num, vqs_groups in self.x_axis_vqs_groups.items():
            y_hco_list = []
            try:
                x_sortf, x_mapf, x_mts = self.x_sortf_mapf_mts[x_axis_num]
            except IndexError:
                x_sortf, x_mapf, x_mts = (None, None, False)
            ptype_x_y_terms = defaultdict(list)
            for vqs_group in vqs_groups.values(): 
                x_term, y_terms_all = vqs_group.items()[0]
                y_terms_by_type = defaultdict(list)
                for y_term in y_terms_all:
                    y_terms_by_type[cht_typ_grp(y_term)].append(y_term)
                for y_type, y_term_list in y_terms_by_type.items():
                    ptype_x_y_terms[y_type].append((x_term, y_term_list))
            
            # ptype = plot type i.e. 'line', 'scatter', 'area', etc. 
            for ptype, x_y_terms_tuples in ptype_x_y_terms.items():
                y_fields_multi = []
                y_aliases_multi = []
                y_types_multi = []
                y_hco_list_multi = []
                y_values_multi = SortedDict()
                y_terms_multi = []
                for x_term, y_terms in x_y_terms_tuples:
                    # x related
                    x_vqs = dss[x_term]['_data']
                    x_field = dss[x_term]['field']
                    # y related 
                    y_fields = [dss[y_term]['field'] for y_term in y_terms]
                    y_aliases = [dss[y_term]['field_alias'] for y_term 
                                 in y_terms]
                    y_types = [self.series_options[y_term].get('type','line') 
                               for y_term in y_terms]
                    y_hco_list = [HCOptions(
                                    copy.deepcopy(
                                        self.series_options[y_term])) for 
                                  y_term in y_terms]
                    for opts, alias, typ in zip(y_hco_list,y_aliases,y_types):
                        opts.pop('_x_axis_term')
                        opts['name'] = alias
                        opts['type'] = typ
                        opts['data'] = []
                    
                    if ptype == 'scatter' or (ptype == 'line' and 
                                              len(x_y_terms_tuples) == 1):
                        if x_mts:
                            if x_mapf: 
                                data = ((x_mapf(value_dict[x_field]), 
                                         [value_dict[y_field] for y_field 
                                          in y_fields]) 
                                        for value_dict in x_vqs)
                                sort_key = ((lambda(x, y): x_sortf(x)) 
                                            if x_sortf is not None else None)
                                data = sorted(data, key=sort_key)
                        else:
                            sort_key = ((lambda(x, y): x_sortf(x)) 
                                            if x_sortf is not None else None)
                            data = sorted(
                                    ((value_dict[x_field], 
                                     [value_dict[y_field] for y_field in 
                                      y_fields]) 
                                     for value_dict in x_vqs), 
                                    key=sort_key)
                            if x_mapf:
                                data = [(x_mapf(x), y) for (x, y) in data]
                            
                        if ptype == 'scatter':
                            if self.series_options[y_term]['type']=='scatter':
                                #scatter plot
                                for x_value, y_value_tuple in data:
                                    for opts, y_value in izip(y_hco_list,
                                                              y_value_tuple):
                                        opts['data'].append((x_value, y_value))
                                self.hcoptions['series'].extend(y_hco_list)
                            else:
                                # pie chart
                                for x_value, y_value_tuple in data:
                                    for opts, y_value in izip(y_hco_list,
                                                              y_value_tuple):
                                        opts['data'].append((str(x_value), 
                                                             y_value))
                                self.hcoptions['series'].extend(y_hco_list)
                            
                        if ptype == 'line' and len(x_y_terms_tuples) == 1:
                            # all other chart types - line, area, etc.
                            hco_x_axis = self.hcoptions['xAxis']
                            if len(hco_x_axis) - 1 < x_axis_num:
                                    hco_x_axis.extend([HCOptions({})]*
                                                      (x_axis_num - 
                                                       (len(hco_x_axis) - 
                                                        1)))
                            hco_x_axis[x_axis_num]['categories'] = []
                            for x_value, y_value_tuple in data:
                                hco_x_axis[x_axis_num]['categories']\
                                  .append(x_value)
                                for opts, y_value in izip(y_hco_list, 
                                                          y_value_tuple):
                                    opts['data'].append(y_value)
                            self.hcoptions['series'].extend(y_hco_list)
                    else:
                        data = ((value_dict[x_field],
                                 [value_dict[y_field] for y_field in 
                                  y_fields])
                                for value_dict in x_vqs)
                        
                        y_terms_multi.extend(y_terms)
                        y_fields_multi.extend(y_fields)
                        y_aliases_multi.extend(y_aliases)
                        y_types_multi.extend(y_types)
                        y_hco_list_multi.extend(y_hco_list)
                        
                        len_y_terms_multi = len(y_terms_multi)
                        ext_len = len(y_terms_multi) - len(y_terms)
                        for x_value, y_value_tuple in data:
                            try: 
                                cur_y = y_values_multi[x_value]
                                cur_y.extend(y_value_tuple)
                            except KeyError:
                                y_values_multi[x_value] = [None]*ext_len
                                y_values_multi[x_value]\
                                  .extend(y_value_tuple)
                        for _y_vals in y_values_multi.values():
                            if len(_y_vals) != len_y_terms_multi:
                                _y_vals.extend([None]*len(y_terms))
                if y_terms_multi:
                    hco_x_axis = self.hcoptions['xAxis']
                    if len(hco_x_axis) - 1 < x_axis_num:
                            hco_x_axis\
                              .extend([HCOptions({})]*
                                      (x_axis_num - (len(hco_x_axis)-1)))
                    hco_x_axis[x_axis_num]['categories'] = []
                    
                    if x_mts:
                        if x_mapf: 
                            data = ((x_mapf(x_value), y_vals) for 
                                    (x_value, y_vals) in 
                                    y_values_multi.iteritems())
                            sort_key = ((lambda(x, y): x_sortf(x)) if x_sortf 
                                        is not None else None)
                            data = sorted(data, key=sort_key)
                    else:
                        data = y_values_multi.iteritems()
                        sort_key = ((lambda(x, y): x_sortf(x)) if x_sortf 
                                    is not None else None)
                        data = sorted(data, key=sort_key)
                        if x_mapf:
                            data = [(x_mapf(x), y) for (x, y) in data]
                    
                    for x_value, y_vals in data:
                        hco_x_axis[x_axis_num]['categories']\
                          .append(x_value)
                        for opts, y_value in izip(y_hco_list_multi, y_vals):
                            opts['data'].append(y_value)
                    self.hcoptions['series'].extend(y_hco_list_multi)
                    
                    
class PivotChart(object):
    
    def __init__(self, datasource, series_options, chart_options=None):
        """Creates the PivotChart object. 
        
        **Arguments**:
        
        - **datasource** (**required**) - a ``PivotDataPool`` object that 
          holds the terms and other information to plot the chart from.
          
        - **series_options** (**required**) - specifies the options to plot 
          the terms on the chart. It is of the form ::
            [{'options': {
                #any items from HighChart series. For ex.
                'type': 'column'
                },
              'terms': [
                'a_valid_term',
                'other_valid_term': {
                  #any options to override. For ex.
                 'type': 'area',
                  ...
                  },
                ...
                ]
              },
              ... #repeat dicts with 'options' & 'terms'
              ]

          Where - 
          
          - **options** (**required**) - a ``dict``. Any of the parameters 
            from the `Highcharts options object - series array 
            <http://www.highcharts.com/ref/#series>`_ are valid as entries in 
            the ``options`` dict except ``data`` (because data array is 
            generated from your datasource by chartit). For example, ``type``, 
            ``xAxis``, etc. are all valid entries here. 
            
            .. note:: The items supplied in the options dict are not validated 
               to make sure that Highcharts actually supports them. Any 
               invalid options are just passed to Highcharts JS which silently 
               ignores them.
               
          - **terms** (**required**) - a ``list``. Only terms that are present 
            in the corresponding datasource are valid. 
            
            .. note:: All the ``terms`` are plotted on the ``y-axis``. The 
              **categories of the datasource are plotted on the x-axis. There 
              is no option to override this.**
             
            Each of the ``terms`` must either be a ``str`` or a ``dict``. If 
            entries are dicts, the keys need to be valid terms and the values 
            need to be any options to override the default options. For 
            example, ::
            
              [{'options': {
                  'type': 'column',
                  'yAxis': 0},
                'terms': [
                  'temperature',
                  {'rainfall': {
                      'type': 'line',
                      'yAxis': 1}}]}]
            
            plots a pivot column chart of temperature on yAxis: 0 and a line 
            pivot chart of rainfall on yAxis: 1. This can alternatively be 
            expressed as two separate entries: ::
            
              [{'options': {
                  'type': 'column',
                  'yAxis': 0},
                'terms': [
                    'temperature']},
               {'options': {
                  'type': 'line',
                  'yAxis': 1},
                'terms': [
                    'rainfall']}]
                    
        - **chart_options** (*optional*) - a ``dict``. Any of the options from 
          the `Highcharts options object <http://www.highcharts.com/ref/>`_ 
          are valid (except the options in the ``series`` array which are 
          passed in the ``series_options`` argument. The following 
          ``chart_options`` for example, set the chart title and the axes 
          titles. :: 
          
              {'chart': {
                 'title': { 
                   'text': 'Weather Chart'}},
               'xAxis': {
                 'title': 'month'},
               'yAxis': {
                 'title': 'temperature'}}
                 
          .. note:: The items supplied in the ``chart_options`` dict are not 
             validated to make sure that Highcharts actually supports them. 
             Any invalid options are just passed to Highcharts JS which 
             silently ignores them.
             
        **Raises**: 
        
        - ``APIInputError`` if any of the terms are not present in the 
          corresponding datasource or if the ``series_options`` cannot be 
          parsed.
        """
        self.user_input = locals()
        if not isinstance(datasource, PivotDataPool):
            raise APIInputError("%s must be an instance of PivotDataPool." 
                                %datasource)
        self.datasource = datasource
        self.series_options = clean_pcso(series_options, self.datasource)
        if chart_options is None:
            chart_options = HCOptions({})
        self.set_default_hcoptions()
        self.hcoptions.update(chart_options)
        # Now generate the plot
        self.generate_plot()
    
    def set_default_hcoptions(self):
        self.hcoptions = HCOptions({})
        # series and terms
        dss = self.datasource.series
        terms = self.series_options.keys()
        # legend by
        lgby_dict = dict(((t, dss[t]['legend_by']) for t in terms))
        lgby_vname_lists= [[dss[t]['field_aliases'].get(lgby, lgby) 
                            for lgby in lgby_tuple]
                           for (t, lgby_tuple) in lgby_dict.items()]
        lgby_titles = (':'.join(lgby_vname_list).title() for 
                       lgby_vname_list in lgby_vname_lists) 
        # chart title
        term_titles = (t.title() for t in terms)
        title = ''
        for t, lg in zip(term_titles, lgby_titles):
            if not lg:
                title += "%s, " % t
            else:
                title += "%s (lgnd. by %s), "  %(t, lg)
        categories = dss[terms[0]]['categories']
        categories_vnames = [dss[terms[0]]['field_aliases'][c].title() 
                             for c in categories]
        category_title = ':'.join(categories_vnames)
        chart_title = "%s vs. %s" % (title[:-2], category_title)
        self.hcoptions['title']['text'] = chart_title    
        
    def generate_plot(self):
        cv_raw = self.datasource.cv_raw
        hco_series = []
        for term, options in self.series_options.items():
            dss = self.datasource.series
            for lv in dss[term]['_lv_set']:
                data = [dss[term]['_cv_lv_dfv'][cv].get(lv, None) for cv 
                        in cv_raw]
                #name = '-'.join(dstd['legend_by']) + ":" + "-".join(lv)
                term_pretty_name = term.replace('_', ' ')
                name = term_pretty_name.title() if not lv else "-".join(lv) 
                hco = copy.deepcopy(options)
                hco['data'] = data
                hco['name'] = name
                hco_series.append(hco)
        self.hcoptions['series'] = hco_series
        self.hcoptions['xAxis']['categories'] = [':'.join(cv) for cv in 
                                                 self.datasource.cv]


########NEW FILE########
__FILENAME__ = exceptions
"""Global ChartIt exception and warning classes."""

class APIInputError(Exception):
    """Some kind of problem when validating the user input."""
    pass 

########NEW FILE########
__FILENAME__ = hcoptions
from ..utils import RecursiveDefaultDict

__all__ = ('HCOptions', )

class HCOptions(RecursiveDefaultDict):
    """The HighCharts options class."""
    pass

########NEW FILE########
__FILENAME__ = models
# Nothing here. But don't delete. 
# This file is needed to make this folder a django app!
########NEW FILE########
__FILENAME__ = chartit
from itertools import izip_longest

from django import template
from django.utils import simplejson
from django.utils.safestring import mark_safe
from django.conf import settings
import posixpath

from ..charts import Chart, PivotChart

try:
    CHARTIT_JS_REL_PATH = settings.CHARTIT_JS_REL_PATH
    if CHARTIT_JS_REL_PATH[0] == '/':
        CHARTIT_JS_REL_PATH = CHARTIT_JS_REL_PATH[1:]
    CHART_LOADER_URL = posixpath.join(settings.STATIC_URL, 
                                      CHARTIT_JS_REL_PATH,
                                      'chartloader.js')
except AttributeError:
    CHARTIT_JS_REL_PATH = 'chartit/js/'
    CHART_LOADER_URL = posixpath.join(settings.STATIC_URL, 
                                      CHARTIT_JS_REL_PATH,
                                      'chartloader.js')

register = template.Library()

@register.filter
def load_charts(chart_list=None, render_to=''):
    """Loads the ``Chart``/``PivotChart`` objects in the ``chart_list`` to the 
    HTML elements with id's specified in ``render_to``. 
    
    :Arguments:
    
    - **chart_list** - a list of Chart/PivotChart objects. If there is just a 
      single element, the Chart/PivotChart object can be passed directly 
      instead of a list with a single element.
       
    - **render_to** - a comma separated string of HTML element id's where the 
      charts needs to be rendered to. If the element id of a specific chart 
      is already defined during the chart creation, the ``render_to`` for that 
      specific chart can be an empty string or a space.
      
      For example, ``render_to = 'container1, , container3'`` renders three 
      charts to three locations in the HTML page. The first one will be 
      rendered in the HTML element with id ``container1``, the second 
      one to it's default location that was specified in ``chart_options`` 
      when the Chart/PivotChart object was created, and the third one in the
      element with id ``container3``.
    
    :returns:
     
    - a JSON array of the HighCharts Chart options. Also returns a link
      to the ``chartloader.js`` javascript file to be embedded in the webpage. 
      The ``chartloader.js`` has a jQuery script that renders a HighChart for 
      each of the options in the JSON array"""
      
    embed_script = (
      '<script type="text/javascript">\n'
      'var _chartit_hco_array = %s;\n</script>\n'
      '<script src="%s" type="text/javascript">\n</script>')
    
    if chart_list is not None:
        if isinstance(chart_list, (Chart, PivotChart)):
            chart_list = [chart_list]
        chart_list = [c.hcoptions for c in chart_list]
        render_to_list = [s.strip() for s in render_to.split(',')]
        for hco, render_to in izip_longest(chart_list, render_to_list):
            if render_to:
                hco['chart']['renderTo'] = render_to
        embed_script = (embed_script % (simplejson.dumps(chart_list, 
                                                         use_decimal=True),
                                        CHART_LOADER_URL))
    else:
        embed_script = embed_script %((), CHART_LOADER_URL)
    return mark_safe(embed_script)
########NEW FILE########
__FILENAME__ = utils
from collections import defaultdict

def _convert_to_rdd(obj):
    """Accepts a dict or a list of dicts and converts it to a  
    RecursiveDefaultDict."""
    if isinstance(obj, dict):
        rdd = RecursiveDefaultDict()
        for k, v in obj.items():
            rdd[k] = _convert_to_rdd(v)
        return rdd
    elif isinstance(obj, list):
        rddlst = []
        for ob in obj:
            rddlst.append(_convert_to_rdd(ob))
        return rddlst
    else:
        return obj
           
class RecursiveDefaultDict(defaultdict):
    """The name says it all.
    """
    def __init__(self, data = None):
        self.default_factory = type(self)
        if data is not None:
            self.data = _convert_to_rdd(data)
            self.update(self.data)
            del self.data
            
    def __getitem__(self, key):
        return super(RecursiveDefaultDict, self).__getitem__(key)
    
    def __setitem__(self, key, item):
        if not isinstance(item, RecursiveDefaultDict):
            super(RecursiveDefaultDict, self).__setitem__(key, 
                                                        _convert_to_rdd(item))
        else:
            super(RecursiveDefaultDict, self).__setitem__(key, item)
    
    def update(self, element):
        super(RecursiveDefaultDict, self).update(_convert_to_rdd(element))
            
        
########NEW FILE########
__FILENAME__ = validation
import copy

from django.db.models.aggregates import Aggregate
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.db.models.query import QuerySet

from .exceptions import APIInputError


def _validate_field_lookup_term(model, term):
    """Checks whether the term is a valid field_lookup for the model.
    
    **Args**:
    - **model** (**required**) - a django model for which to check whether 
      the term is a valid field_lookup.
    - **term** (**required**) - the term to check whether it is a valid 
      field lookup for the model supplied.
            
    **Returns**:
    -  The verbose name of the field if the supplied term is a valid field.
    
    **Raises**:
    - APIInputError: If the term supplied is not a valid field lookup 
      parameter for the model.
    """
    # TODO: Memoization for speed enchancements?
    terms = term.split('__')
    model_fields = model._meta.get_all_field_names()
    if terms[0] not in model_fields:
        raise APIInputError("Field %r does not exist. Valid lookups are %s." 
                         % (terms[0], ', '.join(model_fields)))
    if len(terms) == 1:
        return model._meta.get_field(terms[0]).verbose_name
    else:
        # DocString details for model._meta.get_field_by_name  
        # 
        # Returns a tuple (field_object, model, direct, m2m), where 
        #     field_object is the Field instance for the given name, 
        #     model is the model containing this field (None for 
        #         local fields), 
        #     direct is True if the field exists on this model, 
        #     and m2m is True for many-to-many relations. 
        # When 'direct' is False, 'field_object' is the corresponding 
        # RelatedObject for this field (since the field doesn't have 
        # an instance associated with it).
        field_details = model._meta.get_field_by_name(terms[0])
        # if the field is direct field
        if field_details[2]:
            m = field_details[0].related.parent_model
        else:
            m = field_details[0].model
        
        return _validate_field_lookup_term(m, '__'.join(terms[1:]))

def _clean_source(source):
    if isinstance(source, ModelBase):
        return source._base_manager.all()
    elif isinstance(source, Manager):
        return source.all()
    elif isinstance(source, QuerySet):
        return source
    raise APIInputError("'source' must either be a QuerySet, Model or "
                        "Manager. Got %s of type %s instead."  
                        %(source, type(source)))

def _validate_func(func):
    if not isinstance(func, Aggregate):
        raise APIInputError("'func' must an instance of django Aggregate. "
                            "Got %s of type %s instead" % (func, type(func)))

def _clean_categories(categories, source):
    if isinstance(categories, basestring):
        categories = [categories]
    elif isinstance(categories, (tuple, list)):
        if not categories:
            raise APIInputError("'categories' tuple or list must contain at " 
                                "least one valid model field. Got %s." 
                                %categories)
    else:
        raise APIInputError("'categories' must be one of the following "
                            "types: basestring, tuple or list. Got %s of "
                            "type %s instead."
                            %(categories, type(categories)))
    field_aliases = {}
    for c in categories:
        field_aliases[c] = _validate_field_lookup_term(source.model, c)
    return categories, field_aliases

def _clean_legend_by(legend_by, source):
    if isinstance(legend_by, basestring):
        legend_by = [legend_by]
    elif isinstance(legend_by, (tuple, list)):
        pass
    elif legend_by is None:
        legend_by = ()
    else:
        raise APIInputError("'legend_by' must be one of the following "
                            "types: basestring, tuple or list. Got %s of "
                            "type %s instead."
                            %(legend_by, type(legend_by)))
    field_aliases = {}
    for lg in legend_by:
        field_aliases[lg] = _validate_field_lookup_term(source.model, lg)
    return legend_by, field_aliases

def _validate_top_n_per_cat(top_n_per_cat):
    if not isinstance(top_n_per_cat,  int):
        raise APIInputError("'top_n_per_cat' must be an int. Got %s of type "
                            "%s instead." 
                            %(top_n_per_cat, type(top_n_per_cat)))

def _clean_field_aliases(fa_actual, fa_cat, fa_lgby):
    fa = copy.copy(fa_lgby)
    fa.update(fa_cat)
    fa.update(fa_actual)
    return fa

def _convert_pdps_to_dict(series_list):
    series_dict = {}
    for sd in series_list:
        try:
            options = sd['options']
        except KeyError:
            raise APIInputError("%s is missing the 'options' key." %sd)
        if not isinstance(options, dict):
            raise APIInputError("Expecting a dict in place of: %s" %options)
        
        try:
            terms = sd['terms']
        except KeyError:
            raise APIInputError("%s is missing have the 'terms' key." %sd)
        if isinstance(terms, dict):
            if not terms:
                raise APIInputError("'terms' cannot be empty.")
            for tk, tv in terms.items():
                if isinstance(tv, Aggregate):
                    tv = {'func': tv}
                elif isinstance(tv, dict):
                    pass
                else:
                    raise APIInputError("Expecting a dict or django Aggregate "
                                        "in place of: %s" %tv)
                opts = copy.deepcopy(options)
                opts.update(tv)
                series_dict.update({tk: opts})
        else:
            raise APIInputError("Expecting a dict in place of: %s" 
                                %terms)
    return series_dict

            
def clean_pdps(series):
    """Clean the PivotDataPool series input from the user.
    """
    if isinstance(series, list):
        series = _convert_pdps_to_dict(series)
        clean_pdps(series)
    elif isinstance(series, dict):
        if not series:
            raise APIInputError("'series' cannot be empty.")
        for td in series.values():
            # td is not a dict
            if not isinstance(td, dict):
                raise APIInputError("Expecting a dict in place of: %s" %td)
            # source
            try:
                td['source'] = _clean_source(td['source'])
            except KeyError:
                raise APIInputError("Missing 'source': %s" % td)
            # func
            try:
                _validate_func(td['func'])
            except KeyError:
                raise APIInputError("Missing 'func': %s" % td)
            # categories
            try:
                td['categories'], fa_cat = _clean_categories(td['categories'],
                                                            td['source'])
            except KeyError:
                raise APIInputError("Missing 'categories': %s" % td)
            # legend_by
            try:
                td['legend_by'], fa_lgby = _clean_legend_by(td['legend_by'],
                                                           td['source'])
            except KeyError:
                td['legend_by'], fa_lgby = (), {}
            # top_n_per_cat
            try:
                _validate_top_n_per_cat(td['top_n_per_cat'])
            except KeyError:
                td['top_n_per_cat'] = 0
            # field_aliases
            try:
                fa_actual = td['field_aliases']
            except KeyError:
                td['field_aliases'] = fa_actual = {}
            td['field_aliases'] = _clean_field_aliases(fa_actual, 
                                                       fa_cat, 
                                                       fa_lgby)
    else:
        raise APIInputError("Expecting a dict or list in place of: %s" %series)
    return series

def _convert_dps_to_dict(series_list):
    series_list = copy.deepcopy(series_list)
    series_dict = {}
    if not series_list:
        raise APIInputError("'series' cannot be empty.")
    for sd in series_list:
        try:
            options = sd['options']
        except KeyError:
            raise APIInputError("%s is missing the 'options' key." %sd)
        if not isinstance(options, dict):
            raise APIInputError("Expecting a dict in place of: %s" %options)
        
        try:
            terms = sd['terms']
        except KeyError:
            raise APIInputError("%s is missing the 'terms' key." %sd)
        if isinstance(terms, list):
            for term in terms:
                if isinstance(term, basestring):
                    series_dict[term] = copy.deepcopy(options)
                elif isinstance(term, dict):
                    for tk, tv in term.items():
                        if isinstance(tv, basestring):
                            opts = copy.deepcopy(options)
                            opts['field'] = tv
                            series_dict[tk] = opts
                        elif isinstance(tv, dict):
                            opts = copy.deepcopy(options)
                            opts.update(tv)
                            series_dict[tk] = opts 
                        else:
                            raise APIInputError("Expecting a basestring or "
                                                "dict in place of: %s" %tv)
        elif isinstance(terms, dict):
            for tk, tv in terms.items():
                if isinstance(tv, basestring):
                    opts = copy.deepcopy(options)
                    opts['field'] = tv
                    series_dict[tk] = opts
                elif isinstance(tv, dict):
                    opts = copy.deepcopy(options)
                    opts.update(tv)
                    series_dict[tk] = opts 
                else:
                    raise APIInputError("Expecting a basestring or dict in "
                                        "place of: %s" %tv)
        else:
            raise APIInputError("Expecting a list or dict in place of: %s." 
                                %terms)
    return series_dict

def clean_dps(series):
    """Clean the DataPool series input from the user.
    """
    if isinstance(series, dict):
        if not series:
            raise APIInputError("'series' cannot be empty.")
        for tk, td in series.items():
            try:
                td['source'] = _clean_source(td['source'])
            except KeyError:
                raise APIInputError("%s is missing the 'source' key." %td)
            td.setdefault('field', tk)
            fa = _validate_field_lookup_term(td['source'].model, td['field'])\
                   .title()
            # If the user supplied term is not a field name, use it as an alias
            if tk != td['field']:
                fa = tk 
            td.setdefault('field_alias', fa)
    elif isinstance(series, list):
        series = _convert_dps_to_dict(series)
        clean_dps(series)
    else:
        raise APIInputError("Expecting a dict or list in place of: %s" %series)
    return series

def _convert_pcso_to_dict(series_options):
    series_options_dict = {}
    for stod in series_options:
        try:
            options = stod['options']
        except KeyError:
            raise APIInputError("%s is missing the 'options' key." %stod)
        if not isinstance(options, dict):
            raise APIInputError("Expecting a dict in place of: %s" %options)
        
        try:
            terms = stod['terms']
        except KeyError:
            raise APIInputError("%s is missing the 'terms' key." %stod)
        if isinstance(terms, list):
            for term in terms:
                if isinstance(term, basestring):
                    opts = copy.deepcopy(options)
                    series_options_dict.update({term: opts})
                elif isinstance(term, dict):
                    for tk, tv in term.items():
                        if not isinstance(tv, dict):
                            raise APIInputError("Expecting a dict in place "
                                                "of: %s" %tv)
                        opts = copy.deepcopy(options)
                        opts.update(tv)
                        series_options_dict.update({tk: opts})
        else:
            raise APIInputError("Expecting a list in place of: %s" %terms)
    return series_options_dict


def clean_pcso(series_options, ds):
    """Clean the PivotChart series_options input from the user.
    """
    #todlist = term option dict list
    if isinstance(series_options, dict):
        for sok, sod in series_options.items():
            if sok not in ds.series.keys():
                    raise APIInputError("All the series terms must be present "
                                        "in the series dict of the "
                                        "datasource. Got %s. Allowed values "
                                        "are: %s" 
                                        %(sok, ', '.join(ds.series.keys())))
            if not isinstance(sod, dict):
                raise APIInputError("All the series options must be of the "
                                    "type dict. Got %s of type %s instead." 
                                    %(sod, type(sod)))
    elif isinstance(series_options, list):
        series_options = _convert_pcso_to_dict(series_options)
        clean_pcso(series_options, ds)
    else:
        raise APIInputError("Expecting a dict or list in place of: %s." 
                            %series_options)
    return series_options

def _convert_cso_to_dict(series_options):
    series_options_dict = {}
    #stod: series term and option dict
    for stod in series_options:
        try:
            options = stod['options']
        except KeyError:
            raise APIInputError("%s is missing the 'options' key." %stod)
        if not isinstance(options, dict):
            raise APIInputError("Expecting a dict in place of: %s" %options)
        
        try:
            terms = stod['terms']
        except KeyError:
            raise APIInputError("%s is missing the 'terms' key." %stod)
        
        if isinstance(terms, dict):
            if not terms:
                raise APIInputError("'terms' dict cannot be empty.")
            for tk, td in terms.items():
                if isinstance(td, list):
                    for yterm in td:
                        if isinstance(yterm, basestring):
                            opts = copy.deepcopy(options)
                            opts['_x_axis_term'] = tk
                            series_options_dict[yterm] = opts
                        elif isinstance(yterm, dict):
                            opts = copy.deepcopy(options)
                            opts.update(yterm.values()[0])
                            opts['_x_axis_term'] = tk
                            series_options_dict[yterm.keys()[0]] = opts
                        else:
                            raise APIInputError("Expecting a basestring or "
                                                "dict in place of: %s." %yterm)
                else:
                    raise APIInputError("Expecting a list instead of: %s"
                                        %td)
        else:
            raise APIInputError("Expecting a dict in place of: %s." 
                                %terms)
    return series_options_dict
                    
def clean_cso(series_options, ds):
    """Clean the Chart series_options input from the user.
    """
    if isinstance(series_options, dict):
        for sok, sod in series_options.items():
            if sok not in ds.series.keys():
                    raise APIInputError("%s is not one of the keys of the "
                                        "datasource series. Allowed values "
                                        "are: %s" 
                                        %(sok, ', '.join(ds.series.keys())))
            if not isinstance(sod, dict):
                raise APIInputError("%s is of type: %s. Expecting a dict." 
                                    %(sod, type(sod)))
            try:
                _x_axis_term = sod['_x_axis_term']
                if _x_axis_term not in ds.series.keys():
                    raise APIInputError("%s is not one of the keys of the "
                                        "datasource series. Allowed values "
                                        "are: %s" 
                                        %(_x_axis_term, 
                                          ', '.join(ds.series.keys())))
            except KeyError:
                raise APIInputError("Expecting a '_x_axis_term' for %s." %sod)
            if ds.series[sok]['_data'] != ds.series[_x_axis_term]['_data']:
                raise APIInputError("%s and %s do not belong to the same "
                                    "table." %(sok, _x_axis_term))
                sod['_data'] = ds.series[sok]['_data']
    elif isinstance(series_options, list):
        series_options = _convert_cso_to_dict(series_options)
        clean_cso(series_options, ds)
    else:
        raise APIInputError("'series_options' must either be a dict or a "
                            "list. Got %s of type %s instead." 
                            %(series_options, type(series_options)))
    return series_options

def clean_sortf_mapf_mts(sortf_mapf_mts):
    if sortf_mapf_mts is None:
        sortf_mapf_mts = (None, None, False)
    if isinstance(sortf_mapf_mts, tuple):
        if len(sortf_mapf_mts) != 3:
            raise APIInputError("%r must have exactly three elements."
                                %sortf_mapf_mts)
        sortf, mapf, mts = sortf_mapf_mts
        if not callable(sortf) and sortf is not None:
            raise APIInputError("%r must be callable or None." %sortf)
        if not callable(mapf) and mapf is not None:
            raise APIInputError("%r must be callable or None." %mapf)
        mts = bool(mts)
    return (sortf, mapf, mts)

def clean_x_sortf_mapf_mts(x_sortf_mapf_mts):
    cleaned_x_s_m_mts = []
    if x_sortf_mapf_mts is None:
        x_sortf_mapf_mts = [(None, None, False)]
    if isinstance(x_sortf_mapf_mts, tuple):
        x_sortf_mapf_mts = [x_sortf_mapf_mts]
    for x_s_m_mts in x_sortf_mapf_mts:
        if not isinstance(x_s_m_mts, tuple):
            raise APIInputError("%r must be a tuple." %x_s_m_mts)
        if len(x_s_m_mts) != 3:
            raise APIInputError("%r must have exactly three elements."
                                %x_s_m_mts)
        x_sortf = x_s_m_mts[0]
        if not callable(x_sortf) and x_sortf is not None:
            raise APIInputError("%r must be callable or None." %x_sortf)
        x_mapf = x_s_m_mts[1]
        if not callable(x_mapf) and x_mapf is not None:
            raise APIInputError("%r must be callable or None." %x_mapf)
        x_mts = bool(x_s_m_mts[2])
        cleaned_x_s_m_mts.append((x_sortf, x_mapf, x_mts))
    return cleaned_x_s_m_mts

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG

CHARTIT_DIR = os.path.split(os.path.dirname(__file__))[0]
sys.path = [CHARTIT_DIR] + sys.path

PROJECT_ROOT = os.path.dirname(__file__)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'staticfiles'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'templates')
)

INSTALLED_APPS = (
#    'django.contrib.auth',
#    'django.contrib.contenttypes',
#    'django.contrib.sessions',
#    'django.contrib.sites',
#    'django.contrib.messages',
    'django.contrib.staticfiles',
    'chartit',
    'validation'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


# All production settings like sensitive passwords go here.
# Remember to exclude this file from version control
try:
    from prod_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Author(models.Model):
    
    first_name = models.CharField(max_length=50, db_column='first_name')
    last_name = models.CharField(max_length=50, db_column='last_name')
    
    def __unicode__(self):
        return '%s %s' %(self.first_name, self.last_name)
    
    class Meta:
        db_table = 'author'


class Publisher(models.Model):
    
    name = models.CharField(max_length=50, db_column='name')
    
    def __unicode__(self):
        return '%s' %(self.name)
    
    class Meta:
        db_table = 'publisher'


class Genre(models.Model):
    
    name = models.CharField(max_length=50, db_column='name')
    
    def __unicode__(self):
        return '%s' %(self.name)
    
    class Meta:
        db_table = 'genre'
        
    
class Book(models.Model):
    
    title = models.CharField(max_length=50, db_column='title')
    rating = models.FloatField(db_column='rating')
    rating_count = models.IntegerField(db_column='rating_count')
    authors = models.ManyToManyField(Author, db_column='authors')
    publisher = models.ForeignKey(Publisher, db_column='publisher', null=True, blank=True, 
                                  on_delete=models.SET_NULL)
    related = models.ManyToManyField('self', db_column='related', blank=True)
    genre = models.ForeignKey(Genre, db_column='genre', null=True, blank=True, 
                                     on_delete=models.SET_NULL)
    
    def __unicode__(self):
        return '%s' %(self.title)
    
    class Meta:
        db_table = 'book'
    
class BookStore(models.Model):
    
    name =  models.CharField(max_length=50, db_column='name')
    city = models.ForeignKey('City')
    
    def __unicode__(self):
        return '%s' %(self.name)
    
    class Meta:
        db_table = 'bookstore'
    
class SalesHistory(models.Model):
    
    bookstore = models.ForeignKey(BookStore, db_column='bookstore')
    book = models.ForeignKey(Book, db_column='book')
    sale_date = models.DateField(db_column='sale_date')
    sale_qty = models.IntegerField(db_column='sale_qty')
    price = models.DecimalField(max_digits=5, decimal_places=2, db_column='price')
    
    def __unicode__(self):
        return '%s %s %s' %(self.bookstore, self.book, self.sale_date)
    
    class Meta:
        db_table = 'saleshistory'

class City(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    city = models.CharField(max_length=50, db_column='city')
    state = models.CharField(max_length=2, db_column='state')
    
    def __unicode__(self):
        return '%s, %s' %(self.city, self.state)
    def region(self):
        return 'USA'
    
    class Meta:
        db_table = 'city'

class DailyWeather(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    month = models.IntegerField(db_column='month')
    day = models.IntegerField(db_column='day')
    temperature = models.DecimalField(max_digits=5, decimal_places=1,
                                      db_column='temperature')
    city = models.CharField(max_length=50, db_column='city')
    state = models.CharField(max_length=2, db_column='state')
    
    class Meta:
        db_table = 'daily_weather'
        
class MonthlyWeatherByCity(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    month = models.IntegerField()
    boston_temp = models.DecimalField(max_digits=5, decimal_places=1, 
                                      db_column='boston_temp')
    houston_temp = models.DecimalField(max_digits=5, decimal_places=1, 
                                       db_column='houston_temp')
    new_york_temp = models.DecimalField(max_digits=5, decimal_places=1, 
                                        db_column='new_york_temp')
    san_francisco_temp = models.DecimalField(max_digits=5, decimal_places=1, 
                                            db_column='san_franciso_temp')
    
    class Meta:
        db_table = 'monthly_weather_by_city'
    
class MonthlyWeatherSeattle(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    month = models.IntegerField()
    seattle_temp = models.DecimalField(max_digits=5, decimal_places=1,
                                       db_column='seattle_temp')
    
    class Meta:
        db_table = 'monthly_weather_seattle'
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.db.models import Avg

from chartit import PivotDataPool, DataPool
from chartit.validation import (clean_pdps, clean_dps,
                                clean_pcso, clean_cso)
from chartit.exceptions import APIInputError

from .models import SalesHistory, MonthlyWeatherByCity, MonthlyWeatherSeattle
from .utils import assertOptionDictsEqual

TestCase.assertOptionDictsEqual = assertOptionDictsEqual

class GoodPivotSeriesDictInput(TestCase):
    
    def test_all_terms(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
    
    def test_categories_is_a_str(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': 'bookstore__city__state',
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'book__genre__name': 'name'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'book__genre__name': 'name'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
    
    def test_legend_by_is_a_str(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'legend_by': 'book__genre__name',
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
        
    def test_no_legend_by(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [
               'bookstore__city__state', 
               'bookstore__city__city'],
             'legend_by': (),
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                    series_cleaned)
        
    def test_no_top_n_per_cat(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 0,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
    
    def test_no_field_aliases(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5}}
        series_cleaned = \
          {'avg_price': { 
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state', 'bookstore__city__city'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 5,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'bookstore__city__city': 'city',
              'book__genre__name': 'name'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
        
    def test_custom_field_aliases(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'St',
               'bookstore__city__city': 'Cty',
               'book__genre__name': 'Genre'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'St',
               'bookstore__city__city': 'Cty',
               'book__genre__name': 'Genre'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned) 
        
    def test_partial_field_aliases(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'St'}}}
        series_cleaned = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'St',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
        

class BadPivotSeriesDictInput(TestCase):
    
    def test_series_not_dict_or_list(self):
        series_input = 'foobar'
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_func_dict_wrong_type(self):
        series_input = \
          {'avg_price': 'foobar'}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_source_missing(self):
        series_input = \
          {'avg_price': { 
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
    
    def test_source_wrong_type(self):
        series_input = \
          {'avg_price': { 
             'source': 'foobar',
             'func': Avg('price'),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_func_missing(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_func_wrong_type(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': 'foobar',
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_categories_missing(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_categories_wrong_type(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': 0,
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_categories_not_a_valid_field(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': ['foobar'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)

    def test_categories_empty_list(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': Avg('price'),
             'categories': [],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
                
    def test_legend_by_wrong_type(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': 'foobar',
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': 10,
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_legend_by_not_a_valid_field(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': 'foobar',
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['foobar'],
             'top_n_per_cat': 5,
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)    
    
    def test_top_n_per_cat_wrong_type(self):
        series_input = \
          {'avg_price': { 
             'source': SalesHistory.objects.all(),
             'func': 'foobar',
             'categories': ['bookstore__city__state', 'bookstore__city__city'],
             'legend_by': ['book__genre__name'],
             'top_n_per_cat': 'foobar',
             'field_aliases': {
               'bookstore__city__state': 'state',
               'bookstore__city__city': 'city',
               'book__genre__name': 'name'}}}
        self.assertRaises(APIInputError, clean_pdps, series_input)
    
class GoodPivotSeriesListInput(TestCase):  
    
    def test_all_terms(self):
                
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}},
           'avg_price_all': {
             'func': Avg('price'),
             'source': SalesHistory.objects.all(),
             'categories': ['bookstore__city__state'],
             'legend_by': (),
             'top_n_per_cat': 2,
             'field_aliases': {
               'bookstore__city__state': 'state'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)

    def test_source_a_manager(self):
                
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects,
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}},
           'avg_price_all': {
             'func': Avg('price'),
             'source': SalesHistory.objects.all(),
             'categories': ['bookstore__city__state'],
             'legend_by': (),
             'top_n_per_cat': 2,
             'field_aliases': {
               'bookstore__city__state': 'state'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
    
    def test_source_a_model(self):
                
        series_input = \
          [{'options': 
             {'source': SalesHistory,
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}},
           'avg_price_all': {
             'func': Avg('price'),
             'source': SalesHistory.objects.all(),
             'categories': ['bookstore__city__state'],
             'legend_by': (),
             'top_n_per_cat': 2,
             'field_aliases': {
               'bookstore__city__state': 'state'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
         
    def test_term_opts_an_aggr(self):
        
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': ['bookstore__city__state'],
              'legend_by': ['book__genre__name'],
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price')}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)


    def test_term_opts_a_dict(self):
        
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': {
                'func': Avg('price'),
                'top_n_per_cat':3}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 3,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
    
    def test_opts_empty(self):
        
        series_input = \
          [{'options': {},
            'terms': {
              'avg_price': {
                'source': SalesHistory.objects.all(),
                'categories': ['bookstore__city__state'],
                'func': Avg('price'),
                'top_n_per_cat':3}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': (),
            'top_n_per_cat': 3,
            'field_aliases': {
              'bookstore__city__state': 'state'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)

    def test_categories_a_str(self):
        
        series_input = \
          [{'options': {},
            'terms': {
              'avg_price': {
                'source': SalesHistory.objects.all(),
                'categories': 'bookstore__city__state',
                'func': Avg('price'),
                'top_n_per_cat':3}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': (),
            'top_n_per_cat': 3,
            'field_aliases': {
              'bookstore__city__state': 'state'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)

    def test_legend_by_a_str(self):
        
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': ['bookstore__city__state'],
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price')}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)

    def test_multiple_dicts(self):
                
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price')}},
           {'options': 
             {'source': SalesHistory.objects.filter(price__gte=10),
              'categories': 'bookstore__city__city',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price_high': {
                'func': Avg('price'),
                'legend_by': None}}}]

        series_cleaned = \
          {'avg_price': {
            'source': SalesHistory.objects.all(),
            'func': Avg('price'),
            'categories': ['bookstore__city__state'],
            'legend_by': ['book__genre__name'],
            'top_n_per_cat': 2,
            'field_aliases': {
              'bookstore__city__state': 'state',
              'book__genre__name': 'name'}},
           'avg_price_high': {
             'func': Avg('price'),
             'source': SalesHistory.objects.filter(price__gte=10),
             'categories': ['bookstore__city__city'],
             'legend_by': (),
             'top_n_per_cat': 2,
             'field_aliases': {
               'bookstore__city__city': 'city'}}}
        
        self.assertOptionDictsEqual(clean_pdps(series_input),
                                   series_cleaned)
        
class BadPivotSeriesListInput(TestCase):  
    
    def test_terms_empty(self):
                
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {}}]
          
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_terms_missing(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
    
    def test_terms_a_list_not_a_dict(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': [{
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}]}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_source_missing(self):
        series_input = \
          [{'options': 
             {'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
    
    def test_options_missing(self):
        series_input = \
          [{'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)  
    
    def test_options_empty(self):
        series_input = \
          [{'options': {},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)  
        
    def test_source_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': 'foobar',
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)  
    
    def test_categories_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 10,
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
    
    def test_categories_not_a_field(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'foobar',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_legend_by_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 10,
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)

    def test_legend_by_not_a_field(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'foobar',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_term_func_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': 'foobar',
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_term_dict_func_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': 'foobar',
                'legend_by': None}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
        
    def test_term_dict_legend_by_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__state',
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'avg_price': Avg('price'),
              'avg_price_all': {
                'func': Avg('price'),
                'legend_by': 10}}}]
        self.assertRaises(APIInputError, clean_pdps, series_input)
                    
class GoodDataSeriesListInput(TestCase):
    
    def test_all_terms(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': [
              'price', 
              {'genre': {
                 'field': 'book__genre__name',
                 'source': SalesHistory.objects.filter(price__gte=10),
                 'field_alias': 'gnr'}}]
            }]
        series_cleaned = \
          {'price': {
             'source': SalesHistory.objects.all(),
             'field': 'price',
             'field_alias': 'price'},
           'genre':{
             'source': SalesHistory.objects.filter(price__gte=10),
             'field': 'book__genre__name',
             'field_alias': 'gnr'}}
        self.assertOptionDictsEqual(clean_dps(series_input),
                                    series_cleaned)
    
    def test_terms_list_all_str(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': [
              'price', 
              'book__genre__name']
            }]
        series_cleaned = \
          {'price': {
             'source': SalesHistory.objects.all(),
             'field': 'price',
             'field_alias': 'price'},
           'book__genre__name':{
             'source': SalesHistory.objects.all(),
             'field': 'book__genre__name',
             'field_alias': 'name'}}
        self.assertOptionDictsEqual(clean_dps(series_input),
                                    series_cleaned)
    
    def test_terms_is_a_dict(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': {'price': {}}
            }]
        series_cleaned = \
          {'price': {
             'source': SalesHistory.objects.all(),
             'field': 'price',
             'field_alias': 'price'}}
        self.assertOptionDictsEqual(clean_dps(series_input),
                                    series_cleaned)
        
    def test_multiple_dicts(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': [
              'price']},
           {'options': 
             {'source': SalesHistory.objects.filter(price__gte=10)},
            'terms': 
              {'genre': {
                 'field': 'book__genre__name',
                 'field_alias': 'gnr'}}
            }]
        series_cleaned = \
          {'price': {
             'source': SalesHistory.objects.all(),
             'field': 'price',
             'field_alias': 'price'},
           'genre':{
             'source': SalesHistory.objects.filter(price__gte=10),
             'field': 'book__genre__name',
             'field_alias': 'gnr'}}
        self.assertOptionDictsEqual(clean_dps(series_input),
                                    series_cleaned)
        
class BadDataSeriesListInput(TestCase):
    def test_source_missing(self):
        series_input = \
          [{'options': {},
            'terms': [
              'price', 
              {'genre': {
                 'field': 'book__genre__name',
                 'source': SalesHistory.objects.filter(price__gte=10),
                 'field_alias': 'gnr'}}]
            }]
        self.assertRaises(APIInputError, clean_dps, series_input)
        
    def test_source_wrong_type(self):
        series_input = \
          [{'options': 
              {'source': 'foobar'},
            'terms': [
              'price', 
              {'genre': {
               'field': 'book__genre__name',
               'source': SalesHistory.objects.filter(price__gte=10),
               'field_alias': 'gnr'}}]
            }]
        self.assertRaises(APIInputError, clean_dps, series_input)
        
    def test_series_terms_empty(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': []
            }]
        self.assertRaises(APIInputError, clean_dps, series_input)

    def test_series_terms_wrong_type(self):
        series_input = \
          [{'options': 
             {'source': SalesHistory.objects.all()},
            'terms': 'foobar'
            }]
        self.assertRaises(APIInputError, clean_dps, series_input)
        
    def test_terms_element_wrong_type(self):
        series_input = \
          [{'options': 
              {'source': SalesHistory.objects.all()},
            'terms': [10]}]
        self.assertRaises(APIInputError, clean_dps, series_input)
        
    def test_terms_element_not_a_field(self):
        series_input = \
          [{'options': 
              {'source': SalesHistory.objects.all()},
            'terms': [
              'foobar', 
              {'genre': {
               'field': 'book__genre__name',
               'source': SalesHistory.objects.filter(price__gte=10),
               'field_alias': 'gnr'}}]
            }]
        self.assertRaises(APIInputError, clean_dps, series_input)

class GoodPivotChartOptions(TestCase):
    series_input = \
      [{'options': 
         {'source': SalesHistory.objects.all(),
          'categories': 'bookstore__city__state',
          'legend_by': 'book__genre__name',
          'top_n_per_cat': 2},
        'terms': {
          'avg_price': Avg('price'),
          'avg_price_all': {
            'func': Avg('price'),
            'legend_by': None}}}]
    ds = PivotDataPool(series_input)
    
    def test_all_terms(self):
        pcso_input = \
          [{'options': {
              'type': 'column'},
            'terms':[
              'avg_price',
              {'avg_price_all':{
                 'type': 'area'}}]}
           ]
        series_cleaned = \
          {'avg_price': {
              'type': 'column'},
           'avg_price_all': {
              'type': 'area'}}
        self.assertOptionDictsEqual(clean_pcso(pcso_input, self.ds),
                                    series_cleaned)
    

class BadPivotChartOptions(TestCase):
    series_input = \
      [{'options': 
         {'source': SalesHistory.objects.all(),
          'categories': 'bookstore__city__state',
          'legend_by': 'book__genre__name',
          'top_n_per_cat': 2},
        'terms': {
          'avg_price': Avg('price'),
          'avg_price_all': {
            'func': Avg('price'),
            'legend_by': None}}}]
    ds = PivotDataPool(series_input)
    
    def test_term_not_in_pdps(self):
        pcso_input = \
          [{'options': {
              'type': 'column'},
            'terms':[
              'foobar',
              {'avg_price_all':{
                 'type': 'area'}}]}
           ]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)
  
    def test_opts_missing(self):
        pcso_input = \
          [{'terms':[
              'avg_price',
              {'avg_price_all':{
                 'type': 'area'}}]}
           ]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)

    def test_opts_wrong_type(self):
        pcso_input = \
          [{'options': 0,
            'terms':[
              'avg_price',
              {'avg_price_all':{
                 'type': 'area'}}]}
           ]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)

    def test_terms_missing(self):
        pcso_input = \
          [{'opts': {
              'type': 'column'}}]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)

    def test_terms_a_dict_not_a_list(self):
        pcso_input = \
          [{'options': {
              'type': 'column'},
            'terms':
              {'avg_price_all':{
                 'type': 'area'}}}]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)
  
    def test_terms_a_str(self):
        pcso_input = \
          [{'options': {
              'type': 'column'},
            'terms':
              'foobar'}]
        self.assertRaises(APIInputError, clean_pcso, pcso_input, self.ds)
  
          
class GoodChartOptions(TestCase):
    series_input = \
      [{'options': {
          'source': MonthlyWeatherByCity.objects.all()},
        'terms': [
          'month',
          'boston_temp',
          'houston_temp',
          'new_york_temp']},
       {'options': {
          'source': MonthlyWeatherSeattle.objects.all()},
        'terms': [
          {'month_seattle': 'month'},
          'seattle_temp']
        }]
    ds = DataPool(series_input) 
    
    def test_all_terms(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'month':[
                 'boston_temp', {
                 'new_york_temp': {
                    'type': 'area',
                    'xAxis': 1}}],
              'month_seattle':
                 ['seattle_temp']}
            }]
        so_cleaned = \
          {'boston_temp': {
             '_x_axis_term': 'month',
             'type': 'column'},
           'new_york_temp': {
             '_x_axis_term': 'month',
             'type': 'area',
             'xAxis': 1},
           'seattle_temp':{
             '_x_axis_term': 'month_seattle',
             'type': 'column'}}
        self.assertOptionDictsEqual(clean_cso(so_input, self.ds),
                                    so_cleaned)

    def test_all_terms_str(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'month':[
                 'boston_temp', 
                 'new_york_temp']}
            }]
        so_cleaned = \
          {'boston_temp': {
             '_x_axis_term': 'month',
             'type': 'column'},
           'new_york_temp': {
             '_x_axis_term': 'month',
             'type': 'column'}}
        self.assertOptionDictsEqual(clean_cso(so_input, self.ds),
                                    so_cleaned)

    def test_all_terms_dict(self):
        so_input = \
          [{'options': 
             {'type': 
                'column'},
            'terms': 
              {'month':[
                 {'boston_temp': {
                    'type': 'area',
                    'xAxis': 1}}, 
                 {'new_york_temp':
                    {'xAxis':0}}]}
            }]
        so_cleaned = \
          {'boston_temp': {
             '_x_axis_term': 'month',
             'type': 'area',
             'xAxis': 1},
           'new_york_temp': {
             '_x_axis_term': 'month',
             'type': 'column',
             'xAxis': 0}}
        self.assertOptionDictsEqual(clean_cso(so_input, self.ds),
                                    so_cleaned)

    def test_multiple_items_in_list(self):
        so_input = \
          [{'options':{
              'type': 'column'},
            'terms': 
              {'month':[
                 'boston_temp',
                 'new_york_temp']}
            },
           {'options': {
              'type':'area'},
            'terms':
              {'month_seattle':[
                 'seattle_temp']}
            }]
        so_cleaned = \
          {'boston_temp': {
             '_x_axis_term': 'month',
             'type': 'column'},
           'new_york_temp': {
             '_x_axis_term': 'month',
             'type': 'column'},
           'seattle_temp':{
             '_x_axis_term': 'month_seattle',
             'type': 'area'}}
        self.assertOptionDictsEqual(clean_cso(so_input, self.ds),
                                    so_cleaned)
    

class BadChartOptions(TestCase):

    series_input = \
      [{'options': {
          'source': MonthlyWeatherByCity.objects.all()},
        'terms': [
          'month',
          'boston_temp',
          'houston_temp',
          'new_york_temp']},
       {'options': {
          'source': MonthlyWeatherSeattle.objects.all()},
        'terms': [
          {'month_seattle': 'month'},
          'seattle_temp']
        }]
    ds = DataPool(series_input) 
    
    def test_options_missing(self):
        so_input = \
          [{'terms': {
              'month':[
                 'boston_temp', {
                 'new_york_temp': {
                    'type': 'area',
                    'xAxis': 1}}],
              'month_seattle':
                 ['seattle_temp']}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
    
    def test_options_wrong_type(self):
        so_input = \
          [{'options': 10,
            'terms': {
              'month':[
                 'boston_temp', {
                 'new_york_temp': {
                    'type': 'area',
                    'xAxis': 1}}],
              'month_seattle':
                 ['seattle_temp']}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
        
    def test_terms_missing(self):
        so_input = \
          [{'options': {
              'type': 'line'}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)

    def test_terms_wrong_type(self):
        so_input = \
          [{'options': {
              'type': 'line'},
            'terms': 10
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
    
    def test_terms_a_list_not_a_dict(self):
        so_input = \
          [{'options': {
              'type': 'line'},
            'terms': [{
              'month': ['new_york_temp']}]
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
        
    def test_terms_empty(self):
        so_input = \
          [{'options': {
              'type': 'line'},
            'terms': {}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
   
    def test_yterms_not_in_ds(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'month':[
                 'foobar']}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
    
    def test_xterms_not_in_ds(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'foobar':[
                 'seattle_temp']}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
    
    def test_x_and_y_not_in_same_table(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'month_seattle':['new_york_temp']}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)
    
    def test_yterms_not_a_list(self):
        so_input = \
          [{'options': {
              'type': 'column'},
            'terms': {
              'month':'new_york_temp'}
            }]
        self.assertRaises(APIInputError, clean_cso, so_input, self.ds)

########NEW FILE########
__FILENAME__ = utils
from django.db.models.aggregates import Aggregate
from django.db.models.query import QuerySet

def assertOptionDictsEqual(self, first, second):
    if type(first) != type(second):
        msg = "Types don't match %r --> %r" %(type(first), type(second)) 
        self.fail(msg)
    if len(first) != len(second):
        msg = "Lengths don't match; %r --> %r" %(first, second)
        self.fail(msg)
    if set(first.keys()) != set(second.keys()):
        msg = "Keys don't match %s, %s" %(first.keys(), second.keys())
        self.fail(msg)
    for k1, v1 in first.items():
        v2 = second[k1]
        if isinstance(v1, Aggregate):
            if isinstance(v2, Aggregate):
                if v1.name == v2.name and v1.lookup == v2.lookup:
                    return
                else:
                    msg = "Aggregates don't match"
                    self.fail(msg)
            else:
                msg = "Aggregate being compared to a Non-aggregate."
                self.fail(msg)
        elif isinstance(v1, QuerySet):
            if isinstance(v2, QuerySet):
                if str(v1.query) == str(v2.query):
                    return
                else:
                    msg = "Querysets don't match"
                    self.fail(msg)
            else:
                msg = "QuerySet being compared to a Non-QuerySet."
                self.fail(msg)
        elif isinstance(v1, dict):
            if isinstance(v2, dict):
                self.assertOptionDictsEqual(v1, v2)
            else:
                msg = "Dict being compared to a Non-dict."
                self.fail(msg)
        else:
            self.assertEqual(v1, v2)
                
########NEW FILE########
__FILENAME__ = models
from django.db import models


class MonthlyWeatherByCity(models.Model):
    month = models.IntegerField()
    boston_temp = models.DecimalField(max_digits=5, decimal_places=1)
    houston_temp = models.DecimalField(max_digits=5, decimal_places=1)
    new_york_temp = models.DecimalField(max_digits=5, decimal_places=1)
    san_franciso_temp = models.DecimalField(max_digits=5, decimal_places=1)
    
class MonthlyWeatherSeattle(models.Model):
    month = models.IntegerField()
    seattle_temp = models.DecimalField(max_digits=5, decimal_places=1)
    
class DailyWeather(models.Model):
    month = models.IntegerField()
    day = models.IntegerField()
    temperature = models.DecimalField(max_digits=5, decimal_places=1)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
########NEW FILE########
__FILENAME__ = views
import os
from django.shortcuts import render_to_response
from chartit import DataPool, Chart
from demoproject.utils.decorators import add_source_code_and_doc
from .models import MonthlyWeatherByCity, MonthlyWeatherSeattle, DailyWeather

@add_source_code_and_doc
def basicline(request, title, code, doc, sidebar_items):
    """
    A Basic Line Chart
    ------------------
    This is just a simple line chart with data from 2 different columns.
    
    Points to note:

    - ``terms`` is a list of all fields (both for x-axis and y-axis) 
      to retrieve from the model.
    - Remember that for a Chart, the x and y terms in the ``series_options`` 
      are written as ``x: [y, ...]`` pairs.
    - Any valid items in the `Highcharts options object
      <http://www.highcharts.com/ref/>`_ are valid ``chart_options``.
    """
    
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']}
             ])

    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line',
                  'stacking': False},
                'terms':{
                  'month': [
                    'boston_temp',
                    'houston_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data of Boston and Houston'},
               'xAxis': {
                    'title': {
                       'text': 'Month number'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def basicpie(request, title, code, doc, sidebar_items):
    """
    A Basic Pie Chart
    ------------------
    This is a pie chart of temperature by month for Boston. 
    
    Points to note:

    - ``terms`` is a list of all fields (both for x-axis and y-axis) 
      to retrieve from the model.
    - Remember that for a Chart, the x and y terms in the ``series_options`` 
      are written as ``x: [y, ...]`` pairs.
    - Any valid items in the `Highcharts options object
      <http://www.highcharts.com/ref/>`_ are valid ``chart_options``.
    - We use the ``x_mapf_sortf_mts`` parameter to convert the month numbers 
      retrieved from the database to month names.
      
    Note: This demo is to demonstrate the use of the API and not to teach 
    you data analysis and data presentation skills. Not all charts plotted 
    in this demo may make sense in real life applications. But they can 
    still be useful in demonstrating the API.
    
    """
    
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'boston_temp']}
             ])
    
    def monthname(month_num):
        names ={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        return names[month_num]
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'pie',
                  'stacking': False},
                'terms':{
                  'month': [
                    'boston_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Monthly Temperature of Boston'}},
            x_sortf_mapf_mts = (None, monthname, False))
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def mapf_for_x(request, title, code, doc, sidebar_items):
    """
    Mapping the x-axis
    ------------------
    
    This example demonstrates how to use the ``sortf_mapf_mts`` parameter to 
    *map* the x-axis. The database only has month numbers (1-12) but not the 
    month names. To display the month names in the graph, we create the 
    ``monthname`` function and pass it to the ``Chart`` as the mapping funtion 
    (``mapf``). 
    
    Points to note: 
    
    - ``mts`` is ``False`` because we want to sort by month numbers and map to 
      the month names *after* they are sorted in order of month numbers. 
      Setting it to ``True`` would sort after mapping giving an incorrect sort 
      order like ``Apr``, ``Aug``, ``Dec``, ``...``. 
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']}
             ])
    
    def monthname(month_num):
        names ={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        return names[month_num]
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line',
                  'stacking': False},
                'terms':{
                  'month': [
                    'boston_temp',
                    'houston_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data of Boston and Houston'},
               'xAxis': {
                    'title': {
                       'text': 'Month'}}},
            x_sortf_mapf_mts = (None, monthname, False))
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def multi_table_same_x(request, title, code, doc, sidebar_items):
    """
    Data from multiple models on same chart
    ----------------------------------------
    
    This example demonstrates data from two different models 
    ``MonthlyWeatherByCity`` and ``MonthlyWeatherSeattle`` on the same chart
    and on the same x-axis.
    
    Points to note:
    
    - The `month` in ``terms`` for seattle data is written as 
      ``{'month_seattle': 'month'}`` instead of as just ``'month'`` because 
      in the latter case it would overwrite the ``'month'`` term from the 
      other model.
    - Notice that the Seattle weather data in the database does not have any
      data for August (8) and September (9). Chartit gracefully skips them 
      and plots the rest of the data points aligned correctly.
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']},
             {'options': {
                'source': MonthlyWeatherSeattle.objects.all()},
              'terms': [
                {'month_seattle': 'month'},
                'seattle_temp']}
             ])

    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line',
                  'stacking': False},
                'terms':{
                  'month': [
                    'boston_temp',
                    'houston_temp'],
                  'month_seattle': [
                    'seattle_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather by Month (from 2 different tables)'},
               'xAxis': {
                    'title': {
                       'text': 'Month number'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def multi_axes_and_types(request, title, code, doc, sidebar_items):
    """
    Charts on multiple axes and multiple chart types
    -------------------------------------------------
    
    This example demonstrates how to plot data on different axes using 
    different chart types.
    
    Points to note:
    
    - You can plot data on different axes by setting the ``xAxis`` and 
      ``yAxis``.
    - The ``series_options`` - ``options`` dict takes any of the values from 
      `Highcharts series options <http://www.highcharts.com/ref/#series>`_.
    - If there are only 2 axes (0 and 1), the default behavior of Chartit is 
      to display them on opposite sides. You can override this default behavior
      by setting ``{"opposite": False}`` manually. If there are more than 
      2 axes, Chartit displays all of them on the same side by default.
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']}])

    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line',
                  'xAxis': 0,
                  'yAxis': 0,
                  'zIndex': 1},
                'terms':{
                  'month': [
                    'boston_temp']}},
               {'options': {
                  'type': 'area',
                  'xAxis': 1,
                  'yAxis': 1},
                'terms':{
                  'month': ['houston_temp']}}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data by Month (on different axes)'},
               'xAxis': {
                    'title': {
                       'text': 'Month number'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})
    
@add_source_code_and_doc
def chart_default_options(request, title, code, doc, sidebar_items):
    """
    Some default options explained
    -------------------------------
    
    Even though the ``chart_options`` are not specified, Chartit 
    automatically tries to guess the axis titles, chart titles etc.
    
    Points to note:
    
    - Notice how the axes are named, chart is named etc. by default.
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']},
             {'options': {
                'source': MonthlyWeatherSeattle.objects.all()},
              'terms': [
                {'month_seattle': 'month'},
                'seattle_temp']}
             ])
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line',
                  'stacking': False},
                'terms':{
                  'month': [
                    'boston_temp',
                    'houston_temp'],
                  'month_seattle': [
                    'seattle_temp']
                  }}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})
    
@add_source_code_and_doc
def scatter_plot(request, title, code, doc, sidebar_items):
    """
    Scatter Plot
    -------------
    
    The ``DailyWeather`` database has data by ``month``, ``day``, ``city`` and 
    ``temperature``. In this example we plot a scatter plot of temperature 
    of the city of Boston w.r.t month.
    
    Points to note:
    
    - Notice that the data is filtered naturally using ``filter`` method in 
      django. 
     
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': DailyWeather.objects.filter(city="Boston")},
              'terms': [
                'month', 
                'temperature']}])
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'scatter'},
                'terms':{
                  'month': [
                    'temperature']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Boston weather scatter plot'},
               'xAxis': {
                    'title': {
                       'text': 'Month'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})
    
@add_source_code_and_doc
def combination_plot(request, title, code, doc, sidebar_items):
    """
    Combination Plot
    -----------------
    
    We can do more complicated plots from multiple databases on the same chart.
    In this chart we plot a scatter plot of daily weather of Boston from the 
    ``DailyWeather`` database and the monthly average temperature of Boston as
    a from the ``MonthlyWeatherByCity`` database on the same chart.
    
    Points to note:
    
    - Notice that the data is filtered naturally using ``filter`` method in 
      django. 
    - The ``zIndex`` parameter (one of the many 
      `Highcharts series options <http://www.highcharts.com/ref/#series>`_) is 
      used to force the monthly temperature to be on the top.
    """
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': DailyWeather.objects.filter(city="Boston")},
              'terms': [
                'month', 
                'temperature']},
             {'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                {'month_boston': 'month'}, 
                'boston_temp']}])
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'scatter'},
                'terms':{
                  'month': [
                    'temperature']
                  }},
               {'options':{
                  'type': 'scatter',
                  'zIndex': 1},
                'terms':{
                  'month_boston': [
                    'boston_temp']
                  }},
               ],
            chart_options = 
              {'title': {
                   'text': 'Boston Daily weather and Monthly Average'},
               'yAxis': {
                 'title': {
                   'text': 'Temperature'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def column_chart_multi_stack(request, title, code, doc, sidebar_items):
    """
    Column Chart
    ------------------
    Column chart of temperatures of Boston and New York in one stack and the 
    temperature of Houston in another stack. 
    
    Points to note:
    
    - Notice that ``houston_temp`` shares all the other options with 
      ``boston_temp`` and ``new_york_temp``. So we override just the ``stack``
      parameter from the ``options`` for ``houston_temp`` by writing 
      ``{'houston_temp: {'stack': 1}}``. 
      
      We can also write ``series_options`` as ::
      
        series_options = [
               {'options':{
                  'type': 'column',
                  'stacking': True,
                  'stack': 0},
                'terms':{
                  'month': [
                    'boston_temp',
                    'new_york_temp']}},
                      
               {'options':{
                  'type': 'column',
                  'stacking': True,
                  'stack': 1},
                'terms':{
                  'month': [
                    'houston_temp']}
                    }]
        
      to plot this chart. But the form used in the code is much shorter and
      there is less duplication. 
        
    Note: This demo is to demonstrate the use of the API and not to teach 
    you data analysis and data presentation skills. Not all charts plotted 
    in this demo may make sense in real life applications. But they can 
    still be useful in demonstrating the API.
    """
    
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp',
                'new_york_temp']}
             ])

    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'column',
                  'stacking': True,
                  'stack': 0},
                'terms':{
                  'month': [
                    'boston_temp',
                    'new_york_temp',
                    {'houston_temp': {
                      'stack': 1}},]
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data of Boston, New York and Houston'},
               'xAxis': {
                    'title': {
                       'text': 'Month number'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def column_chart(request, title, code, doc, sidebar_items):
    """
    Column Chart
    ------------------
    Just a simple column chart of temperatures of Boston and Houston stacked 
    on top of each other.
    
    Points to note:
    
    - Any of the `Highcharts series options 
      <http://www.highcharts.com/ref/#series>`_ are valid options for the Chart
      ``series_options`` - ``options`` dict. In this case we set the 
      ``stacking`` parameter to ``True`` to stack the columns on the top of 
      each other.
    
    Note: This demo is to demonstrate the use of the API and not to teach 
    you data analysis and data presentation skills. Not all charts plotted 
    in this demo may make sense in real life applications. But they can 
    still be useful in demonstrating the API.
    """
    
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month',
                'houston_temp', 
                'boston_temp']}
             ])

    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'column',
                  'stacking': True},
                'terms':{
                  'month': [
                    'boston_temp',
                    'houston_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data of Boston and Houston'},
               'xAxis': {
                    'title': {
                       'text': 'Month number'}}})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def combination_line_pie(request, title, code, doc, sidebar_items):
    """
    Combination of line and Pie charts
    -----------------------------------
    A combination of line and pie charts displayed on the same chart.
    
    Points to note:
    
    - ``center`` and ``size`` are used to center the pie chart and scale it 
      to fit in the chart. Remember that any of the `Highcharts series options 
      <http://www.highcharts.com/ref/#series>`_ are valid options for the Chart
      ``series_options`` - ``options`` dict. 

    Note: This demo is to demonstrate the use of the API and not to teach 
    you data analysis and data presentation skills. Not all charts plotted 
    in this demo may make sense in real life applications. But they can 
    still be useful in demonstrating the API.
    """
    
    #start_code
    ds = DataPool(
           series=
            [{'options': {
                'source': MonthlyWeatherByCity.objects.all()},
              'terms': [
                'month', 
                'boston_temp',
                'houston_temp']}
             ])
    
    def monthname(month_num):
        names ={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        return names[month_num]
    
    cht = Chart(
            datasource = ds, 
            series_options = 
              [{'options':{
                  'type': 'line'},
                'terms':{
                  'month': [
                    'boston_temp']
                  }},
               {'options':{
                  'type': 'pie',
                  'center': [150, 100],
                  'size': '50%'},
                'terms':{
                  'month': [
                    'houston_temp']
                  }}],
            chart_options = 
              {'title': {
                   'text': 'Weather Data of Boston (line) and Houston (pie)'}},
            x_sortf_mapf_mts = [(None, monthname, False),
                                (None, monthname, False)])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': cht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def model_details(request, title, code, doc, sidebar_items):
    """
    All the charts in this section are based on the following Models. The raw 
    data is available as a ``SQLite3`` database file  
    `here <../../static/db/chartitdemodb>`_. You can download the file and use 
    `SQLiteBrowser <http://sqlitebrowser.sourceforge.net/>`_ 
    to look at the raw data. 
    """
    fname = os.path.join(os.path.split(os.path.abspath(__file__))[0], 
                         'models.py')
    with open(fname) as f:
        code = ''.join(f.readlines())
    return render_to_response('model_details.html', 
                              {'code': code,
                               'title': title,
                               'doc': doc,
                               'sidebar_items': sidebar_items})
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, redirect
from demoproject.utils.decorators import add_source_code_and_doc

@add_source_code_and_doc
def demohome(request, title, code, doc, sidebar_items):
    """
    Welcome to the Django-Chartit Demo. This demo has a lot of sample charts 
    along with the code to help you get familiarized with the Chartit API. 
    
    The examples start with simple ones and get more and  more complicated. 
    The latter examples use concepts explained in the examples earlier. So if 
    the source code of a particular chart looks confusing, check to see if any 
    details have already been explained in a previous example. 
    
    The models that the examples are based on are explained in Model Details.
    
    The raw data for all the models is available as a ``SQLite3`` database 
    file `here <../../static/db/chartitdemodb>`_. You can download the file 
    and use `SQLiteBrowser <http://sqlitebrowser.sourceforge.net/>`_ 
    to look at the raw data.
    
    Thank you and have fun exploring! 
    """
    return render_to_response('demohome.html', 
                              {'chart_list': None,
                               'code': None,
                               'title': title,
                               'doc': doc,
                               'sidebar_items': sidebar_items})
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from demoproject.chartdemo.models import MonthlyWeatherByCity
from chartit import DataPool, Chart

def homepage(request):
    ds = DataPool(
       series=
        [{'options': {
            'source': MonthlyWeatherByCity.objects.all()},
          'terms': [
            'month',
            'houston_temp', 
            'boston_temp',
            'san_franciso_temp']}
         ])
    def monthname(month_num):
        names ={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        return names[month_num]
    cht = Chart(
        datasource = ds, 
        series_options = 
          [{'options':{
              'type': 'line',
              'stacking': False},
            'terms':{
              'month': [
                'boston_temp',
                'houston_temp']
              }}],
        chart_options = 
          {'title': {
               'text': 'Weather by Month'},
           'xAxis': {
                'title': {
                   'text': 'Month'}},
           'yAxis': {
                'title': {
                    'text': 'Temperature'}},
           'legend': {
                'enabled': False},
           'credits': {
                'enabled': False}},
         x_sortf_mapf_mts = (None, monthname, False))
    return render_to_response('index.html', {'chart_list': cht})
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Author(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    def __unicode__(self):
        return '%s %s' %(self.first_name, self.last_name)

class Publisher(models.Model):
    name = models.CharField(max_length=50)
    def __unicode__(self):
        return '%s' %(self.name)

class Genre(models.Model):
    name = models.CharField(max_length=50)
    def __unicode__(self):
        return '%s' %(self.name)

class Book(models.Model):
    title = models.CharField(max_length=50)
    rating = models.FloatField(db_column='rating')
    rating_count = models.IntegerField()
    authors = models.ManyToManyField(Author)
    publisher = models.ForeignKey(Publisher, null=True, blank=True, 
                                  on_delete=models.SET_NULL)
    related = models.ManyToManyField('self', db_column='related', blank=True)
    genre = models.ForeignKey(Genre, null=True, blank=True, 
                              on_delete=models.SET_NULL)
    def __unicode__(self):
        return '%s' %(self.title)

class City(models.Model):
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=2)
    def __unicode__(self):
        return '%s, %s' %(self.city, self.state)

class BookStore(models.Model):
    name =  models.CharField(max_length=50)
    city = models.ForeignKey('City')
    def __unicode__(self):
        return '%s' %(self.name)
    
class SalesHistory(models.Model):
    bookstore = models.ForeignKey(BookStore)
    book = models.ForeignKey(Book)
    sale_date = models.DateField()
    sale_qty = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2)
    def __unicode__(self):
        return '%s %s %s' %(self.bookstore, self.book, self.sale_date)

########NEW FILE########
__FILENAME__ = views
import os
from django.shortcuts import render_to_response
from django.db.models import Sum, Avg
from chartit import PivotChart, PivotDataPool
from demoproject.utils.decorators import add_source_code_and_doc
from models import SalesHistory


@add_source_code_and_doc
def simplepivot(request, title, code, doc, sidebar_items):
    """
    A simple pivot chart.
    
    Points to notice:
    
    - You can use the default django convention of double underscore (__) to 
      *follow* to the fields in different models.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__city'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}])
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column'},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})
    
@add_source_code_and_doc
def pivot_with_legend(request, title, code, doc, sidebar_items):
    """
    Pivot Chart with legend by field. This pivot chart plots total sale 
    quantity of books in each city legended by the book genre name.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': 'bookstore__city__city',
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}])
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True, 
                   'xAxis': 0,
                   'yAxis': 0},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def pivot_multi_category(request, title, code, doc, sidebar_items):
    """
    Pivot Chart with multiple categories. In this chart the total sale 
    quantity is plotted with respect to state and city.
    
    Points to note:
    
    - You can add any number of categories and legend_by entries in a list. 
    - **Order matters**! Retrieving state and then city may yield different 
      results compared to retrieving city and state depending on what you 
      are trying to plot.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}])
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True, 
                   'xAxis': 0,
                   'yAxis': 0},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def pivot_with_top_n_per_cat(request, title, code, doc, sidebar_items):
    """
    Pivot Chart each category limited to a select top items.
    
    Points to note:
    
    - These charts are helpful when there are too many items in each category
      and we only want to focus on the top few items in each category.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name',
              'top_n_per_cat': 2},
            'terms': {
              'tot_sales':Sum('sale_qty')}}])
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True, 
                   'xAxis': 0,
                   'yAxis': 0},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})


@add_source_code_and_doc
def pivot_top_n(request, title, code, doc, sidebar_items):
    """
    Pivot Chart limited to top few items. In this chart the sales quanity is 
    plotted w.r.t state/city but the chart is limited to only top 5 cities 
    witht the highest sales.
    
    Points to note:
    
    - These charts are helpful in cases where there is a long *tail* and we 
      only are interested in the top few items.
    - ``top_n_term`` is always required. If there are multiple items, it will 
      elimnate confusion regarding what the term the chart needs to be 
      limited by.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}],
          top_n = 5,
          top_n_term = 'tot_sales')
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True, 
                   'xAxis': 0,
                   'yAxis': 0},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def pivot_pareto(request, title, code, doc, sidebar_items):
    """
    Pivot Chart plotted as a `pareto chart 
    <http://en.wikipedia.org/wiki/Pareto_chart>`_ w.r.t the total sales 
    quantity.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}],
          top_n = 5,
          top_n_term = 'tot_sales',
          pareto_term = 'tot_sales')
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True, 
                   'xAxis': 0,
                   'yAxis': 0},
                 'terms': ['tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def pivot_multi_axes(request, title, code, doc, sidebar_items):
    """
    Pivot Chart with multiple terms on multiple axes.
    
    Points to note:
    
    - Note that the term ``avg-price`` is passed as a dict (instead of as a 
      django aggregate to allow us to override the default ``legend_by`` 
      option. When passed as a dict, the aggregate function needs to be passed
      to the ``func`` key. 
    - Alternatively this could be written as ::
    
        series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}},
              
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city']},
            'terms': {
              'avg_price':Avg('price')}}
              ]
              
      but the one used in the code is more succint and has less duplication.
    """
    #start_code
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty'),
              'avg_price':{
                'func': Avg('price'),
                'legend_by': None}}}],
          top_n = 5,
          top_n_term = 'tot_sales',
          pareto_term = 'tot_sales')
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True},
                 'terms': [
                    'tot_sales',
                    {'avg_price': {
                        'type': 'line',
                        'yAxis': 1}}]}],
              chart_options = {
                'yAxis': [{}, {'opposite': True}]})
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def pivot_mapf(request, title, code, doc, sidebar_items):
    """
    Pivot Chart with ``sortf_mapf_mts`` defined to map custom names for x-axis
    and to customize the x-axis sorting. In this chart we would like to plot 
    region:city instead of state:city. However region is not available in the 
    database. So custom mapf function comes to the rescue.
    
    Points to note:
    
    - Note that ``mapf`` receives a tuple and returns a tuple. This is true 
      even when ``categories`` is a single element.
    - ``mts=True`` causes the elements to be mapped and then sorted. So all the 
      N region cities are on the left and the S region cities are on the right
      hand side of the plot. 
    """
    #start_code
    def region_state(x):
        region = {'CA': 'S', 'MA': 'N', 'TX': 'S', 'NY': 'N'}
        return (region[x[0]], x[1])
    
    ds = PivotDataPool(
          series= [
           {'options':{
              'source': SalesHistory.objects.all(),
              'categories': [
                'bookstore__city__state',
                'bookstore__city__city'],
              'legend_by': 'book__genre__name'},
            'terms': {
              'tot_sales':Sum('sale_qty')}}],
          sortf_mapf_mts = (None, region_state, True))
    
    pivcht = PivotChart(
              datasource = ds, 
              series_options = [
                {'options': {
                   'type': 'column',
                   'stacking': True},
                 'terms': [
                    'tot_sales']}])
    #end_code
    return render_to_response('chart_code.html', {'chart_list': pivcht,
                                             'code': code,
                                             'title': title,
                                             'doc': doc,
                                             'sidebar_items': sidebar_items})

@add_source_code_and_doc
def model_details(request, title, code, doc, sidebar_items):
    """
    All the charts in this section are based on the following Models. The raw 
    data is available as a ``SQLite3`` database file  
    `here <../../static/db/chartitdemodb>`_. You can download the file and use 
    `SQLiteBrowser <http://sqlitebrowser.sourceforge.net/>`_ 
    to look at the raw data. 
    """
    fname = os.path.join(os.path.split(os.path.abspath(__file__))[0], 
                         'models.py')
    
    with open(fname) as f:
        code = ''.join(f.readlines())
    
    return render_to_response('model_details.html', 
                              {'code': code,
                               'title': title,
                               'doc': doc,
                               'sidebar_items': sidebar_items})
########NEW FILE########
__FILENAME__ = settings
import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG
CHARTIT_DIR = os.path.split(os.path.dirname(__file__))[0]
sys.path = [CHARTIT_DIR] + sys.path
PROJECT_ROOT = os.path.dirname(__file__)
ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS
TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
STATIC_URL = '/static/'
CHARTIT_JS_REL_PATH = '/chartit/js/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'projectstatic'),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
)
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
ROOT_URLCONF = 'urls'
TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates')
)
INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'django.contrib.markup',
    'syntax_colorize',
    'chartit',
    'chartdemo',
    'pivotdemo',
)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# All production settings like sensitive passwords go here.
# Remember to exclude this file from version control
try:
    from prod_settings_demo import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = syntax_color
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name,guess_lexer,ClassNotFound

register = template.Library()

def generate_pygments_css(path=None):
    if path is None:
        import os
        path = os.path.join(os.getcwd(),'pygments.css')
    f = open(path,'w')
    f.write(HtmlFormatter().get_style_defs('.highlight'))
    f.close()

def get_lexer(value,arg):
    if arg is None:
        return guess_lexer(value)
    return get_lexer_by_name(arg)

@register.filter(name='colorize')
@stringfilter
def colorize(value, arg=None):
    try:
        return mark_safe(highlight(value,get_lexer(value,arg),HtmlFormatter()))
    except ClassNotFound:
        return value


@register.filter(name='colorize_table')
@stringfilter
def colorize_table(value,arg=None):
    try:
        return mark_safe(highlight(value,get_lexer(value,arg),HtmlFormatter(linenos='table')))
    except ClassNotFound:
        return value

    

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns
from django.views.generic.simple import redirect_to

home_view_title = [
    (r'demo/', 'demohome', 
     'Hello there!'),
]

chart_view_title = [
    (r'demo/chart/model-details/', 'model_details',
     'Model Details'),
    (r'demo/chart/basic-line/', 'basicline', 
     'Line chart'),
    (r'demo/chart/mapf-for-x/', 'mapf_for_x',
     'Custom names for x-axis values'),
    (r'demo/chart/column-chart/', 'column_chart', 
     'Column chart'),
    (r'demo/chart/column-chart-multi-stack/', 'column_chart_multi_stack', 
     'Column chart with multiple stacks'),
    (r'demo/chart/scatter-plot/', 'scatter_plot', 
     'Scatter plot'),
    (r'demo/chart/basic-pie/', 'basicpie', 
     'Pie chart'),
    (r'demo/chart/multi-table-same-x/', 'multi_table_same_x', 
     'Data from multiple models on same chart' ),
    (r'demo/chart/multi-axes-and-types/', 'multi_axes_and_types', 
     'Multiple chart types and multiple axes' ),
    (r'demo/chart/chart-default-options/', 'chart_default_options', 
     'Chart default options explained'),
    (r'demo/chart/combination-plot/', 'combination_plot', 
     'Scatter plot with data from multiple models'),
    (r'demo/chart/combination-line-pie/', 'combination_line_pie', 
     'Combination of line and pie'),
]

pivot_view_title = [
    (r'demo/pivot/model-details/', 'model_details',
     'Model Details'),
    (r'demo/pivot/simple/', 'simplepivot', 
     'A basic Pivot Chart'),
    (r'demo/pivot/pivot-with-legend/', 'pivot_with_legend', 
     'Pivot chart with legend by'),
    (r'demo/pivot/multi-category/', 'pivot_multi_category', 
     'Pivot chart with multiple categories'),
    (r'demo/pivot/top-n-per-cat/', 'pivot_with_top_n_per_cat', 
     'Pivot chart with top few items per category'),
    (r'demo/pivot/top-n/', 'pivot_top_n', 
     'Pivot chart with only top few items'),  
    (r'demo/pivot/pareto/', 'pivot_pareto', 
     'Pareto Chart'),    
    (r'demo/pivot/muti-axes/', 'pivot_multi_axes',
     'Pivot Chart on multiple axes'),
    (r'demo/pivot/mapf/', 'pivot_mapf',
     'Pivot Chart with custom mapping for x-axis')
]

home_sidebar = [(r'../' + url, title) for (url, view, title) in 
                 home_view_title]

chart_sidebar = [(r'../' + url, title) for (url, view, title) in 
                 chart_view_title]
pivot_sidebar = [(r'../' + url, title) for (url, view, title) in 
                    pivot_view_title]

sidebar_items = [("Welcome", home_sidebar),
                 ("Charts", chart_sidebar),
                 ("Pivot Charts", pivot_sidebar)]

home_pattern_tuples = [(r'^' + url + r'$', 
                       view, 
                       {'title': title, 
                        'sidebar_items': sidebar_items}) for 
                           (url, view, title) in home_view_title]

chart_pattern_tuples = [(r'^' + url + r'$', 
                       view, 
                       {'title': title, 
                        'sidebar_items': sidebar_items}) for 
                           (url, view, title) in chart_view_title]
pivot_pattern_tuples = [(r'^' + url + r'$', 
                       view, 
                       {'title': title, 
                        'sidebar_items': sidebar_items}) for 
                           (url, view, title) in pivot_view_title] 

homepatterns = patterns('homepage.views', 
                        (r'^$', 'homepage'),)
homepatterns += patterns('',
                         (r'^favicon\.ico$',
                          'django.views.generic.simple.redirect_to',
                          {'url': '/static/home/images/favicon.ico'}))

demopatterns = patterns('demo.views', *home_pattern_tuples)
chartpatterns = patterns('chartdemo.views', *chart_pattern_tuples)
pivotpatterns = patterns('pivotdemo.views', *pivot_pattern_tuples)

urlpatterns = homepatterns + demopatterns + chartpatterns + pivotpatterns
########NEW FILE########
__FILENAME__ = decorators
import inspect
import textwrap
from functools import wraps

def add_source_code_and_doc(f):
    """Instrospects the function and adds source code and the doc string to 
    the return parameters.
    """
    @wraps(f)
    def f_with_source_and_doc(request, title, sidebar_items, 
                              *args, **kwargs):
        doc = f.__doc__
        if doc is None:
            doc = ""
        else:
            doc = textwrap.dedent(f.__doc__)
        
        src_lines, num_lines = inspect.getsourcelines(f)
        start_line = end_line = None
        for i, line in enumerate(src_lines):
            if start_line is None or end_line is None: 
                if '#start_code' in line:
                    start_line = i+1
                if '#end_code' in line:
                    end_line = i
            else:
                break
        if end_line is None:
            end_line = num_lines - 1
        if start_line is None:
            start_line = 1
            
        code = ''.join(src_lines[start_line: end_line])   
        code = textwrap.dedent(code)
        return f(request, code = code, title = title,
                 doc = doc, sidebar_items = sidebar_items)
    return f_with_source_and_doc
        

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django-Chartit documentation build configuration file, created by
# sphinx-quickstart on Thu Nov 03 09:33:01 2011.
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
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django-Chartit'
copyright = u'2011, Praveen Gollakota'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
html_theme = 'nature'

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
htmlhelp_basename = 'Django-Chartitdoc'


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
  ('index', 'Django-Chartit.tex', u'Django-Chartit Documentation',
   u'Praveen Gollakota', 'manual'),
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
    ('index', 'django-chartit', u'Django-Chartit Documentation',
     [u'Praveen Gollakota'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Django-Chartit', u'Django-Chartit Documentation',
   u'Praveen Gollakota', 'Django-Chartit', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = fabfile
import os
import fabric
from fabric.api import env, local, sudo, cd, prefix

env.hosts = ['praveen@173.255.241.59']
env.master_repo = 'ssh://hg@bitbucket.org/pgollakota/django-chartit'
env.sec_repo = 'git+ssh://git@github.com/pgollakota/django-chartit.git'
env.activate = 'source /work/virtualenvs/chartit/bin/activate'
env.project_root = '/home/praveen/cows/django-chartit'


def run(cmd):
    with cd(env.project_root):
        with prefix(env.activate):
            fabric.api.run(cmd)


def push():
    local('hg push %(master_repo)s' % env)
    local('hg push %(sec_repo)s' % env)
    run('hg pull -u %(master_repo)s' % env)


def upload_to_pypi():
    local('python setup.py sdist upload')


def build_docs():
    with prefix('export DJANGO_SETTINGS_MODULE=demoproject.settings'):
        run('cd docs && make html')


def install_requirements():
    run('pip install -r requirements.txt -q')


def upgrade_db():
    run('cd demoproject && python manage.py syncdb')


def deploy_static():
    run('cd demoproject && python manage.py collectstatic -v0 --noinput')


def restart_webserver():
    sudo('supervisorctl restart nginx')
    sudo('supervisorctl restart chartit')


def deploy():
    push()
    build_docs()
    install_requirements()
    upgrade_db()
    deploy_static()
    restart_webserver()

########NEW FILE########
