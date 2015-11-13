__FILENAME__ = columns
"""This file contains code related to "Think Stats",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import csv


def read_csv(filename, constructor):
    """Reads a CSV file, returns the header line and a list of objects.

    filename: string filename
    """
    fp = open(filename)
    reader = csv.reader(fp)

    header = reader.next()
    names = [s.lower() for s in header]

    objs = [make_object(t, names, constructor) for t in reader]
    fp.close()

    return objs


def write_csv(filename, header, data):
    """Writes a CSV file

    filename: string filename
    header: list of strings
    data: list of rows
    """
    fp = open(filename, 'w')
    writer = csv.writer(fp)
    writer.writerow(header)

    for t in data:
        writer.writerow(t)
    fp.close()


def print_cols(cols):
    """Prints the index and first two elements for each column.

    cols: list of columns
    """
    for i, col in enumerate(cols):
        print i, col[0], col[1]


def make_col_dict(cols, names):
    """Selects columns from a dataset and returns a map from name to column.

    cols: list of columns
    names: list of names
    """
    col_dict = {}
    for name, col in zip(names, cols):
        col_dict[name] = col
    return col_dict


def make_object(row, names, constructor):
    """Turns a row of values into an object.

    row: row of values
    names: list of attribute names
    constructor: function that makes the objects

    Returns: new object
    """
    obj = constructor()
    for name, val in zip(names, row):
        func = constructor.convert.get(name, int)
        try:
            val = func(val)
        except:
            pass
        setattr(obj, name, val)
    obj.clean()
    return obj


########NEW FILE########
__FILENAME__ = cookie
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Pmf

pmf = Pmf()
pmf.Set('Bowl 1', 0.5)
pmf.Set('Bowl 2', 0.5)

pmf.Mult('Bowl 1', 0.75)
pmf.Mult('Bowl 2', 0.5)

pmf.Normalize()

print pmf.Prob('Bowl 1')

########NEW FILE########
__FILENAME__ = cookie2
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Pmf


class Cookie(Pmf):
    """A map from string bowl ID to probablity."""

    def __init__(self, hypos):
        """Initialize self.

        hypos: sequence of string bowl IDs
        """
        Pmf.__init__(self)
        for hypo in hypos:
            self.Set(hypo, 1)
        self.Normalize()

    def Update(self, data):
        """Updates the PMF with new data.

        data: string cookie type
        """
        for hypo in self.Values():
            like = self.Likelihood(data, hypo)
            self.Mult(hypo, like)
        self.Normalize()

    mixes = {
        'Bowl 1':dict(vanilla=0.75, chocolate=0.25),
        'Bowl 2':dict(vanilla=0.5, chocolate=0.5),
        }

    def Likelihood(self, data, hypo):
        """The likelihood of the data under the hypothesis.

        data: string cookie type
        hypo: string bowl ID
        """
        mix = self.mixes[hypo]
        like = mix[data]
        return like


def main():
    hypos = ['Bowl 1', 'Bowl 2']

    pmf = Cookie(hypos)

    pmf.Update('vanilla')

    for hypo, prob in pmf.Items():
        print hypo, prob


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = correlation
"""This file contains code used in "Think Stats",
by Allen B. Downey, available from greenteapress.com

Copyright 2010 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math
import random

import thinkstats


def Cov(xs, ys, mux=None, muy=None):
    """Computes Cov(X, Y).

    Args:
        xs: sequence of values
        ys: sequence of values
        mux: optional float mean of xs
        muy: optional float mean of ys

    Returns:
        Cov(X, Y)
    """
    if mux is None:
        mux = thinkstats.Mean(xs)
    if muy is None:
        muy = thinkstats.Mean(ys)

    total = 0.0
    for x, y in zip(xs, ys):
        total += (x-mux) * (y-muy)

    return total / len(xs)


def Corr(xs, ys):
    """Computes Corr(X, Y).

    Args:
        xs: sequence of values
        ys: sequence of values

    Returns:
        Corr(X, Y)
    """
    xbar, varx = thinkstats.MeanVar(xs)
    ybar, vary = thinkstats.MeanVar(ys)

    corr = Cov(xs, ys, xbar, ybar) / math.sqrt(varx * vary)

    return corr


def SerialCorr(xs):
    """Computes the serial correlation of a sequence."""
    return Corr(xs[:-1], xs[1:])


def SpearmanCorr(xs, ys):
    """Computes Spearman's rank correlation.

    Args:
        xs: sequence of values
        ys: sequence of values

    Returns:
        float Spearman's correlation
    """
    xranks = MapToRanks(xs)
    yranks = MapToRanks(ys)
    return Corr(xranks, yranks)


def LeastSquares(xs, ys):
    """Computes a linear least squares fit for ys as a function of xs.

    Args:
        xs: sequence of values
        ys: sequence of values

    Returns:
        tuple of (intercept, slope)
    """
    xbar, varx = thinkstats.MeanVar(xs)
    ybar, vary = thinkstats.MeanVar(ys)

    slope = Cov(xs, ys, xbar, ybar) / varx
    inter = ybar - slope * xbar

    return inter, slope


def FitLine(xs, inter, slope):
    """Returns the fitted line for the range of xs.

    xs: x values used for the fit
    slope: estimated slope
    inter: estimated intercept
    """
    fxs = min(xs), max(xs)
    fys = [x * slope + inter for x in fxs]
    return fxs, fys


def Residuals(xs, ys, inter, slope):
    """Computes residuals for a linear fit with parameters inter and slope.

    Args:
        xs: independent variable
        ys: dependent variable
        inter: float intercept
        slope: float slope

    Returns:
        list of residuals
    """
    res = [y - inter - slope*x for x, y in zip(xs, ys)]
    return res


def CoefDetermination(ys, res):
    """Computes the coefficient of determination (R^2) for given residuals.

    Args:
        ys: dependent variable
        res: residuals
        
    Returns:
        float coefficient of determination
    """
    ybar, vary = thinkstats.MeanVar(ys)
    resbar, varres = thinkstats.MeanVar(res)
    return 1 - varres / vary


def MapToRanks(t):
    """Returns a list of ranks corresponding to the elements in t.

    Args:
        t: sequence of numbers
    
    Returns:
        list of integer ranks, starting at 1
    """
    # pair up each value with its index
    pairs = enumerate(t)
    
    # sort by value
    sorted_pairs = sorted(pairs, key=lambda pair: pair[1])

    # pair up each pair with its rank
    ranked = enumerate(sorted_pairs)

    # sort by index
    resorted = sorted(ranked, key=lambda trip: trip[1][0])

    # extract the ranks
    ranks = [trip[0]+1 for trip in resorted]
    return ranks


def CorrelatedGenerator(rho):
    """Generates standard normal variates with correlation.

    rho: target coefficient of correlation

    Returns: iterable
    """
    x = random.gauss(0, 1)
    yield x

    sigma = math.sqrt(1 - rho**2);    
    while True:
        x = random.gauss(x * rho, sigma)
        yield x


def CorrelatedNormalGenerator(mu, sigma, rho):
    """Generates normal variates with correlation.

    mu: mean of variate
    sigma: standard deviation of variate
    rho: target coefficient of correlation

    Returns: iterable
    """
    for x in CorrelatedGenerator(rho):
        yield x * sigma + mu


def main():
    pass
    

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dice
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Suite


class Dice(Suite):
    """Represents hypotheses about which die was rolled."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer number of sides on the die
        data: integer die roll
        """
        if hypo < data:
            return 0
        else:
            return 1.0/hypo


def main():
    suite = Dice([4, 6, 8, 12, 20])

    suite.Update(6)
    print 'After one 6'
    suite.Print()

    for roll in [4, 8, 7, 7, 2]:
        suite.Update(roll)

    print 'After more rolls'
    suite.Print()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = dungeons
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import random

import thinkbayes
import thinkplot

FORMATS = ['pdf', 'eps', 'png']


class Die(thinkbayes.Pmf):
    """Represents the PMF of outcomes for a die."""

    def __init__(self, sides, name=''):
        """Initializes the die.

        sides: int number of sides
        name: string
        """
        thinkbayes.Pmf.__init__(self, name=name)
        for x in xrange(1, sides+1):
            self.Set(x, 1)
        self.Normalize()


def PmfMax(pmf1, pmf2):
    """Computes the distribution of the max of values drawn from two Pmfs.

    pmf1, pmf2: Pmf objects

    returns: new Pmf
    """
    res = thinkbayes.Pmf()
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            res.Incr(max(v1, v2), p1*p2)
    return res
    

def main():
    pmf_dice = thinkbayes.Pmf()
    pmf_dice.Set(Die(4), 5)
    pmf_dice.Set(Die(6), 4)
    pmf_dice.Set(Die(8), 3)
    pmf_dice.Set(Die(12), 2)
    pmf_dice.Set(Die(20), 1)
    pmf_dice.Normalize()

    mix = thinkbayes.Pmf()
    for die, weight in pmf_dice.Items():
        for outcome, prob in die.Items():
            mix.Incr(outcome, weight*prob)

    mix = thinkbayes.MakeMixture(pmf_dice)

    colors = thinkplot.Brewer.Colors()
    thinkplot.Hist(mix, width=0.9, color=colors[4])
    thinkplot.Save(root='dungeons3',
                xlabel='Outcome',
                ylabel='Probability',
                formats=FORMATS)

    random.seed(17)

    d6 = Die(6, 'd6')

    dice = [d6] * 3
    three = thinkbayes.SampleSum(dice, 1000)
    three.name = 'sample'
    three.Print()

    three_exact = d6 + d6 + d6
    three_exact.name = 'exact'
    three_exact.Print()

    thinkplot.PrePlot(num=2)
    thinkplot.Pmf(three)
    thinkplot.Pmf(three_exact, linestyle='dashed')
    thinkplot.Save(root='dungeons1',
                xlabel='Sum of three d6',
                ylabel='Probability',
                axis=[2, 19, 0, 0.15],
                formats=FORMATS)

    thinkplot.Clf()
    thinkplot.PrePlot(num=1)
    
    # compute the distribution of the best attribute the hard way
    best_attr2 = PmfMax(three_exact, three_exact)
    best_attr4 = PmfMax(best_attr2, best_attr2)
    best_attr6 = PmfMax(best_attr4, best_attr2)
    # thinkplot.Pmf(best_attr6)

    # and the easy way
    best_attr_cdf = three_exact.Max(6)
    best_attr_cdf.name = ''
    best_attr_pmf = thinkbayes.MakePmfFromCdf(best_attr_cdf)
    best_attr_pmf.Print()

    thinkplot.Pmf(best_attr_pmf)
    thinkplot.Save(root='dungeons2',
                xlabel='Sum of three d6',
                ylabel='Probability',
                axis=[2, 19, 0, 0.23],
                formats=FORMATS)
    


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = euro
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

"""This file contains a partial solution to a problem from
MacKay, "Information Theory, Inference, and Learning Algorithms."

    Exercise 3.15 (page 50): A statistical statement appeared in
    "The Guardian" on Friday January 4, 2002:

        When spun on edge 250 times, a Belgian one-euro coin came
        up heads 140 times and tails 110.  'It looks very suspicious
        to me,' said Barry Blight, a statistics lecturer at the London
        School of Economics.  'If the coin were unbiased, the chance of
        getting a result as extreme as that would be less than 7%.'

MacKay asks, "But do these data give evidence that the coin is biased
rather than fair?"

"""

import thinkbayes
import thinkplot


class Euro(thinkbayes.Suite):
    """Represents hypotheses about the probability of heads."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer value of x, the probability of heads (0-100)
        data: string 'H' or 'T'
        """
        x = hypo / 100.0
        if data == 'H':
            return x
        else:
            return 1-x


class Euro2(thinkbayes.Suite):
    """Represents hypotheses about the probability of heads."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer value of x, the probability of heads (0-100)
        data: tuple of (number of heads, number of tails)
        """
        x = hypo / 100.0
        heads, tails = data
        like = x**heads * (1-x)**tails
        return like


def UniformPrior():
    """Makes a Suite with a uniform prior."""
    suite = Euro(xrange(0, 101))
    return suite


def TrianglePrior():
    """Makes a Suite with a triangular prior."""
    suite = Euro()
    for x in range(0, 51):
        suite.Set(x, x)
    for x in range(51, 101):
        suite.Set(x, 100-x) 
    suite.Normalize()
    return suite


def RunUpdate(suite, heads=140, tails=110):
    """Updates the Suite with the given number of heads and tails.

    suite: Suite object
    heads: int
    tails: int
    """
    dataset = 'H' * heads + 'T' * tails

    for data in dataset:
        suite.Update(data)


def Summarize(suite):
    """Prints summary statistics for the suite."""
    print suite.Prob(50)

    print 'MLE', suite.MaximumLikelihood()

    print 'Mean', suite.Mean()
    print 'Median', thinkbayes.Percentile(suite, 50) 

    print '5th %ile', thinkbayes.Percentile(suite, 5) 
    print '95th %ile', thinkbayes.Percentile(suite, 95) 

    print 'CI', thinkbayes.CredibleInterval(suite, 90)


def PlotSuites(suites, root):
    """Plots two suites.

    suite1, suite2: Suite objects
    root: string filename to write
    """
    thinkplot.Clf()
    thinkplot.PrePlot(len(suites))
    thinkplot.Pmfs(suites)

    thinkplot.Save(root=root,
                   xlabel='x',
                   ylabel='Probability',
                   formats=['pdf', 'eps'])


def main():
    # make the priors
    suite1 = UniformPrior()
    suite1.name = 'uniform'

    suite2 = TrianglePrior()
    suite2.name = 'triangle'

    # plot the priors
    PlotSuites([suite1, suite2], 'euro2')

    # update
    RunUpdate(suite1)
    Summarize(suite1)

    RunUpdate(suite2)
    Summarize(suite2)

    # plot the posteriors
    PlotSuites([suite1], 'euro1')
    PlotSuites([suite1, suite2], 'euro3')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = euro2
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

"""This file contains a partial solution to a problem from
MacKay, "Information Theory, Inference, and Learning Algorithms."

    Exercise 3.15 (page 50): A statistical statement appeared in
    "The Guardian" on Friday January 4, 2002:

        When spun on edge 250 times, a Belgian one-euro coin came
        up heads 140 times and tails 110.  'It looks very suspicious
        to me,' said Barry Blight, a statistics lecturer at the London
        School of Economics.  'If the coin were unbiased, the chance of
        getting a result as extreme as that would be less than 7%.'

MacKay asks, "But do these data give evidence that the coin is biased
rather than fair?"

"""

import thinkbayes
import thinkplot


class Euro(thinkbayes.Suite):
    """Represents hypotheses about the probability of heads."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer value of x, the probability of heads (0-100)
        data: string 'H' or 'T'
        """
        x = hypo / 100.0
        if data == 'H':
            return x
        else:
            return 1-x


class Euro2(thinkbayes.Suite):
    """Represents hypotheses about the probability of heads."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer value of x, the probability of heads (0-100)
        data: tuple of (number of heads, number of tails)
        """
        x = hypo / 100.0
        heads, tails = data
        like = x**heads * (1-x)**tails
        return like


def Version1():
    suite = Euro(xrange(0, 101))
    heads, tails = 140, 110
    dataset = 'H' * heads + 'T' * tails

    for data in dataset:
        suite.Update(data)

    return suite


def Version2():
    suite = Euro(xrange(0, 101))
    heads, tails = 140, 110
    dataset = 'H' * heads + 'T' * tails

    suite.UpdateSet(dataset)
    return suite


def Version3():
    suite = Euro2(xrange(0, 101))
    heads, tails = 140, 110

    suite.Update((heads, tails))
    return suite


def main():

    suite = Version3()
    print suite.Mean()

    thinkplot.Pmf(suite)
    thinkplot.Show()
    


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = euro3
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

"""This file contains a partial solution to a problem from
MacKay, "Information Theory, Inference, and Learning Algorithms."

    Exercise 3.15 (page 50): A statistical statement appeared in
    "The Guardian" on Friday January 4, 2002:

        When spun on edge 250 times, a Belgian one-euro coin came
        up heads 140 times and tails 110.  'It looks very suspicious
        to me,' said Barry Blight, a statistics lecturer at the London
        School of Economics.  'If the coin were unbiased, the chance of
        getting a result as extreme as that would be less than 7%.'

MacKay asks, "But do these data give evidence that the coin is biased
rather than fair?"

"""

import thinkbayes


class Euro(thinkbayes.Suite):
    """Represents hypotheses about the probability of heads."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: integer value of x, the probability of heads (0-100)
        data: tuple of (number of heads, number of tails)
        """
        x = hypo / 100.0
        heads, tails = data
        like = x**heads * (1-x)**tails
        return like


def TrianglePrior():
    """Makes a Suite with a triangular prior."""
    suite = Euro()
    for x in range(0, 51):
        suite.Set(x, x)
    for x in range(51, 101):
        suite.Set(x, 100-x) 
    suite.Normalize()
    return suite


def SuiteLikelihood(suite, data):
    """Computes the weighted average of likelihoods for sub-hypotheses.

    suite: Suite that maps sub-hypotheses to probability
    data: some representation of the data
   
    returns: float likelihood
    """
    total = 0
    for hypo, prob in suite.Items():
        like = suite.Likelihood(data, hypo)
        total += prob * like
    return total


def Main():
    data = 140, 110
    data = 8, 12

    suite = Euro()
    like_f = suite.Likelihood(data, 50)
    print 'p(D|F)', like_f

    actual_percent = 100.0 * 140 / 250
    likelihood = suite.Likelihood(data, actual_percent)
    print 'p(D|B_cheat)', likelihood
    print 'p(D|B_cheat) / p(D|F)', likelihood / like_f

    like40 = suite.Likelihood(data, 40)
    like60 = suite.Likelihood(data, 60)
    likelihood = 0.5 * like40 + 0.5 * like60
    print 'p(D|B_two)', likelihood
    print 'p(D|B_two) / p(D|F)', likelihood / like_f

    b_uniform = Euro(xrange(0, 101))
    b_uniform.Remove(50)
    b_uniform.Normalize()
    likelihood = SuiteLikelihood(b_uniform, data)
    print 'p(D|B_uniform)', likelihood
    print 'p(D|B_uniform) / p(D|F)', likelihood / like_f

    b_tri = TrianglePrior()
    b_tri.Remove(50)
    b_tri.Normalize()
    likelihood = b_tri.Update(data)
    print 'p(D|B_tri)', likelihood
    print 'p(D|B_tri) / p(D|F)', likelihood / like_f


if __name__ == '__main__':
    Main()

########NEW FILE########
__FILENAME__ = hockey
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math

import columns
import thinkbayes
import thinkstats
import thinkplot


USE_SUMMARY_DATA = True

