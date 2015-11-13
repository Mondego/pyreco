__FILENAME__ = examples
#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
  -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
  -------------
  '''
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import epipy
import os

try:
    from mpltools import style, layout
    style.use('ggplot')
    layout.use('ggplot')
except:
    pass


#################################
# TEST DATA EXAMPLE #
#################################

# Generate example data
example_df = epipy.generate_example_data(cluster_size=7, outbreak_len=180, clusters=7, gen_time=4, attribute='health')

# Case tree plot                                        
fig, ax = epipy.case_tree_plot(example_df, cluster_id = 'Cluster', \
                    case_id ='ID', date_col='Date', color='health', \
                    gen_mean=4, gen_sd = 1)
ax.set_title('Example outbreak data')

# Checkerboard plot
fig, ax = epipy.checkerboard_plot(example_df, 'ID', 'Cluster', 'Date')
ax.set_title("Example outbreak data")


############################
## MERS-CoV DATA EXAMPLE ###
############################

mers_df = epipy.get_data('mers_line_list')
#you can also get synthetic data using epipy.get_data('example_data')

# Data cleaning
mers_df['onset_date'] = mers_df['Approx onset date'].map(epipy.date_convert)
mers_df['report_date'] = mers_df['Approx reporting date'].map(epipy.date_convert)
mers_df['dates'] = mers_df['onset_date'].combine_first(mers_df['report_date'])

# Case tree plot
fig, ax = epi.case_tree_plot(mers_df, cluster_id='Cluster ID', \
                        case_id='Case #', date_col='dates', gen_mean = 5, \
                        gen_sd = 4, color='condensed_health')
ax.set_title('Human clusters of MERS-CoV')

# Checkerboard plot
fig, ax = epipy.checkerboard_plot(mers_df, 'Case #', 'Cluster ID', 'dates')
ax.set_title("Human clusters of MERS-CoV")

#################
### EPICURVES ###
#################

# Daily epicurve of MERS
plt.figure()
curve, fig, ax = epipy.epicurve_plot(mers_df, date_col='dates', freq='day')
plt.title('Approximate onset or report date');

# Yearly epicurve of MERS
plt.figure()
epipy.epicurve_plot(mers_df, 'dates', freq='y')
plt.title('Approximate onset or report date')

# Monthly epicurve of MERS
plt.figure()
curve, fig, ax = epipy.epicurve_plot(mers_df, 'dates', freq='month')
plt.title('Approximate onset or report date of MERS cases')

#################
### ANALYSES ####
#################

# We'll use the MERS data we worked with above
# For this we'll need to build out the graph
mers_G = epipy.build_graph(mers_df, cluster_id='Cluster ID', case_id='Case #',
		date_col='dates', color='Health status', gen_mean=5, gen_sd=4)

# Analyze attribute by generation
fig, ax, table = epipy.generation_analysis(mers_G, attribute='Health status', plot=True)


# Basic reproduction numbers
R, fig, ax = epipy.reproduction_number(mers_G, index_cases=True, plot=True)
print 'R0 median: {}'.format(R.median()) # the series object returned can be manipulated further

#2X2 table
mers_df['condensed_health'] = mers_df['Health status'].replace(['Critical', 'Alive', 'Asymptomatic', 'Mild', 'Recovered', 'Reocvered'], 'Alive')
table = epipy.create_2x2(mers_df, 'Sex', 'condensed_health', ['M', 'F'], ['Dead', 'Alive'])
epipy.analyze_2x2(table)

########NEW FILE########
__FILENAME__ = analyses
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import numpy as np
from scipy.stats import chi2_contingency
import pandas as pd
import matplotlib.pyplot as plt

"""
Author: Caitlin Rivers
Analysis functions for package epipy.
"""
def _get_table_labels(table):
    """
    Returns classic a, b, c, d labels for contingency table calcs.
    """
    a = table[0][0]
    b = table[0][1]
    c = table[1][0]
    d = table[1][1]

    return a, b, c, d


def _ordered_table(table):
    """
    Determine type of table input. Find classic a, b, c, d labels
    for contigency table calculations.
    """
    if type(table) is list:
       a, b, c, d = _get_table_labels(table)
    elif type(table) is pd.core.frame.DataFrame:
        a, b, c, d = _get_table_labels(table.values)
    elif type(table) is np.ndarray:
        a, b, c, d = _get_table_labels(table)
    else:
        raise TypeError('table format not recognized')

    return a, b, c, d


def _conf_interval(ratio, std_error):
    """
    Calculate 95% confidence interval for odds ratio and relative risk.
    """

    _lci = np.log(ratio) - 1.96*std_error
    _uci = np.log(ratio) + 1.96*std_error

    lci = round(np.exp(_lci), 2)
    uci = round(np.exp(_uci), 2)

    return (lci, uci)


def reproduction_number(G, index_cases=True, plot=True):
    """
    Finds each case's basic reproduction number, which is the number of secondary
    infections each case produces.

    PARAMETERS
    ----------------
    G = networkx object
    index_cases = include index nodes, i.e. those at generation 0. Default is True.
                  Excluding them is useful if you want to calculate the human to human
                  reproduction number without considering zoonotically acquired cases.
    summary = print summary statistics of the case reproduction numbers
    plot = create histogram of case reproduction number distribution.

    RETURNS
    ----------------
    pandas series of case reproduction numbers and matplotlib figure
    and axis objects if plot=True
    """

    if index_cases == True:
        R = pd.Series(G.out_degree())

    elif index_cases == False:
        degrees = {}

        for n in G.node:
            if G.node[n]['generation'] > 0:
                degrees[n] = G.out_degree(n)
        R = pd.Series(degrees)

    print 'Summary of reproduction numbers'
    print R.describe(), '\n'

    if plot == True:
        fig, ax = plt.subplots()
        R.hist(ax=ax, alpha=.5)
        ax.set_xlabel('Secondary cases')
        ax.set_ylabel('Count')
        ax.grid(False)
        return R, fig, ax

    else:
        return R


def generation_analysis(G, attribute, plot=True):
    """
    Analyzes an attribute, e.g. health status, by generation.

    PARAMETERS
    -------------
    G = networkx object
    attribute = case attribute for analysis, e.g. health status or sex
    table = print cross table of attribute by generation. Default is true.
    plot = produce histogram of attribute by generation. Default is true.

    RETURNS
    --------------
    matplotlib figure and axis objects

    """

    gen_df = pd.DataFrame(G.node).T

    print '{} by generation'.format(attribute)
    table = pd.crosstab(gen_df.generation, gen_df[attribute], margins=True)
    print table, '\n'

    if plot == True:
        fig, ax = plt.subplots()
        ax.set_aspect('auto')
        pd.crosstab(gen_df.generation, gen_df[attribute]).plot(kind='bar', ax=ax, alpha=.5)
        ax.set_xlabel('Generation')
        ax.set_ylabel('Case count')
        ax.grid(False)
        ax.legend(loc='best');
        return fig, ax, table
    else:
        return table


def create_2x2(df, row, column, row_order, col_order):
    """
    2x2 table of disease and exposure in traditional epi order.

    Table format:
                Disease
    Exposure    YES     NO
    YES         a       b
    NO          c       d

    PARAMETERS
    -----------------------
    df = pandas dataframe of line listing
    row = name of exposure row as string
    column = name of outcome column as string
    row_order = list of length 2 of row values in yes/no order.
                Example: ['Exposed', 'Unexposed']
    col_order = list of length 2 column values in yes/no order.
                Example: ['Sick', 'Not sick']

    RETURNS
    ------------------------
    pandas dataframe of 2x2 table. Prints odds ratio and relative risk.
    """
    if type(col_order) != list or type(row_order) != list:
        raise TypeError('row_order and col_order must each be lists of length 2')

    if len(col_order) != 2 or len(row_order) != 2:
        raise AssertionError('row_order and col_order must each be lists of length 2')

    _table = pd.crosstab(df[row], df[column], margins=True).to_dict()

    trow = row_order[0]
    brow = row_order[1]
    tcol = col_order[0]
    bcol = col_order[1]

    table = pd.DataFrame(_table, index=[trow, brow, 'All'], columns=[tcol, bcol, 'All'])

    return table


def analyze_2x2(table):
    """
    Prints odds ratio, relative risk, and chi square.
    See also create_2x2(), odds_ratio(), relative_risk(), and chi2()

    PARAMETERS
    --------------------
    2x2 table as pandas dataframe, numpy array, or list in format [a, b, c, d]

    Table format:
                Disease
    Exposure    YES     NO
    YES         a       b
    NO          c       d

    """

    odds_ratio(table)
    relative_risk(table)
    attributable_risk(table)
    chi2(table)


def odds_ratio(table):
    """
    Calculates the odds ratio and 95% confidence interval. See also
    analyze_2x2()
    *Cells in the table with a value of 0 will be replaced with .1

    PARAMETERS
    ----------------------
    table = accepts pandas dataframe, numpy array, or list in [a, b, c, d] format.

    RETURNS
    ----------------------
    returns and prints odds ratio and tuple of 95% confidence interval
    """
    table = table.replace(0, .1)

    a, b, c, d = _ordered_table(table)

    ratio = (a*d)/(b*c)
    or_se = np.sqrt((1/a)+(1/b)+(1/c)+(1/d))
    or_ci = _conf_interval(ratio, or_se)
    print 'Odds ratio: {} (95% CI: {})'.format(round(ratio, 2), or_ci)

    return round(ratio, 2), or_ci


def relative_risk(table, display=True):
    """
    Calculates the relative risk and 95% confidence interval. See also
    analyze_2x2().
    *Cells in the table with a value of 0 will be replaced with .1

    PARAMETERS
    ----------------------
    table = accepts pandas dataframe, numpy array, or list in [a, b, c, d] format.

    RETURNS
    ----------------------
    returns and prints relative risk and tuple of 95% confidence interval
    """
    table = table.replace(0, .1)

    a, b, c, d = _ordered_table(table)

    rr = (a/(a+b))/(c/(c+d))
    rr_se = np.sqrt(((1/a)+(1/c)) - ((1/(a+b)) + (1/(c+d))))
    rr_ci = _conf_interval(rr, rr_se)

    if display is not False:
        print 'Relative risk: {} (95% CI: {})\n'.format(round(rr, 2), rr_ci)

    return rr, rr_ci


def attributable_risk(table):
    """
    Calculate the attributable risk, attributable risk percent,
    and population attributable risk.

    PARAMETERS
    ----------------
    table = 2x2 table. See 2x2_table()

    RETURNS
    ----------------
    prints and returns attributable risk (AR), attributable risk percent
    (ARP), population attributable risk (PAR) and population attributable
    risk percent (PARP).
    """
    a, b, c, d = _ordered_table(table)
    N = a + b + c + d

    ar = (a/(a+b))-(c/(c+d))
    ar_se = np.sqrt(((a+c)/N)*(1-((a+c)/N))*((1/(a+b))+(1/(c+d))))
    ar_ci = (round(ar-(1.96*ar_se), 2), round(ar+(1.96*ar_se), 2))

    rr, rci = relative_risk(table, display=False)
    arp = 100*((rr-1)/(rr))
    arp_se = (1.96*ar_se)/ar
    arp_ci = (round(arp-arp_se, 2), round(arp+arp_se, 3))

    par = ((a+c)/N) - (c/(c+d))
    parp = 100*(par/(((a+c)/N)))

    print 'Attributable risk: {} (95% CI: {})'.format(round(ar, 3), ar_ci)
    print 'Attributable risk percent: {}% (95% CI: {})'.format(round(arp, 2), arp_ci)
    print 'Population attributable risk: {}'.format(round(par, 3))
    print 'Population attributable risk percent: {}% \n'.format(round(parp, 2))

    return ar, arp, par, parp


def chi2(table):
    """
    Scipy.stats function to calculate chi square.
    PARAMETERS
    ----------------------
    table = accepts pandas dataframe or numpy array. See also
    analyze_2x2().

    RETURNS
    ----------------------
    returns chi square with yates correction, p value,
    degrees of freedom, and array of expected values.
    prints chi square and p value
    """
    chi2, p, dof, expected = chi2_contingency(table)
    print 'Chi square: {}'.format(chi2)
    print 'p value: {}'.format(p)

    return chi2, p, dof, expected


def _numeric_summary(column):
    """
    Finds count, number of missing values, min, median, mean, std, and
    max.
    See summary()
    """
    names = ['count', 'missing', 'min', 'median', 'mean', 'std', 'max']
    _count = len(column)
    _miss = _count - len(column.dropna())
    _min = column.min()
    _median = column.median()
    _mean = column.mean()
    _std = column.std()
    _max = column.max()
    summ = pd.Series([_count, _miss, _min, _median, _mean, _std, _max], index=names)

    return summ


def _categorical_summary(column, n=None):
    """
    Finds count and frequency of each unique value in the column.
    See summary().
    """
    if n is not None:
        _count = column.value_counts()[:n]
    else:
        _count = column.value_counts()
    names = ['count', 'freq']
    _freq = column.value_counts(normalize=True)[:n]
    summ = pd.DataFrame([_count, _freq], index=names).T

    return summ


def _summary_calc(column, by=None):
    """
    Calculates approporiate summary statistics based on data type.
    PARAMETERS
    ----------------------
    column = one column (series) of pandas df
    by = optional. stratifies summary statistics by each value in the
                column.

    RETURNS
    ----------------------
    if column data type is numeric, returns summary statistics
    if column data type is an object, returns count and frequency of
        top 5 most common values
    """
    if column.dtype == 'float64' or column.dtype == 'int64':
        coltype = 'numeric'
    elif column.dtype == 'object':
        coltype = 'object'


    if by is None:
        if coltype == 'numeric':
            summ = _numeric_summary(column)

        elif coltype == 'object':
            summ = _categorical_summary(column, 5)

    else:

        if coltype == 'numeric':
            column_list = []

            vals = by.dropna().unique()
            for value in vals:
                subcol = column[by == value]
                summcol = _numeric_summary(subcol)
                column_list.append(summcol)

            summ = pd.DataFrame(column_list, index=vals)

        elif coltype == 'object':
            subcol = column.groupby(by)
            _summ = _categorical_summary(subcol)
            summ = _summ.sort()

    return summ


def summary(data, by=None):
    """
    Displays approporiate summary statistics for each column in a line listing.

    PARAMETERS
    ----------------------
    data = pandas data frame or series

    RETURNS
    ----------------------
    for each column in the dataframe, or for hte series:
    - if column data type is numeric, returns summary statistics
    - if column data type is non-numeric, returns count and frequency of
        top 5 most common values.

    EXAMPLE
    ----------------------
    df = pd.DataFrame({'Age' : [10, 12, 14], 'Group' : ['A', 'B', 'B'] })

    In: summary(df.Age)
    Out:
        count       3
        missing     0
        min        10
        median     12
        mean       12
        std         2
        max        14
        dtype: float64

    In: summary(df.Group)
    Out:
           count      freq
        B      2  0.666667
        A      1  0.333333

    In:summary(df.Age, by=df.Group)
    Out     count  missing  min  median  mean      std  max
        A      1        0   10      10    10       NaN   10
        B      2        0   12      13    13  1.414214   14
    """
    if type(data) == pd.core.series.Series:
        summ = _summary_calc(data, by=by)
        return summ

    elif type(data) == pd.core.frame.DataFrame:
        for column in data:
            summ = _summary_calc(data[column], by=None)
            print '----------------------------------'
            print column, '\n'
            print summ

def diagnostic_accuracy(table, display=True):
    """
    Calculates the sensitivity, specificity, negative and positive predictive values
    of a 2x2 table with 95% confidence intervals. Note that confidence intervals
    are made based on a normal approximation, and may not be appropriate for
    small sample sizes.

    PARAMETERS
    ----------------------
    table = accepts pandas dataframe, numpy array, or list in [a, b, c, d] format.

    RETURNS
    ----------------------
    returns and prints diagnostic accuracy estimates and tuple of 95% confidence interval

    Author: Eric Lofgren
    """
    a, b, c, d = _ordered_table(table)

    sen = (a/(a+c))
    sen_se = np.sqrt((sen*(1-sen))/(a+c))
    sen_ci = (sen-(1.96*sen_se),sen+(1.96*sen_se))
    spec = (d/(b+d))
    spec_se = np.sqrt((spec*(1-spec))/(b+d))
    spec_ci = (spec-(1.96*spec_se),spec+(1.96*spec_se))
    PPV = (a/(a+b))
    PPV_se = np.sqrt((PPV*(1-PPV))/(a+b))
    PPV_ci = (PPV-(1.96*PPV_se),PPV+(1.96*PPV_se))
    NPV = (d/(c+d))
    NPV_se = np.sqrt((NPV*(1-NPV))/(c+d))
    NPV_ci = (NPV-(1.96*NPV_se),NPV+(1.96*NPV_se))

    if display is not False:
        print 'Sensitivity: {} (95% CI: {})\n'.format(round(sen, 2), sen_ci)
        print 'Specificity: {} (95% CI: {})\n'.format(round(spec, 2), spec_ci)
        print 'Positive Predictive Value: {} (95% CI: {})\n'.format(round(PPV, 2), PPV_ci)
        print 'Negative Predictive Value: {} (95% CI: {})\n'.format(round(NPV, 2), NPV_ci)

    return sen,sen_ci,spec,spec_ci,PPV,PPV_ci,NPV,NPV_ci

def kappa_agreement(table, display=True):
    """
    Calculated an unweighted Cohen's kappa statistic of observer agreement for a 2x2 table.
    Note that the kappa statistic can be extended to an n x m table, but this
    implementation is restricted to 2x2.

    PARAMETERS
    ----------------------
    table = accepts pandas dataframe, numpy array, or list in [a, b, c, d] format.

    RETURNS
    ----------------------
    returns and prints the Kappa statistic

    Author: Eric Lofgren
    """
    a, b, c, d = _ordered_table(table)
    n = a + b + c + d
    pr_a = ((a+d)/n)
    pr_e = (((a+b)/n) * ((a+c)/n)) + (((c+d)/n) * ((b+d)/n))
    k = (pr_a - pr_e)/(1 - pr_e)
    if display is not False:
        print "Cohen's Kappa: {}\n".format(round(k, 2))

    return k

########NEW FILE########
__FILENAME__ = basics
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
  -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
  -------------
'''

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import matplotlib as mpl

