__FILENAME__ = 3dvec
"""
QE by Tom Sargent and John Stachurski.
Illustrates the span of two vectors in R^3.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import interp2d

fig = plt.figure()
ax = fig.gca(projection='3d')

x_min, x_max = -5, 5
y_min, y_max = -5, 5

alpha, beta = 0.2, 0.1

ax.set_xlim((x_min, x_max))
ax.set_ylim((x_min, x_max))
ax.set_zlim((x_min, x_max))

# Axes
ax.set_xticks((0,))
ax.set_yticks((0,))
ax.set_zticks((0,))
gs = 3
z = np.linspace(x_min, x_max, gs)
x = np.zeros(gs)
y = np.zeros(gs)
ax.plot(x, y, z, 'k-', lw=2, alpha=0.5)
ax.plot(z, x, y, 'k-', lw=2, alpha=0.5)
ax.plot(y, z, x, 'k-', lw=2, alpha=0.5)


# Fixed linear function, to generate a plane
def f(x, y):
    return alpha * x + beta * y

# Vector locations, by coordinate
x_coords = np.array((3, 3))
y_coords = np.array((4, -4))
z = f(x_coords, y_coords)
for i in (0, 1):
    ax.text(x_coords[i], y_coords[i], z[i], r'$a_{}$'.format(i+1), fontsize=14)

# Lines to vectors
for i in (0, 1):
    x = (0, x_coords[i])
    y = (0, y_coords[i])
    z = (0, f(x_coords[i], y_coords[i]))
    ax.plot(x, y, z, 'b-', lw=1.5, alpha=0.6)


# Draw the plane
grid_size = 20
xr2 = np.linspace(x_min, x_max, grid_size)
yr2 = np.linspace(y_min, y_max, grid_size)
x2, y2 = np.meshgrid(xr2, yr2)
z2 = f(x2, y2)
ax.plot_surface(x2, y2, z2, rstride=1, cstride=1, cmap=cm.jet,
        linewidth=0, antialiased=True, alpha=0.2)
plt.show()



########NEW FILE########
__FILENAME__ = ar1sim
"""
Origin: QE by Thomas J. Sargent and John Stachurski
Filename: ar1sim.py
"""

import numpy as np
from scipy.stats import norm

def proto1(a, b, sigma, T, num_reps, phi=norm.rvs):
    X = np.zeros((num_reps, T+1))
    for i in range(num_reps):
        W = phi(size=T+1)
        for t in range(1, T+1):
            X[i, t] = a * X[i,t-1] + b + W[t]
    return X


def proto2(a, b, sigma, T, num_reps, x0=None, phi=norm.rvs):
    """ 
    More efficient, eliminates one loop.
    """
    if not x0 == None:
        x0.shape = (num_reps, 1)
        X[:, 0] = x0
    W = phi(size=(num_reps, T+1))
    X = np.zeros((num_reps, T+1))
    for t in range(1, T+1):
        X[:, t] = a * X[:,t-1] + b + W[:, t]
    return X

def ols_estimates(X):
    num_reps, ts_length = X.shape
    estimates = np.empty(num_reps)
    for i in range(num_reps):
        X_row = X[i,:].flatten()
        x = X_row[:-1]  # All but last one
        y = X_row[1:]   # All but first one
        estimates[i] = np.dot(x, y) / np.dot(x, x) 
    return estimates

def ope_estimates(X):
    num_reps, ts_length = X.shape
    estimates = np.empty(num_reps)
    for i in range(num_reps):
        x = X[i,:].flatten()
        s2 = x.var()
        estimates[i] = np.sqrt(1 - 1 / s2)
    return estimates

theta = 0.8
num_reps = 100000
n = 1000
X_obs = proto2(theta, 0, 1, n, num_reps)

if 0:
    theta_hats = ols_estimates(X_obs)
    r = np.sqrt(n) * (theta_hats - theta)
    print "OLS Expected: {}".format(1 - theta**2)
    print "OLS Realized: {}".format(r.var())

if 0:
    theta_hats = ope_estimates(X_obs)
    r = np.sqrt(n) * (theta_hats - theta)
    e = (1 - theta**2) * (1 + (1 - theta**2) / (2 * theta**2))
    print "OPE Expected: {}".format(e)
    print "OPE Realized: {}".format(r.var())

s2_hats = X_obs.var(axis=1)
r = np.sqrt(n) * (s2_hats - 1 / (1 - theta**2))
e = 2 * (1 + theta**2) / (1 - theta**2)**3
print "Expected: {}".format(e)
print "Realized: {}".format(r.var())



########NEW FILE########
__FILENAME__ = ar1_acov
"""
Plots autocovariance function for AR(1) X' = phi X + epsilon
"""
import numpy as np
import matplotlib.pyplot as plt

num_rows, num_cols = 2, 1
fig, axes = plt.subplots(num_rows, num_cols, figsize=(10, 8))
plt.subplots_adjust(hspace=0.4)

# Autocovariance when phi = 0.8
temp = r'autocovariance, $\phi = {0:.2}$'
for i, phi in enumerate((0.8, -0.8)):
    ax = axes[i]
    times = range(16)
    acov = [phi**k / (1 - phi**2) for k in times]
    ax.plot(times, acov, 'bo-', alpha=0.6, label=temp.format(phi))
    ax.legend(loc='upper right')
    ax.set_xlabel('time')
    ax.set_xlim((0, 15))
    ax.hlines(0, 0, 15, linestyle='--', alpha=0.5)
plt.show()

########NEW FILE########
__FILENAME__ = ar1_cycles
"""
Helps to illustrate the spectral density for AR(1) X' = phi X + epsilon
"""
import numpy as np
import matplotlib.pyplot as plt

phi = -0.8
times = range(16)
y1 = [phi**k / (1 - phi**2) for k in times]
y2 = [np.cos(np.pi * k) for k in times]
y3 = [a * b for a, b in zip(y1, y2)]

num_rows, num_cols = 3, 1
fig, axes = plt.subplots(num_rows, num_cols, figsize=(10, 8))
plt.subplots_adjust(hspace=0.25)

# Autocovariance when phi = -0.8
ax = axes[0]
ax.plot(times, y1, 'bo-', alpha=0.6, label=r'$\gamma(k)$')
ax.legend(loc='upper right')
ax.set_xlim(0, 15)
ax.set_yticks((-2, 0, 2))
ax.hlines(0, 0, 15, linestyle='--', alpha=0.5)

# Cycles at frequence pi
ax = axes[1]
ax.plot(times, y2, 'bo-', alpha=0.6, label=r'$\cos(\pi k)$')
ax.legend(loc='upper right')
ax.set_xlim(0, 15)
ax.set_yticks((-1, 0, 1))
ax.hlines(0, 0, 15, linestyle='--', alpha=0.5)

# Product
ax = axes[2]
ax.stem(times, y3, label=r'$\gamma(k) \cos(\pi k)$')
ax.legend(loc='upper right')
ax.set_xlim((0, 15))
ax.set_ylim(-3, 3)
ax.set_yticks((-1, 0, 1, 2, 3))
ax.hlines(0, 0, 15, linestyle='--', alpha=0.5)

plt.show()

########NEW FILE########
__FILENAME__ = ar1_sd
"""
Plots spectral density for AR(1) X' = phi X + epsilon
"""
import numpy as np
import matplotlib.pyplot as plt

def ar1_sd(phi, omega):
    return 1 / (1 - 2 * phi * np.cos(omega) + phi**2)

omegas = np.linspace(0, np.pi, 180)
num_rows, num_cols = 2, 1
fig, axes = plt.subplots(num_rows, num_cols, figsize=(10, 8))
plt.subplots_adjust(hspace=0.4)

# Autocovariance when phi = 0.8
temp = r'spectral density, $\phi = {0:.2}$'
for i, phi in enumerate((0.8, -0.8)):
    ax = axes[i]
    sd = ar1_sd(phi, omegas)
    ax.plot(omegas, sd, 'b-', alpha=0.6, lw=2, label=temp.format(phi))
    ax.legend(loc='upper center')
    ax.set_xlabel('frequency')
    ax.set_xlim((0, np.pi))
plt.show()

########NEW FILE########
__FILENAME__ = beta-binomial
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: beta-binomial.py
Authors: John Stachurski, Thomas J. Sargent
LastModified: 11/08/2013

"""
from scipy.special import binom, beta
import matplotlib.pyplot as plt
import numpy as np

def gen_probs(n, a, b):
    probs = np.zeros(n+1)
    for k in range(n+1):
        probs[k] = binom(n, k) * beta(k + a, n - k + b) / beta(a, b)
    return probs

n = 50
a_vals = [0.5, 1, 100]
b_vals = [0.5, 1, 100]
fig, ax = plt.subplots()
for a, b in zip(a_vals, b_vals):
    ab_label = r'$a = %.1f$, $b = %.1f$' % (a, b)
    ax.plot(range(0, n+1), gen_probs(n, a, b), '-o', label=ab_label)
ax.legend()
plt.show()


########NEW FILE########
__FILENAME__ = binom_df
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import binom

fig, axes = plt.subplots(2, 2)
plt.subplots_adjust(hspace=0.4)
axes = axes.flatten()
ns = [1, 2, 4, 8]
dom = range(9) 

for ax, n in zip(axes, ns):
    b = binom(n, 0.5)
    ax.bar(dom, b.pmf(dom), alpha=0.6, align='center')
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(0, 0.55)
    ax.set_xticks(range(9))
    ax.set_yticks((0, 0.2, 0.4))
    ax.set_title(r'$n = {}$'.format(n))

fig.show()


########NEW FILE########
__FILENAME__ = bisection
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Authors: John Stachurski, Thomas J. Sargent
"""


def bisect(f, a, b, tol=10e-5):
    """
    Implements the bisection root finding algorithm, assuming that f is a
    real-valued function on [a, b] satisfying f(a) < 0 < f(b).
    """
    lower, upper = a, b

    while upper - lower > tol:
        middle = 0.5 * (upper + lower)
        # === if root is between lower and middle === #
        if f(middle) > 0:  
            lower, upper = lower, middle
        # === if root is between middle and upper  === #
        else:              
            lower, upper = middle, upper

    return 0.5 * (upper + lower)



########NEW FILE########
__FILENAME__ = career_vf_plot
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: career_vf_plot.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D
import numpy as np
from matplotlib import cm
from quantecon.compute_fp import compute_fixed_point
import quantecon as qe

# === solve for the value function === #
wp = qe.career.workerProblem()
v_init = np.ones((wp.N, wp.N))*100
v = compute_fixed_point(qe.career.bellman, wp, v_init)

# === plot value function === #
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(111, projection='3d')
tg, eg = np.meshgrid(wp.theta, wp.epsilon)
ax.plot_surface(tg, 
                eg,  
                v.T, 
                rstride=2, cstride=2, 
                cmap=cm.jet, 
                alpha=0.5,
                linewidth=0.25)
ax.set_zlim(150, 200)
ax.set_xlabel('theta', fontsize=14)
ax.set_ylabel('epsilon', fontsize=14)
plt.show()

########NEW FILE########
__FILENAME__ = cauchy_samples

import numpy as np
from scipy.stats import cauchy
import matplotlib.pyplot as plt

n = 1000
distribution = cauchy()

fig, ax = plt.subplots()
data = distribution.rvs(n)

if 0:
    ax.plot(range(n), data, 'bo', alpha=0.5)
    ax.vlines(range(n), 0, data, lw=0.2)
    ax.set_title("{} observations from the Cauchy distribution".format(n))

if 1:
    # == Compute sample mean at each n == #
    sample_mean = np.empty(n)
    for i in range(n):
        sample_mean[i] = np.mean(data[:i])

    # == Plot == #
    ax.plot(range(n), sample_mean, 'r-', lw=3, alpha=0.6, label=r'$\bar X_n$')
    ax.plot(range(n), [0] * n, 'k--', lw=0.5)
    ax.legend()

fig.show()




########NEW FILE########
__FILENAME__ = clt3d
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: clt3d.py

Visual illustration of the central limit theorem.  Produces a 3D figure
showing the density of the scaled sample mean  \sqrt{n} \bar X_n plotted
against n.
"""

import numpy as np
from scipy.stats import beta, bernoulli, gaussian_kde
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection
import matplotlib.pyplot as plt

beta_dist = beta(2, 2)  

def gen_x_draws(k):
    """
    Returns a flat array containing k independent draws from the 
    distribution of X, the underlying random variable.  This distribution is
    itself a convex combination of three beta distributions.
    """
    bdraws = beta_dist.rvs((3, k))
    # == Transform rows, so each represents a different distribution == #
    bdraws[0,:] -= 0.5
    bdraws[1,:] += 0.6
    bdraws[2,:] -= 1.1
    # == Set X[i] = bdraws[j, i], where j is a random draw from {0, 1, 2} == #
    js = np.random.random_integers(0, 2, size=k)
    X = bdraws[js, np.arange(k)]
    # == Rescale, so that the random variable is zero mean == #
    m, sigma = X.mean(), X.std()
    return (X - m) / sigma

nmax = 5
reps = 100000
ns = range(1, nmax + 1)

# == Form a matrix Z such that each column is reps independent draws of X == #
Z = np.empty((reps, nmax))
for i in range(nmax):
    Z[:,i] = gen_x_draws(reps)
# == Take cumulative sum across columns
S = Z.cumsum(axis=1)
# == Multiply j-th column by sqrt j == #
Y = (1 / np.sqrt(ns)) * S

# == Plot == #

fig = plt.figure()
ax = fig.gca(projection='3d')

a, b = -3, 3
gs = 100 
xs = np.linspace(a, b, gs)

# == Build verts == #
greys = np.linspace(0.3, 0.7, nmax)
verts = []
for n in ns:
    density = gaussian_kde(Y[:,n-1])
    ys = density(xs)
    verts.append(zip(xs, ys))

poly = PolyCollection(verts, facecolors = [str(g) for g in greys])
poly.set_alpha(0.85)
ax.add_collection3d(poly, zs=ns, zdir='x')

#ax.text(np.mean(rhos), a-1.4, -0.02, r'$\beta$', fontsize=16)
#ax.text(np.max(rhos)+0.016, (a+b)/2, -0.02, r'$\log(y)$', fontsize=16)
ax.set_xlim3d(1, nmax)
ax.set_xticks(ns)
ax.set_xlabel("n")
ax.set_yticks((-3, 0, 3))
ax.set_ylim3d(a, b)
ax.set_zlim3d(0, 0.4)
ax.set_zticks((0.2, 0.4))
plt.show()



########NEW FILE########
__FILENAME__ = descriptor_eg
"""
Filename: descriptor_eg.py
Authors: John Stachurski, Thomas J. Sargent
"""

class Car(object):

    def __init__(self, miles_till_service=1000):

        self.__miles_till_service = miles_till_service
        self.__kms_till_service = miles_till_service * 1.61

    def set_miles(self, value):
        self.__miles_till_service = value
        self.__kms_till_service = value * 1.61

    def set_kms(self, value):
        self.__kms_till_service = value
        self.__miles_till_service = value / 1.61

    def get_miles(self):
        return self.__miles_till_service

    def get_kms(self):
        return self.__kms_till_service

    miles_till_service = property(get_miles, set_miles)
    kms_till_service = property(get_kms, set_kms)

########NEW FILE########
__FILENAME__ = dice
"""
Filename: dice.py
Authors: John Stachurski, Thomas J. Sargent
"""

import random

class Dice:

    faces = (1, 2, 3, 4, 5, 6)

    def __init__(self):
       self.current_face = 1

    def roll(self):
        self.current_face = random.choice(Dice.faces)


########NEW FILE########
__FILENAME__ = eigenvec
"""
Filename: eigenvec.py
Authors: Tom Sargent and John Stachurski.

Illustrates eigenvectors.
"""

import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import eig

A = ((1, 2),
     (2, 1))
A = np.array(A)
evals, evecs = eig(A)
evecs = evecs[:,0], evecs[:,1]

fig, ax = plt.subplots()
# Set the axes through the origin
for spine in ['left', 'bottom']:
    ax.spines[spine].set_position('zero')
for spine in ['right', 'top']:
    ax.spines[spine].set_color('none')
ax.grid(alpha=0.4)
    
xmin, xmax = -3, 3
ymin, ymax = -3, 3
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
#ax.set_xticks(())
#ax.set_yticks(())

# Plot each eigenvector
for v in evecs:
    ax.annotate('', xy=v, xytext=(0, 0), 
                arrowprops=dict(facecolor='blue', 
                    shrink=0, 
                    alpha=0.6,
                    width=0.5))

# Plot the image of each eigenvector
for v in evecs:
    v = np.dot(A, v)
    ax.annotate('', xy=v, xytext=(0, 0), 
                arrowprops=dict(facecolor='red', 
                    shrink=0, 
                    alpha=0.6,
                    width=0.5))

# Plot the lines they run through
x = np.linspace(xmin, xmax, 3)
for v in evecs:
    a = v[1] / v[0]
    ax.plot(x, a * x, 'b-', lw=0.4)


plt.show()


########NEW FILE########
__FILENAME__ = gaussian_contours
"""
Filename: gaussian_contours.py
Authors: John Stachurski and Thomas Sargent

Plots of bivariate Gaussians to illustrate the Kalman filter.  
"""

from scipy import linalg
import numpy as np
import matplotlib.cm as cm
from matplotlib.mlab import bivariate_normal
import matplotlib.pyplot as plt

# == Set up the Gaussian prior density p == #
Sigma = [[0.4, 0.3], [0.3, 0.45]]
Sigma = np.matrix(Sigma)
x_hat = np.matrix([0.2, -0.2]).T
# == Define the matrices G and R from the equation y = G x + N(0, R) == #
G = [[1, 0], [0, 1]]
G = np.matrix(G)
R = 0.5 * Sigma
# == The matrices A and Q == #
A = [[1.2, 0], [0, -0.2]]
A = np.matrix(A)
Q = 0.3 * Sigma
# == The observed value of y == #
y = np.matrix([2.3, -1.9]).T

# == Set up grid for plotting == #
x_grid = np.linspace(-1.5, 2.9, 100)
y_grid = np.linspace(-3.1, 1.7, 100)
X, Y = np.meshgrid(x_grid, y_grid)

def gen_gaussian_plot_vals(mu, C):
    "Z values for plotting the bivariate Gaussian N(mu, C)"
    m_x, m_y = float(mu[0]), float(mu[1])
    s_x, s_y = np.sqrt(C[0,0]), np.sqrt(C[1,1])
    s_xy = C[0,1]
    return bivariate_normal(X, Y, s_x, s_y, m_x, m_y, s_xy)

fig, ax = plt.subplots()
ax.xaxis.grid(True, zorder=0)
ax.yaxis.grid(True, zorder=0)

# == Code for the 4 plots, choose one below == #

def plot1():
    Z = gen_gaussian_plot_vals(x_hat, Sigma)
    ax.contourf(X, Y, Z, 6, alpha=0.6, cmap=cm.jet)
    cs = ax.contour(X, Y, Z, 6, colors="black")
    ax.clabel(cs, inline=1, fontsize=10)

def plot2():
    Z = gen_gaussian_plot_vals(x_hat, Sigma)
    ax.contourf(X, Y, Z, 6, alpha=0.6, cmap=cm.jet)
    cs = ax.contour(X, Y, Z, 6, colors="black")
    ax.clabel(cs, inline=1, fontsize=10)
    ax.text(float(y[0]), float(y[1]), r"$y$", fontsize=20, color="black")

def plot3():
    Z = gen_gaussian_plot_vals(x_hat, Sigma)
    cs1 = ax.contour(X, Y, Z, 6, colors="black")
    ax.clabel(cs1, inline=1, fontsize=10)
    M = Sigma * G.T * linalg.inv(G * Sigma * G.T + R)
    x_hat_F =  x_hat + M * (y - G * x_hat)
    Sigma_F = Sigma  - M * G * Sigma
    new_Z = gen_gaussian_plot_vals(x_hat_F, Sigma_F)
    cs2 = ax.contour(X, Y, new_Z, 6, colors="black")
    ax.clabel(cs2, inline=1, fontsize=10)
    ax.contourf(X, Y, new_Z, 6, alpha=0.6, cmap=cm.jet)
    ax.text(float(y[0]), float(y[1]), r"$y$", fontsize=20, color="black")

def plot4():
    # Density 1
    Z = gen_gaussian_plot_vals(x_hat, Sigma)
    cs1 = ax.contour(X, Y, Z, 6, colors="black")
    ax.clabel(cs1, inline=1, fontsize=10)
    # Density 2
    M = Sigma * G.T * linalg.inv(G * Sigma * G.T + R)
    x_hat_F =  x_hat + M * (y - G * x_hat)
    Sigma_F = Sigma  - M * G * Sigma
    Z_F = gen_gaussian_plot_vals(x_hat_F, Sigma_F)
    cs2 = ax.contour(X, Y, Z_F, 6, colors="black")
    ax.clabel(cs2, inline=1, fontsize=10)
    # Density 3
    new_x_hat = A * x_hat_F 
    new_Sigma = A * Sigma_F * A.T + Q
    new_Z = gen_gaussian_plot_vals(new_x_hat, new_Sigma)
    cs3 = ax.contour(X, Y, new_Z, 6, colors="black")
    ax.clabel(cs3, inline=1, fontsize=10)
    ax.contourf(X, Y, new_Z, 6, alpha=0.6, cmap=cm.jet)
    ax.text(float(y[0]), float(y[1]), r"$y$", fontsize=20, color="black")

# == Choose a plot to generate == #
plot1()
plt.show()

########NEW FILE########
__FILENAME__ = ifp_savings_plots
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: ifp_savings_plots.py
Authors: John Stachurski, Thomas J. Sargent
LastModified: 11/08/2013

"""
from compute_fp import compute_fixed_point
from matplotlib import pyplot as plt
from quantecon.compute_fp import compute_fixed_point
import quantecon as qe

# === solve for optimal consumption === #
m = qe.ifp.consumerProblem(r=0.03, grid_max=4)
v_init, c_init = qe.ifp.initialize(m)
c = compute_fixed_point(qe.ifp.coleman_operator, m, c_init)
a = m.asset_grid
R, z_vals = m.R, m.z_vals

# === generate savings plot === #
fig, ax = plt.subplots()
ax.plot(a, R * a + z_vals[0] - c[:, 0], label='low income')
ax.plot(a, R * a + z_vals[1] - c[:, 1], label='high income')
ax.plot(a, a, 'k--')
ax.set_xlabel('current assets')
ax.set_ylabel('next period assets')
ax.legend(loc='upper left')
plt.show()

########NEW FILE########
__FILENAME__ = illustrates_clt
"""
Filename: illustrates_clt.py
Authors: John Stachurski and Thomas J. Sargent

Visual illustration of the central limit theorem.  Histograms draws of 

    Y_n := \sqrt{n} (\bar X_n - \mu)

for a given distribution of X_i, and a given choice of n.
"""
import numpy as np
from scipy.stats import expon, norm, poisson
import matplotlib.pyplot as plt
from matplotlib import rc

# == Specifying font, needs LaTeX integration == #
rc('font',**{'family':'serif','serif':['Palatino']})
rc('text', usetex=True)

# == Set parameters == #
n = 250     # Choice of n
k = 100000  # Number of draws of Y_n  
distribution = expon(2)  # Exponential distribution, lambda = 1/2 
mu, s = distribution.mean(), distribution.std()

# == Draw underlying RVs. Each row contains a draw of X_1,..,X_n == #
data = distribution.rvs((k, n)) 
# == Compute mean of each row, producing k draws of \bar X_n == #
sample_means = data.mean(axis=1)  
# == Generate observations of Y_n == #
Y = np.sqrt(n) * (sample_means - mu) 

# == Plot == #
fig, ax = plt.subplots()
xmin, xmax = -3 * s, 3 * s
ax.set_xlim(xmin, xmax)
ax.hist(Y, bins=60, alpha=0.5, normed=True)
xgrid = np.linspace(xmin, xmax, 200)
ax.plot(xgrid, norm.pdf(xgrid, scale=s), 'k-', lw=2, label=r'$N(0, \sigma^2)$')
ax.legend()

plt.show()




########NEW FILE########
__FILENAME__ = illustrates_lln
"""
Filename: illustrates_lln.py
Authors: John Stachurski and Thomas J. Sargent

Visual illustration of the law of large numbers.
"""

import random
import numpy as np
from scipy.stats import t, beta, lognorm, expon, gamma, poisson
import matplotlib.pyplot as plt

n = 100

# == Arbitrary collection of distributions == #
distributions = {"student's t with 10 degrees of freedom" : t(10),
                 "beta(2, 2)" : beta(2, 2),
                 "lognormal LN(0, 1/2)" : lognorm(0.5),
                 "gamma(5, 1/2)" : gamma(5, scale=2),
                 "poisson(4)" : poisson(4),
                 "exponential with lambda = 1" : expon(1)}

# == Create a figure and some axes == #
num_plots = 3
fig, axes = plt.subplots(num_plots, 1, figsize=(10, 10))

# == Set some plotting parameters to improve layout == #
bbox = (0., 1.02, 1., .102)
legend_args = {'ncol' : 2, 
               'bbox_to_anchor' : bbox, 
               'loc' : 3, 
               'mode' : 'expand'}
plt.subplots_adjust(hspace=0.5)

for ax in axes:
    # == Choose a randomly selected distribution == #
    name = random.choice(distributions.keys())
    distribution = distributions.pop(name)

    # == Generate n draws from the distribution == #
    data = distribution.rvs(n)

    # == Compute sample mean at each n == #
    sample_mean = np.empty(n)
    for i in range(n):
        sample_mean[i] = np.mean(data[:i])

    # == Plot == #
    ax.plot(range(n), data, 'o', color='grey', alpha=0.5)
    axlabel = r'$\bar X_n$' + ' for ' + r'$X_i \sim$' + ' ' + name
    ax.plot(range(n), sample_mean, 'g-', lw=3, alpha=0.6, label=axlabel)
    m = distribution.mean()
    ax.plot(range(n), [m] * n, 'k--', lw=1.5, label=r'$\mu$')
    ax.vlines(range(n), m, data, lw=0.2)
    ax.legend(**legend_args)

plt.show()




########NEW FILE########
__FILENAME__ = jv_test
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: jv_test.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

Tests jv.py with a particular parameterization.

"""
import matplotlib.pyplot as plt
from jv import workerProblem, bellman_operator
from quantecon.compute_fp import compute_fixed_point
import quantecon.jv as jv

# === solve for optimal policy === #
wp = jv.workerProblem(grid_size=25)
v_init = wp.x_grid * 0.5
V = compute_fixed_point(jv.bellman_operator, wp, v_init, max_iter=40)
s_policy, phi_policy = jv.bellman_operator(wp, V, return_policies=True)

# === plot policies === #
fig, ax = plt.subplots()
ax.set_xlim(0, max(wp.x_grid))
ax.set_ylim(-0.1, 1.1)
ax.plot(wp.x_grid, phi_policy, 'b-', label='phi')
ax.plot(wp.x_grid, s_policy, 'g-', label='s')
ax.legend()
plt.show()


########NEW FILE########
__FILENAME__ = linapprox
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt

def f(x):
    y1 = 2 * np.cos(6 * x) + np.sin(14 * x) 
    return y1 + 2.5

c_grid = np.linspace(0, 1, 6)

def Af(x):
    return sp.interp(x, c_grid, f(c_grid))

f_grid = np.linspace(0, 1, 150)

fig, ax = plt.subplots()
ax.set_xlim(0, 1)

ax.plot(f_grid, f(f_grid), 'b-', lw=2, alpha=0.8, label='true function')
ax.plot(f_grid, Af(f_grid), 'g-', lw=2, alpha=0.8, label='linear approximation')

ax.vlines(c_grid, c_grid * 0, f(c_grid), linestyle='dashed', alpha=0.5)
ax.legend(loc='upper center')

plt.show()