class Hockey(thinkbayes.Suite):
    """Represents hypotheses about the scoring rate for a team."""

    def __init__(self, name=''):
        """Initializes the Hockey object.

        name: string
        """
        if USE_SUMMARY_DATA:
            # prior based on each team's average goals scored
            mu = 2.8
            sigma = 0.3
        else:
            # prior based on each pair-wise match-up
            mu = 2.8
            sigma = 0.85

        pmf = thinkbayes.MakeGaussianPmf(mu, sigma, 4)
        thinkbayes.Suite.__init__(self, pmf, name=name)
            
    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        Evaluates the Poisson PMF for lambda and k.

        hypo: goal scoring rate in goals per game
        data: goals scored in one period
        """
        lam = hypo
        k = data
        like = thinkbayes.EvalPoissonPmf(k, lam)
        return like


def MakeGoalPmf(suite, high=10):
    """Makes the distribution of goals scored, given distribution of lam.

    suite: distribution of goal-scoring rate
    high: upper bound

    returns: Pmf of goals per game
    """
    metapmf = thinkbayes.Pmf()

    for lam, prob in suite.Items():
        pmf = thinkbayes.MakePoissonPmf(lam, high)
        metapmf.Set(pmf, prob)

    mix = thinkbayes.MakeMixture(metapmf, name=suite.name)
    return mix


def MakeGoalTimePmf(suite):
    """Makes the distribution of time til first goal.

    suite: distribution of goal-scoring rate

    returns: Pmf of goals per game
    """
    metapmf = thinkbayes.Pmf()

    for lam, prob in suite.Items():
        pmf = thinkbayes.MakeExponentialPmf(lam, high=2, n=2001)
        metapmf.Set(pmf, prob)

    mix = thinkbayes.MakeMixture(metapmf, name=suite.name)
    return mix


class Game(object):
    """Represents a game.

    Attributes are set in columns.read_csv.
    """
    convert = dict()

    def clean(self):
        self.goals = self.pd1 + self.pd2 + self.pd3


def ReadHockeyData(filename='hockey_data.csv'):
    """Read game scores from the data file.

    filename: string
    """
    game_list = columns.read_csv(filename, Game)

    # map from gameID to list of two games
    games = {}
    for game in game_list:
        if game.season != 2011:
            continue
        key = game.game
        games.setdefault(key, []).append(game)

    # map from (team1, team2) to (score1, score2)
    pairs = {}
    for key, pair in games.iteritems():
        t1, t2 = pair
        key = t1.team, t2.team
        entry = t1.total, t2.total
        pairs.setdefault(key, []).append(entry)

    ProcessScoresTeamwise(pairs)
    ProcessScoresPairwise(pairs)


def ProcessScoresPairwise(pairs):
    """Average number of goals for each team against each opponent.

    pairs: map from (team1, team2) to (score1, score2)
    """
    # map from (team1, team2) to list of goals scored
    goals_scored = {}
    for key, entries in pairs.iteritems():
        t1, t2 = key
        for entry in entries:
            g1, g2 = entry
            goals_scored.setdefault((t1, t2), []).append(g1)
            goals_scored.setdefault((t2, t1), []).append(g2)

    # make a list of average goals scored
    lams = []
    for key, goals in goals_scored.iteritems():
        if len(goals) < 3:
            continue
        lam = thinkstats.Mean(goals)
        lams.append(lam)

    # make the distribution of average goals scored
    cdf = thinkbayes.MakeCdfFromList(lams)
    thinkplot.Cdf(cdf)
    thinkplot.Show()

    mu, var = thinkstats.MeanVar(lams)
    print 'mu, sig', mu, math.sqrt(var)

    print 'BOS v VAN', pairs['BOS', 'VAN']


def ProcessScoresTeamwise(pairs):
    """Average number of goals for each team.

    pairs: map from (team1, team2) to (score1, score2)
    """
    # map from team to list of goals scored
    goals_scored = {}
    for key, entries in pairs.iteritems():
        t1, t2 = key
        for entry in entries:
            g1, g2 = entry
            goals_scored.setdefault(t1, []).append(g1)
            goals_scored.setdefault(t2, []).append(g2)

    # make a list of average goals scored
    lams = []
    for key, goals in goals_scored.iteritems():
        lam = thinkstats.Mean(goals)
        lams.append(lam)

    # make the distribution of average goals scored
    cdf = thinkbayes.MakeCdfFromList(lams)
    thinkplot.Cdf(cdf)
    thinkplot.Show()

    mu, var = thinkstats.MeanVar(lams)
    print 'mu, sig', mu, math.sqrt(var)


def main():
    #ReadHockeyData()
    #return

    formats = ['pdf', 'eps']

    suite1 = Hockey('bruins')
    suite2 = Hockey('canucks')

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    thinkplot.Pmf(suite1)
    thinkplot.Pmf(suite2)
    thinkplot.Save(root='hockey0',
                xlabel='Goals per game',
                ylabel='Probability',
                formats=formats)

    suite1.UpdateSet([0, 2, 8, 4])
    suite2.UpdateSet([1, 3, 1, 0])

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    thinkplot.Pmf(suite1)
    thinkplot.Pmf(suite2)
    thinkplot.Save(root='hockey1',
                xlabel='Goals per game',
                ylabel='Probability',
                formats=formats)


    goal_dist1 = MakeGoalPmf(suite1)
    goal_dist2 = MakeGoalPmf(suite2)

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    thinkplot.Pmf(goal_dist1)
    thinkplot.Pmf(goal_dist2)
    thinkplot.Save(root='hockey2',
                xlabel='Goals',
                ylabel='Probability',
                formats=formats)

    time_dist1 = MakeGoalTimePmf(suite1)    
    time_dist2 = MakeGoalTimePmf(suite2)
 
    print 'MLE bruins', suite1.MaximumLikelihood()
    print 'MLE canucks', suite2.MaximumLikelihood()
   
    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    thinkplot.Pmf(time_dist1)
    thinkplot.Pmf(time_dist2)    
    thinkplot.Save(root='hockey3',
                   xlabel='Games until goal',
                   ylabel='Probability',
                   formats=formats)

    diff = goal_dist1 - goal_dist2
    p_win = diff.ProbGreater(0)
    p_loss = diff.ProbLess(0)
    p_tie = diff.Prob(0)

    print p_win, p_loss, p_tie

    p_overtime = thinkbayes.PmfProbLess(time_dist1, time_dist2)
    p_adjust = thinkbayes.PmfProbEqual(time_dist1, time_dist2)
    p_overtime += p_adjust / 2
    print 'p_overtime', p_overtime 

    print p_overtime * p_tie
    p_win += p_overtime * p_tie
    print 'p_win', p_win

    # win the next two
    p_series = p_win**2

    # split the next two, win the third
    p_series += 2 * p_win * (1-p_win) * p_win

    print 'p_series', p_series


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = kidney
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math
import numpy
import random
import sys

import correlation
import thinkplot
import matplotlib.pyplot as pyplot
import thinkbayes


INTERVAL = 245/365.0
FORMATS = ['pdf', 'eps']
MINSIZE = 0.2
MAXSIZE = 20
BUCKET_FACTOR = 10


def log2(x, denom=math.log(2)):
    """Computes log base 2."""
    return math.log(x) / denom


def SimpleModel():
    """Runs calculations based on a simple model."""

    # time between discharge and diagnosis, in days
    interval = 3291.0

    # doubling time in linear measure is doubling time in volume * 3
    dt = 811.0 * 3

    # number of doublings since discharge
    doublings = interval / dt

    # how big was the tumor at time of discharge (diameter in cm)
    d1 = 15.5
    d0 = d1 / 2.0 ** doublings

    print 'interval (days)', interval
    print 'interval (years)', interval / 365
    print 'dt', dt
    print 'doublings', doublings
    print 'd1', d1
    print 'd0', d0

    # assume an initial linear measure of 0.1 cm
    d0 = 0.1
    d1 = 15.5

    # how many doublings would it take to get from d0 to d1
    doublings = log2(d1 / d0)

    # what linear doubling time does that imply?
    dt = interval / doublings

    print 'doublings', doublings
    print 'dt', dt

    # compute the volumetric doubling time and RDT
    vdt = dt / 3
    rdt = 365 / vdt

    print 'vdt', vdt
    print 'rdt', rdt

    cdf = MakeCdf()
    p = cdf.Prob(rdt)
    print 'Prob{RDT > 2.4}', 1-p


def MakeCdf():
    """Uses the data from Zhang et al. to construct a CDF."""
    n = 53.0
    freqs = [0, 2, 31, 42, 48, 51, 52, 53]
    ps = [freq/n for freq in freqs]
    xs = numpy.arange(-1.5, 6.5, 1.0)

    cdf = thinkbayes.Cdf(xs, ps)
    return cdf


def PlotCdf(cdf):
    """Plots the actual and fitted distributions.

    cdf: CDF object
    """
    xs, ps = cdf.xs, cdf.ps
    cps = [1-p for p in ps]

    # CCDF on logy scale: shows exponential behavior
    thinkplot.Clf()
    thinkplot.Plot(xs, cps, 'bo-')
    thinkplot.Save(root='kidney1',
                formats=FORMATS,
                xlabel='RDT',
                ylabel='CCDF (log scale)',
                yscale='log')

    # CDF, model and data

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    mxs, mys = ModelCdf()
    thinkplot.Plot(mxs, mys, label='model', linestyle='dashed') 

    thinkplot.Plot(xs, ps, 'gs', label='data')
    thinkplot.Save(root='kidney2',
                formats=FORMATS,
                xlabel='RDT (volume doublings per year)',
                ylabel='CDF',
                title='Distribution of RDT',
                axis=[-2, 7, 0, 1],
                loc=4)


def QQPlot(cdf, fit):
    """Makes a QQPlot of the values from actual and fitted distributions.

    cdf: actual Cdf of RDT
    fit: model
    """
    xs = [-1.5, 5.5]
    thinkplot.Clf()
    thinkplot.Plot(xs, xs, 'b-')

    xs, ps = cdf.xs, cdf.ps
    fs = [fit.Value(p) for p in ps]

    thinkplot.Plot(xs, fs, 'gs')
    thinkplot.Save(root = 'kidney3',
                formats=FORMATS,
                xlabel='Actual',
                ylabel='Model')
    

def FitCdf(cdf):
    """Fits a line to the log CCDF and returns the slope.

    cdf: Cdf of RDT
    """
    xs, ps = cdf.xs, cdf.ps
    cps = [1-p for p in ps]

    xs = xs[1:-1]
    lcps = [math.log(p) for p in cps[1:-1]]
    
    _inter, slope = correlation.LeastSquares(xs, lcps)
    return -slope


def CorrelatedGenerator(cdf, rho):
    """Generates a sequence of values from cdf with correlation.

    Generates a correlated standard Gaussian series, then transforms to
    values from cdf

    cdf: distribution to choose from
    rho: target coefficient of correlation
    """
    def Transform(x):
        """Maps from a Gaussian variate to a variate with the given CDF."""
        p = thinkbayes.GaussianCdf(x)
        y = cdf.Value(p)
        return y

    # for the first value, choose from a Gaussian and transform it
    x = random.gauss(0, 1)
    yield Transform(x)

    # for subsequent values, choose from the conditional distribution
    # based on the previous value
    sigma = math.sqrt(1 - rho**2)
    while True:
        x = random.gauss(x * rho, sigma)
        yield Transform(x)


def UncorrelatedGenerator(cdf, _rho=None):
    """Generates a sequence of values from cdf with no correlation.

    Ignores rho, which is accepted as a parameter to provide the
    same interface as CorrelatedGenerator

    cdf: distribution to choose from
    rho: ignored
    """
    while True:
        x = cdf.Random()
        yield x


def RdtGenerator(cdf, rho):
    """Returns an iterator with n values from cdf and the given correlation.

    cdf: Cdf object
    rho: coefficient of correlation
    """
    if rho == 0.0:
        return UncorrelatedGenerator(cdf)
    else:
        return CorrelatedGenerator(cdf, rho)


def GenerateRdt(pc, lam1, lam2):
    """Generate an RDT from a mixture of exponential distributions.

    With prob pc, generate a negative value with param lam2;
    otherwise generate a positive value with param lam1.
    """
    if random.random() < pc:
        return -random.expovariate(lam2)
    else:
        return random.expovariate(lam1)


def GenerateSample(n, pc, lam1, lam2):
    """Generates a sample of RDTs.

    n: sample size
    pc: probablity of negative growth
    lam1: exponential parameter of positive growth
    lam2: exponential parameter of negative growth

    Returns: list of random variates
    """
    xs = [GenerateRdt(pc, lam1, lam2) for _ in xrange(n)]
    return xs


def GenerateCdf(n=1000, pc=0.35, lam1=0.79, lam2=5.0):
    """Generates a sample of RDTs and returns its CDF.

    n: sample size
    pc: probablity of negative growth
    lam1: exponential parameter of positive growth
    lam2: exponential parameter of negative growth

    Returns: Cdf of generated sample
    """
    xs = GenerateSample(n, pc, lam1, lam2)
    cdf = thinkbayes.MakeCdfFromList(xs)
    return cdf


def ModelCdf(pc=0.35, lam1=0.79, lam2=5.0):
    """

    pc: probablity of negative growth
    lam1: exponential parameter of positive growth
    lam2: exponential parameter of negative growth

    Returns: list of xs, list of ys
    """
    cdf = thinkbayes.EvalExponentialCdf
    x1 = numpy.arange(-2, 0, 0.1)
    y1 = [pc * (1 - cdf(-x, lam2)) for x in x1]
    x2 = numpy.arange(0, 7, 0.1)
    y2 = [pc + (1-pc) * cdf(x, lam1) for x in x2]
    return list(x1) + list(x2), y1+y2


def BucketToCm(y, factor=BUCKET_FACTOR):
    """Computes the linear dimension for a given bucket.

    t: bucket number
    factor: multiplicitive factor from one bucket to the next

    Returns: linear dimension in cm
    """
    return math.exp(y / factor)


def CmToBucket(x, factor=BUCKET_FACTOR):
    """Computes the bucket for a given linear dimension.

    x: linear dimension in cm
    factor: multiplicitive factor from one bucket to the next

    Returns: float bucket number
    """
    return round(factor * math.log(x))


def Diameter(volume, factor=3/math.pi/4, exp=1/3.0):
    """Converts a volume to a diameter.

    d = 2r = 2 * (3/4/pi V)^1/3
    """
    return 2 * (factor * volume) ** exp


def Volume(diameter, factor=4*math.pi/3):
    """Converts a diameter to a volume.

    V = 4/3 pi (d/2)^3
    """
    return factor * (diameter/2.0)**3


class Cache(object):
    """Records each observation point for each tumor."""

    def __init__(self):
        """Initializes the cache.

        joint: map from (age, bucket) to frequency
        sequences: map from bucket to a list of sequences
        initial_rdt: sequence of (V0, rdt) pairs
        """
        self.joint = thinkbayes.Joint()
        self.sequences = {}
        self.initial_rdt = []

    def GetBuckets(self):
        """Returns an iterator for the keys in the cache."""
        return self.sequences.iterkeys()

    def GetSequence(self, bucket):
        """Looks up a bucket in the cache."""
        return self.sequences[bucket]

    def ConditionalCdf(self, bucket, name=''):
        """Forms the cdf of ages for a given bucket.

        bucket: int bucket number
        name: string
        """
        pmf = self.joint.Conditional(0, 1, bucket, name=name)
        cdf = pmf.MakeCdf()
        return cdf

    def ProbOlder(self, cm, age):
        """Computes the probability of exceeding age, given size.

        cm: size in cm
        age: age in years
        """
        bucket = CmToBucket(cm)
        cdf = self.ConditionalCdf(bucket)
        p = cdf.Prob(age)
        return 1-p

    def GetDistAgeSize(self, size_thresh=MAXSIZE):
        """Gets the joint distribution of age and size.

        Map from (age, log size in cm) to log freq
        
        Returns: new Pmf object
        """
        joint = thinkbayes.Joint()

        for val, freq in self.joint.Items():
            age, bucket = val
            cm = BucketToCm(bucket)
            if cm > size_thresh:
                continue
            log_cm = math.log10(cm)
            joint.Set((age, log_cm), math.log(freq) * 10)

        return joint

    def Add(self, age, seq, rdt):
        """Adds this observation point to the cache.

        age: age of the tumor in years
        seq: sequence of volumes
        rdt: RDT during this interval
        """
        final = seq[-1]
        cm = Diameter(final)
        bucket = CmToBucket(cm)
        self.joint.Incr((age, bucket))

        self.sequences.setdefault(bucket, []).append(seq)

        initial = seq[-2]
        self.initial_rdt.append((initial, rdt))

    def Print(self):
        """Prints the size (cm) for each bucket, and the number of sequences."""
        for bucket in sorted(self.GetBuckets()):
            ss = self.GetSequence(bucket)
            diameter = BucketToCm(bucket)
            print diameter, len(ss)
        
    def Correlation(self):
        """Computes the correlation between log volumes and rdts."""
        vs, rdts = zip(*self.initial_rdt)
        lvs = [math.log(v) for v in vs]
        return correlation.Corr(lvs, rdts)


class Calculator(object):
    """Encapsulates the state of the computation."""

    def __init__(self):
        """Initializes the cache."""
        self.cache = Cache()

    def MakeSequences(self, n, rho, cdf):
        """Returns a list of sequences of volumes.

        n: number of sequences to make
        rho: serial correlation
        cdf: Cdf of rdts

        Returns: list of n sequences of volumes
        """
        sequences = []
        for i in range(n):
            rdt_seq = RdtGenerator(cdf, rho)
            seq = self.MakeSequence(rdt_seq)
            sequences.append(seq)

            if i % 100 == 0:
                print i

        return sequences

    def MakeSequence(self, rdt_seq, v0=0.01, interval=INTERVAL, 
                     vmax=Volume(MAXSIZE)):
        """Simulate the growth of a tumor.

        rdt_seq: sequence of rdts
        v0: initial volume in mL (cm^3)
        interval: timestep in years
        vmax: volume to stop at

        Returns: sequence of volumes
        """
        seq = v0,
        age = 0

        for rdt in rdt_seq:
            age += interval
            final, seq = self.ExtendSequence(age, seq, rdt, interval)
            if final > vmax:
                break

        return seq

    def ExtendSequence(self, age, seq, rdt, interval):
        """Generates a new random value and adds it to the end of seq.

        Side-effect: adds sub-sequences to the cache.

        age: age of tumor at the end of this interval
        seq: sequence of values so far
        rdt: reciprocal doubling time in doublings per year
        interval: timestep in years

        Returns: final volume, extended sequence
        """
        initial = seq[-1]
        doublings = rdt * interval
        final = initial * 2**doublings
        new_seq = seq + (final,)
        self.cache.Add(age, new_seq, rdt)

        return final, new_seq

    def PlotBucket(self, bucket, color='blue'):
        """Plots the set of sequences for the given bucket.

        bucket: int bucket number
        color: string
        """
        sequences = self.cache.GetSequence(bucket)
        for seq in sequences:
            n = len(seq)
            age = n * INTERVAL
            ts = numpy.linspace(-age, 0, n)
            PlotSequence(ts, seq, color)

    def PlotBuckets(self):
        """Plots the set of sequences that ended in a given bucket."""
        # 2.01, 4.95 cm, 9.97 cm
        buckets = [7.0, 16.0, 23.0]
        buckets = [23.0]
        colors = ['blue', 'green', 'red', 'cyan']

        thinkplot.Clf()
        for bucket, color in zip(buckets, colors):
            self.PlotBucket(bucket, color)

        thinkplot.Save(root='kidney5',
                    formats=FORMATS,
                    title='History of simulated tumors',
                    axis=[-40, 1, MINSIZE, 12],
                    xlabel='years',
                    ylabel='diameter (cm, log scale)',
                    yscale='log')

    def PlotJointDist(self):
        """Makes a pcolor plot of the age-size joint distribution."""
        thinkplot.Clf()

        joint = self.cache.GetDistAgeSize()
        thinkplot.Contour(joint, contour=False, pcolor=True)

        thinkplot.Save(root='kidney8',
                    formats=FORMATS,
                    axis=[0, 41, -0.7, 1.31],
                    yticks=MakeLogTicks([0.2, 0.5, 1, 2, 5, 10, 20]),
                    xlabel='ages',
                    ylabel='diameter (cm, log scale)')

    def PlotConditionalCdfs(self):
        """Plots the cdf of ages for each bucket."""
        buckets = [7.0, 16.0, 23.0, 27.0]
        # 2.01, 4.95 cm, 9.97 cm, 14.879 cm
        names = ['2 cm', '5 cm', '10 cm', '15 cm']
        cdfs = []

        for bucket, name in zip(buckets, names):
            cdf = self.cache.ConditionalCdf(bucket, name)
            cdfs.append(cdf)

        thinkplot.Clf()
        thinkplot.PrePlot(num=len(cdfs))
        thinkplot.Cdfs(cdfs)
        thinkplot.Save(root='kidney6',
                    title='Distribution of age for several diameters',
                    formats=FORMATS,
                    xlabel='tumor age (years)',
                    ylabel='CDF',
                    loc=4)

    def PlotCredibleIntervals(self, xscale='linear'):
        """Plots the confidence interval for each bucket."""
        xs = []
        ts = []
        percentiles = [95, 75, 50, 25, 5]
        min_size = 0.3

        # loop through the buckets, accumulate
        # xs: sequence of sizes in cm
        # ts: sequence of percentile tuples
        for _, bucket in enumerate(sorted(self.cache.GetBuckets())):
            cm = BucketToCm(bucket)
            if cm < min_size or cm > 20.0:
                continue
            xs.append(cm)
            cdf = self.cache.ConditionalCdf(bucket)      
            ps = [cdf.Percentile(p) for p in percentiles]
            ts.append(ps)

        # dump the results into a table
        fp = open('kidney_table.tex', 'w')
        PrintTable(fp, xs, ts)
        fp.close()

        # make the figure
        linewidths = [1, 2, 3, 2, 1]
        alphas = [0.3, 0.5, 1, 0.5, 0.3]
        labels = ['95th', '75th', '50th', '25th', '5th']

        # transpose the ts so we have sequences for each percentile rank
        thinkplot.Clf()
        yys = zip(*ts)

        for ys, linewidth, alpha, label in zip(yys, linewidths, alphas, labels):
            options = dict(color='blue', linewidth=linewidth, 
                                alpha=alpha, label=label, markersize=2)

            # plot the data points
            thinkplot.Plot(xs, ys, 'bo', **options)

            # plot the fit lines
            fxs = [min_size, 20.0]
            fys = FitLine(xs, ys, fxs)

            thinkplot.Plot(fxs, fys, **options)

            # put a label at the end of each line
            x, y = fxs[-1], fys[-1]
            pyplot.text(x*1.05, y, label, color='blue',
                        horizontalalignment='left',
                        verticalalignment='center')

        # make the figure
        thinkplot.Save(root='kidney7',
                       formats=FORMATS,
                       title='Credible interval for age vs diameter',
                       xlabel='diameter (cm, log scale)',
                       ylabel='tumor age (years)',
                       xscale=xscale,
                       xticks=MakeTicks([0.5, 1, 2, 5, 10, 20]),
                       axis=[0.25, 35, 0, 45],
                       legend=False,
                       )


def PlotSequences(sequences):
    """Plots linear measurement vs time.

    sequences: list of sequences of volumes
    """
    thinkplot.Clf()

    options = dict(color='gray', linewidth=1, linestyle='dashed')
    thinkplot.Plot([0, 40], [10, 10], **options)

    for seq in sequences:
        n = len(seq)
        age = n * INTERVAL
        ts = numpy.linspace(0, age, n)
        PlotSequence(ts, seq)

    thinkplot.Save(root='kidney4',
                   formats=FORMATS,
                   axis=[0, 40, MINSIZE, 20],
                   title='Simulations of tumor growth',
                   xlabel='tumor age (years)',
                   yticks=MakeTicks([0.2, 0.5, 1, 2, 5, 10, 20]),
                   ylabel='diameter (cm, log scale)',
                   yscale='log')


def PlotSequence(ts, seq, color='blue'):
    """Plots a time series of linear measurements.

    ts: sequence of times in years
    seq: sequence of columes
    color: color string
    """
    options = dict(color=color, linewidth=1, alpha=0.2)
    xs = [Diameter(v) for v in seq]

    thinkplot.Plot(ts, xs, **options)


def PrintCI(fp, cm, ps):
    """Writes a line in the LaTeX table.

    fp: file pointer
    cm: diameter in cm
    ts: tuples of percentiles
    """
    fp.write('%0.1f' % round(cm, 1))
    for p in reversed(ps):
        fp.write(' & %0.1f ' % round(p, 1))
    fp.write(r'\\' '\n')


def PrintTable(fp, xs, ts):
    """Writes the data in a LaTeX table.

    fp: file pointer
    xs: diameters in cm
    ts: sequence of tuples of percentiles
    """
    fp.write(r'\begin{tabular}{|r||r|r|r|r|r|}' '\n')
    fp.write(r'\hline' '\n')
    fp.write(r'Diameter   & \multicolumn{5}{c|}{Percentiles of age} \\' '\n')
    fp.write(r'(cm)   & 5th & 25th & 50th & 75th & 95th \\' '\n')
    fp.write(r'\hline' '\n')

    for i, (cm, ps) in enumerate(zip(xs, ts)):
        #print cm, ps
        if i % 3 == 0:
            PrintCI(fp, cm, ps)

    fp.write(r'\hline' '\n')
    fp.write(r'\end{tabular}' '\n')


def FitLine(xs, ys, fxs):
    """Fits a line to the xs and ys, and returns fitted values for fxs.

    Applies a log transform to the xs.

    xs: diameter in cm
    ys: age in years
    fxs: diameter in cm
    """
    lxs = [math.log(x) for x in xs]
    inter, slope = correlation.LeastSquares(lxs, ys)
    # res = correlation.Residuals(lxs, ys, inter, slope)
    # r2 = correlation.CoefDetermination(ys, res)

    lfxs = [math.log(x) for x in fxs]
    fys = [inter + slope * x for x in lfxs]
    return fys


def MakeTicks(xs):
    """Makes a pair of sequences for use as pyplot ticks.

    xs: sequence of floats

    Returns (xs, labels), where labels is a sequence of strings.
    """
    labels = [str(x) for x in xs]
    return xs, labels


def MakeLogTicks(xs):
    """Makes a pair of sequences for use as pyplot ticks.

    xs: sequence of floats

    Returns (xs, labels), where labels is a sequence of strings.
    """
    lxs = [math.log10(x) for x in xs]
    labels = [str(x) for x in xs]
    return lxs, labels


def TestCorrelation(cdf):
    """Tests the correlated generator.

    Makes sure that the sequence has the right distribution and correlation.
    """
    n = 10000
    rho = 0.4

    rdt_seq = CorrelatedGenerator(cdf, rho)
    xs = [rdt_seq.next() for _ in range(n)]
    
    rho2 = correlation.SerialCorr(xs)
    print rho, rho2
    cdf2 = thinkbayes.MakeCdfFromList(xs)

    thinkplot.Cdfs([cdf, cdf2])
    thinkplot.Show()


def main(script):
    for size in [1, 5, 10]:
        bucket = CmToBucket(size)
        print 'Size, bucket', size, bucket

    SimpleModel()

    random.seed(17)

    cdf = MakeCdf()

    lam1 = FitCdf(cdf)
    fit = GenerateCdf(lam1=lam1)

    # TestCorrelation(fit)

    PlotCdf(cdf)
    # QQPlot(cdf, fit)

    calc = Calculator()
    rho = 0.0
    sequences = calc.MakeSequences(100, rho, fit)
    PlotSequences(sequences)

    calc.PlotBuckets()

    _ = calc.MakeSequences(1900, rho, fit)
    print 'V0-RDT correlation', calc.cache.Correlation()

    print '15.5 Probability age > 8 year', calc.cache.ProbOlder(15.5, 8)
    print '6.0 Probability age > 8 year', calc.cache.ProbOlder(6.0, 8)

    calc.PlotConditionalCdfs()

    calc.PlotCredibleIntervals(xscale='log')

    calc.PlotJointDist()


if __name__ == '__main__':
    main(*sys.argv)



########NEW FILE########
__FILENAME__ = monty
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Pmf


class Monty(Pmf):
    """Map from string location of car to probability"""

    def __init__(self, hypos):
        """Initialize the distribution.

        hypos: sequence of hypotheses
        """
        Pmf.__init__(self)
        for hypo in hypos:
            self.Set(hypo, 1)
        self.Normalize()

    def Update(self, data):
        """Updates each hypothesis based on the data.

        data: any representation of the data
        """
        for hypo in self.Values():
            like = self.Likelihood(data, hypo)
            self.Mult(hypo, like)
        self.Normalize()

    def Likelihood(self, data, hypo):
        """Compute the likelihood of the data under the hypothesis.

        hypo: string name of the door where the prize is
        data: string name of the door Monty opened
        """
        if hypo == data:
            return 0
        elif hypo == 'A':
            return 0.5
        else:
            return 1


def main():
    hypos = 'ABC'
    pmf = Monty(hypos)

    data = 'B'
    pmf.Update(data)

    for hypo, prob in sorted(pmf.Items()):
        print hypo, prob


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = monty2
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Suite


class Monty(Suite):
    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: string name of the door where the prize is
        data: string name of the door Monty opened
        """
        if hypo == data:
            return 0
        elif hypo == 'A':
            return 0.5
        else:
            return 1


def main():
    suite = Monty('ABC')
    suite.Update('B')
    suite.Print()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = myplot
"""This file contains code for use with "Think Stats",
by Allen B. Downey, available from greenteapress.com

Copyright 2010 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math
import matplotlib
import matplotlib.pyplot as pyplot
import numpy as np

# customize some matplotlib attributes
#matplotlib.rc('figure', figsize=(4, 3))

#matplotlib.rc('font', size=14.0)
#matplotlib.rc('axes', labelsize=22.0, titlesize=22.0)
#matplotlib.rc('legend', fontsize=20.0)

#matplotlib.rc('xtick.major', size=6.0)
#matplotlib.rc('xtick.minor', size=3.0)

#matplotlib.rc('ytick.major', size=6.0)
#matplotlib.rc('ytick.minor', size=3.0)


class Brewer(object):
    """Encapsulates a nice sequence of colors.

    Shades of blue that look good in color and can be distinguished
    in grayscale (up to a point).
    
    Borrowed from http://colorbrewer2.org/
    """
    color_iter = None

    colors = ['#081D58',
              '#253494',
              '#225EA8',
              '#1D91C0',
              '#41B6C4',
              '#7FCDBB',
              '#C7E9B4',
              '#EDF8B1',
              '#FFFFD9']

    # lists that indicate which colors to use depending on how many are used
    which_colors = [[],
                    [1],
                    [1, 3],
                    [0, 2, 4],
                    [0, 2, 4, 6],
                    [0, 2, 3, 5, 6],
                    [0, 2, 3, 4, 5, 6],
                    [0, 1, 2, 3, 4, 5, 6],
                    ]

    @classmethod
    def Colors(cls):
        """Returns the list of colors.
        """
        return cls.colors

    @classmethod
    def ColorGenerator(cls, n):
        """Returns an iterator of color strings.

        n: how many colors will be used
        """
        for i in cls.which_colors[n]:
            yield cls.colors[i]
        raise StopIteration('Ran out of colors in Brewer.ColorGenerator')

    @classmethod
    def InitializeIter(cls, num):
        """Initializes the color iterator with the given number of colors."""
        cls.color_iter = cls.ColorGenerator(num)

    @classmethod
    def ClearIter(cls):
        """Sets the color iterator to None."""
        cls.color_iter = None

    @classmethod
    def GetIter(cls):
        """Gets the color iterator."""
        return cls.color_iter


def PrePlot(num=None, rows=1, cols=1):
    """Takes hints about what's coming.

    num: number of lines that will be plotted
    """
    if num:
        Brewer.InitializeIter(num)

    # TODO: get sharey and sharex working.  probably means switching
    # to subplots instead of subplot.
    # also, get rid of the gray background.

    if rows > 1 or cols > 1:
        pyplot.subplots(rows, cols, sharey=True)
        global SUBPLOT_ROWS, SUBPLOT_COLS
        SUBPLOT_ROWS = rows
        SUBPLOT_COLS = cols
    

def SubPlot(plot_number):
    pyplot.subplot(SUBPLOT_ROWS, SUBPLOT_COLS, plot_number)


class InfiniteList(list):
    """A list that returns the same value for all indices."""
    def __init__(self, val):
        """Initializes the list.

        val: value to be stored
        """
        list.__init__(self)
        self.val = val

    def __getitem__(self, index):
        """Gets the item with the given index.

        index: int

        returns: the stored value
        """
        return self.val


def Underride(d, **options):
    """Add key-value pairs to d only if key is not in d.

    If d is None, create a new dictionary.

    d: dictionary
    options: keyword args to add to d
    """
    if d is None:
        d = {}

    for key, val in options.iteritems():
        d.setdefault(key, val)

    return d


def Clf():
    """Clears the figure and any hints that have been set."""
    Brewer.ClearIter()
    pyplot.clf()
    

def Figure(**options):
    """Sets options for the current figure."""
    Underride(options, figsize=(6, 8))
    pyplot.figure(**options)
    

def Plot(xs, ys, style='', **options):
    """Plots a line.

    Args:
      xs: sequence of x values
      ys: sequence of y values
      style: style string passed along to pyplot.plot
      options: keyword args passed to pyplot.plot
    """
    color_iter = Brewer.GetIter()

    if color_iter:
        try:
            options = Underride(options, color=color_iter.next())
        except StopIteration:
            print 'Warning: Brewer ran out of colors.'
            Brewer.ClearIter()
        
    options = Underride(options, linewidth=3, alpha=0.8)
    pyplot.plot(xs, ys, style, **options)


def Scatter(xs, ys, **options):
    """Makes a scatter plot.

    xs: x values
    ys: y values
    options: options passed to pyplot.scatter
    """
    options = Underride(options, color='blue', alpha=0.2, 
                        s=30, edgecolors='none')
    pyplot.scatter(xs, ys, **options)


def Pmf(pmf, **options):
    """Plots a Pmf or Hist as a line.

    Args:
      pmf: Hist or Pmf object
      options: keyword args passed to pyplot.plot
    """
    xs, ps = pmf.Render()
    if pmf.name:
        options = Underride(options, label=pmf.name)
    Plot(xs, ps, **options)


def Pmfs(pmfs, **options):
    """Plots a sequence of PMFs.

    Options are passed along for all PMFs.  If you want different
    options for each pmf, make multiple calls to Pmf.
    
    Args:
      pmfs: sequence of PMF objects
      options: keyword args passed to pyplot.plot
    """
    for pmf in pmfs:
        Pmf(pmf, **options)


def Hist(hist, **options):
    """Plots a Pmf or Hist with a bar plot.

    Args:
      hist: Hist or Pmf object
      options: keyword args passed to pyplot.bar
    """
    # find the minimum distance between adjacent values
    xs, fs = hist.Render()
    width = min(Diff(xs))

    if hist.name:
        options = Underride(options, label=hist.name)

    options = Underride(options, 
                        align='center',
                        linewidth=0,
                        width=width)

    pyplot.bar(xs, fs, **options)


def Hists(hists, **options):
    """Plots two histograms as interleaved bar plots.

    Options are passed along for all PMFs.  If you want different
    options for each pmf, make multiple calls to Pmf.

    Args:
      hists: list of two Hist or Pmf objects
      options: keyword args passed to pyplot.plot
    """
    for hist in hists:
        Hist(hist, **options)


def Diff(t):
    """Compute the differences between adjacent elements in a sequence.

    Args:
        t: sequence of number

    Returns:
        sequence of differences (length one less than t)
    """
    diffs = [t[i+1] - t[i] for i in range(len(t)-1)]
    return diffs


def Cdf(cdf, complement=False, transform=None, **options):
    """Plots a CDF as a line.

    Args:
      cdf: Cdf object
      complement: boolean, whether to plot the complementary CDF
      transform: string, one of 'exponential', 'pareto', 'weibull', 'gumbel'
      options: keyword args passed to pyplot.plot

    Returns:
      dictionary with the scale options that should be passed to
      myplot.Save or myplot.Show
    """
    xs, ps = cdf.Render()
    scale = dict(xscale='linear', yscale='linear')

    if transform == 'exponential':
        complement = True
        scale['yscale'] = 'log'

    if transform == 'pareto':
        complement = True
        scale['yscale'] = 'log'
        scale['xscale'] = 'log'

    if complement:
        ps = [1.0-p for p in ps]

    if transform == 'weibull':
        xs.pop()
        ps.pop()
        ps = [-math.log(1.0-p) for p in ps]
        scale['xscale'] = 'log'
        scale['yscale'] = 'log'

    if transform == 'gumbel':
        xs.pop(0)
        ps.pop(0)
        ps = [-math.log(p) for p in ps]
        scale['yscale'] = 'log'

    if cdf.name:
        options = Underride(options, label=cdf.name)

    Plot(xs, ps, **options)
    return scale


def Cdfs(cdfs, complement=False, transform=None, **options):
    """Plots a sequence of CDFs.
    
    cdfs: sequence of CDF objects
    complement: boolean, whether to plot the complementary CDF
    transform: string, one of 'exponential', 'pareto', 'weibull', 'gumbel'
    options: keyword args passed to pyplot.plot
    """
    for cdf in cdfs:
        Cdf(cdf, complement, transform, **options)


def Contour(obj, pcolor=False, contour=True, imshow=False, **options):
    """Makes a contour plot.
    
    d: map from (x, y) to z, or object that provides GetDict
    pcolor: boolean, whether to make a pseudocolor plot
    contour: boolean, whether to make a contour plot
    imshow: boolean, whether to use pyplot.imshow
    options: keyword args passed to pyplot.pcolor and/or pyplot.contour
    """
    try:
        d = obj.GetDict()
    except AttributeError:
        d = obj

    Underride(options, linewidth=3, cmap=matplotlib.cm.Blues)

    xs, ys = zip(*d.iterkeys())
    xs = sorted(set(xs))
    ys = sorted(set(ys))

    X, Y = np.meshgrid(xs, ys)
    func = lambda x, y: d.get((x, y), 0)
    func = np.vectorize(func)
    Z = func(X, Y)

    x_formatter = matplotlib.ticker.ScalarFormatter(useOffset=False)
    axes = pyplot.gca()
    axes.xaxis.set_major_formatter(x_formatter)

    if pcolor:
        pyplot.pcolormesh(X, Y, Z, **options)
    if contour:
        cs = pyplot.contour(X, Y, Z, **options)
        pyplot.clabel(cs, inline=1, fontsize=10)
    if imshow:
        extent = xs[0], xs[-1], ys[0], ys[-1]
        pyplot.imshow(Z, extent=extent, **options)
        

def Pcolor(xs, ys, zs, pcolor=True, contour=False, **options):
    """Makes a pseudocolor plot.
    
    xs:
    ys:
    zs:
    pcolor: boolean, whether to make a pseudocolor plot
    contour: boolean, whether to make a contour plot
    options: keyword args passed to pyplot.pcolor and/or pyplot.contour
    """
    Underride(options, linewidth=3, cmap=matplotlib.cm.Blues)

    X, Y = np.meshgrid(xs, ys)
    Z = zs

    x_formatter = matplotlib.ticker.ScalarFormatter(useOffset=False)
    axes = pyplot.gca()
    axes.xaxis.set_major_formatter(x_formatter)

    if pcolor:
        pyplot.pcolormesh(X, Y, Z, **options)

    if contour:
        cs = pyplot.contour(X, Y, Z, **options)
        pyplot.clabel(cs, inline=1, fontsize=10)
        

def Config(**options):
    """Configures the plot.

    Pulls options out of the option dictionary and passes them to
    title, xlabel, ylabel, xscale, yscale, xticks, yticks, axis, legend,
    and loc.
    """
    title = options.get('title', '')
    pyplot.title(title)

    xlabel = options.get('xlabel', '')
    pyplot.xlabel(xlabel)

    ylabel = options.get('ylabel', '')
    pyplot.ylabel(ylabel)

    if 'xscale' in options:
        pyplot.xscale(options['xscale'])

    if 'xticks' in options:
        pyplot.xticks(options['xticks'])

    if 'yscale' in options:
        pyplot.yscale(options['yscale'])

    if 'yticks' in options:
        pyplot.yticks(options['yticks'])

    if 'axis' in options:
        pyplot.axis(options['axis'])

    loc = options.get('loc', 0)
    legend = options.get('legend', True)
    if legend:
        pyplot.legend(loc=loc)


def Show(**options):
    """Shows the plot.

    For options, see Config.

    options: keyword args used to invoke various pyplot functions
    """
    # TODO: figure out how to show more than one plot
    Config(**options)
    pyplot.show()


def Save(root=None, formats=None, **options):
    """Saves the plot in the given formats.

    For options, see Config.

    Args:
      root: string filename root
      formats: list of string formats
      options: keyword args used to invoke various pyplot functions
    """
    Config(**options)

    if formats is None:
        formats = ['pdf', 'eps']

    if root:
        for fmt in formats:
            SaveFormat(root, fmt)
    Clf()


def SaveFormat(root, fmt='eps'):
    """Writes the current figure to a file in the given format.

    Args:
      root: string filename root
      fmt: string format
    """
    filename = '%s.%s' % (root, fmt)
    print 'Writing', filename
    pyplot.savefig(filename, format=fmt, dpi=300)


# provide aliases for calling functons with lower-case names
preplot = PrePlot
subplot = SubPlot
clf = Clf
figure = Figure
plot = Plot
scatter = Scatter
pmf = Pmf
pmfs = Pmfs
hist = Hist
hists = Hists
diff = Diff
cdf = Cdf
cdfs = Cdfs
contour = Contour
pcolor = Pcolor
config = Config
show = Show
save = Save


def main():
    color_iter = Brewer.ColorGenerator(7)
    for color in color_iter:
        print color

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = m_and_m
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from thinkbayes import Suite


class M_and_M(Suite):
    """Map from hypothesis (A or B) to probability."""

    mix94 = dict(brown=30,
                 yellow=20,
                 red=20,
                 green=10,
                 orange=10,
                 tan=10)

    mix96 = dict(blue=24,
                 green=20,
                 orange=16,
                 yellow=14,
                 red=13,
                 brown=13)

    hypoA = dict(bag1=mix94, bag2=mix96)
    hypoB = dict(bag1=mix96, bag2=mix94)

    hypotheses = dict(A=hypoA, B=hypoB)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: string hypothesis (A or B)
        data: tuple of string bag, string color
        """
        bag, color = data
        mix = self.hypotheses[hypo][bag]
        like = mix[color]
        return like


