__FILENAME__ = task
colors = [['red', 'green', 'green', 'red' , 'red'],
          ['red', 'red', 'green', 'red', 'red'],
          ['red', 'red', 'green', 'green', 'red'],
          ['red', 'red', 'red', 'red', 'red']]

measurements = ['green', 'green', 'green', 'green', 'green']


motions = [[0, 0], [0, 1], [1, 0], [1, 0], [0, 1]]

sensor_right = 0.7

p_move = 0.8

def show(p):
    for i in range(len(p)):
        print p[i]


def calculate():

    #DO NOT USE IMPORT
    #ENTER CODE BELOW HERE
    #ANY CODE ABOVE WILL CAUSE
    #HOMEWORK TO BE GRADED
    #INCORRECT
  
    p = []

    #Your probability array must be printed 
    #with the following code.

    show(p)
    return p


########NEW FILE########
__FILENAME__ = test
import unittest
import task

class TestSequenceFunctions(unittest.TestCase):
    def failUnlessArraysAlmostEqual(self, first, second, places=7, msg=None):
        """Fail if the two arrays are unequal as determined by their
           difference rounded to the given number of decimal places
           (default 7) and comparing to zero.

           Note that decimal places (from zero) are usually not the same
           as significant digits (measured from the most signficant digit).
        """
        if (len(first) != len(second)):
            raise self.failureException, \
              (msg or '%r != %r because they have unequal lengths %d & %d', \
                  (first, second, len(first), len(second)))

        for i in range(len(first)):
            if isinstance(first[i], list):
                self.failUnlessArraysAlmostEqual(first[i], second[i], places, msg)
            elif round(abs(second[i]-first[i]), places) != 0:
                raise self.failureException, \
                (msg or '%r != %r within %r places' % (first, second, places))

    # Synonym methods
    assertArrayAlmostEqual = assertArrayAlmostEquals = failUnlessArraysAlmostEqual

    def test_dataset1(self):
        # ARRANGE
        expected_result = [[0, 0, 0],
                           [0, 1, 0],
                           [0, 0, 0]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'green'],
                       ['green', 'green', 'green']]
        task.measurements = ['red']
        task.motions = [[0, 0]]
        task.sensor_right = 1.0
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result)

    def test_dataset2(self):
      # ARRANGE
        expected_result = [[0, 0, 0],
                           [0, 0.5, 0.5],
                           [0, 0, 0]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red']
        task.motions = [[0, 0]]
        task.sensor_right = 1.0
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result)

    def test_dataset3(self):
        # ARRANGE
        expected_result = [[0.06666, 0.06666, 0.06666],
                           [0.06666, 0.26666, 0.26666],
                           [0.06666, 0.06666, 0.06666]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red']
        task.motions = [[0, 0]]
        task.sensor_right = 0.8
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset4(self):
        # ARRANGE
        expected_result = [[0.03333, 0.03333, 0.03333],
                           [0.13333, 0.13333, 0.53333],
                           [0.03333, 0.03333, 0.03333]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [0, 1]]
        task.sensor_right = 0.8
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset5(self):
        # ARRANGE
        expected_result = [[0.0, 0.0, 0.0],
                           [0.0, 0.0, 1.0],
                           [0.0, 0.0, 0.0]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [0, 1]]
        task.sensor_right = 1.0
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset6(self):
        # ARRANGE
        expected_result = [[0.02898, 0.02898, 0.02898],
                           [0.07246, 0.28985, 0.46376],
                           [0.02898, 0.02898, 0.02898]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [0, 1]]
        task.sensor_right = 0.8
        task.p_move = 0.5

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset7(self):
        # ARRANGE
        expected_result = [[0.0, 0.0, 0.0],
                           [0.0, 0.33333, 0.66666],
                           [0.0, 0.0, 0.0]]

        task.colors = [['green', 'green', 'green'],
                       ['green', 'red', 'red'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [0, 1]]
        task.sensor_right = 1.0
        task.p_move = 0.5

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)


    def test_dataset8(self):
        # ARRANGE
        expected_result = [[0.01105, 0.02464, 0.06799, 0.04472, 0.024651],
                           [0.00715, 0.01017, 0.08696, 0.07988, 0.00935],
                           [0.00739, 0.00894, 0.11272, 0.35350, 0.04065],
                           [0.00910, 0.00715, 0.01434, 0.04313, 0.03642]]

        task.colors = [['red', 'green', 'green', 'red','red'],
                       ['red', 'red', 'green', 'red', 'red'],
                       ['red', 'red', 'green', 'green', 'red'],
                       ['red', 'red', 'red', 'red', 'red']]
        task.measurements = ['green', 'green', 'green', 'green', 'green']
        task.motions = [[0, 0], [0, 1], [1, 0], [1, 0], [0, 1]]
        task.sensor_right = 0.7
        task.p_move = 0.8

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset9(self):
        # ARRANGE
        expected_result = [[0.0, 0.0, 0.0],
                           [1.0, 0.0, 0.0],
                           [0.0, 0.0, 0.0]]

        task.colors = [['green', 'green', 'green'],
                       ['red', 'red', 'green'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [0, -1]]
        task.sensor_right = 1.0
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

    def test_dataset10(self):
        # ARRANGE
        expected_result = [[0.0, 1.0, 0.0],
                           [0.0, 0.0, 0.0],
                           [0.0, 0.0, 0.0]]

        task.colors = [['green', 'red', 'green'],
                       ['green', 'red', 'green'],
                       ['green', 'green', 'green']]
        task.measurements = ['red', 'red']
        task.motions = [[0, 0], [-1, 0]]
        task.sensor_right = 1.0
        task.p_move = 1.0

        # ACT
        actual_result = task.calculate()

        # ASSERT
        self.assertArrayAlmostEquals(expected_result, actual_result, 4)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = task
# Fill in the matrices P, F, H, R and I at the bottom

from math import *

class matrix:
    
    # implements basic operations of a matrix class
    
    def __init__(self, value):
        self.value = value
        self.dimx = len(value)
        self.dimy = len(value[0])
        if value == [[]]:
            self.dimx = 0
    
    def zero(self, dimx, dimy):
        # check if valid dimensions
        if dimx < 1 or dimy < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx = dimx
            self.dimy = dimy
            self.value = [[0 for row in range(dimy)] for col in range(dimx)]
    
    def identity(self, dim):
        # check if valid dimension
        if dim < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx = dim
            self.dimy = dim
            self.value = [[0 for row in range(dim)] for col in range(dim)]
            for i in range(dim):
                self.value[i][i] = 1
    
    def show(self):
        for i in range(self.dimx):
            print self.value[i]
        print ' '
    
    def __add__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimy != other.dimy:
            raise ValueError, "Matrices must be of equal dimensions to add"
        else:
            # add if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] + other.value[i][j]
            return res
    
    def __sub__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimy != other.dimy:
            raise ValueError, "Matrices must be of equal dimensions to subtract"
        else:
            # subtract if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] - other.value[i][j]
            return res
    
    def __mul__(self, other):
        # check if correct dimensions
        if self.dimy != other.dimx:
            raise ValueError, "Matrices must be m*n and n*p to multiply"
        else:
            # subtract if correct dimensions
            res = matrix([[]])
            res.zero(self.dimx, other.dimy)
            for i in range(self.dimx):
                for j in range(other.dimy):
                    for k in range(self.dimy):
                        res.value[i][j] += self.value[i][k] * other.value[k][j]
            return res
    
    def transpose(self):
        # compute transpose
        res = matrix([[]])
        res.zero(self.dimy, self.dimx)
        for i in range(self.dimx):
            for j in range(self.dimy):
                res.value[j][i] = self.value[i][j]
        return res
    
    # Thanks to Ernesto P. Adorio for use of Cholesky and CholeskyInverse functions
    
    def Cholesky(self, ztol=1.0e-5):
        # Computes the upper triangular Cholesky factorization of
        # a positive definite matrix.
        res = matrix([[]])
        res.zero(self.dimx, self.dimx)
        
        for i in range(self.dimx):
            S = sum([(res.value[k][i])**2 for k in range(i)])
            d = self.value[i][i] - S
            if abs(d) < ztol:
                res.value[i][i] = 0.0
            else:
                if d < 0.0:
                    raise ValueError, "Matrix not positive-definite"
                res.value[i][i] = sqrt(d)
            for j in range(i+1, self.dimx):
                S = sum([res.value[k][i] * res.value[k][j] for k in range(self.dimx)])
                if abs(S) < ztol:
                    S = 0.0
                res.value[i][j] = (self.value[i][j] - S)/res.value[i][i]
        return res
    
    def CholeskyInverse(self):
        # Computes inverse of matrix given its Cholesky upper Triangular
        # decomposition of matrix.
        res = matrix([[]])
        res.zero(self.dimx, self.dimx)
        
        # Backward step for inverse.
        for j in reversed(range(self.dimx)):
            tjj = self.value[j][j]
            S = sum([self.value[j][k]*res.value[j][k] for k in range(j+1, self.dimx)])
            res.value[j][j] = 1.0/tjj**2 - S/tjj
            for i in reversed(range(j)):
                res.value[j][i] = res.value[i][j] = -sum([self.value[i][k]*res.value[k][j] for k in range(i+1, self.dimx)])/self.value[i][i]
        return res
    
    def inverse(self):
        aux = self.Cholesky()
        res = aux.CholeskyInverse()
        return res
    
    def __repr__(self):
        return repr(self.value)


########################################

def calculate(measurements, initial_xy):
  dt = 0.1

  x = matrix([[initial_xy[0]], [initial_xy[1]], [0.], [0.]]) # initial state (location and velocity)
  u = matrix([[0.], [0.], [0.], [0.]]) # external motion

  ### fill this in: ###
  P =  # initial uncertainty
  F =  # next state function
  H =  # measurement function
  R =  # measurement uncertainty
  I =  # identity matrix

  def filter(x, P):
    for n in range(len(measurements)):
      
      # prediction
      x = (F * x) + u
      P = F * P * F.transpose()
      
      # measurement update
      Z = matrix([measurements[n]])
      y = Z.transpose() - (H * x)
      S = H * P * H.transpose() + R
      K = P * H.transpose() * S.inverse()
      x = x + (K * y)
      P = (I - (K * H)) * P
    return x, P
    
  return filter(x, P)

########NEW FILE########
__FILENAME__ = test

import unittest
import task
from task import matrix

class TestSequenceFunctions(unittest.TestCase):
  def failUnlessArraysAlmostEqual(self, first, second, places=7, msg=None):
      """Fail if the two arrays are unequal as determined by their
         difference rounded to the given number of decimal places
         (default 7) and comparing to zero.

         Note that decimal places (from zero) are usually not the same
         as significant digits (measured from the most signficant digit).
      """
      if (len(first) != len(second)):
          raise self.failureException, \
              (msg or '%r != %r because they have unequal lengths %d & %d', \
                  (first, second, len(first), len(second)))

      for i in range(len(first)):
          if isinstance(first[i], list):
            self.failUnlessArraysAlmostEqual(first[i], second[i], places, msg)
          elif round(abs(second[i]-first[i]), places) != 0:
              raise self.failureException, \
                (msg or '%r != %r within %r places' % (first, second, places))
  
  # Synonym methods
  assertArrayAlmostEqual = assertArrayAlmostEquals = failUnlessArraysAlmostEqual

  def test_dataset1(self):
    # ARRANGE
    measurements = [[5., 10.], [6., 8.], [7., 6.], [8., 4.], [9., 2.], [10., 0.]]
    initial_xy = [4., 12.]
    expected_x = matrix([[9.9993407317877168],[0.001318536424568617],[9.9989012196461928],[-19.997802439292386]])
    expected_P = matrix([[0.039556092737061982, 0.0, 0.06592682122843721, 0.0], [0.0, 0.039556092737061982, 0.0, 0.06592682122843721], [0.065926821228437182, 0.0, 0.10987803538073201, 0.0], [0.0, 0.065926821228437182, 0.0, 0.10987803538073201]])

    # ACT
    x, P = task.calculate(measurements, initial_xy)

    # ASSERT
    self.assertArrayAlmostEquals(expected_x.value, x.value)
    self.assertArrayAlmostEquals(expected_P.value, P.value)
    
  def test_dataset2(self):
    # ARRANGE
    measurements = [[1., 4.], [6., 0.], [11., -4.], [16., -8.]]
    initial_xy = [-4., 8.]
    expected_x = matrix([[15.993335554815062], [-7.9946684438520501], [49.983338887037647], [-39.986671109630123]])

    # ACT
    x, P = task.calculate(measurements, initial_xy)

    # ASSERT
    self.assertArrayAlmostEquals(expected_x.value, x.value)
    
  def test_dataset3(self):
    # ARRANGE
    measurements = [[1., 17.], [1., 15.], [1., 13.], [1., 11.]]
    initial_xy = [1., 19.]
    expected_x = matrix([[1.0], [11.002665778073975], [0.0], [-19.993335554815054]])
    expected_P = matrix([[0.053315561479506911, 0.0, 0.13328890369876803, 0.0], [0.0, 0.053315561479506911, 0.0, 0.13328890369876803], [0.13328890369876789, 0.0, 0.33322225924692717, 0.0], [0.0, 0.13328890369876789, 0.0, 0.333222259246027171]])

    # ACT
    x, P = task.calculate(measurements, initial_xy)

    # ASSERT
    self.assertArrayAlmostEquals(expected_x.value, x.value)
    self.assertArrayAlmostEquals(expected_P.value, P.value)
    
  def test_dataset4(self):
    # ARRANGE
    measurements = [[2., 17.], [0., 15.], [2., 13.], [0., 11.]]
    initial_xy = [1., 19.]
    expected_x = matrix([[0.73342219260246477], [11.002665778073975], [-0.66644451849384057], [-19.993335554815054]])
    expected_P = matrix([[0.053315561479506911, 0.0, 0.13328890369876803, 0.0], [0.0, 0.053315561479506911, 0.0, 0.13328890369876803], [0.13328890369876789, 0.0, 0.33322225924692717, 0.0], [0.0, 0.13328890369876789, 0.0, 0.333222259246027171]])

    # ACT
    x, P = task.calculate(measurements, initial_xy)

    # ASSERT
    self.assertArrayAlmostEquals(expected_x.value, x.value)
    self.assertArrayAlmostEquals(expected_P.value, P.value)

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = task

# --------------
# USER INSTRUCTIONS
#
# Write a function in the class robot called move()
#
# that takes self and a motion vector (this
# motion vector contains a steering* angle and a
# distance) as input and returns an instance of the class
# robot with the appropriate x, y, and orientation
# for the given motion.
#
# *steering is defined in the video
# which accompanies this problem.
#
# For now, please do NOT add noise to your move function.
#
# Please do not modify anything except where indicated
# below.
#
# There are test cases which you are free to use at the
# bottom. If you uncomment them for testing, make sure you
# re-comment them before you submit.


# --------
# 
# the "world" has 4 landmarks.
# the robot's initial coordinates are somewhere in the square
# represented by the landmarks.
#

from math import *
import random

landmarks  = [[0.0, 100.0], [0.0, 0.0], [100.0, 0.0], [100.0, 100.0]] # position of 4 landmarks
world_size = 100.0 # world is NOT cyclic. Robot is allowed to travel "out of bounds"
max_steering_angle = pi/4
tolerance = 0.001

# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------

    # init: 
    # creates robot and initializes location/orientation 
    #

    def __init__(self, length = 10.0):
        self.x = random.random() * world_size # initial x position
        self.y = random.random() * world_size # initial y position
        self.orientation = random.random() * 2.0 * pi # initial orientation
        self.length = length # length of robot
        self.bearing_noise  = 0.0 # initialize bearing noise to zero
        self.steering_noise = 0.0 # initialize steering noise to zero
        self.distance_noise = 0.0 # initialize distance noise to zero
    
    def __repr__(self):
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), str(self.orientation))
    # --------
    # set: 
    # sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):

        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)


    # --------
    # set_noise: 
    # sets the noise parameters
    #

    def set_noise(self, new_b_noise, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.bearing_noise  = float(new_b_noise)
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)
    
    ############# ONLY ADD/MODIFY CODE BELOW HERE ###################

    # --------
    # move:
    #   move along a section of a circular path according to motion
    #
    
    def move(self, motion): # Do not change the name of this function

        # ENTER YOUR CODE HERE
        
        return result # make sure your move function returns an instance
                      # of the robot class with the correct coordinates.
                      
    ############## ONLY ADD/MODIFY CODE ABOVE HERE ####################
        