########NEW FILE########
__FILENAME__ = lin_interp_3d_plot
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: lin_inter_3d_plot.py
Authors: John Stachurski, Thomas J. Sargent
LastModified: 21/08/2013
"""

from scipy.interpolate import interp2d, LinearNDInterpolator
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D
import numpy as np

alpha = 0.7
phi_ext = 2 * 3.14 * 0.5

def f(a, b):
    #return 2 + alpha - 2 * np.cos(b)*np.cos(a) - alpha * np.cos(phi_ext - 2*b)
    return a + np.sqrt(b)

x_max = 3
y_max = 2.5

# === the approximation grid === #
Nx0, Ny0 = 25, 25
x0 = np.linspace(0, x_max, Nx0)
y0 = np.linspace(0, y_max, Ny0)
X0, Y0 = np.meshgrid(x0, y0)
points = np.column_stack((X0.ravel(1), Y0.ravel(1)))

# === generate the function values on the grid === #
Z0 = np.empty(Nx0 * Ny0)
for i in range(len(Z0)):
    a, b = points[i,:]
    Z0[i] = f(a, b)

g = LinearNDInterpolator(points, Z0)

# === a grid for plotting === #
Nx1, Ny1 = 100, 100
x1 = np.linspace(0, x_max, Nx1)
y1 = np.linspace(0, y_max, Ny1)
X1, Y1 = np.meshgrid(x1, y1)

# === the approximating function, as a matrix, for plotting === #
#ZA = np.empty((Ny1, Nx1))
#for i in range(Ny1):
#    for j in range(Nx1):
#        ZA[i, j] = g(x1[j], y1[i])
ZA = g(X1, Y1)
ZF = f(X1, Y1)

# === plot === #
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(1, 1, 1, projection='3d')
p = ax.plot_wireframe(X1, Y1, ZF, rstride=4, cstride=4)
plt.show()

########NEW FILE########
__FILENAME__ = lqramsey_ar1
"""
Filename: lqramsey_ar1.py
Authors: Thomas Sargent, Doc-Jin Jang, Jeong-hun Choi, John Stachurski

Example 1: Govt spending is AR(1) and state is (g, 1).

"""

import numpy as np
from numpy import array
import quantecon as qe

# == Parameters == #
beta = 1 / 1.05   
rho, mg = .7, .35
A = np.identity(2)
A[0,:] = rho, mg * (1-rho)
C = np.zeros((2, 1))
C[0, 0] = np.sqrt(1 - rho**2) * mg / 10 
Sg = array((1, 0)).reshape(1, 2)
Sd = array((0, 0)).reshape(1, 2)
Sb = array((0, 2.135)).reshape(1, 2)
Ss = array((0, 0)).reshape(1, 2)

economy = qe.lqramsey.Economy(beta=beta, 
        Sg=Sg, 
        Sd=Sd, 
        Sb=Sb, 
        Ss=Ss, 
        discrete=False, 
        proc=(A, C))

T = 50
path = qe.lqramsey.compute_paths(T, economy)
qe.lqramsey.gen_fig_1(path)



########NEW FILE########
__FILENAME__ = lqramsey_discrete
"""
Filename: lqramsey_discrete.py
Authors: Thomas Sargent, Doc-Jin Jang, Jeong-hun Choi, John Stachurski

LQ Ramsey model with discrete exogenous process.  

"""

import numpy as np
from numpy import array
import quantecon as qe

# == Parameters == #
beta = 1 / 1.05              
P = array([[0.8, 0.2, 0.0],   
           [0.0, 0.5, 0.5], 
           [0.0, 0.0, 1.0]]) 
# == Possible states of the world == #
# Each column is a state of the world. The rows are [g d b s 1]
x_vals = array([[0.5, 0.5, 0.25], 
                [0.0, 0.0, 0.0], 
                [2.2, 2.2, 2.2],
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0]])
Sg = array((1, 0, 0, 0, 0)).reshape(1, 5)
Sd = array((0, 1, 0, 0, 0)).reshape(1, 5)
Sb = array((0, 0, 1, 0, 0)).reshape(1, 5)
Ss = array((0, 0, 0, 1, 0)).reshape(1, 5)

economy = qe.lqramsey.Economy(beta=beta, 
        Sg=Sg, 
        Sd=Sd, 
        Sb=Sb, 
        Ss=Ss, 
        discrete=True, 
        proc=(P, x_vals))

T = 15
path = qe.lqramsey.compute_paths(T, economy)
qe.lqramsey.gen_fig_1(path)

########NEW FILE########
__FILENAME__ = lq_permanent_1
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: lq_permanent_1.py
Authors: John Stachurski and Thomas J. Sargent
LastModified: 19/09/2013

A permanent income / life-cycle model with iid income
"""

import numpy as np
import matplotlib.pyplot as plt
from quantecon.lqcontrol import LQ

# == Model parameters == #
r       = 0.05
beta    = 1 / (1 + r)
T       = 45
c_bar   = 2
sigma   = 0.25
mu      = 1
q       = 1e6

# == Formulate as an LQ problem == #
Q = 1
R = np.zeros((2, 2)) 
Rf = np.zeros((2, 2))
Rf[0, 0] = q
A = [[1 + r, -c_bar + mu], 
     [0,     1]]
B = [[-1],
     [0]]
C = [[sigma],
     [0]]

# == Compute solutions and simulate == #
lq = LQ(Q, R, A, B, C, beta=beta, T=T, Rf=Rf)
x0 = (0, 1)
xp, up, wp = lq.compute_sequence(x0)

# == Convert back to assets, consumption and income == #
assets = xp[0, :]           # a_t 
c = up.flatten() + c_bar    # c_t
income = wp[0, 1:] + mu     # y_t

# == Plot results == #
n_rows = 2
fig, axes = plt.subplots(n_rows, 1, figsize=(12, 10))

plt.subplots_adjust(hspace=0.5)
for i in range(n_rows):
    axes[i].grid()
    axes[i].set_xlabel(r'Time')
bbox = (0., 1.02, 1., .102)
legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
p_args = {'lw' : 2, 'alpha' : 0.7}

axes[0].plot(range(1, T+1), income, 'g-', label="non-financial income", **p_args)
axes[0].plot(range(T), c, 'k-', label="consumption", **p_args)
axes[0].legend(ncol=2, **legend_args)

axes[1].plot(range(1, T+1), np.cumsum(income - mu), 'r-', label="cumulative unanticipated income", **p_args)
axes[1].plot(range(T+1), assets, 'b-', label="assets", **p_args)
axes[1].plot(range(T), np.zeros(T), 'k-')
axes[1].legend(ncol=2, **legend_args)

plt.show()


########NEW FILE########
__FILENAME__ = lucas_tree_price1

from __future__ import division  # Omit for Python 3.x
import numpy as np
import matplotlib.pyplot as plt
from quantecon.lucastree import lucas_tree, compute_price

fig, ax = plt.subplots()
#grid = np.linspace(1e-10, 4, 100)

tree = lucas_tree(gamma=2, beta=0.95, alpha=0.90, sigma=0.1)
grid, price_vals = compute_price(tree)
ax.plot(grid, price_vals, lw=2, alpha=0.7, label=r'$p^*(y)$')
ax.set_xlim(min(grid), max(grid))

#tree = lucas_tree(gamma=3, beta=0.95, alpha=0.90, sigma=0.1)
#grid, price_vals = compute_price(tree)
#ax.plot(grid, price_vals, lw=2, alpha=0.7, label='more patient')
#ax.set_xlim(min(grid), max(grid))

ax.set_xlabel(r'$y$', fontsize=16)
ax.set_ylabel(r'price', fontsize=16)
ax.legend(loc='upper left')

plt.show()


########NEW FILE########
__FILENAME__ = mc_convergence_plot
"""
Filename: mc_convergence_plot.py
Authors: John Stachurski, Thomas J. Sargent

"""
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from quantecon import mc_tools

P = ((0.971, 0.029, 0.000),  
     (0.145, 0.778, 0.077), 
     (0.000, 0.508, 0.492))
P = np.array(P)

psi = (0.0, 0.2, 0.8)        # Initial condition

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_zlim(0, 1)
ax.set_xticks((0.25, 0.5, 0.75))
ax.set_yticks((0.25, 0.5, 0.75))
ax.set_zticks((0.25, 0.5, 0.75))

x_vals, y_vals, z_vals = [], [], []
for t in range(20):
    x_vals.append(psi[0])
    y_vals.append(psi[1])
    z_vals.append(psi[2])
    psi = np.dot(psi, P)

ax.scatter(x_vals, y_vals, z_vals, c='r', s=60)

psi_star = mc_tools.compute_stationary(P)
ax.scatter(psi_star[0], psi_star[1], psi_star[2], c='k', s=60)

plt.show()

########NEW FILE########
__FILENAME__ = nds
import matplotlib.pyplot as plt 
import numpy as np
from scipy.stats import norm
from random import uniform

fig, ax = plt.subplots()
x = np.linspace(-4, 4, 150)
for i in range(3):
    m, s = uniform(-1, 1), uniform(1, 2)
    y = norm.pdf(x, loc=m, scale=s)
    current_label = r'$\mu = {0:.2f}$'.format(m)
    ax.plot(x, y, linewidth=2, alpha=0.6, label=current_label)
ax.legend()
plt.show()



########NEW FILE########
__FILENAME__ = nx_demo
"""
Filename: nx_demo.py
Authors: John Stachurski and Thomas J. Sargent
"""

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np

G = nx.random_geometric_graph(200, 0.12)  # Generate random graph
pos = nx.get_node_attributes(G, 'pos')    # Get positions of nodes
# find node nearest the center point (0.5,0.5)
dists = [(x - 0.5)**2 + (y - 0.5)**2 for x, y in pos.values()]
ncenter = np.argmin(dists)
# Plot graph, coloring by path length from central node 
p = nx.single_source_shortest_path_length(G, ncenter)
plt.figure()
nx.draw_networkx_edges(G, pos, alpha=0.4)
nx.draw_networkx_nodes(G, pos, nodelist=p.keys(),
                       node_size=120, alpha=0.5,
                       node_color=p.values(), cmap=plt.cm.jet_r)
plt.show()

########NEW FILE########
__FILENAME__ = odu_plot_densities
"""
Filename: odu_plot_densities.py
Authors: John Stachurski, Thomas J. Sargent

"""
import numpy as np
import matplotlib.pyplot as plt
from quantecon import odu_vfi

sp = odu_vfi.searchProblem(F_a=1, F_b=1, G_a=3, G_b=1.2)
grid = np.linspace(0, 2, 150)
fig, ax = plt.subplots()
ax.plot(grid, sp.f(grid), label=r'$f$', lw=2)
ax.plot(grid, sp.g(grid), label=r'$g$', lw=2)
ax.legend(loc=0)
plt.show()

########NEW FILE########
__FILENAME__ = odu_vfi_plots
"""
Filename: odu_vfi_plots.py
Authors: John Stachurski and Thomas Sargent
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D
from matplotlib import cm
from scipy.interpolate import LinearNDInterpolator
import numpy as np

from quantecon import odu_vfi 
from quantecon.compute_fp import compute_fixed_point


sp = odu_vfi.searchProblem(w_grid_size=100, pi_grid_size=100)
v_init = np.zeros(len(sp.grid_points)) + sp.c / (1 - sp.beta)
v = compute_fixed_point(odu_vfi.bellman, sp, v_init)
policy = odu_vfi.get_greedy(sp, v)

# Make functions from these arrays by interpolation
vf = LinearNDInterpolator(sp.grid_points, v)
pf = LinearNDInterpolator(sp.grid_points, policy)

pi_plot_grid_size, w_plot_grid_size = 100, 100
pi_plot_grid = np.linspace(0.001, 0.99, pi_plot_grid_size)
w_plot_grid = np.linspace(0, sp.w_max, w_plot_grid_size)

#plot_choice = 'value_function'
plot_choice = 'policy_function'

if plot_choice == 'value_function':
    Z = np.empty((w_plot_grid_size, pi_plot_grid_size))
    for i in range(w_plot_grid_size):
        for j in range(pi_plot_grid_size):
            Z[i, j] = vf(w_plot_grid[i], pi_plot_grid[j])
    fig, ax = plt.subplots()
    ax.contourf(pi_plot_grid, w_plot_grid, Z, 12, alpha=0.6, cmap=cm.jet)
    cs = ax.contour(pi_plot_grid, w_plot_grid, Z, 12, colors="black")
    ax.clabel(cs, inline=1, fontsize=10)
    ax.set_xlabel('pi', fontsize=14)
    ax.set_ylabel('wage', fontsize=14)
else:
    Z = np.empty((w_plot_grid_size, pi_plot_grid_size))
    for i in range(w_plot_grid_size):
        for j in range(pi_plot_grid_size):
            Z[i, j] = pf(w_plot_grid[i], pi_plot_grid[j])
    fig, ax = plt.subplots()
    ax.contourf(pi_plot_grid, w_plot_grid, Z, 1, alpha=0.6, cmap=cm.jet)
    ax.contour(pi_plot_grid, w_plot_grid, Z, 1, colors="black")
    ax.set_xlabel('pi', fontsize=14)
    ax.set_ylabel('wage', fontsize=14)
    ax.text(0.4, 1.0, 'reject')
    ax.text(0.7, 1.8, 'accept')

plt.show()

########NEW FILE########
__FILENAME__ = optgrowth_v0
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: optgrowth_v0.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

A first pass at solving the optimal growth problem via value function
iteration, provided as an introduction to the techniques.  A more general
version is provided in optgrowth.py.

"""
from __future__ import division  # Omit for Python 3.x
import matplotlib.pyplot as plt
import numpy as np
from numpy import log
from scipy.optimize import fminbound
from scipy import interp

## Primitives and grid
alpha = 0.65
beta=0.95
grid_max=2 
grid_size=150
grid = np.linspace(1e-6, grid_max, grid_size)
## Exact solution
ab = alpha * beta
c1 = (log(1 - ab) + log(ab) * ab / (1 - ab)) / (1 - beta)
c2 = alpha / (1 - ab)
def v_star(k):
    return c1 + c2 * log(k)

def bellman_operator(w):
    """
    The approximate Bellman operator, which computes and returns the updated
    value function Tw on the grid points.

        * w is a flat NumPy array with len(w) = len(grid)

    The vector w represents the value of the input function on the grid
    points.
    """
    # === Apply linear interpolation to w === #
    Aw = lambda x: interp(x, grid, w)  

    # === set Tw[i] equal to max_c { log(c) + beta w(f(k_i) - c)} === #
    Tw = np.empty(grid_size)
    for i, k in enumerate(grid):
        objective = lambda c:  - log(c) - beta * Aw(k**alpha - c)
        c_star = fminbound(objective, 1e-6, k**alpha)
        Tw[i] = - objective(c_star)

    return Tw

# === If file is run directly, not imported, produce figure === #
if __name__ == '__main__':  

    w = 5 * log(grid) - 25  # An initial condition -- fairly arbitrary
    n = 35
    fig, ax = plt.subplots()
    ax.set_ylim(-40, -20)
    ax.set_xlim(np.min(grid), np.max(grid))
    ax.plot(grid, w, color=plt.cm.jet(0), lw=2, alpha=0.6, label='initial condition')
    for i in range(n):
        w = bellman_operator(w)
        ax.plot(grid, w, color=plt.cm.jet(i / n), lw=2, alpha=0.6)
    ax.plot(grid, v_star(grid), 'k-', lw=2, alpha=0.8, label='true value function')
    ax.legend(loc='upper left')

    plt.show()


########NEW FILE########
__FILENAME__ = paths_and_hist

import numpy as np
import matplotlib.pyplot as plt
from quantecon.lss import LSS
import random

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.1

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [sigma, 0, 0, 0]
G = [1, 0, 0, 0]

T = 30
ar = LSS(A, C, G, mu_0=np.ones(4))

ymin, ymax = -0.8, 1.25

fig, axes = plt.subplots(1, 2, figsize=(8, 3))

for ax in axes:
    ax.grid(alpha=0.4)

ax = axes[0]

ax.set_ylim(ymin, ymax)
ax.set_ylabel(r'$y_t$', fontsize=16)
ax.vlines((T,), -1.5, 1.5)

ax.set_xticks((T,))
ax.set_xticklabels((r'$T$',))

sample = []
for i in range(20):
    rcolor = random.choice(('c', 'g', 'b', 'k'))
    x, y = ar.simulate(ts_length=T+15)
    y = y.flatten()
    ax.plot(y, color=rcolor, lw=1, alpha=0.5)
    ax.plot((T,), (y[T],), 'ko', alpha=0.5)
    sample.append(y[T])

y = y.flatten()
axes[1].set_ylim(ymin, ymax)
axes[1].hist(sample, bins=16, normed=True, orientation='horizontal', alpha=0.5)

plt.show()

########NEW FILE########
__FILENAME__ = paths_and_stationarity

import numpy as np
import matplotlib.pyplot as plt
from lss import LSS
import random

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.1

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [sigma, 0, 0, 0]
G = [1, 0, 0, 0]

T0 = 10
T1 = 50
T2 = 75
T4 = 100

ar = LSS(A, C, G, mu_0=np.ones(4))
ymin, ymax = -0.8, 1.25

fig, ax = plt.subplots(figsize=(8, 5))

ax.grid(alpha=0.4)
ax.set_ylim(ymin, ymax)
ax.set_ylabel(r'$y_t$', fontsize=16)
ax.vlines((T0, T1, T2), -1.5, 1.5)

ax.set_xticks((T0, T1, T2))
ax.set_xticklabels((r"$T$", r"$T'$", r"$T''$"), fontsize=14)

sample = []
for i in range(80):
    rcolor = random.choice(('c', 'g', 'b'))
    x, y = ar.simulate(ts_length=T4)
    y = y.flatten()
    ax.plot(y, color=rcolor, lw=0.8, alpha=0.5)
    ax.plot((T0, T1, T2), (y[T0], y[T1], y[T2],), 'ko', alpha=0.5)

plt.show()

########NEW FILE########
__FILENAME__ = perm_inc_fig1
"""
Plots consumption, income and debt for the simple infinite horizon LQ
permanent income model with Gaussian iid income.
"""

from __future__ import division
import random
import numpy as np
import matplotlib.pyplot as plt

r       = 0.05
beta    = 1 / (1 + r)
T       = 60
sigma   = 0.15
mu = 1

def time_path():
    w = np.random.randn(T+1) # w_0, w_1, ..., w_T
    w[0] = 0
    b = np.zeros(T+1)
    for t in range(1, T+1):
        b[t] = w[1:t].sum()
    b = - sigma * b
    c = mu + (1 - beta) * (sigma * w - b)
    return w, b, c



if 1:
    fig, ax = plt.subplots()

    p_args = {'lw' : 2, 'alpha' : 0.7}
    ax.grid()
    ax.set_xlabel(r'Time')
    bbox = (0., 1.02, 1., .102)
    legend_args = {'bbox_to_anchor' : bbox, 'loc' : 'upper left', 'mode' : 'expand'}

    w, b, c = time_path()
    ax.plot(range(T+1), mu + sigma * w, 'g-', label="non-financial income", **p_args)
    ax.plot(range(T+1), c, 'k-', label="consumption", **p_args)
    ax.plot(range(T+1), b, 'b-', label="debt", **p_args)
    ax.legend(ncol=3, **legend_args)

    plt.show()


if 0:
    fig, ax = plt.subplots()

    p_args = {'lw' : 0.8, 'alpha' : 0.7}
    ax.grid()
    ax.set_xlabel(r'Time')
    ax.set_ylabel(r'Consumption')
    b_sum = np.zeros(T+1)
    for i in range(250):
        rcolor = random.choice(('c', 'g', 'b', 'k'))
        w, b, c = time_path()
        ax.plot(range(T+1), c, color=rcolor, **p_args)

    plt.show()



########NEW FILE########
__FILENAME__ = perm_inc_ir
"""
Impulse response functions for the LQ permanent income model permanent and
transitory shocks.
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt

r       = 0.05
beta    = 1 / (1 + r)
T       = 20  # Time horizon
S       = 5   # Impulse date
sigma1  = sigma2 = 0.15

def time_path(permanent=False):
    "Time path of consumption and debt given shock sequence"
    w1 = np.zeros(T+1) 
    w2 = np.zeros(T+1) 
    b = np.zeros(T+1)
    c = np.zeros(T+1)
    if permanent:
        w1[S+1] = 1.0
    else:
        w2[S+1] = 1.0
    for t in range(1, T):
        b[t+1] = b[t] - sigma2 * w2[t]
        c[t+1] = c[t] + sigma1 * w1[t+1] + (1 - beta) * sigma2 * w2[t+1]
    return b, c


fig, axes = plt.subplots(2, 1)
plt.subplots_adjust(hspace=0.5)
p_args = {'lw' : 2, 'alpha' : 0.7}

L = 0.175

for ax in axes:
    ax.grid(alpha=0.5)
    ax.set_xlabel(r'Time')
    ax.set_ylim(-L, L)
    ax.plot((S, S), (-L, L), 'k-', lw=0.5)

ax = axes[0]
b, c = time_path(permanent=0)
ax.set_title('impulse-response, transitory income shock')
ax.plot(range(T+1), c, 'g-', label="consumption", **p_args)
ax.plot(range(T+1), b, 'b-', label="debt", **p_args)
ax.legend(loc='upper right')

ax = axes[1]
b, c = time_path(permanent=1)
ax.set_title('impulse-response, permanent income shock')
ax.plot(range(T+1), c, 'g-', label="consumption", **p_args)
ax.plot(range(T+1), b, 'b-', label="debt", **p_args)
ax.legend(loc='lower right')
plt.show()


########NEW FILE########
__FILENAME__ = plot_example_1
import matplotlib.pyplot as plt   
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'b-', linewidth=2)
plt.show()

########NEW FILE########
__FILENAME__ = plot_example_2
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', lw=2, label='sine function', alpha=0.6)
ax.legend(loc='upper center')
plt.show()

########NEW FILE########
__FILENAME__ = plot_example_3
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', lw=2, label=r'$y=\sin(x)$', alpha=0.6)
ax.legend(loc='upper center')
plt.show()


########NEW FILE########
__FILENAME__ = plot_example_4
import matplotlib.pyplot as plt 
import numpy as np
from scipy.stats import norm
from random import uniform
fig, ax = plt.subplots()
x = np.linspace(-4, 4, 150)
for i in range(3):
    m, s = uniform(-1, 1), uniform(1, 2)
    y = norm.pdf(x, loc=m, scale=s)
    current_label = r'$\mu = {0:.2f}$'.format(m)
    ax.plot(x, y, lw=2, alpha=0.6, label=current_label)
ax.legend()
plt.show()

########NEW FILE########
__FILENAME__ = plot_example_5
import matplotlib.pyplot as plt 
import numpy as np
from scipy.stats import norm
from random import uniform
num_rows, num_cols = 2, 3
fig, axes = plt.subplots(num_rows, num_cols, figsize=(12, 8))
for i in range(num_rows):
    for j in range(num_cols):
        m, s = uniform(-1, 1), uniform(1, 2)
        x = norm.rvs(loc=m, scale=s, size=100)
        axes[i, j].hist(x, alpha=0.6, bins=20)
        t = r'$\mu = {0:.1f},\; \sigma = {1:.1f}$'.format(m, s)
        axes[i, j].set_title(t)
        axes[i, j].set_xticks([-4, 0, 4]) 
        axes[i, j].set_yticks([])
plt.show()


########NEW FILE########
__FILENAME__ = preim1
"""
QE by Tom Sargent and John Stachurski.
Illustrates preimages of functions
"""
import matplotlib.pyplot as plt
import numpy as np

def f(x):
    return 0.6 * np.cos(4 * x) + 1.4


xmin, xmax = -1, 1
x = np.linspace(xmin, xmax, 160)
y = f(x)
ya, yb = np.min(y), np.max(y)

fig, axes = plt.subplots(2, 1, figsize=(8, 8))

for ax in axes:
# Set the axes through the origin
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_position('zero')
    for spine in ['right', 'top']:
        ax.spines[spine].set_color('none')

    ax.set_ylim(-0.6, 3.2)
    ax.set_xlim(xmin, xmax)
    ax.set_yticks(())
    ax.set_xticks(())

    ax.plot(x, y, 'k-', lw=2, label=r'$f$') 
    ax.fill_between(x, ya, yb, facecolor='blue', alpha=0.05)
    ax.vlines([0], ya, yb, lw=3, color='blue', label=r'range of $f$')
    ax.text(0.04, -0.3, '$0$', fontsize=16)

ax = axes[0]

ax.legend(loc='upper right', frameon=False)
ybar = 1.5
ax.plot(x, x * 0 + ybar, 'k--', alpha=0.5)
ax.text(0.05, 0.8 * ybar, r'$y$', fontsize=16)
for i, z in enumerate((-0.35, 0.35)):
    ax.vlines(z, 0, f(z), linestyle='--', alpha=0.5)
    ax.text(z, -0.2, r'$x_{}$'.format(i), fontsize=16)

ax = axes[1]

ybar = 2.6
ax.plot(x, x * 0 + ybar, 'k--', alpha=0.5)
ax.text(0.04, 0.91 * ybar, r'$y$', fontsize=16)

plt.show()

########NEW FILE########
__FILENAME__ = pylab_eg
from pylab import *
x = linspace(0, 10, 200)
y = sin(x)
plot(x, y, 'b-', linewidth=2)
show()

########NEW FILE########
__FILENAME__ = qs

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm
from matplotlib import cm

xmin, xmax = -4, 12
x = 10
alpha = 0.5

m, v = x, 10

xgrid = np.linspace(xmin, xmax, 200)

fig, ax = plt.subplots()

ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.spines['left'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.spines['bottom'].set_position(('data',0))

ax.set_ylim(-0.05, 0.5)
ax.set_xticks((x,))
ax.set_xticklabels((r'$x$',), fontsize=18)
ax.set_yticks(())

K = 3
for i in range(K):
    m = alpha * m
    v = alpha * alpha * v + 1
    f = norm(loc=m, scale=np.sqrt(v))
    k = (i + 0.5) / K
    ax.plot(xgrid, f.pdf(xgrid), lw=1, color='black', alpha=0.4)
    ax.fill_between(xgrid, 0 * xgrid, f.pdf(xgrid), color=cm.jet(k), alpha=0.4)


ax.annotate(r'$Q(x,\cdot)$', xy=(6.6, 0.2),  xycoords='data',
         xytext=(20, 90), textcoords='offset points', fontsize=16,
         arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2"))
ax.annotate(r'$Q^2(x,\cdot)$', xy=(3.6, 0.24),  xycoords='data',
         xytext=(20, 90), textcoords='offset points', fontsize=16,
         arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2"))
ax.annotate(r'$Q^3(x,\cdot)$', xy=(-0.2, 0.28),  xycoords='data',
         xytext=(-90, 90), textcoords='offset points', fontsize=16,
         arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2"))
fig.show()

########NEW FILE########
__FILENAME__ = quadmap_class
"""
Filename: quadmap_class.py
Authors: John Stachurski, Thomas J. Sargent

"""


class QuadMap:

    def __init__(self, initial_state):
        self.x = initial_state

    def update(self):
        "Apply the quadratic map to update the state."
        self.x = 4 * self.x * (1 - self.x)

    def generate_series(self, n): 
        """
        Generate and return a trajectory of length n, starting at the 
        current state.
        """
        trajectory = []
        for i in range(n):
            trajectory.append(self.x)
            self.update()
        return trajectory


########NEW FILE########
__FILENAME__ = robust_monopolist
"""
Filename: robust_monopolist.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski 

The robust control problem for a monopolist with adjustment costs.  The
inverse demand curve is:

  p_t = a_0 - a_1 y_t + d_t

where d_{t+1} = \rho d_t + \sigma_d w_{t+1} for w_t ~ N(0,1) and iid.  
The period return function for the monopolist is

  r_t =  p_t y_t - gamma (y_{t+1} - y_t)^2 / 2 - c y_t   

The objective of the firm is E_t \sum_{t=0}^\infty \beta^t r_t

For the linear regulator, we take the state and control to be

    x_t = (1, y_t, d_t) and u_t = y_{t+1} - y_t 