def main():
    suite = M_and_M('AB')

    suite.Update(('bag1', 'yellow'))
    suite.Update(('bag2', 'green'))

    suite.Print()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = paintball
"""This file contains code used in "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import thinkbayes

import matplotlib.pyplot as pyplot
import thinkplot

import math
import sys


FORMATS = ['pdf', 'eps', 'png']


def StrafingSpeed(alpha, beta, x):
    """Computes strafing speed, given location of shooter and impact.

    alpha: x location of shooter
    beta: y location of shooter
    x: location of impact

    Returns: derivative of x with respect to theta
    """
    theta = math.atan2(x - alpha, beta)
    speed = beta / math.cos(theta)**2
    return speed


def MakeLocationPmf(alpha, beta, locations):
    """Computes the Pmf of the locations, given alpha and beta. 

    Given that the shooter is at coordinates (alpha, beta),
    the probability of hitting any spot is inversely proportionate
    to the strafe speed.

    alpha: x position
    beta: y position
    locations: x locations where the pmf is evaluated

    Returns: Pmf object
    """
    pmf = thinkbayes.Pmf()
    for x in locations:
        prob = 1.0 / StrafingSpeed(alpha, beta, x)
        pmf.Set(x, prob)
    pmf.Normalize()
    return pmf


class Paintball(thinkbayes.Suite, thinkbayes.Joint):
    """Represents hypotheses about the location of an opponent."""

    def __init__(self, alphas, betas, locations):
        """Makes a joint suite of parameters alpha and beta.

        Enumerates all pairs of alpha and beta.
        Stores locations for use in Likelihood.

        alphas: possible values for alpha
        betas: possible values for beta
        locations: possible locations along the wall
        """
        self.locations = locations
        pairs = [(alpha, beta) 
                 for alpha in alphas 
                 for beta in betas]
        thinkbayes.Suite.__init__(self, pairs)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: pair of alpha, beta
        data: location of a hit

        Returns: float likelihood
        """
        alpha, beta = hypo
        x = data
        pmf = MakeLocationPmf(alpha, beta, self.locations)
        like = pmf.Prob(x)
        return like


def MakePmfPlot(alpha = 10):
    """Plots Pmf of location for a range of betas."""
    locations = range(0, 31)

    betas = [10, 20, 40]
    thinkplot.PrePlot(num=len(betas))

    for beta in betas:
        pmf = MakeLocationPmf(alpha, beta, locations)
        pmf.name = 'beta = %d' % beta
        thinkplot.Pmf(pmf)

    thinkplot.Save('paintball1',
                xlabel='Distance',
                ylabel='Prob',
                formats=FORMATS)


def MakePosteriorPlot(suite):
    """Plots the posterior marginal distributions for alpha and beta.

    suite: posterior joint distribution of location
    """
    marginal_alpha = suite.Marginal(0)
    marginal_alpha.name = 'alpha'
    marginal_beta = suite.Marginal(1)
    marginal_beta.name = 'beta'

    print 'alpha CI', marginal_alpha.CredibleInterval(50)
    print 'beta CI', marginal_beta.CredibleInterval(50)

    thinkplot.PrePlot(num=2)

    #thinkplot.Pmf(marginal_alpha)
    #thinkplot.Pmf(marginal_beta)
    
    thinkplot.Cdf(thinkbayes.MakeCdfFromPmf(marginal_alpha))
    thinkplot.Cdf(thinkbayes.MakeCdfFromPmf(marginal_beta))
    
    thinkplot.Save('paintball2',
                xlabel='Distance',
                ylabel='Prob',
                loc=4,
                formats=FORMATS)


def MakeConditionalPlot(suite):
    """Plots marginal CDFs for alpha conditioned on beta.

    suite: posterior joint distribution of location
    """    
    betas = [10, 20, 40]
    thinkplot.PrePlot(num=len(betas))

    for beta in betas:
        cond = suite.Conditional(0, 1, beta)
        cond.name = 'beta = %d' % beta
        thinkplot.Pmf(cond)

    thinkplot.Save('paintball3',
                xlabel='Distance',
                ylabel='Prob',
                formats=FORMATS)


def MakeContourPlot(suite):
    """Plots the posterior joint distribution as a contour plot.

    suite: posterior joint distribution of location
    """
    thinkplot.Contour(suite.GetDict(), contour=False, pcolor=True)

    thinkplot.Save('paintball4',
                xlabel='alpha',
                ylabel='beta',
                axis=[0, 30, 0, 20],
                formats=FORMATS)


def MakeCrediblePlot(suite):
    """Makes a plot showing several two-dimensional credible intervals.

    suite: Suite
    """
    d = dict((pair, 0) for pair in suite.Values())

    percentages = [75, 50, 25]
    for p in percentages:
        interval = suite.MaxLikeInterval(p)
        for pair in interval:
            d[pair] += 1

    thinkplot.Contour(d, contour=False, pcolor=True)
    pyplot.text(17, 4, '25', color='white')
    pyplot.text(17, 15, '50', color='white')
    pyplot.text(17, 30, '75')

    thinkplot.Save('paintball5',
                xlabel='alpha',
                ylabel='beta',
                formats=FORMATS)


def main(script):

    alphas = range(0, 31)
    betas = range(1, 51)
    locations = range(0, 31)

    suite = Paintball(alphas, betas, locations)
    suite.UpdateSet([15, 16, 18, 21])

    MakeCrediblePlot(suite)

    MakeContourPlot(suite)

    MakePosteriorPlot(suite)

    MakeConditionalPlot(suite)

    MakePmfPlot()


if __name__ == '__main__':
    main(*sys.argv)

########NEW FILE########
__FILENAME__ = price
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2013 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import csv
import numpy
import thinkbayes
import thinkplot

import matplotlib.pyplot as pyplot


FORMATS = ['png', 'pdf', 'eps']


def ReadData(filename='showcases.2011.csv'):
    """Reads a CSV file of data.

    Args:
      filename: string filename

    Returns: sequence of (price1 price2 bid1 bid2 diff1 diff2) tuples
    """
    fp = open(filename)
    reader = csv.reader(fp)
    res = []

    for t in reader:
        _heading = t[0]
        data = t[1:]
        try:
            data = [int(x) for x in data]
            # print heading, data[0], len(data)
            res.append(data)
        except ValueError:
            pass

    fp.close()
    return zip(*res)
    

class Price(thinkbayes.Suite):
    """Represents hypotheses about the price of a showcase."""

    def __init__(self, pmf, player, name=''):
        """Constructs the suite.

        pmf: prior distribution of price
        player: Player object
        name: string
        """
        thinkbayes.Suite.__init__(self, pmf, name=name)
        self.player = player

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: actual price
        data: the contestant's guess
        """
        price = hypo
        guess = data

        error = price - guess
        like = self.player.ErrorDensity(error)

        return like


class GainCalculator(object):
    """Encapsulates computation of expected gain."""

    def __init__(self, player, opponent):
        """Constructs the calculator.

        player: Player
        opponent: Player
        """
        self.player = player
        self.opponent = opponent

    def ExpectedGains(self, low=0, high=75000, n=101):
        """Computes expected gains for a range of bids.

        low: low bid
        high: high bid
        n: number of bids to evaluates

        returns: tuple (sequence of bids, sequence of gains)
    
        """
        bids = numpy.linspace(low, high, n)

        gains = [self.ExpectedGain(bid) for bid in bids]

        return bids, gains

    def ExpectedGain(self, bid):
        """Computes the expected return of a given bid.

        bid: your bid
        """
        suite = self.player.posterior
        total = 0
        for price, prob in sorted(suite.Items()):
            gain = self.Gain(bid, price)
            total += prob * gain
        return total

    def Gain(self, bid, price):
        """Computes the return of a bid, given the actual price.

        bid: number
        price: actual price
        """
        # if you overbid, you get nothing
        if bid > price:
            return 0

        # otherwise compute the probability of winning
        diff = price - bid
        prob = self.ProbWin(diff)

        # if you are within 250 dollars, you win both showcases
        if diff <= 250:
            return 2 * price * prob
        else:
            return price * prob

    def ProbWin(self, diff):
        """Computes the probability of winning for a given diff.

        diff: how much your bid was off by
        """
        prob = (self.opponent.ProbOverbid() + 
                self.opponent.ProbWorseThan(diff))
        return prob


class Player(object):
    """Represents a player on The Price is Right."""

    n = 101
    price_xs = numpy.linspace(0, 75000, n)

    def __init__(self, prices, bids, diffs):
        """Construct the Player.

        prices: sequence of prices
        bids: sequence of bids
        diffs: sequence of underness (negative means over)
        """
        self.pdf_price = thinkbayes.EstimatedPdf(prices)
        self.cdf_diff = thinkbayes.MakeCdfFromList(diffs)

        mu = 0
        sigma = numpy.std(diffs)
        self.pdf_error = thinkbayes.GaussianPdf(mu, sigma)

    def ErrorDensity(self, error):
        """Density of the given error in the distribution of error.

        error: how much the bid is under the actual price
        """
        return self.pdf_error.Density(error)

    def PmfPrice(self):
        """Returns a new Pmf of prices.

        A discrete version of the estimated Pdf.
        """
        return self.pdf_price.MakePmf(self.price_xs)

    def CdfDiff(self):
        """Returns a reference to the Cdf of differences (underness).
        """
        return self.cdf_diff

    def ProbOverbid(self):
        """Returns the probability this player overbids.
        """
        return self.cdf_diff.Prob(-1)

    def ProbWorseThan(self, diff):
        """Probability this player's diff is greater than the given diff.

        diff: how much the oppenent is off by (always positive)
        """
        return 1 - self.cdf_diff.Prob(diff)

    def MakeBeliefs(self, guess):
        """Makes a posterior distribution based on estimated price.

        Sets attributes prior and posterior.

        guess: what the player thinks the showcase is worth        
        """
        pmf = self.PmfPrice()
        self.prior = Price(pmf, self, name='prior')
        self.posterior = self.prior.Copy(name='posterior')
        self.posterior.Update(guess)

    def OptimalBid(self, guess, opponent):
        """Computes the bid that maximizes expected return.
        
        guess: what the player thinks the showcase is worth 
        opponent: Player

        Returns: (optimal bid, expected gain)
        """
        self.MakeBeliefs(guess)
        calc = GainCalculator(self, opponent)
        bids, gains = calc.ExpectedGains()
        gain, bid = max(zip(gains, bids))
        return bid, gain

    def PlotBeliefs(self, root):
        """Plots prior and posterior beliefs.

        root: string filename root for saved figure
        """
        thinkplot.Clf()
        thinkplot.PrePlot(num=2)
        thinkplot.Pmfs([self.prior, self.posterior])
        thinkplot.Save(root=root,
                    xlabel='price ($)',
                    ylabel='PMF',
                    formats=FORMATS)


def MakePlots(player1, player2):
    """Generates two plots.

    price1 shows the priors for the two players
    price2 shows the distribution of diff for the two players
    """

    # plot the prior distribution of price for both players
    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    pmf1 = player1.PmfPrice()
    pmf1.name = 'showcase 1'
    pmf2 = player2.PmfPrice()
    pmf2.name = 'showcase 2'
    thinkplot.Pmfs([pmf1, pmf2])
    thinkplot.Save(root='price1',
                xlabel='price ($)',
                ylabel='PDF',
                formats=FORMATS)

    # plot the historical distribution of underness for both players
    thinkplot.Clf()
    thinkplot.PrePlot(num=2)
    cdf1 = player1.CdfDiff()
    cdf1.name = 'player 1'
    cdf2 = player2.CdfDiff()
    cdf2.name = 'player 2'

    print 'Player median', cdf1.Percentile(50)
    print 'Player median', cdf2.Percentile(50)

    print 'Player 1 overbids', player1.ProbOverbid()
    print 'Player 2 overbids', player2.ProbOverbid()

    thinkplot.Cdfs([cdf1, cdf2])
    thinkplot.Save(root='price2',
                xlabel='diff ($)',
                ylabel='CDF',
                formats=FORMATS)


def MakePlayers():
    """Reads data and makes player objects."""
    data = ReadData(filename='showcases.2011.csv')
    data += ReadData(filename='showcases.2012.csv')

    cols = zip(*data)
    price1, price2, bid1, bid2, diff1, diff2 = cols

    # print list(sorted(price1))
    # print len(price1)

    player1 = Player(price1, bid1, diff1)
    player2 = Player(price2, bid2, diff2)

    return player1, player2


def PlotExpectedGains(guess1=20000, guess2=40000):
    """Plots expected gains as a function of bid.

    guess1: player1's estimate of the price of showcase 1
    guess2: player2's estimate of the price of showcase 2
    """
    player1, player2 = MakePlayers()
    MakePlots(player1, player2)

    player1.MakeBeliefs(guess1)
    player2.MakeBeliefs(guess2)

    print 'Player 1 prior mle', player1.prior.MaximumLikelihood()
    print 'Player 2 prior mle', player2.prior.MaximumLikelihood()
    print 'Player 1 mean', player1.posterior.Mean()
    print 'Player 2 mean', player2.posterior.Mean()
    print 'Player 1 mle', player1.posterior.MaximumLikelihood()
    print 'Player 2 mle', player2.posterior.MaximumLikelihood()

    player1.PlotBeliefs('price3')
    player2.PlotBeliefs('price4')

    calc1 = GainCalculator(player1, player2)
    calc2 = GainCalculator(player2, player1)

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)

    bids, gains = calc1.ExpectedGains()
    thinkplot.Plot(bids, gains, label='Player 1')
    print 'Player 1 optimal bid', max(zip(gains, bids))

    bids, gains = calc2.ExpectedGains()
    thinkplot.Plot(bids, gains, label='Player 2')
    print 'Player 2 optimal bid', max(zip(gains, bids))

    thinkplot.Save(root='price5',
                xlabel='bid ($)',
                ylabel='expected gain ($)',
                formats=FORMATS)


def PlotOptimalBid():
    """Plots optimal bid vs estimated price.
    """
    player1, player2 = MakePlayers()
    guesses = numpy.linspace(15000, 60000, 21)

    res = []
    for guess in guesses:
        player1.MakeBeliefs(guess)

        mean = player1.posterior.Mean()
        mle = player1.posterior.MaximumLikelihood()

        calc = GainCalculator(player1, player2)
        bids, gains = calc.ExpectedGains()
        gain, bid = max(zip(gains, bids))

        res.append((guess, mean, mle, gain, bid))

    guesses, means, _mles, gains, bids = zip(*res)
    
    thinkplot.PrePlot(num=3)
    pyplot.plot([15000, 60000], [15000, 60000], color='gray')
    thinkplot.Plot(guesses, means, label='mean')
    #thinkplot.Plot(guesses, mles, label='MLE')
    thinkplot.Plot(guesses, bids, label='bid')
    thinkplot.Plot(guesses, gains, label='gain')
    thinkplot.Save(root='price6',
                   xlabel='guessed price ($)',
                   formats=FORMATS)


def TestCode(calc):
    """Check some intermediate results.

    calc: GainCalculator
    """
    # test ProbWin
    for diff in [0, 100, 1000, 10000, 20000]:
        print diff, calc.ProbWin(diff)
    print

    # test Return
    price = 20000
    for bid in [17000, 18000, 19000, 19500, 19800, 20001]:
        print bid, calc.Gain(bid, price)
    print


def main():
    PlotExpectedGains()
    PlotOptimalBid()



if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = redline
"""This file contains code used in "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2013 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import thinkbayes

import thinkplot
import numpy

import math
import random
import sys

FORMATS = ['pdf', 'eps', 'png', 'jpg']

"""
Notation guide:

z: time between trains
x: time since the last train
y: time until the next train

zb: distribution of z as seen by a random arrival

"""

# longest hypothetical time between trains, in seconds

UPPER_BOUND = 1200

# observed gaps between trains, in seconds
# collected using code in redline_data.py, run daily 4-6pm
# for 5 days, Monday 6 May 2013 to Friday 10 May 2013

OBSERVED_GAP_TIMES = [
    428.0, 705.0, 407.0, 465.0, 433.0, 425.0, 204.0, 506.0, 143.0, 351.0, 
    450.0, 598.0, 464.0, 749.0, 341.0, 586.0, 754.0, 256.0, 378.0, 435.0, 
    176.0, 405.0, 360.0, 519.0, 648.0, 374.0, 483.0, 537.0, 578.0, 534.0, 
    577.0, 619.0, 538.0, 331.0, 186.0, 629.0, 193.0, 360.0, 660.0, 484.0, 
    512.0, 315.0, 457.0, 404.0, 740.0, 388.0, 357.0, 485.0, 567.0, 160.0, 
    428.0, 387.0, 901.0, 187.0, 622.0, 616.0, 585.0, 474.0, 442.0, 499.0, 
    437.0, 620.0, 351.0, 286.0, 373.0, 232.0, 393.0, 745.0, 636.0, 758.0,
]


def BiasPmf(pmf, name='', invert=False):
    """Returns the Pmf with oversampling proportional to value.

    If pmf is the distribution of true values, the result is the
    distribution that would be seen if values are oversampled in
    proportion to their values; for example, if you ask students
    how big their classes are, large classes are oversampled in
    proportion to their size.

    If invert=True, computes in inverse operation; for example,
    unbiasing a sample collected from students.

    Args:
      pmf: Pmf object.
      name: string name for the new Pmf.
      invert: boolean

     Returns:
       Pmf object
    """
    new_pmf = pmf.Copy(name=name)

    for x in pmf.Values():
        if invert:
            new_pmf.Mult(x, 1.0/x)
        else:
            new_pmf.Mult(x, x)
        
    new_pmf.Normalize()
    return new_pmf


def UnbiasPmf(pmf, name=''):
    """Returns the Pmf with oversampling proportional to 1/value.

    Args:
      pmf: Pmf object.
      name: string name for the new Pmf.

     Returns:
       Pmf object
    """
    return BiasPmf(pmf, name, invert=True)


def MakeUniformPmf(low, high):
    """Make a uniform Pmf.

    low: lowest value (inclusive)
    high: highest value (inclusive)
    """
    pmf = thinkbayes.Pmf()
    for x in MakeRange(low=low, high=high):
        pmf.Set(x, 1)
    pmf.Normalize()
    return pmf    
    

def MakeRange(low=10, high=None, skip=10):
    """Makes a range representing possible gap times in seconds.

    low: where to start
    high: where to end
    skip: how many to skip
    """
    if high is None:
        high = UPPER_BOUND

    return range(low, high+skip, skip)


class WaitTimeCalculator(object):
    """Encapsulates the forward inference process.

    Given the actual distribution of gap times (z),
    computes the distribution of gaps as seen by
    a random passenger (zb), which yields the distribution
    of wait times (y) and the distribution of elapsed times (x).
    """

    def __init__(self, pmf, inverse=False):
        """Constructor.

        pmf: Pmf of either z or zb
        inverse: boolean, true if pmf is zb, false if pmf is z
        """
        if inverse:
            self.pmf_zb = pmf
            self.pmf_z = UnbiasPmf(pmf, name="z")
        else:
            self.pmf_z = pmf
            self.pmf_zb = BiasPmf(pmf, name="zb")

        # distribution of wait time
        self.pmf_y = PmfOfWaitTime(self.pmf_zb)

        # the distribution of elapsed time is the same as the
        # distribution of wait time
        self.pmf_x = self.pmf_y

    def GenerateSampleWaitTimes(self, n):
        """Generates a random sample of wait times.

        n: sample size

        Returns: sequence of values
        """
        cdf_y = thinkbayes.MakeCdfFromPmf(self.pmf_y)
        sample = cdf_y.Sample(n)
        return sample

    def GenerateSampleGaps(self, n):
        """Generates a random sample of gaps seen by passengers.

        n: sample size

        Returns: sequence of values
        """
        cdf_zb = thinkbayes.MakeCdfFromPmf(self.pmf_zb)
        sample = cdf_zb.Sample(n)
        return sample

    def GenerateSamplePassengers(self, lam, n):
        """Generates a sample wait time and number of arrivals.

        lam: arrival rate in passengers per second
        n: number of samples

        Returns: list of (k1, y, k2) tuples
        k1: passengers there on arrival
        y: wait time
        k2: passengers arrived while waiting
        """
        zs = self.GenerateSampleGaps(n)
        xs, ys = SplitGaps(zs)

        res = []
        for x, y in zip(xs, ys):
            k1 = numpy.random.poisson(lam * x)
            k2 = numpy.random.poisson(lam * y)
            res.append((k1, y, k2))

        return res

    def PlotPmfs(self, root='redline0'):
        """Plots the computed Pmfs.

        root: string
        """
        pmfs = ScaleDists([self.pmf_z, self.pmf_zb], 1.0/60)

        thinkplot.Clf()
        thinkplot.PrePlot(2)
        thinkplot.Pmfs(pmfs)
        thinkplot.Save(root=root,
                       xlabel='Time (min)',
                       ylabel='CDF',
                       formats=FORMATS)


    def MakePlot(self, root='redline2'):
        """Plots the computed CDFs.

        root: string
        """
        print 'Mean z', self.pmf_z.Mean() / 60
        print 'Mean zb', self.pmf_zb.Mean() / 60
        print 'Mean y', self.pmf_y.Mean() / 60

        cdf_z = self.pmf_z.MakeCdf()
        cdf_zb = self.pmf_zb.MakeCdf()
        cdf_y = self.pmf_y.MakeCdf()

        cdfs = ScaleDists([cdf_z, cdf_zb, cdf_y], 1.0/60)

        thinkplot.Clf()
        thinkplot.PrePlot(3)
        thinkplot.Cdfs(cdfs)
        thinkplot.Save(root=root,
                       xlabel='Time (min)',
                       ylabel='CDF',
                       formats=FORMATS)


def SplitGaps(zs):
    """Splits zs into xs and ys.

    zs: sequence of gaps

    Returns: tuple of sequences (xs, ys)
    """
    xs = [random.uniform(0, z) for z in zs]
    ys = [z-x for z, x in zip(zs, xs)]
    return xs, ys


def PmfOfWaitTime(pmf_zb):
    """Distribution of wait time.

    pmf_zb: dist of gap time as seen by a random observer

    Returns: dist of wait time (also dist of elapsed time)
    """
    metapmf = thinkbayes.Pmf()
    for gap, prob in pmf_zb.Items():
        uniform = MakeUniformPmf(0, gap)
        metapmf.Set(uniform, prob)

    pmf_y = thinkbayes.MakeMixture(metapmf, name='y')
    return pmf_y


def ScaleDists(dists, factor):
    """Scales each of the distributions in a sequence.

    dists: sequence of Pmf or Cdf
    factor: float scale factor
    """
    return [dist.Scale(factor) for dist in dists]


class ElapsedTimeEstimator(object):
    """Uses the number of passengers to estimate time since last train."""

    def __init__(self, wtc, lam, num_passengers):
        """Constructor.

        pmf_x: expected distribution of elapsed time
        lam: arrival rate in passengers per second
        num_passengers: # passengers seen on the platform
        """
        # prior for elapsed time
        self.prior_x = Elapsed(wtc.pmf_x, name='prior x')

        # posterior of elapsed time (based on number of passengers)
        self.post_x = self.prior_x.Copy(name='posterior x')
        self.post_x.Update((lam, num_passengers))

        # predictive distribution of wait time
        self.pmf_y = PredictWaitTime(wtc.pmf_zb, self.post_x)

    def MakePlot(self, root='redline3'):
        """Plot the CDFs.

        root: string
        """
        # observed gaps
        cdf_prior_x = self.prior_x.MakeCdf()
        cdf_post_x = self.post_x.MakeCdf()
        cdf_y = self.pmf_y.MakeCdf()

        cdfs = ScaleDists([cdf_prior_x, cdf_post_x, cdf_y], 1.0/60)

        thinkplot.Clf()
        thinkplot.PrePlot(3)
        thinkplot.Cdfs(cdfs)
        thinkplot.Save(root=root,
                       xlabel='Time (min)',
                       ylabel='CDF',
                       formats=FORMATS)


class ArrivalRate(thinkbayes.Suite):
    """Represents the distribution of arrival rates (lambda)."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        Evaluates the Poisson PMF for lambda and k.

        hypo: arrival rate in passengers per second
        data: tuple of elapsed_time and number of passengers
        """
        lam = hypo
        x, k = data
        like = thinkbayes.EvalPoissonPmf(k, lam * x)
        return like


class ArrivalRateEstimator(object):
    """Estimates arrival rate based on passengers that arrive while waiting.
    """

    def __init__(self, passenger_data):
        """Constructor

        passenger_data: sequence of (k1, y, k2) pairs
        """
        # range for lambda
        low, high = 0, 5
        n = 51
        hypos = numpy.linspace(low, high, n) / 60

        self.prior_lam = ArrivalRate(hypos, name='prior')
        self.prior_lam.Remove(0)

        self.post_lam = self.prior_lam.Copy(name='posterior')

        for _k1, y, k2 in passenger_data:
            self.post_lam.Update((y, k2))

        print 'Mean posterior lambda', self.post_lam.Mean()

    def MakePlot(self, root='redline1'):
        """Plot the prior and posterior CDF of passengers arrival rate.

        root: string
        """
        thinkplot.Clf()
        thinkplot.PrePlot(2)

        # convert units to passengers per minute
        prior = self.prior_lam.MakeCdf().Scale(60)
        post = self.post_lam.MakeCdf().Scale(60)

        thinkplot.Cdfs([prior, post])

        thinkplot.Save(root=root,
                       xlabel='Arrival rate (passengers / min)',
                       ylabel='CDF',
                       formats=FORMATS)
                       