########NEW FILE########
__FILENAME__ = test
import unittest
from math import pi
import task

class TestMoveFunction(unittest.TestCase):
    """ This test works using representation of robots by its __repr__
        function
    """

    def test_case1(self):
        length = 20.0
        bearing_noise = 0.0
        steering_noise = 0.0
        distance_noise = 0.0

        myrobot = task.robot(length)
        myrobot.set(0.0, 0.0, 0.0)
        myrobot.set_noise(bearing_noise, steering_noise, distance_noise)

        motions = [[0.0, 10.0], [pi / 6.0, 10], [0.0, 20.0]]

        expected_repr = ["[x=0.0 y=0.0 orient=0.0]",
                         "[x=10.0 y=0.0 orient=0.0]",
                         "[x=19.861 y=1.4333 orient=0.2886]",
                         "[x=39.034 y=7.1270 orient=0.2886]"]

        self.assertEquals(
            expected_repr[0], 
            repr(myrobot),
            "On initialization step: expected %s got %s" % (expected_repr[0],
                                                            repr(myrobot)))
        for m in range(len(motions)):
            myrobot = myrobot.move(motions[m])
            self.assertEquals(
                expected_repr[m+1], 
                repr(myrobot),
                "On step %d: expected %s got %s" % (m,
                                                    expected_repr[m+1],
                                                    repr(myrobot)))


    def test_case2(self):
        length = 20.0
        bearing_noise = 0.0
        steering_noise = 0.0
        distance_noise = 0.0

        myrobot = task.robot(length)
        myrobot.set(0.0, 0.0, 0.0)
        myrobot.set_noise(bearing_noise, steering_noise, distance_noise)

        motions = [[0.2, 10.] for row in range(10)]

        expected_repr = ["[x=0.0 y=0.0 orient=0.0]",
                         "[x=9.9828 y=0.5063 orient=0.1013]",
                         "[x=19.863 y=2.0201 orient=0.2027]",
                         "[x=29.539 y=4.5259 orient=0.3040]",
                         "[x=38.913 y=7.9979 orient=0.4054]",
                         "[x=47.887 y=12.400 orient=0.5067]",
                         "[x=56.369 y=17.688 orient=0.6081]",
                         "[x=64.273 y=23.807 orient=0.7094]",
                         "[x=71.517 y=30.695 orient=0.8108]",
                         "[x=78.027 y=38.280 orient=0.9121]",
                         "[x=83.736 y=46.485 orient=1.0135]"]
        self.assertEquals(
            expected_repr[0], 
            repr(myrobot),
            "On initialization step: expected %s got %s" % (expected_repr[0],
                                                            repr(myrobot)))
        for m in range(len(motions)):
            myrobot = myrobot.move(motions[m])
            self.assertEquals(
                expected_repr[m+1], 
                repr(myrobot),
                "On step %d: expected %s got %s" % (m,
                                                    expected_repr[m+1],
                                                    repr(myrobot)))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = task
# --------------
# USER INSTRUCTIONS
#
# Write a function in the class robot called sense()
# that takes self as input
# and returns a list, Z, of the four bearings* to the 4
# different landmarks. you will have to use the robot's
# x and y position, as well as its orientation, to
# compute this.
#
# *bearing is defined in the video
# which accompanies this problem.
#
# For now, please do NOT add noise to your sense function.
#
# Please do not modify anything except where indicated
# below.
#
# There are test cases provided at the bottom which you are
# free to use. If you uncomment any of these cases for testing
# make sure that you re-comment it before you submit.

# --------
# 
# the "world" has 4 landmarks.
# the robot's initial coordinates are somewhere in the square
# represented by the landmarks.
#

from math import *
import random

landmarks  = [[0.0, 100.0], [0.0, 0.0], [100.0, 0.0], [100.0, 100.0]] # position of 4 landmarks
world_size = 100.0 # world is NOT cyclic. Robot is allowed to travel "out of bounds"

# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------
    # init: 
    # creates robot and initializes location/orientation
    #

    def __init__(self, length = 10.0):
        self.x = random.random() * world_size # initial x position
        self.y = random.random() * world_size # initial y position
        self.orientation = random.random() * 2.0 * pi # initial orientation
        self.length = length # length of robot
        self.bearing_noise  = 0.0 # initialize bearing noise to zero
        self.steering_noise = 0.0 # initialize steering noise to zero
        self.distance_noise = 0.0 # initialize distance noise to zero



    def __repr__(self):
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), 
                                                str(self.orientation))


    # --------
    # set: 
    # sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):
        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)

    # --------
    # set_noise: 
    # sets the noise parameters
    #

    def set_noise(self, new_b_noise, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.bearing_noise  = float(new_b_noise)
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    ############# ONLY ADD/MODIFY CODE BELOW HERE ###################

    # --------
    # sense:
    #   obtains bearings from positions
    #
    
    def sense(self): #do not change the name of this function
        Z = []

        # ENTER CODE HERE
        # HINT: You will probably need to use the function atan2()

        return Z #Leave this line here. Return vector Z of 4 bearings.
    
    ############## ONLY ADD/MODIFY CODE ABOVE HERE ####################


## IMPORTANT: You may uncomment the test cases below to test your code.
## But when you submit this code, your test cases MUST be commented
## out. Our testing program provides its own code for testing your
## sense function with randomized initial robot coordinates.
    
## --------
## TEST CASES:



##
## 1) The following code should print the list [6.004885648174475, 3.7295952571373605, 1.9295669970654687, 0.8519663271732721]
##
##
##length = 20.
##bearing_noise  = 0.0
##steering_noise = 0.0
##distance_noise = 0.0
##
##myrobot = robot(length)
##myrobot.set(30.0, 20.0, 0.0)
##myrobot.set_noise(bearing_noise, steering_noise, distance_noise)
##
##print 'Robot:        ', myrobot
##print 'Measurements: ', myrobot.sense()
##

## IMPORTANT: You may uncomment the test cases below to test your code.
## But when you submit this code, your test cases MUST be commented
## out. Our testing program provides its own code for testing your
## sense function with randomized initial robot coordinates.
    

##
## 2) The following code should print the list [5.376567117456516, 3.101276726419402, 1.3012484663475101, 0.22364779645531352]
##
##
##length = 20.
##bearing_noise  = 0.0
##steering_noise = 0.0
##distance_noise = 0.0
##
##myrobot = robot(length)
##myrobot.set(30.0, 20.0, pi / 5.0)
##myrobot.set_noise(bearing_noise, steering_noise, distance_noise)
##
##print 'Robot:        ', myrobot
##print 'Measurements: ', myrobot.sense()
##


## IMPORTANT: You may uncomment the test cases below to test your code.
## But when you submit this code, your test cases MUST be commented
## out. Our testing program provides its own code for testing your
## sense function with randomized initial robot coordinates.
    


########NEW FILE########
__FILENAME__ = test
import unittest
from math import pi
import task

class TestSenseFunction(unittest.TestCase):

    def test_case1(self):
        length = 20.0
        bearing_noise  = 0.0
        steering_noise = 0.0
        distance_noise = 0.0
    		
        myrobot = task.robot(length)
        myrobot.set(30.0, 20.0, 0.0)
        myrobot.set_noise(bearing_noise, steering_noise, distance_noise)
    
        expected = [6.004885648174475, 3.7295952571373605, 1.9295669970654687, 0.8519663271732721]

        result = myrobot.sense()
        self.assertEquals(len(expected), len(result),
            "Measurement lengths differ: expected %d got %d" % (len(expected),
                                                                len(result)))
        for i, j in zip(expected, result):
            self.assertAlmostEquals(i, j, 7,
                "Measurements differ: expected %s, got %s" % (repr(expected), 
                                                              repr(result)))

    def test_case2(self):
        length = 20.0
        bearing_noise  = 0.0
        steering_noise = 0.0
        distance_noise = 0.0
    		
        myrobot = task.robot(length)
        myrobot.set(30.0, 20.0, pi / 5.0)
        myrobot.set_noise(bearing_noise, steering_noise, distance_noise)
        
        expected = [5.376567117456516, 3.101276726419402, 1.3012484663475101, 0.22364779645531352]

        result = myrobot.sense()
        self.assertEquals(len(expected), len(result),
            "Measurement lengths differ: expected %d got %d" % (len(expected),
                                                                len(result)))
        for i, j in zip(expected, result):
            self.assertAlmostEquals(i, j, 7,
                "Measurements differ: expected %s, got %s" % (repr(expected), 
                                                              repr(result)))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = task
# --------------
# USER INSTRUCTIONS
#
# Now you will put everything together.
#
# First make sure that your sense and move functions
# work as expected for the test cases provided at the
# bottom of the previous two programming assignments.
# Once you are satisfied, copy your sense and move
# definitions into the robot class on this page, BUT
# now include noise.
#
# A good way to include noise in the sense step is to
# add Gaussian noise, centered at zero with variance
# of self.bearing_noise to each bearing. You can do this
# with the command random.gauss(0, self.bearing_noise)
#
# In the move step, you should make sure that your
# actual steering angle is chosen from a Gaussian
# distribution of steering angles. This distribution
# should be centered at the intended steering angle
# with variance of self.steering_noise.
#
# Feel free to use the included set_noise function.
#
# Please do not modify anything except where indicated
# below.

from math import *
import random

# --------
# 
# some top level parameters
#

max_steering_angle = pi / 4.0
bearing_noise = 0.1 # Noise parameter: should be included in sense function.
steering_noise = 0.1 # Noise parameter: should be included in move function.
distance_noise = 5.0 # Noise parameter: should be included in move function.

tolerance_xy = 15.0 # Tolerance for localization in the x and y directions.
tolerance_orientation = 0.25 # Tolerance for orientation.


# --------
# 
# the "world" has 4 landmarks.
# the robot's initial coordinates are somewhere in the square
# represented by the landmarks.
#

landmarks  = [[0.0, 100.0], [0.0, 0.0], [100.0, 0.0], [100.0, 100.0]] # position of 4 landmarks
world_size = 100.0 # world is NOT cyclic. Robot is allowed to travel "out of bounds"

# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------
    # init: 
    #    creates robot and initializes location/orientation 
    #

    def __init__(self, length = 20.0):
        self.x = random.random() * world_size # initial x position
        self.y = random.random() * world_size # initial y position
        self.orientation = random.random() * 2.0 * pi # initial orientation
        self.length = length # length of robot
        self.bearing_noise  = 0.0 # initialize bearing noise to zero
        self.steering_noise = 0.0 # initialize steering noise to zero
        self.distance_noise = 0.0 # initialize distance noise to zero

    # --------
    # set: 
    #    sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):

        if new_orientation < 0 or new_orientation >= 2 * pi:
            raise ValueError, 'Orientation must be in [0..2pi]'
        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation)

    # --------
    # set_noise: 
    #    sets the noise parameters
    #
    def set_noise(self, new_b_noise, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.bearing_noise  = float(new_b_noise)
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    # --------
    # measurement_prob
    #    computes the probability of a measurement
    #  

    def measurement_prob(self, measurements):

        # calculate the correct measurement
        predicted_measurements = self.sense(0)


        # compute errors
        error = 1.0
        for i in range(len(measurements)):
            error_bearing = abs(measurements[i] - predicted_measurements[i])
            error_bearing = (error_bearing + pi) % (2.0 * pi) - pi # truncate
            

            # update Gaussian
            error *= (exp(- (error_bearing ** 2) / (self.bearing_noise ** 2) / 2.0) /  
                      sqrt(2.0 * pi * (self.bearing_noise ** 2)))

        return error
    
    def __repr__(self): #allows us to print robot attributes.
        return '[x=%.6s y=%.6s orient=%.6s]' % (str(self.x), str(self.y), 
                                                str(self.orientation))
    
    ############# ONLY ADD/MODIFY CODE BELOW HERE ###################
       
    # --------
    # move: 
    #   
    
    # copy your code from the previous exercise
    # and modify it so that it simulates motion noise
    # according to the noise parameters
    #           self.steering_noise
    #           self.distance_noise

    # --------
    # sense: 
    #    

    # copy your code from the previous exercise
    # and modify it so that it simulates bearing noise
    # according to
    #           self.bearing_noise

    ############## ONLY ADD/MODIFY CODE ABOVE HERE ####################

# --------
#
# extract position from a particle set
# 

def get_position(p):
    x = 0.0
    y = 0.0
    orientation = 0.0
    for i in range(len(p)):
        x += p[i].x
        y += p[i].y
        # orientation is tricky because it is cyclic. By normalizing
        # around the first particle we are somewhat more robust to
        # the 0=2pi problem
        orientation += (((p[i].orientation - p[0].orientation + pi) % (2.0 * pi)) 
                        + p[0].orientation - pi)
    return [x / len(p), y / len(p), orientation / len(p)]

# --------
#
# The following code generates the measurements vector
# You can use it to develop your solution.
# 


def generate_ground_truth(motions):

    myrobot = robot()
    myrobot.set_noise(bearing_noise, steering_noise, distance_noise)

    Z = []
    T = len(motions)

    for t in range(T):
        myrobot = myrobot.move(motions[t])
        Z.append(myrobot.sense())
    #print 'Robot:    ', myrobot
    return [myrobot, Z]

# --------
#
# The following code prints the measurements associated
# with generate_ground_truth
#

def print_measurements(Z):

    T = len(Z)

    print 'measurements = [[%.8s, %.8s, %.8s, %.8s],' % \
        (str(Z[0][0]), str(Z[0][1]), str(Z[0][2]), str(Z[0][3]))
    for t in range(1,T-1):
        print '                [%.8s, %.8s, %.8s, %.8s],' % \
            (str(Z[t][0]), str(Z[t][1]), str(Z[t][2]), str(Z[t][3]))
    print '                [%.8s, %.8s, %.8s, %.8s]]' % \
        (str(Z[T-1][0]), str(Z[T-1][1]), str(Z[T-1][2]), str(Z[T-1][3]))

# --------
#
# The following code checks to see if your particle filter
# localizes the robot to within the desired tolerances
# of the true position. The tolerances are defined at the top.
#

def check_output(final_robot, estimated_position):

    error_x = abs(final_robot.x - estimated_position[0])
    error_y = abs(final_robot.y - estimated_position[1])
    error_orientation = abs(final_robot.orientation - estimated_position[2])
    error_orientation = (error_orientation + pi) % (2.0 * pi) - pi
    correct = error_x < tolerance_xy and error_y < tolerance_xy \
              and error_orientation < tolerance_orientation
    return correct



def particle_filter(motions, measurements, N=500): # I know it's tempting, but don't change N!
    # --------
    #
    # Make particles
    # 

    p = []
    for i in range(N):
        r = robot()
        r.set_noise(bearing_noise, steering_noise, distance_noise)
        p.append(r)

    # --------
    #
    # Update particles
    #     

    for t in range(len(motions)):
    
        # motion update (prediction)
        p2 = []
        for i in range(N):
            p2.append(p[i].move(motions[t]))
        p = p2

        # measurement update
        w = []
        for i in range(N):
            w.append(p[i].measurement_prob(measurements[t]))

        # resampling
        p3 = []
        index = int(random.random() * N)
        beta = 0.0
        mw = max(w)
        for i in range(N):
            beta += random.random() * 2.0 * mw
            while beta > w[index]:
                beta -= w[index]
                index = (index + 1) % N
            p3.append(p[index])
        p = p3
    
    return get_position(p)





########NEW FILE########
__FILENAME__ = test
import unittest
from math import pi
import task
import random

class TestRobot(unittest.TestCase):

    def test_case1(self):
        motions = [[2. * pi / 10, 20.] for row in range(8)]
        measurements = [[4.746936, 3.859782, 3.045217, 2.045506],
                        [3.510067, 2.916300, 2.146394, 1.598332],
                        [2.972469, 2.407489, 1.588474, 1.611094],
                        [1.906178, 1.193329, 0.619356, 0.807930],
                        [1.352825, 0.662233, 0.144927, 0.799090],
                        [0.856150, 0.214590, 5.651497, 1.062401],
                        [0.194460, 5.660382, 4.761072, 2.471682],
                        [5.717342, 4.736780, 3.909599, 2.342536]]
        
        expected = [93.476, 75.186, 5.2664]

        result = task.particle_filter(motions, measurements)

        self.assertTrue(abs(result[0] - expected[0]) < task.tolerance_xy,
            "predicted X=%f is far away from expected %f" % (result[0],
                                                             expected[0]))
        self.assertTrue(abs(result[1] - expected[1]) < task.tolerance_xy,
            "predicted Y=%f is far away from expected %f" % (result[1],
                                                             expected[1]))
        self.assertTrue(abs(result[2] - expected[2]) < task.tolerance_orientation,
            "predicted orientation=%f is far away from expected %f" % (result[2],
                                                                       expected[2]))

    def test_case2(self):
        number_of_cycles = 50
        number_to_success = 45
        number_succeeded = 0
        for cycle in range(number_of_cycles):
            number_of_iterations = random.randint(2, 100)
            motions = [[2. * pi / 20, 12.] for row in range(number_of_iterations)]
            
            x = task.generate_ground_truth(motions)
            final_robot = x[0]
            measurements = x[1]
            estimated_position = task.particle_filter(motions, measurements)

            if task.check_output(final_robot, estimated_position):
                number_succeeded += 1
        
        print "TEST: Succeeded %d runs of %d" % (number_succeeded,
                                                 number_of_cycles)
        if number_succeeded < number_to_success:
            self.assertTrue(False, "Too small succes ratio")


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = task
# --------------
# USER INSTRUCTIONS
#
# Write a function called stochastic_value that 
# takes no input and RETURNS two grids. The
# first grid, value, should contain the computed
# value of each cell as shown in the video. The
# second grid, policy, should contain the optimum
# policy for each cell.
#
# Stay tuned for a homework help video! This should
# be available by Thursday and will be visible
# in the course content tab.
#
# Good luck! Keep learning!
#
# --------------
# GRADING NOTES
#
# We will be calling your stochastic_value function
# with several different grids and different values
# of success_prob, collision_cost, and cost_step.
# In order to be marked correct, your function must
# RETURN (it does not have to print) two grids,
# value and policy.
#
# When grading your value grid, we will compare the
# value of each cell with the true value according
# to this model. If your answer for each cell
# is sufficiently close to the correct answer
# (within 0.001), you will be marked as correct.
#
# NOTE: Please do not modify the values of grid,
# success_prob, collision_cost, or cost_step inside
# your function. Doing so could result in your
# submission being inappropriately marked as incorrect.

# -------------
# GLOBAL VARIABLES
#
# You may modify these variables for testing
# purposes, but you should only modify them here.
# Do NOT modify them inside your stochastic_value
# function.

grid = [[0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 1, 1, 0]]
       
goal = [0, len(grid[0])-1] # Goal is in top right corner


delta = [[-1, 0 ], # go up
         [ 0, -1], # go left
         [ 1, 0 ], # go down
         [ 0, 1 ]] # go right

delta_name = ['^', '<', 'v', '>'] # Use these when creating your policy grid.

success_prob = 0.5                      
failure_prob = (1.0 - success_prob)/2.0 # Probability(stepping left) = prob(stepping right) = failure_prob
collision_cost = 100                    
cost_step = 1        
                     

############## INSERT/MODIFY YOUR CODE BELOW ##################
#
# You may modify the code below if you want, but remember that
# your function must...
#
# 1) ...be called stochastic_value().
# 2) ...NOT take any arguments.
# 3) ...return two grids: FIRST value and THEN policy.

def stochastic_value():
    value = [[1000.0 for row in range(len(grid[0]))] for col in range(len(grid))]
    policy = [[' ' for row in range(len(grid[0]))] for col in range(len(grid))]
    
    return value, policy


########NEW FILE########
__FILENAME__ = test
import unittest
import task

class TestMotion(unittest.TestCase):
    def compare_values(self, expected, got):
        self.assertEqual(len(expected), len(got),
            "Value lists have different size: expected %d, got %d" % (len(expected), len(got)))
        for i, row in enumerate(expected):
            self.assertEqual(len(expected[i]), len(got[i]),
                "Value lists have different size: expected %d, got %d in line %d" % (len(expected[i]), len(got[i]), i))
            for j, _ in enumerate(row):
                self.assertAlmostEqual(expected[i][j], got[i][j], 3,
                    "Values differ: expected %.3f got %.3f at [%d][%d]" % (expected[i][j], got[i][j], i, j))

    def compare_policies(self, expected, got):
        self.assertEqual(len(expected), len(got),
            "Policy lists have different size: expected %d, got %d" % (len(expected), len(got)))
        for i, row in enumerate(expected):
            self.assertEqual(len(expected[i]), len(got[i]),
                "Policy lists have different size: expected %d, got %d in line %d" % (len(expected[i]), len(got[i]), i))
            for j, _ in enumerate(row):
                self.assertTrue(got[i][j] in expected[i][j],
                                 "Policies differ: expected %s, got %s at [%d][%d]" % (expected[i][j], got[i][j], i, j))
        #self.assertEqual(expected, got)

    def test_small_1(self):
        exp_value = [[60.472, 37.193, 0.000],
                     [63.503, 44.770, 37.193]]
        exp_policy = [['>', '>', '*'],
                      ['>', '^', '^']]
        task.grid = [[0, 0, 0],
                     [0, 0, 0]]
        task.goal = [0, len(task.grid[0])-1] # Goal is in top right corner
        task.success_prob = 0.5
        task.failure_prob = (1.0 - task.success_prob)/2.0 
        value, policy = task.stochastic_value()
        self.compare_values(exp_value, value)
        self.compare_policies(exp_policy, policy)

    def test_small_2(self):
        exp_value = [[94.041, 1000.000, 0.000],
                     [86.082, 73.143, 44.286]]
        exp_policy = [['v', ' ', '*'],
                      ['>', '>', '^']]
        task.grid = [[0, 1, 0],
                     [0, 0, 0]]
        task.goal = [0, len(task.grid[0])-1] # Goal is in top right corner
        task.success_prob = 0.5
        task.failure_prob = (1.0 - task.success_prob)/2.0 
        value, policy = task.stochastic_value()
        self.compare_values(exp_value, value)
        self.compare_policies(exp_policy, policy)

    def test_big(self):
        exp_value = [[57.903, 40.278, 26.066, 0.000],
                     [47.055, 36.572, 29.994, 27.270],
                     [53.172, 42.023, 37.775, 45.092],
                     [77.586, 1000.000, 1000.000, 73.546]]
        exp_policy = [['>', 'v', 'v', '*'],
                      ['>', '>', '^', '<'],
                      ['>', '^', '^', '<'],
                      ['^', ' ', ' ', '^']]
        task.grid = [[0, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 1, 1, 0]]
        task.goal = [0, len(task.grid[0])-1] # Goal is in top right corner
        task.success_prob = 0.5
        task.failure_prob = (1.0 - task.success_prob)/2.0 
        value, policy = task.stochastic_value()
        self.compare_values(exp_value, value)
        self.compare_policies(exp_policy, policy)

    def test_big_nofail(self):
        exp_value = [[3.000, 2.000, 1.000, 0.000],
                     [4.000, 3.000, 2.000, 1.000],
                     [5.000, 4.000, 3.000, 2.000],
                     [6.000, 1000.000, 1000.000, 3.000]]
        exp_policy = [['>',  '>',  '>',  '*'],
                      ['^>', '^>', '^>', '^'],
                      ['^>', '^>', '^>', '^'],
                      ['^',  ' ',  ' ',  '^']]
        task.grid = [[0, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 0, 0, 0],
                     [0, 1, 1, 0]]
        task.goal = [0, len(task.grid[0])-1] # Goal is in top right corner
        task.success_prob = 1.0
        task.failure_prob = (1.0 - task.success_prob)/2.0 
        value, policy = task.stochastic_value()
        self.compare_values(exp_value, value)
        self.compare_policies(exp_policy, policy)
        
if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = task
# -------------
# User Instructions
#
# Here you will be implementing a cyclic smoothing
# algorithm. This algorithm should not fix the end
# points (as you did in the unit quizzes). You  
# should use the gradient descent equations that
# you used previously.
#
# Your function should return the newpath that it
# calculates..
#
# Feel free to use the provided solution_check function
# to test your code. You can find it at the bottom.
#
# --------------
# Testing Instructions
# 
# To test your code, call the solution_check function with
# two arguments. The first argument should be the result of your
# smooth function. The second should be the corresponding answer.
# For example, calling
#
# solution_check(smooth(testpath1), answer1)
#
# should return True if your answer is correct and False if
# it is not.

from math import *

# Do not modify path inside your function.
path=[[0, 0], 
      [1, 0],
      [2, 0],
      [3, 0],
      [4, 0],
      [5, 0],
      [6, 0],
      [6, 1],
      [6, 2],
      [6, 3],
      [5, 3],
      [4, 3],
      [3, 3],
      [2, 3],
      [1, 3],
      [0, 3],
      [0, 2],
      [0, 1]]

############# ONLY ENTER CODE BELOW THIS LINE ##########

# ------------------------------------------------
# smooth coordinates
# If your code is timing out, make the tolerance parameter
# larger to decrease run time.
#

def smooth(path, weight_data = 0.1, weight_smooth = 0.1, tolerance = 0.00001):

    # 
    # Enter code here
    #

    # deep copy
    newpath = [[0 for row in range(len(path[0]))] for col in range(len(path))]
    for i in range(len(path)):
        for j in range(len(path[0])):
            newpath[i][j] = path[i][j]


# thank you - EnTerr - for posting this on our discussion forum

#newpath = smooth(path)
#for i in range(len(path)):
#    print '['+ ', '.join('%.3f'%x for x in path[i]) +'] -> ['+ ', '.join('%.3f'%x for x in newpath[i]) +']'



########NEW FILE########
__FILENAME__ = test
import unittest
import task
from math import *

class TestSmoothing(unittest.TestCase):

    def assertSmoothingValid(self, path, newpath_expected):
        path_persistent = [pair[:] for pair in path]

        newpath = task.smooth(path)

        self.assertTrue(type(newpath) == type(newpath_expected),
                        "Function doesn't return a list")
        self.assertTrue(len(newpath) == len(newpath_expected),
                        "Newpath has the wrong length")
        self.assertEqual(path, path_persistent,
                         "Original path variable was modified by your code")
        for index, got, expected in zip(range(len(newpath_expected)), newpath, newpath_expected):
            self.assertTrue(type(got) == type(expected),
                            "Returned list doesn't contain a point at position %d" % index)
            self.assertTrue(len(got) == len(expected),
                            "Returned list doesn't contain a list of two coordinates "
                            "at position %d" % index)
            self.assertAlmostEqual(got[0], expected[0], 3,
                                   "X coordinate differs for point %d: "
                                   "expected %.3f, got %.3f" % (index, expected[0], got[0]))
            self.assertAlmostEqual(got[1], expected[1], 3,
                                   "Y coordinate differs for point %d: "
                                   "expected %.3f, got %.3f" % (index, expected[1], got[1]))
    
    def test_videoPath(self):
        path = [[0, 0],
                [1, 0],
                [2, 0],
                [3, 0],
                [4, 0],
                [5, 0],
                [6, 0],
                [6, 1],
                [6, 2],
                [6, 3],
                [5, 3],
                [4, 3],
                [3, 3],
                [2, 3],
                [1, 3],
                [0, 3],
                [0, 2],
                [0, 1]]
        newpath_expected = [[0.5449300156668018, 0.47485226780102946],
                            [1.2230705677535505, 0.2046277687200752],
                            [2.079668890615267, 0.09810778721159963],
                            [3.0000020176660755, 0.07007646364781912],
                            [3.9203348821839112, 0.09810853832382399],
                            [4.7769324511170455, 0.20462917195702085],
                            [5.455071854686622, 0.4748541381544533],
                            [5.697264197153936, 1.1249625336275617],
                            [5.697263485026567, 1.8750401628534337],
                            [5.455069810373743, 2.5251482916876378],
                            [4.776929339068159, 2.795372759575895],
                            [3.92033110541304, 2.9018927284871063],
                            [2.999998066091118, 2.929924058932193],
                            [2.0796652780381826, 2.90189200881968],
                            [1.2230677654766597, 2.7953714133566603],
                            [0.544928391271399, 2.5251464933327794],
                            [0.3027360471605494, 1.875038145804603],
                            [0.302736726373967, 1.1249605602741133]]
        self.assertSmoothingValid(path, newpath_expected)

    def test_secondPath(self):
        path = [[1, 0], # Move in the shape of a plus sign
                [2, 0],
                [2, 1],
                [3, 1],
                [3, 2],
                [2, 2],
                [2, 3],
                [1, 3],
                [1, 2],
                [0, 2], 
                [0, 1],
                [1, 1]]

        answer = [[1.239080543767428, 0.5047204351187283],
                  [1.7609243903912781, 0.5047216452560908],
                  [2.0915039821562416, 0.9085017167753027],
                  [2.495281862032503, 1.2390825203587184],
                  [2.4952805300504783, 1.7609262468826048],
                  [2.0915003641706296, 2.0915058211575475],
                  [1.7609195135622062, 2.4952837841027695],
                  [1.2390757942466555, 2.4952826072236918],
                  [0.9084962737918979, 2.091502621431358],
                  [0.5047183914625598, 1.7609219230352355],
                  [0.504719649257698, 1.2390782835562297],
                  [0.9084996902674257, 0.9084987462432871]]

        self.assertSmoothingValid(path, answer)


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = task
# -------------
# User Instructions
#
# Now you will be incorporating fixed points into
# your smoother. 
#
# You will need to use the equations from gradient
# descent AND the new equations presented in the
# previous lecture to implement smoothing with
# fixed points.
#
# Your function should return the newpath that it
# calculates. 
#
# Feel free to use the provided solution_check function
# to test your code. You can find it at the bottom.
#
# --------------
# Testing Instructions
# 
# To test your code, call the solution_check function with
# two arguments. The first argument should be the result of your
# smooth function. The second should be the corresponding answer.
# For example, calling
#
# solution_check(smooth(testpath1), answer1)
#
# should return True if your answer is correct and False if
# it is not.

from math import *

# Do not modify path inside your function.
path=[[0, 0], #fix 
      [1, 0],
      [2, 0],
      [3, 0],
      [4, 0],
      [5, 0],
      [6, 0], #fix
      [6, 1],
      [6, 2],
      [6, 3], #fix
      [5, 3],
      [4, 3],
      [3, 3],
      [2, 3],
      [1, 3],
      [0, 3], #fix
      [0, 2],
      [0, 1]]

# Do not modify fix inside your function
fix = [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0]

######################## ENTER CODE BELOW HERE #########################

def smooth(path, fix, weight_data = 0.0, weight_smooth = 0.1, tolerance = 0.00001):
    #
    # Enter code here. 
    # The weight for each of the two new equations should be 0.5 * weight_smooth
    #



#thank you - EnTerr - for posting this on our discussion forum

#newpath = smooth(path, fix)
#for i in range(len(path)):

########NEW FILE########
__FILENAME__ = test
import unittest
import task
from math import *

class TestSmoothing(unittest.TestCase):

    def assertSmoothingValid(self, path, fix, newpath_expected):
        path_persistent = [pair[:] for pair in path]
        fix_persistent = fix[:]

        newpath = task.smooth(path, fix)

        self.assertTrue(type(newpath) == type(newpath_expected),
                        "Function doesn't return a list")
        self.assertTrue(len(newpath) == len(newpath_expected),
                        "Newpath has the wrong length")
        self.assertEqual(path, path_persistent,
                         "Original path variable was modified by your code")
        self.assertEqual(fix, fix_persistent,
                         "Original fix variable was modified by your code")
        for index, got, expected in zip(range(len(newpath_expected)), newpath, newpath_expected):
            self.assertTrue(type(got) == type(expected),
                            "Returned list doesn't contain a point at position %d" % index)
            self.assertTrue(len(got) == len(expected),
                            "Returned list doesn't contain a list of two coordinates "
                            "at position %d" % index)
            self.assertAlmostEqual(got[0], expected[0], 3,
                                   "X coordinate differs for point %d: "
                                   "expected %.3f, got %.3f" % (index, expected[0], got[0]))
            self.assertAlmostEqual(got[1], expected[1], 3,
                                   "Y coordinate differs for point %d: "
                                   "expected %.3f, got %.3f" % (index, expected[1], got[1]))
    
    def test_videoPath(self):
        path = [[0, 0],
                [1, 0],
                [2, 0],
                [3, 0],
                [4, 0],
                [5, 0],
                [6, 0],
                [6, 1],
                [6, 2],
                [6, 3],
                [5, 3],
                [4, 3],
                [3, 3],
                [2, 3],
                [1, 3],
                [0, 3],
                [0, 2],
                [0, 1]]
        fix = [1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0]
        newpath_expected = [[0, 0],
                            [0.7938620981547201, -0.8311168821106101],
                            [1.8579052986461084, -1.3834788165869276],
                            [3.053905318597796, -1.5745863173084],
                            [4.23141390533387, -1.3784271816058231],
                            [5.250184859723701, -0.8264215958231558],
                            [6, 0],
                            [6.415150091996651, 0.9836951698796843],
                            [6.41942442687092, 2.019512290770163],
                            [6, 3],
                            [5.206131365604606, 3.831104483245191],
                            [4.142082497497067, 4.383455704596517],
                            [2.9460804122779813, 4.5745592975708105],
                            [1.768574219397359, 4.378404668718541],
                            [0.7498089205417316, 3.826409771585794],
                            [0, 3],
                            [-0.4151464728194156, 2.016311854977891],
                            [-0.4194207879552198, 0.9804948340550833]]
        self.assertSmoothingValid(path, fix, newpath_expected)

    def test_secondPath(self):
        path = [[0, 0], # fix
                [2, 0],
                [4, 0], # fix
                [4, 2],
                [4, 4], # fix
                [2, 4],
                [0, 4], # fix
                [0, 2]]
        fix = [1, 0, 1, 0, 1, 0, 1, 0]
        answer = [[0, 0],
                  [2.0116767115496095, -0.7015439080661671],
                  [4, 0],
                  [4.701543905420104, 2.0116768147460418],
                  [4, 4],
                  [1.9883231877640861, 4.701543807525115],
                  [0, 4],
                  [-0.7015438099112995, 1.9883232808252207]]

        self.assertSmoothingValid(path, fix, answer)


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = task
# --------------
# User Instructions
# 
# Define a function cte in the robot class that will
# compute the crosstrack error for a robot on a
# racetrack with a shape as described in the video.
#
# You will need to base your error calculation on
# the robot's location on the track. Remember that 
# the robot will be traveling to the right on the
# upper straight segment and to the left on the lower
# straight segment.
#
# --------------
# Grading Notes
#
# We will be testing your cte function directly by
# calling it with different robot locations and making
# sure that it returns the correct crosstrack error.  
 
from math import *
import random
import sys


# ------------------------------------------------
# 
# this is the robot class
#

class robot:

    # --------
    # init: 
    #    creates robot and initializes location/orientation to 0, 0, 0
    #

    def __init__(self, length = 20.0):
        self.x = 0.0
        self.y = 0.0
        self.orientation = 0.0
        self.length = length
        self.steering_noise = 0.0
        self.distance_noise = 0.0
        self.steering_drift = 0.0

    # --------
    # set: 
    # sets a robot coordinate
    #

    def set(self, new_x, new_y, new_orientation):

        self.x = float(new_x)
        self.y = float(new_y)
        self.orientation = float(new_orientation) % (2.0 * pi)


    # --------
    # set_noise: 
    # sets the noise parameters
    #

    def set_noise(self, new_s_noise, new_d_noise):
        # makes it possible to change the noise parameters
        # this is often useful in particle filters
        self.steering_noise = float(new_s_noise)
        self.distance_noise = float(new_d_noise)

    # --------
    # set_steering_drift: 
    # sets the systematical steering drift parameter
    #

    def set_steering_drift(self, drift):
        self.steering_drift = drift
        
    # --------
    # move: 
    #    steering = front wheel steering angle, limited by max_steering_angle
    #    distance = total distance driven, most be non-negative

    def move(self, steering, distance, 
             tolerance = 0.001, max_steering_angle = pi / 4.0):

        if steering > max_steering_angle:
            steering = max_steering_angle
        if steering < -max_steering_angle:
            steering = -max_steering_angle
        if distance < 0.0:
            distance = 0.0


        # make a new copy
        res = robot()
        res.length         = self.length
        res.steering_noise = self.steering_noise
        res.distance_noise = self.distance_noise
        res.steering_drift = self.steering_drift

        # apply noise
        steering2 = random.gauss(steering, self.steering_noise)
        distance2 = random.gauss(distance, self.distance_noise)

        # apply steering drift
        steering2 += self.steering_drift

        # Execute motion
        turn = tan(steering2) * distance2 / res.length

        if abs(turn) < tolerance:

            # approximate by straight line motion

            res.x = self.x + (distance2 * cos(self.orientation))
            res.y = self.y + (distance2 * sin(self.orientation))
            res.orientation = (self.orientation + turn) % (2.0 * pi)

        else:

            # approximate bicycle model for motion

            radius = distance2 / turn
            cx = self.x - (sin(self.orientation) * radius)
            cy = self.y + (cos(self.orientation) * radius)
            res.orientation = (self.orientation + turn) % (2.0 * pi)
            res.x = cx + (sin(res.orientation) * radius)
            res.y = cy - (cos(res.orientation) * radius)

        return res




    def __repr__(self):
        return '[x=%.5f y=%.5f orient=%.5f]'  % (self.x, self.y, self.orientation)


############## ONLY ADD / MODIFY CODE BELOW THIS LINE ####################
   
    def cte(self, radius):
        # 
        #
        # Add code here
        #
        #            

        return cte
    
############## ONLY ADD / MODIFY CODE ABOVE THIS LINE ####################





########NEW FILE########
__FILENAME__ = test
import unittest
from math import *
from task import robot

expected_values = [[0.00000,   26.00000, 1.57080,  0.00,            -0.00],
                   [0.01365,   26.99988, 1.54349,  0.0199920063936, -0.49980015984],
                   [0.06592,   27.99840, 1.49349,  0.0662557639978, -1.35651400404],
                   [0.16804,   28.99307, 1.44349,  0.11371377594,   -1.84900793853],
                   [0.31973,   29.98139, 1.39349,  0.150965199558,  -2.06842334984],
                   [0.52064,   30.96090, 1.34349,  0.177962397159,  -2.18458193562],
                   [0.77025,   31.92914, 1.29349,  0.194670934301,  -2.19733740012],
                   [1.06793,   32.88369, 1.24349,  0.201069537222,  -2.10667441603],
                   [1.41296,   33.82218, 1.19349,  0.197150066653,  -1.91270860801],
                   [1.80445,   34.74224, 1.14349,  0.182917507815,  -1.61568669556],
                   [2.24145,   35.64159, 1.09349,  0.158389976536,  -1.21598679617],
                   [2.71993,   36.51960, 1.05016,  0.123598741553,  -0.714118890791],
                   [3.22162,   37.38464, 1.04034,  0.0819185325749, -0.193982191079],
                   [3.72989,   38.24584, 1.03489,  0.0534900673802, -0.10847369588],
                   [4.25610,   39.09613, 0.99837,  0.0573263088422, -0.630806710352],
                   [4.81855,   39.92283, 0.94837,  0.0800789573513, -1.14207930115],
                   [5.42162,   40.72039, 0.89837,  0.0994363512419, -1.28472442078],
                   [6.06380,   41.48681, 0.84837,  0.108633341303,  -1.22428826394],
                   [6.74348,   42.22017, 0.79837,  0.107658108503,  -1.06195259304],
                   [7.45896,   42.91865, 0.74837,  0.0965119056912, -0.797926014729],
                   [8.19955,   43.59058, 0.72529,  0.075209059113,  -0.432547892458],
                   [8.95301,   44.24807, 0.70967,  0.057232780393,  -0.302683623129],
                   [9.72345,   44.88548, 0.67270,  0.0598086737912, -0.636725138885],
                   [10.52084,  45.48877, 0.62270,  0.0759897991992, -1.00261487311],
                   [11.34739,  46.05146, 0.57270,  0.0885590115358, -1.07412830041],
                   [12.20102,  46.57213, 0.52270,  0.0909872822336, -0.946296882803],
                   [13.07810,  47.05231, 0.47911,  0.0832714854916, -0.716977903787],
                   [13.97122,  47.50208, 0.45393,  0.0686279513107, -0.466626500394],
                   [14.87526,  47.92947, 0.42930,  0.0594834635085, -0.457667318051],
                   [15.79372,  48.32476, 0.38354,  0.0653340327104, -0.741098865133],
                   [16.73003,  48.67564, 0.33354,  0.0758860838852, -0.917141606473],
                   [17.68271,  48.97928, 0.28354,  0.0784395091069, -0.822696469394],
                   [18.64733,  49.24274, 0.24969,  0.0708688175334, -0.595127801731],
                   [19.61934,  49.47756, 0.22440,  0.0612581321519, -0.468421040796],
                   [20.59811,  49.68224, 0.18791,  0.0619725027257, -0.630440585864],
                   [21.58477,  49.84441, 0.13791,  0.0716912865403, -0.862694622622],
                   [22.57830,  49.95707, 0.08791,  0.0780497190628, -0.875873678465],
                   [23.57595,  50.02443, 0.04694,  0.0742847231351, -0.686372292436],
                   [24.57538,  50.05743, 0.01906,  0.0649194975067, -0.508716590641],
                   [25.57533,  50.06110, 6.27146,  0.0610252441975, -0.551838642337],
                   [26.57485,  50.03183, 6.23637,  0.061095707937,  -0.612014035463],
                   [27.57389,  49.98806, 6.24243,  0.0318305895701,  0.120670879803],
                   [28.57366,  49.97184, 0.00832, -0.0119426755486,  0.776025732267],
                   [29.57337,  49.99463, 0.03727, -0.0281604433323,  0.524870950079],
                   [30.57291,  50.02448, 0.02245, -0.00537140875948,-0.288121430998],
                   [31.57284,  50.02619, 6.26415,  0.024482677159,  -0.692638060368],
                   [32.57248,  49.99976, 6.24936,  0.0261876266431, -0.287450508691],
                   [33.57219,  49.97648, 6.27043, -0.000239463375792,0.398800984041],
                   [34.57214,  49.98026, 0.02033, -0.0235237803063,  0.58450255702],
                   [35.57185,  50.00413, 0.02740, -0.0197357297608,  0.140536539426],
                   [36.57169,  50.02098, 0.00631,  0.00412748549346,-0.399223083749],
                   [37.57164,  50.01482, 6.26456,  0.0209816904766, -0.462629979512],
                   [38.57144,  49.99480, 6.26176,  0.0148220461863, -0.0558257975097],
                   [39.57135,  49.98257, 6.28015, -0.00520176363523, 0.352374783676],
                   [40.57132,  49.98888, 0.01565, -0.0174304866369,  0.357735711393],
                   [41.57120,  50.00453, 0.01648, -0.0111212702526,  0.016574456761],
                   [42.57115,  50.01382, 0.00210,  0.00453293934653,-0.280142537452],
                   [43.57112,  50.00880, 6.27104,  0.0138236569379, -0.277597333248],
                   [44.57105,  49.99665, 6.27041,  0.00879806609217,-0.0125967982363],
                   [45.57102,  49.98935, 6.28136, -0.00335115900699, 0.215749966557],
                   [46.57101,  49.99301, 0.00915, -0.0106514280427,  0.216018315964],
                   [47.57097,  50.00216, 0.00990, -0.0069867400186,  0.0148970798241],
                   [48.57095,  50.00805, 0.00188,  0.00216390508083,-0.1588987273],
                   [49.57094,  50.00567, 6.27654,  0.00805329449584,-0.168873786183],
                   [50.57091,  49.99851, 6.27549,  0.00567405929998,-0.0210520650619],
                   [51.57090,  49.99389, 6.28164, -0.00149394419282, 0.12245949432],
                   [52.57090,  49.99563, 0.00502, -0.00611148168858, 0.130377879322],
                   [53.57089,  50.00064, 0.00590, -0.00437412157885, 0.0176808141426],
                   [54.57088,  50.00450, 0.00181,  0.000641263368401,-0.0816434078927],
                   [55.57088,  50.00373, 6.27984,  0.00449515758106, -0.102759989001],
                   [56.57087,  49.99973, 6.27855,  0.00372535194535, -0.0257064349178],
                   [57.57086,  49.99667, 6.28168, -0.000265326856493, 0.0625134505925],
                   [58.57086,  49.99715, 0.00247, -0.0033339376576, 0.0793685385926],
                   [59.57086,  50.00015, 0.00353, -0.00284928917591, 0.0212231645338],
                   [60.57086,  50.00252, 0.00120,  0.000154404194063, -0.0465994424903],
                   [61.57085,  50.00220, 6.28135,  0.00252292820562, -0.0607571422296],
                   [62.57085,  50.00037, 6.28048,  0.00220482471616, -0.0172766948197],
                   [63.57085,  49.99826, 6.28168,  0.000365921809191, 0.0239243255126],
                   [64.57085,  49.99798, 0.00094, -0.00173867887543, 0.0489557990235],
                   [65.57085,  49.99953, 0.00216, -0.00202018521617, 0.0244244472728],
                   [66.57085,  50.00170, 0.00123, -0.00046608605021, -0.0186506269873],
                   [67.57085,  50.00169, 6.28194,  0.00169874477855, -0.0494599102169],
                   [68.57085,  50.00045, 6.28110,  0.00169343079205, -0.0168545981229],
                   [69.57084,  49.99836, 6.28181,  0.000450610106775, 0.0141362092113],
                   [70.57084,  49.99818, 0.00100, -0.00163501910181, 0.0476346291469],
                   [71.57084,  49.99971, 0.00206, -0.00182202497018, 0.0210253377274],
                   [72.57084,  50.00126, 0.00105, -0.000291553378929, -0.0200415400795],
                   [73.57084,  50.00142, 6.28244,  0.00126352350424, -0.0359613882898],
                   [74.57084,  50.00067, 6.28162,  0.00141807300395, -0.0164989725351],
                   [75.57084,  49.99910, 6.28184,  0.000673200135921, 0.00444109166118],
                   [76.57083,  49.99448, 6.27528,  0.0056198373117, -0.130397930754],
                   [77.57018,  49.96158, 6.22528,  0.0437891300386, -1.01043069129],
                   [78.56664,  49.87878, 6.17528,  0.0935524754094, -1.68197493466],
                   [79.55772,  49.74628, 6.12528,  0.133138173426, -1.9251672045],
                   [80.54094,  49.56441, 6.07528,  0.162495508275, -2.06531510548],
                   [81.51384,  49.33363, 6.02528,  0.181586973799, -2.10224172085],
                   [82.47399,  49.05451, 5.97528,  0.190388227148, -2.03590107172],
                   [83.41898,  48.72776, 5.92528,  0.188888058822, -1.86637806333],
                   [84.34647,  48.35418, 5.87528,  0.177088378909, -1.5938885904],
                   [85.25413,  47.93471, 5.82528,  0.15500421943, -1.21877980211],
                   [86.14067,  47.47226, 5.77949,  0.122663752801, -0.741530528573],
                   [87.01382,  46.98482, 5.76855,  0.0822097701142, -0.215287960843],
                   [87.88309,  46.49047, 5.76366,  0.0532237175086, -0.0974463860013],
                   [88.74234,  45.97903, 5.72892,  0.0562253391106, -0.607277715137],
                   [89.57912,  45.43168, 5.67892,  0.0793104555002, -1.13938130085],
                   [90.38750,  44.84319, 5.62892,  0.0998873582557, -1.30752712389],
                   [91.16545,  44.21503, 5.57892,  0.110302603075, -1.25925470304],
                   [91.91104,  43.54878, 5.52892,  0.11054280735, -1.10903113763],
                   [92.62239,  42.84610, 5.47892,  0.100607662576, -0.857049454145],
                   [93.30603,  42.11631, 5.45137,  0.080509933975, -0.503633410736],
                   [93.97320,  41.37143, 5.43425,  0.0614984501119, -0.329812243173],
                   [94.62161,  40.61019, 5.40159,  0.0600481134645, -0.578726084933],
                   [95.23797,  39.82286, 5.35159,  0.0736059601889, -0.939427302755],
                   [95.81421,  39.00571, 5.30159,  0.0857087901091, -1.03863034989],
                   [96.34889,  38.16078, 5.25159,  0.0876753069464, -0.906250822022],
                   [96.84513,  37.29267, 5.21177,  0.0795029784288, -0.672444856524],
                   [97.31295,  36.40888, 5.18670,  0.0662959737314, -0.464854666854],
                   [97.75691,  35.51287, 5.15814,  0.0605355800732, -0.518949895857],
                   [98.16532,  34.60018, 5.10814,  0.0678590913781, -0.788443583356],
                   [98.52759,  33.66822, 5.05814,  0.0757931245029, -0.8769417419],
                   [98.84646,  32.72050, 5.01574,  0.0736072196222, -0.703283623013],
                   [99.13136,  31.76198, 4.98688,  0.0651060298688, -0.523542452385],
                   [99.38779,  30.79546, 4.95656,  0.0608692646873, -0.54514116915],
                   [99.60637,  29.81974, 4.90899,  0.066940633941, -0.760476878215],
                   [99.77711,  28.83453, 4.85899,  0.0739587058133, -0.844858136219],
                   [99.90263,  27.84251, 4.81751,  0.0720756502521, -0.692510669102],
                   [99.99307,  26.84664, 4.78839,  0.0643385644523, -0.527329357527],
                   [100.05319, 25.84849, 4.75670,  0.0611996640144, -0.564913133574],
                   [100.07322, 24.84879, 4.70813,  0.0675576191349, -0.770945518158],
                   [100.04396, 23.84932, 4.65813,  0.0736735740262, -0.82847506363],
                   [99.97059,  22.85208, 4.61976,  0.070385366224, -0.654530545208],
                   [99.86404,  21.85780, 4.59151,  0.0628001154397, -0.514222392632],
                   [99.72640,  20.86737, 4.55708,  0.0618056625675, -0.603139832592],
                   [99.54708,  19.88369, 4.50708,  0.0693690112361, -0.80714034239],
                   [99.31882,  18.91019, 4.45708,  0.0746018512093, -0.82451111169],
                   [99.04892,  17.94736, 4.42109,  0.0697167701724, -0.623891486171],
                   [98.74875,  16.99351, 4.39394,  0.0617246681708, -0.497365151684],
                   [98.41857,  16.04965, 4.35781,  0.062065023128, -0.625755555638],
                   [98.04808,  15.12092, 4.30781,  0.070666319643, -0.835682644155],
                   [97.63164,  14.21188, 4.25781,  0.0760880868666, -0.84220737702],
                   [97.17581,  13.32187, 4.22032,  0.0713895679525, -0.643417895814],
                   [96.69139,  12.44708, 4.19301,  0.0628297162082, -0.499899385917],
                   [96.18024,  11.58764, 4.15867,  0.0617665943213, -0.60171911491],
                   [95.63335,  10.75056, 4.10867,  0.0697820804466, -0.818053096345],
                   [95.04531,   9.94186, 4.05867,  0.0755185605425, -0.841232806863],
                   [94.42236,   9.15967, 4.02101,  0.0711356553438, -0.645612975458],
                   [93.77424,   8.39817, 3.99349,  0.0628060377533, -0.503116113675],
                   [93.10288,   7.65711, 3.95910,  0.0617827939515, -0.602479282488],
                   [92.40089,   6.94506, 3.90910,  0.0697055978264, -0.815898036387],
                   [91.66420,   6.26900, 3.85910,  0.0753215769505, -0.837455456368],
                   [90.89867,   5.62568, 3.82183,  0.0708184862586, -0.640638502207],
                   [90.11272,   5.00745, 3.79439,  0.0625633514024, -0.501806491183],
                   [89.30793,   4.41397, 3.75961,  0.0618518159789, -0.607845128437],
                   [88.47875,   3.85516, 3.70961,  0.0699304886425, -0.820484976378],
                   [87.62269,   3.33850, 3.65961,  0.0755036651492, -0.838634299093],
                   [86.74484,   2.85967, 3.62227,  0.0709574829414, -0.641382096298],
                   [85.85194,   2.40950, 3.59487,  0.0626300864084, -0.501389916089],
                   [84.94551,   1.98726, 3.56019,  0.0618307726647, -0.606318020491],
                   [84.02207,   1.60378, 3.51019,  0.0698918398115, -0.819834405317],
                   [83.08062,   1.26693, 3.46019,  0.0755040536915, -0.839223745115],
                   [82.12531,   0.97153, 3.42278,  0.07099690762, -0.642361885128],
                   [81.16090,   0.70724, 3.39535,  0.0626703176269, -0.501804326373],
                   [80.18878,   0.47300, 3.36074,  0.0618200942114, -0.605447590882],
                   [79.20767,   0.28008, 3.31074,  0.0698490039921, -0.81892368663],
                   [78.21814,   0.13645, 3.26074,  0.0754613324773, -0.838798252052],
                   [77.22324,   0.03616, 3.22337,  0.0709543689495, -0.641939236578],
                   [76.22559,  -0.03184, 3.19593,  0.062644504693, -0.501797083083],
                   [75.22632,  -0.06885, 3.16128,  0.0618277634572, -0.606026516033],
                   [74.22644,  -0.06354, 3.11128,  0.069868962555, -0.819307612017],
                   [73.22750,  -0.01824, 3.08128,  0.0635374244233, -0.540401172257],
                   [72.22863,   0.02849, 3.10840,  0.018244730271, 0.496943109574],
                   [71.22876,   0.03668, 3.15840, -0.0284875837802, 0.985860548571],
                   [70.22925,   0.00655, 3.18505, -0.0366789157182, 0.489659136251],
                   [69.22982,  -0.02673, 3.16471, -0.00655288355394, -0.386361646924],
                   [68.22992,  -0.02577, 3.11657,  0.0267254360351, -0.766429154187],
                   [67.23041,   0.00545, 3.10415,  0.0257712676876, -0.243400151664],
                   [66.23071,   0.02848, 3.13298, -0.00545489890037, 0.522941487824],
                   [65.23081,   0.01886, 3.16945, -0.0284797426994, 0.630170083978],
                   [64.23123,  -0.01010, 3.17166, -0.0188618629526, 0.0443504333259],
                   [63.23138,  -0.02534, 3.14201,  0.0100965132369, -0.535340775213],
                   [62.23149,  -0.01268, 3.11585,  0.0253394371831, -0.482038231025],
                   [61.23179,   0.01148, 3.11901,  0.0126762566337, 0.0631851419041],
                   [60.23186,   0.02114, 3.14487, -0.0114836349915, 0.477234724292],
                   [59.23195,   0.00856, 3.16347, -0.0211362067355, 0.356150643515],
                   [58.23214,  -0.01073, 3.15830, -0.00856182037331, -0.1029975917],
                   [57.23218,  -0.01696, 3.13736,  0.0107281381352, -0.396630758979],
                   [56.23225,  -0.00599, 3.12389,  0.0169643925677, -0.263187742164],
                   [55.23236,   0.00909, 3.12914,  0.0059944761888, 0.104603983795],
                   [54.23238,   0.01334, 3.14554, -0.00908641901697, 0.317077618256],
                   [53.23243,   0.00439, 3.15553, -0.0133394325756, 0.197189529136],
                   [52.23249,  -0.00728, 3.15101, -0.00439428924579, -0.0902342574893],
                   [51.23251,  -0.01037, 3.13835,  0.0072833796057, -0.247998828829],
                   [50.23253,  -0.00335, 3.13079,  0.0103690153199, -0.149974688913],
                   [49.23257,   0.00565, 3.13439,  0.0033467337216, 0.0718668867589],
                   [48.23258,   0.00801, 3.14409, -0.00565345739415, 0.191537440678],
                   [47.23260,   0.00261, 3.14988, -0.00800612633662, 0.115351297503],
                   [46.23262,  -0.00430, 3.14714, -0.00261433358108, -0.0547335555224],
                   [45.23262,  -0.00616, 3.13975,  0.00430436988654, -0.14682425088],
                   [44.23263,  -0.00207, 3.13527,  0.00615620659715, -0.0893396166308],
                   [43.23265,   0.00324, 3.13730,  0.00207139975038, 0.0405581051979],
                   [42.23265,   0.00472, 3.14292, -0.00323833874279, 0.112029464825],
                   [41.23266,   0.00165, 3.14640, -0.00472107891341, 0.0694518916933],
                   [40.23266,  -0.00242, 3.14492, -0.00165222082347, -0.0295106631143],
                   [39.23267,  -0.00361, 3.14065,  0.00241774560743, -0.0852269525379],
                   [38.23267,  -0.00132, 3.13795,  0.00361389397082, -0.0540811651591],
                   [37.23267,   0.00180, 3.13901,  0.00132084978213, 0.021187165009],
                   [36.23267,   0.00276, 3.14225, -0.00179578232701, 0.0647073049072],
                   [35.23268,   0.00106, 3.14435, -0.00276271648232, 0.042131177153],
                   [34.23268,  -0.00171, 3.14360, -0.00105580510632, -0.0150456195769],
                   [33.23268,  -0.00225, 3.14067,  0.00170500698199, -0.0584622511446],
                   [32.23268,  -0.00057, 3.13914,  0.00225026092966, -0.0306814185115],
                   [31.23268,   0.00189, 3.14012,  0.00056501614813, 0.0196285102416],
                   [30.23269,   0.00197, 3.14291, -0.00188750337406, 0.0556628265735],
                   [29.23269,   0.00013, 3.14395, -0.00196546411848, 0.0208240523512],
                   [28.23269,  -0.00157, 3.14264, -0.000129739790282, -0.0262384670202],
                   [27.23269,  -0.00158, 3.14058,  0.0015705490332, -0.0412098226843],
                   [26.23269,  -0.00057, 3.13977,  0.00158389737652, -0.0160391989149],
                   [25.23269,   0.00125, 3.14025,  0.000566416729579, 0.00959804240832],
                   [24.23269,   0.00160, 3.14225, -0.00125309181144, 0.0398235462297],
                   [23.23272,   0.00795, 3.12823,  0.010176670085, -0.273213129297],
                   [22.23356,   0.04629, 3.07823,  0.0544582132708, -1.20880528049],
                   [21.23756,   0.13453, 3.02823,  0.106585224842, -1.84775742199],
                   [20.24722,   0.27243, 2.97823,  0.148510752479, -2.11399043935],
                   [19.26501,   0.45966, 2.92823,  0.18018118035, -2.27686822155],
                   [18.29339,   0.69574, 2.87823,  0.201556128092, -2.33618549704],
                   [17.33477,   0.98009, 2.82823,  0.212608400704, -2.29186809622],
                   [16.39157,   1.31200, 2.77823,  0.213323954952, -2.14397286324],
                   [15.46614,   1.69063, 2.72823,  0.20370188207, -1.89268772747],
                   [14.56078,   2.11503, 2.67823,  0.183754406642, -1.538331935],
                   [13.67777,   2.58416, 2.62823,  0.153506901656, -1.08135644178],
                   [12.81386,   3.08774, 2.59945,  0.112997919834, -0.522344470993],
                   [11.95891,   3.60644, 2.59306,  0.0728812479575, -0.127062401435],
                   [11.10943,   4.13405, 2.57855,  0.055029658025, -0.282522731263],
                   [10.27749,   4.68873, 2.52855,  0.0666299690776, -0.840304356566],
                   [9.47431,    5.28429, 2.47855,  0.0858577846849, -1.14699508096],
                   [8.70190,    5.91925, 2.42855,  0.0949468071368, -1.08580340815],
                   [7.96219,    6.59202, 2.37855,  0.0938853386001, -0.922931357951],
                   [7.25300,    7.29696, 2.33986,  0.0826747447657, -0.658588540142],
                   [6.56594,    8.02352, 2.31666,  0.0669828880784, -0.434451030473],
                   [5.89748,    8.76723, 2.28927,  0.0602323635014, -0.50106576636],
                   [5.25833,    9.53618, 2.23927,  0.068090106661, -0.798767214002],
                   [4.65842,   10.33611, 2.18927,  0.0771445554797, -0.907262287079],
                   [4.09760,   11.16395, 2.14318,  0.0760768029255, -0.744751740941],
                   [3.56835,   12.01237, 2.11389,  0.0668420718692, -0.529899752847],
                   [3.06312,   12.87531, 2.08706,  0.0598078407618, -0.492564941008],
                   [2.58864,   13.75549, 2.04336,  0.0646141854734, -0.718237025407],
                   [2.15592,   14.65690, 1.99336,  0.0740490844614, -0.882014329434],
                   [1.76879,   15.57882, 1.94336,  0.0765170630558, -0.802190309475],
                   [1.41990,   16.51593, 1.91104,  0.0688639753062, -0.573843436817],
                   [1.09806,   17.46270, 1.88592,  0.0599391054845, -0.46551800752],
                   [0.80649,   18.41918, 1.84745,  0.0621975613471, -0.655852451411],
                   [0.55751,   19.38759, 1.79745,  0.0725586273996, -0.881002264782],
                   [0.35725,   20.36722, 1.74745,  0.0785658596796, -0.875767080996],
                   [0.20157,   21.35496, 1.70679,  0.0744488545842, -0.682733469412],
                   [0.07972,   22.34748, 1.67912,  0.064882834359, -0.505338040211],
                   [-0.01304,  23.34313, 1.64826,  0.061049873916, -0.553004332516],
                   [-0.06571,  24.34164, 1.59874,  0.0678549982968, -0.780626848679],
                   [-0.06865,  25.34153, 1.54874,  0.0743567249518, -0.841093149344],
                   [-0.02724,  26.34061, 1.51000,  0.0709782942256, -0.659106481363],
                   [0.04757,   27.33777, 1.48182,  0.063119460403, -0.513312096691],
                   [0.15330,   28.33212, 1.44793,  0.0616984523553, -0.595669402838],
                   [0.30061,   29.32110, 1.39793,  0.0691393621112, -0.80300726745],
                   [0.49717,   30.30149, 1.34793,  0.0745240211471, -0.82601009701],
                   [0.73581,   31.27254, 1.31171,  0.0697908818285, -0.626911728507],
                   [1.00515,   32.23555, 1.28446,  0.061835776281, -0.499031179596],
                   [1.30478,   33.18955, 1.24849,  0.0620441221825, -0.623566410349],
                   [1.64511,   34.12975, 1.19849,  0.0705426713923, -0.832904952069],
                   [2.03201,   35.05176, 1.14849,  0.0759450662275, -0.840486584804],
                   [2.45881,   35.95604, 1.11115,  0.0712274025672, -0.641509070767],
                   [2.91462,   36.84608, 1.08385,  0.0627231024301, -0.499666522244],
                   [3.39770,   37.72160, 1.04934,  0.0617977174441, -0.604096399653],
                   [3.91731,   38.57588, 0.99934,  0.0698708459364, -0.819805386748],
                   [4.47896,   39.40313, 0.94934,  0.0755772432128, -0.841368391275],
                   [5.07634,   40.20501, 0.91169,  0.0711641624636, -0.645445413398],
                   [5.69954,   40.98703, 0.88419,  0.0628108807278, -0.50280958124],
                   [6.34663,   41.74939, 0.84981,  0.061780505889, -0.60234943631],
                   [7.02525,   42.48373, 0.79981,  0.0697109430389, -0.816065987638],
                   [7.73973,   43.18325, 0.74981,  0.0753393241485, -0.837818958128],
                   [8.48409,   43.85094, 0.71250,  0.0708486070103, -0.641125313031],
                   [9.24969,   44.49420, 0.68506,  0.0625868605359, -0.501942408244],
                   [10.03491,  45.11334, 0.65031,  0.0618453130503, -0.607329918217],
                   [10.84561,  45.69863, 0.60031,  0.0699086727467, -0.820037122913],
                   [11.68454,  46.24266, 0.55031,  0.0754856765425, -0.838511822363],
                   [12.54647,  46.74959, 0.51298,  0.0709433501728, -0.641298606182],
                   [13.42437,  47.22836, 0.48557,  0.0626230836657, -0.50142683905],
                   [14.31669,  47.67965, 0.45089,  0.0618329632451, -0.606477826142],
                   [15.22727,  48.09274, 0.40089,  0.0698961031285, -0.819908129536],
                   [16.15735,  48.45980, 0.35089,  0.0755044674977, -0.839170140515],
                   [17.10263,  48.78589, 0.31349,  0.0709934713204, -0.642269770544],
                   [18.05800,  49.08119, 0.28606,  0.0626666272713, -0.501763611977],
                   [19.02206,  49.34670, 0.25144,  0.0618210713724, -0.605527375241],
                   [19.99643,  49.57119, 0.20144,  0.0698530204273, -0.819009440096],
                   [20.98080,  49.74670, 0.15144,  0.0754654315531, -0.83884048242],
                   [21.97194,  49.87905, 0.11406,  0.0709585441457, -0.641982130346],
                   [22.96688,  49.97922, 0.08663,  0.0626470778005, -0.501798782828],
                   [23.96443,  50.04847, 0.05198,  0.0618270031005, -0.605968910504],
                   [24.96396,  50.07545, 0.00198,  0.0698669464503, -0.819268614751],
                   [25.96359,  50.05243, 6.23517,  0.0754709995844, -0.838770792854],
                   [26.96221,  49.99992, 6.22613,  0.0524312264672, -0.178715667915],
                   [27.96159,  49.96788, 6.27613, -7.88150333264e-05, 0.788438772841],
                   [28.96133,  49.98583, 0.04295, -0.0321204459081, 0.801828922202],
                   [29.96054,  50.02556, 0.03654, -0.0141737350406, -0.127463312606],
                   [30.96036,  50.03710, 6.26973,  0.0255613245898, -0.851639140353],
                   [31.95992,  50.00852, 6.23947,  0.0371015043079, -0.54411773885],
                   [32.95930,  49.97376, 6.25736,  0.00852210437821, 0.343469955163],
                   [33.95920,  49.97285, 0.02401, -0.0262396838876, 0.783823662862],
                   [34.95870,  50.00419, 0.03867, -0.027146301648, 0.285062282885],
                   [35.95836,  50.02881, 0.01057,  0.0041890553431, -0.511920908297],
                   [36.95826,  50.02008, 6.25517,  0.0288055233431, -0.657302253432],
                   [37.95782,  49.99032, 6.25166,  0.0200840750532, -0.0700190261819],
                   [38.95764,  49.97389, 6.28186, -0.00968173524194, 0.543304506846],
                   [39.95753,  49.98647, 0.02647, -0.0261056767725, 0.507415890685],
                   [40.95722,  50.01160, 0.02381, -0.0135341819208, -0.0532306035686],
                   [41.95713,  50.02198, 6.28013,  0.0116026444912, -0.493078841091],
                   [42.95703,  50.00907, 6.26042,  0.0219758686422, -0.375357048688],
                   [43.95683,  49.98889, 6.26559,  0.00906544713366, 0.103001851292],
                   [44.95679,  49.98227, 0.00436, -0.0111109337112, 0.413755049785],
                   [45.95671,  49.99373, 0.01855, -0.0177267604396, 0.276505005322],
                   [46.95659,  50.00954, 0.01307, -0.00627118895443, -0.109121682734],
                   [47.95656,  50.01398, 6.27899,  0.00953948171244, -0.332554877127],
                   [48.95652,  50.00455, 6.26852,  0.0139772893026, -0.20634000688],
                   [49.95644,  49.99229, 6.27334,  0.0045478208322, 0.0959638187346],
                   [50.95643,  49.98912, 0.00350, -0.00770800319705, 0.260917392409],
                   [51.95640,  49.99656, 0.01139, -0.0108825274272, 0.156443137725],
                   [52.95635,  50.00601, 0.00752, -0.00343876510277, -0.0772687838393],
                   [53.95634,  50.00841, 6.28047,  0.00601266651859, -0.201898139506],
                   [54.95633,  50.00268, 6.27443,  0.0084114853929, -0.120097137044],
                   [55.95630,  49.99541, 6.27740,  0.00267623660709, 0.0592663657163],
                   [56.95629,  49.99353, 0.00203, -0.00459253647864, 0.154956961072],
                   [57.95628,  49.99788, 0.00668, -0.00647274278703, 0.092930522496],
                   [58.95627,  50.00346, 0.00448, -0.00211776727409, -0.0441469599532],
                   [59.95627,  50.00497, 6.28172,  0.0034627784936, -0.118335971451],
                   [60.95626,  50.00169, 6.27810,  0.00496667372275, -0.0722251656647],
                   [61.95625,  49.99741, 6.27971,  0.00168951771067, 0.0322621630744],
                   [62.95625,  49.99620, 0.00104, -0.00258957378412, 0.0900821102631],
                   [63.95625,  49.99865, 0.00386, -0.00380367920818, 0.0562483734426],
                   [64.95624,  50.00193, 0.00270, -0.00135193075016, -0.0232569193686],
                   [65.95624,  50.00291, 6.28245,  0.0019259813256, -0.0684284943924],
                   [66.95624,  50.00108, 6.28026,  0.00290898349863, -0.0438348675817],
                   [67.95623,  49.99816, 6.28109,  0.00108202607595, 0.0165841005807],
                   [68.95623,  49.99762, 0.00102, -0.00184150269827, 0.062267958596],
                   [69.95623,  49.99944, 0.00261, -0.00237704031872, 0.031803467494],
                   [70.95623,  50.00151, 0.00153, -0.000558510494557, -0.0216928424169],
                   [71.95623,  50.00189, 6.28240,  0.00151296765796, -0.0462018488673],
                   [72.95623,  50.00049, 6.28118,  0.0018861723749, -0.024459794503],
                   [73.95623,  49.99849, 6.28198,  0.000491892099603, 0.0159952831333],
                   [74.95623,  49.99841, 0.00106, -0.00151400420956, 0.0452284867331],
                   [75.95622,  49.99947, 0.00191, -0.00158858567727, 0.0170045787883],
                   [76.95614,  49.98875, 6.25985,  0.0177493318554, -0.467562081545],
                   [77.95487,  49.94044, 6.20985,  0.0652006841674, -1.36377712635],
                   [78.94993,  49.84227, 6.15985,  0.114871389698, -1.89377447994],
                   [79.93885,  49.69449, 6.10985,  0.154330833199, -2.1351999845],
                   [80.91914,  49.49747, 6.05985,  0.183528577596, -2.27325194192],
                   [81.88836,  49.25170, 6.00985,  0.202427406192, -2.30775649085],
                   [82.84409,  48.95780, 5.95985,  0.211003276553, -2.23867082094],
                   [83.78393,  48.61650, 5.90985,  0.209245290847, -2.06608312289],
                   [84.70554,  48.22866, 5.85985,  0.197155682431, -1.79021269806],
                   [85.60662,  47.79523, 5.80985,  0.174749818594, -1.41141022838],
                   [86.48491,  47.31732, 5.75985,  0.142056219486, -0.930158208258],
                   [87.34650,  46.80974, 5.74176,  0.0991165933539, -0.347071541551],
                   [88.20268,  46.29306, 5.73868,  0.0619345735952, -0.061615439572],
                   [89.05217,  45.76550, 5.71623,  0.0540416639161, -0.422022993975],
                   [89.88193,  45.20757, 5.66623,  0.0732859304075, -1.02152330145],
                   [90.68278,  44.60887, 5.61623,  0.0961759668563, -1.3051102153],
                   [91.45269,  43.97089, 5.56623,  0.108909091119, -1.28008777513],
                   [92.18976,  43.29523, 5.51623,  0.111468938951, -1.15308710698],
                   [92.89214,  42.58357, 5.46623,  0.103852222567, -0.924271479924],
                   [93.56415,  41.84309, 5.43246,  0.0860687266534, -0.593934827824],
                   [94.21636,  41.08507, 5.41333,  0.0662586576726, -0.365435542015],
                   [94.85070,  40.31206, 5.38580,  0.0598878893147, -0.503317367779],
                   [95.45455,  39.51510, 5.33580,  0.0700868865737, -0.853853824622],
                   [96.01783,  38.68895, 5.28580,  0.0814050927512, -0.983824020175],
                   [96.53911,  37.83569, 5.23580,  0.082593979722, -0.843773101782],
                   [97.02396,  36.96115, 5.20142,  0.0736520157675, -0.602390698357],
                   [97.48288,  36.07270, 5.17695,  0.0623989742911, -0.455194120765],
                   [97.91538,  35.17112, 5.14241,  0.0616151448255, -0.604394006271],
                   [98.30938,  34.25213, 5.09241,  0.0712283823848, -0.856482387238],
                   [98.65696,  33.31459, 5.04241,  0.0784612214397, -0.893104800221],
                   [98.96051,  32.36185, 4.99924,  0.0755699326907, -0.712329995672],
                   [99.22981,  31.39883, 4.97089,  0.0659683285949, -0.515659224511],
                   [99.47148,  30.42851, 4.94207,  0.060499146932, -0.522953744377],
                   [99.67633,  29.44981, 4.89538,  0.0663487794693, -0.751232282754],
                   [99.83364,  28.46236, 4.84538,  0.0743309177548, -0.863041251831],
                   [99.94397,  27.46855, 4.80052,  0.0738476180698, -0.731226685423],
                   [100.01712, 26.47127, 4.77070,  0.06581874208, -0.537754280953],
                   [100.06106, 25.47227, 4.74198,  0.0603453339137, -0.521352216643],
                   [100.06816, 24.47238, 4.69701,  0.0655052215747, -0.732450530661],
                   [100.02781, 23.47330, 4.64701,  0.0737162488022, -0.860327896434],
                   [99.93915,  22.47733, 4.60021,  0.0743266100954, -0.752421520353],
                   [99.81215,  21.48546, 4.56986,  0.0664158372503, -0.545496779826],
                   [99.65662,  20.49766, 4.54259,  0.0598209154029, -0.499285326319],
                   [99.46649,  19.51598, 4.49955,  0.0643209437393, -0.710709862439],
                   [99.23092,  18.54423, 4.44955,  0.0735626584842, -0.874252306016],
                   [98.94707,  17.58547, 4.39955,  0.0761679232528, -0.800758204058],
                   [98.62399,  16.63914, 4.36724,  0.0686526872129, -0.57379833153],
                   [98.27383,  15.70248, 4.34203,  0.0598676561009, -0.466901094329],
                   [97.89398,  14.77750, 4.30342,  0.0622243638759, -0.657594255385],
                   [97.47355,  13.87029, 4.25342,  0.0725708939324, -0.88090689017],
                   [97.00830,  12.98523, 4.20342,  0.0784941805008, -0.873791103535],
                   [96.50351,  12.12207, 4.16299,  0.0742933459133, -0.679920940321]]
                   

class MotionTest(unittest.TestCase):
    
    def test_racetrack(self):
        radius = 25.0
        params = [10.0, 15.0, 0.0]

        myrobot = robot()
        myrobot.set(0.0, radius, pi / 2.0)
        speed = 1.0 # motion distance is equal to speed (we assume time = 1)
        err = 0.0
        int_crosstrack_error = 0.0
        N = 200
    
        crosstrack_error = myrobot.cte(radius)
    
        for i in range(N*2):
            diff_crosstrack_error = - crosstrack_error
            crosstrack_error = myrobot.cte(radius)
            diff_crosstrack_error += crosstrack_error
            int_crosstrack_error += crosstrack_error
            steer = - params[0] * crosstrack_error \
                    - params[1] * diff_crosstrack_error \
                    - params[2] * int_crosstrack_error
            myrobot = myrobot.move(steer, speed)
            if i >= N:
                err += crosstrack_error ** 2

            self.assertAlmostEqual(expected_values[i][0], myrobot.x, 3,
                                   "Robot X coordinate differs at point %d: "
                                   "expected %.3f, got %.3f" % (i, expected_values[i][0], myrobot.x))
            self.assertAlmostEqual(expected_values[i][1], myrobot.y, 3,
                                   "Robot Y coordinate differs at point %d: "
                                   "expected %.3f, got %.3f" % (i, expected_values[i][1], myrobot.x))
            self.assertAlmostEqual(expected_values[i][2], myrobot.orientation, 3,
                                   "Robot orientation coordinate differs at point %d: "
                                   "expected %.3f, got %.3f" % (i, expected_values[i][2], myrobot.x))
            self.assertAlmostEqual(expected_values[i][3], crosstrack_error, 3,
                                   "Crosstrack error differs at point %d: "
                                   "expected %.3f, got %.3f" % (i, expected_values[i][3], myrobot.x))
            self.assertAlmostEqual(expected_values[i][4], steer, 3,
                                   "Steering angle differs at point %d: "
                                   "expected %.3f, got %.3f" % (i, expected_values[i][4], myrobot.x))
        result = err / float(N)

        expected_result = 0.00586850481282
        if result < expected_result:
            print "INFO: your result %.14f is less than expected %.14f " % (result, expected_result), \
                  "therefore it might be accepted"
        self.assertAlmostEqual(result, expected_result, 5,
                               "Your average CTE differs from the expected one. "
                               "Expected %.5f, got %.5f" % (expected_result, result))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = task
# ------------
# User Instructions
#
# In this problem you will implement a more manageable
# version of graph SLAM in 2 dimensions. 
#
# Define a function, online_slam, that takes 5 inputs:
# data, N, num_landmarks, motion_noise, and
# measurement_noise--just as was done in the last 
# programming assignment of unit 6. This function
# must return TWO matrices, mu and the final Omega.
#
# Just as with the quiz, your matrices should have x
# and y interlaced, so if there were two poses and 2
# landmarks, mu would look like:
#
# mu = matrix([[Px0],
#              [Py0],
#              [Px1],
#              [Py1],
#              [Lx0],
#              [Ly0],
#              [Lx1],
#              [Ly1]])
#
# Enter your code at line 566.

# -----------
# Testing
#
# You have two methods for testing your code.
#
# 1) You can make your own data with the make_data
#    function. Then you can run it through the
#    provided slam routine and check to see that your
#    online_slam function gives the same estimated
#    final robot pose and landmark positions.
# 2) You can use the solution_check function at the
#    bottom of this document to check your code
#    for the two provided test cases. The grading
#    will be almost identical to this function, so
#    if you pass both test cases, you should be
#    marked correct on the homework.

from math import *
import random


# ------------------------------------------------
# 
# this is the matrix class
# we use it because it makes it easier to collect constraints in GraphSLAM
# and to calculate solutions (albeit inefficiently)
# 

class matrix:
    
    # implements basic operations of a matrix class

    # ------------
    #
    # initialization - can be called with an initial matrix
    #

    def __init__(self, value = [[]]):
        self.value = value
        self.dimx  = len(value)
        self.dimy  = len(value[0])
        if value == [[]]:
            self.dimx = 0
            
    # -----------
    #
    # defines matrix equality - returns true if corresponding elements
    #   in two matrices are within epsilon of each other.
    #
    
    def __eq__(self, other):
        epsilon = 0.01
        if self.dimx != other.dimx or self.dimy != other.dimy:
            return False
        for i in range(self.dimx):
            for j in range(self.dimy):
                if abs(self.value[i][j] - other.value[i][j]) > epsilon:
                    return False
        return True
    
    def __ne__(self, other):
        return not (self == other)

    # ------------
    #
    # makes matrix of a certain size and sets each element to zero
    #

    def zero(self, dimx, dimy):
        if dimy == 0:
            dimy = dimx
        # check if valid dimensions
        if dimx < 1 or dimy < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dimx
            self.dimy  = dimy
            self.value = [[0.0 for row in range(dimy)] for col in range(dimx)]

    # ------------
    #
    # makes matrix of a certain (square) size and turns matrix into identity matrix
    #

    def identity(self, dim):
        # check if valid dimension
        if dim < 1:
            raise ValueError, "Invalid size of matrix"
        else:
            self.dimx  = dim
            self.dimy  = dim
            self.value = [[0.0 for row in range(dim)] for col in range(dim)]
            for i in range(dim):
                self.value[i][i] = 1.0
                
    # ------------
    #
    # prints out values of matrix
    #

    def show(self, txt = ''):
        for i in range(len(self.value)):
            print txt + '['+ ', '.join('%.3f'%x for x in self.value[i]) + ']' 
        print ' '

    # ------------
    #
    # defines elmement-wise matrix addition. Both matrices must be of equal dimensions
    #

    def __add__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to add"
        else:
            # add if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] + other.value[i][j]
            return res

    # ------------
    #
    # defines elmement-wise matrix subtraction. Both matrices must be of equal dimensions
    #

    def __sub__(self, other):
        # check if correct dimensions
        if self.dimx != other.dimx or self.dimx != other.dimx:
            raise ValueError, "Matrices must be of equal dimension to subtract"
        else:
            # subtract if correct dimensions
            res = matrix()
            res.zero(self.dimx, self.dimy)
            for i in range(self.dimx):
                for j in range(self.dimy):
                    res.value[i][j] = self.value[i][j] - other.value[i][j]
            return res

    # ------------
    #
    # defines multiplication. Both matrices must be of fitting dimensions
    #

    def __mul__(self, other):
        # check if correct dimensions
        if self.dimy != other.dimx:
            raise ValueError, "Matrices must be m*n and n*p to multiply"
        else:
            # multiply if correct dimensions
            res = matrix()
            res.zero(self.dimx, other.dimy)
            for i in range(self.dimx):
                for j in range(other.dimy):
                    for k in range(self.dimy):
                        res.value[i][j] += self.value[i][k] * other.value[k][j]
        return res

    # ------------
    #
    # returns a matrix transpose
    #

    def transpose(self):
        # compute transpose
        res = matrix()
        res.zero(self.dimy, self.dimx)
        for i in range(self.dimx):
            for j in range(self.dimy):
                res.value[j][i] = self.value[i][j]
        return res

    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[ 1,  2,  3,  4,  5], 
    #                   [ 6,  7,  8,  9, 10], 
    #                   [11, 12, 13, 14, 15]])
    #
    #       l.take([0, 2], [0, 2, 3])
    #
    # results in:
    #       
    #       [[1, 3, 4], 
    #        [11, 13, 14]]
    #       
    # 
    # take is used to remove rows and columns from existing matrices
    # list1/list2 define a sequence of rows/columns that shall be taken
    # is no list2 is provided, then list2 is set to list1 (good for symmetric matrices)
    #

    def take(self, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in take()"

        res = matrix()
        res.zero(len(list1), len(list2))
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[i][j] = self.value[list1[i]][list2[j]]
        return res

    # ------------
    #
    # creates a new matrix from the existing matrix elements.
    #
    # Example:
    #       l = matrix([[1, 2, 3],
    #                  [4, 5, 6]])
    #
    #       l.expand(3, 5, [0, 2], [0, 2, 3])
    #
    # results in:
    #
    #       [[1, 0, 2, 3, 0], 
    #        [0, 0, 0, 0, 0], 
    #        [4, 0, 5, 6, 0]]
    # 
    # expand is used to introduce new rows and columns into an existing matrix
    # list1/list2 are the new indexes of row/columns in which the matrix
    # elements are being mapped. Elements for rows and columns 
    # that are not listed in list1/list2 
    # will be initialized by 0.0.
    #

    def expand(self, dimx, dimy, list1, list2 = []):
        if list2 == []:
            list2 = list1
        if len(list1) > self.dimx or len(list2) > self.dimy:
            raise ValueError, "list invalid in expand()"

        res = matrix()
        res.zero(dimx, dimy)
        for i in range(len(list1)):
            for j in range(len(list2)):
                res.value[list1[i]][list2[j]] = self.value[i][j]
        return res

    # ------------
    #
    # Computes the upper triangular Cholesky factorization of  
    # a positive definite matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560

    def Cholesky(self, ztol= 1.0e-5):

        res = matrix()
        res.zero(self.dimx, self.dimx)

        for i in range(self.dimx):
            S = sum([(res.value[k][i])**2 for k in range(i)])
            d = self.value[i][i] - S
            if abs(d) < ztol:
                res.value[i][i] = 0.0
            else: 
                if d < 0.0:
                    raise ValueError, "Matrix not positive-definite"
                res.value[i][i] = sqrt(d)
            for j in range(i+1, self.dimx):
                S = sum([res.value[k][i] * res.value[k][j] for k in range(i)])
                if abs(S) < ztol:
                    S = 0.0
                res.value[i][j] = (self.value[i][j] - S)/res.value[i][i]
        return res 
 
    # ------------
    #
    # Computes inverse of matrix given its Cholesky upper Triangular
    # decomposition of matrix.
    # This code is based on http://adorio-research.org/wordpress/?p=4560

    def CholeskyInverse(self):
    # Computes inverse of matrix given its Cholesky upper Triangular
    # decomposition of matrix.
        # This code is based on http://adorio-research.org/wordpress/?p=4560

        res = matrix()
        res.zero(self.dimx, self.dimx)

    # Backward step for inverse.
        for j in reversed(range(self.dimx)):
            tjj = self.value[j][j]
            S = sum([self.value[j][k]*res.value[j][k] for k in range(j+1, self.dimx)])
            res.value[j][j] = 1.0/ tjj**2 - S/ tjj
            for i in reversed(range(j)):
                res.value[j][i] = res.value[i][j] = \
                    -sum([self.value[i][k]*res.value[k][j] for k in \
                              range(i+1,self.dimx)])/self.value[i][i]
        return res
    
    # ------------
    #
    # comutes and returns the inverse of a square matrix
    #

    def inverse(self):
        aux = self.Cholesky()
        res = aux.CholeskyInverse()
        return res

    # ------------
    #
    # prints matrix (needs work!)
    #

    def __repr__(self):
        return repr(self.value)

# ######################################################################

# ------------------------------------------------
# 
# this is the robot class
# 
# our robot lives in x-y space, and its motion is
# pointed in a random direction. It moves on a straight line
# until is comes close to a wall at which point it turns
# away from the wall and continues to move.
#
# For measurements, it simply senses the x- and y-distance
# to landmarks. This is different from range and bearing as 
# commonly studies in the literature, but this makes it much
# easier to implement the essentials of SLAM without
# cluttered math
#

class robot:

    # --------
    # init: 
    #   creates robot and initializes location to 0, 0
    #

    def __init__(self, world_size = 100.0, measurement_range = 30.0,
                 motion_noise = 1.0, measurement_noise = 1.0):
        self.measurement_noise = 0.0
        self.world_size = world_size
        self.measurement_range = measurement_range
        self.x = world_size / 2.0
        self.y = world_size / 2.0
        self.motion_noise = motion_noise
        self.measurement_noise = measurement_noise
        self.landmarks = []
        self.num_landmarks = 0


    def rand(self):
        return random.random() * 2.0 - 1.0

    # --------
    #
    # make random landmarks located in the world
    #

    def make_landmarks(self, num_landmarks):
        self.landmarks = []
        for i in range(num_landmarks):
            self.landmarks.append([round(random.random() * self.world_size),
                                   round(random.random() * self.world_size)])
        self.num_landmarks = num_landmarks

    # --------
    #
    # move: attempts to move robot by dx, dy. If outside world
    #       boundary, then the move does nothing and instead returns failure
    #

    def move(self, dx, dy):

        x = self.x + dx + self.rand() * self.motion_noise
        y = self.y + dy + self.rand() * self.motion_noise

        if x < 0.0 or x > self.world_size or y < 0.0 or y > self.world_size:
            return False
        else:
            self.x = x
            self.y = y
            return True
    
    # --------
    #
    # sense: returns x- and y- distances to landmarks within visibility range
    #        because not all landmarks may be in this range, the list of measurements
    #        is of variable length. Set measurement_range to -1 if you want all
    #        landmarks to be visible at all times
    #

    def sense(self):
        Z = []
        for i in range(self.num_landmarks):
            dx = self.landmarks[i][0] - self.x + self.rand() * self.measurement_noise
            dy = self.landmarks[i][1] - self.y + self.rand() * self.measurement_noise    
            if self.measurement_range < 0.0 or abs(dx) + abs(dy) <= self.measurement_range:
                Z.append([i, dx, dy])
        return Z

    # --------
    #
    # print robot location
    #

    def __repr__(self):
        return 'Robot: [x=%.5f y=%.5f]'  % (self.x, self.y)


# ######################################################################

# --------
# this routine makes the robot data
#

def make_data(N, num_landmarks, world_size, measurement_range, motion_noise, 
              measurement_noise, distance):

    complete = False

    while not complete:

        data = []

        # make robot and landmarks
        r = robot(world_size, measurement_range, motion_noise, measurement_noise)
        r.make_landmarks(num_landmarks)
        seen = [False for row in range(num_landmarks)]
    
        # guess an initial motion
        orientation = random.random() * 2.0 * pi
        dx = cos(orientation) * distance
        dy = sin(orientation) * distance
    
        for k in range(N-1):
    
            # sense
            Z = r.sense()

            # check off all landmarks that were observed 
            for i in range(len(Z)):
                seen[Z[i][0]] = True
    
            # move
            while not r.move(dx, dy):
                # if we'd be leaving the robot world, pick instead a new direction
                orientation = random.random() * 2.0 * pi
                dx = cos(orientation) * distance
                dy = sin(orientation) * distance

            # memorize data
            data.append([Z, [dx, dy]])

        # we are done when all landmarks were observed; otherwise re-run
        complete = (sum(seen) == num_landmarks)

    print ' '
    print 'Landmarks: ', r.landmarks
    print r

    return data
    
# ######################################################################

# --------------------------------
#
# full_slam - retains entire path and all landmarks
#             Feel free to use this for comparison.
#

def slam(data, N, num_landmarks, motion_noise, measurement_noise):

    # Set the dimension of the filter
    dim = 2 * (N + num_landmarks) 

    # make the constraint information matrix and vector
    Omega = matrix()
    Omega.zero(dim, dim)
    Omega.value[0][0] = 1.0
    Omega.value[1][1] = 1.0

    Xi = matrix()
    Xi.zero(dim, 1)
    Xi.value[0][0] = world_size / 2.0
    Xi.value[1][0] = world_size / 2.0
    
    # process the data

    for k in range(len(data)):

        # n is the index of the robot pose in the matrix/vector
        n = k * 2 
    
        measurement = data[k][0]
        motion      = data[k][1]
    
        # integrate the measurements
        for i in range(len(measurement)):
    
            # m is the index of the landmark coordinate in the matrix/vector
            m = 2 * (N + measurement[i][0])
    
            # update the information maxtrix/vector based on the measurement
            for b in range(2):
                Omega.value[n+b][n+b] +=  1.0 / measurement_noise
                Omega.value[m+b][m+b] +=  1.0 / measurement_noise
                Omega.value[n+b][m+b] += -1.0 / measurement_noise
                Omega.value[m+b][n+b] += -1.0 / measurement_noise
                Xi.value[n+b][0]      += -measurement[i][1+b] / measurement_noise
                Xi.value[m+b][0]      +=  measurement[i][1+b] / measurement_noise


        # update the information maxtrix/vector based on the robot motion
        for b in range(4):
            Omega.value[n+b][n+b] +=  1.0 / motion_noise
        for b in range(2):
            Omega.value[n+b  ][n+b+2] += -1.0 / motion_noise
            Omega.value[n+b+2][n+b  ] += -1.0 / motion_noise
            Xi.value[n+b  ][0]        += -motion[b] / motion_noise
            Xi.value[n+b+2][0]        +=  motion[b] / motion_noise

    # compute best estimate
    mu = Omega.inverse() * Xi

    # return the result
    return mu

# --------------------------------
#
# online_slam - retains all landmarks but only most recent robot pose
#

def online_slam(data, N, num_landmarks, motion_noise, measurement_noise):
    #
    #
    # Enter your code here!
    #
    #
    return mu, Omega # make sure you return both of these matrices to be marked correct.

# --------------------------------
#
# print the result of SLAM, the robot pose(s) and the landmarks
#

def print_result(N, num_landmarks, result):
    print
    print 'Estimated Pose(s):'
    for i in range(N):
        print '    ['+ ', '.join('%.3f'%x for x in result.value[2*i]) + ', ' \
            + ', '.join('%.3f'%x for x in result.value[2*i+1]) +']'
    print 
    print 'Estimated Landmarks:'
    for i in range(num_landmarks):
        print '    ['+ ', '.join('%.3f'%x for x in result.value[2*(N+i)]) + ', ' \
            + ', '.join('%.3f'%x for x in result.value[2*(N+i)+1]) +']'
        
# ------------------------------------------------------------------------
#
# Main routines
#

num_landmarks      = 5        # number of landmarks
N                  = 20       # time steps
world_size         = 100.0    # size of world
measurement_range  = 50.0     # range at which we can sense landmarks
motion_noise       = 2.0      # noise in robot motion
measurement_noise  = 2.0      # noise in the measurements
distance           = 20.0     # distance by which robot (intends to) move each iteratation 


# Uncomment the following three lines to run the full slam routine.

#data = make_data(N, num_landmarks, world_size, measurement_range, motion_noise, measurement_noise, distance)
#result = slam(data, N, num_landmarks, motion_noise, measurement_noise)
#print_result(N, num_landmarks, result)

# Uncomment the following three lines to run the online_slam routine.

#data = make_data(N, num_landmarks, world_size, measurement_range, motion_noise, measurement_noise, distance)
#result = online_slam(data, N, num_landmarks, motion_noise, measurement_noise)
#print_result(1, num_landmarks, result[0])




########NEW FILE########
__FILENAME__ = test
import unittest
from math import *
import random
import task

# -----------
# Test Case 1

testdata1          = [[[[1, 21.796713239511305, 25.32184135169971], [2, 15.067410969755826, -27.599928007267906]], [16.4522379034509, -11.372065246394495]],
                      [[[1, 6.1286996178786755, 35.70844618389858], [2, -0.7470113490937167, -17.709326161950294]], [16.4522379034509, -11.372065246394495]],
                      [[[0, 16.305692184072235, -11.72765549112342], [2, -17.49244296888888, -5.371360408288514]], [16.4522379034509, -11.372065246394495]],
                      [[[0, -0.6443452578030207, -2.542378369361001], [2, -32.17857547483552, 6.778675958806988]], [-16.66697847355152, 11.054945886894709]]]

answer_mu1         = task.matrix([[81.63549976607898],
                             [27.175270706192254],
                             [98.09737507003692],
                             [14.556272940621195],
                             [71.97926631050574],
                             [75.07644206765099],
                             [65.30397603859097],
                             [22.150809430682695]])

answer_omega1      = task.matrix([[0.36603773584905663, 0.0, -0.169811320754717, 0.0, -0.011320754716981133, 0.0, -0.1811320754716981, 0.0],
                             [0.0, 0.36603773584905663, 0.0, -0.169811320754717, 0.0, -0.011320754716981133, 0.0, -0.1811320754716981],
                             [-0.169811320754717, 0.0, 0.6509433962264151, 0.0, -0.05660377358490567, 0.0, -0.40566037735849064, 0.0],
                             [0.0, -0.169811320754717, 0.0, 0.6509433962264151, 0.0, -0.05660377358490567, 0.0, -0.40566037735849064],
                             [-0.011320754716981133, 0.0, -0.05660377358490567, 0.0, 0.6962264150943396, 0.0, -0.360377358490566, 0.0],
                             [0.0, -0.011320754716981133, 0.0, -0.05660377358490567, 0.0, 0.6962264150943396, 0.0, -0.360377358490566],
                             [-0.1811320754716981, 0.0, -0.4056603773584906, 0.0, -0.360377358490566, 0.0, 1.2339622641509433, 0.0],
                             [0.0, -0.1811320754716981, 0.0, -0.4056603773584906, 0.0, -0.360377358490566, 0.0, 1.2339622641509433]])

# -----------
# Test Case 2

testdata2          = [[[[0, 12.637647070797396, 17.45189715769647], [1, 10.432982633935133, -25.49437383412288]], [17.232472057089492, 10.150955955063045]],
                      [[[0, -4.104607680013634, 11.41471295488775], [1, -2.6421937245699176, -30.500310738397154]], [17.232472057089492, 10.150955955063045]],
                      [[[0, -27.157759429499166, -1.9907376178358271], [1, -23.19841267128686, -43.2248146183254]], [-17.10510363812527, 10.364141523975523]],
                      [[[0, -2.7880265859173763, -16.41914969572965], [1, -3.6771540967943794, -54.29943770172535]], [-17.10510363812527, 10.364141523975523]],
                      [[[0, 10.844236516370763, -27.19190207903398], [1, 14.728670653019343, -63.53743222490458]], [14.192077112147086, -14.09201714598981]]]

answer_mu2         = task.matrix([[63.37479912250136],
                             [78.17644539069596],
                             [61.33207502170053],
                             [67.10699675357239],
                             [62.57455560221361],
                             [27.042758786080363]])

answer_omega2      = task.matrix([[0.22871751620895048, 0.0, -0.11351536555795691, 0.0, -0.11351536555795691, 0.0],
                             [0.0, 0.22871751620895048, 0.0, -0.11351536555795691, 0.0, -0.11351536555795691],
                             [-0.11351536555795691, 0.0, 0.7867205207948973, 0.0, -0.46327947920510265, 0.0],
                             [0.0, -0.11351536555795691, 0.0, 0.7867205207948973, 0.0, -0.46327947920510265],
                             [-0.11351536555795691, 0.0, -0.46327947920510265, 0.0, 0.7867205207948973, 0.0],
                             [0.0, -0.11351536555795691, 0.0, -0.46327947920510265, 0.0, 0.7867205207948973]])


##########################################################

class SLAMTest(unittest.TestCase):

    def compare_matrices(self, expected, got, name, precision = 3):
        x = expected
        y = got
        for i, (xrow, yrow) in enumerate(zip(x.value, y.value)):
            for j, (xel, yel) in enumerate(zip(xrow, yrow)):
                self.assertAlmostEqual(xel, yel, precision,
                                       ("The element at (%d, %d) in %s matrix differs: expected %." + 
                                        str(precision+1) + "f, got %." + str(precision+1) + 
                                        "f") % (i, j, name, xel, yel))

    def solution_check(self, result, answer_mu, answer_omega):
        self.assertTrue(len(result) == 2,
                        "Your function doesn't return both matrices mu and Omega")

        user_mu = result[0]
        user_omega = result[1]

        self.assertFalse(user_mu.dimx == answer_omega.dimx and user_mu.dimy == answer_omega.dimy,
                         "It looks like you returned your results in the wrong order. Make sure to return mu then Omega.")

        self.assertFalse(user_mu.dimx != answer_mu.dimx or user_mu.dimy != answer_mu.dimy,
                        "Your mu matrix doesn't have the correct dimensions. Mu should be a %dx%d matrix." % (answer_mu.dimx, answer_mu.dimy))

        self.assertFalse(user_omega.dimx != answer_omega.dimx or user_omega.dimy != answer_omega.dimy,
                        "Your Omega matrix doesn't have the correct dimensions. Mu should be a %dx%d matrix." % (answer_omega.dimx, answer_omega.dimy))

        self.compare_matrices(answer_omega, user_omega, "Omega")
        self.compare_matrices(answer_mu, user_mu, "mu")

    def test_provided1(self):
        result = task.online_slam(testdata1, 5, 3, 2.0, 2.0)
        self.solution_check(result, answer_mu1, answer_omega1)

    def test_provided2(self):
        result = task.online_slam(testdata2, 6, 2, 3.0, 4.0)
        self.solution_check(result, answer_mu2, answer_omega2)

    def test_random(self):
        data = task.make_data(task.N, task.num_landmarks, task.world_size, task.measurement_range, task.motion_noise, task.measurement_noise, task.distance)
        result = task.slam(data, task.N, task.num_landmarks, task.motion_noise, task.measurement_noise)
        online_result = task.online_slam(data, task.N, task.num_landmarks, task.motion_noise, task.measurement_noise)
        mapping = [i - 2 + task.N*2 for i in range(2 * task.num_landmarks)]
        e_result = result.take(mapping, [0])
        self.compare_matrices(e_result, online_result[0], "mu", 2)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