"""

from __future__ import division
import pandas as pd
import numpy as np
from scipy.linalg import eig
from scipy import interp
import matplotlib.pyplot as plt

import quantecon as qe

# == model parameters == #

a_0     = 100
a_1     = 0.5
rho     = 0.9
sigma_d = 0.05
beta    = 0.95
c       = 2
gamma   = 50.0

theta = 0.002
ac    = (a_0 - c) / 2.0

# == Define LQ matrices == #

R = np.array([[0,  ac,    0], 
              [ac, -a_1, 0.5], 
              [0., 0.5,  0]])

R = -R  # For minimization
Q = gamma / 2

A = np.array([[1., 0., 0.], 
              [0., 1., 0.], 
              [0., 0., rho]])
B = np.array([[0.], 
              [1.], 
              [0.]])
C = np.array([[0.], 
              [0.], 
              [sigma_d]])

#-----------------------------------------------------------------------------#
#                                 Functions 
#-----------------------------------------------------------------------------#


def evaluate_policy(theta, F):
    """
    Given theta (scalar, dtype=float) and policy F (array_like), returns the
    value associated with that policy under the worst case path for {w_t}, as
    well as the entropy level.
    """
    rlq = qe.robustlq.RBLQ(Q, R, A, B, C, beta, theta)
    K_F, P_F, d_F, O_F, o_F = rlq.evaluate_F(F)
    x0 = np.array([[1.], [0.], [0.]])
    value = - x0.T.dot(P_F.dot(x0)) - d_F
    entropy = x0.T.dot(O_F.dot(x0)) + o_F
    return map(float, (value, entropy))


def value_and_entropy(emax, F, bw, grid_size=1000):
    """
    Compute the value function and entropy levels for a theta path
    increasing until it reaches the specified target entropy value.

    Parameters
    ==========
    emax : scalar
        The target entropy value

    F : array_like
        The policy function to be evaluated

    bw : str
        A string specifying whether the implied shock path follows best
        or worst assumptions. The only acceptable values are 'best' and
        'worst'.

    Returns
    =======
    df : pd.DataFrame
        A pandas DataFrame containing the value function and entropy
        values up to the emax parameter. The columns are 'value' and
        'entropy'.

    """
    if bw == 'worst':
        thetas = 1 / np.linspace(1e-8, 1000, grid_size)
    else:
        thetas = -1 / np.linspace(1e-8, 1000, grid_size)

    df = pd.DataFrame(index=thetas, columns=('value', 'entropy'))

    for theta in thetas:
        df.ix[theta] = evaluate_policy(theta, F)
        if df.ix[theta, 'entropy'] >= emax:
            break

    df = df.dropna(how='any')
    return df


#-----------------------------------------------------------------------------#
#                                    Main
#-----------------------------------------------------------------------------#


# == Compute the optimal rule == #
optimal_lq = qe.lqcontrol.LQ(Q, R, A, B, C, beta)
Po, Fo, do = optimal_lq.stationary_values()

# == Compute a robust rule given theta == #
baseline_robust = qe.robustlq.RBLQ(Q, R, A, B, C, beta, theta)
Fb, Kb, Pb = baseline_robust.robust_rule()

# == Check the positive definiteness of worst-case covariance matrix to == #
# == ensure that theta exceeds the breakdown point == #
test_matrix = np.identity(Pb.shape[0]) - np.dot(C.T, Pb.dot(C)) / theta
eigenvals, eigenvecs = eig(test_matrix)
assert (eigenvals >= 0).all(), 'theta below breakdown point.'


emax = 1.6e6

optimal_best_case = value_and_entropy(emax, Fo, 'best')
robust_best_case = value_and_entropy(emax, Fb, 'best')
optimal_worst_case = value_and_entropy(emax, Fo, 'worst')
robust_worst_case = value_and_entropy(emax, Fb, 'worst')

fig, ax = plt.subplots()

ax.set_xlim(0, emax)
ax.set_ylabel("Value")
ax.set_xlabel("Entropy")
ax.grid()

for axis in 'x', 'y':
    plt.ticklabel_format(style='sci', axis=axis, scilimits=(0,0))

plot_args = {'lw' : 2, 'alpha' : 0.7} 

colors = 'r', 'b'

df_pairs = ((optimal_best_case, optimal_worst_case),
            (robust_best_case, robust_worst_case))

class Curve:

    def __init__(self, x, y):
        self.x, self.y = x, y

    def __call__(self, z):
        return interp(z, self.x, self.y)


for c, df_pair in zip(colors, df_pairs):
    curves = []
    for df in df_pair:
        # == Plot curves == #
        x, y = df['entropy'], df['value']
        x, y = (np.asarray(a, dtype='float') for a in (x, y))
        egrid = np.linspace(0, emax, 100)
        curve = Curve(x, y)
        print ax.plot(egrid, curve(egrid), color=c, **plot_args)
        curves.append(curve)
    # == Color fill between curves == #
    ax.fill_between(egrid, 
            curves[0](egrid), 
            curves[1](egrid), 
            color=c, alpha=0.1)

plt.show()


########NEW FILE########
__FILENAME__ = sine2
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', linewidth=2, label='sine function', alpha=0.6)
ax.legend()
plt.show()



########NEW FILE########
__FILENAME__ = sine3
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', linewidth=2, label='sine function', alpha=0.6)
ax.legend(loc='upper center')
plt.show()



########NEW FILE########
__FILENAME__ = sine4
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', linewidth=2, label=r'$y=\sin(x)$', alpha=0.6)
ax.legend(loc='upper center')
plt.show()


########NEW FILE########
__FILENAME__ = sine5
import matplotlib.pyplot as plt 
import numpy as np
fig, ax = plt.subplots()
x = np.linspace(0, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', linewidth=2, label=r'$y=\sin(x)$', alpha=0.6)
ax.legend(loc='upper center')
ax.set_yticks([-1, 0, 1]) 
ax.set_title('Test plot') 
plt.show()



########NEW FILE########
__FILENAME__ = six_hists
import matplotlib.pyplot as plt 
import numpy as np
from scipy.stats import norm
from random import uniform
num_rows, num_cols = 3, 2
fig, axes = plt.subplots(num_rows, num_cols, figsize=(8, 12))
for i in range(num_rows):
    for j in range(num_cols):
        m, s = uniform(-1, 1), uniform(1, 2)
        x = norm.rvs(loc=m, scale=s, size=100)
        axes[i, j].hist(x, alpha=0.6, bins=20)
        t = r'$\mu = {0:.1f}, \quad \sigma = {1:.1f}$'.format(m, s)
        axes[i, j].set_title(t)
        axes[i, j].set_xticks([-4, 0, 4]) 
        axes[i, j].set_yticks([])
plt.show()



########NEW FILE########
__FILENAME__ = stochasticgrowth
"""
Neoclassical growth model with constant savings rate, where the dynamics are
given by

    k_{t+1} = s A_t f(k_t) + (1 - delta) k_t

Marginal densities are computed using the look-ahead estimator.  Thus, the
estimate of the density psi_t of k_t is

    (1/n) sum_{i=0}^n p(k_{t-1}^i, y)

This is a density in y.  
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import lognorm, beta
from quantecon.lae import LAE

# == Define parameters == #
s = 0.2
delta = 0.1
a_sigma = 0.4       # A = exp(B) where B ~ N(0, a_sigma)
alpha = 0.4         # We set f(k) = k**alpha
psi_0 = beta(5, 5, scale=0.5)  # Initial distribution
phi = lognorm(a_sigma) 

def p(x, y):
    """
    Stochastic kernel for the growth model with Cobb-Douglas production.
    Both x and y must be strictly positive.
    """
    d = s * x**alpha
    return phi.pdf((y - (1 - delta) * x) / d) / d

n = 10000    # Number of observations at each date t
T = 30       # Compute density of k_t at 1,...,T+1

# == Generate matrix s.t. t-th column is n observations of k_t == #
k = np.empty((n, T))
A = phi.rvs((n, T))
k[:, 0] = psi_0.rvs(n)  # Draw first column from initial distribution
for t in range(T-1):
    k[:, t+1] = s * A[:,t] * k[:, t]**alpha + (1 - delta) * k[:, t]

# == Generate T instances of LAE using this data, one for each date t == #
laes = [LAE(p, k[:, t]) for t in range(T)]  

# == Plot == #
fig, ax = plt.subplots()
ygrid = np.linspace(0.01, 4.0, 200)
greys = [str(g) for g in np.linspace(0.0, 0.8, T)]
greys.reverse()
for psi, g in zip(laes, greys):
    ax.plot(ygrid, psi(ygrid), color=g, lw=2, alpha=0.6)
ax.set_xlabel('capital')
title = r'Density of $k_1$ (lighter) to $k_T$ (darker) for $T={}$'
ax.set_title(title.format(T))
plt.show()

########NEW FILE########
__FILENAME__ = subplots

import matplotlib.pyplot as plt
import numpy as np

def subplots():
    "Custom subplots with axes throught the origin"
    fig, ax = plt.subplots()

    # Set the axes through the origin
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_position('zero')
    for spine in ['right', 'top']:
        ax.spines[spine].set_color('none')
    
    ax.grid()
    return fig, ax


fig, ax = subplots()  # Call the local version, not plt.subplots()
x = np.linspace(-2, 10, 200)
y = np.sin(x)
ax.plot(x, y, 'r-', linewidth=2, label='sine function', alpha=0.6)
ax.legend(loc='lower right')
plt.show()


########NEW FILE########
__FILENAME__ = temp


########NEW FILE########
__FILENAME__ = test_program_1
import pylab
from random import normalvariate
ts_length = 100
epsilon_values = []   # An empty list
for i in range(ts_length):
    e = normalvariate(0, 1)
    epsilon_values.append(e)