class Elapsed(thinkbayes.Suite):
    """Represents the distribution of elapsed time (x)."""

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        Evaluates the Poisson PMF for lambda and k.

        hypo: elapsed time since the last train
        data: tuple of arrival rate and number of passengers
        """
        x = hypo
        lam, k = data
        like = thinkbayes.EvalPoissonPmf(k, lam * x)
        return like


def PredictWaitTime(pmf_zb, pmf_x):
    """Computes the distribution of wait times.

    Enumerate all pairs of zb from pmf_zb and x from pmf_x,
    and accumulate the distribution of y = z - x.

    pmf_zb: distribution of gaps seen by random observer
    pmf_x: distribution of elapsed time
    """
    pmf_y = pmf_zb - pmf_x
    pmf_y.name = 'pred y'
    RemoveNegatives(pmf_y)
    return pmf_y


def RemoveNegatives(pmf):
    """Removes negative values from a PMF.

    pmf: Pmf
    """
    for val in pmf.Values():
        if val < 0:
            pmf.Remove(val)
    pmf.Normalize()


class Gaps(thinkbayes.Suite):
    """Represents the distribution of gap times,
    as updated by an observed waiting time."""

    def Likelihood(self, data, hypo):
        """The likelihood of the data under the hypothesis.

        If the actual gap time is z, what is the likelihood
        of waiting y seconds?

        hypo: actual time between trains
        data: observed wait time
        """
        z = hypo
        y = data
        if y > z:
            return 0
        return 1.0 / z


class GapDirichlet(thinkbayes.Dirichlet):
    """Represents the distribution of prevalences for each
    gap time."""

    def __init__(self, xs):
        """Constructor.

        xs: sequence of possible gap times
        """
        n = len(xs)
        thinkbayes.Dirichlet.__init__(self, n)
        self.xs = xs
        self.mean_zbs = []

    def PmfMeanZb(self):
        """Makes the Pmf of mean zb.

        Values stored in mean_zbs.
        """
        return thinkbayes.MakePmfFromList(self.mean_zbs)

    def Preload(self, data):
        """Adds pseudocounts to the parameters.

        data: sequence of pseudocounts
        """
        thinkbayes.Dirichlet.Update(self, data)

    def Update(self, data):
        """Computes the likelihood of the data.

        data: wait time observed by random arrival (y)

        Returns: float probability
        """
        k, y = data

        print k, y
        prior = self.PredictivePmf(self.xs)
        gaps = Gaps(prior)
        gaps.Update(y)
        probs = gaps.Probs(self.xs)

        self.params += numpy.array(probs)


class GapDirichlet2(GapDirichlet):
    """Represents the distribution of prevalences for each
    gap time."""

    def Update(self, data):
        """Computes the likelihood of the data.

        data: wait time observed by random arrival (y)

        Returns: float probability
        """
        k, y = data

        # get the current best guess for pmf_z
        pmf_zb = self.PredictivePmf(self.xs)

        # use it to compute prior pmf_x, pmf_y, pmf_z
        wtc = WaitTimeCalculator(pmf_zb, inverse=True)

        # use the observed passengers to estimate posterior pmf_x
        elapsed = ElapsedTimeEstimator(wtc,
                                       lam=0.0333,
                                       num_passengers=k)

        # use posterior_x and observed y to estimate observed z
        obs_zb = elapsed.post_x + Floor(y)
        probs = obs_zb.Probs(self.xs)

        mean_zb = obs_zb.Mean()
        self.mean_zbs.append(mean_zb)
        print k, y, mean_zb

        # use observed z to update beliefs about pmf_z
        self.params += numpy.array(probs)


class GapTimeEstimator(object):
    """Infers gap times using passenger data."""

    def __init__(self, xs, pcounts, passenger_data):
        self.xs = xs
        self.pcounts = pcounts
        self.passenger_data = passenger_data

        self.wait_times = [y for _k1, y, _k2 in passenger_data]
        self.pmf_y = thinkbayes.MakePmfFromList(self.wait_times, name="y")

        dirichlet = GapDirichlet2(self.xs)
        dirichlet.params /= 1.0

        dirichlet.Preload(self.pcounts)
        dirichlet.params /= 20.0

        self.prior_zb = dirichlet.PredictivePmf(self.xs, name="prior zb")
        
        for k1, y, _k2 in passenger_data:
            dirichlet.Update((k1, y))

        self.pmf_mean_zb = dirichlet.PmfMeanZb()

        self.post_zb = dirichlet.PredictivePmf(self.xs, name="post zb")
        self.post_z = UnbiasPmf(self.post_zb, name="post z")

    def PlotPmfs(self):
        """Plot the PMFs."""
        print 'Mean y', self.pmf_y.Mean()
        print 'Mean z', self.post_z.Mean()
        print 'Mean zb', self.post_zb.Mean()

        thinkplot.Pmf(self.pmf_y)
        thinkplot.Pmf(self.post_z)
        thinkplot.Pmf(self.post_zb)

    def MakePlot(self):
        """Plot the CDFs."""
        thinkplot.Cdf(self.pmf_y.MakeCdf())
        thinkplot.Cdf(self.prior_zb.MakeCdf())
        thinkplot.Cdf(self.post_zb.MakeCdf())
        thinkplot.Cdf(self.pmf_mean_zb.MakeCdf())
        thinkplot.Show()


def Floor(x, factor=10):
    """Rounds down to the nearest multiple of factor.

    When factor=10, all numbers from 10 to 19 get floored to 10.
    """
    return int(x/factor) * factor


def TestGte():
    """Tests the GapTimeEstimator."""
    random.seed(17)

    xs = [60, 120, 240]
    
    gap_times = [60, 60, 60, 60, 60, 120, 120, 120, 240, 240]

    # distribution of gap time (z)
    pdf_z = thinkbayes.EstimatedPdf(gap_times)
    pmf_z = pdf_z.MakePmf(xs, name="z")

    wtc = WaitTimeCalculator(pmf_z, inverse=False)

    lam = 0.0333
    n = 100
    passenger_data = wtc.GenerateSamplePassengers(lam, n)

    pcounts = [0, 0, 0]

    ite = GapTimeEstimator(xs, pcounts, passenger_data)

    thinkplot.Clf()

    # thinkplot.Cdf(wtc.pmf_z.MakeCdf(name="actual z"))    
    thinkplot.Cdf(wtc.pmf_zb.MakeCdf(name="actual zb"))
    ite.MakePlot()


class WaitMixtureEstimator(object):
    """Encapsulates the process of estimating wait time with uncertain lam.
    """

    def __init__(self, wtc, are, num_passengers=15):
        """Constructor.

        wtc: WaitTimeCalculator
        are: ArrivalTimeEstimator
        num_passengers: number of passengers seen on the platform
        """
        self.metapmf = thinkbayes.Pmf()

        for lam, prob in sorted(are.post_lam.Items()):
            ete = ElapsedTimeEstimator(wtc, lam, num_passengers)
            self.metapmf.Set(ete.pmf_y, prob)

        self.mixture = thinkbayes.MakeMixture(self.metapmf)

        lam = are.post_lam.Mean()
        ete = ElapsedTimeEstimator(wtc, lam, num_passengers)
        self.point = ete.pmf_y

    def MakePlot(self, root='redline4'):
        """Makes a plot showing the mixture."""
        thinkplot.Clf()

        # plot the MetaPmf
        for pmf, prob in sorted(self.metapmf.Items()):
            cdf = pmf.MakeCdf().Scale(1.0/60)
            width = 2/math.log(-math.log(prob))
            thinkplot.Plot(cdf.xs, cdf.ps,
                           alpha=0.2, linewidth=width, color='blue', 
                           label='')

        # plot the mixture and the distribution based on a point estimate
        thinkplot.PrePlot(2)
        #thinkplot.Cdf(self.point.MakeCdf(name='point').Scale(1.0/60))
        thinkplot.Cdf(self.mixture.MakeCdf(name='mix').Scale(1.0/60))

        thinkplot.Save(root=root,
                       xlabel='Wait time (min)',
                       ylabel='CDF',
                       formats=FORMATS,
                       axis=[0,10,0,1])



def GenerateSampleData(gap_times, lam=0.0333, n=10):
    """Generates passenger data based on actual gap times.

    gap_times: sequence of float
    lam: arrival rate in passengers per second
    n: number of simulated observations
    """
    xs = MakeRange(low=10)
    pdf_z = thinkbayes.EstimatedPdf(gap_times)
    pmf_z = pdf_z.MakePmf(xs, name="z")

    wtc = WaitTimeCalculator(pmf_z, inverse=False)
    passenger_data = wtc.GenerateSamplePassengers(lam, n)
    return wtc, passenger_data


def RandomSeed(x):
    """Initialize the random and numpy.random generators.

    x: int seed
    """
    random.seed(x)
    numpy.random.seed(x)
    

def RunSimpleProcess(gap_times, lam=0.0333, num_passengers=15, plot=True):
    """Runs the basic analysis and generates figures.

    gap_times: sequence of float
    lam: arrival rate in passengers per second
    num_passengers: int number of passengers on the platform
    plot: boolean, whether to generate plots

    Returns: WaitTimeCalculator, ElapsedTimeEstimator
    """
    global UPPER_BOUND
    UPPER_BOUND = 1200

    cdf_z = thinkbayes.MakeCdfFromList(gap_times).Scale(1.0/60)
    print 'CI z', cdf_z.CredibleInterval(90)

    xs = MakeRange(low=10)

    pdf_z = thinkbayes.EstimatedPdf(gap_times)
    pmf_z = pdf_z.MakePmf(xs, name="z")

    wtc = WaitTimeCalculator(pmf_z, inverse=False)    

    if plot:
        wtc.PlotPmfs()
        wtc.MakePlot()

    ete = ElapsedTimeEstimator(wtc, lam, num_passengers)

    if plot:
        ete.MakePlot()

    return wtc, ete


def RunMixProcess(gap_times, lam=0.0333, num_passengers=15, plot=True):
    """Runs the analysis for unknown lambda.

    gap_times: sequence of float
    lam: arrival rate in passengers per second
    num_passengers: int number of passengers on the platform
    plot: boolean, whether to generate plots

    Returns: WaitMixtureEstimator
    """
    global UPPER_BOUND
    UPPER_BOUND = 1200

    wtc, _ete = RunSimpleProcess(gap_times, lam, num_passengers)

    RandomSeed(20)
    passenger_data = wtc.GenerateSamplePassengers(lam, n=5)

    total_y = 0
    total_k2 = 0
    for k1, y, k2 in passenger_data:
        print k1, y/60, k2
        total_y += y/60
        total_k2 += k2
    print total_k2, total_y
    print 'Average arrival rate', total_k2 / total_y

    are = ArrivalRateEstimator(passenger_data)

    if plot:
        are.MakePlot()

    wme = WaitMixtureEstimator(wtc, are, num_passengers)

    if plot:
        wme.MakePlot()

    return wme


def RunLoop(gap_times, nums, lam=0.0333):
    """Runs the basic analysis for a range of num_passengers.

    gap_times: sequence of float
    nums: sequence of values for num_passengers
    lam: arrival rate in passengers per second

    Returns: WaitMixtureEstimator
    """
    global UPPER_BOUND
    UPPER_BOUND = 4000

    thinkplot.Clf()

    RandomSeed(18)

    # resample gap_times
    n = 220
    cdf_z = thinkbayes.MakeCdfFromList(gap_times)
    sample_z = cdf_z.Sample(n)
    pmf_z = thinkbayes.MakePmfFromList(sample_z)

    # compute the biased pmf and add some long delays
    cdf_zp = BiasPmf(pmf_z).MakeCdf()
    sample_zb = cdf_zp.Sample(n) + [1800, 2400, 3000]

    # smooth the distribution of zb
    pdf_zb = thinkbayes.EstimatedPdf(sample_zb)
    xs = MakeRange(low=60)
    pmf_zb = pdf_zb.MakePmf(xs)

    # unbias the distribution of zb and make wtc
    pmf_z = UnbiasPmf(pmf_zb)
    wtc = WaitTimeCalculator(pmf_z)

    probs = []
    for num_passengers in nums:
        ete = ElapsedTimeEstimator(wtc, lam, num_passengers)

        # compute the posterior prob of waiting more than 15 minutes
        cdf_y = ete.pmf_y.MakeCdf()
        prob = 1 - cdf_y.Prob(900)
        probs.append(prob)

        # thinkplot.Cdf(ete.pmf_y.MakeCdf(name=str(num_passengers)))
    
    thinkplot.Plot(nums, probs)
    thinkplot.Save(root='redline5',
                   xlabel='Num passengers',
                   ylabel='P(y > 15 min)',
                   formats=FORMATS,
                   )


def main(script):
    RunLoop(OBSERVED_GAP_TIMES, nums=[0, 5, 10, 15, 20, 25, 30, 35])
    RunMixProcess(OBSERVED_GAP_TIMES)
    

if __name__ == '__main__':
    main(*sys.argv)

########NEW FILE########
__FILENAME__ = redline_data
#!/usr/bin/python

"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2013 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import csv
import json
import numpy
import os
import sys
import redis
import urllib2

from datetime import datetime, time

from time import sleep


class Redis(object):
    """Provides access to a Redis instance on Redis To Go"""

    host = 'dory.redistogo.com'
    port = 10534

    def __init__(self):
        try:
            password = os.environ['REDIS_AUTH']
        except KeyError:
            print 'Environment variable REDIS_AUTH is not set.'
            sys.exit()
        
        self.r = redis.StrictRedis(host=self.host, 
                                   port=self.port,
                                   password=password,
                                   db=0)

    def WriteTrainSpotting(self, timestamp, tripid, seconds, live=True):
        """Writes a trainspotting event to the database.

        timestamp: int seconds since epoch
        tripid: string unique id
        seconds: int how many seconds away the train is
        live: boolean, whether to actually write the data
        """
        dt = datetime.fromtimestamp(timestamp)
        day = dt.date().isoformat()

        print dt, tripid, seconds, timestamp

        if live:
            self.r.sadd('days', day)
            self.r.sadd(day, tripid)
            self.r.zadd(tripid, seconds, timestamp)

    def FindArrivals(self, start_hour=16, end_hour=18):
        """For each trip, find the best estimate of the arrival time.

        start_hour: int 0-24, beginning of observation window
        end_hour: int 0-24, end of window

        Returns: map from string day to unsorted list of arrival datetimes
        """
        days = self.r.smembers('days')
        print days

        start_time = time(hour=start_hour)
        end_time = time(hour=end_hour)

        arrival_map = {}

        for day in days:
            tripids = self.r.smembers(day)

            for tripid in tripids:
                pred_dt = self.GetPredictedArrival(tripid)
                pred_time = pred_dt.time()

                if start_time < pred_time < end_time:
                    arrival_map.setdefault(day, []).append(pred_dt)

        return arrival_map

    def GetPredictedArrival(self, tripid):
        """Gets the best predicted arrival time for a given trip.

        tripid: string TripID like R98313D88
        """
        pair = self.r.zrange(tripid, 0, 1, withscores=True)
        timestamp, seconds = pair[0]
        pred_ts = float(timestamp) + seconds
        pred_dt = datetime.fromtimestamp(pred_ts)
        return pred_dt

class TrainSpotting(object):
    """Represents one observation of a train."""

    def __init__(self, t):
        self.timestamp = int(t[0])
        self.tripid = t[2]
        self.seconds = int(t[6])
    

def ReadCsv(url = 'http://developer.mbta.com/lib/rthr/red.csv'):
    """Reads data from the red line.

    Returns: list of TrainSpotting objects
    """
    fp = urllib2.urlopen(url)
    reader = csv.reader(fp)

    tss = []
    for t in reader:
        if t[5] != 'Kendall/MIT': continue        
        if t[3] != 'Braintree': continue

        ts = TrainSpotting(t)
        tss.append(ts)

    fp.close()
    return tss


def ReadJson():
    url = 'http://developer.mbta.com/lib/rthr/red.json'
    json_text = urllib2.urlopen(url).read()
    json_obj = json.loads(json_text)
    print json_obj


def ReadAndStore(red):
    """Read data from the MBTA and put it in the database.

    red: Redis object
    """
    tss = ReadCsv()
    for ts in tss:
        red.WriteTrainSpotting(ts.timestamp, ts.tripid, ts.seconds)


def Loop(red, start_time, end_time, delay=60):
    """Collects data from start_time until end_time.

    red: Redis object to store data
    start_time: datetime
    end_time: datetime
    delay: time to sleep between collections, in seconds
    """
    if datetime.now() < start_time:
        diff = start_time - datetime.now()
        print 'Sleeping', diff
        sleep(diff.total_seconds())

    while datetime.now() < end_time:
        print 'Collecting'
        ReadAndStore(red)
        sleep(delay)


def TodayAt(hour):
    """Makes a datetime object with today's date and the given time.

    hour: int 0-24
    """
    now = datetime.now()
    return datetime.combine(now, time(hour=hour))


def GetInterarrivals(arrival_map):
    """Finds all interarrival times in the arrival map.

    arrival_map: map from string day to unsorted list of arrival datetimes

    Returns: list of float interarrival times in seconds
    """
    interarrival_seconds = []
    for day, arrivals in sorted(arrival_map.iteritems()):
        print day, len(arrivals)
        arrivals.sort()
        diffs = numpy.diff(arrivals)
        diffs = [diff.total_seconds() for diff in diffs]
        interarrival_seconds.extend(diffs)

    return interarrival_seconds


def main(script, command='collect'):
    red = Redis()

    if command == 'collect':
        start = TodayAt(16)
        end = TodayAt(18)

        print start, end
        Loop(red, start, end)
        
    elif command == 'report':
        arrival_map = red.FindArrivals()
        interarrivals = GetInterarrivals(arrival_map)
        print repr(interarrivals)


if __name__ == '__main__':
    main(*sys.argv)

########NEW FILE########
__FILENAME__ = sat
"""This file contains code used in "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import csv
import math
import numpy
import sys

import matplotlib
import matplotlib.pyplot as pyplot

import thinkbayes
import thinkplot


def ReadScale(filename='sat_scale.csv', col=2):
    """Reads a CSV file of SAT scales (maps from raw score to standard score).

    Args:
      filename: string filename
      col: which column to start with (0=Reading, 2=Math, 4=Writing)

    Returns: thinkbayes.Interpolator object
    """
    def ParseRange(s):
        """Parse a range of values in the form 123-456

        s: string
        """
        t = [int(x) for x in s.split('-')]
        return 1.0 * sum(t) / len(t)

    fp = open(filename)
    reader = csv.reader(fp)
    raws = []
    scores = []

    for t in reader:
        try:
            raw = int(t[col])
            raws.append(raw)
            score = ParseRange(t[col+1])
            scores.append(score)
        except ValueError:
            pass

    raws.sort()
    scores.sort()
    return thinkbayes.Interpolator(raws, scores)


def ReadRanks(filename='sat_ranks.csv'):
    """Reads a CSV file of SAT scores.

    Args:
      filename: string filename

    Returns:
      list of (score, freq) pairs
    """
    fp = open(filename)
    reader = csv.reader(fp)
    res = []

    for t in reader:
        try:
            score = int(t[0])
            freq = int(t[1])
            res.append((score, freq))
        except ValueError:
            pass

    return res


def DivideValues(pmf, denom):
    """Divides the values in a Pmf by denom.

    Returns a new Pmf.
    """
    new = thinkbayes.Pmf()
    denom = float(denom)
    for val, prob in pmf.Items():
        x = val / denom
        new.Set(x, prob)
    return new


class Exam(object):
    """Encapsulates information about an exam.

    Contains the distribution of scaled scores and an
    Interpolator that maps between scaled and raw scores.
    """
    def __init__(self):
        self.scale = ReadScale()

        scores = ReadRanks()
        score_pmf = thinkbayes.MakePmfFromDict(dict(scores))

        self.raw = self.ReverseScale(score_pmf)
        self.max_score = max(self.raw.Values())
        self.prior = DivideValues(self.raw, denom=self.max_score)
        
        center = -0.05
        width = 1.8
        self.difficulties = MakeDifficulties(center, width, self.max_score)

    def CompareScores(self, a_score, b_score, constructor):
        """Computes posteriors for two test scores and the likelihood ratio.

        a_score, b_score: scales SAT scores
        constructor: function that instantiates an Sat or Sat2 object
        """
        a_sat = constructor(self, a_score)
        b_sat = constructor(self, b_score)

        a_sat.PlotPosteriors(b_sat)

        if constructor is Sat:
            PlotJointDist(a_sat, b_sat)

        top = TopLevel('AB')
        top.Update((a_sat, b_sat))
        top.Print()

        ratio = top.Prob('A') / top.Prob('B')
        
        print 'Likelihood ratio', ratio

        posterior = ratio / (ratio + 1)
        print 'Posterior', posterior

        if constructor is Sat2:
            ComparePosteriorPredictive(a_sat, b_sat)

    def MakeRawScoreDist(self, efficacies):
        """Makes the distribution of raw scores for given difficulty.

        efficacies: Pmf of efficacy
        """
        pmfs = thinkbayes.Pmf()
        for efficacy, prob in efficacies.Items():
            scores = self.PmfCorrect(efficacy)
            pmfs.Set(scores, prob)

        mix = thinkbayes.MakeMixture(pmfs)
        return mix

    def CalibrateDifficulty(self):
        """Make a plot showing the model distribution of raw scores."""
        thinkplot.Clf()
        thinkplot.PrePlot(num=2)

        cdf = thinkbayes.MakeCdfFromPmf(self.raw, name='data')
        thinkplot.Cdf(cdf)

        efficacies = thinkbayes.MakeGaussianPmf(0, 1.5, 3)
        pmf = self.MakeRawScoreDist(efficacies)
        cdf = thinkbayes.MakeCdfFromPmf(pmf, name='model')
        thinkplot.Cdf(cdf)
        
        thinkplot.Save(root='sat_calibrate',
                    xlabel='raw score',
                    ylabel='CDF',
                    formats=['pdf', 'eps'])

    def PmfCorrect(self, efficacy):
        """Returns the PMF of number of correct responses.

        efficacy: float
        """
        pmf = PmfCorrect(efficacy, self.difficulties)
        return pmf

    def Lookup(self, raw):
        """Looks up a raw score and returns a scaled score."""
        return self.scale.Lookup(raw)
        
    def Reverse(self, score):
        """Looks up a scaled score and returns a raw score.

        Since we ignore the penalty, negative scores round up to zero.
        """
        raw = self.scale.Reverse(score)
        return raw if raw > 0 else 0
        
    def ReverseScale(self, pmf):
        """Applies the reverse scale to the values of a PMF.

        Args:
            pmf: Pmf object
            scale: Interpolator object

        Returns:
            new Pmf
        """
        new = thinkbayes.Pmf()
        for val, prob in pmf.Items():
            raw = self.Reverse(val)
            new.Incr(raw, prob)
        return new


class Sat(thinkbayes.Suite):
    """Represents the distribution of p_correct for a test-taker."""

    def __init__(self, exam, score):
        self.exam = exam
        self.score = score

        # start with the prior distribution
        thinkbayes.Suite.__init__(self, exam.prior)

        # update based on an exam score
        self.Update(score)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of a test score, given efficacy."""
        p_correct = hypo
        score = data

        k = self.exam.Reverse(score)
        n = self.exam.max_score
        like = thinkbayes.EvalBinomialPmf(k, n, p_correct)
        return like

    def PlotPosteriors(self, other):
        """Plots posterior distributions of efficacy.

        self, other: Sat objects.
        """
        thinkplot.Clf()
        thinkplot.PrePlot(num=2)

        cdf1 = thinkbayes.MakeCdfFromPmf(self, 'posterior %d' % self.score)
        cdf2 = thinkbayes.MakeCdfFromPmf(other, 'posterior %d' % other.score)

        thinkplot.Cdfs([cdf1, cdf2])
        thinkplot.Save(xlabel='p_correct', 
                    ylabel='CDF', 
                    axis=[0.7, 1.0, 0.0, 1.0],
                    root='sat_posteriors_p_corr',
                    formats=['pdf', 'eps'])


class Sat2(thinkbayes.Suite):
    """Represents the distribution of efficacy for a test-taker."""

    def __init__(self, exam, score):
        self.exam = exam
        self.score = score

        # start with the Gaussian prior
        efficacies = thinkbayes.MakeGaussianPmf(0, 1.5, 3)
        thinkbayes.Suite.__init__(self, efficacies)

        # update based on an exam score
        self.Update(score)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of a test score, given efficacy."""
        efficacy = hypo
        score = data
        raw = self.exam.Reverse(score)

        pmf = self.exam.PmfCorrect(efficacy)
        like = pmf.Prob(raw)
        return like

    def MakePredictiveDist(self):
        """Returns the distribution of raw scores expected on a re-test."""
        raw_pmf = self.exam.MakeRawScoreDist(self)
        return raw_pmf
    
    def PlotPosteriors(self, other):
        """Plots posterior distributions of efficacy.

        self, other: Sat objects.
        """
        thinkplot.Clf()
        thinkplot.PrePlot(num=2)

        cdf1 = thinkbayes.MakeCdfFromPmf(self, 'posterior %d' % self.score)
        cdf2 = thinkbayes.MakeCdfFromPmf(other, 'posterior %d' % other.score)

        thinkplot.Cdfs([cdf1, cdf2])
        thinkplot.Save(xlabel='efficacy', 
                    ylabel='CDF', 
                    axis=[0, 4.6, 0.0, 1.0],
                    root='sat_posteriors_eff',
                    formats=['pdf', 'eps'])


def PlotJointDist(pmf1, pmf2, thresh=0.8):
    """Plot the joint distribution of p_correct.

    pmf1, pmf2: posterior distributions
    thresh: lower bound of the range to be plotted
    """
    def Clean(pmf):
        """Removes values below thresh."""
        vals = [val for val in pmf.Values() if val < thresh]
        [pmf.Remove(val) for val in vals]

    Clean(pmf1)
    Clean(pmf2)
    pmf = thinkbayes.MakeJoint(pmf1, pmf2)

    thinkplot.Figure(figsize=(6, 6))    
    thinkplot.Contour(pmf, contour=False, pcolor=True)

    thinkplot.Plot([thresh, 1.0], [thresh, 1.0],
                color='gray', alpha=0.2, linewidth=4)

    thinkplot.Save(root='sat_joint',
                   xlabel='p_correct Alice', 
                   ylabel='p_correct Bob',
                   axis=[thresh, 1.0, thresh, 1.0],
                   formats=['pdf', 'eps'])


def ComparePosteriorPredictive(a_sat, b_sat):
    """Compares the predictive distributions of raw scores.

    a_sat: posterior distribution
    b_sat:
    """
    a_pred = a_sat.MakePredictiveDist()
    b_pred = b_sat.MakePredictiveDist()

    #thinkplot.Clf()
    #thinkplot.Pmfs([a_pred, b_pred])
    #thinkplot.Show()

    a_like = thinkbayes.PmfProbGreater(a_pred, b_pred)
    b_like = thinkbayes.PmfProbLess(a_pred, b_pred)
    c_like = thinkbayes.PmfProbEqual(a_pred, b_pred)

    print 'Posterior predictive'
    print 'A', a_like
    print 'B', b_like
    print 'C', c_like


def PlotPriorDist(pmf):
    """Plot the prior distribution of p_correct.

    pmf: prior
    """
    thinkplot.Clf()
    thinkplot.PrePlot(num=1)

    cdf1 = thinkbayes.MakeCdfFromPmf(pmf, 'prior')
    thinkplot.Cdf(cdf1)
    thinkplot.Save(root='sat_prior',
                   xlabel='p_correct', 
                   ylabel='CDF',
                   formats=['pdf', 'eps'])


class TopLevel(thinkbayes.Suite):
    """Evaluates the top-level hypotheses about Alice and Bob.

    Uses the bottom-level posterior distribution about p_correct
    (or efficacy).
    """

    def Update(self, data):
        a_sat, b_sat = data

        a_like = thinkbayes.PmfProbGreater(a_sat, b_sat)
        b_like = thinkbayes.PmfProbLess(a_sat, b_sat)
        c_like = thinkbayes.PmfProbEqual(a_sat, b_sat)

        a_like += c_like / 2
        b_like += c_like / 2

        self.Mult('A', a_like)
        self.Mult('B', b_like)

        self.Normalize()


def ProbCorrect(efficacy, difficulty, a=1):
    """Returns the probability that a person gets a question right.

    efficacy: personal ability to answer questions
    difficulty: how hard the question is

    Returns: float prob
    """
    return 1 / (1 + math.exp(-a * (efficacy - difficulty)))


def BinaryPmf(p):
    """Makes a Pmf with values 1 and 0.
    
    p: probability given to 1
    
    Returns: Pmf object
    """
    pmf = thinkbayes.Pmf()
    pmf.Set(1, p)
    pmf.Set(0, 1-p)
    return pmf


def PmfCorrect(efficacy, difficulties):
    """Computes the distribution of correct responses.

    efficacy: personal ability to answer questions
    difficulties: list of difficulties, one for each question

    Returns: new Pmf object
    """
    pmf0 = thinkbayes.Pmf([0])

    ps = [ProbCorrect(efficacy, difficulty) for difficulty in difficulties]
    pmfs = [BinaryPmf(p) for p in ps]
    dist = sum(pmfs, pmf0)
    return dist


def MakeDifficulties(center, width, n):
    """Makes a list of n difficulties with a given center and width.

    Returns: list of n floats between center-width and center+width
    """
    low, high = center-width, center+width
    return numpy.linspace(low, high, n)


def ProbCorrectTable():
    """Makes a table of p_correct for a range of efficacy and difficulty."""
    efficacies = [3, 1.5, 0, -1.5, -3]
    difficulties = [-1.85, -0.05, 1.75]

    for eff in efficacies:
        print '%0.2f & ' % eff, 
        for diff in difficulties:
            p = ProbCorrect(eff, diff)
            print '%0.2f & ' % p, 
        print r'\\'


def main(script):
    ProbCorrectTable()

    exam = Exam()

    PlotPriorDist(exam.prior)
    exam.CalibrateDifficulty()

    exam.CompareScores(780, 740, constructor=Sat)

    exam.CompareScores(780, 740, constructor=Sat2)


if __name__ == '__main__':
    main(*sys.argv)