def date_convert(date, str_format='%Y-%m-%d'):
    """ Convert dates to datetime object
    """
    if type(date) == str:
        y = datetime.strptime(date, str_format)
        return y
    elif np.isnan(date) == True:
        y = np.nan
        return y
    else:
        raise ValueError('format of {} not recognized'.format(date))


def group_clusters(df, cluster_id, date_col):
    ''' Use pandas to group clusters by cluster identifier
    df = pandas dataframe
    cluster_id = column that identifies cluster membership, which can
        be a basic string like "hospital cluster A"
    date_col = onset or report date column
    '''
    clusters = df[df[date_col].notnull()]
    groups = clusters.groupby(clusters[cluster_id])

    return groups


def cluster_builder(df, cluster_id, case_id, date_col, attr_col, gen_mean, gen_sd):
    '''
    Given a line list with dates and info about cluster membership,
    this script will estimate the transmission tree of an infectious
    disease based on case onset dates.

    df = pandas dataframe of line list
    cluster_id = col that identifies cluster membership. Can be a
        basic string like "hospital cluster A"
    case_id = col with unique case identifier
    date_col = onset or report date column
    attr_col = column that will be used to color nodes based on
        attribute, e.g. case severity or gender
    gen_mean = generation time mean
    gen_sd = generation time standard deviation

    returns pandas groupby dataframe
    '''
    clusters = group_clusters(df, cluster_id, date_col)
    gen_max = timedelta((gen_mean + gen_sd), 0)

    cluster_obj = []
    for key, group in clusters:
        row = [tmp[1:4] for tmp in group[[case_id, date_col,
                attr_col]].sort(date_col, ).itertuples()]
        cluster_obj.append(row)

    network = []
    for cluster in cluster_obj:
        #reverse dates, last case first
        cluster = np.array(cluster[::-1])
        ids = cluster[:, 0]
        dates = cluster[:, 1]
        colors = cluster[:, 2]

        index_node = ids[-1]
        source_nodes = []
        for i, (date, idx) in enumerate(zip(dates, ids)):
            start_date = date - gen_max
            start_node = ids[dates >= start_date][-1]

            if start_node == idx and idx != index_node:
                start_node = ids[i+1]

            source_nodes.append(start_node)

        for i in range(len(ids)):
            result = (ids[i], colors[i], index_node, source_nodes[i], dates[i])
            network.append(result)

    df_out = pd.DataFrame(network, columns=['case_id', attr_col, 'index_node', 'source_node', 'time'])
    df_out.time = pd.to_datetime(df_out.time)

    df_out[['case_id', 'source_node', 'index_node']] = df_out[['case_id', 'source_node', 'index_node']].astype('int')
    df_out['pltdate'] = [mpl.dates.date2num(i) for i in df_out.time]
    df_out.index = df_out.case_id
    df_out = df_out.sort('pltdate')

    return df_out