pylab.plot(epsilon_values, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_2
import pylab
from random import normalvariate
ts_length = 100
epsilon_values = []   
i = 0
while i < ts_length:
    e = normalvariate(0, 1)
    epsilon_values.append(e)
    i = i + 1
pylab.plot(epsilon_values, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_3
import pylab
from random import normalvariate

def generate_data(n):
    epsilon_values = []   
    for i in range(n):
        e = normalvariate(0, 1)
        epsilon_values.append(e)
    return epsilon_values

data = generate_data(100)
pylab.plot(data, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_4
import pylab
from random import normalvariate, uniform

def generate_data(n, generator_type):
    epsilon_values = []   
    for i in range(n):
        if generator_type == 'U':
            e = uniform(0, 1)
        else:
            e = normalvariate(0, 1)
        epsilon_values.append(e)
    return epsilon_values

data = generate_data(100, 'U')
pylab.plot(data, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_5
import pylab
from random import normalvariate, uniform

def generate_data(n, generator_type):
    epsilon_values = []   
    for i in range(n):
        e = uniform(0, 1) if generator_type == 'U' else normalvariate(0, 1)
        epsilon_values.append(e)
    return epsilon_values

data = generate_data(100, 'U')
pylab.plot(data, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_5_short
import pylab
from random import normalvariate, uniform

def generate_data(n, generator_type):
    epsilon_values = []   
    for i in range(n):
        e = uniform(0, 1) if generator_type == 'U' \
                             else normalvariate(0, 1)
        epsilon_values.append(e)
    return epsilon_values

ts_length = 100
data = generate_data(ts_length, 'U')
pylab.plot(data, 'b-')
pylab.show()

########NEW FILE########
__FILENAME__ = test_program_6
import pylab
from random import normalvariate, uniform

def generate_data(n, generator_type):
    epsilon_values = []   
    for i in range(n):
        e = generator_type(0, 1)
        epsilon_values.append(e)
    return epsilon_values

data = generate_data(100, uniform)
pylab.plot(data, 'b-')
pylab.show()


########NEW FILE########
__FILENAME__ = tsh_hg

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from quantecon.lss import LSS
import random

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.1

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [sigma, 0, 0, 0]
G = [1, 0, 0, 0]

T = 30
ar = LSS(A, C, G)

ymin, ymax = -0.8, 1.25

fig, ax = plt.subplots(figsize=(8,4))

ax.set_xlim(ymin, ymax)
ax.set_xlabel(r'$y_t$', fontsize=16)

x, y = ar.replicate(T=T, num_reps=500000)
mu_x, mu_y, Sigma_x, Sigma_y = ar.moments(T=T, mu_0=np.ones(4))
f_y = norm(loc=float(mu_y), scale=float(np.sqrt(Sigma_y)))

y = y.flatten()
ax.hist(y, bins=50, normed=True, alpha=0.4)

ygrid = np.linspace(ymin, ymax, 150)
ax.plot(ygrid, f_y.pdf(ygrid), 'k-', lw=2, alpha=0.8, label='true density')
ax.legend()
plt.show()

########NEW FILE########
__FILENAME__ = us_cities
data_file = open('us_cities.txt', 'r')
for line in data_file:
    city, population = line.split(':')            # Tuple unpacking
    city = city.title()                           # Capitalize city names
    population = '{0:,}'.format(int(population))  # Add commas to numbers
    print(city.ljust(15) + population)
data_file.close()

########NEW FILE########
__FILENAME__ = vecs
"""
QE by Tom Sargent and John Stachurski.
Illustrates vectors in the plane.
"""
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
# Set the axes through the origin
for spine in ['left', 'bottom']:
    ax.spines[spine].set_position('zero')
for spine in ['right', 'top']:
    ax.spines[spine].set_color('none')
    

ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.grid()
vecs = ((2, 4), (-3, 3), (-4, -3.5))
for v in vecs:
    ax.annotate('', xy=v, xytext=(0, 0), 
                arrowprops=dict(facecolor='blue', 
                    shrink=0, 
                    alpha=0.7,
                    width=0.5))
    ax.text(1.1 * v[0], 1.1 * v[1], str(v))
plt.show()

########NEW FILE########
__FILENAME__ = vecs2
"""
QE by Tom Sargent and John Stachurski.
Illustrates scalar multiplication.
"""
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots()
# Set the axes through the origin
for spine in ['left', 'bottom']:
    ax.spines[spine].set_position('zero')
for spine in ['right', 'top']:
    ax.spines[spine].set_color('none')
    
ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)

x = (2, 2)
ax.annotate('', xy=x, xytext=(0, 0), 
            arrowprops=dict(facecolor='blue', 
                shrink=0, 
                alpha=1,
                width=0.5))
ax.text(x[0] + 0.4, x[1] - 0.2, r'$x$', fontsize='16')


scalars = (-2, 2)
x = np.array(x)

for s in scalars:
    v = s * x
    ax.annotate('', xy=v, xytext=(0, 0), 
                arrowprops=dict(facecolor='red', 
                    shrink=0, 
                    alpha=0.5,
                    width=0.5))
    ax.text(v[0] + 0.4, v[1] - 0.2, r'${} x$'.format(s), fontsize='16')
plt.show()


########NEW FILE########
__FILENAME__ = wb_download
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: wb_download.py
Authors: John Stachurski, Tomohito Okabe
LastModified: 29/08/2013

Dowloads data from the World Bank site on GDP per capita and plots result for
a subset of countries.
"""
import pandas as pd
import matplotlib.pyplot as plt
from pandas.io.parsers import ExcelFile
import urllib

# == Get data and read into file gd.xls == #
wb_data_file_dir = "http://api.worldbank.org/datafiles/"
file_name = "GC.DOD.TOTL.GD.ZS_Indicator_MetaData_en_EXCEL.xls"
url = wb_data_file_dir + file_name
urllib.urlretrieve(url, "gd.xls")

# == Parse data into a DataFrame == #
gov_debt_xls = ExcelFile('gd.xls')
govt_debt = gov_debt_xls.parse('Sheet1', index_col=1, na_values=['NA'])

# == Take desired values and plot == #
govt_debt = govt_debt.transpose()
govt_debt = govt_debt[['AUS', 'DEU', 'FRA', 'USA']]
govt_debt = govt_debt[36:]
govt_debt.plot(lw=2)
plt.show()

########NEW FILE########
__FILENAME__ = web_network

import numpy as np
import matplotlib.pyplot as plt
import mc_tools
import re

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def gen_rw_mat(n):
    "Generate an n x n matrix of zeros and ones."
    Q = np.random.randn(n, n) - 0.8
    Q = np.where(Q > 0, 1, 0)
    # Make sure that no row contains only zeros
    for i in range(n):
        if Q[i,:].sum() == 0:
            Q[i,np.random.randint(0, n, 1)] = 1
    return Q

def adj_matrix_to_dot(Q, outfile='/tmp/foo_out.dot'):
    """
    Convert an adjacency matrix to a dot file.
    """
    n = Q.shape[0]
    f = open(outfile, 'w')
    f.write('digraph {\n')
    for i in range(n):
        for j in range(n):
            if Q[i, j]:
                f.write('   {0} -> {1};\n'.format(alphabet[i], alphabet[j]))
    f.write('}\n')
    f.close()

def dot_to_adj_matrix(node_num, infile='/tmp/foo_out.dot'):
    Q = np.zeros((node_num, node_num), dtype=int)
    f = open(infile, 'r')
    lines = f.readlines()
    f.close()
    edges = lines[1:-1]  # Drop first and last lines
    for edge in edges:
        from_node, to_node = re.findall('\w', edge)
        i, j = alphabet.index(from_node), alphabet.index(to_node)
        Q[i, j] = 1
    return Q

def adj_matrix_to_markov(Q):
    n = Q.shape[0]
    P = np.empty((n, n))
    for i in range(n):
        P[i,:] = Q[i,:] / float(Q[i,:].sum())
    return P



########NEW FILE########
__FILENAME__ = white_noise_plot
from pylab import plot, show, legend
from random import normalvariate

x = [normalvariate(0, 1) for i in range(100)]
plot(x, 'b-', label="white noise")
legend()
show()

########NEW FILE########
__FILENAME__ = yahoo_fin
"""
Filename: yahoo_fin.py
Authors: John Stachurski, Thomas J. Sargent

Compute returns on a certain portfolio since the start of the year, and plot
them from best to worst.
"""

from urllib import urlopen, urlencode
from datetime import date, timedelta
from operator import itemgetter

today = date.today()
base_url = 'http://ichart.finance.yahoo.com/table.csv'

def get_stock_price(request_date, ticker):
    """
    Get stock price corresponding to the date and ticker.  

    Parameters
    ===========

    request_date : datetime.date instance
        The desired day

    ticker : string
        The stock, such as 'AAPL'

    Returns
    ========

    The opening price as a float
    """
    
    previous_date = request_date - timedelta(days=1)

    dd1 = str(previous_date.day)
    mm1 = str(previous_date.month - 1)  
    yr1 = str(previous_date.year)  

    dd2 = str(request_date.day)
    mm2 = str(request_date.month - 1)  
    yr2 = str(request_date.year)  

    request_data = {'a': mm1,            # Start month, base zero
                    'b': dd1,            # Start day
                    'c': yr1,            # Start year
                    'd': mm2,            # End month, base zero
                    'e': dd2,            # End day
                    'f': yr2,            # End year
                    'g': 'd',            # Daily data
                    's': ticker,         # Ticker name
                    'ignore': '.csv'}    # Data type

    url = base_url + '?' + urlencode(request_data)
    response = urlopen(url)
    response.next()                 # Skip the first line
    prices = response.next()        
    price = prices.split(',')[1]    # Opening price
    return float(price)

# Find the first Monday of the current year
first_weekday = date(today.year, 1, 1)  # Start at 1st of Jan
while first_weekday.weekday() > 4:      # 5 and 6 correspond to the weekend
    first_weekday += timedelta(days=1)  # Increment date by one day

# Find the most recent weekday, starting yesterday
most_recent_weekday = today - timedelta(days=1)
while most_recent_weekday.weekday() > 4:       # If it's the weekend
    most_recent_weekday -= timedelta(days=1)   # Go back one day

portfolio = open('examples/portfolio.txt')  
percent_change = {}
for line in portfolio:
    ticker, company_name = [item.strip() for item in line.split(',')]
    old_price = get_stock_price(first_weekday, ticker)
    new_price = get_stock_price(most_recent_weekday, ticker)
    percent_change[company_name] = 100 * (new_price - old_price) / old_price
portfolio.close()

items = percent_change.items()

for name, change in sorted(items, key=itemgetter(1), reverse=True):
    print '%-12s %10.2f' % (name, change)

########NEW FILE########
__FILENAME__ = asset_pricing
"""
Filename: asset_pricing.py
Authors: David Evans, John Stachurski and Thomas J. Sargent

Computes asset prices in an endowment economy when the endowment obeys
geometric growth driven by a finite state Markov chain.  The transition matrix
of the Markov chain is P, and the set of states is s.  The discount
factor is beta, and gamma is the coefficient of relative risk aversion in the
household's utility function.
"""

import numpy as np
from numpy.linalg import solve

class AssetPrices:

    def __init__(self, beta, P, s, gamma):
        '''
        Initializes an instance of AssetPrices

        Parameters
        ==========
        beta : float
            discount factor 

        P : array_like
            transition matrix 
            
        s : array_like
            growth rate of consumption 

        gamma : float
            coefficient of risk aversion 
        '''
        self.beta, self.gamma = beta, gamma
        self.P, self.s = [np.atleast_2d(x) for x in P, s]
        self.n = self.P.shape[0]
        self.s.shape = self.n, 1

    def tree_price(self):
        '''
        Computes the function v such that the price of the lucas tree is
        v(lambda)C_t
        '''
        # == Simplify names == #
        P, s, gamma, beta = self.P, self.s, self.gamma, self.beta
        # == Compute v == #
        P_tilde = P * s**(1-gamma) #using broadcasting
        I = np.identity(self.n)
        O = np.ones(self.n)
        v = beta * solve(I - beta * P_tilde, P_tilde.dot(O))
        return v
        
    def consol_price(self, zeta):
        '''
        Computes price of a consol bond with payoff zeta

        Parameters
        ===========
        zeta : float
            coupon of the console

        '''
        # == Simplify names == #
        P, s, gamma, beta = self.P, self.s, self.gamma, self.beta
        # == Compute price == #
        P_check = P * s**(-gamma)
        I = np.identity(self.n)
        O = np.ones(self.n)
        p_bar = beta * solve(I - beta * P_check, P_check.dot(zeta * O))
        return p_bar
        
    def call_option(self, zeta, p_s, T=[], epsilon=1e-8):
        '''
        Computes price of a call option on a consol bond with payoff zeta

        Parameters
        ===========
        zeta : float
            coupon of the console

        p_s : float
            strike price 

        T : list of integers 
            length of option 

        epsilon : float
            tolerance for infinite horizon problem
        '''
        # == Simplify names, initialize variables == #
        P, s, gamma, beta = self.P, self.s, self.gamma, self.beta
        P_check = P * s**(-gamma)
        # == Compute consol price == #
        v_bar = self.consol_price(zeta)
        # == Compute option price == #
        w_bar = np.zeros(self.n)
        error = epsilon + 1
        t = 0
        w_bars = {}
        while error > epsilon:
            if t in T:
                w_bars[t] = w_bar
            # == Maximize across columns == #
            to_stack = (beta*P_check.dot(w_bar), v_bar-p_s)
            w_bar_new = np.amax(np.vstack(to_stack), axis = 0 ) 
            # == Find maximal difference of each component == #
            error = np.amax(np.abs(w_bar-w_bar_new)) 
            # == Update == #
            w_bar = w_bar_new
            t += 1
        
        return w_bar, w_bars

########NEW FILE########
__FILENAME__ = career
"""
Filename: career.py
Authors: Thomas Sargent, John Stachurski 

A collection of functions to solve the career / job choice model of Neal.
"""

import numpy as np
from scipy.special import binom, beta


def gen_probs(n, a, b):
    """
    Generate and return the vector of probabilities for the Beta-binomial 
    (n, a, b) distribution.
    """
    probs = np.zeros(n+1)
    for k in range(n+1):
        probs[k] = binom(n, k) * beta(k + a, n - k + b) / beta(a, b)
    return probs


class workerProblem:

    def __init__(self, B=5.0, beta=0.95, N=50, F_a=1, F_b=1, G_a=1, G_b=1):
        self.beta, self.N, self.B = beta, N, B
        self.theta = np.linspace(0, B, N)     # set of theta values
        self.epsilon = np.linspace(0, B, N)   # set of epsilon values
        self.F_probs = gen_probs(N-1, F_a, F_b)
        self.G_probs = gen_probs(N-1, G_a, G_b)
        self.F_mean = np.sum(self.theta * self.F_probs)
        self.G_mean = np.sum(self.epsilon * self.G_probs)

def bellman(w, v):
    """
    The Bellman operator.  
    
        * w is an instance of workerProblem
        * v is a 2D NumPy array representing the value function
        
    The array v should be interpreted as v[i, j] = v(theta_i, epsilon_j).  
    Returns the updated value function Tv as an array of shape v.shape
    """
    new_v = np.empty(v.shape)
    for i in range(w.N):
        for j in range(w.N):
            v1 = w.theta[i] + w.epsilon[j] + w.beta * v[i, j]
            v2 = w.theta[i] + w.G_mean + w.beta * np.dot(v[i, :], w.G_probs)
            v3 = w.G_mean + w.F_mean + w.beta * \
                    np.dot(w.F_probs, np.dot(v, w.G_probs))
            new_v[i, j] = max(v1, v2, v3)
    return new_v

def get_greedy(w, v):
    """
    Compute optimal actions taking v as the value function.  Parameters are
    the same as for bellman().  Returns a 2D NumPy array "policy", where
    policy[i, j] is the optimal action at state (theta_i, epsilon_j).  The
    optimal action is represented as an integer in the set 1, 2, 3, where 1 =
    'stay put', 2 = 'new job' and 3 = 'new life'
    """
    policy = np.empty(v.shape, dtype=int)
    for i in range(w.N):
        for j in range(w.N):
            v1 = w.theta[i] + w.epsilon[j] + w.beta * v[i, j]
            v2 = w.theta[i] + w.G_mean + w.beta * np.dot(v[i, :], w.G_probs)
            v3 = w.G_mean + w.F_mean + w.beta * \
                    np.dot(w.F_probs, np.dot(v, w.G_probs))
            if v1 > max(v2, v3):
                action = 1  
            elif v2 > max(v1, v3):
                action = 2
            else:
                action = 3
            policy[i, j] = action
    return policy

########NEW FILE########
__FILENAME__ = compute_fp
"""
Filename: compute_fp.py
Authors: Thomas Sargent, John Stachurski 

Compute the fixed point of a given operator T, starting from 
specified initial condition v.
"""

import numpy as np

def compute_fixed_point(T, specs, v, error_tol=1e-3, max_iter=50, verbose=1):
    """
    Computes and returns T^k v, where T is an operator, v is an initial
    condition and k is the number of iterates. Provided that T is a
    contraction mapping or similar, T^k v will be an approximation to the
    fixed point.

    The convention for using this function is that T can be called as 
    
        new_v = T(specs, v).

    """
    iterate = 0 
    error = error_tol + 1
    while iterate < max_iter and error > error_tol:
        new_v = T(specs, v)
        iterate += 1
        error = np.max(np.abs(new_v - v))
        if verbose:
            print "Computed iterate %d with error %f" % (iterate, error)
        v = new_v
    return v


########NEW FILE########
__FILENAME__ = discrete_rv
"""
Filename: discrete_rv.py
Authors: Thomas Sargent, John Stachurski 

Generates an array of draws from a discrete random variable with a specified
vector of probabilities.
"""

from numpy import cumsum
from numpy.random import uniform

class discreteRV(object):
    """
    Generates an array of draws from a discrete random variable with vector of
    probabilities given by q.  
    """

    def __init__(self, q):
        """
        The argument q is a NumPy array, or array like, nonnegative and sums
        to 1
        """
        self._q = q
        self.Q = cumsum(q)

    def get_q(self):
        return self._q

    def set_q(self, val):
        self._q = val
        self.Q = cumsum(val)

    q = property(get_q, set_q)

    def draw(self, k=1):
        """
        Returns k draws from q. For each such draw, the value i is returned
        with probability q[i].  
        """
        return self.Q.searchsorted(uniform(0, 1, size=k)) 



########NEW FILE########
__FILENAME__ = ecdf
"""
Filename: ecdf.py
Authors: Thomas Sargent, John Stachurski 

Implements the empirical cumulative distribution function given an array of
observations.
"""

import numpy as np
import matplotlib.pyplot as plt

class ecdf:

    def __init__(self, observations):
        self.observations = np.asarray(observations)

    def __call__(self, x): 
        return np.mean(self.observations <= x)

    def plot(self, a=None, b=None): 

        # === choose reasonable interval if [a, b] not specified === #
        if not a:
            a = self.observations.min() - self.observations.std()
        if not b:
            b = self.observations.max() + self.observations.std()

        # === generate plot === #
        x_vals = np.linspace(a, b, num=100)
        f = np.vectorize(self.__call__)
        plt.plot(x_vals, f(x_vals))
        plt.show()


########NEW FILE########
__FILENAME__ = estspec
"""
Filename: estspec.py
Authors: Thomas Sargent, John Stachurski 

Functions for working with periodograms of scalar data.
"""

from __future__ import division, print_function  # Omit for Python 3.x
import numpy as np
from numpy.fft import fft
from pandas import ols, Series

def smooth(x, window_len=7, window='hanning'):
    """
    Smooth the data in x using convolution with a window of requested size
    and type.

    Parameters:

        * x is a flat NumPy array --- the data to smooth

        * window_len is an odd integer --- the length of the window

        * window is a string giving the window type 
          ('flat', 'hanning', 'hamming', 'bartlett' or 'blackman')

    Application of the smoothing window at the top and bottom of x is done by
    reflecting x around these points to extend it sufficiently in each
    direction.

    """
    if len(x) < window_len:
        raise ValueError, "Input vector length must be at least window length."

    if window_len < 3:
        raise ValueError, "Window length must be at least 3."

    if not window_len % 2:  # window_len is even
        window_len +=1
        print("Window length reset to {}".format(window_len))

    windows = {'hanning': np.hanning,
               'hamming': np.hamming, 
               'bartlett': np.bartlett,
               'blackman': np.blackman}

    # === reflect x around x[0] and x[-1] prior to convolution === #
    k = int(window_len / 2)
    xb = x[:k]   # First k elements
    xt = x[-k:]  # Last k elements
    s = np.concatenate((xb[::-1], x, xt[::-1]))
    
    # === select window values === #
    if window == 'flat':  
        w = np.ones(window_len)  # moving average
    else:
        try:
            w = windows[window](window_len)
        except KeyError:
            print("Unrecognized window type.  Defaulting to 'hanning'.")
            w = windows['hanning'](window_len)

    return np.convolve(w / w.sum(), s, mode='valid')


def periodogram(x, window=None, window_len=7):
    """
    Computes the periodogram 

        I(w) = (1 / n) | sum_{t=0}^{n-1} x_t e^{itw} |^2

    at the Fourier frequences w_j := 2 pi j / n, j = 0, ..., n - 1, using the
    fast Fourier transform.  Only the frequences w_j in [0, pi] and
    corresponding values I(w_j) are returned.  If a window type is given then
    smoothing is performed.

        * x is a flat NumPy array --- the time series data

        * window is a string giving the window type 
          ('flat', 'hanning', 'hamming', 'bartlett' or 'blackman')

        * window_len is an odd integer --- the length of the window

    """
    n = len(x)
    I_w = np.abs(fft(x))**2 / n
    w = 2 * np.pi * np.arange(n) / n
    w, I_w = w[:int(n/2)+1], I_w[:int(n/2)+1]  # Take only values on [0, pi]
    if window:
        I_w = smooth(I_w, window_len=window_len, window=window)
    return w, I_w


def ar_periodogram(x, window='hanning', window_len=7):
    """
    Compute periodogram from data x, using prewhitening, smoothing and
    recoloring.  The data is fitted to an AR(1) model for prewhitening,
    and the residuals are used to compute a first-pass periodogram with
    smoothing.  The fitted coefficients are then used for recoloring.

    Parameters:

        * x is a NumPy array containing time series data
        * window is a string indicating window type 
        * window_len is an odd integer

    See the periodogram function documentation for more details on the window
    arguments.
    """              
    # === run regression === #
    x_current, x_lagged = x[1:], x[:-1]                       # x_t and x_{t-1}
    x_current, x_lagged = Series(x_current), Series(x_lagged) # pandas series
    results = ols(y=x_current, x=x_lagged, intercept=True, nw_lags=1)
    e_hat = results.resid.values
    phi = results.beta['x']

    # === compute periodogram on residuals === #
    w, I_w = periodogram(e_hat, window=window, window_len=window_len) 

    # === recolor and return === #
    I_w = I_w  / np.abs(1 - phi * np.exp(1j * w))**2  
    return w, I_w

########NEW FILE########
__FILENAME__ = ifp
"""
Filename: ifp.py
Authors: Thomas Sargent, John Stachurski 

Functions for solving the income fluctuation problem. Iteration with either
the Coleman or Bellman operators from appropriate initial conditions leads to
convergence to the optimal consumption policy.  The income process is a finite
state Markov chain.  Note that the Coleman operator is the preferred method,
as it is almost always faster and more accurate.  The Bellman operator is only
provided for comparison.

"""

import numpy as np
from scipy.optimize import fminbound, brentq
from scipy import interp

class consumerProblem:
    """
    This class is just a "struct" to hold the collection of parameters
    defining the consumer problem.  
    """

    def __init__(self, 
            r=0.01, 
            beta=0.96, 
            Pi=((0.6, 0.4), (0.05, 0.95)), 
            z_vals=(0.5, 1.0), 
            b=0, 
            grid_max=16, 
            grid_size=50,
            u=np.log, 
            du=lambda x: 1/x):
        """
        Parameters:

            * r and beta are scalars with r > 0 and (1 + r) * beta < 1
            * Pi is a 2D NumPy array --- the Markov matrix for {z_t}
            * z_vals is an array/list containing the state space of {z_t}
            * u is the utility function and du is the derivative
            * b is the borrowing constraint
            * grid_max and grid_size describe the grid used in the solution

        """
        self.u, self.du = u, du
        self.r, self.R = r, 1 + r
        self.beta, self.b = beta, b
        self.Pi, self.z_vals = np.array(Pi), tuple(z_vals)
        self.asset_grid = np.linspace(-b, grid_max, grid_size)


def bellman_operator(cp, V, return_policy=False):
    """
    The approximate Bellman operator, which computes and returns the updated
    value function TV (or the V-greedy policy c if return_policy == True).

    Parameters:

        * cp is an instance of class consumerProblem
        * V is a NumPy array of dimension len(cp.asset_grid) x len(cp.z_vals)

    """
    # === simplify names, set up arrays === #
    R, Pi, beta, u, b = cp.R, cp.Pi, cp.beta, cp.u, cp.b  
    asset_grid, z_vals = cp.asset_grid, cp.z_vals        
    new_V = np.empty(V.shape)
    new_c = np.empty(V.shape)
    z_index = range(len(z_vals))  

    # === linear interpolation of V along the asset grid === #
    vf = lambda a, i_z: interp(a, asset_grid, V[:, i_z]) 

    # === solve r.h.s. of Bellman equation === #
    for i_a, a in enumerate(asset_grid):
        for i_z, z in enumerate(z_vals):
            def obj(c):  # objective function to be *minimized*
                y = sum(vf(R * a + z - c, j) * Pi[i_z, j] for j in z_index)
                return - u(c) - beta * y
            c_star = fminbound(obj, np.min(z_vals), R * a + z + b)
            new_c[i_a, i_z], new_V[i_a, i_z] = c_star, -obj(c_star)

    if return_policy:
        return new_c
    else:
        return new_V


def coleman_operator(cp, c):
    """
    The approximate Coleman operator.  Iteration with this operator
    corresponds to policy function iteration.  Computes and returns the
    updated consumption policy c.

    Parameters:

        * cp is an instance of class consumerProblem
        * c is a NumPy array of dimension len(cp.asset_grid) x len(cp.z_vals)

    The array c is replaced with a function cf that implements univariate
    linear interpolation over the asset grid for each possible value of z.
    """
    # === simplify names, set up arrays === #
    R, Pi, beta, du, b = cp.R, cp.Pi, cp.beta, cp.du, cp.b  
    asset_grid, z_vals = cp.asset_grid, cp.z_vals          
    z_size = len(z_vals)
    gamma = R * beta
    vals = np.empty(z_size)  

    # === linear interpolation to get consumption function === #
    def cf(a):
        """
        The call cf(a) returns an array containing the values c(a, z) for each
        z in z_vals.  For each such z, the value c(a, z) is constructed by
        univariate linear approximation over asset space, based on the values
        in the array c
        """
        for i in range(z_size):
            vals[i] = interp(a, cp.asset_grid, c[:, i])
        return vals

    # === solve for root to get Kc === #
    Kc = np.empty(c.shape)
    for i_a, a in enumerate(asset_grid):
        for i_z, z in enumerate(z_vals):
            def h(t):
                expectation = np.dot(du(cf(R * a + z - t)), Pi[i_z, :])
                return du(t) - max(gamma * expectation, du(R * a + z + b))
            Kc[i_a, i_z] = brentq(h, np.min(z_vals), R * a + z + b)

    return Kc

def initialize(cp):
    """
    Creates a suitable initial conditions V and c for value function and
    policy function iteration respectively.

        * cp is an instance of class consumerProblem.

    """
    # === simplify names, set up arrays === #
    R, beta, u, b = cp.R, cp.beta, cp.u, cp.b             
    asset_grid, z_vals = cp.asset_grid, cp.z_vals        
    shape = len(asset_grid), len(z_vals)         
    V, c = np.empty(shape), np.empty(shape)

    # === populate V and c === #
    for i_a, a in enumerate(asset_grid):
        for i_z, z in enumerate(z_vals):
            c_max = R * a + z + b
            c[i_a, i_z] = c_max
            V[i_a, i_z] = u(c_max) / (1 - beta)
    return V, c



########NEW FILE########
__FILENAME__ = jv
"""
Filename: jv.py
Authors: Thomas Sargent, John Stachurski 

A Jovanovic-type model of employment with on-the-job search. The value
function is given by

  V(x) = max_{phi, s} w(x, phi, s)

  for w(x, phi, s) := x(1 - phi - s) 
                        + beta (1 - pi(s)) V(G(x, phi)) 
                        + beta pi(s) E V[ max(G(x, phi), U)]
Here

    * x = human capital
    * s = search effort
    * phi = investment in human capital 
    * pi(s) = probability of new offer given search level s
    * x(1 - phi - s) = wage
    * G(x, phi) = updated human capital when current job retained
    * U = a random variable with distribution F -- new draw of human capital

"""

import numpy as np
from scipy.integrate import fixed_quad as integrate
from scipy.optimize import fmin_slsqp as minimize
import scipy.stats as stats
from scipy import interp

epsilon = 1e-4  #  A small number, used in the optimization routine

class workerProblem:

    def __init__(self, A=1.4, alpha=0.6, beta=0.96, grid_size=50):
        """
        This class is just a "struct" to hold the attributes of a given model.
        """
        self.A, self.alpha, self.beta = A, alpha, beta
        # === set defaults for G, pi and F === #
        self.G = lambda x, phi: A * (x * phi)**alpha 
        self.pi = np.sqrt 
        self.F = stats.beta(2, 2)  
        # === Set up grid over the state space for DP === #
        # Max of grid is the max of a large quantile value for F and the 
        # fixed point y = G(y, 1).
        grid_max = max(A**(1 / (1 - alpha)), self.F.ppf(1 - epsilon))
        self.x_grid = np.linspace(epsilon, grid_max, grid_size)


def bellman_operator(wp, V, brute_force=False, return_policies=False):
    """
    Parameter wp is an instance of workerProblem.  Thus function returns the
    approximate value function TV by applying the Bellman operator associated
    with the model wp to the function V.  Returns TV, or the V-greedy policies
    s_policy and phi_policy when return_policies=True.

    In the function, the array V is replaced below with a function Vf that
    implements linear interpolation over the points (V(x), x) for x in x_grid.
    If the brute_force flag is true, then grid search is performed at each
    maximization step.  In either case, T returns a NumPy array representing
    the updated values TV(x) over x in x_grid.

    """
    # === simplify names, set up arrays, etc. === #
    G, pi, F, beta = wp.G, wp.pi, wp.F, wp.beta  
    Vf = lambda x: interp(x, wp.x_grid, V) 
    N = len(wp.x_grid)
    new_V, s_policy, phi_policy = np.empty(N), np.empty(N), np.empty(N)
    a, b = F.ppf(0.005), F.ppf(0.995)  # Quantiles, for integration
    c1 = lambda z: 1 - sum(z)          # used to enforce s + phi <= 1
    c2 = lambda z: z[0] - epsilon      # used to enforce s >= epsilon
    c3 = lambda z: z[1] - epsilon      # used to enforce phi >= epsilon
    guess, constraints = (0.2, 0.2), [c1, c2, c3]

    # === solve r.h.s. of Bellman equation === #
    for i, x in enumerate(wp.x_grid):

        # === set up objective function === #
        def w(z):  
            s, phi = z
            integrand = lambda u: Vf(np.maximum(G(x, phi), u)) * F.pdf(u)
            integral, err = integrate(integrand, a, b)
            q = pi(s) * integral + (1 - pi(s)) * Vf(G(x, phi))
            return - x * (1 - phi - s) - beta * q  # minus because we minimize

        # === either use SciPy solver === #
        if not brute_force:  
            max_s, max_phi = minimize(w, guess, ieqcons=constraints, disp=0)
            max_val = -w((max_s, max_phi))

        # === or search on a grid === #
        else:  
            search_grid = np.linspace(epsilon, 1, 15)
            max_val = -1
            for s in search_grid:
                for phi in search_grid:
                    current_val = -w((s, phi)) if s + phi <= 1 else -1
                    if current_val > max_val:
                        max_val, max_s, max_phi = current_val, s, phi

        # === store results === #
        new_V[i] = max_val
        s_policy[i], phi_policy[i] = max_s, max_phi

    if return_policies:
        return s_policy, phi_policy
    else:
        return new_V



########NEW FILE########
__FILENAME__ = kalman
"""
Filename: kalman.py
Authors: Thomas Sargent, John Stachurski 

Implements the Kalman filter for the state space model

    x_{t+1} = A x_t + w_{t+1}
    y_t = G x_t + v_t.

Here x_t is the hidden state and y_t is the measurement.  The shocks {w_t} 
and {v_t} are iid zero mean Gaussians with covariance matrices Q and R
respectively.
"""

import numpy as np
from numpy import dot
from scipy.linalg import inv
import riccati

class Kalman:

    def __init__(self, A, G, Q, R):
        """
        Provides initial parameters describing the state space model

            x_{t+1} = A x_t + w_{t+1}       (w_t ~ N(0, Q))

            y_t = G x_t + v_t               (v_t ~ N(0, R))
        
        Parameters
        ============
        
        All arguments should be scalars or array_like

            * A is n x n
            * Q is n x n, symmetric and nonnegative definite
            * G is k x n
            * R is k x k, symmetric and nonnegative definite

        """
        self.A, self.G, self.Q, self.R = map(self.convert, (A, G, Q, R))
        self.k, self.n = self.G.shape

    def convert(self, x): 
        """
        Convert array_like objects (lists of lists, floats, etc.) into well
        formed 2D NumPy arrays
        """
        return np.atleast_2d(np.asarray(x, dtype='float32'))

    def set_state(self, x_hat, Sigma):
        """
        Set the state, which is the mean x_hat and covariance matrix Sigma of
        the prior/predictive density.  

            * x_hat is n x 1
            * Sigma is n x n and positive definite

        Must be Python scalars or NumPy arrays.
        """
        self.current_Sigma = self.convert(Sigma)
        self.current_x_hat = self.convert(x_hat)
        self.current_x_hat.shape = self.n, 1

    def prior_to_filtered(self, y):
        """
        Updates the moments (x_hat, Sigma) of the time t prior to the time t
        filtering distribution, using current measurement y_t.  The parameter
        y should be a Python scalar or NumPy array.  The updates are according
        to 

            x_hat^F = x_hat + Sigma G' (G Sigma G' + R)^{-1}(y - G x_hat)
            Sigma^F = Sigma - Sigma G' (G Sigma G' + R)^{-1} G Sigma

        """
        # === simplify notation === #
        G, R = self.G, self.R
        x_hat, Sigma = self.current_x_hat, self.current_Sigma

        # === and then update === #
        y = self.convert(y)
        y.shape = self.k, 1
        A = dot(Sigma, G.T)
        B = dot(dot(G, Sigma), G.T) + R
        M = dot(A, inv(B))
        self.current_x_hat = x_hat + dot(M, (y - dot(G, x_hat)))
        self.current_Sigma = Sigma  - dot(M, dot(G,  Sigma))

    def filtered_to_forecast(self):
        """
        Updates the moments of the time t filtering distribution to the
        moments of the predictive distribution -- which becomes the time t+1
        prior
        """
        # === simplify notation === #
        A, Q = self.A, self.Q
        x_hat, Sigma = self.current_x_hat, self.current_Sigma

        # === and then update === #
        self.current_x_hat = dot(A, x_hat)
        self.current_Sigma = dot(A, dot(Sigma, A.T)) + Q

    def update(self, y):
        """
        Updates x_hat and Sigma given k x 1 ndarray y.  The full update, from
        one period to the next
        """
        self.prior_to_filtered(y)
        self.filtered_to_forecast()

    def stationary_values(self):
        """
        Computes the limit of Sigma_t as t goes to infinity by solving the
        associated Riccati equation.  Computation is via the doubling
        algorithm (see the documentation in riccati.dare).  Returns the limit
        and the stationary Kalman gain.
        """
        # === simplify notation === #
        A, Q, G, R = self.A, self.Q, self.G, self.R
        # === solve Riccati equation, obtain Kalman gain === #
        Sigma_infinity = riccati.dare(A.T, G.T, R, Q)
        temp1 = dot(dot(A, Sigma_infinity), G.T)
        temp2 = inv(dot(G, dot(Sigma_infinity, G.T)) + R)
        K_infinity = dot(temp1, temp2)
        return Sigma_infinity, K_infinity

########NEW FILE########
__FILENAME__ = lae
"""
Filename: lae.py
Authors: Thomas J. Sargent, John Stachurski,

Computes a sequence of marginal densities for a continuous state space Markov
chain {X_t} where the transition probabilities can be represented as densities.
The estimate of the marginal density psi_t of X_t is

    (1/n) sum_{i=0}^n p(X_{t-1}^i, y)

This is a density in y.  

"""

import numpy as np

class LAE:
    """
    An instance is a representation of a look ahead estimator associated with
    a given stochastic kernel p and a vector of observations X.  For example,

        >>> psi = LAE(p, X)
        >>> y = np.linspace(0, 1, 100)
        >>> psi(y)  # Evaluate look ahead estimate at grid of points y
    """

    def __init__(self, p, X):
        """
        Parameters
        ==========
        p : function
            The stochastic kernel.  A function p(x, y) that is vectorized in
            both x and y

        X : array_like
            A vector containing observations
        """
        X = X.flatten()  # So we know what we're dealing with
        n = len(X)
        self.p, self.X = p, X.reshape((n, 1))


    def __call__(self, y):
        """
        Parameters
        ==========
        y : array_like
            A vector of points at which we wish to evaluate the look-ahead
            estimator

        Returns
        =======
        psi_vals : numpy.ndarray
            The values of the density estimate at the points in y

        """
        k = len(y)
        v = self.p(self.X, y.reshape((1, k)))
        psi_vals = np.mean(v, axis=0)    # Take mean along each row
        return psi_vals.flatten()



########NEW FILE########
__FILENAME__ = linproc
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: linproc.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013
"""
import numpy as np
from numpy import conj, pi, real
import matplotlib.pyplot as plt
from scipy.signal import dimpulse, freqz, dlsim


class linearProcess(object):
    """
    This class provides functions for working with scalar ARMA processes.  In
    particular, it defines methods for computing and plotting the
    autocovariance function, the spectral density, the impulse-response
    function and simulated time series.

    """
    
    def __init__(self, phi, theta=0, sigma=1) :
        """
        This class represents scalar ARMA(p, q) processes.  The parameters phi
        and theta can be NumPy arrays, array-like sequences (lists, tuples) or
        scalars.

        If phi and theta are scalars, then the model is
        understood to be 
        
            X_t = phi X_{t-1} + epsilon_t + theta epsilon_{t-1}  
            
        where {epsilon_t} is a white noise process with standard deviation
        sigma.  If phi and theta are arrays or sequences, then the
        interpretation is the ARMA(p, q) model 

            X_t = phi_1 X_{t-1} + ... + phi_p X_{t-p} + 
                epsilon_t + theta_1 epsilon_{t-1} + ... + theta_q epsilon_{t-q}

        where

            * phi = (phi_1, phi_2,..., phi_p)
            * theta = (theta_1, theta_2,..., theta_q)
            * sigma is a scalar, the standard deviation of the white noise

        """
        self._phi, self._theta = phi, theta
        self.sigma = sigma
        self.set_params()  

    def get_phi(self):
        return self._phi

    def get_theta(self):
        return self._theta

    def set_phi(self, new_value):
        self._phi = new_value
        self.set_params()

    def set_theta(self, new_value):
        self._theta = new_value
        self.set_params()

    phi = property(get_phi, set_phi)
    theta = property(get_theta, set_theta)

    def set_params(self):
        """
        Internally, scipy.signal works with systems of the form 
        
            ar_poly(L) X_t = ma_poly(L) epsilon_t 

        where L is the lag operator. To match this, we set
        
            ar_poly = (1, -phi_1, -phi_2,..., -phi_p)
            ma_poly = (1, theta_1, theta_2,..., theta_q) 
            
        In addition, ar_poly must be at least as long as ma_poly.  This can be
        achieved by padding it out with zeros when required.
        """
        # === set up ma_poly === #
        ma_poly = np.asarray(self._theta)
        self.ma_poly = np.insert(ma_poly, 0, 1)      # The array (1, theta)

        # === set up ar_poly === #
        if np.isscalar(self._phi):
            ar_poly = np.array(-self._phi)
        else:
            ar_poly = -np.asarray(self._phi)
        self.ar_poly = np.insert(ar_poly, 0, 1)      # The array (1, -phi)

        # === pad ar_poly with zeros if required === #
        if len(self.ar_poly) < len(self.ma_poly):    
            temp = np.zeros(len(self.ma_poly) - len(self.ar_poly))
            self.ar_poly = np.hstack((self.ar_poly, temp))
        
    def impulse_response(self, impulse_length=30):
        """
        Get the impulse response corresponding to our model.  Returns psi,
        where psi[j] is the response at lag j.  Note: psi[0] is unity.
        """        
        sys = self.ma_poly, self.ar_poly, 1 
        times, psi = dimpulse(sys, n=impulse_length)
        psi = psi[0].flatten()  # Simplify return value into flat array
        return psi

    def spectral_density(self, two_pi=True, resolution=1200) :
        """
        Compute the spectral density function over [0, pi] if two_pi is False
        and [0, 2 pi] otherwise.  The spectral density is the discrete time
        Fourier transform of the autocovariance function.  In particular,

            f(w) = sum_k gamma(k) exp(-ikw)

        where gamma is the autocovariance function and the sum is over the set
        of all integers.
        """       
        w, h = freqz(self.ma_poly, self.ar_poly, worN=resolution, whole=two_pi)
        spect = h * conj(h) * self.sigma**2 
        return w, spect

    def autocovariance(self, num_autocov=16) :
        """
        Compute the autocovariance function over the integers
        range(num_autocov) using the spectral density and the inverse Fourier
        transform.
        """
        spect = self.spectral_density()[1]
        acov = np.fft.ifft(spect).real
        return acov[:num_autocov]  # num_autocov should be <= len(acov) / 2

    def simulation(self, ts_length=90) :
        " Compute a simulated sample path. "        
        sys = self.ma_poly, self.ar_poly, 1
        u = np.random.randn(ts_length, 1)
        vals = dlsim(sys, u)[1]
        return vals.flatten()

    def plot_impulse_response(self, ax=None, show=True):
        if show:
            fig, ax = plt.subplots()
        ax.set_title('Impulse response')
        yi = self.impulse_response()
        ax.stem(range(len(yi)), yi)
        ax.set_xlim(xmin=(-0.5))
        ax.set_ylim(min(yi)-0.1,max(yi)+0.1)
        ax.set_xlabel('time')
        ax.set_ylabel('response')
        if show:
            plt.show()

    def plot_spectral_density(self, ax=None, show=True):
        if show:
            fig, ax = plt.subplots()
        ax.set_title('Spectral density')
        w, spect = self.spectral_density(two_pi=False)  
        ax.semilogy(w, spect)
        ax.set_xlim(0, pi)
        ax.set_ylim(0, np.max(spect))
        ax.set_xlabel('frequency')
        ax.set_ylabel('spectrum')
        if show:
            plt.show()

    def plot_autocovariance(self, ax=None, show=True):
        if show:
            fig, ax = plt.subplots()
        ax.set_title('Autocovariance')
        acov = self.autocovariance() 
        ax.stem(range(len(acov)), acov)
        ax.set_xlim(-0.5, len(acov) - 0.5)
        ax.set_xlabel('time')
        ax.set_ylabel('autocovariance')     
        if show:
            plt.show()

    def plot_simulation(self, ax=None, show=True):
        if show:
            fig, ax = plt.subplots()
        ax.set_title('Sample path')    
        x_out = self.simulation() 
        ax.plot(x_out)
        ax.set_xlabel('time')
        ax.set_ylabel('state space')
        if show:
            plt.show()

    def quad_plot(self) :
        """
        Plots the impulse response, spectral_density, autocovariance, and one
        realization of the process.
        """
        num_rows, num_cols = 2, 2
        fig, axes = plt.subplots(num_rows, num_cols, figsize=(12, 8))
        plt.subplots_adjust(hspace=0.4)
        self.plot_impulse_response(axes[0, 0], show=False)
        self.plot_spectral_density(axes[0, 1], show=False)
        self.plot_autocovariance(axes[1, 0], show=False)
        self.plot_simulation(axes[1, 1], show=False)
        plt.show()



########NEW FILE########
__FILENAME__ = lqcontrol
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: lqcontrol.py
Authors: John Stachurski and Thomas J. Sargent
LastModified: 12/09/2013

Solves LQ control problems.
"""

import numpy as np
from numpy import dot
from scipy.linalg import solve
import riccati

class LQ:
    """
    This class is for analyzing linear quadratic optimal control problems of
    either the infinite horizon form 

        min E sum_{t=0}^{infty} beta^t r(x_t, u_t)
        
    with 
    
        r(x_t, u_t) := x_t' R x_t + u_t' Q u_t 

    or the finite horizon form 

    min E sum_{t=0}^{T-1} beta^t r(x_t, u_t) + x_T' R_f x_T

    Both are minimized subject to the law of motion

        x_{t+1} = A x_t + B u_t + C w_{t+1}

    Here x is n x 1, u is k x 1, w is j x 1 and the matrices are conformable
    for these dimensions.  The sequence {w_t} is assumed to be white noise,
    with zero mean and E w_t w_t' = I, the j x j identity.

    If C is not supplied as a parameter, the model is assumed to be
    deterministic (and C is set to a zero matrix of appropriate dimension).

    For this model, the time t value (i.e., cost-to-go) function V_t takes the
    form

        x' P_T x + d_T

    and the optimal policy is of the form u_T = -F_T x_T.  In the infinite
    horizon case, V, P, d and F are all stationary.
    """

    def __init__(self, Q, R, A, B, C=None, beta=1, T=None, Rf=None):
        """
        Provides parameters describing the LQ model
        
        Parameters
        ============
        
            * R and Rf are n x n, symmetric and nonnegative definite
            * Q is k x k, symmetric and positive definite
            * A is n x n
            * B is n x k
            * C is n x j, or None for a deterministic model
            * beta is a scalar in (0, 1] and T is an int

        All arguments should be scalars or NumPy ndarrays.

        Here T is the time horizon. If T is not supplied, then the LQ problem
        is assumed to be infinite horizon.  If T is supplied, then the
        terminal reward matrix Rf should also be specified.  For
        interpretation of the other parameters, see the docstring of the LQ
        class.

        We also initialize the pair (P, d) that represents the value function
        via V(x) = x' P x + d, and the policy function matrix F.
        """
        # == Make sure all matrices can be treated as 2D arrays == #
        converter = lambda X: np.atleast_2d(np.asarray(X, dtype='float32'))
        self.A, self.B, self.Q, self.R = map(converter, (A, B, Q, R))
        # == Record dimensions == #
        self.k, self.n = self.Q.shape[0], self.R.shape[0]

        self.beta = beta

        if C == None:
            # == If C not given, then model is deterministic. Set C=0. == #
            self.j = 1
            self.C = np.zeros((self.n, self.j))
        else:
            self.C = converter(C)
            self.j = self.C.shape[1]

        if T:
            # == Model is finite horizon == #
            self.T = T
            self.Rf = np.asarray(Rf, dtype='float32')
            self.P = self.Rf
            self.d = 0
        else:
            self.P = None
            self.d = None
            self.T = None

        self.F = None

    def update_values(self):
        """
        This method is for updating in the finite horizon case.  It shifts the
        current value function 

            V_t(x) = x' P_t x + d_t
        
        and the optimal policy F_t one step *back* in time, replacing the pair
        P_t and d_t with P_{t-1} and d_{t-1}, and F_t with F_{t-1}  
        """
        # === Simplify notation === #
        Q, R, A, B, C = self.Q, self.R, self.A, self.B, self.C
        P, d = self.P, self.d
        # == Some useful matrices == #
        S1 = Q + self.beta * dot(B.T, dot(P, B))   
        S2 = self.beta * dot(B.T, dot(P, A))
        S3 = self.beta * dot(A.T, dot(P, A))
        # == Compute F as (Q + B'PB)^{-1} (beta B'PA) == #
        self.F = solve(S1, S2)  
        # === Shift P back in time one step == #
        new_P = R - dot(S2.T, solve(S1, S2)) + S3  
        # == Recalling that trace(AB) = trace(BA) == #
        new_d = self.beta * (d + np.trace(dot(P, dot(C, C.T))))  
        # == Set new state == #
        self.P, self.d = new_P, new_d

    def stationary_values(self):
        """
        Computes the matrix P and scalar d that represent the value function

            V(x) = x' P x + d

        in the infinite horizon case.  Also computes the control matrix F from
        u = - Fx

        """
        # === simplify notation === #
        Q, R, A, B, C = self.Q, self.R, self.A, self.B, self.C
        # === solve Riccati equation, obtain P === #
        A0, B0 = np.sqrt(self.beta) * A, np.sqrt(self.beta) * B
        P = riccati.dare(A0, B0, Q, R)
        # == Compute F == #
        S1 = Q + self.beta * dot(B.T, dot(P, B))  
        S2 = self.beta * dot(B.T, dot(P, A)) 
        F = solve(S1, S2)
        # == Compute d == #
        d = self.beta * np.trace(dot(P, dot(C, C.T))) / (1 - self.beta)
        # == Bind states and return values == #
        self.P, self.F, self.d = P, F, d
        return P, F, d

    def compute_sequence(self, x0, ts_length=None):
        """
        Compute and return the optimal state and control sequences x_0,...,
        x_T and u_0,..., u_T  under the assumption that {w_t} is iid and 
        N(0, 1).

        Parameters
        ===========
        x0 : numpy.ndarray
            The initial state, a vector of length n

        ts_length : int
            Length of the simulation -- defaults to T in finite case

        Returns
        ========
        x_path : numpy.ndarray
            An n x T matrix, where the t-th column represents x_t

        u_path : numpy.ndarray
            A k x T matrix, where the t-th column represents u_t
        
        """
        # === Simplify notation === #
        Q, R, A, B, C = self.Q, self.R, self.A, self.B, self.C
        # == Preliminaries, finite horizon case == #
        if self.T:
            T = self.T if not ts_length else min(ts_length, self.T)
            self.P, self.d = self.Rf, 0
        # == Preliminaries, infinite horizon case == #
        else:
            T = ts_length if ts_length else 100
            self.stationary_values()
        # == Set up initial condition and arrays to store paths == #
        x0 = np.asarray(x0)
        x0 = x0.reshape(self.n, 1)  # Make sure x0 is a column vector
        x_path = np.empty((self.n, T+1))
        u_path = np.empty((self.k, T))
        w_path = dot(C, np.random.randn(self.j, T+1))
        # == Compute and record the sequence of policies == #
        policies = []
        for t in range(T):
            if self.T:  # Finite horizon case
                self.update_values()
            policies.append(self.F)
        # == Use policy sequence to generate states and controls == #
        F = policies.pop() 
        x_path[:, 0] = x0.flatten()
        u_path[:, 0] = - dot(F, x0).flatten()
        for t in range(1, T):
            F = policies.pop() 
            Ax, Bu = dot(A, x_path[:, t-1]), dot(B, u_path[:, t-1])
            x_path[:, t] =  Ax + Bu + w_path[:, t]
            u_path[:, t] = - dot(F, x_path[:, t])
        Ax, Bu = dot(A, x_path[:, T-1]), dot(B, u_path[:, T-1])
        x_path[:, T] =  Ax + Bu + w_path[:, T]
        return x_path, u_path, w_path

########NEW FILE########
__FILENAME__ = lqramsey
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: lqramsey.py
Authors: Thomas Sargent, Doc-Jin Jang, Jeong-hun Choi, John Stachurski
LastModified: 11/08/2013

This module provides code to compute Ramsey equilibria in a LQ economy with
distortionary taxation.  The program computes allocations (consumption,
leisure), tax rates, revenues, the net present value of the debt and other
related quantities.

Functions for plotting the results are also provided below.

See the lecture at http://quant-econ.net/lqramsey.html for a description of
the model.

"""

import sys
import numpy as np
from numpy import sqrt, max, eye, dot, zeros, cumsum, array
from numpy.random import randn
import scipy.linalg 
import matplotlib.pyplot as plt
from collections import namedtuple
from rank_nullspace import nullspace
import mc_tools
from quadsums import var_quadratic_sum



# == Set up a namedtuple to store data on the model economy == #
Economy = namedtuple('economy',
        ('beta',        # Discount factor
          'Sg',         # Govt spending selector matrix
          'Sd',         # Exogenous endowment selector matrix
          'Sb',         # Utility parameter selector matrix
          'Ss',         # Coupon payments selector matrix
          'discrete',   # Discrete or continuous -- boolean
          'proc'))      # Stochastic process parameters

# == Set up a namedtuple to store return values for compute_paths() == #
Path = namedtuple('path',
       ('g',            # Govt spending
        'd',            # Endowment
        'b',            # Utility shift parameter
        's',            # Coupon payment on existing debt
        'c',            # Consumption
        'l',            # Labor
        'p',            # Price
        'tau',          # Tax rate
        'rvn',          # Revenue
        'B',            # Govt debt
        'R',            # Risk free gross return
        'pi',           # One-period risk-free interest rate
        'Pi',           # Cumulative rate of return, adjusted
        'xi'))          # Adjustment factor for Pi


def compute_paths(T, econ):
    """
    Compute simulated time paths for exogenous and endogenous variables.

    Parameters
    ===========
    T: int
        Length of the simulation

    econ: a namedtuple of type 'Economy', containing
         beta       - Discount factor
         Sg         - Govt spending selector matrix
         Sd         - Exogenous endowment selector matrix
         Sb         - Utility parameter selector matrix
         Ss         - Coupon payments selector matrix
         discrete   - Discrete exogenous process (True or False)
         proc       - Stochastic process parameters

    Returns
    ========
    path: a namedtuple of type 'Path', containing
         g            - Govt spending
         d            - Endowment
         b            - Utility shift parameter
         s            - Coupon payment on existing debt
         c            - Consumption
         l            - Labor
         p            - Price
         tau          - Tax rate
         rvn          - Revenue
         B            - Govt debt
         R            - Risk free gross return
         pi           - One-period risk-free interest rate
         Pi           - Cumulative rate of return, adjusted
         xi           - Adjustment factor for Pi

        The corresponding values are flat numpy ndarrays.

    """

    # == Simplify names == #
    beta, Sg, Sd, Sb, Ss = econ.beta, econ.Sg, econ.Sd, econ.Sb, econ.Ss

    if econ.discrete:
        P, x_vals = econ.proc
    else:
        A, C = econ.proc

    # == Simulate the exogenous process x == #
    if econ.discrete:
        state = mc_tools.sample_path(P, init=0, sample_size=T)
        x = x_vals[:,state]
    else:
        # == Generate an initial condition x0 satisfying x0 = A x0 == #
        nx, nx = A.shape
        x0 = nullspace((eye(nx) - A))
        x0 = -x0 if (x0[nx-1] < 0) else x0
        x0 = x0 / x0[nx-1]

        # == Generate a time series x of length T starting from x0 == #
        nx, nw = C.shape
        x = zeros((nx, T))
        w = randn(nw, T)    
        x[:, 0] = x0.T    
        for t in range(1,T):    
            x[:, t] = dot(A, x[:, t-1]) + dot(C, w[:, t])

    # == Compute exogenous variable sequences == #
    g, d, b, s = (dot(S, x).flatten() for S in (Sg, Sd, Sb, Ss))
        
    # == Solve for Lagrange multiplier in the govt budget constraint == #
    ## In fact we solve for nu = lambda / (1 + 2*lambda).  Here nu is the 
    ## solution to a quadratic equation a(nu**2 - nu) + b = 0 where
    ## a and b are expected discounted sums of quadratic forms of the state.
    Sm = Sb - Sd - Ss    
    # == Compute a and b == #
    if econ.discrete:
        ns = P.shape[0]
        F = scipy.linalg.inv(np.identity(ns) - beta * P)
        a0 = 0.5 * dot(F, dot(Sm, x_vals).T**2)[0]
        H = dot(Sb - Sd + Sg, x_vals) * dot(Sg - Ss, x_vals)
        b0 = 0.5 * dot(F, H.T)[0]
        a0, b0 = float(a0), float(b0)
    else:
        H = dot(Sm.T, Sm)
        a0 = 0.5 * var_quadratic_sum(A, C, H, beta, x0)
        H = dot((Sb - Sd + Sg).T, (Sg + Ss))
        b0 = 0.5 * var_quadratic_sum(A, C, H, beta, x0)

    # == Test that nu has a real solution before assigning == #
    warning_msg = """
    Hint: you probably set government spending too {}.  Elect a {}
    Congress and start over.
    """
    disc = a0**2 - 4 * a0 * b0
    if disc >= 0:  
        nu = 0.5 * (a0 - sqrt(disc)) / a0
    else:
        print "There is no Ramsey equilibrium for these parameters."
        print warning_msg.format('high', 'Republican')
        sys.exit(0)

    # == Test that the Lagrange multiplier has the right sign == #
    if nu * (0.5 - nu) < 0:  
        print "Negative multiplier on the government budget constraint."
        print warning_msg.format('low', 'Democratic')
        sys.exit(0)

    # == Solve for the allocation given nu and x == #
    Sc = 0.5 * (Sb + Sd - Sg - nu * Sm)    
    Sl = 0.5 * (Sb - Sd + Sg - nu * Sm)   
    c = dot(Sc, x).flatten()
    l = dot(Sl, x).flatten()
    p = dot(Sb - Sc, x).flatten()  # Price without normalization
    tau = 1 - l / (b - c)
    rvn = l * tau  

    # == Compute remaining variables == #
    if econ.discrete:
        H = dot(Sb - Sc, x_vals) * dot(Sl - Sg, x_vals) - dot(Sl, x_vals)**2
        temp = dot(F, H.T).flatten()
        B = temp[state] / p
        H = dot(P[state, :], dot(Sb - Sc, x_vals).T).flatten()
        R = p / (beta * H)
        temp = dot(P[state,:], dot(Sb - Sc, x_vals).T).flatten()
        xi = p[1:] / temp[:T-1]
    else:
        H = dot(Sl.T, Sl) - dot((Sb - Sc).T, Sl - Sg) 
        L = np.empty(T)
        for t in range(T):
            L[t] = var_quadratic_sum(A, C, H, beta, x[:, t])
        B = L / p
        Rinv = (beta * dot(dot(Sb - Sc, A), x)).flatten() / p
        R = 1 / Rinv
        AF1 = dot(Sb - Sc, x[:, 1:])
        AF2 = dot(dot(Sb - Sc, A), x[:, :T-1])
        xi =  AF1 / AF2
        xi = xi.flatten()

    pi = B[1:] - R[:T-1] * B[:T-1] - rvn[:T-1] + g[:T-1]
    Pi = cumsum(pi * xi)

    # == Prepare return values == #
    path = Path(g=g, 
            d=d,
            b=b,
            s=s,
            c=c,
            l=l,
            p=p,
            tau=tau,
            rvn=rvn,
            B=B,
            R=R,
            pi=pi,
            Pi=Pi,
            xi=xi)

    return path


def gen_fig_1(path):
    """
    The parameter is the path namedtuple returned by compute_paths().  See
    the docstring of that function for details.
    """

    T = len(path.c)  

    # == Prepare axes == #
    num_rows, num_cols = 2, 2
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(14, 10))
    plt.subplots_adjust(hspace=0.4)
    for i in range(num_rows):
        for j in range(num_cols):
            axes[i, j].grid()
            axes[i, j].set_xlabel(r'Time')
    bbox = (0., 1.02, 1., .102)
    legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
    p_args = {'lw' : 2, 'alpha' : 0.7}

    # == Plot consumption, govt expenditure and revenue == #
    ax = axes[0, 0]
    ax.plot(path.rvn, label=r'$\tau_t \ell_t$', **p_args)
    ax.plot(path.g, label=r'$g_t$', **p_args)
    ax.plot(path.c, label=r'$c_t$', **p_args)
    ax.legend(ncol=3, **legend_args)

    # == Plot govt expenditure and debt == #
    ax = axes[0, 1]
    ax.plot(range(1,T+1), path.rvn, label=r'$\tau_t \ell_t$', **p_args)
    ax.plot(range(1,T+1), path.g, label=r'$g_t$', **p_args)
    ax.plot(range(1,T), path.B[1:T], label=r'$B_{t+1}$', **p_args)
    ax.legend(ncol=3, **legend_args)

    # == Plot risk free return == #
    ax = axes[1, 0]
    ax.plot(range(1,T+1), path.R - 1, label=r'$R_t - 1$', **p_args)
    ax.legend(ncol=1, **legend_args)

    # == Plot revenue, expenditure and risk free rate == #
    ax = axes[1, 1]
    ax.plot(range(1,T+1), path.rvn, label=r'$\tau_t \ell_t$', **p_args)
    ax.plot(range(1,T+1), path.g, label=r'$g_t$', **p_args)
    axes[1, 1].plot(range(1,T), path.pi, label=r'$\pi_{t+1}$', **p_args)
    ax.legend(ncol=3, **legend_args)

    plt.show()


def gen_fig_2(path):
    """
    The parameter is the path namedtuple returned by compute_paths().  See
    the docstring of that function for details.
    """

    T = len(path.c)  

    # == Prepare axes == #
    num_rows, num_cols = 2, 1
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(10, 10))
    plt.subplots_adjust(hspace=0.5)
    bbox = (0., 1.02, 1., .102)
    bbox = (0., 1.02, 1., .102)
    legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
    p_args = {'lw' : 2, 'alpha' : 0.7}

    # == Plot adjustment factor == #
    ax = axes[0]
    ax.plot(range(2,T+1), path.xi, label=r'$\xi_t$', **p_args)
    ax.grid()
    ax.set_xlabel(r'Time')
    ax.legend(ncol=1, **legend_args)

    # == Plot adjusted cumulative return == #
    ax = axes[1]
    ax.plot(range(2,T+1), path.Pi, label=r'$\Pi_t$', **p_args) 
    ax.grid()
    ax.set_xlabel(r'Time')
    ax.legend(ncol=1, **legend_args)

    plt.show()