########NEW FILE########
__FILENAME__ = species
"""This file contains code used in "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import matplotlib.pyplot as pyplot
import thinkplot
import numpy

import csv
import random
import shelve
import sys
import time

import thinkbayes

import warnings

warnings.simplefilter('error', RuntimeWarning)


FORMATS = ['pdf', 'eps', 'png']


class Locker(object):
    """Encapsulates a shelf for storing key-value pairs."""

    def __init__(self, shelf_file):
        self.shelf = shelve.open(shelf_file)

    def Close(self):
        """Closes the shelf.
        """
        self.shelf.close()

    def Add(self, key, value):
        """Adds a key-value pair."""
        self.shelf[str(key)] = value

    def Lookup(self, key):
        """Looks up a key."""
        return self.shelf.get(str(key))

    def Keys(self):
        """Returns an iterator of keys."""
        return self.shelf.iterkeys()

    def Read(self):
        """Returns the contents of the shelf as a map."""
        return dict(self.shelf)


class Subject(object):
    """Represents a subject from the belly button study."""

    def __init__(self, code):
        """
        code: string ID
        species: sequence of (int count, string species) pairs
        """
        self.code = code
        self.species = []
        self.suite = None
        self.num_reads = None
        self.num_species = None
        self.total_reads = None
        self.total_species = None
        self.prev_unseen = None
        self.pmf_n = None
        self.pmf_q = None
        self.pmf_l = None

    def Add(self, species, count):
        """Add a species-count pair.

        It is up to the caller to ensure that species names are unique.

        species: string species/genus name
        count: int number of individuals
        """
        self.species.append((count, species))

    def Done(self, reverse=False, clean_param=0):
        """Called when we are done adding species counts.

        reverse: which order to sort in
        """
        if clean_param:
            self.Clean(clean_param)

        self.species.sort(reverse=reverse)        
        counts = self.GetCounts()
        self.num_species = len(counts)
        self.num_reads = sum(counts)

    def Clean(self, clean_param=50):
        """Identifies and removes bogus data.

        clean_param: parameter that controls the number of legit species
        """
        def prob_bogus(k, r):
            """Compute the probability that a species is bogus."""
            q = clean_param / r
            p = (1-q) ** k
            return p

        print self.code, clean_param

        counts = self.GetCounts()
        r = 1.0 * sum(counts)

        species_seq = []
        for k, species in sorted(self.species):

            if random.random() < prob_bogus(k, r):
                continue
            species_seq.append((k, species))
        self.species = species_seq

    def GetM(self):
        """Gets number of observed species."""
        return len(self.species)
        
    def GetCounts(self):
        """Gets the list of species counts

        Should be in increasing order, if Sort() has been invoked.
        """
        return [count for count, _ in self.species]

    def MakeCdf(self):
        """Makes a CDF of total prevalence vs rank."""
        counts = self.GetCounts()
        counts.sort(reverse=True)
        cdf = thinkbayes.MakeCdfFromItems(enumerate(counts))
        return cdf

    def GetNames(self):
        """Gets the names of the seen species."""
        return [name for _, name in self.species]

    def PrintCounts(self):
        """Prints the counts and species names."""
        for count, name in reversed(self.species):
            print count, name

    def GetSpecies(self, index):
        """Gets the count and name of the indicated species.

        Returns: count-species pair
        """
        return self.species[index]

    def GetCdf(self):
        """Returns cumulative prevalence vs number of species.
        """
        counts = self.GetCounts()
        items = enumerate(counts)
        cdf = thinkbayes.MakeCdfFromItems(items)
        return cdf

    def GetPrevalences(self):
        """Returns a sequence of prevalences (normalized counts).
        """
        counts = self.GetCounts()
        total = sum(counts)
        prevalences = numpy.array(counts, dtype=numpy.float) / total
        return prevalences

    def Process(self, low=None, high=500, conc=1, iters=100):
        """Computes the posterior distribution of n and the prevalences.

        Sets attribute: self.suite

        low: minimum number of species
        high: maximum number of species
        conc: concentration parameter
        iters: number of iterations to use in the estimator
        """
        counts = self.GetCounts()
        m = len(counts)
        if low is None:
            low = max(m, 2)
        ns = range(low, high+1)

        #start = time.time()    
        self.suite = Species5(ns, conc=conc, iters=iters)
        self.suite.Update(counts)
        #end = time.time()

        #print 'Processing time' end-start

    def MakePrediction(self, num_sims=100):
        """Make predictions for the given subject.

        Precondition: Process has run

        num_sims: how many simulations to run for predictions

        Adds attributes
        pmf_l: predictive distribution of additional species
        """
        add_reads = self.total_reads - self.num_reads
        curves = self.RunSimulations(num_sims, add_reads)
        self.pmf_l = self.MakePredictive(curves)

    def MakeQuickPrediction(self, num_sims=100):
        """Make predictions for the given subject.

        Precondition: Process has run

        num_sims: how many simulations to run for predictions

        Adds attribute:
        pmf_l: predictive distribution of additional species
        """
        add_reads = self.total_reads - self.num_reads
        pmf = thinkbayes.Pmf()
        _, seen = self.GetSeenSpecies()

        for _ in range(num_sims):
            _, observations = self.GenerateObservations(add_reads)
            all_seen = seen.union(observations)
            l = len(all_seen) - len(seen)
            pmf.Incr(l)

        pmf.Normalize()
        self.pmf_l = pmf

    def DistL(self):
        """Returns the distribution of additional species, l.
        """
        return self.pmf_l

    def MakeFigures(self):
        """Makes figures showing distribution of n and the prevalences."""
        self.PlotDistN()
        self.PlotPrevalences()

    def PlotDistN(self):
        """Plots distribution of n."""
        pmf = self.suite.DistN()
        print '90% CI for N:', pmf.CredibleInterval(90)
        pmf.name = self.code

        thinkplot.Clf()
        thinkplot.PrePlot(num=1)

        thinkplot.Pmf(pmf)

        root = 'species-ndist-%s' % self.code
        thinkplot.Save(root=root,
                    xlabel='Number of species',
                    ylabel='Prob',
                    formats=FORMATS,
                    )

    def PlotPrevalences(self, num=5):
        """Plots dist of prevalence for several species.

        num: how many species (starting with the highest prevalence)
        """
        thinkplot.Clf()
        thinkplot.PrePlot(num=5)

        for rank in range(1, num+1):
            self.PlotPrevalence(rank)

        root = 'species-prev-%s' % self.code
        thinkplot.Save(root=root,
                    xlabel='Prevalence',
                    ylabel='Prob',
                    formats=FORMATS,
                    axis=[0, 0.3, 0, 1],
                    )

    def PlotPrevalence(self, rank=1, cdf_flag=True):
        """Plots dist of prevalence for one species.

        rank: rank order of the species to plot.
        cdf_flag: whether to plot the CDF
        """
        # convert rank to index
        index = self.GetM() - rank

        _, mix = self.suite.DistOfPrevalence(index)
        count, _ = self.GetSpecies(index)
        mix.name = '%d (%d)' % (rank, count)

        print '90%% CI for prevalence of species %d:' % rank, 
        print mix.CredibleInterval(90)

        if cdf_flag:
            cdf = mix.MakeCdf()
            thinkplot.Cdf(cdf)
        else:
            thinkplot.Pmf(mix)

    def PlotMixture(self, rank=1):
        """Plots dist of prevalence for all n, and the mix.

        rank: rank order of the species to plot
        """
        # convert rank to index
        index = self.GetM() - rank

        print self.GetSpecies(index)
        print self.GetCounts()[index]

        metapmf, mix = self.suite.DistOfPrevalence(index)

        thinkplot.Clf()
        for pmf in metapmf.Values():
            thinkplot.Pmf(pmf, color='blue', alpha=0.2, linewidth=0.5)

        thinkplot.Pmf(mix, color='blue', alpha=0.9, linewidth=2)

        root = 'species-mix-%s' % self.code
        thinkplot.Save(root=root,
                    xlabel='Prevalence',
                    ylabel='Prob',
                    formats=FORMATS,
                    axis=[0, 0.3, 0, 0.3],
                    legend=False)

    def GetSeenSpecies(self):
        """Makes a set of the names of seen species.

        Returns: number of species, set of string species names
        """
        names = self.GetNames()
        m = len(names)
        seen = set(SpeciesGenerator(names, m))
        return m, seen

    def GenerateObservations(self, num_reads):
        """Generates a series of random observations.

        num_reads: number of reads to generate

        Returns: number of species, sequence of string species names
        """
        n, prevalences = self.suite.SamplePosterior()

        names = self.GetNames()
        name_iter = SpeciesGenerator(names, n)

        items = zip(name_iter, prevalences)

        cdf = thinkbayes.MakeCdfFromItems(items)
        observations = cdf.Sample(num_reads)

        #for ob in observations:
        #    print ob

        return n, observations

    def Resample(self, num_reads):
        """Choose a random subset of the data (without replacement).

        num_reads: number of reads in the subset
        """
        t = []
        for count, species in self.species:
            t.extend([species]*count)

        random.shuffle(t)
        reads = t[:num_reads]

        subject = Subject(self.code)
        hist = thinkbayes.MakeHistFromList(reads)
        for species, count in hist.Items():
            subject.Add(species, count)

        subject.Done()
        return subject

    def Match(self, match):
        """Match up a rarefied subject with a complete subject.

        match: complete Subject

        Assigns attributes:
        total_reads:
        total_species:
        prev_unseen:
        """
        self.total_reads = match.num_reads
        self.total_species = match.num_species

        # compute the prevalence of unseen species (at least approximately,
        # based on all species counts in match
        _, seen = self.GetSeenSpecies()

        seen_total = 0.0
        unseen_total = 0.0
        for count, species in match.species:
            if species in seen:
                seen_total += count
            else:
                unseen_total += count

        self.prev_unseen = unseen_total / (seen_total + unseen_total)

    def RunSimulation(self, num_reads, frac_flag=False, jitter=0.01):
        """Simulates additional observations and returns a rarefaction curve.

        k is the number of additional observations
        num_new is the number of new species seen

        num_reads: how many new reads to simulate
        frac_flag: whether to convert to fraction of species seen
        jitter: size of jitter added if frac_flag is true

        Returns: list of (k, num_new) pairs
        """
        m, seen = self.GetSeenSpecies()
        n, observations = self.GenerateObservations(num_reads)

        curve = []
        for i, obs in enumerate(observations):
            seen.add(obs)

            if frac_flag:
                frac_seen = len(seen) / float(n)
                frac_seen += random.uniform(-jitter, jitter)
                curve.append((i+1, frac_seen))
            else:
                num_new = len(seen) - m
                curve.append((i+1, num_new))

        return curve

    def RunSimulations(self, num_sims, num_reads, frac_flag=False):
        """Runs simulations and returns a list of curves.

        Each curve is a sequence of (k, num_new) pairs.

        num_sims: how many simulations to run
        num_reads: how many samples to generate in each simulation
        frac_flag: whether to convert num_new to fraction of total
        """
        curves = [self.RunSimulation(num_reads, frac_flag) 
                  for _ in range(num_sims)]
        return curves

    def MakePredictive(self, curves):
        """Makes a predictive distribution of additional species.

        curves: list of (k, num_new) curves 

        Returns: Pmf of num_new
        """
        pred = thinkbayes.Pmf(name=self.code)
        for curve in curves:
            _, last_num_new = curve[-1]
            pred.Incr(last_num_new)
        pred.Normalize()
        return pred


def MakeConditionals(curves, ks):
    """Makes Cdfs of the distribution of num_new conditioned on k.

    curves: list of (k, num_new) curves 
    ks: list of values of k

    Returns: list of Cdfs
    """
    joint = MakeJointPredictive(curves)

    cdfs = []
    for k in ks:
        pmf = joint.Conditional(1, 0, k)
        pmf.name = 'k=%d' % k
        cdf = pmf.MakeCdf()
        cdfs.append(cdf)
        print '90%% credible interval for %d' % k,
        print cdf.CredibleInterval(90)
    return cdfs


def MakeJointPredictive(curves):
    """Makes a joint distribution of k and num_new.

    curves: list of (k, num_new) curves 

    Returns: joint Pmf of (k, num_new)
    """
    joint = thinkbayes.Joint()
    for curve in curves:
        for k, num_new in curve:
            joint.Incr((k, num_new))
    joint.Normalize()
    return joint


def MakeFracCdfs(curves, ks):
    """Makes Cdfs of the fraction of species seen.

    curves: list of (k, num_new) curves 

    Returns: list of Cdfs
    """
    d = {}
    for curve in curves:
        for k, frac in curve:
            if k in ks:
                d.setdefault(k, []).append(frac)

    cdfs = {}
    for k, fracs in d.iteritems():
        cdf = thinkbayes.MakeCdfFromList(fracs)
        cdfs[k] = cdf

    return cdfs

def SpeciesGenerator(names, num):
    """Generates a series of names, starting with the given names.

    Additional names are 'unseen' plus a serial number.

    names: list of strings
    num: total number of species names to generate

    Returns: string iterator
    """
    i = 0
    for name in names:
        yield name
        i += 1

    while i < num:
        yield 'unseen-%d' % i
        i += 1
            

def ReadRarefactedData(filename='journal.pone.0047712.s001.csv', 
                       clean_param=0):
    """Reads a data file and returns a list of Subjects.

    Data from http://www.plosone.org/article/
    info%3Adoi%2F10.1371%2Fjournal.pone.0047712#s4

    filename: string filename to read
    clean_param: parameter passed to Clean

    Returns: map from code to Subject
    """
    fp = open(filename)
    reader = csv.reader(fp)
    _ = reader.next()
    
    subject = Subject('')
    subject_map = {}

    i = 0
    for t in reader:
        code = t[0]
        if code != subject.code:
            # start a new subject
            subject = Subject(code)
            subject_map[code] = subject

        # append a number to the species names so they're unique
        species = t[1]
        species = '%s-%d' % (species, i)
        i += 1

        count = int(t[2])
        subject.Add(species, count)

    for code, subject in subject_map.iteritems():
        subject.Done(clean_param=clean_param)

    return subject_map


def ReadCompleteDataset(filename='BBB_data_from_Rob.csv', clean_param=0):
    """Reads a data file and returns a list of Subjects.

    Data from personal correspondence with Rob Dunn, received 2-7-13.
    Converted from xlsx to csv.

    filename: string filename to read
    clean_param: parameter passed to Clean

    Returns: map from code to Subject
    """
    fp = open(filename)
    reader = csv.reader(fp)
    header = reader.next()
    header = reader.next()

    subject_codes = header[1:-1]
    subject_codes = ['B'+code for code in subject_codes]

    # create the subject map
    uber_subject = Subject('uber')
    subject_map = {}
    for code in subject_codes:
        subject_map[code] = Subject(code)

    # read lines
    i = 0
    for t in reader:
        otu_code = t[0]
        if otu_code == '':
            continue

        # pull out a species name and give it a number
        otu_names = t[-1]
        taxons = otu_names.split(';')
        species = taxons[-1]
        species = '%s-%d' % (species, i)
        i += 1

        counts = [int(x) for x in t[1:-1]]

        # print otu_code, species

        for code, count in zip(subject_codes, counts):
            if count > 0:
                subject_map[code].Add(species, count)
                uber_subject.Add(species, count)

    uber_subject.Done(clean_param=clean_param)
    for code, subject in subject_map.iteritems():
        subject.Done(clean_param=clean_param)

    return subject_map, uber_subject
        

def JoinSubjects():
    """Reads both datasets and computers their inner join.

    Finds all subjects that appear in both datasets.

    For subjects in the rarefacted dataset, looks up the total
    number of reads and stores it as total_reads.  num_reads
    is normally 400.
    
    Returns: map from code to Subject
    """

    # read the rarefacted dataset
    sampled_subjects = ReadRarefactedData()

    # read the complete dataset
    all_subjects, _ = ReadCompleteDataset()

    for code, subject in sampled_subjects.iteritems():
        if code in all_subjects:
            match = all_subjects[code]
            subject.Match(match)

    return sampled_subjects


def JitterCurve(curve, dx=0.2, dy=0.3):
    """Adds random noise to the pairs in a curve.

    dx and dy control the amplitude of the noise in each dimension.
    """
    curve = [(x+random.uniform(-dx, dx), 
              y+random.uniform(-dy, dy)) for x, y in curve]
    return curve


def OffsetCurve(curve, i, n, dx=0.3, dy=0.3):
    """Adds random noise to the pairs in a curve.

    i is the index of the curve
    n is the number of curves

    dx and dy control the amplitude of the noise in each dimension.
    """
    xoff = -dx + 2 * dx * i / (n-1)
    yoff = -dy + 2 * dy * i / (n-1)
    curve = [(x+xoff, y+yoff) for x, y in curve]
    return curve


def PlotCurves(curves, root='species-rare'):
    """Plots a set of curves.

    curves is a list of curves; each curve is a list of (x, y) pairs.
    """
    thinkplot.Clf()
    color = '#225EA8'

    n = len(curves)
    for i, curve in enumerate(curves):
        curve = OffsetCurve(curve, i, n)
        xs, ys = zip(*curve)
        thinkplot.Plot(xs, ys, color=color, alpha=0.3, linewidth=0.5)

    thinkplot.Save(root=root,
                xlabel='# samples',
                ylabel='# species',
                formats=FORMATS,
                legend=False)


def PlotConditionals(cdfs, root='species-cond'):
    """Plots cdfs of num_new conditioned on k.

    cdfs: list of Cdf
    root: string filename root
    """
    thinkplot.Clf()
    thinkplot.PrePlot(num=len(cdfs))

    thinkplot.Cdfs(cdfs)

    thinkplot.Save(root=root,
                xlabel='# new species',
                ylabel='Prob',
                formats=FORMATS)


def PlotFracCdfs(cdfs, root='species-frac'):
    """Plots CDFs of the fraction of species seen.

    cdfs: map from k to CDF of fraction of species seen after k samples
    """
    thinkplot.Clf()
    color = '#225EA8'

    for k, cdf in cdfs.iteritems():
        xs, ys = cdf.Render()
        ys = [1-y for y in ys]
        thinkplot.Plot(xs, ys, color=color, linewidth=1)

        x = 0.9
        y = 1 - cdf.Prob(x)
        pyplot.text(x, y, str(k), fontsize=9, color=color,
                    horizontalalignment='center',
                    verticalalignment='center',
                    bbox=dict(facecolor='white', edgecolor='none'))

    thinkplot.Save(root=root,
                xlabel='Fraction of species seen',
                ylabel='Probability',
                formats=FORMATS,
                legend=False)


class Species(thinkbayes.Suite):
    """Represents hypotheses about the number of species."""
    
    def __init__(self, ns, conc=1, iters=1000):
        hypos = [thinkbayes.Dirichlet(n, conc) for n in ns]
        thinkbayes.Suite.__init__(self, hypos)
        self.iters = iters

    def Update(self, data):
        """Updates the suite based on the data.

        data: list of observed frequencies
        """
        # call Update in the parent class, which calls Likelihood
        thinkbayes.Suite.Update(self, data)

        # update the next level of the hierarchy
        for hypo in self.Values():
            hypo.Update(data)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under this hypothesis.

        hypo: Dirichlet object
        data: list of observed frequencies
        """
        dirichlet = hypo

        # draw sample Likelihoods from the hypothetical Dirichlet dist
        # and add them up
        like = 0
        for _ in range(self.iters):
            like += dirichlet.Likelihood(data)

        # correct for the number of ways the observed species
        # might have been chosen from all species
        m = len(data)
        like *= thinkbayes.BinomialCoef(dirichlet.n, m)

        return like

    def DistN(self):
        """Computes the distribution of n."""
        pmf = thinkbayes.Pmf()
        for hypo, prob in self.Items():
            pmf.Set(hypo.n, prob)
        return pmf
        

class Species2(object):
    """Represents hypotheses about the number of species.

    Combines two layers of the hierarchy into one object.

    ns and probs represent the distribution of N

    params represents the parameters of the Dirichlet distributions
    """
    
    def __init__(self, ns, conc=1, iters=1000):
        self.ns = ns
        self.conc = conc
        self.probs = numpy.ones(len(ns), dtype=numpy.float)
        self.params = numpy.ones(self.ns[-1], dtype=numpy.float) * conc
        self.iters = iters
        self.num_reads = 0
        self.m = 0

    def Preload(self, data):
        """Change the initial parameters to fit the data better.

        Just an experiment.  Doesn't work.
        """
        m = len(data)
        singletons = data.count(1)
        num = m - singletons
        print m, singletons, num
        addend = numpy.ones(num, dtype=numpy.float) * 1
        print len(addend)
        print len(self.params[singletons:m])
        self.params[singletons:m] += addend
        print 'Preload', num

    def Update(self, data):
        """Updates the distribution based on data.

        data: numpy array of counts
        """
        self.num_reads += sum(data)

        like = numpy.zeros(len(self.ns), dtype=numpy.float)
        for _ in range(self.iters):
            like += self.SampleLikelihood(data)

        self.probs *= like
        self.probs /= self.probs.sum()

        self.m = len(data)
        #self.params[:self.m] += data * self.conc
        self.params[:self.m] += data

    def SampleLikelihood(self, data):
        """Computes the likelihood of the data for all values of n.

        Draws one sample from the distribution of prevalences.

        data: sequence of observed counts

        Returns: numpy array of m likelihoods
        """
        gammas = numpy.random.gamma(self.params)

        m = len(data)
        row = gammas[:m]
        col = numpy.cumsum(gammas)

        log_likes = []
        for n in self.ns:
            ps = row / col[n-1]
            terms = numpy.log(ps) * data
            log_like = terms.sum()
            log_likes.append(log_like)

        log_likes -= numpy.max(log_likes)
        likes = numpy.exp(log_likes)

        coefs = [thinkbayes.BinomialCoef(n, m) for n in self.ns]
        likes *= coefs

        return likes

    def DistN(self):
        """Computes the distribution of n.

        Returns: new Pmf object
        """
        pmf = thinkbayes.MakePmfFromItems(zip(self.ns, self.probs))
        return pmf

    def RandomN(self):
        """Returns a random value of n."""
        return self.DistN().Random()

    def DistQ(self, iters=100):
        """Computes the distribution of q based on distribution of n.

        Returns: pmf of q
        """
        cdf_n = self.DistN().MakeCdf()
        sample_n = cdf_n.Sample(iters)

        pmf = thinkbayes.Pmf()
        for n in sample_n:
            q = self.RandomQ(n)
            pmf.Incr(q)

        pmf.Normalize()
        return pmf

    def RandomQ(self, n):
        """Returns a random value of q.

        Based on n, self.num_reads and self.conc.

        n: number of species

        Returns: q
        """
        # generate random prevalences
        dirichlet = thinkbayes.Dirichlet(n, conc=self.conc)
        prevalences = dirichlet.Random()

        # generate a simulated sample
        pmf = thinkbayes.MakePmfFromItems(enumerate(prevalences))
        cdf = pmf.MakeCdf()
        sample = cdf.Sample(self.num_reads)
        seen = set(sample)

        # add up the prevalence of unseen species
        q = 0
        for species, prev in enumerate(prevalences):
            if species not in seen:
                q += prev

        return q

    def MarginalBeta(self, n, index):
        """Computes the conditional distribution of the indicated species.
        
        n: conditional number of species
        index: which species

        Returns: Beta object representing a distribution of prevalence.
        """
        alpha0 = self.params[:n].sum()
        alpha = self.params[index]
        return thinkbayes.Beta(alpha, alpha0-alpha)

    def DistOfPrevalence(self, index):
        """Computes the distribution of prevalence for the indicated species.

        index: which species

        Returns: (metapmf, mix) where metapmf is a MetaPmf and mix is a Pmf
        """
        metapmf = thinkbayes.Pmf()

        for n, prob in zip(self.ns, self.probs):
            beta = self.MarginalBeta(n, index)
            pmf = beta.MakePmf()
            metapmf.Set(pmf, prob)

        mix = thinkbayes.MakeMixture(metapmf)
        return metapmf, mix
        
    def SamplePosterior(self):
        """Draws random n and prevalences.

        Returns: (n, prevalences)
        """
        n = self.RandomN()
        prevalences = self.SamplePrevalences(n)

        #print 'Peeking at n_cheat'
        #n = n_cheat

        return n, prevalences

    def SamplePrevalences(self, n):
        """Draws a sample of prevalences given n.

        n: the number of species assumed in the conditional

        Returns: numpy array of n prevalences
        """
        if n == 1:
            return [1.0]

        q_desired = self.RandomQ(n)
        q_desired = max(q_desired, 1e-6)

        params = self.Unbias(n, self.m, q_desired)

        gammas = numpy.random.gamma(params)
        gammas /= gammas.sum()
        return gammas
        
    def Unbias(self, n, m, q_desired):
        """Adjusts the parameters to achieve desired prev_unseen (q).

        n: number of species
        m: seen species
        q_desired: prevalence of unseen species
        """
        params = self.params[:n].copy()

        if n == m:
            return params
        
        x = sum(params[:m])
        y = sum(params[m:])
        a = x + y
        #print x, y, a, x/a, y/a

        g = q_desired * a / y
        f = (a - g * y) / x
        params[:m] *= f
        params[m:] *= g

        return params


class Species3(Species2):
    """Represents hypotheses about the number of species."""
    
    def Update(self, data):
        """Updates the suite based on the data.

        data: list of observations
        """
        # sample the likelihoods and add them up
        like = numpy.zeros(len(self.ns), dtype=numpy.float)
        for _ in range(self.iters):
            like += self.SampleLikelihood(data)

        self.probs *= like
        self.probs /= self.probs.sum()

        m = len(data)
        self.params[:m] += data

    def SampleLikelihood(self, data):
        """Computes the likelihood of the data under all hypotheses.

        data: list of observations
        """
        # get a random sample
        gammas = numpy.random.gamma(self.params)

        # row is just the first m elements of gammas
        m = len(data)
        row = gammas[:m]

        # col is the cumulative sum of gammas
        col = numpy.cumsum(gammas)[self.ns[0]-1:]

        # each row of the array is a set of ps, normalized
        # for each hypothetical value of n
        array = row / col[:, numpy.newaxis]

        # computing the multinomial PDF under a log transform
        # take the log of the ps and multiply by the data
        terms = numpy.log(array) * data

        # add up the rows
        log_likes = terms.sum(axis=1)

        # before exponentiating, scale into a reasonable range
        log_likes -= numpy.max(log_likes)
        likes = numpy.exp(log_likes)

        # correct for the number of ways we could see m species
        # out of a possible n
        coefs = [thinkbayes.BinomialCoef(n, m) for n in self.ns]
        likes *= coefs

        return likes