########NEW FILE########
__FILENAME__ = case_tree
#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
 CASE TREE PLOT
 -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
 -------------
 Case trees are a type of plot I've developed^ to visualize clusters
 of related cases in an outbreak. They are particularly useful for
 visualizing zoonoses.

 My wish list for improvements includes:
 * add an option to include nodes that have no children, i.e. are not
   part of a human to human cluster
 * improve color choice reliabely produces an attractive color palette

 ^ I have seen similar examples in the literature,
   e.g. Antia et al (Nature 2003)
"""
from __future__ import division
from itertools import cycle
import numpy as np
import basics
import matplotlib.pyplot as plt
import networkx as nx
from random import choice, sample
from matplotlib import cm

def build_graph(df, cluster_id, case_id, date_col, color, gen_mean, gen_sd):
    """
    Generate a directed graph from data on transmission tree.
    Node color is determined by node attributes, e.g. case severity or gender.
    df = pandas dataframe
    """

    clusters = basics.cluster_builder(df=df, cluster_id=cluster_id, \
                case_id=case_id, date_col=date_col, attr_col=color, \
                gen_mean=gen_mean, gen_sd=gen_sd)

    G = nx.DiGraph()
    G.add_nodes_from(clusters['case_id'])

    edgelist = [pair for pair in clusters[['source_node']].dropna().itertuples()]
    G.add_edges_from(edgelist)
    nx.set_node_attributes(G, 'date', clusters['time'].to_dict())
    nx.set_node_attributes(G, 'pltdate', clusters['pltdate'].to_dict())
    nx.set_node_attributes(G, 'source_node', clusters['source_node'].to_dict())
    nx.set_node_attributes(G, color, clusters[color].to_dict())
    nx.set_node_attributes(G, 'index_node', clusters['index_node'].to_dict())
    G = nx.DiGraph.reverse(G)

    for i in G.nodes():
        G.node[i]['generation'] = _generations(G, i)
    
    return G


def case_tree_plot(df, cluster_id, case_id, date_col, color, \
                    gen_mean, gen_sd, node_size=100, loc='best',\
                    legend=True):
    """
    Plot casetree
    df = pandas dataframe, line listing
    cluster_id = col that identifies cluster membership. Can be a
        basic string like "hospital cluster A"
    case_id = col with unique case identifier
    date_col = onset or report date column
    color = column that will be used to color nodes based on
        attribute, e.g. case severity or gender
    gen_mean = generation time mean
    gen_sd = generation time standard deviation
    node_size = on (display node) or off (display edge only). Default is on.
    loc = legend location. See matplotlib args.
    """

    G = build_graph(df, cluster_id, case_id, date_col, color, \
                    gen_mean, gen_sd)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.xaxis_date()
    ax.set_aspect('auto')
    axprop =  ax.axis()
    ax.set_ylabel('Generations')
    ax.grid(True)
    fig.autofmt_xdate()

    coords = _layout(G)
    plt.ylim(ymin=-.05, ymax=max([val[1] for val in coords.itervalues()])+1)

    colormap, color_floats = _colors(G, color)

    if legend == True:
        x_val = G.nodes()[0]
        lines = []

        for key, value in colormap.iteritems():
            plt.scatter(G.node[x_val]['pltdate'], value[0], color=value, alpha=0)
            line = plt.Line2D(range(1), range(1), color=value, marker='o', markersize=6, alpha=.5, label=key)
            lines.append(line)

        ax.legend(lines, [k for k in colormap.iterkeys()], loc=loc)

    nx.draw_networkx(G, ax=ax, with_labels=False, pos=coords, node_color=color_floats,
                     node_size=node_size, alpha=.6)

    return fig, ax


def _colors(G, color):
    """
    Determines colors of the node based on node attribute,
	e.g. case severity or gender.
    G = networkx object
    color = name of node attribute in graph used to assign color
    """
    # collect list of unique attributes from graph
    categories = []
    for node in G.nodes():
        categories.append(G.node[node][color])

    # create color map of attributes and colors
    colors = cm.rainbow(np.linspace(0, 1, num=len(categories)*2))
    colors = sample(colors, len(categories))
    colordict = dict(zip(categories, colors))

    color_floats = []
    for node in G.nodes():
        G.node[node]['plot_color'] = colordict[G.node[node][color]]
        color_floats.append(colordict[G.node[node][color]])


    return colordict, color_floats


def _generations(G, node):
    """ Recursively determines the generation of the node, e.g. how many
    links up the chain of transmission it is.
    This value is used as the y coordinate.
    G = networkx object
    node = node in network
    """
    levels = 0

    while node != G.node[node]['source_node']:
        node = G.node[node]['source_node']
        levels += 1

    return levels


def _layout(G):
    """Determine x and y coordinates of each node.
    G = networkx object
    axprop = matplotlib axis object
    """
    np.random.seed(0)  # consistent layout between runs(?)
    positions = []

    for i in G.nodes():
        xcord = G.node[i]['pltdate']
        generation = G.node[i]['generation']
        if generation == 0:
            ygen = generation
        else:
            jittery = np.random.uniform(-.2, .2, 1)
            ygen = generation + jittery
        
        positions.append([xcord, ygen])

    return dict(zip(G, np.array(positions)))



########NEW FILE########
__FILENAME__ = checkerboard
#! /usr/bin/env python
# -*- coding: utf-8 -*-
'''
  -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
  -------------
 I developed checkerboard plots as a companion to case tree plots. A
 checkerboard plot shows when cases in a cluster occurred or were
 diagnosed, without assuming how they are related.
'''
import epipy
import matplotlib.pyplot as plt
from datetime import timedelta
from itertools import cycle
import numpy as np

def checkerboard_plot(df, case_id, cluster_id, date_col, labels='on'):
    '''
    PARAMETERS
    ---------------------
    df = pandas dataframe of line listing
    case_id = unique identifier of the cases
    cluster_id = identifier for each cluster, e.g. FamilyA
    date_col = column of onset or report dates
    labels = accepts 'on' or 'off'. Labels the first and last case in the cluster with
            the unique case identifier.

    RETURNS
    ---------------------
    matplotlib figure and axis objects
    '''
    clusters = epipy.group_clusters(df, cluster_id, date_col)

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.xaxis_date()
    ax.set_aspect('auto')
    axprop = ax.axis()
    fig.autofmt_xdate()

    grpnames = [key for key, group in clusters if len(group) > 1]
    plt.ylim(1, len(grpnames))
    plt.yticks(np.arange(len(grpnames)), grpnames)

    xtog = timedelta(((4*axprop[1]-axprop[0])/axprop[1]), 0, 0)
    counter = 0
    cols = cycle([color for i, color in enumerate(plt.rcParams['axes.color_cycle'])])

    for key, group in clusters:
        if len(group) > 1:
            color = next(cols)
            casenums = [int(num) for num in group.index]
            iter_casenums = cycle(casenums)

            positions = []

            for casedate in group[date_col].order():
                curr_casenum = next(iter_casenums)

                x1 = casedate
                x2 = casedate + xtog
                positions.append(x2)

                y1 = np.array([counter, counter])
                y2 = y1 + 1

                plt.fill_between([x1, x2], y1, y2, color=color, alpha=.3)
                ypos = y1[0] + .5

                if curr_casenum == min(casenums) or curr_casenum == max(casenums):
                    textspot = x1 + timedelta((x2 - x1).days/2.0, 0, 0)
                    plt.text(textspot, ypos, curr_casenum, horizontalalignment='center',
                    verticalalignment='center')


            counter += 1

    return fig, ax
########NEW FILE########
__FILENAME__ = data_generator
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import numpy as np
import pandas as pd
from datetime import timedelta, datetime
import itertools
import string


def _date_choice(ix_date, gen_time):
    date_rng = pd.date_range(ix_date, periods=gen_time*2, freq='D')
    date = np.random.choice(date_rng, 1)

    return date


def generate_example_data(cluster_size, outbreak_len, clusters, gen_time, attribute='sex'):
    """
    Generates example outbreak data

    PARAMETERS
    ------------------------------
    cluster_size = mean number of cases in cluster. Build in sd of 2
    outbreak_len = duration of outbreak in days
    clusters = number of clusters to begenerated
    gen_time = time between cases in a cluster
    attribute = case attribute. Options are 'sex' (returns M, F) and
                'health' (returns asymptomatic, alive, critical, dead)

    RETURNS
    ------------------------------
    pandas dataframe with columns ['ID', 'Date', 'Cluster', 'Sex']

    """
    line_list = []
    used = []
    for i in range(clusters):
        cluster_letter = np.random.choice([i for i in string.ascii_uppercase if i not in used])[0]
        cluster_name = 'Cluster' + cluster_letter
        used.append(cluster_letter)

        ix_rng = pd.date_range('1/1/2014', periods=outbreak_len, freq='D')
        ix_date = np.random.choice(ix_rng, size=1)

        rng = int(np.random.normal(cluster_size, 2, 1))
        if rng < 2:
            rng += 1

        dates = [ix_date[0]]
        for n in range(rng):
            date = _date_choice(dates[-1], gen_time)[0]
            dates.append(date)
            
            if attribute.lower() == 'sex':
                attr =  np.random.choice(['Male', 'Female'], size=1)[0]
            elif attribute.lower() == 'health':
                attr = np.random.choice(['asymptomatic', 'alive', 'critical', 'dead'], size=1)[0]

            line_list.append((len(line_list), date, cluster_name, attr))

    return pd.DataFrame(line_list, columns=['ID', 'Date', 'Cluster', attribute])

########NEW FILE########
__FILENAME__ = epicurve
#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
  -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
  -------------
 Epicurve creates weekly, monthly, or daily epicurves
 (count of new cases over time) from a line list.
'''
from __future__ import division
import epipy
from .basics import date_convert
import pandas as pd
import matplotlib.pyplot as plt


def epicurve_plot(df, date_col, freq, title=None):
    '''
    Creates an epicurve (count of new cases over time)

    df = pandas dataframe
    date_col = date used to denote case onset or report date
    freq = desired plotting frequency. Can be day, month or year
    title = optional
    date_format = datetime string format, default is "%Y-%m-%d"
    '''

    fig, ax = plt.subplots()
    
    df = df[df[date_col].isnull() == False]
    freq = freq.lower()[0]
    df.new_col = df[date_col]

    #count the number of cases per time period
    if freq == 'd':
        curve = pd.DataFrame(df[date_col].value_counts(), columns=['count'])

    elif freq == 'm':
	#convert dates to months
        format_date = df.new_col.dropna().map(lambda x: str(x.strftime("%Y/%m"))) 
        form = format_date.map(lambda x: date_convert(x, "%Y/%m"))
	#count number of cases per month
        curve = pd.DataFrame(form.value_counts(), columns=['count'])
        
    elif freq == 'y':
	#convert dates to year
        df.new_col = df.new_col.dropna().map(lambda x: x.year)
	#count number of cases per year
        curve = pd.DataFrame(df.new_col.value_counts(), columns=['count'])
        
    _plot(curve, freq, fig, ax, title)

    return curve, fig, ax


def _plot(freq_table, freq, fig, ax, title=None):
    '''
    Plot number of new cases over time
    freq_table = frequency table of cases by date, from epicurve()
    freq = inherited from epicurve
    '''
    
    axprop =  ax.axis()
    freq_table['plotdates'] = freq_table.index 

    # care about date formatting
    if freq == 'd':
        wid = ((2*axprop[1]-axprop[0])/axprop[1])
        ax.xaxis_date()
        fig.autofmt_xdate()
        
    elif freq == 'm':
        ax.xaxis_date()
        fig.autofmt_xdate()
        wid = len(freq_table)
    
    elif freq == 'y':
        locs = freq_table['plotdates'].values.tolist()
        labels = [str(loc) for loc in locs]
        wid = 1 
        ax.set_xticks(locs)
        ax.set_xticklabels(labels)
                
    ax.bar(freq_table['plotdates'].values, freq_table['count'].values,
	width=wid, align='center')
    
    if title != None:
        ax.set_title(title)

########NEW FILE########
__FILENAME__ = or_plot
# usr/bin/python
# -*- coding: utf-8 -*-

'''
  -------------
 * Caitlin Rivers
 * [cmrivers@vbi.vt.edu](cmrivers@vbi.vt.edu)
  -------------
  Modify to handle nonstring values
  '''

import pandas as pd
import matplotlib.pyplot as plt
import analyses

def _plot(_df):
    """
    """

    _df = pd.DataFrame(_df)
    df = _df.sort('ratio')
    df['color'] = 'grey'
    df.color[(df.lower > 1) & (df.upper > 1)] = 'blue'
    df.color[(df.lower < 1) & (df.upper < 1)] = 'red'

    df.index = range(len(df))  # reset the index to reflect order

    fig, ax = plt.subplots(figsize=(8, 12))
    ax.set_aspect('auto')
    ax.set_xlabel('Odds ratio')
    ax.grid(True)

    ax.set_ylim(-.5, len(df) - .5)
    plt.yticks(df.index)

    ax.scatter(df.ratio, df.index, c=df.color, s=50)
    for pos in range(len(df)):
        ax.fill_between([df.lower[pos], df.upper[pos]], pos-.01, pos+.01, color='grey', alpha=.3)

    ax.set_yticklabels(df.names)

    return fig, ax



def or_plot(df, risk_cols, outcome_col, risk_order=False):
    """
    df = pandas dataframe of line listing
    cols = list of columns to include in analysis

    # Order of operations #
    + read in dataframe or series
    + for each column
    + send to create_2x2
    + send to odds_ratio
    -plot OR on scatterplot
    -color by OR
    -plot CI on scatterplot
    """

    ratio_df = []
    cnt = 1
    for risk_col in risk_cols:
        if risk_order == False:
            risks = ["{}".format(val) for val in df[risk_col].dropna().unique()]
            outcome_order = ["{}".format(val) for val in df[outcome_col].dropna().unique()]
        else:
            outcome_order = risk_order[0]
            risks = risk_order[cnt]

        table = create_2x2(df, risk_col, outcome_col, risks, outcome_order)
        ratio, or_ci = epi.odds_ratio(table)
        ratio_df.append({'names': risk_col, 'ratio':ratio, 'lower':or_ci[0], 'upper':or_ci[1]})

        cnt += 1

    fig, ax = _plot(ratio_df)









########NEW FILE########
__FILENAME__ = rolling_proportion
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def rolling_proportion(Series, val, window=30, dropna=True, label=False, fig=None, ax=None):
    """
    Series = pandas Series with DatetimeIndex
    val = value to tally
    window = number of days to include. Default is 30.
    dropna = exclude rows where val is NaN. Default is true. False will include those rows.
    label = legend label
    fig, ax = matplotlib objects

    Example:
    datetime_df.index = df.dates
    rolling_proportion(datetime_df.sex, 'Male')
    """
    if dropna == False:
        df = pd.DataFrame(Series).fillna(False)
    else:
        df = pd.DataFrame(Series.dropna())

    df['matches'] = df == val
    df['matches'] = df['matches'].astype(np.int)
    df['ones'] = 1

    prop = pd.DataFrame(df.matches.groupby(by=df.index).sum(), columns=['numerator'])
    prop['denom'] = df.ones.groupby(by=df.index).sum()
    prop['proportion'] = pd.rolling_sum(prop.numerator, window, 5)/pd.rolling_sum(prop.denom, window, 5)

    ts = pd.date_range(min(df.index), max(df.index))

    prop = prop.reindex(ts)
    prop.proportion = prop.proportion.fillna(method='pad')

    if fig == None:
        fig, ax = plt.subplots(sharex=True)

    ax.xaxis_date()
    prop.proportion.plot(ax=ax, label=label)
    fig.autofmt_xdate()
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel('')
    if label != False:
        ax.legend()

    return fig
########NEW FILE########
__FILENAME__ = test_analyses
#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import numpy as np
import pandas as pd
import networkx as nx
import pytest
import analyses

def test_ordered_table_list():
    table = [(0, 1),
             (2, 3)]

    a, b, c, d = analyses._ordered_table(table)
    assert a == 0
    assert b == 1
    assert c == 2
    assert d == 3


def test_ordered_table_numpy():
    table = [(0, 1),
             (2, 3)]
    table = np.array(table)

    a, b, c, d = analyses._ordered_table(table)
    assert a == 0
    assert b == 1
    assert c == 2
    assert d == 3


def test_ordered_table_DataFrame():
    table = [(0, 1),
             (2, 3)]
    table = pd.DataFrame(table)

    a, b, c, d = analyses._ordered_table(table)
    assert a == 0
    assert b == 1
    assert c == 2
    assert d == 3


def test_ordered_table_typeError():
    table = [(0, 1),
             (2, 3)]
    table = np.matrix(table)

    with pytest.raises(TypeError):
        a, b, c, d = analyses._ordered_table(table)



def test_odds_ratio():
    table = [(1, 2),
             (3, 4)]

    ratio, or_ci = analyses.odds_ratio(table)

    assert np.allclose(ratio, .6667, atol=.01)
    assert np.allclose(or_ci, (0.03939, 11.28), atol=.01)


def test_relative_risk():
    table = [(1, 2),
             (3, 4)]

    rr, rr_ci = analyses.relative_risk(table)

    assert np.allclose(rr, 0.7778, atol=.01)
    assert np.allclose(rr_ci, (0.1267, 4.774), atol=.01)


def test_chi2():
    table = [(1, 2),
             (3, 4)]

    chi2, p, dof, expected = analyses.chi2(table)

    assert np.allclose(chi2, 0.1786, atol=.01)


def test_AR():
    table = [(1, 2),
             (3, 4)]

    ar, arp, par, parp = analyses.attributable_risk(table)

    assert np.allclose(ar, -.09524, atol=.01)
    assert np.allclose(arp, -28.5714, atol=.01)
    assert np.allclose(par, -.02857, atol=.01)
    assert np.allclose(parp, -7.143, atol=.01)


def test_create2x2():
    df = pd.DataFrame({'Exposed':['Y', 'Y', 'N', 'Y'], \
                          'Sick':['Y', 'N', 'N', 'Y']})
    table = analyses.create_2x2(df, 'Exposed', 'Sick', ['Y', 'N'], \
            ['Y', 'N'])

    assert table.ix[0][0] == 2
    assert table.ix[0][1] == 1
    assert table.ix[1][0] == 0
    assert table.ix[1][1] == 1


def test_2x2_errorRaises():
    df = pd.DataFrame({'Exposed':['Y', 'Y', 'N', 'Y'], \
                          'Sick':['Y', 'N', 'N', 'Y']})

    with pytest.raises(TypeError):
        table = analyses.create_2x2(df, 'Exposed', 'Sick', ['Y', 'N'], \
            'Y')

    with pytest.raises(AssertionError):
        table = analyses.create_2x2(df, 'Exposed', 'Sick', ['Y', 'N'], \
            ['Y'])

def _create_graph():
    G = nx.DiGraph()
    G.add_nodes_from([3, 4, 5])
    G.node[3]['generation'] = 0
    G.node[4]['generation'] = 1
    G.node[5]['generation'] = 1
    G.node[3]['health'] = 'alive'
    G.node[4]['health'] = 'dead'
    G.node[5]['health'] = 'alive'
    G.add_edges_from([(3, 4), (3, 5)])

    return G


def test_generation_analysis():
    G = _create_graph()
    table = analyses.generation_analysis(G, 'health', plot=False)

    assert table.ix[0][0] == 1
    assert table.ix[0][1] == 0
    assert table.ix[1][0] == 1
    assert table.ix[1][1] == 1


def test_reproduction_number_index():
    G = _create_graph()
    R = analyses.reproduction_number(G, index_cases=True, plot=False)

    assert len(R) == 3
    assert R.iget(0) == 2
    assert R.iget(1) == 0
    assert R.iget(2) == 0


def test_reproduction_number_noindex():
    G = _create_graph()
    R = analyses.reproduction_number(G, index_cases=False, plot=False)

    assert len(R) == 2
    assert R.iget(0) == 0
    assert R.iget(1) == 0


def test_numeric_summary():
    df = pd.DataFrame({'Age' : [10, 12, 14], 'Group' : ['A', 'B', 'B'] })
    summ = analyses.summary(df.Age)

    assert summ['count'] == 3
    assert summ['missing'] == 0
    assert summ['min'] == 10
    assert summ['median'] == 12
    assert summ['mean'] == 12
    assert summ['std'] == 2
    assert summ['max'] == 14


def test_categorical_summary():
    df = pd.DataFrame({'Age' : [10, 12, 14], 'Group' : ['A', 'B', 'B'] })
    summ = analyses.summary(df.Group)

    assert summ.ix[0]['count'] == 2
    assert  np.allclose(summ.ix[0]['freq'], 2/3, atol=.01)


def test_grouped_summary():
    df = pd.DataFrame({'Age' : [10, 12, 14], 'Group' : ['A', 'B', 'B'] })
    summ = analyses.summary(df.Age, df.Group)

    assert len(summ) == 2
    assert len(summ.columns) == 7





########NEW FILE########
__FILENAME__ = test_basics
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytest
import basics

def _test_data():
    _data = [(0, 'ClusterA', '2013-01-01', 'M'),
            (1, 'ClusterB', '2013-01-01', 'F'),
            (2, 'ClusterA', np.nan, 'M'),
            (3, 'ClusterC', '2013-01-04', 'F'),
            (4, 'ClusterB', '2013-01-03', 'M'),
            (5, 'ClusterB', '2013-01-05', 'M')]
    df = pd.DataFrame(_data, columns=['id', 'cluster', 'date', 'sex'])

    return df


def test_date_convert_str():
    df = _test_data()
    str_val = df.date[0]
    dtime = basics.date_convert(str_val)

    assert type(dtime) == datetime
    assert dtime == datetime(2013, 01, 01)


def test_date_convert_nan():
    df = _test_data()
    nan_val = df.date[2]
    dtime = basics.date_convert(nan_val)
    
    assert type(dtime) == float
    assert np.isnan(dtime) == True


def test_date_convert_wrongformat():
    wrong_val = '01-2012-01'

    with pytest.raises(ValueError):
        dtime = basics.date_convert(wrong_val)


def test_date_convert_wrongformat2():
    wrong_int = 01201201

    with pytest.raises(ValueError):
        dtime = basics.date_convert(wrong_int)

    
def test_group_clusters():
    df = _test_data()
    groups = basics.group_clusters(df, 'cluster', 'date')

    assert len(groups) == 3
    assert groups.groups == {'ClusterA': [0], 'ClusterB': [1, 4, 5], \
                            'ClusterC': [3]}


def test_cluster_to_tuple():
    df = _test_data()
    df['datetime'] = df['date'].map(basics.date_convert)

    df_out = basics.cluster_builder(df, 'cluster', 'id', 'datetime', \
                                    'sex', 2, 1)
    df_out = df_out.sort('case_id')

    #sanity check
    assert df_out.ix[0]['case_id'] == 0
    assert df_out.ix[3]['case_id'] == 3
    #index nodes
    assert df_out.ix[0]['index_node'] == 0
    assert df_out.ix[4]['index_node'] == 1
    #source nodes
    assert df_out.ix[5]['source_node'] == 4

    

    

########NEW FILE########
__FILENAME__ = test_casetree
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytest
import case_tree

def _test_data():
    times = pd.date_range('1/1/2013', periods=6, freq='d')
    times = times.to_datetime()
    _data = [(0, 'ClusterA',  0, 0),
            (1, 'ClusterB', 1, 1),
            (2, 'ClusterA', 0, 0),
            (3, 'ClusterA', 0, 2),
            (4, 'ClusterB', 1, 1),
            (5, 'ClusterB', 1, 4)]
    df = pd.DataFrame(_data, columns=['case_id', 'cluster', 'index_node', 'source_node'])
    df['pltdate'] = times
    
    return df


def test_build_graph_graph():
    data = _test_data()
    G = case_tree.build_graph(data, 'cluster', 'case_id', 'pltdate', 'cluster', 1, 1)

    assert len(G.node) == 6
    edges = [(0, 0), (1, 1), (0, 2), (2, 3), (1, 4), (4, 5)]
    assert len(G.edges()) == len(edges)
    for tup in G.edges():
        assert tup in edges


def test_build_graph_generation():
    data = _test_data()
    G = case_tree.build_graph(data, 'cluster', 'case_id', 'pltdate', 'cluster', 1, 1)

    assert G.node[0]['generation'] == 0
    assert G.node[1]['generation'] == 0
    assert G.node[2]['generation'] == 1
    assert G.node[3]['generation'] == 2
    assert G.node[4]['generation'] == 1
    assert G.node[5]['generation'] == 2
    




########NEW FILE########
__FILENAME__ = test_data_generator
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest
import data_generator


def test_generate_example_data():
    data = data_generator.generate_example_data(cluster_size=5, outbreak_len=180,
                clusters=10, gen_time=5, attribute='health')
    
    assert len(data.Cluster.unique()) == 10
    

########NEW FILE########
__FILENAME__ = test_epicurve_plot
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest
from random import sample
import epicurve

def _test_data():
    times = pd.date_range('12/1/2013', periods=60, freq='d')
    times = times.to_datetime()
    _data = [(0, 'ClusterA',  0, 0),
            (1, 'ClusterB', 1, 1),
            (2, 'ClusterA', 0, 0),
            (3, 'ClusterA', 0, 2),
            (4, 'ClusterB', 1, 1),
            (5, 'ClusterB', 1, 4)]
    df = pd.DataFrame(_data, columns=['case_id', 'cluster', 'index_node', 'source_node'])
    df['pltdate'] = sample(times, len(_data))
    
    return df
    

def test_epicurve_plot_month():
    data = _test_data()
    curve, fig, ax = epicurve.epicurve_plot(data, 'pltdate', 'm')
    
    assert len(curve) == 2
    assert curve['count'].sum() == 6


def test_epicurve_plot_day():
    data = _test_data()
    curve, fig, ax = epicurve.epicurve_plot(data, 'pltdate', 'd')
    
    assert len(curve) == 6
    assert curve['count'].sum() == 6


def test_epicurve_plot_year():
    data = _test_data()
    curve, fig, ax = epicurve.epicurve_plot(data, 'pltdate', 'y')
    
    assert len(curve) == 2
    assert curve['count'].sum() == 6
    
    




########NEW FILE########