########NEW FILE########
__FILENAME__ = lss
"""
Origin: QE by Thomas J. Sargent and John Stachurski
Filename: lss.py
LastModified: 30/01/2014

Computes quantities related to the linear state space model

    x_{t+1} = A x_t + C w_{t+1}
        y_t = G x_t

The shocks {w_t} are iid and N(0, I)
"""

import numpy as np
from numpy import dot
from numpy.random import multivariate_normal
from scipy.linalg import eig, solve, solve_discrete_lyapunov

class LSS:

    def __init__(self, A, C, G, mu_0=None, Sigma_0=None):
        """
        Provides initial parameters describing the state space model

            x_{t+1} = A x_t + C w_{t+1}
                y_t = G x_t 

        where {w_t} are iid and N(0, I).  If the initial conditions mu_0 and
        Sigma_0 for x_0 ~ N(mu_0, Sigma_0) are not supplied, both are set to
        zero. When Sigma_0=0, the draw of x_0 is exactly mu_0.
        
        Parameters
        ============
        
        All arguments should be scalars or array_like

            * A is n x n
            * C is n x m
            * G is k x n
            * mu_0 is n x 1
            * Sigma_0 is n x n, positive definite and symmetric

        """
        self.A, self.G, self.C = map(self.convert, (A, G, C))
        self.k, self.n = self.G.shape
        self.m = self.C.shape[1]
        # == Default initial conditions == #
        if mu_0 == None:
            self.mu_0 = np.zeros((self.n, 1))
        else:
            self.mu_0 = np.asarray(mu_0)
        if Sigma_0 == None:
            self.Sigma_0 = np.zeros((self.n, self.n))
        else:
            self.Sigma_0 = Sigma_0

    def convert(self, x): 
        """
        Convert array_like objects (lists of lists, floats, etc.) into well
        formed 2D NumPy arrays
        """
        return np.atleast_2d(np.asarray(x, dtype='float32'))

    def simulate(self, ts_length=100):
        """
        Simulate a time series of length ts_length, first drawing 
        
            x_0 ~ N(mu_0, Sigma_0)


        Returns
        ========
        x : numpy.ndarray
            An n x ts_length array, where the t-th column is x_t

        y : numpy.ndarray
            A k x ts_length array, where the t-th column is y_t

        """
        x = np.empty((self.n, ts_length))
        x[:,0] = multivariate_normal(self.mu_0.flatten(), self.Sigma_0)
        w = np.random.randn(self.m, ts_length-1)
        for t in range(ts_length-1):
            x[:, t+1] = self.A.dot(x[:, t]) + self.C.dot(w[:, t])
        y = self.G.dot(x)
        return x, y

    def replicate(self, T=10, num_reps=100):
        """
        Simulate num_reps observations of x_T and y_T given 
        x_0 ~ N(mu_0, Sigma_0).

        Returns
        ========
        x : numpy.ndarray
            An n x num_reps array, where the j-th column is the j_th
            observation of x_T

        y : numpy.ndarray
            A k x num_reps array, where the j-th column is the j_th
            observation of y_T
        """
        x = np.empty((self.n, num_reps))
        for j in range(num_reps):
            x_T, _ = self.simulate(ts_length=T+1)
            x[:, j] = x_T[:, -1]
        y = self.G.dot(x)
        return x, y

    def moment_sequence(self):
        """
        Create a generator to calculate the population mean and
        variance-convariance matrix for both x_t and y_t, starting at the
        initial condition (self.mu_0, self.Sigma_0).  

        Returns
        ========

        A generator, such that each iteration produces the moments of x and y,
        updated one unit of time.  The moments are returned as a 4-tuple with
        the following interpretation:

        mu_x : numpy.ndarray
            An n x 1 array representing the population mean of x_t

        mu_y : numpy.ndarray
            A  k x 1 array representing the population mean of y_t

        Sigma_x : numpy.ndarray
            An n x n array representing the variance-covariance matrix of x_t

        Sigma_y : numpy.ndarray
            A k x k array representing the variance-covariance matrix of y_t

        """
        # == Simplify names == #
        A, C, G = self.A, self.C, self.G
        # == Initial moments == #
        mu_x, Sigma_x = self.mu_0, self.Sigma_0
        while 1:
            mu_y, Sigma_y = G.dot(mu_x), G.dot(Sigma_x).dot(G.T)
            yield mu_x, mu_y, Sigma_x, Sigma_y
            # == Update moments of x == #
            mu_x = A.dot(mu_x)
            Sigma_x = A.dot(Sigma_x).dot(A.T) + C.dot(C.T)

    def stationary_distributions(self, max_iter=200, tol=1e-5):
        """
        Compute the moments of the stationary distributions of x_t and y_t if
        possible.  Computation is by iteration, starting from the initial
        conditions self.mu_0 and self.Sigma_0

        Returns
        ========
        mu_x_star : numpy.ndarray
            An n x 1 array representing the stationary mean of x_t

        mu_y_star : numpy.ndarray
            An k x 1 array representing the stationary mean of y_t

        Sigma_x_star : numpy.ndarray
            An n x n array representing the stationary var-cov matrix of x_t

        Sigma_y_star : numpy.ndarray
            An k x k array representing the stationary var-cov matrix of y_t

        """
        # == Initialize iteration == #
        m = self.moment_sequence()
        mu_x, mu_y, Sigma_x, Sigma_y = m.next()
        i = 0
        error = tol + 1
        # == Loop until convergence or failuer == #
        while error > tol:

            if i > max_iter:
                fail_message = 'Convergence failed after {} iterations'
                raise ValueError(fail_message.format(max_iter))

            else:
                i += 1
                mu_x1, mu_y1, Sigma_x1, Sigma_y1 = m.next()
                error_mu = np.max(np.abs(mu_x1 - mu_x))
                error_Sigma = np.max(np.abs(Sigma_x1 - Sigma_x))
                error = max(error_mu, error_Sigma)
                mu_x, Sigma_x = mu_x1, Sigma_x1

        # == Prepare return values == #
        mu_x_star, Sigma_x_star = mu_x, Sigma_x
        mu_y_star, Sigma_y_star = mu_y1, Sigma_y1
        return mu_x_star, mu_y_star, Sigma_x_star, Sigma_y_star


    def geometric_sums(self, beta, x_t):
        """
        Forecast the geometric sums

            S_x := E [sum_{j=0}^{\infty} beta^j x_{t+j} | x_t ]

            S_y := E [sum_{j=0}^{\infty} beta^j y_{t+j} | x_t ]

        Parameters
        ===========
        beta : float
            Discount factor, in [0, 1)

        beta : array_like
            The term x_t for conditioning

        Returns
        ========
        S_x : numpy.ndarray
            Geometric sum as defined above

        S_y : numpy.ndarray
            Geometric sum as defined above

        """
        I = np.identity(self.n)
        S_x = solve(I - beta * self.A, x_t)
        S_y = self.G.dot(S_x)
        return S_x, S_y


########NEW FILE########
__FILENAME__ = lucastree
"""
Origin: QE by Thomas J. Sargent and John Stachurski 
Filename: lucastree.py
Authors: Thomas Sargent, John Stachurski
LastModified: Tue May 6 08:37:18 EST 2014

Solves the price function for the Lucas tree in a continuous state setting,
using piecewise linear approximation for the sequence of candidate price
functions.  The consumption endownment follows the log linear AR(1) process

    log y' = alpha log y + sigma epsilon

where y' is a next period y and epsilon is an iid standard normal shock.
Hence

    y' = y^alpha * xi   where xi = e^(sigma * epsilon)

The distribution phi of xi is

    phi = LN(0, sigma^2) where LN means lognormal

Example usage:

    tree = lucas_tree(gamma=2, beta=0.95, alpha=0.90, sigma=0.1)
    grid, price_vals = compute_price(tree)


"""

from __future__ import division  # Omit for Python 3.x
import numpy as np
from collections import namedtuple
from scipy import interp
from scipy.stats import lognorm
from scipy.integrate import fixed_quad

# == Use a namedtuple to store the parameters of the Lucas tree == #

lucas_tree = namedtuple('lucas_tree', 
        ['gamma',   # Risk aversion
         'beta',    # Discount factor
         'alpha',   # Correlation coefficient
         'sigma'])  # Shock volatility

# == A function to compute the price == #

def compute_price(lt, grid=None):
    """
    Compute the equilibrium price function associated Lucas tree lt

    Parameters
    ==========
    lt : namedtuple, lucas_tree
        A namedtuple containing the parameters of the Lucas tree

    grid : a NumPy array giving the grid points on which to return the
        function values.  Grid points should be nonnegative.

    """
    # == Simplify names, set up distribution phi == #
    gamma, beta, alpha, sigma = lt.gamma, lt.beta, lt.alpha, lt.sigma
    phi = lognorm(sigma)

    # == Set up a function for integrating w.r.t. phi == #

    int_min, int_max = np.exp(-4 * sigma), np.exp(4 * sigma)  
    def integrate(g):
        "Integrate over three standard deviations"
        integrand = lambda z: g(z) * phi.pdf(z)
        result, error = fixed_quad(integrand, int_min, int_max)
        return result

    # == If there's no grid, form an appropriate one == #

    if grid == None:
        grid_size = 100
        if abs(alpha) >= 1:
            # If nonstationary, put the grid on [0,10]
            grid_min, grid_max = 0, 10
        else:
            # Set the grid interval to contain most of the mass of the
            # stationary distribution of the consumption endowment
            ssd = sigma / np.sqrt(1 - alpha**2)
            grid_min, grid_max = np.exp(-4 * ssd), np.exp(4 * ssd)
        grid = np.linspace(grid_min, grid_max, grid_size)
    else:
        grid_min, grid_max, grid_size = min(grid), max(grid), len(grid)

    # == Compute the function h in the Lucas operator as a vector of == # 
    # == values on the grid == #

    h = np.empty(grid_size)
    # Recall that h(y) = beta * int u'(G(y,z)) G(y,z) phi(dz)
    for i, y in enumerate(grid):
        integrand = lambda z: (y**alpha * z)**(1 - gamma) # u'(G(y,z)) G(y,z)
        h[i] = beta * integrate(integrand)

    # == Set up the Lucas operator T == #

    def lucas_operator(f):
        """
        The approximate Lucas operator, which computes and returns the updated
        function Tf on the grid poitns.

        Parameters
        ==========

        f : flat NumPy array with len(f) = len(grid)
            A candidate function on R_+ represented as points on a grid 

        """
        Tf = np.empty(len(f))
        Af = lambda x: interp(x, grid, f)  # Piecewise linear interpolation

        for i, y in enumerate(grid):
            Tf[i] = h[i] + beta * integrate(lambda z: Af(y**alpha * z))

        return Tf

    # == Now compute the price by iteration == #

    error_tol, max_iter = 1e-3, 50
    error = error_tol + 1
    iterate = 0
    f = np.zeros(len(grid))  # Initial condition
    while iterate < max_iter and error > error_tol:
        new_f = lucas_operator(f)
        iterate += 1
        error = np.max(np.abs(new_f - f))
        print error
        f = new_f

    return grid, f * grid**gamma # p(y) = f(y) / u'(y) = f(y) * y^gamma




########NEW FILE########
__FILENAME__ = mc_tools
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: mc_tools.py
Authors: John Stachurski and Thomas J. Sargent
LastModified: 11/08/2013
"""

import numpy as np
from discrete_rv import discreteRV

def compute_stationary(P):
    """
    Computes the stationary distribution of Markov matrix P.

    Parameters: 
    
        * P is a square 2D NumPy array

    Returns: A flat array giving the stationary distribution
    """
    n = len(P)                               # P is n x n
    I = np.identity(n)                       # Identity matrix
    B, b = np.ones((n, n)), np.ones((n, 1))  # Matrix and vector of ones
    A = np.transpose(I - P + B) 
    solution = np.linalg.solve(A, b)
    return solution.flatten()                # Return a flat array



def sample_path(P, init=0, sample_size=1000): 
    """
    Generates one sample path from a finite Markov chain with (n x n) Markov
    matrix P on state space S = {0,...,n-1}. 

    Parameters: 

        * P is a nonnegative 2D NumPy array with rows that sum to 1
        * init is either an integer in S or a nonnegative array of length n
            with elements that sum to 1
        * sample_size is an integer

    If init is an integer, the integer is treated as the determinstic initial
    condition.  If init is a distribution on S, then X_0 is drawn from this
    distribution.

    Returns: A NumPy array containing the sample path
    """
    # === set up array to store output === #
    X = np.empty(sample_size, dtype=int)
    if isinstance(init, int):
        X[0] = init
    else:
        X[0] = discreteRV(init).draw()

    # === turn each row into a distribution === #
    # In particular, let P_dist[i] be the distribution corresponding to the
    # i-th row P[i,:]
    n = len(P)
    P_dist = [discreteRV(P[i,:]) for i in range(n)]

    # === generate the sample path === #
    for t in range(sample_size - 1):
        X[t+1] = P_dist[X[t]].draw()
    return X


########NEW FILE########
__FILENAME__ = odu_vfi
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: odu_vfi.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

Solves the "Offer Distribution Unknown" Model by value function iteration.

Note that a much better technique is given in solution_odu_ex1.py
"""
from scipy.interpolate import LinearNDInterpolator
from scipy.integrate import fixed_quad
from scipy.stats import beta as beta_distribution
import numpy as np