class Species4(Species):
    """Represents hypotheses about the number of species."""
    
    def Update(self, data):
        """Updates the suite based on the data.

        data: list of observed frequencies
        """
        m = len(data)

        # loop through the species and update one at a time
        for i in range(m):
            one = numpy.zeros(i+1)
            one[i] = data[i]
            
            # call the parent class
            Species.Update(self, one)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under this hypothesis.

        Note: this only works correctly if we update one species at a time.

        hypo: Dirichlet object
        data: list of observed frequencies
        """
        dirichlet = hypo
        like = 0
        for _ in range(self.iters):
            like += dirichlet.Likelihood(data)

        # correct for the number of unseen species the new one
        # could have been
        m = len(data)
        num_unseen = dirichlet.n - m + 1
        like *= num_unseen

        return like


class Species5(Species2):
    """Represents hypotheses about the number of species.

    Combines two laters of the hierarchy into one object.

    ns and probs represent the distribution of N

    params represents the parameters of the Dirichlet distributions
    """
    
    def Update(self, data):
        """Updates the suite based on the data.

        data: list of observed frequencies in increasing order
        """
        # loop through the species and update one at a time
        m = len(data)
        for i in range(m):
            self.UpdateOne(i+1, data[i])
            self.params[i] += data[i]

    def UpdateOne(self, i, count):
        """Updates the suite based on the data.

        Evaluates the likelihood for all values of n.

        i: which species was observed (1..n)
        count: how many were observed
        """
        # how many species have we seen so far
        self.m = i

        # how many reads have we seen
        self.num_reads += count

        if self.iters == 0:
            return

        # sample the likelihoods and add them up
        likes = numpy.zeros(len(self.ns), dtype=numpy.float)
        for _ in range(self.iters):
            likes += self.SampleLikelihood(i, count)

        # correct for the number of unseen species the new one
        # could have been
        unseen_species = [n-i+1 for n in self.ns]
        likes *= unseen_species

        # multiply the priors by the likelihoods and renormalize
        self.probs *= likes
        self.probs /= self.probs.sum()

    def SampleLikelihood(self, i, count):
        """Computes the likelihood of the data under all hypotheses.

        i: which species was observed
        count: how many were observed
        """
        # get a random sample of p
        gammas = numpy.random.gamma(self.params)

        # sums is the cumulative sum of p, for each value of n
        sums = numpy.cumsum(gammas)[self.ns[0]-1:]

        # get p for the mth species, for each value of n
        ps = gammas[i-1] / sums
        log_likes = numpy.log(ps) * count

        # before exponentiating, scale into a reasonable range
        log_likes -= numpy.max(log_likes)
        likes = numpy.exp(log_likes)

        return likes


def MakePosterior(constructor, data, ns, conc=1, iters=1000):
    """Makes a suite, updates it and returns the posterior suite.

    Prints the elapsed time.

    data: observed species and their counts
    ns: sequence of hypothetical ns
    conc: concentration parameter
    iters: how many samples to draw

    Returns: posterior suite of the given type
    """
    suite = constructor(ns, conc=conc, iters=iters)

    # print constructor.__name__
    start = time.time()
    suite.Update(data)
    end = time.time()
    print 'Processing time', end-start

    return suite


def PlotAllVersions():
    """Makes a graph of posterior distributions of N."""
    data = [1, 2, 3]
    m = len(data)
    n = 20
    ns = range(m, n)

    for constructor in [Species, Species2, Species3, Species4, Species5]:
        suite = MakePosterior(constructor, data, ns)
        pmf = suite.DistN()
        pmf.name = '%s' % (constructor.__name__)
        thinkplot.Pmf(pmf)

    thinkplot.Save(root='species3',
                xlabel='Number of species',
                ylabel='Prob')


def PlotMedium():
    """Makes a graph of posterior distributions of N."""
    data = [1, 1, 1, 1, 2, 3, 5, 9]
    m = len(data)
    n = 20
    ns = range(m, n)

    for constructor in [Species, Species2, Species3, Species4, Species5]:
        suite = MakePosterior(constructor, data, ns)
        pmf = suite.DistN()
        pmf.name = '%s' % (constructor.__name__)
        thinkplot.Pmf(pmf)

    thinkplot.Show()


def SimpleDirichletExample():
    """Makes a plot showing posterior distributions for three species.

    This is the case where we know there are exactly three species.
    """
    thinkplot.Clf()
    thinkplot.PrePlot(3)

    names = ['lions',  'tigers', 'bears']
    data = [3, 2, 1]

    dirichlet = thinkbayes.Dirichlet(3)
    for i in range(3):
        beta = dirichlet.MarginalBeta(i)
        print 'mean', names[i], beta.Mean()

    dirichlet.Update(data)
    for i in range(3):
        beta = dirichlet.MarginalBeta(i)
        print 'mean', names[i], beta.Mean()

        pmf = beta.MakePmf(name=names[i])
        thinkplot.Pmf(pmf)

    thinkplot.Save(root='species1',
                xlabel='Prevalence',
                ylabel='Prob',
                formats=FORMATS,
                )


def HierarchicalExample():
    """Shows the posterior distribution of n for lions, tigers and bears.
    """
    ns = range(3, 30)
    suite = Species(ns, iters=8000)

    data = [3, 2, 1]
    suite.Update(data)

    thinkplot.Clf()
    thinkplot.PrePlot(num=1)

    pmf = suite.DistN()
    thinkplot.Pmf(pmf)
    thinkplot.Save(root='species2',
                xlabel='Number of species',
                ylabel='Prob',
                formats=FORMATS,
                )


def CompareHierarchicalExample():
    """Makes a graph of posterior distributions of N."""
    data = [3, 2, 1]
    m = len(data)
    n = 30
    ns = range(m, n)

    constructors = [Species, Species5]
    iters = [1000, 100]

    for constructor, iters in zip(constructors, iters):
        suite = MakePosterior(constructor, data, ns, iters)
        pmf = suite.DistN()
        pmf.name = '%s' % (constructor.__name__)
        thinkplot.Pmf(pmf)

    thinkplot.Show()


def ProcessSubjects(codes):
    """Process subjects with the given codes and plot their posteriors.

    code: sequence of string codes
    """
    thinkplot.Clf()
    thinkplot.PrePlot(len(codes))

    subjects = ReadRarefactedData()
    pmfs = []
    for code in codes:
        subject = subjects[code]

        subject.Process()
        pmf = subject.suite.DistN()
        pmf.name = subject.code
        thinkplot.Pmf(pmf)

        pmfs.append(pmf)

    print 'ProbGreater', thinkbayes.PmfProbGreater(pmfs[0], pmfs[1])
    print 'ProbLess', thinkbayes.PmfProbLess(pmfs[0], pmfs[1])

    thinkplot.Save(root='species4',
                xlabel='Number of species',
                ylabel='Prob',
                formats=FORMATS,
                )


def RunSubject(code, conc=1, high=500):
    """Run the analysis for the subject with the given code.

    code: string code
    """
    subjects = JoinSubjects()
    subject = subjects[code]

    subject.Process(conc=conc, high=high, iters=300)
    subject.MakeQuickPrediction()

    PrintSummary(subject)
    actual_l = subject.total_species - subject.num_species
    cdf_l = subject.DistL().MakeCdf()
    PrintPrediction(cdf_l, actual_l)

    subject.MakeFigures()

    num_reads = 400
    curves = subject.RunSimulations(100, num_reads)
    root = 'species-rare-%s' % subject.code
    PlotCurves(curves, root=root)

    num_reads = 800
    curves = subject.RunSimulations(500, num_reads)
    ks = [100, 200, 400, 800]
    cdfs = MakeConditionals(curves, ks)
    root = 'species-cond-%s' % subject.code
    PlotConditionals(cdfs, root=root)

    num_reads = 1000
    curves = subject.RunSimulations(500, num_reads, frac_flag=True)
    ks = [10, 100, 200, 400, 600, 800, 1000]
    cdfs = MakeFracCdfs(curves, ks)
    root = 'species-frac-%s' % subject.code
    PlotFracCdfs(cdfs, root=root)


def PrintSummary(subject):
    """Print a summary of a subject.

    subject: Subject
    """
    print subject.code
    print 'found %d species in %d reads' % (subject.num_species,
                                            subject.num_reads)

    print 'total %d species in %d reads' % (subject.total_species,
                                            subject.total_reads)

    cdf = subject.suite.DistN().MakeCdf()
    print 'n'
    PrintPrediction(cdf, 'unknown')
    

def PrintPrediction(cdf, actual):
    """Print a summary of a prediction.

    cdf: predictive distribution
    actual: actual value
    """
    median = cdf.Percentile(50)
    low, high = cdf.CredibleInterval(75)
    
    print 'predicted %0.2f (%0.2f %0.2f)' % (median, low, high)
    print 'actual', actual


def RandomSeed(x):
    """Initialize random.random and numpy.random.

    x: int seed
    """
    random.seed(x)
    numpy.random.seed(x)


def GenerateFakeSample(n, r, tr, conc=1):
    """Generates fake data with the given parameters.

    n: number of species
    r: number of reads in subsample
    tr: total number of reads
    conc: concentration parameter

    Returns: hist of all reads, hist of subsample, prev_unseen
    """
    # generate random prevalences
    dirichlet = thinkbayes.Dirichlet(n, conc=conc)
    prevalences = dirichlet.Random()
    prevalences.sort()

    # generate a simulated sample
    pmf = thinkbayes.MakePmfFromItems(enumerate(prevalences))
    cdf = pmf.MakeCdf()
    sample = cdf.Sample(tr)

    # collect the species counts
    hist = thinkbayes.MakeHistFromList(sample)

    # extract a subset of the data
    if tr > r:
        random.shuffle(sample)
        subsample = sample[:r]
        subhist = thinkbayes.MakeHistFromList(subsample)
    else:
        subhist = hist

    # add up the prevalence of unseen species
    prev_unseen = 0
    for species, prev in enumerate(prevalences):
        if species not in subhist:
            prev_unseen += prev

    return hist, subhist, prev_unseen


def PlotActualPrevalences():
    """Makes a plot comparing actual prevalences with a model.
    """
    # read data
    subject_map, _ = ReadCompleteDataset()

    # for subjects with more than 50 species,
    # PMF of max prevalence, and PMF of max prevalence
    # generated by a simulation
    pmf_actual = thinkbayes.Pmf()
    pmf_sim = thinkbayes.Pmf()

    # concentration parameter used in the simulation
    conc = 0.06

    for code, subject in subject_map.iteritems():
        prevalences = subject.GetPrevalences()
        m = len(prevalences)
        if m < 2:
            continue

        actual_max = max(prevalences)
        print code, m, actual_max

        # incr the PMFs
        if m > 50:
            pmf_actual.Incr(actual_max)
            pmf_sim.Incr(SimulateMaxPrev(m, conc))

    # plot CDFs for the actual and simulated max prevalence
    cdf_actual = pmf_actual.MakeCdf(name='actual')
    cdf_sim = pmf_sim.MakeCdf(name='sim')

    thinkplot.Cdfs([cdf_actual, cdf_sim])
    thinkplot.Show()


def ScatterPrevalences(ms, actual):
    """Make a scatter plot of actual prevalences and expected values.

    ms: sorted sequence of in m (number of species)
    actual: sequence of actual max prevalence
    """
    for conc in [1, 0.5, 0.2, 0.1]:
        expected = [ExpectedMaxPrev(m, conc) for m in ms]
        thinkplot.Plot(ms, expected)

    thinkplot.Scatter(ms, actual)
    thinkplot.Show(xscale='log')


def SimulateMaxPrev(m, conc=1):
    """Returns random max prevalence from a Dirichlet distribution.

    m: int number of species
    conc: concentration parameter of the Dirichlet distribution

    Returns: float max of m prevalences
    """
    dirichlet = thinkbayes.Dirichlet(m, conc)
    prevalences = dirichlet.Random()
    return max(prevalences)
        

def ExpectedMaxPrev(m, conc=1, iters=100):
    """Estimate expected max prevalence.

    m: number of species
    conc: concentration parameter
    iters: how many iterations to run

    Returns: expected max prevalence
    """
    dirichlet = thinkbayes.Dirichlet(m, conc)

    t = []
    for _ in range(iters):
        prevalences = dirichlet.Random()
        t.append(max(prevalences))

    return numpy.mean(t)


class Calibrator(object):
    """Encapsulates the calibration process."""

    def __init__(self, conc=0.1):
        """
        """
        self.conc = conc

        self.ps =  range(10, 100, 10)
        self.total_n = numpy.zeros(len(self.ps))
        self.total_q = numpy.zeros(len(self.ps))
        self.total_l = numpy.zeros(len(self.ps))

        self.n_seq = []
        self.q_seq = []
        self.l_seq = []

    def Calibrate(self, num_runs=100, n_low=30, n_high=400, r=400, tr=1200):
        """Runs calibrations.

        num_runs: how many runs
        """
        for seed in range(num_runs):
            self.RunCalibration(seed, n_low, n_high, r, tr)

        self.total_n *= 100.0 / num_runs
        self.total_q *= 100.0 / num_runs
        self.total_l *= 100.0 / num_runs

    def Validate(self, num_runs=100, clean_param=0):
        """Runs validations.

        num_runs: how many runs
        """
        subject_map, _ = ReadCompleteDataset(clean_param=clean_param)

        i = 0
        for match in subject_map.itervalues():
            if match.num_reads < 400:
                continue
            num_reads = 100

            print 'Validate', match.code
            subject = match.Resample(num_reads)
            subject.Match(match)

            n_actual = None
            q_actual = subject.prev_unseen
            l_actual = subject.total_species - subject.num_species
            self.RunSubject(subject, n_actual, q_actual, l_actual)
            
            i += 1
            if i == num_runs:
                break

        self.total_n *= 100.0 / num_runs
        self.total_q *= 100.0 / num_runs
        self.total_l *= 100.0 / num_runs

    def PlotN(self, root='species-n'):
        """Makes a scatter plot of simulated vs actual prev_unseen (q).
        """
        xs, ys = zip(*self.n_seq)
        if None in xs:
            return

        high = max(xs+ys)

        thinkplot.Plot([0, high], [0, high], color='gray')
        thinkplot.Scatter(xs, ys)
        thinkplot.Save(root=root,
                       xlabel='Actual n',
                       ylabel='Predicted')

    def PlotQ(self, root='species-q'):
        """Makes a scatter plot of simulated vs actual prev_unseen (q).
        """
        thinkplot.Plot([0, 0.2], [0, 0.2], color='gray')
        xs, ys = zip(*self.q_seq)
        thinkplot.Scatter(xs, ys)
        thinkplot.Save(root=root,
                       xlabel='Actual q',
                       ylabel='Predicted')

    def PlotL(self, root='species-n'):
        """Makes a scatter plot of simulated vs actual l.
        """
        thinkplot.Plot([0, 20], [0, 20], color='gray')
        xs, ys = zip(*self.l_seq)
        thinkplot.Scatter(xs, ys)
        thinkplot.Save(root=root,
                       xlabel='Actual l',
                       ylabel='Predicted')

    def PlotCalibrationCurves(self, root='species5'):
        """Plots calibration curves"""
        print self.total_n
        print self.total_q
        print self.total_l

        thinkplot.Plot([0, 100], [0, 100], color='gray', alpha=0.2)

        if self.total_n[0] >= 0:
            thinkplot.Plot(self.ps, self.total_n, label='n')

        thinkplot.Plot(self.ps, self.total_q, label='q')
        thinkplot.Plot(self.ps, self.total_l, label='l')

        thinkplot.Save(root=root,
                       axis=[0, 100, 0, 100],
                       xlabel='Ideal percentages',
                       ylabel='Predictive distributions',
                       formats=FORMATS,
                       )

    def RunCalibration(self, seed, n_low, n_high, r, tr):
        """Runs a single calibration run.

        Generates N and prevalences from a Dirichlet distribution,
        then generates simulated data.

        Runs analysis to get the posterior distributions.
        Generates calibration curves for each posterior distribution.

        seed: int random seed
        """
        # generate a random number of species and their prevalences
        # (from a Dirichlet distribution with alpha_i = conc for all i)
        RandomSeed(seed)
        n_actual = random.randrange(n_low, n_high+1)

        hist, subhist, q_actual = GenerateFakeSample(
            n_actual, 
            r, 
            tr, 
            self.conc)

        l_actual = len(hist) - len(subhist)
        print 'Run low, high, conc', n_low, n_high, self.conc
        print 'Run r, tr', r, tr
        print 'Run n, q, l', n_actual, q_actual, l_actual

        # extract the data
        data = [count for species, count in subhist.Items()]
        data.sort()
        print 'data', data

        # make a Subject and process
        subject = Subject('simulated')
        subject.num_reads = r
        subject.total_reads = tr

        for species, count in subhist.Items():
            subject.Add(species, count)
        subject.Done()

        self.RunSubject(subject, n_actual, q_actual, l_actual)

    def RunSubject(self, subject, n_actual, q_actual, l_actual):
        """Runs the analysis for a subject.

        subject: Subject
        n_actual: number of species
        q_actual: prevalence of unseen species
        l_actual: number of new species
        """
        # process and make prediction
        subject.Process(conc=self.conc, iters=100)
        subject.MakeQuickPrediction()

        # extract the posterior suite
        suite = subject.suite

        # check the distribution of n
        pmf_n = suite.DistN() 
        print 'n'
        self.total_n += self.CheckDistribution(pmf_n, n_actual, self.n_seq)

        # check the distribution of q
        pmf_q = suite.DistQ()
        print 'q'
        self.total_q += self.CheckDistribution(pmf_q, q_actual, self.q_seq)

        # check the distribution of additional species
        pmf_l = subject.DistL()
        print 'l'
        self.total_l += self.CheckDistribution(pmf_l, l_actual, self.l_seq)

    def CheckDistribution(self, pmf, actual, seq):
        """Checks a predictive distribution and returns a score vector.

        pmf: predictive distribution
        actual: actual value
        seq: which sequence to append (actual, mean) onto
        """
        mean = pmf.Mean()
        seq.append((actual, mean))

        cdf = pmf.MakeCdf()
        PrintPrediction(cdf, actual)

        sv = ScoreVector(cdf, self.ps, actual)
        return sv


def ScoreVector(cdf, ps, actual):
    """Checks whether the actual value falls in each credible interval.
    
    cdf: predictive distribution
    ps: percentages to check (0-100)
    actual: actual value

    Returns: numpy array of 0, 0.5, or 1
    """
    scores = []
    for p in ps:
        low, high = cdf.CredibleInterval(p)
        score = Score(low, high, actual)
        scores.append(score)

    return numpy.array(scores)


def Score(low, high, n):
    """Score whether the actual value falls in the range.

    Hitting the posts counts as 0.5, -1 is invalid.

    low: low end of range
    high: high end of range
    n: actual value

    Returns: -1, 0, 0.5 or 1
    """
    if n is None:
        return -1
    if low < n < high:
        return 1
    if n == low or n == high:
        return 0.5
    else:
        return 0


def FakeSubject(n=300, conc=0.1, num_reads=400, prevalences=None):
    """Makes a fake Subject.
    
    If prevalences is provided, n and conc are ignored.

    n: number of species
    conc: concentration parameter
    num_reads: number of reads
    prevalences: numpy array of prevalences (overrides n and conc)
    """
    # generate random prevalences
    if prevalences is None:
        dirichlet = thinkbayes.Dirichlet(n, conc=conc)
        prevalences = dirichlet.Random()
        prevalences.sort()

    # generate a simulated sample
    pmf = thinkbayes.MakePmfFromItems(enumerate(prevalences))
    cdf = pmf.MakeCdf()
    sample = cdf.Sample(num_reads)

    # collect the species counts
    hist = thinkbayes.MakeHistFromList(sample)

    # extract the data
    data = [count for species, count in hist.Items()]
    data.sort()

    # make a Subject and process
    subject = Subject('simulated')

    for species, count in hist.Items():
        subject.Add(species, count)
    subject.Done()

    return subject


def PlotSubjectCdf(code=None, clean_param=0):
    """Checks whether the Dirichlet model can replicate the data.
    """
    subject_map, uber_subject = ReadCompleteDataset(clean_param=clean_param)

    if code is None:
        subjects = subject_map.values()
        subject = random.choice(subjects)
        code = subject.code
    elif code == 'uber':
        subject = uber_subject
    else:
        subject = subject_map[code]

    print subject.code

    m = subject.GetM()

    subject.Process(high=m, conc=0.1, iters=0)
    print subject.suite.params[:m]

    # plot the cdf
    options = dict(linewidth=3, color='blue', alpha=0.5)
    cdf = subject.MakeCdf()
    thinkplot.Cdf(cdf, **options)

    options = dict(linewidth=1, color='green', alpha=0.5)

    # generate fake subjects and plot their CDFs
    for _ in range(10):
        prevalences = subject.suite.SamplePrevalences(m)
        fake = FakeSubject(prevalences=prevalences)
        cdf = fake.MakeCdf()
        thinkplot.Cdf(cdf, **options)

    root = 'species-cdf-%s' % code
    thinkplot.Save(root=root,
                   xlabel='rank',
                   ylabel='CDF',
                   xscale='log',
                   formats=FORMATS,
                   )


def RunCalibration(flag='cal', num_runs=100, clean_param=50):
    """Runs either the calibration or validation process.

    flag: string 'cal' or 'val'
    num_runs: how many runs
    clean_param: parameter used for data cleaning
    """
    cal = Calibrator(conc=0.1)

    if flag == 'val':
        cal.Validate(num_runs=num_runs, clean_param=clean_param)
    else:
        cal.Calibrate(num_runs=num_runs)

    cal.PlotN(root='species-n-%s' % flag)
    cal.PlotQ(root='species-q-%s' % flag)
    cal.PlotL(root='species-l-%s' % flag)
    cal.PlotCalibrationCurves(root='species5-%s' % flag)


def RunTests():
    """Runs calibration code and generates some figures."""
    RunCalibration(flag='val')
    RunCalibration(flag='cal')

    PlotSubjectCdf('B1558.G', clean_param=50)
    PlotSubjectCdf(None)


def main(script):
    RandomSeed(17)
    RunSubject('B1242', conc=1, high=100)

    RandomSeed(17)
    SimpleDirichletExample()

    RandomSeed(17)
    HierarchicalExample()


if __name__ == '__main__':
    main(*sys.argv)

########NEW FILE########
__FILENAME__ = thinkbayes
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

"""This file contains class definitions for:

Hist: represents a histogram (map from values to integer frequencies).

Pmf: represents a probability mass function (map from values to probs).

_DictWrapper: private parent class for Hist and Pmf.

Cdf: represents a discrete cumulative distribution function

Pdf: represents a continuous probability density function

