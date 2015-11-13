__FILENAME__ = center
import networkx as nx
g = nx.read_edgelist('data/facebook/0.edges')
sg = nx.connected_component_subgraphs(g)[0]
center = [node for node in sg.nodes() if nx.eccentricity(sg, node) == nx.radius(sg)]
print(center)

########NEW FILE########
__FILENAME__ = center2
import networkx as nx
g = nx.read_edgelist('data/facebook/0.edges')
sg = nx.connected_component_subgraphs(g)[0]
# we compute the eccentricity once, for all nodes
ecc = nx.eccentricity(sg)
# we compute the radius once
r = nx.radius(sg)
center = [node for node in sg.nodes() if ecc[node] == r]
print(center)

########NEW FILE########
__FILENAME__ = egos
import sys
import os
# we retrieve the folder as the first positional argument
# to the command-line call
if len(sys.argv) > 1:
    folder = sys.argv[1]
# we list all files in the specified folder
files = os.listdir(folder)
# ids contains the sorted list of all unique idenfitiers
ids = sorted(set(map(lambda file: int(file.split('.')[0]), files)))

########NEW FILE########
__FILENAME__ = gui
"""Basic GUI example with PyQt."""
from PyQt4 import QtGui

class HelloWorld(QtGui.QWidget):
    def __init__(self):
        super(HelloWorld, self).__init__()
        # create the button
        self.button = QtGui.QPushButton('Click me', self)
        self.button.clicked.connect(self.clicked)
        # create the layout
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.button)
        self.setLayout(vbox)
        # show the window
        self.show()
        
    def clicked(self):
        msg = QtGui.QMessageBox(self)
        msg.setText("Hello World !")
        msg.show()
        
window = HelloWorld()

########NEW FILE########
__FILENAME__ = psum
from mpi4py import MPI
import numpy as np

# This function will be executed on all processes.
def psum(a):
    # "a" only contains a subset of all integers.
    # They are summed locally on this process. 
    locsum = np.sum(a)

    # We allocate a variable that will contain the final result, that is,
    # the sum of all our integers.
    rcvBuf = np.array(0.0,'d')

    # We use a MPI reduce operation:
    #   * locsum is combined from all processes
    #   * these local sums are summed with the MPI.SUM operation
    #   * the result (total sum) is distributed back to all processes in
    #     the rcvBuf variable
    MPI.COMM_WORLD.Allreduce([locsum, MPI.DOUBLE],
        [rcvBuf, MPI.DOUBLE],
        op=MPI.SUM)
    return rcvBuf

########NEW FILE########
__FILENAME__ = cppmagic
import IPython.core.magic as ipym

@ipym.magics_class
class CppMagics(ipym.Magics):
    @ipym.cell_magic
    def cpp(self, line, cell=None):
        """Compile, execute C++ code, and return the standard output."""
        # Define the source and executable filenames.
        source_filename = 'temp.cpp'
        program_filename = 'temp.exe'
        # Write the code contained in the cell to the C++ file.
        with open(source_filename, 'w') as f:
            f.write(cell)
        # Compile the C++ code into an executable.
        compile = self.shell.getoutput("g++ {0:s} -o {1:s}".format(
            source_filename, program_filename))
        # Execute the executable and return the output.
        output = self.shell.getoutput(program_filename)
        return output

def load_ipython_extension(ipython):
    ipython.register_magics(CppMagics)

########NEW FILE########
__FILENAME__ = myscript
import numpy as np
import matplotlib.pyplot as plt
def myfun():
    dx = np.random.randn(1000, 10000)
    x = np.sum(dx, axis=0)
    plt.hist(x, bins=np.linspace(-100, 100, 20))
    
########NEW FILE########