class searchProblem:
    """
    A class to store a given parameterization of the "offer distribution
    unknown" model.
    """

    def __init__(self, beta=0.95, c=0.6, F_a=1, F_b=1, G_a=3, G_b=1.2, 
            w_max=2, w_grid_size=40, pi_grid_size=40):
        """
        Sets up parameters and grid.  The attribute "grid_points" defined
        below is a 2 column array that stores the 2D grid points for the DP
        problem. Each row represents a single (w, pi) pair.
        """
        self.beta, self.c, self.w_max = beta, c, w_max
        self.F = beta_distribution(F_a, F_b, scale=w_max)
        self.G = beta_distribution(G_a, G_b, scale=w_max)
        self.f, self.g = self.F.pdf, self.G.pdf    # Density functions
        self.pi_min, self.pi_max = 1e-3, 1 - 1e-3  # Avoids instability
        self.w_grid = np.linspace(0, w_max, w_grid_size)
        self.pi_grid = np.linspace(self.pi_min, self.pi_max, pi_grid_size)
        x, y = np.meshgrid(self.w_grid, self.pi_grid)
        self.grid_points = np.column_stack((x.ravel(1), y.ravel(1)))

    def q(self, w, pi):
        """
        Updates pi using Bayes' rule and the current wage observation w.
        """
        new_pi = 1.0 / (1 + ((1 - pi) * self.g(w)) / (pi * self.f(w)))
        # Return new_pi when in [pi_min, pi_max], and the end points otherwise
        return np.maximum(np.minimum(new_pi, self.pi_max), self.pi_min)


def bellman(sp, v):
    """
    The Bellman operator.

        * sp is an instance of searchProblem
        * v is an approximate value function represented as a one-dimensional
            array.
    """
    f, g, beta, c, q = sp.f, sp.g, sp.beta, sp.c, sp.q  # Simplify names
    vf = LinearNDInterpolator(sp.grid_points, v)
    N = len(v)
    new_v = np.empty(N)
    for i in range(N):
        w, pi = sp.grid_points[i,:]
        v1 = w / (1 - beta)
        integrand = lambda m: vf(m, q(m, pi)) * (pi * f(m) + (1 - pi) * g(m))
        integral, error = fixed_quad(integrand, 0, sp.w_max)
        v2 = c + beta * integral
        new_v[i] = max(v1, v2)
    return new_v

def get_greedy(sp, v):
    """
    Compute optimal actions taking v as the value function.  Parameters are
    the same as for bellman().  Returns a NumPy array called "policy", where
    policy[i] is the optimal action at sp.grid_points[i,:].  The optimal
    action is represented in binary, where 0 indicates reject and 1 indicates
    accept.
    """
    f, g, beta, c, q = sp.f, sp.g, sp.beta, sp.c, sp.q  # Simplify names
    vf = LinearNDInterpolator(sp.grid_points, v)
    N = len(v)
    policy = np.zeros(N, dtype=int)
    for i in range(N):
        w, pi = sp.grid_points[i,:]
        v1 = w / (1 - beta)
        integrand = lambda m: vf(m, q(m, pi)) * (pi * f(m) + (1 - pi) * g(m))
        integral, error = fixed_quad(integrand, 0, sp.w_max)
        v2 = c + beta * integral
        policy[i] = v1 > v2  # Evaluates to 1 or 0
    return policy


########NEW FILE########
__FILENAME__ = optgrowth
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: optgrowth.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

Solving the optimal growth problem via value function iteration.

"""

from __future__ import division  # Omit for Python 3.x
import numpy as np
from scipy.optimize import fminbound
from scipy import interp

class growthModel:
    """
    This class is just a "struct" to hold the collection of primitives
    defining the growth model.  The default values are 

        f(k) = k**alpha, i.e, Cobb-douglas production function
        u(c) = ln(c), i.e, log utility

    See the __init__ function for details
    """
    def __init__(self, f=lambda k: k**0.65, beta=0.95, u=np.log, 
            grid_max=2, grid_size=150):
        """
        Parameters:

            * f is the production function and u is the utility function 
            * beta is the discount factor, a scalar in (0, 1)
            * grid_max and grid_size describe the grid 

        """
        self.u, self.f, self.beta = u, f, beta
        self.grid = np.linspace(1e-6, grid_max, grid_size)


def bellman_operator(gm, w):
    """
    The approximate Bellman operator, which computes and returns the updated
    value function Tw on the grid poitns.

    Parameters:

        * gm is an instance of the growthModel class
        * w is a flat NumPy array with len(w) = len(grid)

    The vector w represents the value of the input function on the grid
    points.

    """
    # === Apply linear interpolation to w === #
    Aw = lambda x: interp(x, gm.grid, w)  

    # === set Tw[i] equal to max_c { u(c) + beta w(f(k_i) - c)} === #
    Tw = np.empty(len(w))
    for i, k in enumerate(gm.grid):
        objective = lambda c:  - gm.u(c) - gm.beta * Aw(gm.f(k) - c)
        c_star = fminbound(objective, 1e-6, gm.f(k))
        Tw[i] = - objective(c_star)

    return Tw


def compute_greedy(gm, w):
    """
    Compute the w-greedy policy on the grid points.  Parameters:

        * gm is an instance of the growthModel class
        * w is a flat NumPy array with len(w) = len(grid)

    """
    # === Apply linear interpolation to w === #
    Aw = lambda x: interp(x, gm.grid, w)  

    # === set sigma[i] equal to argmax_c { u(c) + beta w(f(k_i) - c)} === #
    sigma = np.empty(len(w))
    for i, k in enumerate(gm.grid):
        objective = lambda c:  - gm.u(c) - gm.beta * Aw(gm.f(k) - c)
        sigma[i] = fminbound(objective, 1e-6, gm.f(k))

    return sigma


########NEW FILE########
__FILENAME__ = quadsums
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: quadsums.py
Authors: Thomas Sargent,  John Stachurski
LastModified: 11/12/2013

This module provides functions to compute quadratic sums of the form described
in the docstrings.

"""


import numpy as np
from numpy import sqrt, dot
import scipy.linalg 


def var_quadratic_sum(A, C, H, beta, x0):
    """
    Computes the expected discounted quadratic sum
    
        q(x_0) := E \sum_{t=0}^{\infty} \beta^t x_t' H x_t

    Here {x_t} is the VAR process x_{t+1} = A x_t + C w_t with {w_t} standard
    normal and x_0 the initial condition.

    Parameters
    ===========
    A, C, and H: numpy.ndarray
        All are n x n matrices represented as NumPy arrays

    beta: float
        A scalar in (0, 1) 
    
    x_0: numpy.ndarray
        The initial condtion. A conformable array (of length n, or with n rows) 

    Returns
    ========
    q0: numpy.ndarray
        Represents the value q(x_0)

    Remarks: The formula for computing q(x_0) is q(x_0) = x_0' Q x_0 + v where 

        Q is the solution to Q = H + beta A' Q A and 
        v = \trace(C' Q C) \beta / (1 - \beta)

    """
    # == Make sure that A, C, H and x0 are array_like == #
    A, C, H, x0 = map(np.asarray, (A, C, H, x0))
    # == Start computations == #
    Q = scipy.linalg.solve_discrete_lyapunov(sqrt(beta) * A.T, H)
    cq = dot(dot(C.T, Q), C)
    v = np.trace(cq) * beta / (1 - beta)
    q0 = dot(dot(x0.T, Q), x0) + v
    return q0


def m_quadratic_sum(A, B, max_it=50):
    """
    Computes the quadratic sum 

        V = \sum_{j=0}^{\infty} A^j B A^j'

    Parameters
    ===========
    A, B: numpy.ndarray
        Both are n x n matrices represented as NumPy arrays.  For convergence
        we assume that the eigenvalues of A have moduli bounded by unity

    Returns
    ========
    gamma1: numpy.ndarray
        Represents the value V

    V is computed by using a doubling algorithm. In particular, we iterate to
    convergence on V_j with the following recursions for j = 1, 2,...
    starting from V_0 = B, a_0 = A:

        a_j = a_{j-1} a_{j-1}

        V_j = V_{j-1} + a_{j-1} V_{j-1} a_{j-1}'

    """
    alpha0 = A
    gamma0 = B

    diff = 5
    n_its = 1

    while diff > 1e-15:

        alpha1 = alpha0.dot(alpha0)
        gamma1 = gamma0 + np.dot(alpha0.dot(gamma0), alpha0.T)

        diff = np.max(np.abs(gamma1 - gamma0))
        alpha0 = alpha1
        gamma0 = gamma1

        n_its += 1

        if n_its > max_it:
            raise ValueError('Exceeded maximum iterations of %i.' % (max_it) +
                             ' Check your input matrices')

    return gamma1

########NEW FILE########
__FILENAME__ = rank_nullspace
import numpy as np
from numpy.linalg import svd

def rank(A, atol=1e-13, rtol=0):
    """Estimate the rank (i.e. the dimension of the nullspace) of a matrix.

    The algorithm used by this function is based on the singular value
    decomposition of `A`.

    Parameters
    ----------
    A : ndarray
        A should be at most 2-D.  A 1-D array with length n will be treated
        as a 2-D with shape (1, n)
    atol : float
        The absolute tolerance for a zero singular value.  Singular values
        smaller than `atol` are considered to be zero.
    rtol : float
        The relative tolerance.  Singular values less than rtol*smax are
        considered to be zero, where smax is the largest singular value.

    If both `atol` and `rtol` are positive, the combined tolerance is the
    maximum of the two; that is::
        tol = max(atol, rtol * smax)
    Singular values smaller than `tol` are considered to be zero.

    Return value
    ------------
    r : int
        The estimated rank of the matrix.

    See also
    --------
    numpy.linalg.matrix_rank
        matrix_rank is basically the same as this function, but it does not
        provide the option of the absolute tolerance.
    """

    A = np.atleast_2d(A)
    s = svd(A, compute_uv=False)
    tol = max(atol, rtol * s[0])
    rank = int((s >= tol).sum())
    return rank


def nullspace(A, atol=1e-13, rtol=0):
    """Compute an approximate basis for the nullspace of A.

    The algorithm used by this function is based on the singular value
    decomposition of `A`.

    Parameters
    ----------
    A : ndarray
        A should be at most 2-D.  A 1-D array with length k will be treated
        as a 2-D with shape (1, k)
    atol : float
        The absolute tolerance for a zero singular value.  Singular values
        smaller than `atol` are considered to be zero.
    rtol : float
        The relative tolerance.  Singular values less than rtol*smax are
        considered to be zero, where smax is the largest singular value.

    If both `atol` and `rtol` are positive, the combined tolerance is the
    maximum of the two; that is::
        tol = max(atol, rtol * smax)
    Singular values smaller than `tol` are considered to be zero.

    Return value
    ------------
    ns : ndarray
        If `A` is an array with shape (m, k), then `ns` will be an array
        with shape (k, n), where n is the estimated dimension of the
        nullspace of `A`.  The columns of `ns` are a basis for the
        nullspace; each element in numpy.dot(A, ns) will be approximately
        zero.
    """

    A = np.atleast_2d(A)
    u, s, vh = svd(A)
    tol = max(atol, rtol * s[0])
    nnz = (s >= tol).sum()
    ns = vh[nnz:].conj().T
    return ns


########NEW FILE########
__FILENAME__ = riccati
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: riccati.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/09/2013