"""

import bisect
import copy
import logging
import math
import numpy
import random

import scipy.stats
from scipy.special import erf, erfinv

ROOT2 = math.sqrt(2)

def RandomSeed(x):
    """Initialize the random and numpy.random generators.

    x: int seed
    """
    random.seed(x)
    numpy.random.seed(x)
    

def Odds(p):
    """Computes odds for a given probability.

    Example: p=0.75 means 75 for and 25 against, or 3:1 odds in favor.

    Note: when p=1, the formula for odds divides by zero, which is
    normally undefined.  But I think it is reasonable to define Odds(1)
    to be infinity, so that's what this function does.

    p: float 0-1

    Returns: float odds
    """
    if p == 1:
        return float('inf')
    return p / (1 - p)


def Probability(o):
    """Computes the probability corresponding to given odds.

    Example: o=2 means 2:1 odds in favor, or 2/3 probability

    o: float odds, strictly positive

    Returns: float probability
    """
    return o / (o + 1)


def Probability2(yes, no):
    """Computes the probability corresponding to given odds.

    Example: yes=2, no=1 means 2:1 odds in favor, or 2/3 probability.
    
    yes, no: int or float odds in favor
    """
    return float(yes) / (yes + no)


class Interpolator(object):
    """Represents a mapping between sorted sequences; performs linear interp.

    Attributes:
        xs: sorted list
        ys: sorted list
    """

    def __init__(self, xs, ys):
        self.xs = xs
        self.ys = ys

    def Lookup(self, x):
        """Looks up x and returns the corresponding value of y."""
        return self._Bisect(x, self.xs, self.ys)

    def Reverse(self, y):
        """Looks up y and returns the corresponding value of x."""
        return self._Bisect(y, self.ys, self.xs)

    def _Bisect(self, x, xs, ys):
        """Helper function."""
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect(xs, x)
        frac = 1.0 * (x - xs[i - 1]) / (xs[i] - xs[i - 1])
        y = ys[i - 1] + frac * 1.0 * (ys[i] - ys[i - 1])
        return y


class _DictWrapper(object):
    """An object that contains a dictionary."""

    def __init__(self, values=None, name=''):
        """Initializes the distribution.

        hypos: sequence of hypotheses
        """
        self.name = name
        self.d = {}

        # flag whether the distribution is under a log transform
        self.log = False

        if values is None:
            return

        init_methods = [
            self.InitPmf,
            self.InitMapping,
            self.InitSequence,
            self.InitFailure,
            ]

        for method in init_methods:
            try:
                method(values)
                break
            except AttributeError:
                continue

        if len(self) > 0:
            self.Normalize()

    def InitSequence(self, values):
        """Initializes with a sequence of equally-likely values.

        values: sequence of values
        """
        for value in values:
            self.Set(value, 1)

    def InitMapping(self, values):
        """Initializes with a map from value to probability.

        values: map from value to probability
        """
        for value, prob in values.iteritems():
            self.Set(value, prob)

    def InitPmf(self, values):
        """Initializes with a Pmf.

        values: Pmf object
        """
        for value, prob in values.Items():
            self.Set(value, prob)

    def InitFailure(self, values):
        """Raises an error."""
        raise ValueError('None of the initialization methods worked.')

    def __len__(self):
        return len(self.d)

    def __iter__(self):
        return iter(self.d)

    def iterkeys(self):
        return iter(self.d)

    def __contains__(self, value):
        return value in self.d

    def Copy(self, name=None):
        """Returns a copy.

        Make a shallow copy of d.  If you want a deep copy of d,
        use copy.deepcopy on the whole object.

        Args:
            name: string name for the new Hist
        """
        new = copy.copy(self)
        new.d = copy.copy(self.d)
        new.name = name if name is not None else self.name
        return new

    def Scale(self, factor):
        """Multiplies the values by a factor.

        factor: what to multiply by

        Returns: new object
        """
        new = self.Copy()
        new.d.clear()

        for val, prob in self.Items():
            new.Set(val * factor, prob)
        return new

    def Log(self, m=None):
        """Log transforms the probabilities.
        
        Removes values with probability 0.

        Normalizes so that the largest logprob is 0.
        """
        if self.log:
            raise ValueError("Pmf/Hist already under a log transform")
        self.log = True

        if m is None:
            m = self.MaxLike()

        for x, p in self.d.iteritems():
            if p:
                self.Set(x, math.log(p / m))
            else:
                self.Remove(x)

    def Exp(self, m=None):
        """Exponentiates the probabilities.

        m: how much to shift the ps before exponentiating

        If m is None, normalizes so that the largest prob is 1.
        """
        if not self.log:
            raise ValueError("Pmf/Hist not under a log transform")
        self.log = False

        if m is None:
            m = self.MaxLike()

        for x, p in self.d.iteritems():
            self.Set(x, math.exp(p - m))

    def GetDict(self):
        """Gets the dictionary."""
        return self.d

    def SetDict(self, d):
        """Sets the dictionary."""
        self.d = d

    def Values(self):
        """Gets an unsorted sequence of values.

        Note: one source of confusion is that the keys of this
        dictionary are the values of the Hist/Pmf, and the
        values of the dictionary are frequencies/probabilities.
        """
        return self.d.keys()

    def Items(self):
        """Gets an unsorted sequence of (value, freq/prob) pairs."""
        return self.d.items()

    def Render(self):
        """Generates a sequence of points suitable for plotting.

        Returns:
            tuple of (sorted value sequence, freq/prob sequence)
        """
        return zip(*sorted(self.Items()))

    def Print(self):
        """Prints the values and freqs/probs in ascending order."""
        for val, prob in sorted(self.d.iteritems()):
            print val, prob

    def Set(self, x, y=0):
        """Sets the freq/prob associated with the value x.

        Args:
            x: number value
            y: number freq or prob
        """
        self.d[x] = y

    def Incr(self, x, term=1):
        """Increments the freq/prob associated with the value x.

        Args:
            x: number value
            term: how much to increment by
        """
        self.d[x] = self.d.get(x, 0) + term

    def Mult(self, x, factor):
        """Scales the freq/prob associated with the value x.

        Args:
            x: number value
            factor: how much to multiply by
        """
        self.d[x] = self.d.get(x, 0) * factor

    def Remove(self, x):
        """Removes a value.

        Throws an exception if the value is not there.

        Args:
            x: value to remove
        """
        del self.d[x]

    def Total(self):
        """Returns the total of the frequencies/probabilities in the map."""
        total = sum(self.d.itervalues())
        return total

    def MaxLike(self):
        """Returns the largest frequency/probability in the map."""
        return max(self.d.itervalues())


class Hist(_DictWrapper):
    """Represents a histogram, which is a map from values to frequencies.

    Values can be any hashable type; frequencies are integer counters.
    """

    def Freq(self, x):
        """Gets the frequency associated with the value x.

        Args:
            x: number value

        Returns:
            int frequency
        """
        return self.d.get(x, 0)

    def Freqs(self, xs):
        """Gets frequencies for a sequence of values."""
        return [self.Freq(x) for x in xs]

    def IsSubset(self, other):
        """Checks whether the values in this histogram are a subset of
        the values in the given histogram."""
        for val, freq in self.Items():
            if freq > other.Freq(val):
                return False
        return True

    def Subtract(self, other):
        """Subtracts the values in the given histogram from this histogram."""
        for val, freq in other.Items():
            self.Incr(val, -freq)


class Pmf(_DictWrapper):
    """Represents a probability mass function.
    
    Values can be any hashable type; probabilities are floating-point.
    Pmfs are not necessarily normalized.
    """

    def Prob(self, x, default=0):
        """Gets the probability associated with the value x.

        Args:
            x: number value
            default: value to return if the key is not there

        Returns:
            float probability
        """
        return self.d.get(x, default)

    def Probs(self, xs):
        """Gets probabilities for a sequence of values."""
        return [self.Prob(x) for x in xs]

    def MakeCdf(self, name=None):
        """Makes a Cdf."""
        return MakeCdfFromPmf(self, name=name)

    def ProbGreater(self, x):
        """Probability that a sample from this Pmf exceeds x.

        x: number

        returns: float probability
        """
        t = [prob for (val, prob) in self.d.iteritems() if val > x]
        return sum(t)

    def ProbLess(self, x):
        """Probability that a sample from this Pmf is less than x.

        x: number

        returns: float probability
        """
        t = [prob for (val, prob) in self.d.iteritems() if val < x]
        return sum(t)

    def __lt__(self, obj):
        """Less than.

        obj: number or _DictWrapper

        returns: float probability
        """
        if isinstance(obj, _DictWrapper):
            return PmfProbLess(self, obj)
        else:
            return self.ProbLess(obj)

    def __gt__(self, obj):
        """Greater than.

        obj: number or _DictWrapper

        returns: float probability
        """
        if isinstance(obj, _DictWrapper):
            return PmfProbGreater(self, obj)
        else:
            return self.ProbGreater(obj)

    def __ge__(self, obj):
        """Greater than or equal.

        obj: number or _DictWrapper

        returns: float probability
        """
        return 1 - (self < obj)

    def __le__(self, obj):
        """Less than or equal.

        obj: number or _DictWrapper

        returns: float probability
        """
        return 1 - (self > obj)

    def __eq__(self, obj):
        """Less than.

        obj: number or _DictWrapper

        returns: float probability
        """
        if isinstance(obj, _DictWrapper):
            return PmfProbEqual(self, obj)
        else:
            return self.Prob(obj)

    def __ne__(self, obj):
        """Less than.

        obj: number or _DictWrapper

        returns: float probability
        """
        return 1 - (self == obj)

    def Normalize(self, fraction=1.0):
        """Normalizes this PMF so the sum of all probs is fraction.

        Args:
            fraction: what the total should be after normalization

        Returns: the total probability before normalizing
        """
        if self.log:
            raise ValueError("Pmf is under a log transform")

        total = self.Total()
        if total == 0.0:
            raise ValueError('total probability is zero.')
            logging.warning('Normalize: total probability is zero.')
            return total

        factor = float(fraction) / total
        for x in self.d:
            self.d[x] *= factor

        return total

    def Random(self):
        """Chooses a random element from this PMF.

        Returns:
            float value from the Pmf
        """
        if len(self.d) == 0:
            raise ValueError('Pmf contains no values.')

        target = random.random()
        total = 0.0
        for x, p in self.d.iteritems():
            total += p
            if total >= target:
                return x

        # we shouldn't get here
        assert False

    def Mean(self):
        """Computes the mean of a PMF.

        Returns:
            float mean
        """
        mu = 0.0
        for x, p in self.d.iteritems():
            mu += p * x
        return mu

    def Var(self, mu=None):
        """Computes the variance of a PMF.

        Args:
            mu: the point around which the variance is computed;
                if omitted, computes the mean

        Returns:
            float variance
        """
        if mu is None:
            mu = self.Mean()

        var = 0.0
        for x, p in self.d.iteritems():
            var += p * (x - mu) ** 2
        return var

    def MaximumLikelihood(self):
        """Returns the value with the highest probability.

        Returns: float probability
        """
        prob, val = max((prob, val) for val, prob in self.Items())
        return val

    def CredibleInterval(self, percentage=90):
        """Computes the central credible interval.

        If percentage=90, computes the 90% CI.

        Args:
            percentage: float between 0 and 100

        Returns:
            sequence of two floats, low and high
        """
        cdf = self.MakeCdf()
        return cdf.CredibleInterval(percentage)

    def __add__(self, other):
        """Computes the Pmf of the sum of values drawn from self and other.

        other: another Pmf

        returns: new Pmf
        """
        try:
            return self.AddPmf(other)
        except AttributeError:
            return self.AddConstant(other)

    def AddPmf(self, other):
        """Computes the Pmf of the sum of values drawn from self and other.

        other: another Pmf

        returns: new Pmf
        """
        pmf = Pmf()
        for v1, p1 in self.Items():
            for v2, p2 in other.Items():
                pmf.Incr(v1 + v2, p1 * p2)
        return pmf

    def AddConstant(self, other):
        """Computes the Pmf of the sum a constant and  values from self.

        other: a number

        returns: new Pmf
        """
        pmf = Pmf()
        for v1, p1 in self.Items():
            pmf.Set(v1 + other, p1)
        return pmf

    def __sub__(self, other):
        """Computes the Pmf of the diff of values drawn from self and other.

        other: another Pmf

        returns: new Pmf
        """
        pmf = Pmf()
        for v1, p1 in self.Items():
            for v2, p2 in other.Items():
                pmf.Incr(v1 - v2, p1 * p2)
        return pmf

    def Max(self, k):
        """Computes the CDF of the maximum of k selections from this dist.

        k: int

        returns: new Cdf
        """
        cdf = self.MakeCdf()
        cdf.ps = [p ** k for p in cdf.ps]
        return cdf


class Joint(Pmf):
    """Represents a joint distribution.

    The values are sequences (usually tuples)
    """

    def Marginal(self, i, name=''):
        """Gets the marginal distribution of the indicated variable.

        i: index of the variable we want

        Returns: Pmf
        """
        pmf = Pmf(name=name)
        for vs, prob in self.Items():
            pmf.Incr(vs[i], prob)
        return pmf

    def Conditional(self, i, j, val, name=''):
        """Gets the conditional distribution of the indicated variable.

        Distribution of vs[i], conditioned on vs[j] = val.

        i: index of the variable we want
        j: which variable is conditioned on
        val: the value the jth variable has to have

        Returns: Pmf
        """
        pmf = Pmf(name=name)
        for vs, prob in self.Items():
            if vs[j] != val: continue
            pmf.Incr(vs[i], prob)

        pmf.Normalize()
        return pmf

    def MaxLikeInterval(self, percentage=90):
        """Returns the maximum-likelihood credible interval.

        If percentage=90, computes a 90% CI containing the values
        with the highest likelihoods.

        percentage: float between 0 and 100

        Returns: list of values from the suite
        """
        interval = []
        total = 0

        t = [(prob, val) for val, prob in self.Items()]
        t.sort(reverse=True)

        for prob, val in t:
            interval.append(val)
            total += prob
            if total >= percentage / 100.0:
                break

        return interval


def MakeJoint(pmf1, pmf2):
    """Joint distribution of values from pmf1 and pmf2.

    Args:
        pmf1: Pmf object
        pmf2: Pmf object

    Returns:
        Joint pmf of value pairs
    """
    joint = Joint()
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            joint.Set((v1, v2), p1 * p2)
    return joint


def MakeHistFromList(t, name=''):
    """Makes a histogram from an unsorted sequence of values.

    Args:
        t: sequence of numbers
        name: string name for this histogram

    Returns:
        Hist object
    """
    hist = Hist(name=name)
    [hist.Incr(x) for x in t]
    return hist


def MakeHistFromDict(d, name=''):
    """Makes a histogram from a map from values to frequencies.

    Args:
        d: dictionary that maps values to frequencies
        name: string name for this histogram

    Returns:
        Hist object
    """
    return Hist(d, name)


def MakePmfFromList(t, name=''):
    """Makes a PMF from an unsorted sequence of values.

    Args:
        t: sequence of numbers
        name: string name for this PMF

    Returns:
        Pmf object
    """
    hist = MakeHistFromList(t)
    d = hist.GetDict()
    pmf = Pmf(d, name)
    pmf.Normalize()
    return pmf


def MakePmfFromDict(d, name=''):
    """Makes a PMF from a map from values to probabilities.

    Args:
        d: dictionary that maps values to probabilities
        name: string name for this PMF

    Returns:
        Pmf object
    """
    pmf = Pmf(d, name)
    pmf.Normalize()
    return pmf


def MakePmfFromItems(t, name=''):
    """Makes a PMF from a sequence of value-probability pairs

    Args:
        t: sequence of value-probability pairs
        name: string name for this PMF

    Returns:
        Pmf object
    """
    pmf = Pmf(dict(t), name)
    pmf.Normalize()
    return pmf


def MakePmfFromHist(hist, name=None):
    """Makes a normalized PMF from a Hist object.

    Args:
        hist: Hist object
        name: string name

    Returns:
        Pmf object
    """
    if name is None:
        name = hist.name

    # make a copy of the dictionary
    d = dict(hist.GetDict())
    pmf = Pmf(d, name)
    pmf.Normalize()
    return pmf


def MakePmfFromCdf(cdf, name=None):
    """Makes a normalized Pmf from a Cdf object.

    Args:
        cdf: Cdf object
        name: string name for the new Pmf

    Returns:
        Pmf object
    """
    if name is None:
        name = cdf.name

    pmf = Pmf(name=name)

    prev = 0.0
    for val, prob in cdf.Items():
        pmf.Incr(val, prob - prev)
        prev = prob

    return pmf


def MakeMixture(metapmf, name='mix'):
    """Make a mixture distribution.

    Args:
      metapmf: Pmf that maps from Pmfs to probs.
      name: string name for the new Pmf.

    Returns: Pmf object.
    """
    mix = Pmf(name=name)
    for pmf, p1 in metapmf.Items():
        for x, p2 in pmf.Items():
            mix.Incr(x, p1 * p2)
    return mix


def MakeUniformPmf(low, high, n):
    """Make a uniform Pmf.

    low: lowest value (inclusive)
    high: highest value (inclusize)
    n: number of values
    """
    pmf = Pmf()
    for x in numpy.linspace(low, high, n):
        pmf.Set(x, 1)
    pmf.Normalize()
    return pmf


class Cdf(object):
    """Represents a cumulative distribution function.

    Attributes:
        xs: sequence of values
        ps: sequence of probabilities
        name: string used as a graph label.
    """

    def __init__(self, xs=None, ps=None, name=''):
        self.xs = [] if xs is None else xs
        self.ps = [] if ps is None else ps
        self.name = name

    def Copy(self, name=None):
        """Returns a copy of this Cdf.

        Args:
            name: string name for the new Cdf
        """
        if name is None:
            name = self.name
        return Cdf(list(self.xs), list(self.ps), name)

    def MakePmf(self, name=None):
        """Makes a Pmf."""
        return MakePmfFromCdf(self, name=name)

    def Values(self):
        """Returns a sorted list of values.
        """
        return self.xs

    def Items(self):
        """Returns a sorted sequence of (value, probability) pairs.

        Note: in Python3, returns an iterator.
        """
        return zip(self.xs, self.ps)

    def Append(self, x, p):
        """Add an (x, p) pair to the end of this CDF.

        Note: this us normally used to build a CDF from scratch, not
        to modify existing CDFs.  It is up to the caller to make sure
        that the result is a legal CDF.
        """
        self.xs.append(x)
        self.ps.append(p)

    def Shift(self, term):
        """Adds a term to the xs.

        term: how much to add
        """
        new = self.Copy()
        new.xs = [x + term for x in self.xs]
        return new

    def Scale(self, factor):
        """Multiplies the xs by a factor.

        factor: what to multiply by
        """
        new = self.Copy()
        new.xs = [x * factor for x in self.xs]
        return new

    def Prob(self, x):
        """Returns CDF(x), the probability that corresponds to value x.

        Args:
            x: number

        Returns:
            float probability
        """
        if x < self.xs[0]: return 0.0
        index = bisect.bisect(self.xs, x)
        p = self.ps[index - 1]
        return p

    def Value(self, p):
        """Returns InverseCDF(p), the value that corresponds to probability p.

        Args:
            p: number in the range [0, 1]

        Returns:
            number value
        """
        if p < 0 or p > 1:
            raise ValueError('Probability p must be in range [0, 1]')

        if p == 0: return self.xs[0]
        if p == 1: return self.xs[-1]
        index = bisect.bisect(self.ps, p)
        if p == self.ps[index - 1]:
            return self.xs[index - 1]
        else:
            return self.xs[index]

    def Percentile(self, p):
        """Returns the value that corresponds to percentile p.

        Args:
            p: number in the range [0, 100]

        Returns:
            number value
        """
        return self.Value(p / 100.0)

    def Random(self):
        """Chooses a random value from this distribution."""
        return self.Value(random.random())

    def Sample(self, n):
        """Generates a random sample from this distribution.
        
        Args:
            n: int length of the sample
        """
        return [self.Random() for i in range(n)]

    def Mean(self):
        """Computes the mean of a CDF.

        Returns:
            float mean
        """
        old_p = 0
        total = 0.0
        for x, new_p in zip(self.xs, self.ps):
            p = new_p - old_p
            total += p * x
            old_p = new_p
        return total

    def CredibleInterval(self, percentage=90):
        """Computes the central credible interval.

        If percentage=90, computes the 90% CI.

        Args:
            percentage: float between 0 and 100

        Returns:
            sequence of two floats, low and high
        """
        prob = (1 - percentage / 100.0) / 2
        interval = self.Value(prob), self.Value(1 - prob)
        return interval

    def _Round(self, multiplier=1000.0):
        """
        An entry is added to the cdf only if the percentile differs
        from the previous value in a significant digit, where the number
        of significant digits is determined by multiplier.  The
        default is 1000, which keeps log10(1000) = 3 significant digits.
        """
        # TODO(write this method)
        raise UnimplementedMethodException()

    def Render(self):
        """Generates a sequence of points suitable for plotting.

        An empirical CDF is a step function; linear interpolation
        can be misleading.

        Returns:
            tuple of (xs, ps)
        """
        xs = [self.xs[0]]
        ps = [0.0]
        for i, p in enumerate(self.ps):
            xs.append(self.xs[i])
            ps.append(p)

            try:
                xs.append(self.xs[i + 1])
                ps.append(p)
            except IndexError:
                pass
        return xs, ps

    def Max(self, k):
        """Computes the CDF of the maximum of k selections from this dist.

        k: int

        returns: new Cdf
        """
        cdf = self.Copy()
        cdf.ps = [p ** k for p in cdf.ps]
        return cdf


def MakeCdfFromItems(items, name=''):
    """Makes a cdf from an unsorted sequence of (value, frequency) pairs.

    Args:
        items: unsorted sequence of (value, frequency) pairs
        name: string name for this CDF

    Returns:
        cdf: list of (value, fraction) pairs
    """
    runsum = 0
    xs = []
    cs = []

    for value, count in sorted(items):
        runsum += count
        xs.append(value)
        cs.append(runsum)

    total = float(runsum)
    ps = [c / total for c in cs]

    cdf = Cdf(xs, ps, name)
    return cdf


def MakeCdfFromDict(d, name=''):
    """Makes a CDF from a dictionary that maps values to frequencies.

    Args:
       d: dictionary that maps values to frequencies.
       name: string name for the data.

    Returns:
        Cdf object
    """
    return MakeCdfFromItems(d.iteritems(), name)


def MakeCdfFromHist(hist, name=''):
    """Makes a CDF from a Hist object.

    Args:
       hist: Pmf.Hist object
       name: string name for the data.

    Returns:
        Cdf object
    """
    return MakeCdfFromItems(hist.Items(), name)


def MakeCdfFromPmf(pmf, name=None):
    """Makes a CDF from a Pmf object.

    Args:
       pmf: Pmf.Pmf object
       name: string name for the data.

    Returns:
        Cdf object
    """
    if name == None:
        name = pmf.name
    return MakeCdfFromItems(pmf.Items(), name)


def MakeCdfFromList(seq, name=''):
    """Creates a CDF from an unsorted sequence.

    Args:
        seq: unsorted sequence of sortable values
        name: string name for the cdf

    Returns:
       Cdf object
    """
    hist = MakeHistFromList(seq)
    return MakeCdfFromHist(hist, name)


class UnimplementedMethodException(Exception):
    """Exception if someone calls a method that should be overridden."""


class Suite(Pmf):
    """Represents a suite of hypotheses and their probabilities."""

    def Update(self, data):
        """Updates each hypothesis based on the data.

        data: any representation of the data

        returns: the normalizing constant
        """
        for hypo in self.Values():
            like = self.Likelihood(data, hypo)
            self.Mult(hypo, like)
        return self.Normalize()

    def LogUpdate(self, data):
        """Updates a suite of hypotheses based on new data.

        Modifies the suite directly; if you want to keep the original, make
        a copy.

        Note: unlike Update, LogUpdate does not normalize.

        Args:
            data: any representation of the data
        """
        for hypo in self.Values():
            like = self.LogLikelihood(data, hypo)
            self.Incr(hypo, like)

    def UpdateSet(self, dataset):
        """Updates each hypothesis based on the dataset.

        This is more efficient than calling Update repeatedly because
        it waits until the end to Normalize.

        Modifies the suite directly; if you want to keep the original, make
        a copy.

        dataset: a sequence of data

        returns: the normalizing constant
        """
        for data in dataset:
            for hypo in self.Values():
                like = self.Likelihood(data, hypo)
                self.Mult(hypo, like)
        return self.Normalize()

    def LogUpdateSet(self, dataset):
        """Updates each hypothesis based on the dataset.

        Modifies the suite directly; if you want to keep the original, make
        a copy.

        dataset: a sequence of data

        returns: None
        """
        for data in dataset:
            self.LogUpdate(data)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        hypo: some representation of the hypothesis
        data: some representation of the data
        """
        raise UnimplementedMethodException()

    def LogLikelihood(self, data, hypo):
        """Computes the log likelihood of the data under the hypothesis.

        hypo: some representation of the hypothesis
        data: some representation of the data
        """
        raise UnimplementedMethodException()

    def Print(self):
        """Prints the hypotheses and their probabilities."""
        for hypo, prob in sorted(self.Items()):
            print hypo, prob

    def MakeOdds(self):
        """Transforms from probabilities to odds.

        Values with prob=0 are removed.
        """
        for hypo, prob in self.Items():
            if prob:
                self.Set(hypo, Odds(prob))
            else:
                self.Remove(hypo)

    def MakeProbs(self):
        """Transforms from odds to probabilities."""
        for hypo, odds in self.Items():
            self.Set(hypo, Probability(odds))


def MakeSuiteFromList(t, name=''):
    """Makes a suite from an unsorted sequence of values.

    Args:
        t: sequence of numbers
        name: string name for this suite

    Returns:
        Suite object
    """
    hist = MakeHistFromList(t)
    d = hist.GetDict()
    return MakeSuiteFromDict(d)


def MakeSuiteFromHist(hist, name=None):
    """Makes a normalized suite from a Hist object.

    Args:
        hist: Hist object
        name: string name

    Returns:
        Suite object
    """
    if name is None:
        name = hist.name

    # make a copy of the dictionary
    d = dict(hist.GetDict())
    return MakeSuiteFromDict(d, name)


def MakeSuiteFromDict(d, name=''):
    """Makes a suite from a map from values to probabilities.

    Args:
        d: dictionary that maps values to probabilities
        name: string name for this suite

    Returns:
        Suite object
    """
    suite = Suite(name=name)
    suite.SetDict(d)
    suite.Normalize()
    return suite


def MakeSuiteFromCdf(cdf, name=None):
    """Makes a normalized Suite from a Cdf object.

    Args:
        cdf: Cdf object
        name: string name for the new Suite

    Returns:
        Suite object
    """
    if name is None:
        name = cdf.name

    suite = Suite(name=name)

    prev = 0.0
    for val, prob in cdf.Items():
        suite.Incr(val, prob - prev)
        prev = prob

    return suite


class Pdf(object):
    """Represents a probability density function (PDF)."""

    def Density(self, x):
        """Evaluates this Pdf at x.

        Returns: float probability density
        """
        raise UnimplementedMethodException()

    def MakePmf(self, xs, name=''):
        """Makes a discrete version of this Pdf, evaluated at xs.

        xs: equally-spaced sequence of values

        Returns: new Pmf
        """
        pmf = Pmf(name=name)
        for x in xs:
            pmf.Set(x, self.Density(x))
        pmf.Normalize()
        return pmf


class GaussianPdf(Pdf):
    """Represents the PDF of a Gaussian distribution."""

    def __init__(self, mu, sigma):
        """Constructs a Gaussian Pdf with given mu and sigma.

        mu: mean
        sigma: standard deviation
        """
        self.mu = mu
        self.sigma = sigma

    def Density(self, x):
        """Evaluates this Pdf at x.

        Returns: float probability density
        """
        return EvalGaussianPdf(x, self.mu, self.sigma)


class EstimatedPdf(Pdf):
    """Represents a PDF estimated by KDE."""

    def __init__(self, sample):
        """Estimates the density function based on a sample.

        sample: sequence of data
        """
        self.kde = scipy.stats.gaussian_kde(sample)

    def Density(self, x):
        """Evaluates this Pdf at x.

        Returns: float probability density
        """
        return self.kde.evaluate(x)

    def MakePmf(self, xs, name=''):
        ps = self.kde.evaluate(xs)
        pmf = MakePmfFromItems(zip(xs, ps), name=name)
        return pmf


def Percentile(pmf, percentage):
    """Computes a percentile of a given Pmf.

    percentage: float 0-100
    """
    p = percentage / 100.0
    total = 0
    for val, prob in pmf.Items():
        total += prob
        if total >= p:
            return val


def CredibleInterval(pmf, percentage=90):
    """Computes a credible interval for a given distribution.

    If percentage=90, computes the 90% CI.

    Args:
        pmf: Pmf object representing a posterior distribution
        percentage: float between 0 and 100

    Returns:
        sequence of two floats, low and high
    """
    cdf = pmf.MakeCdf()
    prob = (1 - percentage / 100.0) / 2
    interval = cdf.Value(prob), cdf.Value(1 - prob)
    return interval


def PmfProbLess(pmf1, pmf2):
    """Probability that a value from pmf1 is less than a value from pmf2.

    Args:
        pmf1: Pmf object
        pmf2: Pmf object

    Returns:
        float probability
    """
    total = 0.0
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            if v1 < v2:
                total += p1 * p2
    return total


def PmfProbGreater(pmf1, pmf2):
    """Probability that a value from pmf1 is less than a value from pmf2.

    Args:
        pmf1: Pmf object
        pmf2: Pmf object

    Returns:
        float probability
    """
    total = 0.0
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            if v1 > v2:
                total += p1 * p2
    return total


def PmfProbEqual(pmf1, pmf2):
    """Probability that a value from pmf1 equals a value from pmf2.

    Args:
        pmf1: Pmf object
        pmf2: Pmf object

    Returns:
        float probability
    """
    total = 0.0
    for v1, p1 in pmf1.Items():
        for v2, p2 in pmf2.Items():
            if v1 == v2:
                total += p1 * p2
    return total


def RandomSum(dists):
    """Chooses a random value from each dist and returns the sum.

    dists: sequence of Pmf or Cdf objects

    returns: numerical sum
    """
    total = sum(dist.Random() for dist in dists)
    return total


def SampleSum(dists, n):
    """Draws a sample of sums from a list of distributions.

    dists: sequence of Pmf or Cdf objects
    n: sample size

    returns: new Pmf of sums
    """
    pmf = MakePmfFromList(RandomSum(dists) for i in xrange(n))
    return pmf


def EvalGaussianPdf(x, mu, sigma):
    """Computes the unnormalized PDF of the normal distribution.

    x: value
    mu: mean
    sigma: standard deviation
    
    returns: float probability density
    """
    return scipy.stats.norm.pdf(x, mu, sigma)


def MakeGaussianPmf(mu, sigma, num_sigmas, n=201):
    """Makes a PMF discrete approx to a Gaussian distribution.
    
    mu: float mean
    sigma: float standard deviation
    num_sigmas: how many sigmas to extend in each direction
    n: number of values in the Pmf

    returns: normalized Pmf
    """
    pmf = Pmf()
    low = mu - num_sigmas * sigma
    high = mu + num_sigmas * sigma

    for x in numpy.linspace(low, high, n):
        p = EvalGaussianPdf(x, mu, sigma)
        pmf.Set(x, p)
    pmf.Normalize()
    return pmf


def EvalBinomialPmf(k, n, p):
    """Evaluates the binomial pmf.

    Returns the probabily of k successes in n trials with probability p.
    """
    return scipy.stats.binom.pmf(k, n, p)
    

def EvalPoissonPmf(k, lam):
    """Computes the Poisson PMF.

    k: number of events
    lam: parameter lambda in events per unit time

    returns: float probability
    """
    # don't use the scipy function (yet).  for lam=0 it returns NaN;
    # should be 0.0
    # return scipy.stats.poisson.pmf(k, lam)

    return lam ** k * math.exp(-lam) / math.factorial(k)


def MakePoissonPmf(lam, high, step=1):
    """Makes a PMF discrete approx to a Poisson distribution.

    lam: parameter lambda in events per unit time
    high: upper bound of the Pmf

    returns: normalized Pmf
    """
    pmf = Pmf()
    for k in xrange(0, high + 1, step):
        p = EvalPoissonPmf(k, lam)
        pmf.Set(k, p)
    pmf.Normalize()
    return pmf


def EvalExponentialPdf(x, lam):
    """Computes the exponential PDF.

    x: value
    lam: parameter lambda in events per unit time

    returns: float probability density
    """
    return lam * math.exp(-lam * x)


def EvalExponentialCdf(x, lam):
    """Evaluates CDF of the exponential distribution with parameter lam."""
    return 1 - math.exp(-lam * x)


def MakeExponentialPmf(lam, high, n=200):
    """Makes a PMF discrete approx to an exponential distribution.

    lam: parameter lambda in events per unit time
    high: upper bound
    n: number of values in the Pmf

    returns: normalized Pmf
    """
    pmf = Pmf()
    for x in numpy.linspace(0, high, n):
        p = EvalExponentialPdf(x, lam)
        pmf.Set(x, p)
    pmf.Normalize()
    return pmf


def StandardGaussianCdf(x):
    """Evaluates the CDF of the standard Gaussian distribution.
    
    See http://en.wikipedia.org/wiki/Normal_distribution
    #Cumulative_distribution_function

    Args:
        x: float
                
    Returns:
        float
    """
    return (erf(x / ROOT2) + 1) / 2


def GaussianCdf(x, mu=0, sigma=1):
    """Evaluates the CDF of the gaussian distribution.
    
    Args:
        x: float

        mu: mean parameter
        
        sigma: standard deviation parameter
                
    Returns:
        float
    """
    return StandardGaussianCdf(float(x - mu) / sigma)


def GaussianCdfInverse(p, mu=0, sigma=1):
    """Evaluates the inverse CDF of the gaussian distribution.

    See http://en.wikipedia.org/wiki/Normal_distribution#Quantile_function  

    Args:
        p: float

        mu: mean parameter
        
        sigma: standard deviation parameter
                
    Returns:
        float
    """
    x = ROOT2 * erfinv(2 * p - 1)
    return mu + x * sigma


class Beta(object):
    """Represents a Beta distribution.

    See http://en.wikipedia.org/wiki/Beta_distribution
    """
    def __init__(self, alpha=1, beta=1, name=''):
        """Initializes a Beta distribution."""
        self.alpha = alpha
        self.beta = beta
        self.name = name

    def Update(self, data):
        """Updates a Beta distribution.

        data: pair of int (heads, tails)
        """
        heads, tails = data
        self.alpha += heads
        self.beta += tails

    def Mean(self):
        """Computes the mean of this distribution."""
        return float(self.alpha) / (self.alpha + self.beta)

    def Random(self):
        """Generates a random variate from this distribution."""
        return random.betavariate(self.alpha, self.beta)

    def Sample(self, n):
        """Generates a random sample from this distribution.

        n: int sample size
        """
        size = n,
        return numpy.random.beta(self.alpha, self.beta, size)

    def EvalPdf(self, x):
        """Evaluates the PDF at x."""
        return x ** (self.alpha - 1) * (1 - x) ** (self.beta - 1)

    def MakePmf(self, steps=101, name=''):
        """Returns a Pmf of this distribution.

        Note: Normally, we just evaluate the PDF at a sequence
        of points and treat the probability density as a probability
        mass.

        But if alpha or beta is less than one, we have to be
        more careful because the PDF goes to infinity at x=0
        and x=1.  In that case we evaluate the CDF and compute
        differences.
        """
        if self.alpha < 1 or self.beta < 1:
            cdf = self.MakeCdf()
            pmf = cdf.MakePmf()
            return pmf

        xs = [i / (steps - 1.0) for i in xrange(steps)]
        probs = [self.EvalPdf(x) for x in xs]
        pmf = MakePmfFromDict(dict(zip(xs, probs)), name)
        return pmf

    def MakeCdf(self, steps=101):
        """Returns the CDF of this distribution."""
        xs = [i / (steps - 1.0) for i in xrange(steps)]
        ps = [scipy.special.betainc(self.alpha, self.beta, x) for x in xs]
        cdf = Cdf(xs, ps)
        return cdf


class Dirichlet(object):
    """Represents a Dirichlet distribution.

    See http://en.wikipedia.org/wiki/Dirichlet_distribution
    """

    def __init__(self, n, conc=1, name=''):
        """Initializes a Dirichlet distribution.

        n: number of dimensions
        conc: concentration parameter (smaller yields more concentration)
        name: string name
        """
        if n < 2:
            raise ValueError('A Dirichlet distribution with '
                             'n<2 makes no sense')

        self.n = n
        self.params = numpy.ones(n, dtype=numpy.float) * conc
        self.name = name

    def Update(self, data):
        """Updates a Dirichlet distribution.

        data: sequence of observations, in order corresponding to params
        """
        m = len(data)
        self.params[:m] += data

    def Random(self):
        """Generates a random variate from this distribution.

        Returns: normalized vector of fractions
        """
        p = numpy.random.gamma(self.params)
        return p / p.sum()

    def Likelihood(self, data):
        """Computes the likelihood of the data.

        Selects a random vector of probabilities from this distribution.

        Returns: float probability
        """
        m = len(data)
        if self.n < m:
            return 0

        x = data
        p = self.Random()
        q = p[:m] ** x
        return q.prod()

    def LogLikelihood(self, data):
        """Computes the log likelihood of the data.

        Selects a random vector of probabilities from this distribution.

        Returns: float log probability
        """
        m = len(data)
        if self.n < m:
            return float('-inf')

        x = self.Random()
        y = numpy.log(x[:m]) * data
        return y.sum()

    def MarginalBeta(self, i):
        """Computes the marginal distribution of the ith element.

        See http://en.wikipedia.org/wiki/Dirichlet_distribution
        #Marginal_distributions

        i: int

        Returns: Beta object
        """
        alpha0 = self.params.sum()
        alpha = self.params[i]
        return Beta(alpha, alpha0 - alpha)

    def PredictivePmf(self, xs, name=''):
        """Makes a predictive distribution.

        xs: values to go into the Pmf

        Returns: Pmf that maps from x to the mean prevalence of x
        """
        alpha0 = self.params.sum()
        ps = self.params / alpha0
        return MakePmfFromItems(zip(xs, ps), name=name)


def BinomialCoef(n, k):
    """Compute the binomial coefficient "n choose k".

    n: number of trials
    k: number of successes

    Returns: float
    """
    return scipy.misc.comb(n, k)


def LogBinomialCoef(n, k):
    """Computes the log of the binomial coefficient.

    http://math.stackexchange.com/questions/64716/
    approximating-the-logarithm-of-the-binomial-coefficient

    n: number of trials
    k: number of successes

    Returns: float
    """
    return n * log(n) - k * log(k) - (n - k) * log(n - k)



########NEW FILE########
__FILENAME__ = thinkplot
"""This file contains code for use with "Think Stats",
by Allen B. Downey, available from greenteapress.com

Copyright 2010 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math
import matplotlib
import matplotlib.pyplot as pyplot
import numpy as np

# customize some matplotlib attributes
#matplotlib.rc('figure', figsize=(4, 3))

#matplotlib.rc('font', size=14.0)
#matplotlib.rc('axes', labelsize=22.0, titlesize=22.0)
#matplotlib.rc('legend', fontsize=20.0)

#matplotlib.rc('xtick.major', size=6.0)
#matplotlib.rc('xtick.minor', size=3.0)

#matplotlib.rc('ytick.major', size=6.0)
#matplotlib.rc('ytick.minor', size=3.0)


class Brewer(object):
    """Encapsulates a nice sequence of colors.

    Shades of blue that look good in color and can be distinguished
    in grayscale (up to a point).
    
    Borrowed from http://colorbrewer2.org/
    """
    color_iter = None

    colors = ['#081D58',
              '#253494',
              '#225EA8',
              '#1D91C0',
              '#41B6C4',
              '#7FCDBB',
              '#C7E9B4',
              '#EDF8B1',
              '#FFFFD9']

    # lists that indicate which colors to use depending on how many are used
    which_colors = [[],
                    [1],
                    [1, 3],
                    [0, 2, 4],
                    [0, 2, 4, 6],
                    [0, 2, 3, 5, 6],
                    [0, 2, 3, 4, 5, 6],
                    [0, 1, 2, 3, 4, 5, 6],
                    ]

    @classmethod
    def Colors(cls):
        """Returns the list of colors.
        """
        return cls.colors

    @classmethod
    def ColorGenerator(cls, n):
        """Returns an iterator of color strings.

        n: how many colors will be used
        """
        for i in cls.which_colors[n]:
            yield cls.colors[i]
        raise StopIteration('Ran out of colors in Brewer.ColorGenerator')

    @classmethod
    def InitializeIter(cls, num):
        """Initializes the color iterator with the given number of colors."""
        cls.color_iter = cls.ColorGenerator(num)

    @classmethod
    def ClearIter(cls):
        """Sets the color iterator to None."""
        cls.color_iter = None

    @classmethod
    def GetIter(cls):
        """Gets the color iterator."""
        return cls.color_iter


def PrePlot(num=None, rows=1, cols=1):
    """Takes hints about what's coming.

    num: number of lines that will be plotted
    """
    if num:
        Brewer.InitializeIter(num)

    # TODO: get sharey and sharex working.  probably means switching
    # to subplots instead of subplot.
    # also, get rid of the gray background.

    if rows > 1 or cols > 1:
        pyplot.subplots(rows, cols, sharey=True)
        global SUBPLOT_ROWS, SUBPLOT_COLS
        SUBPLOT_ROWS = rows
        SUBPLOT_COLS = cols
    

def SubPlot(plot_number):
    pyplot.subplot(SUBPLOT_ROWS, SUBPLOT_COLS, plot_number)


class InfiniteList(list):
    """A list that returns the same value for all indices."""
    def __init__(self, val):
        """Initializes the list.

        val: value to be stored
        """
        list.__init__(self)
        self.val = val

    def __getitem__(self, index):
        """Gets the item with the given index.

        index: int

        returns: the stored value
        """
        return self.val


def Underride(d, **options):
    """Add key-value pairs to d only if key is not in d.

    If d is None, create a new dictionary.

    d: dictionary
    options: keyword args to add to d
    """
    if d is None:
        d = {}

    for key, val in options.iteritems():
        d.setdefault(key, val)

    return d


def Clf():
    """Clears the figure and any hints that have been set."""
    Brewer.ClearIter()
    pyplot.clf()
    

def Figure(**options):
    """Sets options for the current figure."""
    Underride(options, figsize=(6, 8))
    pyplot.figure(**options)
    

def Plot(xs, ys, style='', **options):
    """Plots a line.

    Args:
      xs: sequence of x values
      ys: sequence of y values
      style: style string passed along to pyplot.plot
      options: keyword args passed to pyplot.plot
    """
    color_iter = Brewer.GetIter()

    if color_iter:
        try:
            options = Underride(options, color=color_iter.next())
        except StopIteration:
            print 'Warning: Brewer ran out of colors.'
            Brewer.ClearIter()
        
    options = Underride(options, linewidth=3, alpha=0.8)
    pyplot.plot(xs, ys, style, **options)


def Scatter(xs, ys, **options):
    """Makes a scatter plot.

    xs: x values
    ys: y values
    options: options passed to pyplot.scatter
    """
    options = Underride(options, color='blue', alpha=0.2, 
                        s=30, edgecolors='none')
    pyplot.scatter(xs, ys, **options)


def Pmf(pmf, **options):
    """Plots a Pmf or Hist as a line.

    Args:
      pmf: Hist or Pmf object
      options: keyword args passed to pyplot.plot
    """
    xs, ps = pmf.Render()
    if pmf.name:
        options = Underride(options, label=pmf.name)
    Plot(xs, ps, **options)


def Pmfs(pmfs, **options):
    """Plots a sequence of PMFs.

    Options are passed along for all PMFs.  If you want different
    options for each pmf, make multiple calls to Pmf.
    
    Args:
      pmfs: sequence of PMF objects
      options: keyword args passed to pyplot.plot
    """
    for pmf in pmfs:
        Pmf(pmf, **options)


def Hist(hist, **options):
    """Plots a Pmf or Hist with a bar plot.

    Args:
      hist: Hist or Pmf object
      options: keyword args passed to pyplot.bar
    """
    # find the minimum distance between adjacent values
    xs, fs = hist.Render()
    width = min(Diff(xs))

    if hist.name:
        options = Underride(options, label=hist.name)

    options = Underride(options, 
                        align='center',
                        linewidth=0,
                        width=width)

    pyplot.bar(xs, fs, **options)


def Hists(hists, **options):
    """Plots two histograms as interleaved bar plots.

    Options are passed along for all PMFs.  If you want different
    options for each pmf, make multiple calls to Pmf.

    Args:
      hists: list of two Hist or Pmf objects
      options: keyword args passed to pyplot.plot
    """
    for hist in hists:
        Hist(hist, **options)


def Diff(t):
    """Compute the differences between adjacent elements in a sequence.

    Args:
        t: sequence of number

    Returns:
        sequence of differences (length one less than t)
    """
    diffs = [t[i+1] - t[i] for i in range(len(t)-1)]
    return diffs


def Cdf(cdf, complement=False, transform=None, **options):
    """Plots a CDF as a line.

    Args:
      cdf: Cdf object
      complement: boolean, whether to plot the complementary CDF
      transform: string, one of 'exponential', 'pareto', 'weibull', 'gumbel'
      options: keyword args passed to pyplot.plot

    Returns:
      dictionary with the scale options that should be passed to
      myplot.Save or myplot.Show
    """
    xs, ps = cdf.Render()
    scale = dict(xscale='linear', yscale='linear')

    if transform == 'exponential':
        complement = True
        scale['yscale'] = 'log'

    if transform == 'pareto':
        complement = True
        scale['yscale'] = 'log'
        scale['xscale'] = 'log'

    if complement:
        ps = [1.0-p for p in ps]

    if transform == 'weibull':
        xs.pop()
        ps.pop()
        ps = [-math.log(1.0-p) for p in ps]
        scale['xscale'] = 'log'
        scale['yscale'] = 'log'

    if transform == 'gumbel':
        xs.pop(0)
        ps.pop(0)
        ps = [-math.log(p) for p in ps]
        scale['yscale'] = 'log'

    if cdf.name:
        options = Underride(options, label=cdf.name)

    Plot(xs, ps, **options)
    return scale


def Cdfs(cdfs, complement=False, transform=None, **options):
    """Plots a sequence of CDFs.
    
    cdfs: sequence of CDF objects
    complement: boolean, whether to plot the complementary CDF
    transform: string, one of 'exponential', 'pareto', 'weibull', 'gumbel'
    options: keyword args passed to pyplot.plot
    """
    for cdf in cdfs:
        Cdf(cdf, complement, transform, **options)


def Contour(obj, pcolor=False, contour=True, imshow=False, **options):
    """Makes a contour plot.
    
    d: map from (x, y) to z, or object that provides GetDict
    pcolor: boolean, whether to make a pseudocolor plot
    contour: boolean, whether to make a contour plot
    imshow: boolean, whether to use pyplot.imshow
    options: keyword args passed to pyplot.pcolor and/or pyplot.contour
    """
    try:
        d = obj.GetDict()
    except AttributeError:
        d = obj

    Underride(options, linewidth=3, cmap=matplotlib.cm.Blues)

    xs, ys = zip(*d.iterkeys())
    xs = sorted(set(xs))
    ys = sorted(set(ys))

    X, Y = np.meshgrid(xs, ys)
    func = lambda x, y: d.get((x, y), 0)
    func = np.vectorize(func)
    Z = func(X, Y)

    x_formatter = matplotlib.ticker.ScalarFormatter(useOffset=False)
    axes = pyplot.gca()
    axes.xaxis.set_major_formatter(x_formatter)

    if pcolor:
        pyplot.pcolormesh(X, Y, Z, **options)
    if contour:
        cs = pyplot.contour(X, Y, Z, **options)
        pyplot.clabel(cs, inline=1, fontsize=10)
    if imshow:
        extent = xs[0], xs[-1], ys[0], ys[-1]
        pyplot.imshow(Z, extent=extent, **options)
        

def Pcolor(xs, ys, zs, pcolor=True, contour=False, **options):
    """Makes a pseudocolor plot.
    
    xs:
    ys:
    zs:
    pcolor: boolean, whether to make a pseudocolor plot
    contour: boolean, whether to make a contour plot
    options: keyword args passed to pyplot.pcolor and/or pyplot.contour
    """
    Underride(options, linewidth=3, cmap=matplotlib.cm.Blues)

    X, Y = np.meshgrid(xs, ys)
    Z = zs

    x_formatter = matplotlib.ticker.ScalarFormatter(useOffset=False)
    axes = pyplot.gca()
    axes.xaxis.set_major_formatter(x_formatter)

    if pcolor:
        pyplot.pcolormesh(X, Y, Z, **options)

    if contour:
        cs = pyplot.contour(X, Y, Z, **options)
        pyplot.clabel(cs, inline=1, fontsize=10)
        

def Config(**options):
    """Configures the plot.

    Pulls options out of the option dictionary and passes them to
    title, xlabel, ylabel, xscale, yscale, xticks, yticks, axis, legend,
    and loc.
    """
    title = options.get('title', '')
    pyplot.title(title)

    xlabel = options.get('xlabel', '')
    pyplot.xlabel(xlabel)

    ylabel = options.get('ylabel', '')
    pyplot.ylabel(ylabel)

    if 'xscale' in options:
        pyplot.xscale(options['xscale'])

    if 'xticks' in options:
        pyplot.xticks(options['xticks'])

    if 'yscale' in options:
        pyplot.yscale(options['yscale'])

    if 'yticks' in options:
        pyplot.yticks(options['yticks'])

    if 'axis' in options:
        pyplot.axis(options['axis'])

    loc = options.get('loc', 0)
    legend = options.get('legend', True)
    if legend:
        pyplot.legend(loc=loc)


def Show(**options):
    """Shows the plot.

    For options, see Config.

    options: keyword args used to invoke various pyplot functions
    """
    # TODO: figure out how to show more than one plot
    Config(**options)
    pyplot.show()


def Save(root=None, formats=None, **options):
    """Saves the plot in the given formats.

    For options, see Config.

    Args:
      root: string filename root
      formats: list of string formats
      options: keyword args used to invoke various pyplot functions
    """
    Config(**options)

    if formats is None:
        formats = ['pdf', 'eps']

    if root:
        for fmt in formats:
            SaveFormat(root, fmt)
    Clf()


def SaveFormat(root, fmt='eps'):
    """Writes the current figure to a file in the given format.

    Args:
      root: string filename root
      fmt: string format
    """
    filename = '%s.%s' % (root, fmt)
    print 'Writing', filename
    pyplot.savefig(filename, format=fmt, dpi=300)


# provide aliases for calling functons with lower-case names
preplot = PrePlot
subplot = SubPlot
clf = Clf
figure = Figure
plot = Plot
scatter = Scatter
pmf = Pmf
pmfs = Pmfs
hist = Hist
hists = Hists
diff = Diff
cdf = Cdf
cdfs = Cdfs
contour = Contour
pcolor = Pcolor
config = Config
show = Show
save = Save


def main():
    color_iter = Brewer.ColorGenerator(7)
    for color in color_iter:
        print color

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = thinkstats
"""This file contains code for use with "Think Stats",
by Allen B. Downey, available from greenteapress.com

Copyright 2010 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import bisect
import random

def Mean(t):
    """Computes the mean of a sequence of numbers.

    Args:
        t: sequence of numbers

    Returns:
        float
    """
    return float(sum(t)) / len(t)


def MeanVar(t):
    """Computes the mean and variance of a sequence of numbers.

    Args:
        t: sequence of numbers

    Returns:
        tuple of two floats
    """
    mu = Mean(t)
    var = Var(t, mu)
    return mu, var


def Trim(t, p=0.01):
    """Trims the largest and smallest elements of t.

    Args:
        t: sequence of numbers
        p: fraction of values to trim off each end

    Returns:
        sequence of values
    """
    n = int(p * len(t))
    t = sorted(t)[n:-n]
    return t


def Jitter(values, jitter=0.5):
    """Jitters the values by adding a uniform variate in (-jitter, jitter)."""
    return [x + random.uniform(-jitter, jitter) for x in values]


def TrimmedMean(t, p=0.01):
    """Computes the trimmed mean of a sequence of numbers.

    Side effect: sorts the list.

    Args:
        t: sequence of numbers
        p: fraction of values to trim off each end

    Returns:
        float
    """
    t = Trim(t, p)
    return Mean(t)


def TrimmedMeanVar(t, p=0.01):
    """Computes the trimmed mean and variance of a sequence of numbers.

    Side effect: sorts the list.

    Args:
        t: sequence of numbers
        p: fraction of values to trim off each end

    Returns:
        float
    """
    t = Trim(t, p)
    mu, var = MeanVar(t)
    return mu, var


def Var(t, mu=None):
    """Computes the variance of a sequence of numbers.

    Args:
        t: sequence of numbers
        mu: value around which to compute the variance; by default,
            computes the mean.

    Returns:
        float
    """
    if mu is None:
        mu = Mean(t)

    # compute the squared deviations and return their mean.
    dev2 = [(x - mu)**2 for x in t]
    var = Mean(dev2)
    return var


def Binom(n, k, d={}):
    """Compute the binomial coefficient "n choose k".

    Args:
      n: number of trials
      k: number of successes
      d: map from (n,k) tuples to cached results

    Returns:
      int
    """
    if k == 0:
        return 1
    if n == 0:
        return 0

    try:
        return d[n, k]
    except KeyError:
        res = Binom(n-1, k) + Binom(n-1, k-1)
        d[n, k] = res
        return res


class Interpolator(object):
    """Represents a mapping between sorted sequences; performs linear interp.

    Attributes:
        xs: sorted list
        ys: sorted list
    """
    def __init__(self, xs, ys):
        self.xs = xs
        self.ys = ys

    def Lookup(self, x):
        """Looks up x and returns the corresponding value of y."""
        return self._Bisect(x, self.xs, self.ys)

    def Reverse(self, y):
        """Looks up y and returns the corresponding value of x."""
        return self._Bisect(y, self.ys, self.xs)

    def _Bisect(self, x, xs, ys):
        """Helper function."""
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect(xs, x)
        frac = 1.0 * (x - xs[i-1]) / (xs[i] - xs[i-1])
        y = ys[i-1] + frac * 1.0 * (ys[i] - ys[i-1])
        return y



########NEW FILE########
__FILENAME__ = train
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from dice import Dice
import thinkplot


class Train(Dice):
    """Represents hypotheses about how many trains the company has.

    The likelihood function for the train problem is the same as
    for the Dice problem.
    """


def main():
    hypos = xrange(1, 1001)
    suite = Train(hypos)

    suite.Update(60)
    print suite.Mean()

    thinkplot.PrePlot(1)
    thinkplot.Pmf(suite)
    thinkplot.Save(root='train1',
                   xlabel='Number of trains',
                   ylabel='Probability',
                   formats=['pdf', 'eps'])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = train2
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

from dice import Dice
import thinkplot

class Train(Dice):
    """The likelihood function for the train problem is the same as
    for the Dice problem."""


def Mean(suite):
    total = 0
    for hypo, prob in suite.Items():
        total += hypo * prob
    return total


def MakePosterior(high, dataset):
    hypos = xrange(1, high+1)
    suite = Train(hypos)
    suite.name = str(high)

    for data in dataset:
        suite.Update(data)

    thinkplot.Pmf(suite)
    return suite


def main():
    dataset = [30, 60, 90]

    for high in [500, 1000, 2000]:
        suite = MakePosterior(high, dataset)
        print high, suite.Mean()

    thinkplot.Save(root='train2',
                   xlabel='Number of trains',
                   ylabel='Probability')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = train3
"""This file contains code for use with "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import thinkbayes
import thinkplot

from thinkbayes import Pmf, Percentile
from dice import Dice


class Train(Dice):
    """Represents hypotheses about how many trains the company has."""


class Train2(Dice):
    """Represents hypotheses about how many trains the company has."""

    def __init__(self, hypos, alpha=1.0):
        """Initializes the hypotheses with a power law distribution.

        hypos: sequence of hypotheses
        alpha: parameter of the power law prior
        """
        Pmf.__init__(self)
        for hypo in hypos:
            self.Set(hypo, hypo**(-alpha))
        self.Normalize()


def MakePosterior(high, dataset, constructor):
    """Makes and updates a Suite.

    high: upper bound on the range of hypotheses
    dataset: observed data to use for the update
    constructor: function that makes a new suite

    Returns: posterior Suite
    """
    hypos = xrange(1, high+1)
    suite = constructor(hypos)
    suite.name = str(high)

    for data in dataset:
        suite.Update(data)

    return suite


def ComparePriors():
    """Runs the analysis with two different priors and compares them."""
    dataset = [60]
    high = 1000

    thinkplot.Clf()
    thinkplot.PrePlot(num=2)

    constructors = [Train, Train2]
    labels = ['uniform', 'power law']

    for constructor, label in zip(constructors, labels):
        suite = MakePosterior(high, dataset, constructor)
        suite.name = label
        thinkplot.Pmf(suite)

    thinkplot.Save(root='train4',
                xlabel='Number of trains',
                ylabel='Probability')

def main():
    ComparePriors()

    dataset = [30, 60, 90]

    thinkplot.Clf()
    thinkplot.PrePlot(num=3)

    for high in [500, 1000, 2000]:
        suite = MakePosterior(high, dataset, Train2)
        print high, suite.Mean()

    thinkplot.Save(root='train3',
                   xlabel='Number of trains',
                   ylabel='Probability')

    interval = Percentile(suite, 5), Percentile(suite, 95)
    print interval

    cdf = thinkbayes.MakeCdfFromPmf(suite)
    interval = cdf.Percentile(5), cdf.Percentile(95)
    print interval


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = variability
"""This file contains code used in "Think Bayes",
by Allen B. Downey, available from greenteapress.com

Copyright 2012 Allen B. Downey
License: GNU GPLv3 http://www.gnu.org/licenses/gpl.html
"""

import math
import numpy
import cPickle
import numpy
import random
import scipy

import brfss

import thinkplot
import thinkbayes
import thinkstats

import matplotlib.pyplot as pyplot


NUM_SIGMAS = 1

class Height(thinkbayes.Suite, thinkbayes.Joint):
    """Hypotheses about parameters of the distribution of height."""

    def __init__(self, mus, sigmas, name=''):
        """Makes a prior distribution for mu and sigma based on a sample.

        mus: sequence of possible mus
        sigmas: sequence of possible sigmas
        name: string name for the Suite
        """
        pairs = [(mu, sigma) 
                 for mu in mus
                 for sigma in sigmas]

        thinkbayes.Suite.__init__(self, pairs, name=name)

    def Likelihood(self, data, hypo):
        """Computes the likelihood of the data under the hypothesis.

        Args:
            hypo: tuple of hypothetical mu and sigma
            data: float sample

        Returns:
            likelihood of the sample given mu and sigma
        """
        x = data
        mu, sigma = hypo
        like = scipy.stats.norm.pdf(x, mu, sigma)
        return like

    def LogLikelihood(self, data, hypo):
        """Computes the log likelihood of the data under the hypothesis.

        Args:
            data: a list of values
            hypo: tuple of hypothetical mu and sigma

        Returns:
            log likelihood of the sample given mu and sigma (unnormalized)
        """
        x = data
        mu, sigma = hypo
        loglike = EvalGaussianLogPdf(x, mu, sigma)
        return loglike

    def LogUpdateSetFast(self, data):
        """Updates the suite using a faster implementation.

        Computes the sum of the log likelihoods directly.

        Args:
            data: sequence of values
        """
        xs = tuple(data)
        n = len(xs)

        for hypo in self.Values():
            mu, sigma = hypo
            total = Summation(xs, mu)
            loglike = -n * math.log(sigma) - total / 2 / sigma**2
            self.Incr(hypo, loglike)

    def LogUpdateSetMeanVar(self, data):
        """Updates the suite using ABC and mean/var.

        Args:
            data: sequence of values
        """
        xs = data
        n = len(xs)

        m = numpy.mean(xs)
        s = numpy.std(xs)

        self.LogUpdateSetABC(n, m, s)

    def LogUpdateSetMedianIPR(self, data):
        """Updates the suite using ABC and median/iqr.

        Args:
            data: sequence of values
        """
        xs = data
        n = len(xs)

        # compute summary stats
        median, s = MedianS(xs, num_sigmas=NUM_SIGMAS)
        print 'median, s', median, s

        self.LogUpdateSetABC(n, median, s)

    def LogUpdateSetABC(self, n, m, s):
        """Updates the suite using ABC.

        n: sample size
        m: estimated central tendency
        s: estimated spread
        """
        for hypo in sorted(self.Values()):
            mu, sigma = hypo

            # compute log likelihood of m, given hypo
            stderr_m = sigma / math.sqrt(n)
            loglike = EvalGaussianLogPdf(m, mu, stderr_m)

            #compute log likelihood of s, given hypo
            stderr_s = sigma / math.sqrt(2 * (n-1))
            loglike += EvalGaussianLogPdf(s, sigma, stderr_s)

            self.Incr(hypo, loglike)


def EvalGaussianLogPdf(x, mu, sigma):
    """Computes the log PDF of x given mu and sigma.

    x: float values
    mu, sigma: paramemters of Gaussian

    returns: float log-likelihood
    """
    return scipy.stats.norm.logpdf(x, mu, sigma)


def FindPriorRanges(xs, num_points, num_stderrs=3.0, median_flag=False):
    """Find ranges for mu and sigma with non-negligible likelihood.

    xs: sample
    num_points: number of values in each dimension
    num_stderrs: number of standard errors to include on either side
    
    Returns: sequence of mus, sequence of sigmas    
    """
    def MakeRange(estimate, stderr):
        """Makes a linear range around the estimate.

        estimate: central value
        stderr: standard error of the estimate

        returns: numpy array of float
        """
        spread = stderr * num_stderrs
        array = numpy.linspace(estimate-spread, estimate+spread, num_points)
        return array

    # estimate mean and stddev of xs
    n = len(xs)
    if median_flag:
        m, s = MedianS(xs, num_sigmas=NUM_SIGMAS)
    else:
        m = numpy.mean(xs)
        s = numpy.std(xs)

    print 'classical estimators', m, s

    # compute ranges for m and s
    stderr_m = s / math.sqrt(n)
    mus = MakeRange(m, stderr_m)

    stderr_s = s / math.sqrt(2 * (n-1))
    sigmas = MakeRange(s, stderr_s)

    return mus, sigmas


def Summation(xs, mu, cache={}):
    """Computes the sum of (x-mu)**2 for x in t.

    Caches previous results.

    xs: tuple of values
    mu: hypothetical mean
    cache: cache of previous results
    """
    try:
        return cache[xs, mu]
    except KeyError:
        ds = [(x-mu)**2 for x in xs]
        total = sum(ds)
        cache[xs, mu] = total
        return total


def CoefVariation(suite):
    """Computes the distribution of CV.

    suite: Pmf that maps (x, y) to z

    Returns: Pmf object for CV.
    """
    pmf = thinkbayes.Pmf()
    for (m, s), p in suite.Items():
        pmf.Incr(s/m, p)
    return pmf


def PlotCdfs(d, labels):
    """Plot CDFs for each sequence in a dictionary.

    Jitters the data and subtracts away the mean.

    d: map from key to sequence of values
    labels: map from key to string label
    """
    thinkplot.Clf()
    for key, xs in d.iteritems():
        mu = thinkstats.Mean(xs)
        xs = thinkstats.Jitter(xs, 1.3)
        xs = [x-mu for x in xs]
        cdf = thinkbayes.MakeCdfFromList(xs)
        thinkplot.Cdf(cdf, label=labels[key])
    thinkplot.Show()
                  

def PlotPosterior(suite, pcolor=False, contour=True):
    """Makes a contour plot.
    
    suite: Suite that maps (mu, sigma) to probability
    """
    thinkplot.Clf()
    thinkplot.Contour(suite.GetDict(), pcolor=pcolor, contour=contour)

    thinkplot.Save(root='variability_posterior_%s' % suite.name,
                title='Posterior joint distribution',
                xlabel='Mean height (cm)',
                ylabel='Stddev (cm)')


def PlotCoefVariation(suites):
    """Plot the posterior distributions for CV.

    suites: map from label to Pmf of CVs.
    """
    thinkplot.Clf()
    thinkplot.PrePlot(num=2)

    pmfs = {}
    for label, suite in suites.iteritems():
        pmf = CoefVariation(suite)
        print 'CV posterior mean', pmf.Mean()
        cdf = thinkbayes.MakeCdfFromPmf(pmf, label)
        thinkplot.Cdf(cdf)
    
        pmfs[label] = pmf

    thinkplot.Save(root='variability_cv',
                xlabel='Coefficient of variation',
                ylabel='Probability')

    print 'female bigger', thinkbayes.PmfProbGreater(pmfs['female'],
                                                     pmfs['male'])
    print 'male bigger', thinkbayes.PmfProbGreater(pmfs['male'],
                                                   pmfs['female'])


def PlotOutliers(samples):
    """Make CDFs showing the distribution of outliers."""
    cdfs = []
    for label, sample in samples.iteritems():
        outliers = [x for x in sample if x < 150]

        cdf = thinkbayes.MakeCdfFromList(outliers, label)
        cdfs.append(cdf)

    thinkplot.Clf()
    thinkplot.Cdfs(cdfs)
    thinkplot.Save(root='variability_cdfs',
                title='CDF of height',
                xlabel='Reported height (cm)',
                ylabel='CDF')


def PlotMarginals(suite):
    """Plots marginal distributions from a joint distribution.

    suite: joint distribution of mu and sigma.
    """
    thinkplot.Clf()

    pyplot.subplot(1, 2, 1)
    pmf_m = suite.Marginal(0)
    cdf_m = thinkbayes.MakeCdfFromPmf(pmf_m)
    thinkplot.Cdf(cdf_m)

    pyplot.subplot(1, 2, 2)
    pmf_s = suite.Marginal(1)
    cdf_s = thinkbayes.MakeCdfFromPmf(pmf_s)
    thinkplot.Cdf(cdf_s)

    thinkplot.Show()


def DumpHeights(data_dir='.', n=10000):
    """Read the BRFSS dataset, extract the heights and pickle them."""
    resp = brfss.Respondents()
    resp.ReadRecords(data_dir, n)

    d = {1:[], 2:[]}
    [d[r.sex].append(r.htm3) for r in resp.records if r.htm3 != 'NA']

    fp = open('variability_data.pkl', 'wb')
    cPickle.dump(d, fp)
    fp.close()


def LoadHeights():
    """Read the pickled height data.

    returns: map from sex code to list of heights.
    """
    fp = open('variability_data.pkl', 'r')
    d = cPickle.load(fp)
    fp.close()
    return d


def UpdateSuite1(suite, xs):
    """Computes the posterior distibution of mu and sigma.

    Computes untransformed likelihoods.

    suite: Suite that maps from (mu, sigma) to prob
    xs: sequence
    """
    suite.UpdateSet(xs)


def UpdateSuite2(suite, xs):
    """Computes the posterior distibution of mu and sigma.

    Computes log likelihoods.

    suite: Suite that maps from (mu, sigma) to prob
    xs: sequence
    """
    suite.Log()
    suite.LogUpdateSet(xs)
    suite.Exp()
    suite.Normalize()


def UpdateSuite3(suite, xs):
    """Computes the posterior distibution of mu and sigma.

    Computes log likelihoods efficiently.

    suite: Suite that maps from (mu, sigma) to prob
    t: sequence
    """
    suite.Log()
    suite.LogUpdateSetFast(xs)
    suite.Exp()
    suite.Normalize()


def UpdateSuite4(suite, xs):
    """Computes the posterior distibution of mu and sigma.

    Computes log likelihoods efficiently.

    suite: Suite that maps from (mu, sigma) to prob
    t: sequence
    """
    suite.Log()
    suite.LogUpdateSetMeanVar(xs)
    suite.Exp()
    suite.Normalize()


def UpdateSuite5(suite, xs):
    """Computes the posterior distibution of mu and sigma.

    Computes log likelihoods efficiently.

    suite: Suite that maps from (mu, sigma) to prob
    t: sequence
    """
    suite.Log()
    suite.LogUpdateSetMedianIPR(xs)
    suite.Exp()
    suite.Normalize()


def MedianIPR(xs, p):
    """Computes the median and interpercentile range.

    xs: sequence of values
    p: range (0-1), 0.5 yields the interquartile range

    returns: tuple of float (median, IPR)
    """
    cdf = thinkbayes.MakeCdfFromList(xs)
    median = cdf.Percentile(50)

    alpha = (1-p) / 2
    ipr = cdf.Value(1-alpha) - cdf.Value(alpha)
    return median, ipr


def MedianS(xs, num_sigmas):
    """Computes the median and an estimate of sigma.

    Based on an interpercentile range (IPR).

    factor: number of standard deviations spanned by the IPR
    """
    half_p = thinkbayes.StandardGaussianCdf(num_sigmas) - 0.5
    median, ipr = MedianIPR(xs, half_p * 2)
    s = ipr / 2 / num_sigmas

    return median, s

def Summarize(xs):
    """Prints summary statistics from a sequence of values.

    xs: sequence of values
    """
    # print smallest and largest
    xs.sort()
    print 'smallest', xs[:10]
    print 'largest', xs[-10:]

    # print median and interquartile range
    cdf = thinkbayes.MakeCdfFromList(xs)
    print cdf.Percentile(25), cdf.Percentile(50), cdf.Percentile(75)


def RunEstimate(update_func, num_points=31, median_flag=False):
    """Runs the whole analysis.

    update_func: which of the update functions to use
    num_points: number of points in the Suite (in each dimension)
    """
    # DumpHeights(n=10000000)
    d = LoadHeights()
    labels = {1:'male', 2:'female'}

    # PlotCdfs(d, labels)

    suites = {}
    for key, xs in d.iteritems():
        name = labels[key]
        print name, len(xs)
        Summarize(xs)

        xs = thinkstats.Jitter(xs, 1.3)

        mus, sigmas = FindPriorRanges(xs, num_points, median_flag=median_flag)
        suite = Height(mus, sigmas, name)
        suites[name] = suite
        update_func(suite, xs)
        print 'MLE', suite.MaximumLikelihood()

        PlotPosterior(suite)

        pmf_m = suite.Marginal(0)
        pmf_s = suite.Marginal(1)
        print 'marginal mu', pmf_m.Mean(), pmf_m.Var()
        print 'marginal sigma', pmf_s.Mean(), pmf_s.Var()

        # PlotMarginals(suite)

    PlotCoefVariation(suites)


def main():
    random.seed(17)

    func = UpdateSuite5
    median_flag = (func == UpdateSuite5)
    RunEstimate(func, median_flag=median_flag)


if __name__ == '__main__':
    main()


""" Results:

UpdateSuite1 (100):
marginal mu 162.816901408 0.55779791443
marginal sigma 6.36966103214 0.277026082819

UpdateSuite2 (100):
marginal mu 162.816901408 0.55779791443
marginal sigma 6.36966103214 0.277026082819

UpdateSuite3 (100):
marginal mu 162.816901408 0.55779791443
marginal sigma 6.36966103214 0.277026082819

UpdateSuite4 (100):
marginal mu 162.816901408 0.547456009605
marginal sigma 6.30305516111 0.27544106054

UpdateSuite3 (1000):
marginal mu 163.722137405 0.0660294386397
marginal sigma 6.64453251495 0.0329935312671

UpdateSuite4 (1000):
marginal mu 163.722137405 0.0658920503302
marginal sigma 6.63692197049 0.0329689887609

UpdateSuite3 (all):
marginal mu 163.223475005 0.000203282582659
marginal sigma 7.26918836916 0.000101641131229

UpdateSuite4 (all):
marginal mu 163.223475004 0.000203281499857
marginal sigma 7.26916693422 0.000101640932082

UpdateSuite5 (all):
marginal mu 163.1805214 7.9399898468e-07
marginal sigma 7.29969524118 3.26257030869e-14

"""


########NEW FILE########