Solves the discrete-time algebraic Riccati equation 
"""

import numpy as np
from numpy import dot
from numpy.linalg import solve

def dare(A, B, R, Q, tolerance=1e-10, max_iter=150):
    """
    Solves the discrete-time algebraic Riccati equation 
    
        X = A'XA - A'XB(B'XB + R)^{-1}B'XA + Q  

    via the doubling algorithm.  An explanation of the algorithm can be found
    in "Optimal Filtering" by B.D.O. Anderson and J.B. Moore (Dover
    Publications, 2005, p. 159).

    Parameters
    ============
    All arguments should be NumPy ndarrays.

        * A is k x k
        * B is k x n
        * Q is k x k, symmetric and nonnegative definite
        * R is n x n, symmetric and positive definite

    Returns
    ========
    X : a  k x k numpy.ndarray representing the approximate solution

    """
    # == Set up == #
    error = tolerance + 1
    fail_msg = "Convergence failed after {} iterations."
    # == Make sure that all arrays are two-dimensional == #
    A, B, Q, R = map(np.atleast_2d, (A, B, Q, R))
    k = Q.shape[0]
    I = np.identity(k)

    # == Initial conditions == #
    a0 = A
    b0 = dot(B, solve(R, B.T))
    g0 = Q
    i = 1

    # == Main loop == #
    while error > tolerance:

        if i > max_iter:
            raise ValueError(fail_msg.format(i))

        else:

            a1 = dot(a0, solve(I + dot(b0, g0), a0))
            b1 = b0 + dot(a0, solve(I + dot(b0, g0), dot(b0, a0.T)))
            g1 = g0 + dot(dot(a0.T, g0), solve(I + dot(b0, g0), a0))

            error = np.max(np.abs(g1 - g0))

            a0 = a1
            b0 = b1
            g0 = g1

            i += 1

    return g1  # Return X


if __name__ == '__main__': ## Example of useage

    a = np.array([[0.1, 0.1, 0.0],
                  [0.1, 0.0, 0.1],
                  [0.0, 0.4, 0.0]])
                       
    b = np.array([[1.0, 0.0], 
                  [0.0, 0.0], 
                  [0.0, 1.0]])
                       
    r = np.array([[0.5, 0.0], 
                  [0.0, 1.0]])
                       
    q = np.array([[1, 0.0, 0.0],
                  [0.0, 1, 0.0],
                  [0.0, 0.0, 10.0]])

    x = dare(a, b, r, q)
    print x

########NEW FILE########
__FILENAME__ = robustlq
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: robustlq.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski 
LastModified: 28/01/2014

Solves robust LQ control problems.
"""

from __future__ import division  # Remove for Python 3.sx
import numpy as np
from lqcontrol import LQ
from quadsums import var_quadratic_sum
from numpy import dot, log, sqrt, identity, hstack, vstack, trace
from scipy.linalg import solve, inv, det, solve_discrete_lyapunov

class RBLQ:
    """
    Provides methods for analysing infinite horizon robust LQ control 
    problems of the form

        min_{u_t}  sum_t beta^t {x_t' R x_t + u'_t Q u_t }

    subject to
        
        x_{t+1} = A x_t + B u_t + C w_{t+1}

    and with model misspecification parameter theta.
    """

    def __init__(self, Q, R, A, B, C, beta, theta):
        """
        Sets up the robust control problem.

        Parameters
        ==========

        Q, R : array_like, dtype = float
            The matrices R and Q from the objective function

        A, B, C : array_like, dtype = float
            The matrices A, B, and C from the state space system

        beta, theta : scalar, float
            The discount and robustness factors in the robust control problem

        We assume that
        
            * R is n x n, symmetric and nonnegative definite
            * Q is k x k, symmetric and positive definite
            * A is n x n
            * B is n x k
            * C is n x j
            
        """
        # == Make sure all matrices can be treated as 2D arrays == #
        A, B, C, Q, R = map(np.atleast_2d, (A, B, C, Q, R))
        self.A, self.B, self.C, self.Q, self.R = A, B, C, Q, R
        # == Record dimensions == #
        self.k = self.Q.shape[0]
        self.n = self.R.shape[0]
        self.j = self.C.shape[1]
        # == Remaining parameters == #
        self.beta, self.theta = beta, theta

    def d_operator(self, P):
        """
        The D operator, mapping P into 
        
            D(P) := P + PC(theta I - C'PC)^{-1} C'P.

        Parameters
        ==========
        P : array_like
            A self.n x self.n array

        """
        C, theta = self.C, self.theta
        I = np.identity(self.j)
        S1 = dot(P, C)
        S2 = dot(C.T, S1)
        return P + dot(S1, solve(theta * I - S2, S1.T)) 

    def b_operator(self, P):
        """
        The B operator, mapping P into 
        
            B(P) := R - beta^2 A'PB (Q + beta B'PB)^{-1} B'PA + beta A'PA

        and also returning

            F := (Q + beta B'PB)^{-1} beta B'PA

        Parameters
        ==========
        P : array_like
            An self.n x self.n array

        """
        A, B, Q, R, beta = self.A, self.B, self.Q, self.R, self.beta
        S1 = Q + beta * dot(B.T, dot(P, B))   
        S2 = beta * dot(B.T, dot(P, A))
        S3 = beta * dot(A.T, dot(P, A))
        F = solve(S1, S2)  
        new_P = R - dot(S2.T, solve(S1, S2)) + S3  
        return F, new_P

    def robust_rule(self):
        """
        This method solves the robust control problem by tricking it into a
        stacked LQ problem, as described in chapter 2 of Hansen-Sargent's text
        "Robustness."  The optimal control with observed state is

            u_t = - F x_t

        And the value function is -x'Px

        Returns
        =======
        F : array_like, dtype = float
            The optimal control matrix from above above

        P : array_like, dtype = float
            The psoitive semi-definite matrix defining the value function

        K : array_like, dtype = float
            the worst-case shock matrix K, where :math:`w_{t+1} = K x_t` is
            the worst case shock

        """
        # == Simplify names == #
        A, B, C, Q, R = self.A, self.B, self.C, self.Q, self.R
        beta, theta = self.beta, self.theta
        k, j = self.k, self.j
        # == Set up LQ version == #
        I = identity(j)
        Z = np.zeros((k, j))
        Ba = hstack([B, C])
        Qa = vstack([hstack([Q, Z]), hstack([Z.T, -beta*I*theta])])
        lq = LQ(Qa, R, A, Ba, beta=beta)
        # == Solve and convert back to robust problem == #
        P, f, d = lq.stationary_values()
        F = f[:k, :]
        K = -f[k:f.shape[0], :]
        return F, K, P

    def robust_rule_simple(self, P_init=None, max_iter=80, tol=1e-8):
        """
        A simple algorithm for computing the robust policy F and the
        corresponding value function P, based around straightforward iteration
        with the robust Bellman operator.  This function is easier to
        understand but one or two orders of magnitude slower than
        self.robust_rule().  For more information see the docstring of that
        method.
        """
        # == Simplify names == #
        A, B, C, Q, R = self.A, self.B, self.C, self.Q, self.R
        beta, theta = self.beta, self.theta
        # == Set up loop == #
        P = np.zeros((self.n, self.n)) if not P_init else P_init
        iterate, e = 0, tol + 1
        while iterate < max_iter and e > tol:
            F, new_P = self.b_operator(self.d_operator(P))
            e = np.sqrt(np.sum((new_P - P)**2))
            iterate += 1
            P = new_P
        I = np.identity(self.j)
        S1 = P.dot(C)
        S2 = C.T.dot(S1)
        K = inv(theta * I - S2).dot(S1.T).dot(A - B.dot(F))
        return F, K, P  

    def F_to_K(self, F):
        """
        Compute agent 2's best cost-minimizing response K, given F.

        Parameters
        ==========
        F : array_like
            A self.k x self.n array

        Returns
        =======
        K : array_like, dtype = float
        P : array_like, dtype = float

        """
        Q2 = self.beta * self.theta
        R2 = - self.R - dot(F.T, dot(self.Q, F))
        A2 = self.A - dot(self.B, F)
        B2 = self.C
        lq = LQ(Q2, R2, A2, B2, beta=self.beta)
        P, neg_K, d = lq.stationary_values()
        return - neg_K, P

    def K_to_F(self, K):
        """
        Compute agent 1's best value-maximizing response F, given K.

        Parameters
        ==========
        K : array_like
            A self.j x self.n array

        Returns
        =======
        F : array_like, dtype = float
        P : array_like, dtype = float

        """
        A1 = self.A + dot(self.C, K)
        B1 = self.B
        Q1 = self.Q
        R1 = self.R - self.beta * self.theta * dot(K.T, K)
        lq = LQ(Q1, R1, A1, B1, beta=self.beta)
        P, F, d = lq.stationary_values()
        return F, P

    def compute_deterministic_entropy(self, F, K, x0):
        """
        Given K and F, compute the value of deterministic entropy, which is 
        sum_t beta^t x_t' K'K x_t with x_{t+1} = (A - BF + CK) x_t.
        """
        H0 = dot(K.T, K)
        C0 = np.zeros((self.n, 1))
        A0 = self.A - dot(self.B, F) + dot(self.C, K)
        e = var_quadratic_sum(A0, C0, H0, self.beta, x0)
        return e

    def evaluate_F(self, F):
        """
        Given a fixed policy F, with the interpretation u = -F x, this
        function computes the matrix P_F and constant d_F associated with
        discounted cost J_F(x) = x' P_F x + d_F. 

        Parameters
        ==========
        F : array_like
            A self.k x self.n array

        Returns
        =======
        P_F : array_like, dtype = float
            Matrix for discounted cost

        d_F : scalar
            Constant for discounted cost

        K_F : array_like, dtype = float
            Worst case policy
            
        O_F : array_like, dtype = float
            Matrix for discounted entropy
            
        o_F : scalar
            Constant for discounted entropy

        
        """
        # == Simplify names == #
        Q, R, A, B, C = self.Q, self.R, self.A, self.B, self.C
        beta, theta = self.beta, self.theta
        # == Solve for policies and costs using agent 2's problem == #
        K_F, neg_P_F = self.F_to_K(F)
        P_F = - neg_P_F
        I = np.identity(self.j)
        H = inv(I - C.T.dot(P_F.dot(C)) / theta)
        d_F = log(det(H))
        # == Compute O_F and o_F == #
        sig = -1.0 / theta
        AO = sqrt(beta) * (A - dot(B, F) + dot(C, K_F))
        O_F = solve_discrete_lyapunov(AO.T, beta * dot(K_F.T, K_F))
        ho = (trace(H - 1) - d_F) / 2.0
        tr = trace(dot(O_F, C.dot(H.dot(C.T))))
        o_F = (ho + beta * tr) / (1 - beta)
        return K_F, P_F, d_F, O_F, o_F


########NEW FILE########
__FILENAME__ = tauchen
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: tauchen.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

Discretizes Gaussian linear AR(1) processes via Tauchen's method

"""

import numpy as np
from scipy.stats import norm

def approx_markov(rho, sigma_u, m=3, n=7):
    """
    Computes the Markov matrix associated with a discretized version of
    the linear Gaussian AR(1) process 

        y_{t+1} = rho * y_t + u_{t+1}

    according to Tauchen's method.  Here {u_t} is an iid Gaussian process with
    zero mean.

    Parameters:

        * rho is the correlation coefficient
        * sigma_u is the standard deviation of u
        * m parameterizes the width of the state space
        * n is the number of states
    
    Returns:

        * x, the state space, as a NumPy array
        * a matrix P, where P[i,j] is the probability of transitioning from
            x[i] to x[j]

    """
    F = norm(loc=0, scale=sigma_u).cdf
    std_y = np.sqrt(sigma_u**2 / (1-rho**2))  # standard deviation of y_t
    x_max = m * std_y                         # top of discrete state space
    x_min = - x_max                           # bottom of discrete state space
    x = np.linspace(x_min, x_max, n)          # discretized state space
    step = (x_max - x_min) / (n - 1)
    half_step = 0.5 * step
    P = np.empty((n, n))

    for i in range(n):
        P[i, 0] = F(x[0]-rho * x[i] + half_step)
        P[i, n-1] = 1 - F(x[n-1] - rho * x[i] - half_step)
        for j in range(1, n-1):
            z = x[j] - rho * x[i]
            P[i, j] = F(z + half_step) - F(z - half_step)

    return x, P

########NEW FILE########
__FILENAME__ = bisection2
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: bisection2.py
Authors: John Stachurski, Thomas J. Sargent
LastModified: 11/08/2013

"""

def bisect(f, a, b, tol=10e-5):
    """
    Implements the bisection root finding algorithm, assuming that f is a
    real-valued function on [a, b] satisfying f(a) < 0 < f(b).
    """
    lower, upper = a, b
    if upper - lower < tol:
        return 0.5 * (upper + lower)
    else:
        middle = 0.5 * (upper + lower)
        print('Current mid point = {}'.format(middle))
        if f(middle) > 0:   # Implies root is between lower and middle
            bisect(f, lower, middle)
        else:               # Implies root is between middle and upper
            bisect(f, middle, upper)




########NEW FILE########
__FILENAME__ = discrete_rv0
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: discrete_rv0.py
Authors: John Stachurski and Thomas Sargent
LastModified: 11/08/2013

"""

from numpy import cumsum
from numpy.random import uniform

class discreteRV:
    """
    Generates an array of draws from a discrete random variable with vector of
    probabilities given by q.  
    """

    def __init__(self, q):
        """
        The argument q is a NumPy array, or array like, nonnegative and sums
        to 1
        """
        self.q = q
        self.Q = cumsum(q)

    def draw(self, k=1):
        """
        Returns k draws from q. For each such draw, the value i is returned
        with probability q[i].
        """
        return self.Q.searchsorted(uniform(0, 1, size=k)) 



########NEW FILE########
__FILENAME__ = linapprox
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: linapprox.py
Authors: John Stachurski, Thomas J. Sargent
LastModified: 11/08/2013

"""

from __future__ import division  # Omit if using Python 3.x

def linapprox(f, a, b, n, x):
    """
    Evaluates the piecewise linear interpolant of f at x on the interval 
    [a, b], with n evenly spaced grid points.

    Parameters 
    ===========
        f : function
            The function to approximate

        x, a, b : scalars (floats or integers) 
            Evaluation point and endpoints, with a <= x <= b

        n : integer
            Number of grid points

    Returns
    =========
        A float. The interpolant evaluated at x

    """
    length_of_interval = b - a
    num_subintervals = n - 1
    step = length_of_interval / num_subintervals  

    # === find first grid point larger than x === #
    point = a
    while point <= x:
        point += step

    # === x must lie between the gridpoints (point - step) and point === #
    u, v = point - step, point  

    return f(u) + (x - u) * (f(v) - f(u)) / (v - u)

########NEW FILE########
__FILENAME__ = solution_career_ex1
""" 
Simulate job / career paths and compute the waiting time to permanent job /
career.  In reading the code, recall that optimal_policy[i, j] = policy at
(theta_i, epsilon_j) = either 1, 2 or 3; meaning 'stay put', 'new job' and
'new life'.
"""
import matplotlib.pyplot as plt
import numpy as np
from discrete_rv import discreteRV
from career import *
from compute_fp import compute_fixed_point

wp = workerProblem()
v_init = np.ones((wp.N, wp.N))*100
v = compute_fixed_point(bellman, wp, v_init)
optimal_policy = get_greedy(wp, v)
F = discreteRV(wp.F_probs)
G = discreteRV(wp.G_probs)

def gen_path(T=20):
    i = j = 0  
    theta_index = []
    epsilon_index = []
    for t in range(T):
        if optimal_policy[i, j] == 1:    # Stay put
            pass
        elif optimal_policy[i, j] == 2:  # New job
            j = int(G.draw())
        else:                            # New life
            i, j  = int(F.draw()), int(G.draw())
        theta_index.append(i)
        epsilon_index.append(j)
    return wp.theta[theta_index], wp.epsilon[epsilon_index]

theta_path, epsilon_path = gen_path()
fig = plt.figure()
ax1 = plt.subplot(211)
ax1.plot(epsilon_path, label='epsilon')
ax1.plot(theta_path, label='theta')
ax1.legend(loc='lower right')
theta_path, epsilon_path = gen_path()
ax2 = plt.subplot(212)
ax2.plot(epsilon_path, label='epsilon')
ax2.plot(theta_path, label='theta')
ax2.legend(loc='lower right')
plt.show()

########NEW FILE########
__FILENAME__ = solution_career_ex2
import matplotlib.pyplot as plt
import numpy as np
from discrete_rv import discreteRV
from career import *
from compute_fp import compute_fixed_point

wp = workerProblem()
v_init = np.ones((wp.N, wp.N))*100
v = compute_fixed_point(bellman, wp, v_init)
optimal_policy = get_greedy(wp, v)
F = discreteRV(wp.F_probs)
G = discreteRV(wp.G_probs)

def gen_first_passage_time():
    t = 0
    i = j = 0  
    theta_index = []
    epsilon_index = []
    while 1:
        if optimal_policy[i, j] == 1:    # Stay put
            return t
        elif optimal_policy[i, j] == 2:  # New job
            j = int(G.draw())
        else:                            # New life
            i, j  = int(F.draw()), int(G.draw())
        t += 1

M = 25000 # Number of samples
samples = np.empty(M)
for i in range(M): 
    samples[i] = gen_first_passage_time()
print np.median(samples)

########NEW FILE########
__FILENAME__ = solution_career_ex3
import matplotlib.pyplot as plt
from matplotlib import cm
from career import *
from compute_fp import compute_fixed_point

wp = workerProblem()
v_init = np.ones((wp.N, wp.N))*100
v = compute_fixed_point(bellman, wp, v_init)
optimal_policy = get_greedy(wp, v)

fig = plt.figure(figsize=(6,6))
ax = fig.add_subplot(111)
tg, eg = np.meshgrid(wp.theta, wp.epsilon)
lvls=(0.5, 1.5, 2.5, 3.5)
ax.contourf(tg, eg, optimal_policy.T, levels=lvls, cmap=cm.winter, alpha=0.5)
ax.contour(tg, eg, optimal_policy.T, colors='k', levels=lvls, linewidths=2)
ax.set_xlabel('theta', fontsize=14)
ax.set_ylabel('epsilon', fontsize=14)
ax.text(1.8, 2.5, 'new life', fontsize=14)
ax.text(4.5, 2.5, 'new job', fontsize=14, rotation='vertical')
ax.text(4.0, 4.5, 'stay put', fontsize=14)
plt.show()

########NEW FILE########
__FILENAME__ = solution_estspec_ex1

import numpy as np
import matplotlib.pyplot as plt
from linproc import linearProcess
from estspec import periodogram

## Data
n = 400
phi = 0.5
theta = 0, -0.8
lp = linearProcess(phi, theta)
X = lp.simulation(ts_length=n)

fig, ax = plt.subplots(3, 1)

for i, wl in enumerate((15, 55, 175)):  # window lengths
    
    x, y = periodogram(X)
    ax[i].plot(x, y, 'b-', lw=2, alpha=0.5, label='periodogram')

    x_sd, y_sd = lp.spectral_density(two_pi=False, resolution=120)
    ax[i].plot(x_sd, y_sd, 'r-', lw=2, alpha=0.8, label='spectral density')

    x, y_smoothed = periodogram(X, window='hamming', window_len=wl)
    ax[i].plot(x, y_smoothed, 'k-', lw=2, label='smoothed periodogram')

    ax[i].legend()
    ax[i].set_title('window length = {}'.format(wl))

plt.show()


########NEW FILE########
__FILENAME__ = solution_estspec_ex2
import numpy as np
import matplotlib.pyplot as plt
from linproc import linearProcess
import estspec

lp = linearProcess(-0.9)
wl = 65


fig, ax = plt.subplots(3, 1)

for i in range(3):
    X = lp.simulation(ts_length=150)
    ax[i].set_xlim(0, np.pi)

    x_sd, y_sd = lp.spectral_density(two_pi=False, resolution=180)
    ax[i].semilogy(x_sd, y_sd, 'r-', lw=2, alpha=0.75, label='spectral density')

    x, y_smoothed = estspec.periodogram(X, window='hamming', window_len=wl)
    ax[i].semilogy(x, y_smoothed, 'k-', lw=2, alpha=0.75, label='standard smoothed periodogram')

    x, y_ar = estspec.ar_periodogram(X, window='hamming', window_len=wl)
    ax[i].semilogy(x, y_ar, 'b-', lw=2, alpha=0.75, label='AR smoothed periodogram')

    ax[i].legend(loc='upper left')
plt.show()


########NEW FILE########
__FILENAME__ = solution_ifp_ex1
from matplotlib import pyplot as plt
from ifp import *

m = consumerProblem()
K = 80

# Bellman iteration 
V, c = initialize(m)
print "Starting value function iteration"
for i in range(K):
    print "Current iterate = " + str(i)
    V = bellman_operator(m, V)  
c1 = bellman_operator(m, V, return_policy=True)  

# Policy iteration 
print "Starting policy function iteration"
V, c2 = initialize(m)
for i in range(K):
    print "Current iterate = " + str(i)
    c2 = coleman_operator(m, c2)

fig, ax = plt.subplots()
ax.plot(m.asset_grid, c1[:, 0], label='value function iteration')
ax.plot(m.asset_grid, c2[:, 0], label='policy function iteration')
ax.set_xlabel('asset level')
ax.set_ylabel('consumption (low income)')
ax.legend(loc='upper left')
plt.show()


########NEW FILE########
__FILENAME__ = solution_ifp_ex2
from compute_fp import compute_fixed_point
from matplotlib import pyplot as plt
import numpy as np
from ifp import coleman_operator, consumerProblem, initialize

r_vals = np.linspace(0, 0.04, 4)  

fig, ax = plt.subplots()
for r_val in r_vals:
    cp = consumerProblem(r=r_val)
    v_init, c_init = initialize(cp)
    c = compute_fixed_point(coleman_operator, cp, c_init)
    ax.plot(cp.asset_grid, c[:, 0], label=r'$r = %.3f$' % r_val)

ax.set_xlabel('asset level')
ax.set_ylabel('consumption (low income)')
ax.legend(loc='upper left')
plt.show()


########NEW FILE########
__FILENAME__ = solution_ifp_ex3
from matplotlib import pyplot as plt
import numpy as np
from ifp import consumerProblem, coleman_operator, initialize
from compute_fp import compute_fixed_point
from scipy import interp
import mc_tools 

def compute_asset_series(cp, T=500000):
    """
    Simulates a time series of length T for assets, given optimal savings
    behavior.  Parameter cp is an instance of consumerProblem
    """

    Pi, z_vals, R = cp.Pi, cp.z_vals, cp.R  # Simplify names
    v_init, c_init = initialize(cp)
    c = compute_fixed_point(coleman_operator, cp, c_init)
    cf = lambda a, i_z: interp(a, cp.asset_grid, c[:, i_z])
    a = np.zeros(T+1)
    z_seq = mc_tools.sample_path(Pi, sample_size=T)
    for t in range(T):
        i_z = z_seq[t]
        a[t+1] = R * a[t] + z_vals[i_z] - cf(a[t], i_z)
    return a

if __name__ == '__main__':

    cp = consumerProblem(r=0.03, grid_max=4)
    a = compute_asset_series(cp)
    fig, ax = plt.subplots()
    ax.hist(a, bins=20, alpha=0.5, normed=True)
    ax.set_xlabel('assets')
    ax.set_xlim(-0.05, 0.75)
    plt.show()

########NEW FILE########
__FILENAME__ = solution_ifp_ex4
from matplotlib import pyplot as plt
import numpy as np
from compute_fp import compute_fixed_point
from ifp import coleman_operator, consumerProblem, initialize
from solution_ifp_ex3 import compute_asset_series

M = 25
r_vals = np.linspace(0, 0.04, M)  
fig, ax = plt.subplots()

for b in (1, 3):
    asset_mean = []
    for r_val in r_vals:
        cp = consumerProblem(r=r_val, b=b)
        mean = np.mean(compute_asset_series(cp, T=250000))
        asset_mean.append(mean)
    ax.plot(asset_mean, r_vals, label=r'$b = %d$' % b)

ax.set_yticks(np.arange(.0, 0.045, .01))
ax.set_xticks(np.arange(-3, 2, 1))
ax.set_xlabel('capital')
ax.set_ylabel('interest rate')
ax.grid(True)
ax.legend(loc='upper left')
plt.show()


########NEW FILE########
__FILENAME__ = solution_jv_ex1
import matplotlib.pyplot as plt
import random
from jv import workerProblem, bellman_operator
from compute_fp import compute_fixed_point
import numpy as np

# Set up
wp = workerProblem(grid_size=25)
G, pi, F = wp.G, wp.pi, wp.F       # Simplify names

v_init = wp.x_grid * 0.5
V = compute_fixed_point(bellman_operator, wp, v_init, max_iter=40)
s_policy, phi_policy = bellman_operator(wp, V, return_policies=True)

# Turn the policy function arrays into actual functions
s = lambda y: np.interp(y, wp.x_grid, s_policy)
phi = lambda y: np.interp(y, wp.x_grid, phi_policy)

def h(x, b, U):
    return (1 - b) * G(x, phi(x)) + b * max(G(x, phi(x)), U)

plot_grid_max, plot_grid_size = 1.2, 100
plot_grid = np.linspace(0, plot_grid_max, plot_grid_size)
fig, ax = plt.subplots()
ax.set_xlim(0, plot_grid_max)
ax.set_ylim(0, plot_grid_max)
ticks = (0.25, 0.5, 0.75, 1.0)
ax.set_xticks(ticks)
ax.set_yticks(ticks)
ax.set_xlabel(r'$x_t$', fontsize=16)
ax.set_ylabel(r'$x_{t+1}$', fontsize=16, rotation='horizontal')

ax.plot(plot_grid, plot_grid, 'k--')  # 45 degree line
for x in plot_grid:
    for i in range(50):
        b = 1 if random.uniform(0, 1) < pi(s(x)) else 0
        U = wp.F.rvs(1)
        y = h(x, b, U)
        ax.plot(x, y, 'go', alpha=0.25)
plt.show()

########NEW FILE########
__FILENAME__ = solution_jv_ex2
from matplotlib import pyplot as plt
from jv import workerProblem 
import numpy as np

# Set up
wp = workerProblem(grid_size=25)

def xbar(phi):
    return (wp.A * phi**wp.alpha)**(1 / (1 - wp.alpha))

phi_grid = np.linspace(0, 1, 100)
fig, ax = plt.subplots()
ax.set_xlabel(r'$\phi$', fontsize=16)
ax.plot(phi_grid, [xbar(phi) * (1 - phi) for phi in phi_grid], 'b-', label=r'$w^*(\phi)$')
ax.legend(loc='upper left')
plt.show()

########NEW FILE########
__FILENAME__ = solution_kalman_ex1
import numpy as np
import matplotlib.pyplot as plt
from kalman import Kalman
from scipy.stats import norm

## Parameters
theta = 10
A, G, Q, R = 1, 1, 0, 1
x_hat_0, Sigma_0 = 8, 1
## Initialize Kalman filter
kalman = Kalman(A, G, Q, R)
kalman.set_state(x_hat_0, Sigma_0)

N = 5
fig, ax = plt.subplots()
xgrid = np.linspace(theta - 5, theta + 2, 200)
for i in range(N):
    # Record the current predicted mean and variance, and plot their densities
    m, v = kalman.current_x_hat, kalman.current_Sigma
    m, v = float(m), float(v)
    ax.plot(xgrid, norm.pdf(xgrid, loc=m, scale=np.sqrt(v)), label=r'$t=%d$' % i)
    # Generate the noisy signal
    y = theta + norm.rvs(size=1)
    # Update the Kalman filter
    kalman.update(y)

ax.set_title(r'First %d densities when $\theta = %.1f$' % (N, theta)) 
ax.legend(loc='upper left')
plt.show()


########NEW FILE########
__FILENAME__ = solution_kalman_ex2
import numpy as np
import matplotlib.pyplot as plt
from kalman import Kalman
from scipy.stats import norm
from scipy.integrate import quad

## Parameters
theta = 10
A, G, Q, R = 1, 1, 0, 1
x_hat_0, Sigma_0 = 8, 1
epsilon = 0.1
## Initialize Kalman filter
kalman = Kalman(A, G, Q, R)
kalman.set_state(x_hat_0, Sigma_0)

T = 600
z = np.empty(T)
for t in range(T):
    # Record the current predicted mean and variance, and plot their densities
    m, v = kalman.current_x_hat, kalman.current_Sigma
    m, v = float(m), float(v)
    f = lambda x: norm.pdf(x, loc=m, scale=np.sqrt(v))
    integral, error = quad(f, theta - epsilon, theta + epsilon)
    z[t] = 1 - integral
    # Generate the noisy signal and update the Kalman filter
    kalman.update(theta + norm.rvs(size=1))

fig, ax = plt.subplots()
ax.set_ylim(0, 1)
ax.set_xlim(0, T)
ax.plot(range(T), z) 
ax.fill_between(range(T), np.zeros(T), z, color="blue", alpha=0.2) 
plt.show()


########NEW FILE########
__FILENAME__ = solution_kalman_ex3
from __future__ import print_function  # Remove for Python 3.x
import numpy as np
from numpy.random import multivariate_normal
import matplotlib.pyplot as plt
from scipy.linalg import eigvals
from kalman import Kalman

# === Define A, Q, G, R === #
G = np.eye(2)
R = 0.5 * np.eye(2)
A = [[0.5, 0.4], 
     [0.6, 0.3]]
Q = 0.3 * np.eye(2)

# === Define the prior density === #
Sigma = [[0.9, 0.3], 
         [0.3, 0.9]]
Sigma = np.array(Sigma)
x_hat = np.array([8, 8])

# === Initialize the Kalman filter === #
kn = Kalman(A, G, Q, R)
kn.set_state(x_hat, Sigma)

# === Set the true initial value of the state === #
x = np.zeros(2)

# == Print eigenvalues of A == #
print("Eigenvalues of A:")
print(eigvals(A))

# == Print stationary Sigma == #
S, K = kn.stationary_values()
print("Stationary prediction error variance:")
print(S)

# === Generate the plot === #
T = 50
e1 = np.empty(T)
e2 = np.empty(T)
for t in range(T):
    # == Generate signal and update prediction == #
    y = multivariate_normal(mean=np.dot(G, x), cov=R)
    kn.update(y)
    # == Update state and record error == #
    Ax = np.dot(A, x)
    x = multivariate_normal(mean=Ax, cov=Q)
    e1[t] = np.sum((x - kn.current_x_hat)**2)
    e2[t] = np.sum((x - Ax)**2)

fig, ax = plt.subplots()
ax.plot(range(T), e1, 'k-', lw=2, alpha=0.6, label='Kalman filter error') 
ax.plot(range(T), e2, 'g-', lw=2, alpha=0.6, label='conditional expectation error') 
ax.legend()
plt.show()


########NEW FILE########
__FILENAME__ = solution_lln_ex1
"""
Illustrates the delta method, a consequence of the central limit theorem.
"""
import numpy as np
from scipy.stats import uniform, norm
import matplotlib.pyplot as plt
from matplotlib import rc

# == Specifying font, needs LaTeX integration == #
rc('font',**{'family':'serif','serif':['Palatino']})
rc('text', usetex=True)

# == Set parameters == #
n = 250
replications = 100000
distribution = uniform(loc=0, scale=(np.pi / 2))
mu, s = distribution.mean(), distribution.std()

g = np.sin
g_prime = np.cos

# == Generate obs of sqrt{n} (g(\bar X_n) - g(\mu)) == #
data = distribution.rvs((replications, n)) 
sample_means = data.mean(axis=1)  # Compute mean of each row
error_obs = np.sqrt(n) * (g(sample_means) - g(mu))

# == Plot == #
asymptotic_sd = g_prime(mu) * s
fig, ax = plt.subplots()
xmin = -3 * g_prime(mu) * s
xmax = -xmin
ax.set_xlim(xmin, xmax)
ax.hist(error_obs, bins=60, alpha=0.5, normed=True)
xgrid = np.linspace(xmin, xmax, 200)
lb = r"$N(0, g'(\mu)^2  \sigma^2)$"
ax.plot(xgrid, norm.pdf(xgrid, scale=asymptotic_sd), 'k-', lw=2, label=lb)
ax.legend()

plt.show()




########NEW FILE########
__FILENAME__ = solution_lln_ex2
"""
Illustrates a consequence of the vector CLT.  The underlying random vector is
X = (W, U + W), where W is Uniform(-1, 1), U is Uniform(-2, 2), and U and W
are independent of each other.
"""
import numpy as np
from scipy.stats import uniform, chi2
from scipy.linalg import inv, sqrtm
import matplotlib.pyplot as plt

# == Set parameters == #
n = 250
replications = 50000
dw = uniform(loc=-1, scale=2)  # Uniform(-1, 1)
du = uniform(loc=-2, scale=4)  # Uniform(-2, 2)
sw, su = dw.std(), du.std()
vw, vu = sw**2, su**2
Sigma = ((vw, vw), (vw, vw + vu))
Sigma = np.array(Sigma)

# == Compute Sigma^{-1/2} == #
Q = inv(sqrtm(Sigma))  

# == Generate observations of the normalized sample mean == #
error_obs = np.empty((2, replications))
for i in range(replications):
    # == Generate one sequence of bivariate shocks == #
    X = np.empty((2, n))
    W = dw.rvs(n)
    U = du.rvs(n)
    # == Construct the n observations of the random vector == #
    X[0, :] = W
    X[1, :] = W + U
    # == Construct the i-th observation of Y_n == #
    error_obs[:, i] = np.sqrt(n) * X.mean(axis=1)

# == Premultiply by Q and then take the squared norm == #
temp = np.dot(Q, error_obs)
chisq_obs = np.sum(temp**2, axis=0)

# == Plot == #
fig, ax = plt.subplots()
xmax = 8
ax.set_xlim(0, xmax)
xgrid = np.linspace(0, xmax, 200)
lb = "Chi-squared with 2 degrees of freedom"
ax.plot(xgrid, chi2.pdf(xgrid, 2), 'k-', lw=2, label=lb)
ax.legend()
ax.hist(chisq_obs, bins=50, normed=True)

plt.show()

########NEW FILE########
__FILENAME__ = solution_lqc_ex1
"""
An LQ permanent income / life-cycle model with hump-shaped income

    y_t = m1 * t + m2 * t^2 + sigma w_{t+1}

where {w_t} is iid N(0, 1) and the coefficients m1 and m2 are chosen so that
p(t) = m1 * t + m2 * t^2 has an inverted U shape with p(0) = 0, p(T/2) = mu
and p(T) = 0.
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from lqcontrol import *

# == Model parameters == #
r       = 0.05
beta    = 1 / (1 + r)
T       = 50
c_bar   = 1.5
sigma   = 0.15
mu      = 2
q       = 1e4
m1      = T * (mu / (T/2)**2)
m2      = - (mu / (T/2)**2)

# == Formulate as an LQ problem == #
Q = 1
R = np.zeros((4, 4)) 
Rf = np.zeros((4, 4))
Rf[0, 0] = q
A = [[1 + r, -c_bar, m1, m2], 
     [0,     1,      0,  0],
     [0,     1,      1,  0],
     [0,     1,      2,  1]]
B = [[-1],
     [0],
     [0],
     [0]]
C = [[sigma],
     [0],
     [0],
     [0]]

# == Compute solutions and simulate == #
lq = LQ(Q, R, A, B, C, beta=beta, T=T, Rf=Rf)
x0 = (0, 1, 0, 0)
xp, up, wp = lq.compute_sequence(x0)

# == Convert results back to assets, consumption and income == #
ap = xp[0, :]               # Assets
c = up.flatten() + c_bar    # Consumption
time = np.arange(1, T+1)
income = wp[0, 1:] + m1 * time + m2 * time**2  # Income


# == Plot results == #
n_rows = 2
fig, axes = plt.subplots(n_rows, 1, figsize=(12, 10))

plt.subplots_adjust(hspace=0.5)
for i in range(n_rows):
    axes[i].grid()
    axes[i].set_xlabel(r'Time')
bbox = (0., 1.02, 1., .102)
legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
p_args = {'lw' : 2, 'alpha' : 0.7}

axes[0].plot(range(1, T+1), income, 'g-', label="non-financial income", **p_args)
axes[0].plot(range(T), c, 'k-', label="consumption", **p_args)
axes[1].plot(range(T+1), np.zeros(T+1), 'k-')
axes[0].legend(ncol=2, **legend_args)

axes[1].plot(range(T+1), ap.flatten(), 'b-', label="assets", **p_args)
axes[1].plot(range(T), np.zeros(T), 'k-')
axes[1].legend(ncol=1, **legend_args)

plt.show()



########NEW FILE########
__FILENAME__ = solution_lqc_ex2
"""
An permanent income / life-cycle model with polynomial growth in income
over working life followed by a fixed retirement income.  The model is solved
by combining two LQ programming problems as described in the lecture.
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from lqcontrol import *

# == Model parameters == #
r       = 0.05
beta    = 1 / (1 + r)
T       = 60
K       = 40
c_bar   = 4
sigma   = 0.35
mu      = 4
q       = 1e4
s       = 1
m1      = 2 * mu / K
m2      = - mu / K**2

# == Formulate LQ problem 1 (retirement) == #
Q = 1
R = np.zeros((4, 4)) 
Rf = np.zeros((4, 4))
Rf[0, 0] = q
A = [[1 + r, s - c_bar, 0, 0], 
     [0,     1,      0,  0],
     [0,     1,      1,  0],
     [0,     1,      2,  1]]
B = [[-1],
     [0],
     [0],
     [0]]
C = [[0],
     [0],
     [0],
     [0]]

# == Initialize LQ instance for retired agent == #
lq_retired = LQ(Q, R, A, B, C, beta=beta, T=T-K, Rf=Rf)
# == Iterate back to start of retirement, record final value function == #
for i in range(T-K):
    lq_retired.update_values()
Rf2 = lq_retired.P

# == Formulate LQ problem 2 (working life) == #
R = np.zeros((4, 4)) 
A = [[1 + r, -c_bar, m1, m2], 
     [0,     1,      0,  0],
     [0,     1,      1,  0],
     [0,     1,      2,  1]]
B = [[-1],
     [0],
     [0],
     [0]]
C = [[sigma],
     [0],
     [0],
     [0]]

# == Set up working life LQ instance with terminal Rf from lq_retired == #
lq_working = LQ(Q, R, A, B, C, beta=beta, T=K, Rf=Rf2)

# == Simulate working state / control paths == #
x0 = (0, 1, 0, 0)
xp_w, up_w, wp_w = lq_working.compute_sequence(x0)
# == Simulate retirement paths (note the initial condition) == #
xp_r, up_r, wp_r = lq_retired.compute_sequence(xp_w[:, K]) 

# == Convert results back to assets, consumption and income == #
xp = np.column_stack((xp_w, xp_r[:, 1:]))
assets = xp[0, :]               # Assets

up = np.column_stack((up_w, up_r))
c = up.flatten() + c_bar    # Consumption

time = np.arange(1, K+1)
income_w = wp_w[0, 1:K+1] + m1 * time + m2 * time**2  # Income
income_r = np.ones(T-K) * s
income = np.concatenate((income_w, income_r))

# == Plot results == #
n_rows = 2
fig, axes = plt.subplots(n_rows, 1, figsize=(12, 10))

plt.subplots_adjust(hspace=0.5)
for i in range(n_rows):
    axes[i].grid()
    axes[i].set_xlabel(r'Time')
bbox = (0., 1.02, 1., .102)
legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
p_args = {'lw' : 2, 'alpha' : 0.7}

axes[0].plot(range(1, T+1), income, 'g-', label="non-financial income", **p_args)
axes[0].plot(range(T), c, 'k-', label="consumption", **p_args)
axes[1].plot(range(T+1), np.zeros(T+1), 'k-')
axes[0].legend(ncol=2, **legend_args)

axes[1].plot(range(T+1), assets, 'b-', label="assets", **p_args)
axes[1].plot(range(T), np.zeros(T), 'k-')
axes[1].legend(ncol=1, **legend_args)

plt.show()

########NEW FILE########
__FILENAME__ = solution_lqc_ex3
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: solution_lqc_ex3.py
An infinite horizon profit maximization problem for a monopolist with
adjustment costs.
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from lqcontrol import *

# == Model parameters == #
a0      = 5
a1      = 0.5
sigma   = 0.15
rho     = 0.9
gamma   = 1
beta    = 0.95
c       = 2
T       = 120

# == Useful constants == #
m0 = (a0 - c) / (2 * a1)
m1 = 1 / (2 * a1)

# == Formulate LQ problem == #
Q = gamma
R = [[a1, -a1, 0],
     [-a1, a1, 0],
     [0,   0,  0]]
A = [[rho, 0, m0 * (1 - rho)],
     [0,   1, 0],
     [0,   0, 1]]

B = [[0],
     [1],
     [0]]
C = [[m1 * sigma],
     [0],
     [0]]

lq = LQ(Q, R, A, B, C=C, beta=beta)

# == Simulate state / control paths == #
x0 = (m0, 2, 1)
xp, up, wp = lq.compute_sequence(x0, ts_length=150)
q_bar = xp[0, :] 
q     = xp[1, :]

# == Plot simulation results == #
fig, ax = plt.subplots(figsize=(10, 6.5))
ax.set_xlabel('Time')

# == Some fancy plotting stuff -- simplify if you prefer == #
bbox = (0., 1.01, 1., .101)
legend_args = {'bbox_to_anchor' : bbox, 'loc' : 3, 'mode' : 'expand'}
p_args = {'lw' : 2, 'alpha' : 0.6}

time = range(len(q))
ax.set_xlim(0, max(time))
ax.plot(time, q_bar, 'k-', lw=2, alpha=0.6, label=r'$\bar q_t$')
ax.plot(time, q, 'b-', lw=2, alpha=0.6, label=r'$q_t$')
ax.legend(ncol=2, **legend_args)
s = r'dynamics with $\gamma = {}$'.format(gamma)
ax.text(max(time) * 0.6, 1 * q_bar.max(), s, fontsize=14)

plt.show()

########NEW FILE########
__FILENAME__ = solution_lqramsey_ex1

import numpy as np
from numpy import array
from lqramsey import *

# == Parameters == #
beta = 1 / 1.05   
rho, mg = .95, .35
A = array([[0, 0, 0, rho, mg*(1-rho)],
           [1, 0, 0, 0, 0],
           [0, 1, 0, 0, 0],
           [0, 0, 1, 0, 0],
           [0, 0, 0, 0, 1]])
C = np.zeros((5, 1))
C[0, 0] = np.sqrt(1 - rho**2) * mg / 8
Sg = array((1, 0, 0, 0, 0)).reshape(1, 5)        
Sd = array((0, 0, 0, 0, 0)).reshape(1, 5)       
Sb = array((0, 0, 0, 0, 2.135)).reshape(1, 5)  # Chosen st. (Sc + Sg) * x0 = 1
Ss = array((0, 0, 0, 0, 0)).reshape(1, 5)

economy = Economy(beta=beta, 
        Sg=Sg, 
        Sd=Sd, 
        Sb=Sb, 
        Ss=Ss, 
        discrete=False, 
        proc=(A, C))

T = 50
path = compute_paths(T, economy)
gen_fig_1(path)



########NEW FILE########
__FILENAME__ = solution_lss_ex1

import numpy as np
import matplotlib.pyplot as plt
from lss import LSS

phi_0, phi_1, phi_2 = 1.1, 0.8, -0.8

A = [[1,     0,     0],
     [phi_0, phi_1, phi_2],
     [0,     1,     0]]
C = np.zeros((3, 1))
G = [0, 1, 0]

ar = LSS(A, C, G, mu_0=np.ones(3))
x, y = ar.simulate(ts_length=50)

fig, ax = plt.subplots(figsize=(8, 4.6))
y = y.flatten()
ax.plot(y, 'b-', lw=2, alpha=0.7)
ax.grid()
ax.set_xlabel('time')
ax.set_ylabel(r'$y_t$', fontsize=16)
plt.show()

########NEW FILE########
__FILENAME__ = solution_lss_ex2


import numpy as np
import matplotlib.pyplot as plt
from lss import LSS

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.2

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [[sigma], 
     [0], 
     [0], 
     [0]]
G = [1, 0, 0, 0]

ar = LSS(A, C, G, mu_0=np.ones(4))
x, y = ar.simulate(ts_length=200)

fig, ax = plt.subplots(figsize=(8, 4.6))
y = y.flatten()
ax.plot(y, 'b-', lw=2, alpha=0.7)
ax.grid()
ax.set_xlabel('time')
ax.set_ylabel(r'$y_t$', fontsize=16)
plt.show()

########NEW FILE########
__FILENAME__ = solution_lss_ex3

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from lss import LSS
import random

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.1

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [[sigma], 
     [0], 
     [0], 
     [0]]
G = [1, 0, 0, 0]

I = 20
T = 50
ar = LSS(A, C, G, mu_0=np.ones(4))
ymin, ymax = -0.5, 1.15

fig, ax = plt.subplots()

ax.set_ylim(ymin, ymax)
ax.set_xlabel(r'time', fontsize=16)
ax.set_ylabel(r'$y_t$', fontsize=16)

ensemble_mean = np.zeros(T)
for i in range(I):
    x, y = ar.simulate(ts_length=T)
    y = y.flatten()
    ax.plot(y, 'c-', lw=0.8, alpha=0.5)
    ensemble_mean = ensemble_mean + y

ensemble_mean = ensemble_mean / I
ax.plot(ensemble_mean, color='b', lw=2, alpha=0.8, label=r'$\bar y_t$')

m = ar.moment_sequence()
population_means = []
for t in range(T):
    mu_x, mu_y, Sigma_x, Sigma_y = m.next()
    population_means.append(mu_y)
ax.plot(population_means, color='g', lw=2, alpha=0.8, label=r'$G\mu_t$')
ax.legend(ncol=2)

plt.show()

########NEW FILE########
__FILENAME__ = solution_lss_ex4

import numpy as np
import matplotlib.pyplot as plt
from lss import LSS
import random

phi_1, phi_2, phi_3, phi_4 = 0.5, -0.2, 0, 0.5
sigma = 0.1

A = [[phi_1, phi_2, phi_3, phi_4],
     [1,     0,     0,     0],
     [0,     1,     0,     0],
     [0,     0,     1,     0]]
C = [[sigma], 
     [0], 
     [0], 
     [0]]
G = [1, 0, 0, 0]

T0 = 10
T1 = 50
T2 = 75
T4 = 100

ar = LSS(A, C, G, mu_0=np.ones(4))
ymin, ymax = -0.6, 0.6

fig, ax = plt.subplots(figsize=(8, 5))

ax.grid(alpha=0.4)
ax.set_ylim(ymin, ymax)
ax.set_ylabel(r'$y_t$', fontsize=16)
ax.vlines((T0, T1, T2), -1.5, 1.5)

ax.set_xticks((T0, T1, T2))
ax.set_xticklabels((r"$T$", r"$T'$", r"$T''$"), fontsize=14)

mu_x, mu_y, Sigma_x, Sigma_y = ar.stationary_distributions()
ar.mu_0 = mu_x
ar.Sigma_0 = Sigma_x

for i in range(80):
    rcolor = random.choice(('c', 'g', 'b'))
    x, y = ar.simulate(ts_length=T4)
    y = y.flatten()
    ax.plot(y, color=rcolor, lw=0.8, alpha=0.5)
    ax.plot((T0, T1, T2), (y[T0], y[T1], y[T2],), 'ko', alpha=0.5)

plt.show()

########NEW FILE########
__FILENAME__ = solution_mass_ex1
"""
Filename: solution_mass_ex1.py
Authors: David Evans, John Stachurski and Thomas J. Sargent
LastModified: 12/02/2014
"""

import numpy as np
import asset_pricing 

# == Define primitives == #
n = 5
P = 0.0125 * np.ones((n, n))
P += np.diag(0.95 - 0.0125 * np.ones(5))
s = np.array([1.05, 1.025, 1.0, 0.975, 0.95])
gamma = 2.0
beta = 0.94
zeta = 1.0

ap = asset_pricing.AssetPrices(beta, P, s, gamma)

v = ap.tree_price()
print "Lucas Tree Prices: ", v

v_consol = ap.consol_price(zeta)
print "Consol Bond Prices: ", v_consol

P_tilde = P * s**(1-gamma)
temp = beta * P_tilde.dot(v) - beta * P_tilde.dot(np.ones(n))
print "Should be 0: ",  v - temp 

p_s = 150.0
w_bar, w_bars = ap.call_option(zeta, p_s, T = [10,20,30])

########NEW FILE########
__FILENAME__ = solution_mass_ex2
from __future__ import division  # Omit for Python 3.x
import numpy as np
import matplotlib.pyplot as plt
from lucastree import lucas_tree, compute_price

fig, ax = plt.subplots()

ax.set_xlabel(r'$y$', fontsize=16)
ax.set_ylabel(r'price', fontsize=16)

for beta in (.95, 0.98):
    tree = lucas_tree(gamma=2, beta=beta, alpha=0.90, sigma=0.1)
    grid, price_vals = compute_price(tree)
    label = r'$\beta = {}$'.format(beta)
    ax.plot(grid, price_vals, lw=2, alpha=0.7, label=label)

ax.legend(loc='upper left')
ax.set_xlim(min(grid), max(grid))
plt.show()

########NEW FILE########
__FILENAME__ = solution_mc_ex1
"""
Compute the fraction of time that the worker spends unemployed,
and compare it to the stationary probability.
"""
import numpy as np
import matplotlib.pyplot as plt
import mc_tools

alpha = beta = 0.1
N = 10000
p = beta / (alpha + beta)

P = ((1 - alpha, alpha),   # Careful: P and p are distinct
     (beta, 1 - beta))
P = np.array(P)

fig, ax = plt.subplots()
ax.set_ylim(-0.25, 0.25)
ax.grid()
ax.hlines(0, 0, N, lw=2, alpha=0.6)  # Horizonal line at zero

for x0, col in ((0, 'blue'), (1, 'green')):
    # == Generate time series for worker that starts at x0 == #
    X = mc_tools.sample_path(P, x0, N)
    # == Compute fraction of time spent unemployed, for each n == #
    X_bar = (X == 0).cumsum() / (1 + np.arange(N, dtype=float)) 
    # == Plot == #
    ax.fill_between(range(N), np.zeros(N), X_bar - p, color=col, alpha=0.1)
    ax.plot(X_bar - p, color=col, label=r'$X_0 = \, {} $'.format(x0))
    ax.plot(X_bar - p, 'k-', alpha=0.6)  # Overlay in black--make lines clearer

ax.legend(loc='upper right')
plt.show()

########NEW FILE########
__FILENAME__ = solution_mc_ex2
"""
Return list of pages, ordered by rank
"""
from __future__ import print_function, division  # Omit if using Python 3.x
import numpy as np
import mc_tools
from operator import itemgetter
import re

infile = 'web_graph_data.txt'
alphabet = 'abcdefghijklmnopqrstuvwxyz'

n = 14 # Total number of web pages (nodes)

# == Create a matrix Q indicating existence of links == #
#  * Q[i, j] = 1 if there is a link from i to j
#  * Q[i, j] = 0 otherwise
Q = np.zeros((n, n), dtype=int)
f = open(infile, 'r')
edges = f.readlines()
f.close()
for edge in edges:
    from_node, to_node = re.findall('\w', edge)
    i, j = alphabet.index(from_node), alphabet.index(to_node)
    Q[i, j] = 1
# == Create the corresponding Markov matrix P == #
P = np.empty((n, n))
for i in range(n):
    P[i,:] = Q[i,:] / Q[i,:].sum()
# == Compute the stationary distribution r == #
r = mc_tools.compute_stationary(P)
ranked_pages = {alphabet[i] : r[i] for i in range(n)}
# == Print solution, sorted from highest to lowest rank == #
print('Rankings\n ***')
for name, rank in sorted(ranked_pages.iteritems(), key=itemgetter(1), reverse=1):
    print('{0}: {1:.4}'.format(name, rank))


########NEW FILE########
__FILENAME__ = solution_odu_ex1
"""
Solves the "Offer Distribution Unknown" model by iterating on a guess of the
reservation wage function.
"""
from scipy import interp
import numpy as np
from numpy import maximum as npmax
import matplotlib.pyplot as plt
from odu_vfi import searchProblem
from scipy.integrate import fixed_quad
from compute_fp import compute_fixed_point


def res_wage_operator(sp, phi):
    """
    Updates the reservation wage function guess phi via the operator Q.
    Returns the updated function Q phi, represented as the array new_phi.
    
        * sp is an instance of searchProblem, defined in odu_vfi
        * phi is a NumPy array with len(phi) = len(sp.pi_grid)

    """
    beta, c, f, g, q = sp.beta, sp.c, sp.f, sp.g, sp.q    # Simplify names
    phi_f = lambda p: interp(p, sp.pi_grid, phi)  # Turn phi into a function
    new_phi = np.empty(len(phi))
    for i, pi in enumerate(sp.pi_grid):
        def integrand(x):
            "Integral expression on right-hand side of operator"
            return npmax(x, phi_f(q(x, pi))) * (pi * f(x) + (1 - pi) * g(x))
        integral, error = fixed_quad(integrand, 0, sp.w_max)
        new_phi[i] = (1 - beta) * c + beta * integral
    return new_phi


if __name__ == '__main__':  # If module is run rather than imported

    sp = searchProblem(pi_grid_size=50)
    phi_init = np.ones(len(sp.pi_grid)) 
    w_bar = compute_fixed_point(res_wage_operator, sp, phi_init)

    fig, ax = plt.subplots()
    ax.plot(sp.pi_grid, w_bar, linewidth=2, color='black')
    ax.set_ylim(0, 2)
    ax.grid(axis='x', linewidth=0.25, linestyle='--', color='0.25')
    ax.grid(axis='y', linewidth=0.25, linestyle='--', color='0.25')
    ax.fill_between(sp.pi_grid, 0, w_bar, color='blue', alpha=0.15)
    ax.fill_between(sp.pi_grid, w_bar, 2, color='green', alpha=0.15)
    ax.text(0.42, 1.2, 'reject')
    ax.text(0.7, 1.8, 'accept')
    plt.show()

########NEW FILE########
__FILENAME__ = solution_odu_ex2
from scipy import interp
import numpy as np
import matplotlib.pyplot as plt
from odu_vfi import searchProblem
from solution_odu_ex1 import res_wage_operator
from compute_fp import compute_fixed_point

# Set up model and compute the function w_bar
sp = searchProblem(pi_grid_size=50, F_a=1, F_b=1)
pi_grid, f, g, F, G = sp.pi_grid, sp.f, sp.g, sp.F, sp.G
phi_init = np.ones(len(sp.pi_grid)) 
w_bar_vals = compute_fixed_point(res_wage_operator, sp, phi_init)
w_bar = lambda x: interp(x, pi_grid, w_bar_vals)


class Agent:
    """
    Holds the employment state and beliefs of an individual agent.
    """

    def __init__(self, pi=1e-3):
        self.pi = pi
        self.employed = 1

    def update(self, H):
        "Update self by drawing wage offer from distribution H."
        if self.employed == 0:
            w = H.rvs()
            if w >= w_bar(self.pi):
                self.employed = 1
            else:
                self.pi = 1.0 / (1 + ((1 - self.pi) * g(w)) / (self.pi * f(w)))


num_agents = 5000
separation_rate = 0.025  # Fraction of jobs that end in each period 
separation_num = int(num_agents * separation_rate)
agent_indices = range(num_agents)
agents = [Agent() for i in range(num_agents)]
sim_length = 600
H = G  # Start with distribution G
change_date = 200  # Change to F after this many periods

unempl_rate = []
for i in range(sim_length):
    print "date = ", i
    if i == change_date:
        H = F
    # Randomly select separation_num agents and set employment status to 0
    np.random.shuffle(agent_indices)
    separation_list = agent_indices[:separation_num]
    for agent_index in separation_list:
        agents[agent_index].employed = 0
    # Update agents
    for agent in agents:
        agent.update(H)
    employed = [agent.employed for agent in agents]
    unempl_rate.append(1 - np.mean(employed))

fig, ax = plt.subplots()
ax.plot(unempl_rate, lw=2, alpha=0.8, label='unemployment rate')
ax.axvline(change_date, color="red")
ax.legend()
plt.show()

########NEW FILE########
__FILENAME__ = solution_og_ex1
import matplotlib.pyplot as plt
from optgrowth import growthModel, bellman_operator, compute_greedy
from compute_fp import compute_fixed_point

alpha, beta = 0.65, 0.95
gm = growthModel() 
true_sigma = (1 - alpha * beta) * gm.grid**alpha
w = 5 * gm.u(gm.grid) - 25  # Initial condition

fig, ax = plt.subplots(3, 1, figsize=(8, 10))

for i, n in enumerate((2, 4, 6)):
    ax[i].set_ylim(0, 1)
    ax[i].set_xlim(0, 2)
    ax[i].set_yticks((0, 1))
    ax[i].set_xticks((0, 2))

    v_star = compute_fixed_point(bellman_operator, gm, w, max_iter=n)
    sigma = compute_greedy(gm, v_star)

    ax[i].plot(gm.grid, sigma, 'b-', lw=2, alpha=0.8, label='approximate optimal policy')
    ax[i].plot(gm.grid, true_sigma, 'k-', lw=2, alpha=0.8, label='true optimal policy')
    ax[i].legend(loc='upper left')
    ax[i].set_title('{} value function iterations'.format(n))

plt.show()

########NEW FILE########
__FILENAME__ = solution_og_ex2
import matplotlib.pyplot as plt
import numpy as np
from scipy import interp
from optgrowth import growthModel, bellman_operator, compute_greedy
from compute_fp import compute_fixed_point

gm = growthModel() 
w = 5 * gm.u(gm.grid) - 25  # To be used as an initial condition
discount_factors = (0.9, 0.94, 0.98)
series_length = 25

fig, ax = plt.subplots()
ax.set_xlabel("time")
ax.set_ylabel("capital")

for beta in discount_factors:

    # Compute the optimal policy given the discount factor
    gm.beta = beta
    v_star = compute_fixed_point(bellman_operator, gm, w, max_iter=20)
    sigma = compute_greedy(gm, v_star)

    # Compute the corresponding time series for capital
    k = np.empty(series_length)
    k[0] = 0.1
    sigma_function = lambda x: interp(x, gm.grid, sigma)
    for t in range(1, series_length):
        k[t] = gm.f(k[t-1]) - sigma_function(k[t-1])
    ax.plot(k, 'o-', lw=2, alpha=0.75, label=r'$\beta = {}$'.format(beta))

ax.legend(loc='lower right')
plt.show()



########NEW FILE########
__FILENAME__ = solution_oop_ex1
class ecdf:

    def __init__(self, observations):
        self.observations = observations

    def __call__(self, x):
        counter = 0.0
        for obs in self.observations:
            if obs <= x:
                counter += 1
        return counter / len(self.observations)


########NEW FILE########
__FILENAME__ = solution_oop_ex2
class Polynomial:

    def __init__(self, coefficients):
        """
        Creates an instance of the Polynomial class representing 

            p(x) = a_0 x^0 + ... + a_N x^N, 
            
        where a_i = coefficients[i].
        """
        self.coefficients = coefficients

    def __call__(self, x):
        "Evaluate the polynomial at x."
        y = 0
        for i, a in enumerate(self.coefficients):
            y += a * x**i  
        return y

    def differentiate(self):
        "Reset self.coefficients to those of p' instead of p."
        new_coefficients = []
        for i, a in enumerate(self.coefficients):
            new_coefficients.append(i * a)
        # Remove the first element, which is zero
        del new_coefficients[0]  
        # And reset coefficients data to new values
        self.coefficients = new_coefficients


########NEW FILE########
__FILENAME__ = solution_pbe_ex1
def factorial(n):
    k = 1
    for i in range(n):
        k = k * (i + 1)
    return k

########NEW FILE########
__FILENAME__ = solution_pbe_ex2
from random import uniform

def binomial_rv(n, p):
    count = 0
    for i in range(n):
        U = uniform(0, 1)
        if U < p:
            count = count + 1    # Or count += 1
    print count


########NEW FILE########
__FILENAME__ = solution_pbe_ex3
from __future__ import division  # Omit if using Python 3.x
from random import uniform
from math import sqrt

n = 100000

count = 0
for i in range(n):
    u, v = uniform(0, 1), uniform(0, 1)
    d = sqrt((u - 0.5)**2 + (v - 0.5)**2)
    if d < 0.5:
        count += 1

area_estimate = count / n

print area_estimate * 4  # dividing by radius**2


########NEW FILE########
__FILENAME__ = solution_pbe_ex4
from random import uniform

payoff = 0
count = 0

for i in range(10):
    U = uniform(0, 1)
    count = count + 1 if U < 0.5 else 0
    if count == 3:
        payoff = 1

print payoff

########NEW FILE########
__FILENAME__ = solution_pbe_ex5
from pylab import plot, show
from random import normalvariate

alpha = 0.9
ts_length = 200
current_x = 0

x_values = []
for i in range(ts_length):
    x_values.append(current_x)
    current_x = alpha * current_x + normalvariate(0, 1)
plot(x_values, 'b-')
show()


########NEW FILE########
__FILENAME__ = solution_pbe_ex6
from pylab import plot, show, legend
from random import normalvariate

alphas = [0.0, 0.8, 0.98]
ts_length = 200

for alpha in alphas:
    x_values = []
    current_x = 0
    for i in range(ts_length):
        x_values.append(current_x)
        current_x = alpha * current_x + normalvariate(0, 1)
    plot(x_values, label='alpha = ' + str(alpha))
legend()
show()



########NEW FILE########
__FILENAME__ = solution_pd_ex1
import numpy as np
import pandas as pd
import datetime as dt
import pandas.io.data as web
import matplotlib.pyplot as plt

ticker_list = {'INTC': 'Intel',
               'MSFT': 'Microsoft',
               'IBM': 'IBM',
               'BHP': 'BHP',
               'RSH': 'RadioShack',
               'TM': 'Toyota',
               'AAPL': 'Apple',
               'AMZN': 'Amazon',
               'BA': 'Boeing',
               'QCOM': 'Qualcomm',
               'KO': 'Coca-Cola',
               'GOOG': 'Google',
               'SNE': 'Sony',
               'PTR': 'PetroChina'}

start = dt.datetime(2013, 1, 1)
end = dt.datetime.today()

price_change = {}

for ticker in ticker_list:
    prices = web.DataReader(ticker, 'yahoo', start, end)
    closing_prices = prices['Close']
    change = 100 * (closing_prices[-1] - closing_prices[0]) / closing_prices[0]
    name = ticker_list[ticker]
    price_change[name] = change

pc = pd.Series(price_change)
pc.sort()
fig, ax = plt.subplots()
pc.plot(kind='bar', ax=ax)
plt.show()


########NEW FILE########
__FILENAME__ = solution_ree_ex1
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: solution_ree_ex1.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski
Solves an exercise from the rational expectations module
"""
from __future__ import print_function
import numpy as np
from lqcontrol import LQ


# == Model parameters == #

a0      = 100
a1      = 0.05
beta    = 0.95
gamma   = 10.0

# == Beliefs == #

kappa0  = 95.5
kappa1  = 0.95

# == Formulate the LQ problem == #

A = np.array([[1, 0, 0], [0, kappa1, kappa0], [0, 0, 1]])
B = np.array([1, 0, 0])
B.shape = 3, 1
R = np.array([[0, -a1/2, a0/2], [-a1/2, 0, 0], [a0/2, 0, 0]])
Q = -0.5 * gamma

# == Solve for the optimal policy == #

lq = LQ(Q, R, A, B, beta=beta)
P, F, d = lq.stationary_values()
F = F.flatten()
out1 = "F = [{0:.3f}, {1:.3f}, {2:.3f}]".format(F[0], F[1], F[2])
h0, h1, h2 = -F[2], 1 - F[0], -F[1]
out2 = "(h0, h1, h2) = ({0:.3f}, {1:.3f}, {2:.3f})".format(h0, h1, h2)

print(out1)
print(out2)

########NEW FILE########
__FILENAME__ = solution_ree_ex2
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: solution_ree_ex2.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski
Solves an exercise from the rational expectations module
"""
from __future__ import print_function
import numpy as np
from lqcontrol import LQ
from solution_ree_ex1 import beta, R, Q, B

candidates = (
          (94.0886298678, 0.923409232937),
          (93.2119845412, 0.984323478873),
          (95.0818452486, 0.952459076301)
             )

for kappa0, kappa1 in candidates:

    # == Form the associated law of motion == #
    A = np.array([[1, 0, 0], [0, kappa1, kappa0], [0, 0, 1]])

    # == Solve the LQ problem for the firm == #
    lq = LQ(Q, R, A, B, beta=beta)
    P, F, d = lq.stationary_values()
    F = F.flatten()
    h0, h1, h2 = -F[2], 1 - F[0], -F[1]

    # == Test the equilibrium condition == #
    if np.allclose((kappa0, kappa1), (h0, h1 + h2)):
        print('Equilibrium pair =', kappa0, kappa1)
        print('(h0, h1, h2) = ', h0, h1, h2)
        break



########NEW FILE########
__FILENAME__ = solution_ree_ex3
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: solution_ree_ex3.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski
Solves an exercise from the rational expectations module
"""

from __future__ import print_function
import numpy as np
from lqcontrol import LQ
from solution_ree_ex1 import a0, a1, beta, gamma

# == Formulate the planner's LQ problem == #

A = np.array([[1, 0], [0, 1]])
B = np.array([[1], [0]])
R = -np.array([[a1 / 2, -a0 / 2], [-a0 / 2, 0]])
Q = - gamma / 2

# == Solve for the optimal policy == #

lq = LQ(Q, R, A, B, beta=beta)
P, F, d = lq.stationary_values()

# == Print the results == #

F = F.flatten()
kappa0, kappa1 = -F[1], 1 - F[0]
print(kappa0, kappa1)

########NEW FILE########
__FILENAME__ = solution_ree_ex4
"""
Origin: QE by John Stachurski and Thomas J. Sargent
Filename: solution_ree_ex4.py
Authors: Chase Coleman, Spencer Lyon, Thomas Sargent, John Stachurski
Solves an exercise from the rational expectations module
"""

from __future__ import print_function
import numpy as np
from lqcontrol import LQ
from solution_ree_ex1 import a0, a1, beta, gamma

A = np.array([[1, 0], [0, 1]])
B = np.array([[1], [0]])
R = - np.array([[a1, -a0 / 2], [-a0 / 2, 0]])
Q = - gamma / 2

lq = LQ(Q, R, A, B, beta=beta)
P, F, d = lq.stationary_values()

F = F.flatten()
m0, m1 = -F[1], 1 - F[0]
print(m0, m1)

########NEW FILE########
__FILENAME__ = solution_shortpath
"""
Source: QE by John Stachurski and Thomas J. Sargent
Filename: solution_shortpath.py
Authors: John Stachurksi and Thomas J. Sargent
LastModified: 11/08/2013
"""

def read_graph():
    """ Read in the graph from the data file.  The graph is stored
    as a dictionary, where the keys are the nodes, and the values
    are a list of pairs (d, c), where d is a node and c is a number.
    If (d, c) is in the list for node n, then d can be reached from
    n at cost c.
    """
    graph = {}
    infile = open('graph.txt')
    for line in infile:
        elements = line.split(',')
        node = elements.pop(0).strip()
        graph[node] = []
        if node != 'node99':
            for element in elements:
                destination, cost = element.split()
                graph[node].append((destination.strip(), float(cost)))
    infile.close()
    return graph

def update_J(J, graph):
    "The Bellman operator."
    next_J = {}
    for node in graph:
        if node == 'node99':
            next_J[node] = 0
        else:
            next_J[node] = min(cost + J[dest] for dest, cost in graph[node])
    return next_J

def print_best_path(J, graph):
    """ Given a cost-to-go function, computes the best path.  At each node n, 
    the function prints the current location, looks at all nodes that can be 
    reached from n, and moves to the node m which minimizes c + J[m], where c 
    is the cost of moving to m.
    """
    sum_costs = 0
    current_location = 'node0'
    while current_location != 'node99':
        print current_location
        running_min = 1e100  # Any big number
        for destination, cost in graph[current_location]:
            cost_of_path = cost + J[destination]
            if cost_of_path < running_min:
                running_min = cost_of_path
                minimizer_cost = cost
                minimizer_dest = destination
        current_location = minimizer_dest
        sum_costs += minimizer_cost

    print 'node99'
    print
    print 'Cost: ', sum_costs


## Main loop

graph = read_graph()
M = 1e10
J = {}
for node in graph:
    J[node] = M
J['node99'] = 0

while 1:
    next_J = update_J(J, graph)
    if next_J == J:
        break
    else:
        J = next_J
print_best_path(J, graph)


########NEW FILE########
__FILENAME__ = solution_statd_ex1
"""
Look ahead estimation of a TAR stationary density, where the TAR model is

    X' = theta |X| + sqrt(1 - theta^2) xi

and xi is standard normal.  Try running at n = 10, 100, 1000, 10000 to get an
idea of the speed of convergence.
"""
import numpy as np
from scipy.stats import norm, gaussian_kde
import matplotlib.pyplot as plt
from lae import lae

phi = norm()
n = 500
theta = 0.8
# == Frequently used constants == #
d = np.sqrt(1 - theta**2) 
delta = theta / d

def psi_star(y):
    "True stationary density of the TAR Model"
    return 2 * norm.pdf(y) * norm.cdf(delta * y) 

def p(x, y):
        "Stochastic kernel for the TAR model."
        return phi.pdf((y - theta * np.abs(x)) / d) / d

Z = phi.rvs(n)
X = np.empty(n)
for t in range(n-1):
    X[t+1] = theta * np.abs(X[t]) + d * Z[t]
psi_est = lae(p, X)
k_est = gaussian_kde(X)

fig, ax = plt.subplots()
ys = np.linspace(-3, 3, 200)
ax.plot(ys, psi_star(ys), 'b-', lw=2, alpha=0.6, label='true')
ax.plot(ys, psi_est(ys), 'g-', lw=2, alpha=0.6, label='look ahead estimate')
ax.plot(ys, k_est(ys), 'k-', lw=2, alpha=0.6, label='kernel based estimate')
ax.legend(loc='upper left')
plt.show()

########NEW FILE########
__FILENAME__ = solution_statd_ex2
import numpy as np
from scipy.stats import lognorm, beta
import matplotlib.pyplot as plt
from lae import lae

# == Define parameters == #
s = 0.2
delta = 0.1
a_sigma = 0.4       # A = exp(B) where B ~ N(0, a_sigma)
alpha = 0.4         # f(k) = k^{\alpha}

phi = lognorm(a_sigma) 

def p(x, y):
    "Stochastic kernel, vectorized in x.  Both x and y must be positive."
    d = s * x**alpha
    return phi.pdf((y - (1 - delta) * x) / d) / d

n = 1000     # Number of observations at each date t
T = 40       # Compute density of k_t at 1,...,T

fig, axes = plt.subplots(2, 2)
axes = axes.flatten()
xmax = 6.5

for i in range(4):
    ax = axes[i] 
    ax.set_xlim(0, xmax)
    psi_0 = beta(5, 5, scale=0.5, loc=i*2)  # Initial distribution

    # == Generate matrix s.t. t-th column is n observations of k_t == #
    k = np.empty((n, T))
    A = phi.rvs((n, T))
    k[:, 0] = psi_0.rvs(n)
    for t in range(T-1):
        k[:, t+1] = s * A[:,t] * k[:, t]**alpha + (1 - delta) * k[:, t]

    # == Generate T instances of lae using this data, one for each t == #
    laes = [lae(p, k[:, t]) for t in range(T)]

    ygrid = np.linspace(0.01, xmax, 150)
    greys = [str(g) for g in np.linspace(0.0, 0.8, T)]
    greys.reverse()
    for psi, g in zip(laes, greys):
        ax.plot(ygrid, psi(ygrid), color=g, lw=2, alpha=0.6)
    #ax.set_xlabel('capital')
    #title = r'Density of $k_1$ (lighter) to $k_T$ (darker) for $T={}$'
    #ax.set_title(title.format(T))

plt.show()


########NEW FILE########
