__FILENAME__ = add_expr
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
from cvxpy.expressions.expression import Expression
from cvxpy.expressions.constants import Constant
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
import operator as op

class AddExpression(AffAtom):
    """The sum of any number of expressions.
    """

    def __init__(self, terms):
        # TODO call super class init?
        self._dcp_attr = reduce(op.add, [t._dcp_attr for t in terms])
        # Promote args to the correct size.
        terms = [self._promote(t) for t in terms]
        self.args = []
        for term in terms:
            self.args += self.expand_args(term)
        self.subexpressions = self.args

    def expand_args(self, expr):
        """Helper function to extract the arguments from an AddExpression.
        """
        if isinstance(expr, AddExpression):
            return expr.args
        else:
            return [expr]

    def name(self):
        result = str(self.args[0])
        for i in xrange(1, len(self.args)):
            result += " + " + str(self.args[i])
        return result

    def numeric(self, values):
        return reduce(op.add, values)

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Sum the linear expressions.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.sum_expr(arg_objs), [])

    def _promote(self, expr):
        """Promote a scalar expression to a matrix.

        Parameters
        ----------
        expr : Expression
            The expression to promote.
        rows : int
            The number of rows in the promoted matrix.
        cols : int
            The number of columns in the promoted matrix.

        Returns
        -------
        Expression
            An expression with size (rows, cols).

        """
        if expr.size == (1, 1) and expr.size != self.size:
            ones = Constant(intf.DEFAULT_INTERFACE.ones(*self.size))
            return ones*expr
        else:
            return expr

########NEW FILE########
__FILENAME__ = affine_atom
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import cvxpy.utilities as u
from cvxpy.atoms.atom import Atom
import operator as op

class AffAtom(Atom):
    """ Abstract base class for affine atoms. """
    __metaclass__ = abc.ABCMeta
    # The curvature of the atom if all arguments conformed to DCP.
    def func_curvature(self):
        return u.Curvature.AFFINE

    def sign_from_args(self):
        """By default, the sign is the most general of all the argument signs.
        """
        arg_signs = [arg._dcp_attr.sign for arg in self.args]
        return reduce(op.add, arg_signs)

    # Doesn't matter for affine atoms.
    def monotonicity(self):
        return len(self.args)*[u.monotonicity.INCREASING]

########NEW FILE########
__FILENAME__ = binary_operators
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from affine_atom import AffAtom
import cvxpy.interface as intf
from ...expressions.constants import Constant
import cvxpy.lin_ops.lin_utils as lu
import operator as op
import numpy as np

class BinaryOperator(AffAtom):
    """
    Base class for expressions involving binary operators.

    """
    def __init__(self, lh_exp, rh_exp):
        super(BinaryOperator, self).__init__(lh_exp, rh_exp)

    def name(self):
        return ' '.join([self.args[0].name(),
                         self.OP_NAME,
                         self.args[1].name()])

    # Applies the binary operator to the values.
    def numeric(self, values):
        return reduce(self.OP_FUNC, values)

    # Sets the sign, curvature, and shape.
    def init_dcp_attr(self):
        self._dcp_attr = self.OP_FUNC(self.args[0]._dcp_attr,
                                      self.args[1]._dcp_attr)

    # Validate the dimensions.
    def validate_arguments(self):
        self.OP_FUNC(self.args[0].shape, self.args[1].shape)

class MulExpression(BinaryOperator):
    OP_NAME = "*"
    OP_FUNC = op.mul

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Multiply the linear expressions.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.mul_expr(arg_objs[0], arg_objs[1], size), [])

class DivExpression(BinaryOperator):
    OP_NAME = "/"
    OP_FUNC = op.div

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Multiply the linear expressions.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.div_expr(arg_objs[0], arg_objs[1]), [])

########NEW FILE########
__FILENAME__ = conv
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
import numpy as np

class conv(AffAtom):
    """ 1D discrete convolution of two vectors.
    """
    # TODO work with right hand constant.
    def __init__(self, lh_expr, rh_expr):
        super(conv, self).__init__(lh_expr, rh_expr)

    @AffAtom.numpy_numeric
    def numeric(self, values):
        """Convolve the two values.
        """
        # Convert values to 1D.
        values = map(intf.from_2D_to_1D, values)
        return np.convolve(values[0], values[1])

    def validate_arguments(self):
        """Checks that both arguments are vectors, and the first is constant.
        """
        if not self.args[0].is_vector() or not self.args[1].is_vector():
            raise TypeError("The arguments to conv must resolve to vectors." )
        if not self.args[0].is_constant():
            raise TypeError("The first argument to conv must be constant.")

    def shape_from_args(self):
        """The sum of the argument dimensions - 1.
        """
        lh_length = self.args[0].size[0]
        rh_length = self.args[1].size[0]
        return u.Shape(lh_length + rh_length - 1, 1)

    def sign_from_args(self):
        """Always unknown.
        """
        return u.Sign.UNKNOWN

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Convolve two vectors.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.conv(arg_objs[0], arg_objs[1], size), [])

########NEW FILE########
__FILENAME__ = hstack
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.affine.affine_atom import AffAtom
from cvxpy.atoms.affine.index import index
import numpy as np

class hstack(AffAtom):
    """ Horizontal concatenation """
    # Returns the hstack of the values.
    @AffAtom.numpy_numeric
    def numeric(self, values):
        return np.hstack(values)

    # The shape is the common height and the sum of the widths.
    def shape_from_args(self):
        cols = sum(arg.size[1] for arg in self.args)
        rows = self.args[0].size[0]
        return u.Shape(rows, cols)

    # All arguments must have the same height.
    def validate_arguments(self):
        arg_cols = [arg.size[0] for arg in self.args]
        if max(arg_cols) != min(arg_cols):
            raise TypeError( ("All arguments to hstack must have "
                              "the same number of rows.") )

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Stack the expressions horizontally.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        X = lu.create_var(size)
        constraints = []
        # Create an equality constraint for each arg.
        offset = 0
        for arg in arg_objs:
            index.block_eq(X, arg, constraints,
                           0, size[0],
                           offset, arg.size[1] + offset)
            offset += arg.size[1]
        return (X, constraints)

########NEW FILE########
__FILENAME__ = index
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
from cvxpy.utilities import key_utils as ku
import cvxpy.lin_ops.lin_utils as lu

class index(AffAtom):
    """ Indexing/slicing into a matrix. """
    # expr - the expression indexed/sliced into.
    # key - the index/slicing key (i.e. expr[key[0],key[1]]).
    def __init__(self, expr, key):
        # Format and validate key.
        self.key = ku.validate_key(key, expr.shape)
        super(index, self).__init__(expr)

    # The string representation of the atom.
    def name(self):
        return self.args[0].name() + "[%s, %s]" % ku.to_str(self.key)

    # Returns the index/slice into the given value.
    @AffAtom.numpy_numeric
    def numeric(self, values):
        return values[0][self.key]

    def shape_from_args(self):
        """Returns the shape of the index expression.
        """
        return u.Shape(*ku.size(self.key, self.args[0].shape))

    def get_data(self):
        """Returns the (row slice, column slice).
        """
        return self.key

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Index into the expression.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data : tuple
            A tuple of slices.

        Returns
        -------
        tuple
            (LinOp, [constraints])
        """
        obj = lu.index(arg_objs[0], size, data)
        return (obj, [])

    @staticmethod
    def get_index(matrix, constraints, row, col):
        """Returns a canonicalized index into a matrix.

        Parameters
        ----------
        matrix : LinOp
            The matrix to be indexed.
        constraints : list
            A list of constraints to append to.
        row : int
            The row index.
        col : int
            The column index.
        """
        key = (ku.index_to_slice(row),
               ku.index_to_slice(col))
        idx, idx_constr = index.graph_implementation([matrix],
                                                     (1, 1),
                                                     key)
        constraints += idx_constr
        return idx

    @staticmethod
    def block_eq(matrix, block, constraints,
                 row_start, row_end, col_start, col_end):
        """Adds an equality setting a section of the matrix equal to block.

        Assumes block does not need to be promoted.

        Parameters
        ----------
        matrix : LinOp
            The matrix in the block equality.
        block : LinOp
            The block in the block equality.
        constraints : list
            A list of constraints to append to.
        row_start : int
            The first row of the matrix section.
        row_end : int
            The last row + 1 of the matrix section.
        col_start : int
            The first column of the matrix section.
        col_end : int
            The last column + 1 of the matrix section.
        """
        key = (slice(row_start, row_end, None),
               slice(col_start, col_end, None))
        rows = row_end - row_start
        cols = col_end - col_start
        assert block.size == (rows, cols)
        slc, idx_constr = index.graph_implementation([matrix],
                                                     (rows, cols),
                                                     key)
        constraints += [lu.create_eq(slc, block)] + idx_constr

########NEW FILE########
__FILENAME__ = mul_elemwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
import numpy as np

class mul_elemwise(AffAtom):
    """ Multiplies two expressions elementwise.

    The first expression must be constant.
    """

    def __init__(self, lh_const, rh_expr):
        super(mul_elemwise, self).__init__(lh_const, rh_expr)

    @AffAtom.numpy_numeric
    def numeric(self, values):
        """Multiplies the values elementwise.
        """
        return np.multiply(values[0], values[1])

    def validate_arguments(self):
        """Checks that the arguments are valid.

           Left-hand argument must be constant.
        """
        if not self.args[0].is_constant():
            raise ValueError( ("The first argument to mul_elemwise must "
                               "be constant.") )

    def init_dcp_attr(self):
        """Sets the sign, curvature, and shape.
        """
        self._dcp_attr = u.DCPAttr.mul_elemwise(
            self.args[0]._dcp_attr,
            self.args[1]._dcp_attr,
        )

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Multiply the expressions elementwise.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        # Promote arguments if necessary.
        for i, arg in enumerate(arg_objs):
            if arg.size != size:
                arg_objs[i] = lu.promote(arg, size)

        return (lu.mul_elemwise(arg_objs[0], arg_objs[1]), [])

########NEW FILE########
__FILENAME__ = reshape
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
import numpy as np

class reshape(AffAtom):
    """ Reshapes the expression.

    Vectorizes the expression then unvectorizes it into the new shape.
    The entries are stored in column-wise order.
    """
    def __init__(self, expr, rows, cols):
        self.rows = rows
        self.cols = cols
        super(reshape, self).__init__(expr)

    @AffAtom.numpy_numeric
    def numeric(self, values):
        """Reshape the value.
        """
        return np.reshape(values[0], (self.rows, self.cols), "F")

    def validate_arguments(self):
        """Checks that the new shape has the same number of entries as the old.
        """
        old_len = self.args[0].size[0]*self.args[0].size[1]
        new_len = self.rows*self.cols
        if not old_len == new_len:
            raise ValueError(
                "Invalid reshape dimensions (%i, %i)." % (self.rows, self.cols)
            )

    def shape_from_args(self):
        """Returns the shape from the rows, cols arguments.
        """
        return u.Shape(self.rows, self.cols)

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Convolve two vectors.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.reshape(arg_objs[0], size), [])

########NEW FILE########
__FILENAME__ = sum_entries
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
import numpy as np

class sum_entries(AffAtom):
    """ Summing the entries of an expression.

    Attributes
    ----------
    expr : CVXPY Expression
        The expression to sum the entries of.
    """

    def __init__(self, expr):
        super(sum_entries, self).__init__(expr)

    @AffAtom.numpy_numeric
    def numeric(self, values):
        """Sums the entries of value.
        """
        return np.sum(values[0])

    def shape_from_args(self):
        """Always scalar.
        """
        return u.Shape(1, 1)

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Sum the linear expression's entries.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.sum_entries(arg_objs[0]), [])

########NEW FILE########
__FILENAME__ = transpose
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.utilities as u
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu

class transpose(AffAtom):
    """ Matrix transpose. """
    # The string representation of the atom.
    def name(self):
        return "%s.T" % self.args[0]

    # Returns the transpose of the given value.
    @AffAtom.numpy_numeric
    def numeric(self, values):
        return values[0].T

    def shape_from_args(self):
        """Returns the shape of the transpose expression.
        """
        rows, cols = self.args[0].size
        return u.Shape(cols, rows)

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Create a new variable equal to the argument transposed.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return lu.transpose(arg_objs[0])

########NEW FILE########
__FILENAME__ = unary_operators
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.affine_atom import AffAtom
import cvxpy.lin_ops.lin_utils as lu
import operator as op

class UnaryOperator(AffAtom):
    """
    Base class for expressions involving unary operators.
    """
    def __init__(self, expr):
        super(UnaryOperator, self).__init__(expr)

    def name(self):
        return self.OP_NAME + self.args[0].name()

    # Applies the unary operator to the value.
    def numeric(self, values):
        return self.OP_FUNC(values[0])

    # Returns the sign, curvature, and shape.
    def init_dcp_attr(self):
        self._dcp_attr = self.OP_FUNC(self.args[0]._dcp_attr)

class NegExpression(UnaryOperator):
    OP_NAME = "-"
    OP_FUNC = op.neg

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Negate the affine objective.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return (lu.neg_expr(arg_objs[0]), [])

########NEW FILE########
__FILENAME__ = vstack
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.affine.affine_atom import AffAtom
from cvxpy.atoms.affine.index import index
import numpy as np

class vstack(AffAtom):
    """ Vertical concatenation """
    # Returns the vstack of the values.
    @AffAtom.numpy_numeric
    def numeric(self, values):
        return np.vstack(values)

    # The shape is the common width and the sum of the heights.
    def shape_from_args(self):
        cols = self.args[0].size[1]
        rows = sum(arg.size[0] for arg in self.args)
        return u.Shape(rows, cols)

    # All arguments must have the same width.
    def validate_arguments(self):
        arg_cols = [arg.size[1] for arg in self.args]
        if max(arg_cols) != min(arg_cols):
            raise TypeError( ("All arguments to vstack must have "
                              "the same number of columns.") )

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Stack the expressions vertically.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        X = lu.create_var(size)
        constraints = []
        # Create an equality constraint for each arg.
        offset = 0
        for arg in arg_objs:
            index.block_eq(X, arg, constraints,
                           offset, arg.size[0] + offset,
                           0, size[1])
            offset += arg.size[0]
        return (X, constraints)

########NEW FILE########
__FILENAME__ = atom
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from .. import settings as s
from .. import utilities as u
from .. import interface as intf
from ..expressions.constants import Constant, ConstantAtom
from ..expressions.variables import Variable
from ..expressions.expression import Expression
import abc

class Atom(Expression):
    """ Abstract base class for atoms. """
    __metaclass__ = abc.ABCMeta
    # args are the expressions passed into the Atom constructor.
    def __init__(self, *args):
        # Throws error if args is empty.
        if len(args) == 0:
            raise TypeError(
                "No arguments given to %s." % self.__class__.__name__
            )
        # Convert raw values to Constants.
        self.args = [Atom.cast_to_const(arg) for arg in args]
        self.validate_arguments()
        self.init_dcp_attr()
        self.subexpressions = self.args

    # Returns the string representation of the function call.
    def name(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join([arg.name() for arg in self.args]))

    # Determines the curvature, sign, and shape from the arguments.
    def init_dcp_attr(self):
        # Initialize _shape. Raises an error for invalid argument sizes.
        shape = self.shape_from_args()
        sign = self.sign_from_args()
        curvature = Atom.dcp_curvature(self.func_curvature(),
                                       self.args,
                                       self.monotonicity())
        self._dcp_attr = u.DCPAttr(sign, curvature, shape)

    # Returns argument curvatures as a list.
    def argument_curvatures(self):
        return [arg.curvature for arg in self.args]

    # Raises an error if the arguments are invalid.
    def validate_arguments(self):
        pass

    # The curvature of the atom if all arguments conformed to DCP.
    # Alternatively, the curvature of the atom's function.
    @abc.abstractmethod
    def func_curvature(self):
        return NotImplemented

    # Returns a list with the monotonicity in each argument.
    # monotonicity can depend on the sign of the argument.
    @abc.abstractmethod
    def monotonicity(self):
        return NotImplemented

    # Applies DCP composition rules to determine curvature in each argument.
    # The overall curvature is the sum of the argument curvatures.
    @staticmethod
    def dcp_curvature(curvature, args, monotonicities):
        if len(args) != len(monotonicities):
            raise Exception('The number of args be'
                            ' equal to the number of monotonicities.')
        arg_curvatures = []
        for arg, monotonicity in zip(args,monotonicities):
            arg_curv = u.monotonicity.dcp_curvature(monotonicity, curvature,
                                                    arg._dcp_attr.sign,
                                                    arg._dcp_attr.curvature)
            arg_curvatures.append(arg_curv)
        return reduce(lambda x,y: x+y, arg_curvatures)

    # Represent the atom as an affine objective and affine/basic SOC constraints.
    def canonicalize(self):
        # Constant atoms are treated as a leaf.
        if self.is_constant():
            return ConstantAtom(self).canonical_form
        else:
            arg_objs = []
            constraints = []
            for arg in self.args:
                obj, constr = arg.canonical_form
                arg_objs.append(obj)
                constraints += constr
            # Special info required by the graph implementation.
            data = self.get_data()
            graph_obj, graph_constr = self.graph_implementation(arg_objs,
                                                                self.size,
                                                                data)
            return (graph_obj, constraints + graph_constr)


    def get_data(self):
        """Returns special info required for graph implementation.
        """
        return None

    @abc.abstractmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        return NotImplemented

    def variables(self):
        """Returns all the variables present in the arguments.
        """
        var_list = []
        for arg in self.args:
            var_list += arg.variables()
        # Remove duplicates.
        return list(set(var_list))

    def parameters(self):
        """Returns all the parameters present in the arguments.
        """
        param_list = []
        for arg in self.args:
            param_list += arg.parameters()
        # Remove duplicates.
        return list(set(param_list))

    @property
    def value(self):
        # Catch the case when the expression is known to be
        # zero through DCP analysis.
        if self.is_zero():
            result = intf.DEFAULT_INTERFACE.zeros(*self.size)
        else:
            arg_values = []
            for arg in self.args:
                # A argument without a value makes all higher level
                # values None.
                if arg.value is None:
                    return None
                else:
                    arg_values.append(arg.value)
            result = self.numeric(arg_values)
        # Reduce to a scalar if possible.
        if intf.size(result) == (1, 1):
            return intf.scalar_value(result)
        else:
            return result

    # Wraps an atom's numeric function that requires numpy ndarrays as input.
    # Ensures both inputs and outputs are the correct matrix types.
    @staticmethod
    def numpy_numeric(numeric_func):
        def new_numeric(self, values):
            interface = intf.DEFAULT_INTERFACE
            values = [interface.const_to_matrix(v, convert_scalars=True)
                      for v in values]
            result = numeric_func(self, values)
            return intf.DEFAULT_INTERFACE.const_to_matrix(result)
        return new_numeric

########NEW FILE########
__FILENAME__ = abs
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.expressions import types
from cvxpy.expressions.variables import Variable
from elementwise import Elementwise
import numpy as np

class abs(Elementwise):
    """ Elementwise absolute value """
    def __init__(self, x):
        super(abs, self).__init__(x)

    # Returns the elementwise absolute value of x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return np.absolute(values[0])

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var(x.size)
        constraints = [lu.create_geq(lu.sum_expr([x, t])),
                       lu.create_leq(x, t),
        ]
        return (t, constraints)

########NEW FILE########
__FILENAME__ = elementwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
from cvxpy.atoms.atom import Atom

class Elementwise(Atom):
    """ Abstract base class for elementwise atoms. """
    __metaclass__ = abc.ABCMeta
    # The shape is the same as the argument's shape.
    def shape_from_args(self):
        return self.args[0].shape

    def validate_arguments(self):
        """
        Verify that all the shapes are the same
        or can be promoted.
        """
        shape = self.args[0].shape
        for arg in self.args[1:]:
            shape = shape + arg.shape
########NEW FILE########
__FILENAME__ = entr
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.affine.index import index
from cvxpy.constraints.exponential import ExpCone
import numpy as np
from scipy.special import xlogy

class entr(Elementwise):
    """Elementwise :math:`-x\log x`.
    """
    def __init__(self, x):
        super(entr, self).__init__(x)

    @Elementwise.numpy_numeric
    def numeric(self, values):
        x = values[0]
        results = -xlogy(x, x)
        # Return -inf outside the domain
        results[np.isnan(results)] = -np.inf
        return results

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        t = lu.create_var(size)
        x = arg_objs[0]
        ones = lu.create_const(np.mat(np.ones(size)), size)

        return (t, [ExpCone(t, x, ones)])

########NEW FILE########
__FILENAME__ = exp
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.affine.index import index
from cvxpy.constraints.exponential import ExpCone
import numpy as np

class exp(Elementwise):
    """Elementwise :math:`e^{x}`.
    """
    def __init__(self, x):
        super(exp, self).__init__(x)

    # Returns the matrix e^x[i, j].
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return np.exp(values[0])

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        t = lu.create_var(size)
        x = arg_objs[0]
        ones = lu.create_const(np.mat(np.ones(size)), size)

        return (t, [ExpCone(x, ones, t)])

########NEW FILE########
__FILENAME__ = huber
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.elementwise.abs import abs
from cvxpy.atoms.elementwise.square import square

def huber(x, M=1):
    """The Huber function

    Huber(x, M) = 2M|x|-M^2 for |x| >= |M|
                  |x|^2 for |x| <= |M|
    M defaults to 1.

    Parameters
    ----------
    x : Expression
        A CVXPY expression.
    M : int/float
    """
    # TODO require that M is positive?
    return square(M)*huber_pos(abs(x)/abs(M))

class huber_pos(Elementwise):
    """Elementwise Huber function for non-negative expressions and M=1.
    """
    def __init__(self, x):
        super(huber_pos, self).__init__(x)

    # Returns the huber function applied elementwise to x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        x = values[0]
        for row in range(x.shape[0]):
            for col in range(x.shape[1]):
                if x[row, col] >= 1:
                    x[row, col] = 2*x[row, col] - 1
                else:
                    x[row, col] = x[row, col]**2

        return values[0]

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        w = lu.create_var(size)
        v = lu.create_var(size)
        two = lu.create_const(2, (1, 1))
        # w**2 + 2*v
        obj, constraints = square.graph_implementation([w], size)
        obj = lu.sum_expr([obj, lu.mul_expr(two, v, size)])
        # x <= w + v
        constraints.append(lu.create_leq(x, lu.sum_expr([w, v])))
        # v >= 0
        constraints.append(lu.create_geq(v))
        return (obj, constraints)

########NEW FILE########
__FILENAME__ = inv_pos
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.elementwise.qol_elemwise import qol_elemwise
import numpy as np

class inv_pos(Elementwise):
    """ Elementwise 1/x, x >= 0 """
    def __init__(self, x):
        super(inv_pos, self).__init__(x)

    # Returns the elementwise inverse of x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return 1.0/values[0]

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.DECREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        ones = lu.create_const(np.mat(np.ones(size)), size)
        obj, constraints = qol_elemwise([ones, x], size)

        return (obj, constraints)

########NEW FILE########
__FILENAME__ = log
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.affine.index import index
from cvxpy.constraints.exponential import ExpCone
import numpy as np

class log(Elementwise):
    """Elementwise :math:`\log x`.
    """
    def __init__(self, x):
        super(log, self).__init__(x)

    # Returns the elementwise natural log of x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return np.log(values[0])

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return [u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        t = lu.create_var(size)
        x = arg_objs[0]
        ones = lu.create_const(np.mat(np.ones(size)), size)

        return (t, [ExpCone(t, ones, x)])

########NEW FILE########
__FILENAME__ = max_elemwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
import numpy as np

class max_elemwise(Elementwise):
    """ Elementwise maximum. """

    def __init__(self, arg1, arg2, *args):
        """Requires at least 2 arguments.
        """
        super(max_elemwise, self).__init__(arg1, arg2, *args)

    @Elementwise.numpy_numeric
    def numeric(self, values):
        """Returns the elementwise maximum.
        """
        return reduce(np.maximum, values)

    def sign_from_args(self):
        """Determins the sign of max_elemwise from the arguments' signs.

        Reduces the list of argument signs according to the following rules:
            POSITIVE, ANYTHING = POSITIVE
            ZERO, UNKNOWN = POSITIVE
            ZERO, ZERO = ZERO
            ZERO, NEGATIVE = ZERO
            UNKNOWN, NEGATIVE = UNKNOWN
            NEGATIVE, NEGATIVE = NEGATIVE

        Returns
        -------
        Sign
            The Sign of the expression.
        """
        arg_signs = [arg._dcp_attr.sign for arg in self.args]
        if u.Sign.POSITIVE in arg_signs:
            max_sign = u.Sign.POSITIVE
        elif u.Sign.ZERO in arg_signs:
            if u.Sign.UNKNOWN in arg_signs:
                max_sign = u.Sign.POSITIVE
            else:
                max_sign = u.Sign.ZERO
        elif u.Sign.UNKNOWN in arg_signs:
            max_sign = u.Sign.UNKNOWN
        else:
            max_sign = u.Sign.NEGATIVE

        return max_sign

    def func_curvature(self):
        """The function's default curvature is convex.
        """
        return u.Curvature.CONVEX

    def monotonicity(self):
        """The function is increasing in each argument.
        """
        return len(self.args)*[u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        t = lu.create_var(size)
        constraints = []
        for obj in arg_objs:
            # Promote obj.
            if obj.size != size:
                obj = lu.promote(obj, size)
            constraints.append(lu.create_leq(obj, t))
        return (t, constraints)

########NEW FILE########
__FILENAME__ = min_elemwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.elementwise.max_elemwise import max_elemwise
import numpy as np

class min_elemwise(max_elemwise):
    """ Elementwise minimum. """
    # Returns the elementwise minimum.
    @max_elemwise.numpy_numeric
    def numeric(self, values):
        return reduce(np.minimum, values)

    def sign_from_args(self):
        """
        Reduces the list of argument signs according to the following rules:
            NEGATIVE, ANYTHING = NEGATIVE
            ZERO, UNKNOWN = NEGATIVE
            ZERO, ZERO = ZERO
            ZERO, POSITIVE = ZERO
            UNKNOWN, POSITIVE = UNKNOWN
            POSITIVE, POSITIVE = POSITIVE
        """
        arg_signs = [arg._dcp_attr.sign for arg in self.args]
        if u.Sign.NEGATIVE in arg_signs:
            min_sign = u.Sign.NEGATIVE
        elif u.Sign.ZERO in arg_signs:
            if u.Sign.UNKNOWN in arg_signs:
                min_sign = u.Sign.NEGATIVE
            else:
                min_sign = u.Sign.ZERO
        elif u.Sign.UNKNOWN in arg_signs:
            min_sign = u.Sign.UNKNOWN
        else:
            min_sign = u.Sign.POSITIVE

        return min_sign

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        t = lu.create_var(size)
        constraints = []
        for obj in arg_objs:
            # Promote obj.
            if obj.size != size:
                obj = lu.promote(obj, size)
            constraints.append(lu.create_leq(t, obj))
        return (t, constraints)

########NEW FILE########
__FILENAME__ = neg
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.elementwise.min_elemwise import min_elemwise

def neg(x):
    """ Alias for -min_elemwise{x, 0}.

    """
    return -min_elemwise(x, 0)

########NEW FILE########
__FILENAME__ = pos
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.elementwise.max_elemwise import max_elemwise

def pos(x):
    """ Alias for max_elemwise{x,0}.

    """
    return max_elemwise(x, 0)

########NEW FILE########
__FILENAME__ = qol_elemwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.constraints import SOC_Elemwise

def qol_elemwise(arg_objs, size, data=None):
    """Reduces the atom to an affine expression and list of constraints.

    Parameters
    ----------
    arg_objs : list
        LinExpr for each argument.
    size : tuple
        The size of the resulting expression.
    data :
        Additional data required by the atom.

    Returns
    -------
    tuple
        (LinOp for objective, list of constraints)
    """
    x = arg_objs[0]
    y = arg_objs[1]
    t = lu.create_var(x.size)
    two = lu.create_const(2, (1, 1))
    constraints = [SOC_Elemwise(lu.sum_expr([y, t]),
                                [lu.sub_expr(y, t),
                                 lu.mul_expr(two, x, x.size)]),
                   lu.create_geq(y)]
    return (t, constraints)

########NEW FILE########
__FILENAME__ = sqrt
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.elementwise.square import square
import numpy as np

class sqrt(Elementwise):
    """ Elementwise square root """
    def __init__(self, x):
        super(sqrt, self).__init__(x)

    # Returns the elementwise square root of x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return np.sqrt(values[0])

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return [u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var(size)
        # x >= 0 implied by x >= t^2.
        # t >= 0 implied because t is only pushed to increase.
        obj, constraints = square.graph_implementation([t], size)
        return (t, constraints + [lu.create_leq(obj, x)])

########NEW FILE########
__FILENAME__ = square
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.elementwise import Elementwise
from cvxpy.atoms.elementwise.qol_elemwise import qol_elemwise
import numpy as np

class square(Elementwise):
    """ Elementwise square """
    def __init__(self, x):
        super(square, self).__init__(x)

    # Returns the elementwise square of x.
    @Elementwise.numpy_numeric
    def numeric(self, values):
        return np.square(values[0])

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        ones = lu.create_const(np.mat(np.ones(size)), size)
        obj, constraints = qol_elemwise([x, ones], size)

        return (obj, constraints)

########NEW FILE########
__FILENAME__ = geo_mean
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.constraints import SOC
import math

class geo_mean(Atom):
    """ Geometric mean of two scalars; :math:`(x_1, \cdots, x_n)^{1/n}`. """
    def __init__(self, x, y):
        super(geo_mean, self).__init__(x, y)

    # Returns the geometric mean of x and y.
    def numeric(self, values):
        return math.sqrt(values[0]*values[1])

    # The shape is the common width and the sum of the heights.
    def shape_from_args(self):
        return u.Shape(1, 1)

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return len(self.args)*[u.monotonicity.INCREASING]

    # Only scalar arguments are valid.
    def validate_arguments(self):
        if not self.args[0].is_scalar() or not self.args[1].is_scalar():
            raise TypeError("The arguments to geo_mean must resolve to scalars." )

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        # TODO use log for n != 2.
        v = lu.create_var((1, 1))
        x = arg_objs[0]
        y = arg_objs[1]
        two = lu.create_const(2, (1, 1))
        # SOC(x + y, [y - x, 2*v])
        constraints = [
            SOC(lu.sum_expr([x, y]),
                [lu.sub_expr(y, x),
                 lu.mul_expr(two, v, (1, 1))])
        ]
        # 0 <= x, 0 <= y
        constraints += [lu.create_geq(x), lu.create_geq(y)]
        return (v, constraints)

########NEW FILE########
__FILENAME__ = kl_div
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.constraints.exponential import ExpCone
import numpy as np
from scipy.special import xlogy

class kl_div(Atom):
    """:math:`x\log(x/y) - x + y`

    """
    def __init__(self, x, y):
        super(kl_div, self).__init__(x, y)

    @Atom.numpy_numeric
    def numeric(self, values):
        x = values[0]
        y = values[1]
        #TODO return inf outside the domain
        return xlogy(x, x/y) - x + y

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1, 1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return len(self.args)*[u.monotonicity.NONMONOTONIC]

    # Only scalar arguments are valid.
    def validate_arguments(self):
        if not self.args[0].is_scalar() or not self.args[1].is_scalar():
            raise TypeError("The arguments to kl_div must resolve to scalars." )

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        y = arg_objs[1]
        t = lu.create_var((1, 1))
        constraints = [ExpCone(t, x, y),
                       lu.create_geq(y)] # 0 <= y
        # -t - x + y
        obj = lu.sub_expr(y, lu.sum_expr([x, t]))
        return (obj, constraints)

########NEW FILE########
__FILENAME__ = lambda_max
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.affine.index import index
from cvxpy.atoms.affine.transpose import transpose
from cvxpy.constraints.semi_definite import SDP
import scipy.sparse as sp
from numpy import linalg as LA

class lambda_max(Atom):
    """ Maximum eigenvalue; :math:`\lambda_{\max}(A)`.

    """
    def __init__(self, A):
        super(lambda_max, self).__init__(A)

    # Returns the smallest eigenvalue of A.
    # Requires that A be symmetric.
    @Atom.numpy_numeric
    def numeric(self, values):
        if not (values[0].T == values[0]).all():
            raise Exception("lambda_max called on a non-symmetric matrix.")
        w, v = LA.eig(values[0])
        return max(w)

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Verify that the argument A is square.
    def validate_arguments(self):
        if not self.args[0].size[0] == self.args[0].size[1]:
            raise TypeError("The argument '%s' to lambda_max must resolve to a square matrix."
                % self.args[0].name())

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        A = arg_objs[0]
        n, _ = A.size
        # Requires that A is symmetric.
        # A == A.T
        obj, constraints = transpose.graph_implementation([A], (n, n))
        constraints.append(lu.create_eq(A, obj))
        # SDP constraint.
        t = lu.create_var((1, 1))
        I = lu.create_const(sp.eye(n, n), (n, n))
        # I*t - A
        expr = lu.sub_expr(lu.mul_expr(I, t, (n, n)), A)
        return (t, [SDP(expr)] + constraints)

########NEW FILE########
__FILENAME__ = lambda_min
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.affine.index import index
from cvxpy.atoms.affine.transpose import transpose
from cvxpy.constraints.semi_definite import SDP
import scipy.sparse as sp
from numpy import linalg as LA

class lambda_min(Atom):
    """ Miximum eigenvalue; :math:`\lambda_{\min}(A)`.

    """
    def __init__(self, A):
        super(lambda_min, self).__init__(A)

    # Returns the smallest eigenvalue of A.
    # Requires that A be symmetric.
    @Atom.numpy_numeric
    def numeric(self, values):
        if not (values[0].T == values[0]).all():
            raise Exception("lambda_min called on a non-symmetric matrix.")
        w, v = LA.eig(values[0])
        return min(w)

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Verify that the argument A is square.
    def validate_arguments(self):
        if not self.args[0].size[0] == self.args[0].size[1]:
            raise TypeError("The argument '%s' to lambda_min must resolve to a square matrix."
                % self.args[0].name())

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        A = arg_objs[0]
        n, _ = A.size
        # Requires that A is symmetric.
        obj, constraints = transpose.graph_implementation([A], (n, n))
        # A == A.T
        constraints.append(lu.create_eq(A, obj))
        # SDP constraint.
        t = lu.create_var((1, 1))
        I = lu.create_const(sp.eye(n, n), (n, n))
        # I*t - A
        expr = lu.sub_expr(A, lu.mul_expr(I, t, (n, n)))
        return (t, [SDP(expr)] + constraints)

########NEW FILE########
__FILENAME__ = log_det
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.elementwise.log import log
from cvxpy.atoms.affine.index import index
from cvxpy.atoms.affine.transpose import transpose
from cvxpy.constraints.semi_definite import SDP
import numpy as np
from numpy import linalg as LA

class log_det(Atom):
    """:math:`\log\det A`

    """
    def __init__(self, A):
        super(log_det, self).__init__(A)

    # Returns the nuclear norm (i.e. the sum of the singular values) of A.
    @Atom.numpy_numeric
    def numeric(self, values):
        return np.log(LA.det(values[0]))

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Any argument size is valid.
    def validate_arguments(self):
        n, m = self.args[0].size
        if n != m:
            raise TypeError("The argument to log_det must be a square matrix." )

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONCAVE

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Creates the equivalent problem::

           maximize    sum(log(D[i, i]))
           subject to: D diagonal
                       diag(D) = diag(Z)
                       Z is upper triangular.
                       [D Z; Z.T A] is positive semidefinite

        The problem computes the LDL factorization:

        .. math::

           A = (Z^TD^{-1})D(D^{-1}Z)

        This follows from the inequality:

        .. math::

           \det(A) >= \det(D) + \det([D, Z; Z^T, A])/\det(D)
                   >= \det(D)

        because (Z^TD^{-1})D(D^{-1}Z) is a feasible D, Z that achieves
        det(A) = det(D) and the objective maximizes det(D).

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        A = arg_objs[0] # n by n matrix.
        n, _ = A.size
        X = lu.create_var((2*n, 2*n))
        Z = lu.create_var((n, n))
        D = lu.create_var((n, n))
        # Require that X is symmetric (which implies
        # A is symmetric).
        # X == X.T
        obj, constraints = transpose.graph_implementation([X], (n, n))
        constraints.append(lu.create_eq(X, obj))
        # Require that X and A are PSD.
        constraints += [SDP(X), SDP(A)]
        # Fix Z as upper triangular, D as diagonal,
        # and diag(D) as diag(Z).
        for i in xrange(n):
            for j in xrange(n):
                if i == j:
                    # D[i, j] == Z[i, j]
                    Dij = index.get_index(D, constraints, i, j)
                    Zij = index.get_index(Z, constraints, i, j)
                    constraints.append(lu.create_eq(Dij, Zij))
                if i != j:
                    # D[i, j] == 0
                    Dij = index.get_index(D, constraints, i, j)
                    constraints.append(lu.create_eq(Dij))
                if i > j:
                    # Z[i, j] == 0
                    Zij = index.get_index(Z, constraints, i, j)
                    constraints.append(lu.create_eq(Zij))
        # Fix X using the fact that A must be affine by the DCP rules.
        # X[0:n, 0:n] == D
        index.block_eq(X, D, constraints, 0, n, 0, n)
        # X[0:n, n:2*n] == Z,
        index.block_eq(X, Z, constraints, 0, n, n, 2*n)
        # X[n:2*n, n:2*n] == A
        index.block_eq(X, A, constraints, n, 2*n, n, 2*n)
        # Add the objective sum(log(D[i, i])
        log_diag = []
        for i in xrange(n):
            Dii = index.get_index(D, constraints, i, i)
            obj, constr = log.graph_implementation([Dii], (1, 1))
            constraints += constr
            log_diag.append(obj)
        obj = lu.sum_expr(log_diag)
        return (obj, constraints)

########NEW FILE########
__FILENAME__ = log_sum_exp
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.elementwise.exp import exp
from cvxpy.atoms.affine.sum_entries import sum_entries
from cvxpy.constraints.exponential import ExpCone
import numpy as np

class log_sum_exp(Atom):
    """:math:`\log\sum_i e^{x_i}`

    """
    def __init__(self, x):
        super(log_sum_exp, self).__init__(x)

    # Evaluates e^x elementwise, sums, and takes the log.
    @Atom.numpy_numeric
    def numeric(self, values):
        exp_mat = np.exp(values[0])
        exp_sum = exp_mat.sum(axis = 1).sum(axis = 0)
        return np.log(exp_sum)

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1, 1)

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.UNKNOWN

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var((1, 1))
        # sum(exp(x - t))
        prom_t = lu.promote(t, x.size)
        expr = lu.sub_expr(x, prom_t)
        obj, constraints = exp.graph_implementation([expr], x.size)
        obj, constr = sum_entries.graph_implementation([obj], (1, 1))
        # obj <= 1
        one = lu.create_const(1, (1, 1))
        constraints += constr + [lu.create_leq(obj, one)]
        return (t, constraints)

########NEW FILE########
__FILENAME__ = max_entries
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.atom import Atom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu

class max_entries(Atom):
    """:math:`\max_{i,j}\{X_{i,j}\}`.
    """
    def __init__(self, x):
        super(max_entries, self).__init__(x)

    @Atom.numpy_numeric
    def numeric(self, values):
        """Returns the largest entry in x.
        """
        return values[0].max()

    def shape_from_args(self):
        """Resolves to a scalar.
        """
        return u.Shape(1, 1)

    def sign_from_args(self):
        """Has the same sign as the argument.
        """
        return self.args[0]._dcp_attr.sign

    def func_curvature(self):
        """Default curvature is convex.
        """
        return u.Curvature.CONVEX

    def monotonicity(self):
        """Increasing in its arguments.
        """
        return [u.monotonicity.INCREASING]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var((1, 1))
        promoted_t = lu.promote(t, x.size)
        constraints = [lu.create_leq(x, promoted_t)]
        return (t, constraints)

########NEW FILE########
__FILENAME__ = min_entries
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.max_entries import max_entries
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu

class min_entries(max_entries):
    """:math:`\min_{i,j}\{X_{i,j}\}`.
    """
    def __init__(self, x):
        super(min_entries, self).__init__(x)

    @max_entries.numpy_numeric
    def numeric(self, values):
        """Returns the smallest entry in x.
        """
        return values[0].min()

    def func_curvature(self):
        """Default curvature is concave.
        """
        return u.Curvature.CONCAVE

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var((1, 1))
        promoted_t = lu.promote(t, x.size)
        constraints = [lu.create_leq(promoted_t, x)]
        return (t, constraints)

########NEW FILE########
__FILENAME__ = norm
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from norm1 import norm1
from norm2 import norm2
from norm_inf import normInf
from norm_nuc import normNuc
from sigma_max import sigma_max
from ..expressions.expression import Expression

# Wrapper on the different norm atoms.
def norm(x, p=2):
    x = Expression.cast_to_const(x)
    if p == 1:
        return norm1(x)
    elif p == "inf":
        return normInf(x)
    elif p == "nuc":
        return normNuc(x)
    elif p == "fro":
        return norm2(x)
    elif p == 2:
        if x.is_matrix():
            return sigma_max(x)
        else:
            return norm2(x)
    else:
        raise Exception("Invalid value %s for p." % p)
########NEW FILE########
__FILENAME__ = norm1
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.atom import Atom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.elementwise.abs import abs
from cvxpy.atoms.affine.sum_entries import sum_entries
from numpy import linalg as LA

class norm1(Atom):
    """L1 norm; :math:`\sum_i|x_i|`.

    """
    def __init__(self, x):
        super(norm1, self).__init__(x)

    # Returns the L1 norm of x.
    @Atom.numpy_numeric
    def numeric(self, values):
        cols = values[0].shape[1]
        return sum([LA.norm(values[0][:, i], 1) for i in range(cols)])

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        obj, abs_constr = abs.graph_implementation([x], x.size)
        obj, sum_constr = sum_entries.graph_implementation([obj], (1, 1))
        return (obj, abs_constr + sum_constr)

########NEW FILE########
__FILENAME__ = norm2
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.atom import Atom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.constraints.second_order import SOC
from numpy import linalg as LA

class norm2(Atom):
    """L2 norm; :math:`(\sum_i x_i^2)^{1/2}`.

    """
    def __init__(self, x):
        super(norm2, self).__init__(x)

    # Returns the L2 norm of x for vector x
    # and the Frobenius norm for matrix x.
    @Atom.numpy_numeric
    def numeric(self, values):
        return LA.norm(values[0])

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var((1, 1))
        return (t, [SOC(t, [x])])

########NEW FILE########
__FILENAME__ = norm_inf
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.atom import Atom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
import numpy as np
from numpy import linalg as LA

class normInf(Atom):
    """Infinity norm; :math:`\max_i\{|x_i|, \dots, |x_n|\}`.

    """
    def __init__(self, x):
        super(normInf, self).__init__(x)

    # Returns the Infinity norm of x.
    @Atom.numpy_numeric
    def numeric(self, values):
        cols = values[0].shape[1]
        return max([LA.norm(values[0][:,i], np.inf) for i in range(cols)])

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.SIGNED]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        t = lu.create_var((1, 1))
        promoted_t = lu.promote(t, x.size)
        constraints = [lu.create_geq(lu.sum_expr([x, promoted_t])),
                       lu.create_leq(x, promoted_t)]
        return (t, constraints)

########NEW FILE########
__FILENAME__ = norm_nuc
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.affine.index import index
from cvxpy.atoms.affine.transpose import transpose
from cvxpy.constraints.semi_definite import SDP
from numpy import linalg as LA

class normNuc(Atom):
    """ Sum of the singular values. """
    def __init__(self, A):
        super(normNuc, self).__init__(A)

    # Returns the nuclear norm (i.e. the sum of the singular values) of A.
    @Atom.numpy_numeric
    def numeric(self, values):
        U,s,V = LA.svd(values[0])
        return sum(s)

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        A = arg_objs[0] # m by n matrix.
        n, m = A.size
        # Create the equivalent problem:
        #   minimize (trace(U) + trace(V))/2
        #   subject to:
        #            [U A; A.T V] is positive semidefinite
        X = lu.create_var((n+m, n+m))
        # Expand A.T.
        obj, constraints = transpose.graph_implementation([A], (m, n))
        # Fix X using the fact that A must be affine by the DCP rules.
        # X[0:n,n:n+m] == A
        index.block_eq(X, A, constraints,
                       0, n, n, n+m)
        # X[n:n+m,0:n] == obj
        index.block_eq(X, obj, constraints,
                       n, n+m, 0, n)
        diag = [index.get_index(X, constraints, i, i) for i in range(n+m)]
        half = lu.create_const(0.5, (1, 1))
        trace = lu.mul_expr(half, lu.sum_expr(diag), (1, 1))
        # Add SDP constraint.
        return (trace, [SDP(X)] + constraints)

########NEW FILE########
__FILENAME__ = quad_form
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from .. import interface as intf
from ..expressions.expression import Expression
from ..expressions.constants import Constant
from norm2 import norm2
from elementwise.square import square
from scipy import linalg as LA
import numpy as np

class CvxPyDomainError(Exception):
    pass


def _decomp_quad(P, cond=None, rcond=None, lower=True, check_finite=True):
    """
    Compute a matrix decomposition.

    Compute sgn, scale, M such that P = sgn * scale * dot(M, M.T).
    The strategy of determination of eigenvalue negligibility follows
    the pinvh contributions from the scikit-learn project to scipy.

    Parameters
    ----------
    P : matrix or ndarray
        A real symmetric positive or negative (semi)definite input matrix
    cond, rcond : float, optional
        Cutoff for small eigenvalues.
        Singular values smaller than rcond * largest_eigenvalue
        are considered negligible.
        If None or -1, suitable machine precision is used (default).
    lower : bool, optional
        Whether the array data is taken from the lower or upper triangle of P.
        The default is to take it from the lower triangle.
    check_finite : bool, optional
        Whether to check that the input matrix contains only finite numbers.
        The default is True; disabling may give a performance gain
        but may result in problems (crashes, non-termination) if the inputs
        contain infinities or NaNs.

    Returns
    -------
    sgn : -1 or 1
        1 if P is positive (semi)definite otherwise -1
    scale : float
        induced matrix 2-norm of P
    M : 2d ndarray
        A rectangular ndarray such that P = sgn * scale * dot(M, M.T)

    """
    w, V = LA.eigh(P, lower=lower, check_finite=check_finite)
    abs_w = np.absolute(w)
    sgn_w = np.sign(w)
    scale, sgn = max(zip(np.absolute(w), np.sign(w)))
    if rcond is not None:
        cond = rcond
    if cond in (None, -1):
        t = V.dtype.char.lower()
        factor = {'f': 1e3, 'd':1e6}
        cond = factor[t] * np.finfo(t).eps
    scaled_abs_w = abs_w / scale
    mask = scaled_abs_w > cond
    if np.any(w[mask] * sgn < 0):
        msg = 'P has both positive and negative eigenvalues.'
        raise CvxPyDomainError(msg)
    M = V[:, mask] * np.sqrt(scaled_abs_w[mask])
    return sgn, scale, M

def quad_form(x, P):
    """ Alias for :math:`x^T P x`.

    """
    x, P = map(Expression.cast_to_const, (x,P))
    # Check dimensions.
    n = P.size[0]
    if P.size[1] != n or x.size != (n,1):
        raise Exception("Invalid dimensions for arguments.")
    if x.is_constant():
        return x.T * P * x
    elif P.is_constant():
        np_intf = intf.get_matrix_interface(np.ndarray)
        P = np_intf.const_to_matrix(P.value)
        sgn, scale, M = _decomp_quad(P)
        return sgn * scale * square(norm2(Constant(M.T) * x))
    else:
        raise Exception("At least one argument to quad_form must be constant.")

########NEW FILE########
__FILENAME__ = quad_over_lin
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.atom import Atom
import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.constraints.second_order import SOC
import numpy as np

class quad_over_lin(Atom):
    """ :math:`(sum_{ij}X^2_{ij})/y`

    """
    def __init__(self, x, y):
        super(quad_over_lin, self).__init__(x, y)

    @Atom.numpy_numeric
    def numeric(self, values):
        """Returns the sum of the entries of x squared over y.
        """
        return np.square(values[0]).sum()/values[1]

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always positive.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    # Increasing for positive entry of x, decreasing for negative.
    def monotonicity(self):
        return [u.monotonicity.SIGNED, u.monotonicity.DECREASING]

    def validate_arguments(self):
        """Check dimensions of arguments.
        """
        if not self.args[1].is_scalar():
            raise ValueError("The second argument to quad_over_lin must be a scalar")

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        x = arg_objs[0]
        y = arg_objs[1] # Known to be a scalar.
        v = lu.create_var((1, 1))
        two = lu.create_const(2, (1, 1))
        constraints = [SOC(lu.sum_expr([y, v]),
                           [lu.sub_expr(y, v),
                            lu.mul_expr(two, x, x.size)]),
                       lu.create_geq(y)]
        return (v, constraints)

########NEW FILE########
__FILENAME__ = sigma_max
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.atoms.atom import Atom
from cvxpy.atoms.affine.index import index
from cvxpy.atoms.affine.transpose import transpose
from cvxpy.constraints.semi_definite import SDP
import scipy.sparse as sp
from numpy import linalg as LA

class sigma_max(Atom):
    """ Maximum singular value. """
    def __init__(self, A):
        super(sigma_max, self).__init__(A)

    # Returns the largest singular value of A.
    @Atom.numpy_numeric
    def numeric(self, values):
        return LA.norm(values[0], 2)

    # Resolves to a scalar.
    def shape_from_args(self):
        return u.Shape(1,1)

    # Always unknown.
    def sign_from_args(self):
        return u.Sign.POSITIVE

    # Default curvature.
    def func_curvature(self):
        return u.Curvature.CONVEX

    def monotonicity(self):
        return [u.monotonicity.NONMONOTONIC]

    @staticmethod
    def graph_implementation(arg_objs, size, data=None):
        """Reduces the atom to an affine expression and list of constraints.

        Parameters
        ----------
        arg_objs : list
            LinExpr for each argument.
        size : tuple
            The size of the resulting expression.
        data :
            Additional data required by the atom.

        Returns
        -------
        tuple
            (LinOp for objective, list of constraints)
        """
        A = arg_objs[0] # m by n matrix.
        n, m = A.size
        # Create a matrix with Schur complement I*t - (1/t)*A.T*A.
        X = lu.create_var((n+m, n+m))
        t = lu.create_var((1, 1))
        I_n = lu.create_const(sp.eye(n), (n, n))
        I_m = lu.create_const(sp.eye(m), (m, m))
        # Expand A.T.
        obj, constraints = transpose.graph_implementation([A], (m, n))
        # Fix X using the fact that A must be affine by the DCP rules.
        # X[0:n, 0:n] == I_n*t
        index.block_eq(X, lu.mul_expr(I_n, t, (n, n)), constraints,
                       0, n, 0, n)
        # X[0:n, n:n+m] == A
        index.block_eq(X, A, constraints,
                       0, n, n, n+m)
        # X[n:n+m, 0:n] == obj
        index.block_eq(X, obj, constraints,
                       n, n+m, 0, n)
        # X[n:n+m, n:n+m] == I_m*t
        index.block_eq(X, lu.mul_expr(I_m, t, (m, m)), constraints,
                       n, n+m, n, n+m)
        # Add SDP constraint.
        return (t, constraints + [SDP(X)])

########NEW FILE########
__FILENAME__ = sum_squares
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.norm import norm
from cvxpy.atoms.elementwise.square import square

def sum_squares(expr):
    """The sum of the squares of the entries.

    Parameters
    ----------
    expr: Expression
        The expression to take the sum of squares of.

    Returns
    -------
    Expression
        An expression representing the sum of squares.
    """
    return square(norm(expr, "fro"))

########NEW FILE########
__FILENAME__ = eq_constraint
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from leq_constraint import LeqConstraint
import cvxpy.lin_ops.lin_utils as lu

class EqConstraint(LeqConstraint):
    OP_NAME = "=="
    # Both sides must be affine.
    def is_dcp(self):
        return self._expr.is_affine()

    @property
    def value(self):
        """Does the constraint hold?

        Returns
        -------
        bool
        """
        if self._expr.value is None:
            return None
        else:
            return abs(self._expr.value) <= self.TOLERANCE

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Marks the top level constraint as the dual_holder,
        so the dual value will be saved to the EqConstraint.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        obj, constraints = self._expr.canonical_form
        dual_holder = lu.create_eq(obj, constr_id=self.id)
        return (None, constraints + [dual_holder])

########NEW FILE########
__FILENAME__ = exponential
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.settings as s
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.lin_ops.lin_op import VARIABLE
from cvxpy.constraints.nonlinear import NonlinearConstraint
from cvxpy.constraints.utilities import format_elemwise
import cvxopt
import math

class ExpCone(NonlinearConstraint):
    """A reformulated exponential cone constraint.

    Operates elementwise on x, y, z.

    Original cone:
    K = {(x,y,z) | y > 0, ye^(x/y) <= z}
         U {(x,y,z) | x <= 0, y = 0, z >= 0}
    Reformulated cone:
    K = {(x,y,z) | y, z > 0, y * log(y) + x <= y * log(z)}
         U {(x,y,z) | x <= 0, y = 0, z >= 0}

    Attributes
    ----------
        x: Variable x in the exponential cone.
        y: Variable y in the exponential cone.
        z: Variable z in the exponential cone.
    """
    CVXOPT_DENSE_INTF = intf.get_matrix_interface(cvxopt.matrix)
    CVXOPT_SPARSE_INTF = intf.get_matrix_interface(cvxopt.spmatrix)

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.size = self.x.size
        super(ExpCone, self).__init__(self._solver_hook,
                                      [self.x, self.y, self.z])

    def __str__(self):
        return "ExpCone(%s, %s, %s)" % (self.x, self.y, self.z)

    def format(self, solver):
        """Formats EXP constraints for the solver.

        Parameters
        ----------
            solver : str
                The solver targetted.
        """
        # Need x, y, z to be lone Variables.
        if solver == s.CVXOPT:
            constraints = []
            for i, var in enumerate(self.vars_):
                if not var.type is VARIABLE:
                    lone_var = lu.create_var(var.size)
                    constraints.append(lu.create_eq(lone_var, var))
                    self.vars_[i] = lone_var
            return constraints
        # Converts to an inequality constraint.
        elif solver == s.SCS:
            return format_elemwise([self.x, self.y, self.z])
        else:
            raise TypeError("Solver does not support exponential cone.")

    def _solver_hook(self, vars_=None, scaling=None):
        """A function used by CVXOPT's nonlinear solver.

        Based on f(x,y,z) = y * log(y) + x - y * log(z).

        Parameters
        ----------
            vars_: A cvxopt dense matrix with values for (x,y,z).
            scaling: A scaling for the Hessian.

        Returns
        -------
            _solver_hook() returns the constraint size and a feasible point.
            _solver_hook(x) returns the function value and gradient at x.
            _solver_hook(x, z) returns the function value, gradient,
            and (z scaled) Hessian at x.
        """
        entries = self.size[0]*self.size[1]
        if vars_ is None:
            x_init = entries*[0.0]
            y_init = entries*[0.5]
            z_init = entries*[1.0]
            return self.size[0], cvxopt.matrix(x_init + y_init + z_init)
        # Unpack vars_
        x = vars_[0:entries]
        y = vars_[entries:2*entries]
        z = vars_[2*entries:]
        # Out of domain.
        # TODO what if y == 0.0?
        if min(y) <= 0.0 or min(z) <= 0.0:
            return None
        # Evaluate the function.
        f = self.CVXOPT_DENSE_INTF.zeros(entries, 1)
        for i in range(entries):
            f[i] = x[i] - y[i]*math.log(z[i]) + y[i]*math.log(y[i])
        # Compute the gradient.
        Df = self.CVXOPT_DENSE_INTF.zeros(entries, 3*entries)
        for i in range(entries):
            Df[i, i] = 1.0
            Df[i, entries+i] = math.log(y[i]) - math.log(z[i]) + 1.0
            Df[i, 2*entries+i] = -y[i]/z[i]

        if scaling is None:
            return f, Df
        # Compute the Hessian.
        big_H = self.CVXOPT_SPARSE_INTF.zeros(3*entries, 3*entries)
        for i in range(entries):
            H = cvxopt.matrix([
                    [0.0, 0.0, 0.0],
                    [0.0, 1.0/y[i], -1.0/z[i]],
                    [0.0, -1.0/z[i], y[i]/(z[i]**2)],
                ])
            big_H[i:3*entries:entries, i:3*entries:entries] = scaling[i]*H
        return f, Df, big_H

########NEW FILE########
__FILENAME__ = leq_constraint
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.lin_ops.lin_utils as lu

class LeqConstraint(u.Canonical):
    OP_NAME = "<="
    TOLERANCE = 1e-4
    def __init__(self, lh_exp, rh_exp):
        self.id = lu.get_id()
        self.lh_exp = lh_exp
        self.rh_exp = rh_exp
        self._expr = self.lh_exp - self.rh_exp
        self._dual_value = None

    def name(self):
        return ' '.join([str(self.lh_exp),
                         self.OP_NAME,
                         str(self.rh_exp)])

    def __repr__(self):
        return self.name()

    @property
    def size(self):
        return self._expr.size

    # Left hand expression must be convex and right hand must be concave.
    def is_dcp(self):
        return self._expr.is_convex()

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Marks the top level constraint as the dual_holder,
        so the dual value will be saved to the LeqConstraint.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        obj, constraints = self._expr.canonical_form
        dual_holder = lu.create_leq(obj, constr_id=self.id)
        return (None, constraints + [dual_holder])

    def variables(self):
        """Returns the variables in the compared expressions.
        """
        return self._expr.variables()

    def parameters(self):
        """Returns the parameters in the compared expressions.
        """
        return self._expr.parameters()

    @property
    def value(self):
        """Does the constraint hold?

        Returns
        -------
        bool
        """
        if self._expr.value is None:
            return None
        else:
            return self._expr.value <= self.TOLERANCE

    # The value of the dual variable.
    @property
    def dual_value(self):
        return self._dual_value

    def save_value(self, value):
        """Save the value of the dual variable for the constraint's parent.

        Args:
            value: The value of the dual variable.
        """
        self._dual_value = value

########NEW FILE########
__FILENAME__ = nonlinear
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u

class NonlinearConstraint(object):
    """
    A nonlinear inequality constraint:
        f(x) <= 0
    where f is twice-differentiable.

    TODO: this may not be the best way to handle these constraints, but it is
    one of many (of course).
    """
    # f - a nonlinear function
    # vars_ - the variables involved in the function
    def __init__(self, f, vars_):
        self.f = f
        self.vars_ = vars_
        # The shape of vars_ in f(vars_)
        cols = self.vars_[0].size[1]
        rows = sum(var.size[0] for var in self.vars_)
        self.x_size = (rows*cols, 1)
        super(NonlinearConstraint, self).__init__()

    # Returns the variables involved in the function
    # in order, i.e. f(vars_) = f(vstack(variables))
    def variables(self):
        return self.vars_

    # Place x0 = f() in the vector of all variables.
    def place_x0(self, big_x, var_offsets, interface):
        m, x0 = self.f()
        offset = 0
        for var in self.variables():
            var_size = var.size[0]*var.size[1]
            var_x0 = x0[offset:offset+var_size]
            interface.block_add(big_x, var_x0, var_offsets[var.data],
                                0, var_size, 1)
            offset += var_size

    # Place Df in the gradient of all functions.
    def place_Df(self, big_Df, Df, var_offsets, vert_offset, interface):
        horiz_offset = 0
        for var in self.variables():
            var_size = var.size[0]*var.size[1]
            var_Df = Df[:, horiz_offset:horiz_offset+var_size]
            interface.block_add(big_Df, var_Df,
                                vert_offset, var_offsets[var.data],
                                self.size[0]*self.size[1], var_size)
            horiz_offset += var_size

    # Place H in the Hessian of all functions.
    def place_H(self, big_H, H, var_offsets, interface):
        offset = 0
        for var in self.variables():
            var_size = var.size[0]*var.size[1]
            var_H = H[offset:offset+var_size, offset:offset+var_size]
            interface.block_add(big_H, var_H,
                                var_offsets[var.data], var_offsets[var.data],
                                var_size, var_size)
            offset += var_size

    # Extract the function variables from the vector x of all variables.
    def extract_variables(self, x, var_offsets, interface):
        local_x = interface.zeros(*self.x_size)
        offset = 0
        for var in self.variables():
            var_size = var.size[0]*var.size[1]
            value = x[var_offsets[var.data]:var_offsets[var.data]+var_size]
            interface.block_add(local_x, value, offset, 0, var_size, 1)
            offset += var_size
        return local_x

########NEW FILE########
__FILENAME__ = second_order
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.lin_ops.lin_utils as lu

class SOC(object):
    """A second-order cone constraint, i.e., norm2(x) <= t.

    Attributes:
        t: The scalar part of the second-order constraint.
        x_elems: The elements of the vector part of the constraint.
    """
    def __init__(self, t, x_elems):
        self.t = t
        self.x_elems = x_elems
        super(SOC, self).__init__()

    def __str__(self):
        return "SOC(%s, %s)" % (self.t, self.x_elems)

    def format(self):
        """Formats SOC constraints as inequalities for the solver.
        """
        constraints = [lu.create_geq(self.t)]
        for elem in self.x_elems:
            constraints.append(lu.create_geq(elem))
        return constraints

    @property
    def size(self):
        """The dimensions of the second-order cone.
        """
        rows = 1
        for elem in self.x_elems:
            rows += elem.size[0]*elem.size[1]
        return (rows, 1)

########NEW FILE########
__FILENAME__ = semi_definite
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.lin_ops.lin_utils as lu

class SDP(object):
    """
    A semi-definite cone constraint:
        { symmetric A | x.T*A*x >= 0 for all x }
    (the set of all symmetric matrices such that the quadratic
    form x.T*A*x is positive for all x).

    Attributes:
        A: The matrix variable constrained to be semi-definite.
    """
    def __init__(self, A):
        self.A = A

    def __str__(self):
        return "SDP(%s)" % self.A

    def format(self):
        """Formats SDP constraints as inequalities for the solver.
        """
        # 0 <= A
        return [lu.create_geq(self.A)]

    @property
    def size(self):
        """The dimensions of the semi-definite cone.
        """
        return self.A.size

########NEW FILE########
__FILENAME__ = soc_elemwise
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.lin_ops.lin_utils as lu
from cvxpy.constraints.second_order import SOC
from cvxpy.constraints.utilities import format_elemwise

class SOC_Elemwise(SOC):
    """A second-order cone constraint for each element of the input.

    norm2([x1_ij; ... ; xn_ij]) <= t_ij for all i,j.

    Assumes t, xi, ..., xn all have the same dimensions.

    Attributes:
        t: The scalar part of the second-order constraint.
        x_elems: The elements of the vector part of the constraint.
    """
    def __str__(self):
        return "SOC_Elemwise(%s, %s)" % (self.t, self.x_elems)

    def format(self):
        """Formats SOC constraints as inequalities for the solver.
        """
        return format_elemwise([self.t] + self.x_elems)

    def num_cones(self):
        """The number of elementwise cones.
        """
        return self.t.size[0]*self.t.size[1]

    def cone_size(self):
        """The dimensions of a single cone.
        """
        return (1 + len(self.x_elems), 1)

    @property
    def size(self):
        """The dimensions of the second-order cones.

        Returns
        -------
        list
            A list of the dimensions of the elementwise cones.
        """
        cones = []
        cone_size = self.cone_size()
        for i in range(self.num_cones()):
            cones.append(cone_size)
        return cones

########NEW FILE########
__FILENAME__ = utilities
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Utility functions for constraints.

import cvxpy.lin_ops.lin_utils as lu
import scipy.sparse as sp

def format_elemwise(vars_):
    """Formats all the elementwise cones for the solver.

    Parameters
    ----------
    vars_ : list
        A list of the LinOp expressions in the elementwise cones.

    Returns
    -------
    list
        A list of LinLeqConstr that represent all the elementwise cones.
    """
    # Create matrices Ai such that 0 <= A0*x0 + ... + An*xn
    # gives the format for the elementwise cone constraints.
    spacing = len(vars_)
    prod_size = (spacing*vars_[0].size[0], vars_[0].size[1])
    # Matrix spaces out columns of the LinOp expressions.
    mat_size = (spacing*vars_[0].size[0], vars_[0].size[0])
    terms = []
    for i, var in enumerate(vars_):
        mat = get_spacing_matrix(mat_size, spacing, i)
        terms.append(lu.mul_expr(mat, var, prod_size))
    return [lu.create_geq(lu.sum_expr(terms))]

def get_spacing_matrix(size, spacing, offset):
    """Returns a sparse matrix LinOp that spaces out an expression.

    Parameters
    ----------
    size : tuple
        (rows in matrix, columns in matrix)
    spacing : int
        The number of rows between each non-zero.
    offset : int
        The number of zero rows at the beginning of the matrix.

    Returns
    -------
    LinOp
        A sparse matrix constant LinOp.
    """
    val_arr = []
    row_arr = []
    col_arr = []
    # Selects from each column.
    for var_row in range(size[1]):
        val_arr.append(1.0)
        row_arr.append(spacing*var_row + offset)
        col_arr.append(var_row)
    mat = sp.coo_matrix((val_arr, (row_arr, col_arr)), size).tocsc()
    return lu.create_const(mat, size, sparse=True)

########NEW FILE########
__FILENAME__ = constant
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
import cvxpy.interface as intf
import cvxpy.settings as s
from cvxpy.expressions.leaf import Leaf
import cvxpy.lin_ops.lin_utils as lu

class Constant(Leaf):
    """
    A constant, either matrix or scalar.
    """
    def __init__(self, value):
        # Keep sparse matrices sparse.
        if intf.is_sparse(value):
            self._value = intf.DEFAULT_SPARSE_INTERFACE.const_to_matrix(value)
            self._sparse = True
        else:
            self._value = intf.DEFAULT_INTERFACE.const_to_matrix(value)
            self._sparse = False
        # Set DCP attributes.
        self.init_dcp_attr()

    def name(self):
        return str(self.value)

    @property
    def value(self):
        return self._value

    # Return the DCP attributes of the constant.
    def init_dcp_attr(self):
        shape = u.Shape(*intf.size(self.value))
        # If scalar, check sign. Else unknown sign.
        if shape.size == (1, 1):
            sign = u.Sign.val_to_sign(self.value)
        else:
            sign = u.Sign.UNKNOWN
        self._dcp_attr = u.DCPAttr(sign, u.Curvature.CONSTANT, shape)

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        obj = lu.create_const(self.value, self.size, self._sparse)
        return (obj, [])

########NEW FILE########
__FILENAME__ = constant_atom
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from constant import Constant
import cvxpy.lin_ops.lin_utils as lu

class ConstantAtom(Constant):
    """An atom with constant arguments.
    """

    def __init__(self, atom):
        self.atom = atom
        self._dcp_attr = self.atom._dcp_attr

    @property
    def value(self):
        """The value of the atom evaluated on its arguments.
        """
        return self.atom.value

    def parameters(self):
        """Return all the parameters in the atom.
        """
        return self.atom.parameters()

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        if len(self.parameters()) > 0:
            obj = lu.create_param(self, self.size)
        else:
            obj = lu.create_const(self.value, self.size)
        return (obj, [])

########NEW FILE########
__FILENAME__ = parameter
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from ... import settings as s
from ... import utilities as u
from ... import interface as intf
from constant import Constant
import cvxpy.lin_ops.lin_utils as lu

class Parameter(Constant):
    """
    A parameter, either matrix or scalar.
    """
    PARAM_COUNT = 0
    def __init__(self, rows=1, cols=1, name=None, sign="unknown"):
        self.id = lu.get_id()
        self._rows = rows
        self._cols = cols
        self.sign_str = sign
        if name is None:
            self._name = "%s%d" % (s.PARAM_PREFIX, self.id)
        else:
            self._name = name
        self.init_dcp_attr()

    def name(self):
        return self._name

    def init_dcp_attr(self):
        shape = u.Shape(self._rows, self._cols)
        sign = u.Sign(self.sign_str)
        self._dcp_attr = u.DCPAttr(sign, u.Curvature.CONSTANT, shape)

    # Getter and setter for parameter value.
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        # Convert val to the proper matrix type.
        val = intf.DEFAULT_INTERFACE.const_to_matrix(val)
        size = intf.size(val)
        if size != self.size:
            raise Exception("Invalid dimensions (%s,%s) for Parameter value." % size)
        # All signs are valid if sign is unknown.
        # Otherwise value sign must match declared sign.
        sign = intf.sign(val)
        if self.is_positive() and not sign.is_positive() or \
           self.is_negative() and not sign.is_negative():
            raise Exception("Invalid sign for Parameter value.")
        self._value = val

    def parameters(self):
        """Returns itself as a parameter.
        """
        return [self]

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        obj = lu.create_param(self, self.size)
        return (obj, [])

########NEW FILE########
__FILENAME__ = expression
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from .. import interface as intf
from .. import utilities as u
from .. import settings as s
from ..utilities import performance_utils as pu
from ..constraints import EqConstraint, LeqConstraint
import types
import abc
import numpy as np

def _cast_other(binary_op):
    """Casts the second argument of a binary operator as an Expression.

    Args:
        binary_op: A binary operator in the Expression class.

    Returns:
        A wrapped binary operator that can handle non-Expression arguments.
    """
    def cast_op(self, other):
        """A wrapped binary operator that can handle non-Expression arguments.
        """
        other = self.cast_to_const(other)
        return binary_op(self, other)
    return cast_op

class Expression(u.Canonical):
    """
    A mathematical expression in a convex optimization problem.
    """

    __metaclass__ = abc.ABCMeta

    # Handles arithmetic operator overloading with Numpy.
    __array_priority__ = 100

    def __array__(self):
        """Prevents Numpy == from iterating over the Expression.
        """
        return np.array([s.NP_EQUAL_STR], dtype="object")

    @abc.abstractmethod
    def value(self):
        """Returns the numeric value of the expression.

        Returns:
            A numpy matrix or a scalar.
        """
        return NotImplemented

    def __repr__(self):
        """TODO priority
        """
        return self.name()

    @abc.abstractmethod
    def name(self):
        """Returns the string representation of the expression.
        """
        return NotImplemented

    # Curvature properties.

    @property
    def curvature(self):
        """ Returns the curvature of the expression.
        """
        return str(self._dcp_attr.curvature)

    def is_constant(self):
        """Is the expression constant?
        """
        return self._dcp_attr.curvature.is_constant()

    def is_affine(self):
        """Is the expression affine?
        """
        return self._dcp_attr.curvature.is_affine()

    def is_convex(self):
        """Is the expression convex?
        """
        return self._dcp_attr.curvature.is_convex()

    def is_concave(self):
        """Is the expression concave?
        """
        return self._dcp_attr.curvature.is_concave()

    def is_dcp(self):
        """Is the expression DCP compliant? (i.e., no unknown curvatures).
        """
        return self._dcp_attr.curvature.is_dcp()

    # Sign properties.

    @property
    def sign(self):
        """ Returns the sign of the expression.
        """
        return str(self._dcp_attr.sign)

    def is_zero(self):
        """Is the expression all zero?
        """
        return self._dcp_attr.sign.is_zero()

    def is_positive(self):
        """Is the expression positive?
        """
        return self._dcp_attr.sign.is_positive()

    def is_negative(self):
        """Is the expression negative?
        """
        return self._dcp_attr.sign.is_negative()

    # The shape of the expression, an object.
    @property
    def shape(self):
        """ Returns the shape of the expression.
        """
        return self._dcp_attr.shape

    @property
    def size(self):
        """ Returns the (row, col) dimensions of the expression.
        """
        return self.shape.size

    def is_scalar(self):
        """Is the expression a scalar?
        """
        return self.size == (1, 1)

    def is_vector(self):
        """Is the expression a column vector?
        """
        return self.size[1] == 1

    def is_matrix(self):
        """Is the expression a matrix?
        """
        return self.size[0] > 1 and self.size[1] > 1

    def __getitem__(self, key):
        """Return a slice/index into the expression.
        """
        # Indexing into a scalar returns the scalar.
        if self.is_scalar():
            return self
        else:
            return types.index()(self, key)

    @property
    def T(self):
        """The transpose of an expression.
        """
        # Transpose of a scalar is that scalar.
        if self.is_scalar():
            return self
        else:
            return types.transpose()(self)

    # Arithmetic operators.
    @staticmethod
    def cast_to_const(expr):
        """Converts a non-Expression to a Constant.
        """
        return expr if isinstance(expr, Expression) else types.constant()(expr)

    @_cast_other
    def __add__(self, other):
        """The sum of two expressions.
        """
        return types.add_expr()([self, other])

    @_cast_other
    def __radd__(self, other):
        """Called for Number + Expression.
        """
        return other + self

    @_cast_other
    def __sub__(self, other):
        """The difference of two expressions.
        """
        return self + -other

    @_cast_other
    def __rsub__(self, other):
        """Called for Number - Expression.
        """
        return other - self

    @_cast_other
    def __mul__(self, other):
        """The product of two expressions.
        """
        # Cannot multiply two non-constant expressions.
        if not self.is_constant() and \
           not other.is_constant():
            raise TypeError("Cannot multiply two non-constants.")
        # The constant term must always be on the left.
        elif not self.is_constant():
            # If other is a scalar, simply move it left.
            if other.is_scalar():
                return types.mul_expr()(other, self)
            else:
                return (other.T * self.T).T
        else:
            return types.mul_expr()(self, other)

    @_cast_other
    def __div__(self, other):
        """One expression divided by another.
        """
        # Can only divide by scalar constants.
        if other.is_constant() and other.is_scalar():
            return types.div_expr()(self, other)
        else:
            raise TypeError("Can only divide by a scalar constant.")

    @_cast_other
    def __rdiv__(self, other):
        """Called for Number / Expression.
        """
        return other / self

    @_cast_other
    def __rmul__(self, other):
        """Called for Number * Expression.
        """
        return other * self

    def __neg__(self):
        """The negation of the expression.
        """
        return types.neg_expr()(self)

    # Comparison operators.
    @_cast_other
    def __eq__(self, other):
        """Returns an equality constraint.
        """
        return EqConstraint(self, other)

    @_cast_other
    def __le__(self, other):
        """Returns an inequality constraint.
        """
        return LeqConstraint(self, other)

    @_cast_other
    def __ge__(self, other):
        """Returns an inequality constraint.
        """
        return other.__le__(self)

########NEW FILE########
__FILENAME__ = leaf
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import expression

class Leaf(expression.Expression):
    """
    A leaf node, i.e. a Variable, Constant, or Parameter.
    """

    __metaclass__ = abc.ABCMeta

    def variables(self):
        """Default is empty list of Variables.
        """
        return []

    def parameters(self):
        """Default is empty list of Parameters.
        """
        return []

########NEW FILE########
__FILENAME__ = types
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Utility functions to solve circular imports.
def constant():
    import constants
    return constants.Constant

def add_expr():
    from ..atoms.affine import add_expr
    return add_expr.AddExpression

def mul_expr():
    from ..atoms.affine import binary_operators
    return binary_operators.MulExpression

def div_expr():
    from ..atoms.affine import binary_operators
    return binary_operators.DivExpression

def neg_expr():
    from ..atoms.affine import unary_operators
    return unary_operators.NegExpression

def index():
    from ..atoms.affine import index
    return index.index

def transpose():
    from ..atoms.affine import transpose
    return transpose.transpose

########NEW FILE########
__FILENAME__ = semidefinite
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""
from . variable import Variable
from ... constraints.semi_definite import SDP

class semidefinite(Variable):
    """ A semidefinite variable. """
    def __init__(self, n, name=None):
        super(semidefinite, self).__init__(n,n,name)

    # A semidefinite variable is no different from a normal variable except
    # that it adds an SDP constraint on the variable.
    def canonicalize(self):
        obj, constr = super(semidefinite, self).canonicalize()
        return (obj, constr + [SDP(obj)])

########NEW FILE########
__FILENAME__ = variable
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from ... import settings as s
from ... import utilities as u
from ..leaf import Leaf
import cvxpy.lin_ops.lin_utils as lu

class Variable(Leaf):
    """ The base variable class """
    # name - unique identifier.
    # rows - variable height.
    # cols - variable width.
    def __init__(self, rows=1, cols=1, name=None):
        self.id = lu.get_id()
        if name is None:
            self._name = "%s%d" % (s.VAR_PREFIX, self.id)
        else:
            self._name = name
        self.primal_value = None
        self._dcp_attr = u.DCPAttr(u.Sign.UNKNOWN,
                                   u.Curvature.AFFINE,
                                   u.Shape(rows, cols))

    def name(self):
        return self._name

    # Save the value of the primal variable.
    def save_value(self, value):
        self.primal_value = value

    @property
    def value(self):
        return self.primal_value

    def variables(self):
        """Returns itself as a variable.
        """
        return [self]

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        obj = lu.create_var(self.size, self.id)
        return (obj, [])

########NEW FILE########
__FILENAME__ = base_matrix_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import matrix_utilities as intf
import abc
import numbers
import numpy as np

class BaseMatrixInterface(object):
    """
    An interface between constants' internal values
    and the target matrix used internally.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        return NotImplemented

    # Adds a case for scalars to const_to_matrix methods.
    @staticmethod
    def scalar_const(converter):
        def new_converter(self, value, convert_scalars=False):
            if not convert_scalars and intf.is_scalar(value):
                return intf.scalar_value(value)
            else:
                return converter(self, value)
        return new_converter

    # Return an identity matrix.
    @abc.abstractmethod
    def identity(self, size):
        return NotImplemented

    # Return the dimensions of the matrix.
    @abc.abstractmethod
    def size(self, matrix):
        return NotImplemented

    # Get the matrix interpreted as a scalar.
    @abc.abstractmethod
    def scalar_value(self, matrix):
        return NotImplemented

    # Return a matrix with all 0's.
    def zeros(self, rows, cols):
        return self.scalar_matrix(0, rows, cols)

    # Return a matrix with all 1's.
    def ones(self, rows, cols):
        return self.scalar_matrix(1, rows, cols)

    # A matrix with all entries equal to the given scalar value.
    @abc.abstractmethod
    def scalar_matrix(self, value, rows, cols):
        return NotImplemented

    # Return the value at the given index in the matrix.
    def index(self, matrix, key):
        value = matrix[key]
        # Reduce to a scalar if possible.
        if intf.size(value) == (1,1):
            return intf.scalar_value(value)
        else:
            return value

    # Coerce the matrix into the given shape.
    @abc.abstractmethod
    def reshape(self, matrix, size):
        return NotImplemented

    def block_add(self, matrix, block, vert_offset, horiz_offset, rows, cols,
                  vert_step=1, horiz_step=1):
        """Add the block to a slice of the matrix.

        Args:
            matrix: The matrix the block will be added to.
            block: The matrix/scalar to be added.
            vert_offset: The starting row for the matrix slice.
            horiz_offset: The starting column for the matrix slice.
            rows: The height of the block.
            cols: The width of the block.
            vert_step: The row step size for the matrix slice.
            horiz_step: The column step size for the matrix slice.
        """
        block = self._format_block(matrix, block, rows, cols)
        matrix[vert_offset:(rows+vert_offset):vert_step,
               horiz_offset:(horiz_offset+cols):horiz_step] += block

    def _format_block(self, matrix, block, rows, cols):
        """Formats the block for block_add.

        Args:
            matrix: The matrix the block will be added to.
            block: The matrix/scalar to be added.
            rows: The height of the block.
            cols: The width of the block.
        """
        # If the block is a scalar, promote it.
        if intf.is_scalar(block):
            block = self.scalar_matrix(intf.scalar_value(block), rows, cols)
        # If the block is a vector coerced into a matrix, promote it.
        elif intf.is_vector(block) and cols > 1:
            block = self.reshape(block, (rows, cols))
        # If the block is a matrix coerced into a vector, vectorize it.
        elif not intf.is_vector(block) and cols == 1:
            block = self.reshape(block, (rows, cols))
        # Ensure the block is the same type as the matrix.
        elif type(block) != type(matrix):
            block = self.const_to_matrix(block)
        return block

########NEW FILE########
__FILENAME__ = dense_matrix_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from ..base_matrix_interface import BaseMatrixInterface
import cvxopt
import scipy.sparse as sp
import numbers

class DenseMatrixInterface(BaseMatrixInterface):
    """
    An interface to convert constant values to the cvxopt dense matrix class.
    """
    TARGET_MATRIX = cvxopt.matrix

    @BaseMatrixInterface.scalar_const
    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        if sp.issparse(value):
            value = value.todense()
        return cvxopt.matrix(value, tc='d')

    # Return an identity matrix.
    def identity(self, size):
        matrix = self.zeros(size, size)
        for i in range(size):
            matrix[i,i] = 1
        return matrix

    # Return the dimensions of the matrix.
    def size(self, matrix):
        return matrix.size

    # Get the value of the passed matrix, interpreted as a scalar.
    def scalar_value(self, matrix):
        return matrix[0,0]

    # A matrix with all entries equal to the given scalar value.
    def scalar_matrix(self, value, rows, cols):
        return cvxopt.matrix(value, (rows,cols), tc='d')

    # Stuff the matrix into a different shape.
    # First convert the matrix to a cvxopt dense matrix.
    def reshape(self, matrix, size):
        matrix = self.const_to_matrix(matrix)
        return cvxopt.matrix(list(matrix), size, tc='d')

########NEW FILE########
__FILENAME__ = sparse_matrix_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from dense_matrix_interface import DenseMatrixInterface
import scipy.sparse as sp
import cvxopt
import numpy

class SparseMatrixInterface(DenseMatrixInterface):
    """
    An interface to convert constant values to the cvxopt sparse matrix class.
    """
    TARGET_MATRIX = cvxopt.spmatrix

    @DenseMatrixInterface.scalar_const
    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        if isinstance(value, numpy.ndarray):
            return cvxopt.sparse(cvxopt.matrix(value), tc='d')
        # Convert scipy sparse matrices to coo form first.
        if sp.issparse(value):
            value = value.tocoo()
            V = value.data
            I = value.row
            J = value.col
            return cvxopt.spmatrix(V, I, J, value.shape)
        return cvxopt.sparse(value, tc='d')

    # Return an identity matrix.
    def identity(self, size):
        return cvxopt.spmatrix(1, range(size), range(size))

    # A matrix with all entries equal to the given scalar value.
    def scalar_matrix(self, value, rows, cols):
        if value == 0:
            return cvxopt.spmatrix(0, [], [], size=(rows,cols))
        else:
            dense = cvxopt.matrix(value, (rows,cols), tc='d')
            return cvxopt.sparse(dense)

    def reshape(self, matrix, size):
        old_size = matrix.size
        new_mat = self.zeros(*size)
        for v,i,j in zip(matrix.V, matrix.I, matrix.J):
            pos = i + old_size[0]*j
            new_row = pos % size[0]
            new_col = pos / size[0]
            new_mat[new_row, new_col] = v
        return new_mat

########NEW FILE########
__FILENAME__ = matrix_utilities
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxopt_interface as co_intf
import numpy_interface as np_intf
import cvxopt
import scipy.sparse as sp
import numbers
import numpy as np
from ..utilities.sign import Sign

# A mapping of class to interface.
INTERFACES = {cvxopt.matrix: co_intf.DenseMatrixInterface(),
              cvxopt.spmatrix: co_intf.SparseMatrixInterface(),
              np.ndarray: np_intf.NDArrayInterface(),
              np.matrix: np_intf.MatrixInterface(),
              sp.csc_matrix: np_intf.SparseMatrixInterface(),
}
# Default Numpy interface.
DEFAULT_NP_INTERFACE = INTERFACES[np.ndarray]
# Default dense and sparse matrix interfaces.
DEFAULT_INTERFACE = INTERFACES[np.matrix]
DEFAULT_SPARSE_INTERFACE = INTERFACES[sp.csc_matrix]

# Returns the interface for interacting with the target matrix class.
def get_matrix_interface(target_class):
    return INTERFACES[target_class]

def is_sparse(constant):
    """Is the constant a sparse matrix?
    """
    return sp.issparse(constant) or isinstance(constant, cvxopt.spmatrix)

# Get the dimensions of the constant.
def size(constant):
    if isinstance(constant, numbers.Number):
        return (1,1)
    elif isinstance(constant, list):
        if len(constant) == 0:
            return (0,0)
        elif isinstance(constant[0], numbers.Number): # Vector
            return (len(constant),1)
        else: # Matrix
            return (len(constant[0]),len(constant))
    elif constant.__class__ in INTERFACES:
        return INTERFACES[constant.__class__].size(constant)
    # Direct all sparse matrices to CSC interface.
    elif is_sparse(constant):
        return INTERFACES[sp.csc_matrix].size(constant)
    else:
        raise Exception("%s is not a valid type for a Constant value." % type(constant))

# Is the constant a column vector?
def is_vector(constant):
    return size(constant)[1] == 1

# Is the constant a scalar?
def is_scalar(constant):
    return size(constant) == (1, 1)

def from_2D_to_1D(constant):
    """Convert 2D Numpy matrices or arrays to 1D.
    """
    return np.asarray(constant)[:, 0]

def from_1D_to_2D(constant):
    """Convert 1D Numpy arrays to matrices.
    """
    if constant.ndim == 1:
        return np.mat(constant).T
    else:
        return constant

# Get the value of the passed constant, interpreted as a scalar.
def scalar_value(constant):
    assert is_scalar(constant)
    if isinstance(constant, numbers.Number):
        return constant
    elif isinstance(constant, list):
        return constant[0]
    elif constant.__class__ in INTERFACES:
        return INTERFACES[constant.__class__].scalar_value(constant)
    # Direct all sparse matrices to CSC interface.
    elif is_sparse(constant):
        return INTERFACES[sp.csc_matrix].scalar_value(constant.tocsc())
    else:
        raise Exception("%s is not a valid type for a Constant value." % type(constant))

# Return the collective sign of the matrix entries.
def sign(constant):
    if isinstance(constant, numbers.Number):
        return Sign.val_to_sign(constant)
    elif isinstance(constant, cvxopt.spmatrix):
        max_val = max(constant.V)
        min_val = min(constant.V)
    elif sp.issparse(constant):
        max_val = constant.max()
        min_val = constant.min()
    else: # Convert to Numpy array.
        mat = INTERFACES[np.ndarray].const_to_matrix(constant)
        max_val = mat.max()
        min_val = mat.min()
    max_sign = Sign.val_to_sign(max_val)
    min_sign = Sign.val_to_sign(min_val)
    return max_sign + min_sign

# Get the value at the given index.
def index(constant, key):
    if is_scalar(constant):
        return constant
    elif constant.__class__ in INTERFACES:
        return INTERFACES[constant.__class__].index(constant, key)
    # Use CSC interface for all sparse matrices.
    elif is_sparse(constant):
        interface = INTERFACES[sp.csc_matrix]
        constant = interface.const_to_matrix(constant)
        return interface.index(constant, key)

########NEW FILE########
__FILENAME__ = matrix_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from ndarray_interface import NDArrayInterface
import scipy.sparse as sp
import cvxopt
import numpy as np

class MatrixInterface(NDArrayInterface):
    """
    An interface to convert constant values to the numpy matrix class.
    """
    TARGET_MATRIX = np.matrix

    @NDArrayInterface.scalar_const
    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        # Convert cvxopt sparse to dense.
        if isinstance(value, cvxopt.spmatrix):
            value = cvxopt.matrix(value)
        # Lists and 1D arrays become column vectors.
        if isinstance(value, list) or \
           isinstance(value, np.ndarray) and value.ndim == 1:
            mat = np.asmatrix(value, dtype='float64')
            return mat.T
        # First convert sparse to dense.
        if sp.issparse(value):
            value = value.todense()
        return np.asmatrix(value, dtype='float64')

    # Return an identity matrix.
    def identity(self, size):
        return np.asmatrix(np.eye(size))

    # A matrix with all entries equal to the given scalar value.
    def scalar_matrix(self, value, rows, cols):
        mat = np.zeros((rows,cols), dtype='float64') + value
        return np.asmatrix(mat)

    def reshape(self, matrix, size):
        return np.reshape(matrix, size, order='F')

########NEW FILE########
__FILENAME__ = ndarray_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from .. import base_matrix_interface as base
import numpy
import cvxopt
import numbers

class NDArrayInterface(base.BaseMatrixInterface):
    """
    An interface to convert constant values to the numpy ndarray class.
    """
    TARGET_MATRIX = numpy.ndarray

    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        # Convert cvxopt sparse to dense.
        if isinstance(value, cvxopt.spmatrix):
            value = cvxopt.matrix(value)
        mat = numpy.array(value, dtype='float64')
        if isinstance(value, list):
            mat = numpy.atleast_2d(mat)
            return mat.T
        return numpy.atleast_2d(mat)

    # Return an identity matrix.
    def identity(self, size):
        return numpy.eye(size)

    # Return the dimensions of the matrix.
    def size(self, matrix):
        # Slicing drops the second dimension.
        if len(matrix.shape) == 1:
            dim = matrix.shape[0]
            return (dim, matrix.size/dim)
        else:
            return matrix.shape

    # Get the value of the passed matrix, interpreted as a scalar.
    def scalar_value(self, matrix):
        return numpy.asscalar(matrix)

    # A matrix with all entries equal to the given scalar value.
    def scalar_matrix(self, value, rows, cols):
        return numpy.zeros((rows,cols), dtype='float64') + value

    def reshape(self, matrix, size):
        return numpy.reshape(matrix, size, order='F')

########NEW FILE########
__FILENAME__ = sparse_matrix_interface
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from ndarray_interface import NDArrayInterface
import scipy.sparse as sp
import numpy as np
import numbers
import cvxopt

class SparseMatrixInterface(NDArrayInterface):
    """
    An interface to convert constant values to the scipy sparse CSC class.
    """
    TARGET_MATRIX = sp.csc_matrix

    @NDArrayInterface.scalar_const
    def const_to_matrix(self, value, convert_scalars=False):
        """Convert an arbitrary value into a matrix of type self.target_matrix.

        Args:
            value: The constant to be converted.
            convert_scalars: Should scalars be converted?

        Returns:
            A matrix of type self.target_matrix or a scalar.
        """
        # Convert cvxopt sparse to coo matrix.
        if isinstance(value, cvxopt.spmatrix):
            Vp, Vi, Vx = value.CCS
            Vp, Vi = (np.fromiter(iter(x),
                                  dtype=np.int32,
                                  count=len(x))
                      for x in (Vp, Vi))
            Vx = np.fromiter(iter(Vx), dtype=np.double)
            m, n = value.size
            return sp.csc_matrix((Vx, Vi, Vp), shape=(m, n))
        if isinstance(value, list):
            return sp.csc_matrix(value).T
        return sp.csc_matrix(value)

    def identity(self, size):
        """Return an identity matrix.
        """
        return sp.eye(size, size, format="csc")

    def size(self, matrix):
        """Return the dimensions of the matrix.
        """
        return matrix.shape

    def scalar_value(self, matrix):
        """Get the value of the passed matrix, interpreted as a scalar.
        """
        return matrix[0, 0]

    def zeros(self, rows, cols):
        """Return a matrix with all 0's.
        """
        return sp.csc_matrix((rows, cols), dtype='float64')

    def reshape(self, matrix, size):
        """Change the shape of the matrix.
        """
        matrix = matrix.todense()
        matrix = super(SparseMatrixInterface, self).reshape(matrix, size)
        return self.const_to_matrix(matrix)

    def block_add(self, matrix, block, vert_offset, horiz_offset, rows, cols,
                  vert_step=1, horiz_step=1):
        """Add the block to a slice of the matrix.

        Args:
            matrix: The matrix the block will be added to.
            block: The matrix/scalar to be added.
            vert_offset: The starting row for the matrix slice.
            horiz_offset: The starting column for the matrix slice.
            rows: The height of the block.
            cols: The width of the block.
            vert_step: The row step size for the matrix slice.
            horiz_step: The column step size for the matrix slice.
        """
        block = self._format_block(matrix, block, rows, cols)
        slice_ = [slice(vert_offset, rows+vert_offset, vert_step),
                  slice(horiz_offset, horiz_offset+cols, horiz_step)]
        # Convert to lil before changing sparsity structure.
        matrix[slice_[0], slice_[1]] = matrix[slice_[0], slice_[1]] + block

########NEW FILE########
__FILENAME__ = numpy_wrapper
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
from ..expressions import expression as exp
from .. import settings as s

# http://stackoverflow.com/questions/14619449/how-can-i-override-comparisons-between-numpys-ndarray-and-my-type

def override(name):
    """Wraps a Numpy comparison ufunc so cvxpy can overload the operator.

    Args:
        name: The name of a numpy comparison ufunc.

    Returns:
        A function.
    """
    # Numpy tries to convert the Expression to an array for ==.
    if name == "equal":
        def ufunc(x, y):
            if isinstance(y, np.ndarray) and y.ndim > 0 \
               and y[0] is s.NP_EQUAL_STR:
                    raise Exception("Prevent Numpy equal ufunc.")
            return getattr(np, name)(x, y)
        return ufunc
    else:
        def ufunc(x, y):
            if isinstance(y, exp.Expression):
                return NotImplemented
            return getattr(np, name)(x, y)
        return ufunc

# Implements operator overloading with comparisons.
np.set_numeric_ops(
    ** {
        ufunc : override(ufunc) for ufunc in (
            "less_equal", "equal", "greater_equal"
        )
    }
)

########NEW FILE########
__FILENAME__ = lin_constraints
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from collections import namedtuple

# Constraints with linear expressions.
# constr_id is used to recover dual variables.
# expr == 0
LinEqConstr = namedtuple("LinEqConstr", ["expr",
                                         "constr_id",
                                         "size"])
# expr <= 0
LinLeqConstr = namedtuple("LinLeqConstr", ["expr",
                                           "constr_id",
                                           "size"])

########NEW FILE########
__FILENAME__ = lin_op
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from collections import namedtuple

# A linear operator applied to a variable
# or a constant or function of parameters.
LinOp = namedtuple("LinOp", ["type",
                             "size",
                             "args",
                             "data"])

# The types of linear operators.

# A variable.
# Data: var id.
VARIABLE = "variable"
# Multiplying an expression by a constant.
# Data: LinOp evaluating to the left hand multiple.
MUL = "mul"
# Multiplying an expression elementwise by a constant.
# Data: LinOp evaluating to the left hand multiple.
MUL_ELEM = "mul_elem"
# Dividing an expression by a scalar constant.
# Data: LinOp evaluating to the divisor.
DIV = "div"
# Summing expressions.
SUM = "sum"
# Negating an expression.
NEG = "neg"
# An index/slice into an expression.
# Data: (row slice, col slice).
INDEX = "index"
# The transpose of an expression.
# Data: None.
TRANSPOSE = "transpose"
# The sum of the entries of an expression.
# Data: None
SUM_ENTRIES = "sum_entries"
# An expression cast into a different shape.
# Data: None
RESHAPE = "reshape"
# The 1D discrete convolution of two vectors.
# Data: LinOp evaluating to the left hand term.
CONV = "conv"
# A scalar constant.
# Data: Python float.
SCALAR_CONST = "scalar_const"
# A dense matrix/vector constant.
# Data: NumPy matrix.
DENSE_CONST = "dense_const"
# A sparse matrix constant.
# Data: SciPy sparse matrix.
SPARSE_CONST = "sparse_const"
# Some function of parameters.
# Data: CVXPY expression.
PARAM = "param"
# An expression with no variables.
# Data: None
NO_OP = "no_op"
# ID in coefficients for constants.
CONSTANT_ID = "constant_id"

########NEW FILE########
__FILENAME__ = lin_to_matrix
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.lin_ops.lin_op as lo
import cvxpy.interface as intf
import numpy as np
import scipy.sparse as sp
import scipy.linalg as sp_la

# Utility functions for converting LinOps into matrices.

def flatten(matrix):
    """Converts the matrix into a column vector.

    Parameters
    ----------
    matrix :
        The matrix to flatten.
    """
    np_mat = intf.DEFAULT_INTERFACE
    matrix = np_mat.const_to_matrix(matrix, convert_scalars=True)
    size = intf.size(matrix)
    return np_mat.reshape(matrix, (size[0]*size[1], 1))

def get_coefficients(lin_op):
    """Converts a linear op into coefficients.

    Parameters
    ----------
    lin_op : LinOp
        The linear op to convert.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    # VARIABLE converts to a giant identity matrix.
    if lin_op.type is lo.VARIABLE:
        coeffs = var_coeffs(lin_op)
    # Constants convert directly to their value.
    elif lin_op.type is lo.PARAM:
        coeffs = [(lo.CONSTANT_ID, lin_op.size, lin_op.data.value)]
    elif lin_op.type in [lo.SCALAR_CONST, lo.DENSE_CONST, lo.SPARSE_CONST]:
        coeffs = [(lo.CONSTANT_ID, lin_op.size, lin_op.data)]
    # For non-leaves, recurse on args.
    elif lin_op.type in TYPE_TO_FUNC:
        coeffs = TYPE_TO_FUNC[lin_op.type](lin_op)
    else:
        raise Exception("Unknown linear operator.")
    return coeffs

def var_coeffs(lin_op):
    """Returns the coefficients for a VARIABLE.

    Parameters
    ----------
    lin_op : LinOp
        The variable linear op.

    Returns
    -------
    list
       A list of (id, size, coefficient) tuples.
    """
    id_ = lin_op.data
    size = lin_op.size
    coeff = sp.eye(lin_op.size[0]*lin_op.size[1]).tocsc()
    return [(id_, size, coeff)]

def sum_coeffs(lin_op):
    """Returns the coefficients for SUM linear op.

    Parameters
    ----------
    lin_op : LinOp
        The sum linear op.

    Returns
    -------
    list
       A list of (id, size, coefficient) tuples.
    """
    coeffs = []
    for arg in lin_op.args:
        coeffs += get_coefficients(arg)
    return coeffs

def sum_entries_coeffs(lin_op):
    """Returns the coefficients for SUM_ENTRIES linear op.

    Parameters
    ----------
    lin_op : LinOp
        The sum entries linear op.

    Returns
    -------
    list
       A list of (id, size, coefficient) tuples.
    """
    coeffs = get_coefficients(lin_op.args[0])
    new_coeffs = []
    for id_, size, block in coeffs:
        # Sum all elements if constant.
        if id_ is lo.CONSTANT_ID:
            size = (1, 1)
            block = np.sum(block)
        # Sum columns if variable.
        else:
            block = block.sum(axis=0)
        new_coeffs.append((id_, size, block))
    return new_coeffs

def neg_coeffs(lin_op):
    """Returns the coefficients for NEG linear op.

    Parameters
    ----------
    lin_op : LinOp
        The neg linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    coeffs = get_coefficients(lin_op.args[0])
    new_coeffs = []
    for id_, size, block in coeffs:
        new_coeffs.append((id_, size, -block))
    return new_coeffs

def merge_constants(coeffs):
    """Sums all the constant coefficients.

    Parameters
    ----------
    coeffs : list
        A list of (id, size, coefficient) tuples.

    Returns
    -------
    The constant term.
    """
    constant = None
    for id_, size, block in coeffs:
        # Sum constants.
        if id_ is lo.CONSTANT_ID:
            if constant is None:
                constant = block
            else:
                constant += block
    return constant

def div_coeffs(lin_op):
    """Returns the coefficients for DIV linea op.

    Assumes dividing by scalar constants.

    Parameters
    ----------
    lin_op : LinOp
        The div linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    rh_coeffs = get_coefficients(lin_op.data)
    divisor = merge_constants(rh_coeffs)

    lh_coeffs = get_coefficients(lin_op.args[0])
    new_coeffs = []
    # Divide all right-hand constants by left-hand constant.
    for (id_, lh_size, coeff) in lh_coeffs:
        new_coeffs.append((id_, lh_size, coeff/divisor))
    return new_coeffs

def mul_elemwise_coeffs(lin_op):
    """Returns the coefficients for MUL_ELEM linear op.

    Parameters
    ----------
    lin_op : LinOp
        The mul_elem linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    lh_coeffs = get_coefficients(lin_op.data)
    constant = merge_constants(lh_coeffs)
    # Convert the constant to a giant diagonal matrix.
    vectorized = intf.from_2D_to_1D(flatten(constant))
    constant = sp.diags(vectorized, 0)
    rh_coeffs = get_coefficients(lin_op.args[0])

    new_coeffs = []
    # Multiply left-hand constant by right-hand terms.
    for (id_, rh_size, coeff) in rh_coeffs:
        new_coeffs.append((id_, rh_size, constant*coeff))

    return new_coeffs

def mul_coeffs(lin_op):
    """Returns the coefficients for MUL linear op.

    Parameters
    ----------
    lin_op : LinOp
        The mul linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    lh_coeffs = get_coefficients(lin_op.data)
    constant = merge_constants(lh_coeffs)
    rh_coeffs = get_coefficients(lin_op.args[0])

    return mul_by_const(constant, rh_coeffs, lin_op.size)

def mul_by_const(constant, rh_coeffs, size):
    """Multiplies a constant by a list of coefficients.

    Parameters
    ----------
    constant : numeric type
        The constant to multiply by.
    rh_coeffs : list
        The coefficients of the right hand side.
    size : tuple
        (product rows, product columns)

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    new_coeffs = []
    rep_mat = sp.block_diag(size[1]*[constant]).tocsc()
    # Multiply all left-hand constants by right-hand terms.
    for (id_, rh_size, coeff) in rh_coeffs:
        # For scalar left hand constants,
        # if right hand term is constant,
        # or single column, just multiply.
        if intf.is_scalar(constant) or \
           id_ is lo.CONSTANT_ID or size[1] == 1:
            product = constant*coeff
        # For promoted variables with matrix coefficients,
        # flatten the matrix.
        elif size != (1, 1) and intf.is_scalar(coeff):
            flattened_const = flatten(constant)
            product = flattened_const*coeff
        # Otherwise replicate the matrix.
        else:
            product = rep_mat*coeff
        new_coeffs.append((id_, rh_size, product))
    rh_coeffs = new_coeffs

    return new_coeffs

def index_var(lin_op):
    """Returns the coefficients from indexing a raw variable.

    Parameters
    ----------
    lin_op : LinOp
        The index linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    key = lin_op.data
    var_rows, var_cols = lin_op.args[0].size
    row_selection = range(var_rows)[key[0]]
    col_selection = range(var_cols)[key[1]]
    # Construct a coo matrix.
    val_arr = []
    row_arr = []
    col_arr = []
    counter = 0
    for col in col_selection:
        for row in row_selection:
            val_arr.append(1.0)
            row_arr.append(counter)
            col_arr.append(col*var_rows + row)
            counter += 1
    block_rows = lin_op.size[0]*lin_op.size[1]
    block_cols = var_rows*var_cols
    block = sp.coo_matrix((val_arr, (row_arr, col_arr)),
                          (block_rows, block_cols)).tocsc()
    return [(lin_op.args[0].data, lin_op.args[0].size, block)]

def index_coeffs(lin_op):
    """Returns the coefficients for INDEX linear op.

    Parameters
    ----------
    lin_op : LinOp
        The index linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    # Special case if variable.
    if lin_op.args[0].type is lo.VARIABLE:
        return index_var(lin_op)
    key = lin_op.data
    coeffs = get_coefficients(lin_op.args[0])
    new_coeffs = []
    for id_, size, block in coeffs:
        # Index/slice constants normally.
        if id_ is lo.CONSTANT_ID:
            size = lin_op.size
            block = intf.index(block, key)
        # Split into column blocks, slice column blocks list,
        # then index each column block and merge.
        else:
            block = get_index_block(block, lin_op.args[0].size, key)
        new_coeffs.append((id_, size, block))

    return new_coeffs

def get_index_block(block, idx_size, key):
    """Transforms a coefficient into an indexed coefficient.

    Parameters
    ----------
    block : matrix
        The coefficient matrix.
    idx_size : tuple
        The dimensions of the indexed expression.
    key : tuple
        (row slice, column slice)

    Returns
    -------
    The indexed/sliced coefficient matrix.
    """
    rows, cols = idx_size
    # Number of rows in each column block.
    # and number of column blocks.
    col_selection = range(cols)[key[1]]
    # Split into column blocks.
    col_blocks = get_col_blocks(rows, block, col_selection)
    # Select rows from each remaining column block.
    row_key = (key[0], slice(None, None, None))
    # Short circuit for single column.
    if len(col_blocks) == 1:
        block = intf.index(col_blocks[0], row_key)
    else:
        indexed_blocks = []
        for col_block in col_blocks:
            idx_block = intf.index(col_block, row_key)
            # Convert to sparse CSC matrix.
            sp_intf = intf.DEFAULT_SPARSE_INTERFACE
            idx_block = sp_intf.const_to_matrix(idx_block)
            indexed_blocks.append(idx_block)
        block = sp.vstack(indexed_blocks)
    return block

def get_col_blocks(rows, coeff, col_selection):
    """Selects column blocks from a matrix.

    Parameters
    ----------
    rows : int
        The number of rows in the expression.
    coeff : NumPy matrix or SciPy sparse matrix
        The coefficient matrix to split.
    col_selection : list
        The indices of the columns to select.

    Returns
    -------
    list
        A list of column blocks from the coeff matrix.
    """
    col_blocks = []
    for col in col_selection:
        key = (slice(col*rows, (col+1)*rows, 1),
               slice(None, None, None))
        block = intf.index(coeff, key)
        col_blocks.append(block)
    return col_blocks

def transpose_coeffs(lin_op):
    """Returns the coefficients for TRANSPOSE linear op.

    Assumes lin_op's arg is a single variable.

    Parameters
    ----------
    lin_op : LinOp
        The transpose linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    coeffs = get_coefficients(lin_op.args[0])
    assert len(coeffs) == 1
    id_, size, _ = coeffs[0]
    rows, cols = size
    # Create a sparse matrix representing the transpose.
    val_arr = []
    row_arr = []
    col_arr = []
    for row in xrange(rows):
        for col in xrange(cols):
            # Row in transpose coeff.
            row_arr.append(row*cols + col)
            # Row in original coeff.
            col_arr.append(col*rows + row)
            val_arr.append(1.0)

    new_size = (rows*cols, rows*cols)
    new_block = sp.coo_matrix((val_arr, (row_arr, col_arr)), new_size)
    return [(id_, size, new_block.tocsc())]

def reshape_coeffs(lin_op):
    """Returns the coefficients for RESHAPE linear op.

    Just changes the size tuple stored with the coefficient.
    Everything else is taken care of automatically.

    Parameters
    ----------
    lin_op : LinOp
        The reshape linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    new_coeffs = []
    coeffs = get_coefficients(lin_op.args[0])
    for id_, size, block in coeffs:
        new_coeffs.append((id_, lin_op.size, block))

    return new_coeffs

def conv_coeffs(lin_op):
    """Returns the coefficients for CONV linear op.

    Parameters
    ----------
    lin_op : LinOp
        The conv linear op.

    Returns
    -------
    list
        A list of (id, size, coefficient) tuples.
    """
    lh_coeffs = get_coefficients(lin_op.data)
    constant = merge_constants(lh_coeffs)
    # Cast to 1D.
    constant = intf.from_2D_to_1D(constant)
    rh_coeffs = get_coefficients(lin_op.args[0])

    # Create a Toeplitz matrix with constant as columns.
    rows = lin_op.size[0]
    nonzeros = lin_op.data.size[0]
    toeplitz_col = np.zeros(rows)
    toeplitz_col[0:nonzeros] = constant

    cols = lin_op.args[0].size[0]
    toeplitz_row = np.zeros(cols)
    toeplitz_row[0] = constant[0]
    coeff = sp_la.toeplitz(toeplitz_col, toeplitz_row)

    # Multiply the right hand terms by the toeplitz matrix.
    return mul_by_const(coeff, rh_coeffs, (rows, 1))


# A map of LinOp type to the function to the coefficients function.
TYPE_TO_FUNC = {
    lo.SUM: sum_coeffs,
    lo.NEG: neg_coeffs,
    lo.MUL: mul_coeffs,
    lo.MUL_ELEM: mul_elemwise_coeffs,
    lo.DIV: div_coeffs,
    lo.SUM_ENTRIES: sum_entries_coeffs,
    lo.INDEX: index_coeffs,
    lo.TRANSPOSE: transpose_coeffs,
    lo.RESHAPE: reshape_coeffs,
    lo.CONV: conv_coeffs,
}


########NEW FILE########
__FILENAME__ = lin_utils
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.lin_ops.lin_op as lo
from cvxpy.lin_ops.lin_constraints import LinEqConstr, LinLeqConstr
import numpy as np

# Utility functions for dealing with LinOp.

class Counter(object):
    """A counter for ids.

    Attributes
    ----------
    count : int
        The current count.
    """
    def __init__(self):
        self.count = 0

ID_COUNTER = Counter()

def get_id():
    """Returns a new id and updates the id counter.

    Returns
    -------
    int
        A new id.
    """
    new_id = ID_COUNTER.count
    ID_COUNTER.count += 1
    return new_id

def create_var(size, var_id=None):
    """Creates a new internal variable.

    Parameters
    ----------
    size : tuple
        The (rows, cols) dimensions of the variable.
    var_id : int
        The id of the variable.

    Returns
    -------
    LinOP
        A LinOp representing the new variable.
    """
    if var_id is None:
        var_id = get_id()
    return lo.LinOp(lo.VARIABLE, size, [], var_id)

def create_param(value, size):
    """Wraps a parameter.

    Parameters
    ----------
    value : CVXPY Expression
        A function of parameters.
    size : tuple
        The (rows, cols) dimensions of the operator.

    Returns
    -------
    LinOP
        A LinOp wrapping the parameter.
    """
    return lo.LinOp(lo.PARAM, size, [], value)

def create_const(value, size, sparse=False):
    """Wraps a constant.

    Parameters
    ----------
    value : scalar, NumPy matrix, or SciPy sparse matrix.
        The numeric constant to wrap.
    size : tuple
        The (rows, cols) dimensions of the constant.
    sparse : bool
        Is the constant a SciPy sparse matrix?

    Returns
    -------
    LinOP
        A LinOp wrapping the constant.
    """
    # Check if scalar.
    if size == (1, 1):
        op_type = lo.SCALAR_CONST
    # Check if sparse.
    elif sparse:
        op_type = lo.SPARSE_CONST
    else:
        op_type = lo.DENSE_CONST
    return lo.LinOp(op_type, size, [], value)

def sum_expr(operators):
    """Add linear operators.

    Parameters
    ----------
    operators : list
        A list of linear operators.

    Returns
    -------
    LinOp
        A LinOp representing the sum of the operators.
    """
    return lo.LinOp(lo.SUM, operators[0].size, operators, None)

def neg_expr(operator):
    """Negate an operator.

    Parameters
    ----------
    expr : LinOp
        The operator to be negated.

    Returns
    -------
    LinOp
        The negated operator.
    """
    return lo.LinOp(lo.NEG, operator.size, [operator], None)

def sub_expr(lh_op, rh_op):
    """Difference of linear operators.

    Parameters
    ----------
    lh_op : LinOp
        The left-hand operator in the difference.
    rh_op : LinOp
        The right-hand operator in the difference.

    Returns
    -------
    LinOp
        A LinOp representing the difference of the operators.
    """
    return sum_expr([lh_op, neg_expr(rh_op)])

def mul_expr(lh_op, rh_op, size):
    """Multiply two linear operators.

    Parameters
    ----------
    lh_op : LinOp
        The left-hand operator in the product.
    rh_op : LinOp
        The right-hand operator in the product.
    size : tuple
        The size of the product.

    Returns
    -------
    LinOp
        A linear operator representing the product.
    """
    return lo.LinOp(lo.MUL, size, [rh_op], lh_op)

def mul_elemwise(lh_op, rh_op):
    """Multiply two linear operators elementwise.

    Parameters
    ----------
    lh_op : LinOp
        The left-hand operator in the product.
    rh_op : LinOp
        The right-hand operator in the product.

    Returns
    -------
    LinOp
        A linear operator representing the product.
    """
    return lo.LinOp(lo.MUL_ELEM, lh_op.size, [rh_op], lh_op)

def div_expr(lh_op, rh_op):
    """Divide one linear operator by another.

    Assumes rh_op is a scalar constant.

    Parameters
    ----------
    lh_op : LinOp
        The left-hand operator in the quotient.
    rh_op : LinOp
        The right-hand operator in the quotient.
    size : tuple
        The size of the quotient.

    Returns
    -------
    LinOp
        A linear operator representing the quotient.
    """
    return lo.LinOp(lo.DIV, lh_op.size, [lh_op], rh_op)

def promote(operator, size):
    """Promotes a scalar operator to the given size.

    Parameters
    ----------
    operator : LinOp
        The operator to promote.
    size : tuple
        The dimensions to promote to.

    Returns
    -------
    LinOp
        The promoted operator.
    """
    ones = create_const(np.ones(size), size)
    return mul_expr(ones, operator, size)

def sum_entries(operator):
    """Sum the entries of an operator.

    Parameters
    ----------
    expr : LinOp
        The operator to sum the entries of.

    Returns
    -------
    LinOp
        An operator representing the sum.
    """
    return lo.LinOp(lo.SUM_ENTRIES, (1, 1), [operator], None)

def index(operator, size, keys):
    """Indexes/slices an operator.

    Parameters
    ----------
    operator : LinOp
        The expression to index.
    keys : tuple
        (row slice, column slice)
    size : tuple
        The size of the expression after indexing.

    Returns
    -------
    LinOp
        An operator representing the indexing.
    """
    return lo.LinOp(lo.INDEX, size, [operator], keys)

def conv(lh_op, rh_op, size):
    """1D discrete convolution of two vectors.

    Parameters
    ----------
    lh_op : LinOp
        The left-hand operator in the convolution.
    rh_op : LinOp
        The right-hand operator in the convolution.
    size : tuple
        The size of the convolution.

    Returns
    -------
    LinOp
        A linear operator representing the convolution.
    """
    return lo.LinOp(lo.CONV, size, [rh_op], lh_op)

def transpose(operator):
    """Transposes an operator.

    Parameters
    ----------
    operator : LinOp
        The operator to transpose.

    Returns
    -------
    tuple
       (LinOp representing the transpose, [constraints])
    """
    size = (operator.size[1], operator.size[0])
    # If operator is a Variable, no need to create a new variable.
    if operator.type is lo.VARIABLE:
        return (lo.LinOp(lo.TRANSPOSE, size, [operator], None), [])
    # Operator is not a variable, create a constraint and new variable.
    else:
        new_var = create_var(operator.size)
        new_op = lo.LinOp(lo.TRANSPOSE, size, [new_var], None)
        constraints = [create_eq(new_var, operator)]
        return (new_op, constraints)

def reshape(operator, size):
    """Reshapes an operator.

    Parameters
    ----------
    operator : LinOp
        The operator to reshape.
    size : tuple
        The (rows, cols) of the reshaped operator.

    Returns
    -------
    LinOp
       LinOp representing the reshaped expression.
    """
    return lo.LinOp(lo.RESHAPE, size, [operator], None)

def get_constr_expr(lh_op, rh_op):
    """Returns the operator in the constraint.
    """
    # rh_op defaults to 0.
    if rh_op is None:
        return lh_op
    else:
        return sum_expr([lh_op, neg_expr(rh_op)])

def create_eq(lh_op, rh_op=None, constr_id=None):
    """Creates an internal equality constraint.

    Parameters
    ----------
    lh_term : LinOp
        The left-hand operator in the equality constraint.
    rh_term : LinOp
        The right-hand operator in the equality constraint.
    constr_id : int
        The id of the CVXPY equality constraint creating the constraint.

    Returns
    -------
    LinEqConstr
    """
    if constr_id is None:
        constr_id = get_id()
    expr = get_constr_expr(lh_op, rh_op)
    return LinEqConstr(expr, constr_id, lh_op.size)

def create_leq(lh_op, rh_op=None, constr_id=None):
    """Creates an internal less than or equal constraint.

    Parameters
    ----------
    lh_term : LinOp
        The left-hand operator in the <= constraint.
    rh_term : LinOp
        The right-hand operator in the <= constraint.
    constr_id : int
        The id of the CVXPY equality constraint creating the constraint.

    Returns
    -------
    LinLeqConstr
    """
    if constr_id is None:
        constr_id = get_id()
    expr = get_constr_expr(lh_op, rh_op)
    return LinLeqConstr(expr, constr_id, lh_op.size)

def create_geq(lh_op, rh_op=None, constr_id=None):
    """Creates an internal greater than or equal constraint.

    Parameters
    ----------
    lh_term : LinOp
        The left-hand operator in the <= constraint.
    rh_term : LinOp
        The right-hand operator in the <= constraint.
    constr_id : int
        The id of the CVXPY equality constraint creating the constraint.

    Returns
    -------
    LinLeqConstr
    """
    if rh_op is not None:
        rh_op = neg_expr(rh_op)
    return create_leq(neg_expr(lh_op), rh_op, constr_id)

def get_expr_vars(operator):
    """Get a list of the variables in the operator and their sizes.

    Parameters
    ----------
    operator : LinOp
        The operator to extract the variables from.

    Returns
    -------
    list
        A list of (var id, var size) pairs.
    """
    if operator.type is lo.VARIABLE:
        return [(operator.data, operator.size)]
    else:
        vars_ = []
        for arg in operator.args:
            vars_ += get_expr_vars(arg)
        return vars_

########NEW FILE########
__FILENAME__ = tree_mat
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.interface as intf
import cvxpy.lin_ops.lin_op as lo
import copy
import numpy as np
from numpy.fft import fft, ifft

# Utility functions for treating an expression tree as a matrix
# and multiplying by it and it's transpose.

def mul(lin_op, val_dict):
    """Multiply the expression tree by a vector.

    Parameters
    ----------
    lin_op : LinOp
        The root of an expression tree.
    val_dict : dict
        A map of variable id to value.

    Returns
    -------
    NumPy matrix
        The result of the multiplication.
    """
    # Look up the value for a variable.
    if lin_op.type is lo.VARIABLE:
        if lin_op.data in val_dict:
            return val_dict[lin_op.data]
        # Defaults to zero if no value given.
        else:
            return np.mat(np.zeros(lin_op.size))
    # Return all zeros for NO_OP.
    elif lin_op.type is lo.NO_OP:
        return np.mat(np.zeros(lin_op.size))
    else:
        eval_args = []
        for arg in lin_op.args:
            eval_args.append(mul(arg, val_dict))
        return op_mul(lin_op, eval_args)

def tmul(lin_op, value):
    """Multiply the transpose of the expression tree by a vector.

    Parameters
    ----------
    lin_op : LinOp
        The root of an expression tree.
    value : NumPy matrix
        The vector to multiply by.

    Returns
    -------
    dict
        A map of variable id to value.
    """
    # Store the value as the variable.
    if lin_op.type is lo.VARIABLE:
        return {lin_op.data: value}
    # Do nothing for NO_OP.
    elif lin_op.type is lo.NO_OP:
        return {}
    else:
        result = op_tmul(lin_op, value)
        result_dicts = []
        for arg in lin_op.args:
            result_dicts.append(tmul(arg, result))
        # Sum repeated ids.
        return sum_dicts(result_dicts)

def sum_dicts(dicts):
    """Sums the dictionaries entrywise.

    Parameters
    ----------
    dicts : list
        A list of dictionaries with numeric entries.

    Returns
    -------
    dict
        A dict with the sum.
    """
    # Sum repeated entries.
    sum_dict = {}
    for val_dict in dicts:
        for id_, value in val_dict.items():
            if id_ in sum_dict:
                sum_dict[id_] = sum_dict[id_] + value
            else:
                sum_dict[id_] = value
    return sum_dict

def op_mul(lin_op, args):
    """Applies the linear operator to the arguments.

    Parameters
    ----------
    lin_op : LinOp
        A linear operator.
    args : list
        The arguments to the operator.

    Returns
    -------
    NumPy matrix or SciPy sparse matrix.
        The result of applying the linear operator.
    """
    #print lin_op.type
    # Constants convert directly to their value.
    if lin_op.type in [lo.SCALAR_CONST, lo.DENSE_CONST, lo.SPARSE_CONST]:
        result = lin_op.data
    # No-op is not evaluated.
    elif lin_op.type is lo.NO_OP:
        return None
    # For non-leaves, recurse on args.
    elif lin_op.type is lo.SUM:
        result = sum(args)
    elif lin_op.type is lo.NEG:
        result = -args[0]
    elif lin_op.type is lo.MUL:
        coeff = mul(lin_op.data, {})
        result = coeff*args[0]
    elif lin_op.type is lo.DIV:
        divisor = mul(lin_op.data, {})
        result = args[0]/divisor
    elif lin_op.type is lo.SUM_ENTRIES:
        result = np.sum(args[0])
    elif lin_op.type is lo.INDEX:
        row_slc, col_slc = lin_op.data
        result = args[0][row_slc, col_slc]
    elif lin_op.type is lo.TRANSPOSE:
        result = args[0].T
    elif lin_op.type is lo.CONV:
        result = conv_mul(lin_op, args[0])
    else:
        raise Exception("Unknown linear operator.")
    #print result
    return result

def op_tmul(lin_op, value):
    """Applies the transpose of the linear operator to the arguments.

    Parameters
    ----------
    lin_op : LinOp
        A linear operator.
    value : NumPy matrix
        A numeric value to apply the operator's transpose to.

    Returns
    -------
    NumPy matrix or SciPy sparse matrix.
        The result of applying the linear operator.
    """
    if lin_op.type is lo.SUM:
        result = value
    elif lin_op.type is lo.NEG:
        result = -value
    elif lin_op.type is lo.MUL:
        coeff = mul(lin_op.data, {})
        # Scalar coefficient, no need to transpose.
        if np.isscalar(coeff):
            result = coeff*value
        # If the right hand side was promoted,
        # multiplying by the transpose is a dot product.
        elif lin_op.args[0].size == (1, 1):
            result = np.multiply(coeff, value).sum()
        else:
            result = coeff.T*value
    elif lin_op.type is lo.DIV:
        divisor = mul(lin_op.data, {})
        result = value/divisor
    elif lin_op.type is lo.SUM_ENTRIES:
        result = np.mat(np.ones(lin_op.args[0].size))*value
    elif lin_op.type is lo.INDEX:
        row_slc, col_slc = lin_op.data
        result = np.mat(np.zeros(lin_op.args[0].size))
        result[row_slc, col_slc] = value
    elif lin_op.type is lo.TRANSPOSE:
        result = value.T
    elif lin_op.type is lo.CONV:
        return conv_mul(lin_op, value, True)
    else:
        raise Exception("Unknown linear operator.")
    return result

def conv_mul(lin_op, rh_val, transpose=False):
    """Multiply by a convolution operator.
    """
    # F^-1{F{left hand}*F(right hand)}
    length = lin_op.size[0]
    constant = mul(lin_op.data, {})
    # Convert to 2D
    constant, rh_val = map(intf.from_1D_to_2D, [constant, rh_val])
    lh_term = fft(constant, length, axis=0)
    rh_term = fft(rh_val, length, axis=0)
    # Transpose equivalent to taking conjugate
    # and keeping only first m terms.
    if transpose:
        lh_term = np.conjugate(lh_term)
    product = np.multiply(lh_term, rh_term)
    result = ifft(product, length, axis=0).real

    if transpose:
        rh_length = lin_op.args[0].size[0]
        return result[:rh_length]
    else:
        return result

def get_constant(lin_op):
    """Returns the constant term in the expression.

    Parameters
    ----------
    lin_op : LinOp
        The root linear operator.

    Returns
    -------
    NumPy NDArray
        The constant term as a flattened vector.
    """
    constant = mul(lin_op, {})
    const_size = constant.shape[0]*constant.shape[1]
    return np.reshape(constant, const_size, 'F')

def get_constr_constant(constraints):
    """Returns the constant term for the constraints matrix.

    Parameters
    ----------
    constraints : list
        The constraints that form the matrix.

    Returns
    -------
    NumPy NDArray
        The constant term as a flattened vector.
    """
    # TODO what if constraints is empty?
    constants = [get_constant(c.expr) for c in constraints]
    return np.hstack(constants)

def prune_constants(constraints):
    """Returns a new list of constraints with constant terms removed.

    Parameters
    ----------
    constraints : list
        The constraints that form the matrix.

    Returns
    -------
    list
        The pruned constraints.
    """
    pruned_constraints = []
    for constr in constraints:
        constr_type = type(constr)
        expr = copy.deepcopy(constr.expr)
        is_constant = prune_expr(expr)
        # Replace a constant root with a NO_OP.
        if is_constant:
            expr = lo.LinOp(lo.NO_OP, expr.size, [], None)
        pruned = constr_type(expr, constr.constr_id, constr.size)
        pruned_constraints.append(pruned)
    return pruned_constraints

def prune_expr(lin_op):
    """Prunes constant branches from the expression.

    Parameters
    ----------
    lin_op : LinOp
        The root linear operator.

    Returns
    -------
    bool
        Were all the expression's arguments pruned?
    """
    if lin_op.type is lo.VARIABLE:
        return False
    elif lin_op.type in [lo.SCALAR_CONST,
                         lo.DENSE_CONST,
                         lo.SPARSE_CONST,
                         lo.PARAM]:
        return True

    pruned_args = []
    is_constant = True
    for arg in lin_op.args:
        arg_constant = prune_expr(arg)
        if not arg_constant:
            is_constant = False
            pruned_args.append(arg)
    # Overwrite old args with only non-constant args.
    lin_op.args[:] = pruned_args[:]
    return is_constant

########NEW FILE########
__FILENAME__ = sparse
import cvxpy as cp
import cvxpy.settings as s
import itertools
from cvxopt import spmatrix
import cvxopt
import numpy as np
import time

import cProfile
cProfile.run("""
import cvxpy as cp
n = 2000
A = cp.Variable(n*n, 1)
obj = cp.Minimize(cp.norm(A, 'fro'))
p = cp.Problem(obj, [A >= 2])
result = p.solve(verbose=True)
print result
""")

# m = 100
# n = 1000
# prob = 0.999

# a_arr = np.random.random((m, n))
# a_arr[a_arr < prob] = 0

# a_arr_sp = spmatrix(a_arr[a_arr.nonzero()[0],
# 						  a_arr.nonzero()[1]],
# 					a_arr.nonzero()[0],
# 					a_arr.nonzero()[1],
# 					size=(m, n))

# W = cp.Variable(n, n)
# constraints = []

# constraints.extend( [W[i,i] == 0 for i in range(n)] )
# constraints.append(W >= 0)
# lam = 8
# beta = 0.5
# loss = cp.sum(a_arr_sp - a_arr_sp*W)
# l2_reg = 0.5*beta*cp.square(cp.norm(W))
# l1_reg = lam*cp.sum(W)
# obj = cp.Minimize(loss + l2_reg + l1_reg)
# # TODO No constraints, get error.
# p = cp.Problem(obj, constraints)

# import cProfile
# cProfile.run('p.solve()')


# objective, constr_map, dims = p.canonicalize()

# all_ineq = itertools.chain(constr_map[s.EQ], constr_map[s.INEQ])
# var_offsets, x_length = p._get_var_offsets(objective, all_ineq)

# c, obj_offset = p._constr_matrix([objective], var_offsets, x_length,
#                                  p._DENSE_INTF,
#                                  p._DENSE_INTF)
# A, b = p._constr_matrix(constr_map[s.EQ], var_offsets, x_length,
#                            p._SPARSE_INTF, p._DENSE_INTF)

# G, h = p._constr_matrix(constr_map[s.INEQ], var_offsets, x_length,
#                            p._SPARSE_INTF, p._DENSE_INTF)

# print len(constr_map[s.EQ])
# print len(constr_map[s.INEQ])

# cProfile.run("""
# G, h = p._constr_matrix(constr_map[s.INEQ], var_offsets, x_length,
#                            p._SPARSE_INTF, p._DENSE_INTF)
# """)
# import numbers

# aff_expressions = constr_map[s.INEQ]
# matrix_intf, vec_intf = p._SPARSE_INTF, p._DENSE_INTF

# expr_offsets = {}
# vert_offset = 0
# for aff_exp in aff_expressions:
#     expr_offsets[str(aff_exp)] = vert_offset
#     vert_offset += aff_exp.size[0]*aff_exp.size[1]

# #rows = sum([aff.size[0] * aff.size[1] for aff in aff_expressions])
# rows = vert_offset
# cols = x_length
# #const_vec = vec_intf.zeros(rows, 1)
# vert_offset = 0

# def carrier(expr_offsets, var_offsets):
#     def f(aff_exp):
#         V, I, J = [], [], []
#         vert_offset = expr_offsets[str(aff_exp)]
#         coefficients = aff_exp.coefficients()
#         for var, blocks in coefficients.items():
#             # Constant is not in var_offsets.
#             horiz_offset = var_offsets.get(var)
#             for col, block in enumerate(blocks):
#                 vert_start = vert_offset + col*aff_exp.size[0]
#                 vert_end = vert_start + aff_exp.size[0]
#                 if var is s.CONSTANT:
#                     pass
#                     #const_vec[vert_start:vert_end, :] = block
#                 else:
#                     if isinstance(block, numbers.Number):
#                         V.append(block)
#                         I.append(vert_start)
#                         J.append(horiz_offset)
#                     else: # Block is a matrix or spmatrix.
#                         if isinstance(block, cvxopt.matrix):
#                             block = cvxopt.sparse(block)
#                         V.extend(block.V)
#                         I.extend(block.I + vert_start)
#                         J.extend(block.J + horiz_offset)
#         return (V, I, J)
#     return f

# f = carrier(expr_offsets, var_offsets)

# from multiprocessing import Pool
# p = Pool(1)
# result = p.map(f, aff_expressions)
# V, I, J = [], [], []
# for v, i, j in result:
#     V.extend(v)
#     I.extend(i)
#     J.extend(j)

# #[item for sublist in l for item in sublist]
# # Create the constraints matrix.
# if len(V) > 0:
#     matrix = cvxopt.spmatrix(V, I, J, (rows, cols), tc='d')
#     # Convert the constraints matrix to the correct type.
#     matrix = matrix_intf.const_to_matrix(matrix, convert_scalars=True)
# else: # Empty matrix.
#     matrix = matrix_intf.zeros(rows, cols)

########NEW FILE########
__FILENAME__ = test_robustness
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.atoms as at
from cvxpy.expressions.constants import Constant
from cvxpy.expressions.variables import Variable
from cvxpy.problems.objective import *
from cvxpy.problems.problem import Problem
import cvxpy.interface.matrix_utilities as intf
from cvxopt import matrix
import scipy.sparse as sp
import unittest

class TestProblem(unittest.TestCase):
    """ Unit tests for the expression/expression module. """
    def setUp(self):
        self.a = Variable(name='a')
        self.b = Variable(name='b')
        self.c = Variable(name='c')

        self.x = Variable(2, name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(2, name='z')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # Overriden method to handle lists and lower accuracy.
    # ECHU: uncommented to ensure that tests pass
    def assertAlmostEqual(self, a, b, interface=intf.DEFAULT_INTERFACE):
        try:
            a = list(a)
            b = list(b)
            for i in range(len(a)):
                self.assertAlmostEqual(a[i], b[i])
        except Exception:
            super(TestProblem, self).assertAlmostEqual(a,b,places=4)

    def test_large_sum(self):
        """Test large number of variables summed.
        """
        for n in [10, 20, 30, 40, 50]:
            A = matrix(range(n*n), (n,n))
            x = Variable(n,n)
            p = Problem(Minimize(at.sum_entries(x)), [x >= A])
            result = p.solve()
            answer = n*n*(n*n+1)/2 - n*n
            print result - answer
            self.assertAlmostEqual(result, answer)

    def test_large_square(self):
        """Test large number of variables squared.
        """
        for n in [10, 20, 30, 40, 50]:
            A = matrix(range(n*n), (n,n))
            x = Variable(n,n)
            p = Problem(Minimize(at.square(x[0, 0])),
                [x >= A])
            result = p.solve()
            self.assertAlmostEqual(result, 0)

    def test_sdp(self):
        """Test a problem with semidefinite cones.
        """
        a = sp.rand(100,100,.1, random_state=1)
        a = a.todense()
        X = Variable(100,100)
        obj = at.norm(X, "nuc") + at.norm(X-a,'fro')
        p = Problem(Minimize(obj))
        p.solve(solver="SCS")

########NEW FILE########
__FILENAME__ = iterative
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Methods for SCS iterative solver.

from cvxpy.lin_ops.tree_mat import mul, tmul, sum_dicts
import numpy as np
import scipy.sparse.linalg as LA


def get_mul_funcs(constraints, dims,
                  var_offsets, var_sizes, var_length):

    def accAmul(x, y):
        # y += A*x
        rows = y.shape[0]
        var_dict = vec_to_dict(x, var_offsets, var_sizes)
        y += constr_mul(constraints, var_dict, rows)

    def accATmul(x, y):
        # y += A.T*x
        terms = constr_unpack(constraints, x)
        val_dict = constr_tmul(constraints, terms)
        y += dict_to_vec(val_dict, var_offsets,
                         var_sizes, var_length)

    return (accAmul, accATmul)

def constr_unpack(constraints, vector):
    """Unpacks a vector into a list of values for constraints.
    """
    values = []
    offset = 0
    for constr in constraints:
        rows, cols = constr.size
        val = np.zeros((rows, cols))
        for col in range(cols):
            val[:, col] = vector[offset:offset+rows]
            offset += rows
        values.append(val)
    return values

def vec_to_dict(vector, var_offsets, var_sizes):
    """Converts a vector to a map of variable id to value.

    Parameters
    ----------
    vector : NumPy matrix
        The vector of values.
    var_offsets : dict
        A map of variable id to offset in the vector.
    var_sizes : dict
        A map of variable id to variable size.

    Returns
    -------
    dict
        A map of variable id to variable value.
    """
    val_dict = {}
    for id_, offset in var_offsets.items():
        size = var_sizes[id_]
        value = np.zeros(size)
        offset = var_offsets[id_]
        for col in range(size[1]):
            value[:, col] = vector[offset:size[0]+offset]
            offset += size[0]
        val_dict[id_] = value
    return val_dict

def dict_to_vec(val_dict, var_offsets, var_sizes, vec_len):
    """Converts a map of variable id to value to a vector.

    Parameters
    ----------
    val_dict : dict
        A map of variable id to value.
    var_offsets : dict
        A map of variable id to offset in the vector.
    var_sizes : dict
        A map of variable id to variable size.
    vector : NumPy matrix
        The vector to store the values in.
    """
    # TODO take in vector.
    vector = np.zeros(vec_len)
    for id_, value in val_dict.items():
        size = var_sizes[id_]
        offset = var_offsets[id_]
        for col in range(size[1]):
            # Handle scalars separately.
            if np.isscalar(value):
                vector[offset:size[0]+offset] = value
            else:
                vector[offset:size[0]+offset] =  np.squeeze(value[:, col])
            offset += size[0]
    return vector

def constr_mul(constraints, var_dict, vec_size):
    """Multiplies a vector by the matrix implied by the constraints.

    Parameters
    ----------
    constraints : list
        A list of linear constraints.
    var_dict : dict
        A dictionary mapping variable id to value.
    vec_size : int
        The length of the product vector.
    """
    product = np.zeros(vec_size)
    offset = 0
    for constr in constraints:
        result = mul(constr.expr, var_dict)
        rows, cols = constr.size
        for col in range(cols):
            # Handle scalars separately.
            if np.isscalar(result):
                product[offset:offset+rows] = result
            else:
                product[offset:offset+rows] = np.squeeze(result[:, col])
            offset += rows

    return product

def constr_tmul(constraints, values):
    """Multiplies a vector by the transpose of the constraints matrix.

    Parameters
    ----------
    constraints : list
        A list of linear constraints.
    values : list
        A list of NumPy matrices.

    Returns
    -------
    dict
        A mapping of variable id to value.
    """
    products = []
    for constr, val in zip(constraints, values):
        products.append(tmul(constr.expr, val))
    return sum_dicts(products)

########NEW FILE########
__FILENAME__ = kktsolver
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# A custom KKT solver for CVXOPT that can handle redundant constraints.
# Uses regularization and iterative refinement.

from cvxopt import blas, lapack
from cvxopt.base import matrix
from cvxopt.misc import scale, pack, unpack

# Regularization constant.
REG_EPS = 1e-9

# Returns a kktsolver for linear cone programs (or nonlinear if F is given).
def get_kktsolver(G, dims, A, F=None):
    if F is None:
        factor = kkt_ldl(G, dims, A)
        def kktsolver(W):
            return factor(W)
    else:
        mnl, x0 = F()
        factor = kkt_ldl(G, dims, A, mnl)
        def kktsolver(x, z, W):
            f, Df, H = F(x, z)
            return factor(W, H, Df)
    return kktsolver

def kkt_ldl(G, dims, A, mnl = 0):
    """
    Solution of KKT equations by a dense LDL factorization of the
    3 x 3 system.

    Returns a function that (1) computes the LDL factorization of

        [ H           A'   GG'*W^{-1} ]
        [ A           0    0          ],
        [ W^{-T}*GG   0   -I          ]

    given H, Df, W, where GG = [Df; G], and (2) returns a function for
    solving

        [ H     A'   GG'   ]   [ ux ]   [ bx ]
        [ A     0    0     ] * [ uy ] = [ by ].
        [ GG    0   -W'*W  ]   [ uz ]   [ bz ]

    H is n x n,  A is p x n, Df is mnl x n, G is N x n where
    N = dims['l'] + sum(dims['q']) + sum( k**2 for k in dims['s'] ).
    """

    p, n = A.size
    ldK = n + p + mnl + dims['l'] + sum(dims['q']) + sum([ int(k*(k+1)/2)
        for k in dims['s'] ])
    K = matrix(0.0, (ldK, ldK))
    ipiv = matrix(0, (ldK, 1))
    u = matrix(0.0, (ldK, 1))
    g = matrix(0.0, (mnl + G.size[0], 1))

    def factor(W, H = None, Df = None):
        blas.scal(0.0, K)
        if H is not None: K[:n, :n] = H
        K[n:n+p, :n] = A
        for k in range(n):
            if mnl: g[:mnl] = Df[:,k]
            g[mnl:] = G[:,k]
            scale(g, W, trans = 'T', inverse = 'I')
            pack(g, K, dims, mnl, offsety = k*ldK + n + p)
        K[(ldK+1)*(p+n) :: ldK+1]  = -1.0
        # Add positive regularization in 1x1 block and negative in 2x2 block.
        K[0 : (ldK+1)*n : ldK+1]  += REG_EPS
        K[(ldK+1)*n :: ldK+1]  += -REG_EPS
        lapack.sytrf(K, ipiv)

        def solve(x, y, z):

            # Solve
            #
            #     [ H          A'   GG'*W^{-1} ]   [ ux   ]   [ bx        ]
            #     [ A          0    0          ] * [ uy   [ = [ by        ]
            #     [ W^{-T}*GG  0   -I          ]   [ W*uz ]   [ W^{-T}*bz ]
            #
            # and return ux, uy, W*uz.
            #
            # On entry, x, y, z contain bx, by, bz.  On exit, they contain
            # the solution ux, uy, W*uz.
            blas.copy(x, u)
            blas.copy(y, u, offsety = n)
            scale(z, W, trans = 'T', inverse = 'I')
            pack(z, u, dims, mnl, offsety = n + p)
            lapack.sytrs(K, ipiv, u)
            blas.copy(u, x, n = n)
            blas.copy(u, y, offsetx = n, n = p)
            unpack(u, z, dims, mnl, offsetx = n + p)

        return solve

    return factor

########NEW FILE########
__FILENAME__ = objective
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.utilities as u
from cvxpy.expressions.expression import Expression
import cvxpy.lin_ops.lin_utils as lu

class Minimize(u.Canonical):
    """An optimization objective for minimization.
    """

    NAME = "minimize"

    def __init__(self, expr):
        self._expr = Expression.cast_to_const(expr)
        # Validate that the objective resolves to a scalar.
        if self._expr.size != (1, 1):
            raise Exception("The '%s' objective must resolve to a scalar."
                            % self.NAME)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._expr))

    def __str__(self):
        return ' '.join([self.NAME, self._expr.name()])

    def canonicalize(self):
        """Pass on the target expression's objective and constraints.
        """
        return self._expr.canonical_form

    def variables(self):
        """Returns the variables in the objective.
        """
        return self._expr.variables()

    def parameters(self):
        """Returns the parameters in the objective.
        """
        return self._expr.parameters()

    def is_dcp(self):
        """The objective must be convex.
        """
        return self._expr.is_convex()

    @property
    def value(self):
        """The value of the objective expression.
        """
        return self._expr.value

    @staticmethod
    def _primal_to_result(result):
        """The value of the objective given the solver primal value.
        """
        return result

class Maximize(Minimize):
    """An optimization objective for maximization.
    """

    NAME = "maximize"

    def canonicalize(self):
        """Negates the target expression's objective.
        """
        obj, constraints = super(Maximize, self).canonicalize()
        return (lu.neg_expr(obj), constraints)

    def is_dcp(self):
        """The objective must be concave.
        """
        return self._expr.is_concave()

    @staticmethod
    def _primal_to_result(result):
        """The value of the objective given the solver primal value.
        """
        return -result

########NEW FILE########
__FILENAME__ = problem
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.settings as s
import cvxpy.utilities as u
from toolz.itertoolz import unique
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
import cvxpy.lin_ops as lo
import cvxpy.lin_ops.lin_to_matrix as op2mat
import cvxpy.lin_ops.tree_mat as tree_mat
from cvxpy.constraints import (EqConstraint, LeqConstraint,
SOC, SOC_Elemwise, SDP, ExpCone)
from cvxpy.problems.objective import Minimize, Maximize
from cvxpy.problems.kktsolver import get_kktsolver
import cvxpy.problems.iterative as iterative

from collections import OrderedDict
import itertools
import numbers
import cvxopt
import cvxopt.solvers
import ecos
import scs
import numpy as np
import scipy.sparse as sp

class Problem(u.Canonical):
    """A convex optimization problem.

    Attributes
    ----------
    objective : Minimize or Maximize
        The expression to minimize or maximize.
    constraints : list
        The constraints on the problem variables.
    """

    # The solve methods available.
    REGISTERED_SOLVE_METHODS = {}
    # Interfaces for interacting with matrices.
    _SPARSE_INTF = intf.DEFAULT_SPARSE_INTERFACE
    _DENSE_INTF = intf.DEFAULT_INTERFACE
    _CVXOPT_DENSE_INTF = intf.get_matrix_interface(cvxopt.matrix)
    _CVXOPT_SPARSE_INTF = intf.get_matrix_interface(cvxopt.spmatrix)

    def __init__(self, objective, constraints=None):
        if constraints is None:
            constraints = []
        self.objective = objective
        self.constraints = constraints
        self._value = None
        self._status = None

    @property
    def value(self):
        """The value from the last time the problem was solved.

        Returns
        -------
        float or None
        """
        return self._value

    @property
    def status(self):
        """The status from the last time the problem was solved.

        Returns
        -------
        str
        """
        return self._status

    def is_dcp(self):
        """Does the problem satisfy DCP rules?
        """
        return all(exp.is_dcp() for exp in self.constraints + [self.objective])

    def _filter_constraints(self, constraints):
        """Separate the constraints by type.

        Parameters
        ----------
        constraints : list
            A list of constraints.

        Returns
        -------
        dict
            A map of type key to an ordered set of constraints.
        """
        constr_map = {s.EQ: [],
                      s.LEQ: [],
                      s.SOC: [],
                      s.SOC_EW: [],
                      s.SDP: [],
                      s.EXP: []}
        for c in constraints:
            if isinstance(c, lo.LinEqConstr):
                constr_map[s.EQ].append(c)
            elif isinstance(c, lo.LinLeqConstr):
                constr_map[s.LEQ].append(c)
            elif isinstance(c, SOC_Elemwise):
                constr_map[s.SOC_EW].append(c)
            elif isinstance(c, SOC):
                constr_map[s.SOC].append(c)
            elif isinstance(c, SDP):
                constr_map[s.SDP].append(c)
            elif isinstance(c, ExpCone):
                constr_map[s.EXP].append(c)
        return constr_map

    def canonicalize(self):
        """Computes the graph implementation of the problem.

        Returns
        -------
        tuple
            (affine objective,
             constraints dict)
        """
        constraints = []
        obj, constr = self.objective.canonical_form
        constraints += constr
        unique_constraints = list(unique(self.constraints,
                                         key=lambda c: c.id))
        for constr in unique_constraints:
            constraints += constr.canonical_form[1]
        constr_map = self._filter_constraints(constraints)

        return (obj, constr_map)

    def _format_for_solver(self, constr_map, solver):
        """Formats the problem for the solver.

        Parameters
        ----------
        constr_map : dict
            A map of constraint type to a list of constraints.
        solver: str
            The solver being targetted.

        Returns
        -------
        dict
            The dimensions of the cones.
        """
        dims = {}
        dims["f"] = sum(c.size[0]*c.size[1] for c in constr_map[s.EQ])
        dims["l"] = sum(c.size[0]*c.size[1] for c in constr_map[s.LEQ])
        # Formats SOC, SOC_EW, and SDP constraints for the solver.
        nonlin = constr_map[s.SOC] + constr_map[s.SOC_EW] + constr_map[s.SDP]
        for constr in nonlin:
            for ineq_constr in constr.format():
                constr_map[s.LEQ].append(ineq_constr)
        dims["q"] = [c.size[0] for c in constr_map[s.SOC]]
        # Elemwise SOC constraints have an SOC constraint
        # for each element in their arguments.
        for constr in constr_map[s.SOC_EW]:
            for cone_size in constr.size:
                dims["q"].append(cone_size[0])
        dims["s"] = [c.size[0] for c in constr_map[s.SDP]]

        # Format exponential cone constraints.
        if solver == s.CVXOPT:
            for constr in constr_map[s.EXP]:
                constr_map[s.EQ] += constr.format(s.CVXOPT)
        elif solver == s.SCS:
            for constr in constr_map[s.EXP]:
                constr_map[s.LEQ] += constr.format(s.SCS)
            dims["ep"] = sum(c.size[0]*c.size[1] for c in constr_map[s.EXP])

        # Remove redundant constraints.
        for key in [s.EQ, s.LEQ]:
            constraints = unique(constr_map[key],
                                 key=lambda c: c.constr_id)
            constr_map[key] = list(constraints)

        return dims

    @staticmethod
    def _constraints_count(constr_map):
        """Returns the number of internal constraints.
        """
        return sum([len(cset) for cset in constr_map.values()])

    def _choose_solver(self, constr_map):
        """Determines the appropriate solver.

        Parameters
        ----------
        constr_map: dict
            A dict of the canonicalized constraints.

        Returns
        -------
        str
            The solver that will be used.
        """
        # If no constraints, use ECOS.
        if self._constraints_count(constr_map) == 0:
            return s.ECOS
        # If SDP, defaults to CVXOPT.
        elif constr_map[s.SDP]:
            return s.CVXOPT
        # If EXP cone without SDP, defaults to SCS.
        elif constr_map[s.EXP]:
            return s.SCS
        # Otherwise use ECOS.
        else:
            return s.ECOS

    def _validate_solver(self, constr_map, solver):
        """Raises an exception if the solver cannot solve the problem.

        Parameters
        ----------
        constr_map: dict
            A dict of the canonicalized constraints.
        solver : str
            The solver to be used.
        """
        if (constr_map[s.SDP] and not solver in s.SDP_CAPABLE) or \
           (constr_map[s.EXP] and not solver in s.EXP_CAPABLE) or \
           (self._constraints_count(constr_map) == 0 and solver == s.SCS):
            raise Exception(
                "The solver %s cannot solve the problem." % solver
            )

    def variables(self):
        """Returns a list of the variables in the problem.
        """
        vars_ = self.objective.variables()
        for constr in self.constraints:
            vars_ += constr.variables()
        # Remove duplicates.
        return list(set(vars_))

    def parameters(self):
        """Returns a list of the parameters in the problem.
        """
        params = self.objective.parameters()
        for constr in self.constraints:
            params += constr.parameters()
        # Remove duplicates.
        return list(set(params))

    def solve(self, *args, **kwargs):
        """Solves the problem using the specified method.

        Parameters
        ----------
        method : function
            The solve method to use.
        solver : str, optional
            The solver to use.
        verbose : bool, optional
            Overrides the default of hiding solver output.
        solver_specific_opts : dict, optional
            A dict of options that will be passed to the specific solver.
            In general, these options will override any default settings
            imposed by cvxpy.

        Returns
        -------
        float
            The optimal value for the problem, or a string indicating
            why the problem could not be solved.
        """
        func_name = kwargs.pop("method", None)
        if func_name is not None:
            func = Problem.REGISTERED_SOLVE_METHODS[func_name]
            return func(self, *args, **kwargs)
        else:
            return self._solve(*args, **kwargs)

    @classmethod
    def register_solve(cls, name, func):
        """Adds a solve method to the Problem class.

        Parameters
        ----------
        name : str
            The keyword for the method.
        func : function
            The function that executes the solve method.
        """
        cls.REGISTERED_SOLVE_METHODS[name] = func

    def get_problem_data(self, solver):
        """Returns the problem data used in the call to the solver.

        Parameters
        ----------
        solver : str
            The solver the problem data is for.

        Returns
        -------
        tuple
            arguments to solver
        """
        objective, constr_map = self.canonicalize()
        # Raise an error if the solver cannot handle the problem.
        self._validate_solver(constr_map, solver)
        dims = self._format_for_solver(constr_map, solver)
        all_ineq = constr_map[s.EQ] + constr_map[s.LEQ]
        var_offsets, var_sizes, x_length = self._get_var_offsets(objective,
                                                                 all_ineq)

        if solver == s.ECOS and not (constr_map[s.SDP] or constr_map[s.EXP]):
            args, offset = self._ecos_problem_data(objective, constr_map, dims,
                                                   var_offsets, x_length)
        elif solver == s.CVXOPT and not constr_map[s.EXP]:
            args, offset = self._cvxopt_problem_data(objective, constr_map, dims,
                                                     var_offsets, x_length)
        elif solver == s.SCS:
            args, offset = self._scs_problem_data(objective, constr_map, dims,
                                                  var_offsets, x_length)
        else:
            raise Exception("Cannot return problem data for the solver %s." % solver)
        return args

    def _solve(self, solver=None, ignore_dcp=False, verbose=False,
               solver_specific_opts=None):
        """Solves a DCP compliant optimization problem.

        Saves the values of primal and dual variables in the variable
        and constraint objects, respectively.

        Parameters
        ----------
        solver : str, optional
            The solver to use. Defaults to ECOS.
        ignore_dcp : bool, optional
            Overrides the default of raising an exception if the problem is not
            DCP.
        verbose : bool, optional
            Overrides the default of hiding solver output.
        solver_specific_opts : dict, optional
            A dict of options that will be passed to the specific solver.
            In general, these options will override any default settings
            imposed by cvxpy.

        Returns
        -------
        float
            The optimal value for the problem, or a string indicating
            why the problem could not be solved.
        """
        # Safely set default as empty dict.
        if solver_specific_opts is None:
            solver_specific_opts = {}

        if not self.is_dcp():
            if ignore_dcp:
                print ("Problem does not follow DCP rules. "
                       "Solving a convex relaxation.")
            else:
                raise Exception("Problem does not follow DCP rules.")

        objective, constr_map = self.canonicalize()
        # Choose a default solver if none specified.
        if solver is None:
            solver = self._choose_solver(constr_map)
        else:
            # Raise an error if the solver cannot handle the problem.
            self._validate_solver(constr_map, solver)

        dims = self._format_for_solver(constr_map, solver)

        all_ineq = constr_map[s.EQ] + constr_map[s.LEQ]
        var_offsets, var_sizes, x_length = self._get_var_offsets(objective,
                                                                 all_ineq)

        if solver == s.CVXOPT:
            result = self._cvxopt_solve(objective, constr_map, dims,
                                        var_offsets, x_length,
                                        verbose, solver_specific_opts)
        elif solver == s.SCS:
            result = self._scs_solve(objective, constr_map, dims,
                                     var_offsets, x_length,
                                     verbose, solver_specific_opts)
        elif solver == s.ECOS:
            result = self._ecos_solve(objective, constr_map, dims,
                                      var_offsets, x_length,
                                      verbose, solver_specific_opts)
        else:
            raise Exception("Unknown solver.")

        status, value, x, y, z = result
        if status == s.OPTIMAL:
            self._save_values(x, self.variables(), var_offsets)
            self._save_dual_values(y, constr_map[s.EQ], EqConstraint)
            self._save_dual_values(z, constr_map[s.LEQ], LeqConstraint)
            self._value = value
        else:
            self._handle_failure(status)
        self._status = status
        return self.value

    def _ecos_problem_data(self, objective, constr_map, dims,
                           var_offsets, x_length):
        """Returns the problem data for the call to ECOS.

        Parameters
        ----------
            objective: Expression
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
        Returns
        -------
        tuple
            ((c, G, h, dims, A, b), offset)
        """
        c, obj_offset = self._get_obj(objective, var_offsets, x_length,
                                      self._DENSE_INTF,
                                      self._DENSE_INTF)
        # Convert obj_offset to a scalar.
        obj_offset = self._DENSE_INTF.scalar_value(obj_offset)

        A, b = self._constr_matrix(constr_map[s.EQ], var_offsets, x_length,
                                   self._SPARSE_INTF, self._DENSE_INTF)
        G, h = self._constr_matrix(constr_map[s.LEQ], var_offsets, x_length,
                                   self._SPARSE_INTF, self._DENSE_INTF)
        # Convert c,h,b to 1D arrays.
        c, h, b = map(intf.from_2D_to_1D, [c.T, h, b])
        # Return the arguments that would be passed to ECOS.
        return ((c, G, h, dims, A, b), obj_offset)

    def _ecos_solve(self, objective, constr_map, dims,
                    var_offsets, x_length,
                    verbose, opts):
        """Calls the ECOS solver and returns the result.

        Parameters
        ----------
            objective: Expression
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
            verbose: bool
                Should the solver show output?
            opts: dict
                List of user-specific options for ECOS
        Returns
        -------
        tuple
            (status, optimal objective, optimal x,
             optimal equality constraint dual,
             optimal inequality constraint dual)

        """
        prob_data = self._ecos_problem_data(objective, constr_map, dims,
                                            var_offsets, x_length)
        obj_offset = prob_data[1]
        results = ecos.solve(*prob_data[0], verbose=verbose)
        status = s.SOLVER_STATUS[s.ECOS][results['info']['exitFlag']]
        if status == s.OPTIMAL:
            primal_val = results['info']['pcost']
            value = self.objective._primal_to_result(
                          primal_val - obj_offset)
            return (status, value,
                    results['x'], results['y'], results['z'])
        else:
            return (status, None, None, None, None)

    def _cvxopt_problem_data(self, objective, constr_map, dims,
                             var_offsets, x_length):
        """Returns the problem data for the call to CVXOPT.

        Assumes no exponential cone constraints.

        Parameters
        ----------
            objective: Expression
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
        Returns
        -------
        tuple
            ((c, G, h, dims, A, b), offset)
        """
        c, obj_offset = self._get_obj(objective, var_offsets, x_length,
                                      self._CVXOPT_DENSE_INTF,
                                      self._CVXOPT_DENSE_INTF)
        # Convert obj_offset to a scalar.
        obj_offset = self._CVXOPT_DENSE_INTF.scalar_value(obj_offset)

        A, b = self._constr_matrix(constr_map[s.EQ], var_offsets, x_length,
                                   self._CVXOPT_SPARSE_INTF,
                                   self._CVXOPT_DENSE_INTF)
        G, h = self._constr_matrix(constr_map[s.LEQ], var_offsets, x_length,
                                   self._CVXOPT_SPARSE_INTF,
                                   self._CVXOPT_DENSE_INTF)
        # Return the arguments that would be passed to CVXOPT.
        return ((c.T, G, h, dims, A, b), obj_offset)


    def _cvxopt_solve(self, objective, constr_map, dims,
                      var_offsets, x_length,
                      verbose, opts):
        """Calls the CVXOPT conelp or cpl solver and returns the result.

        Parameters
        ----------
            objective: Expression
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            sorted_vars: list
                An ordered list of the problem variables.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
            verbose: bool
                Should the solver show output?
            opts: dict
                List of user-specific options for CVXOPT;
                will be inserted into cvxopt.solvers.options.

        Returns
        -------
        tuple
            (status, optimal objective, optimal x,
             optimal equality constraint dual,
             optimal inequality constraint dual)

        """
        prob_data = self._cvxopt_problem_data(objective, constr_map, dims,
                                              var_offsets, x_length)
        c, G, h, dims, A, b = prob_data[0]
        obj_offset = prob_data[1]
        # Save original cvxopt solver options.
        old_options = cvxopt.solvers.options
        # Silence cvxopt if verbose is False.
        cvxopt.solvers.options['show_progress'] = verbose
        # Always do one step of iterative refinement after solving KKT system.
        cvxopt.solvers.options['refinement'] = 1

        # Apply any user-specific options
        for key, value in opts.items():
            cvxopt.solvers.options[key] = value

        # Target cvxopt clp if nonlinear constraints exist
        if constr_map[s.EXP]:
            # Get the nonlinear constraints.
            F = self._merge_nonlin(constr_map[s.EXP], var_offsets,
                                   x_length)
            # Get custom kktsolver.
            kktsolver = get_kktsolver(G, dims, A, F)
            results = cvxopt.solvers.cpl(c, F, G, h, dims, A, b,
                                         kktsolver=kktsolver)
        else:
            # Get custom kktsolver.
            kktsolver = get_kktsolver(G, dims, A)
            results = cvxopt.solvers.conelp(c, G, h, dims, A, b,
                                            kktsolver=kktsolver)
        # Restore original cvxopt solver options.
        cvxopt.solvers.options = old_options
        status = s.SOLVER_STATUS[s.CVXOPT][results['status']]
        if status == s.OPTIMAL:
            primal_val = results['primal objective']
            value = self.objective._primal_to_result(
                          primal_val - obj_offset)
            if constr_map[s.EXP]:
                ineq_dual = results['zl']
            else:
                ineq_dual = results['z']
            return (status, value, results['x'], results['y'], ineq_dual)
        else:
            return (status, None, None, None, None)

    def _scs_problem_data(self, objective, constr_map, dims,
                          var_offsets, x_length):
        """Returns the problem data for the call to SCS.

        Parameters
        ----------
            objective: Expression
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
        Returns
        -------
        tuple
            ((data, dims), offset)
        """
        c, obj_offset = self._get_obj(objective, var_offsets, x_length,
                                      self._DENSE_INTF,
                                      self._DENSE_INTF)
        # Convert obj_offset to a scalar.
        obj_offset = self._DENSE_INTF.scalar_value(obj_offset)

        A, b = self._constr_matrix(constr_map[s.EQ] + constr_map[s.LEQ],
                                   var_offsets, x_length,
                                   self._SPARSE_INTF, self._DENSE_INTF)
        # Convert c, b to 1D arrays.
        c, b = map(intf.from_2D_to_1D, [c.T, b])
        data = {"c": c}
        data["A"] = A
        data["b"] = b
        return ((data, dims), obj_offset)

    def _scs_solve(self, objective, constr_map, dims,
                   var_offsets, x_length,
                   verbose, opts):
        """Calls the SCS solver and returns the result.

        Parameters
        ----------
            objective: LinExpr
                The canonicalized objective.
            constr_map: dict
                A dict of the canonicalized constraints.
            dims: dict
                A dict with information about the types of constraints.
            var_offsets: dict
                A dict mapping variable id to offset in the stacked variable x.
            x_length: int
                The height of x.
            verbose: bool
                Should the solver show output?
            opts: dict
                A dict of the solver parameters passed to scs

        Returns
        -------
        tuple
            (status, optimal objective, optimal x,
             optimal equality constraint dual,
             optimal inequality constraint dual)
        """
        prob_data = self._scs_problem_data(objective, constr_map, dims,
                                           var_offsets, x_length)
        obj_offset = prob_data[1]
        # Set the options to be VERBOSE plus any user-specific options.
        opts = dict({ "VERBOSE": verbose }.items() + opts.items())
        use_indirect = opts["USE_INDIRECT"] if "USE_INDIRECT" in opts else False
        results = scs.solve(*prob_data[0], opts=opts, USE_INDIRECT = use_indirect)
        status = s.SOLVER_STATUS[s.SCS][results["info"]["status"]]
        if status == s.OPTIMAL:
            primal_val = results["info"]["pobj"]
            value = self.objective._primal_to_result(primal_val - obj_offset)
            eq_dual = results["y"][0:dims["f"]]
            ineq_dual = results["y"][dims["f"]:]
            return (status, value, results["x"], eq_dual, ineq_dual)
        else:
            return (status, None, None, None, None)

    def _handle_failure(self, status):
        """Updates value fields based on the cause of solver failure.

        Parameters
        ----------
            status: str
                The status of the solver.
        """
        # Set all primal and dual variable values to None.
        for var_ in self.variables():
            var_.save_value(None)
        for constr in self.constraints:
            constr.save_value(None)
        # Set the problem value.
        if status == s.INFEASIBLE:
            self._value = self.objective._primal_to_result(np.inf)
        elif status == s.UNBOUNDED:
            self._value = self.objective._primal_to_result(-np.inf)
        else: # Solver error
            self._value = None

    def _get_var_offsets(self, objective, constraints):
        """Maps each variable to a horizontal offset.

        Parameters
        ----------
        objective : Expression
            The canonicalized objective.
        constraints : list
            The canonicalized constraints.

        Returns
        -------
        tuple
            (map of variable to offset, length of variable vector)
        """
        vars_ = lu.get_expr_vars(objective)
        for constr in constraints:
            vars_ += lu.get_expr_vars(constr.expr)
        var_offsets = OrderedDict()
        var_sizes = {}
        # Ensure the variables are always in the same
        # order for the same problem.
        var_names = list(set(vars_))
        var_names.sort(key=lambda (var_id, var_size): var_id)
        # Map var ids to offsets.
        vert_offset = 0
        for var_id, var_size in var_names:
            var_sizes[var_id] = var_size
            var_offsets[var_id] = vert_offset
            vert_offset += var_size[0]*var_size[1]

        return (var_offsets, var_sizes, vert_offset)

    def _save_dual_values(self, result_vec, constraints, constr_type):
        """Saves the values of the dual variables.

        Parameters
        ----------
        results_vec : array_like
            A vector containing the dual variable values.
        constraints : list
            A list of the LinEqConstr/LinLeqConstr in the problem.
        constr_type : type
            EqConstr or LeqConstr
        """
        constr_offsets = {}
        offset = 0
        for constr in constraints:
            constr_offsets[constr.constr_id] = offset
            offset += constr.size[0]*constr.size[1]
        active_constraints = []
        for constr in self.constraints:
            if type(constr) == constr_type:
                active_constraints.append(constr)
        self._save_values(result_vec, active_constraints, constr_offsets)

    def _save_values(self, result_vec, objects, offset_map):
        """Saves the values of the optimal primal/dual variables.

        Parameters
        ----------
        results_vec : array_like
            A vector containing the variable values.
        objects : list
            The variables or constraints where the values will be stored.
        offset_map : dict
            A map of object id to offset in the results vector.
        """
        if len(result_vec) > 0:
            # Cast to desired matrix type.
            result_vec = self._DENSE_INTF.const_to_matrix(result_vec)
        for obj in objects:
            rows, cols = obj.size
            if obj.id in offset_map:
                offset = offset_map[obj.id]
                # Handle scalars
                if (rows, cols) == (1,1):
                    value = intf.index(result_vec, (offset, 0))
                else:
                    value = self._DENSE_INTF.zeros(rows, cols)
                    self._DENSE_INTF.block_add(value,
                        result_vec[offset:offset + rows*cols],
                        0, 0, rows, cols)
                offset += rows*cols
            else: # The variable was multiplied by zero.
                value = self._DENSE_INTF.zeros(rows, cols)
            obj.save_value(value)

    def _get_obj(self, objective, var_offsets, x_length,
                 matrix_intf, vec_intf):
        """Wraps _constr_matrix so it can be called for the objective.
        """
        dummy_constr = lu.create_eq(objective)
        return self._constr_matrix([dummy_constr], var_offsets, x_length,
                                   matrix_intf, vec_intf)

    def _constr_matrix(self, constraints, var_offsets, x_length,
                       matrix_intf, vec_intf):
        """Returns a matrix and vector representing a list of constraints.

        In the matrix, each constraint is given a block of rows.
        Each variable coefficient is inserted as a block with upper
        left corner at matrix[variable offset, constraint offset].
        The constant term in the constraint is added to the vector.

        Parameters
        ----------
        constraints : list
            A list of constraints.
        var_offsets : dict
            A dict of variable id to horizontal offset.
        x_length : int
            The length of the x vector.
        matrix_intf : interface
            The matrix interface to use for creating the constraints matrix.
        vec_intf : interface
            The matrix interface to use for creating the constant vector.

        Returns
        -------
        tuple
            A (matrix, vector) tuple.
        """

        rows = sum([c.size[0] * c.size[1] for c in constraints])
        cols = x_length
        V, I, J = [], [], []
        const_vec = vec_intf.zeros(rows, 1)
        vert_offset = 0
        for constr in constraints:
            coeffs = op2mat.get_coefficients(constr.expr)
            for id_, size, block in coeffs:
                vert_start = vert_offset
                vert_end = vert_start + constr.size[0]*constr.size[1]
                if id_ is lo.CONSTANT_ID:
                    # Flatten the block.
                    block = self._DENSE_INTF.const_to_matrix(block)
                    block_size = intf.size(block)
                    block = self._DENSE_INTF.reshape(
                        block,
                        (block_size[0]*block_size[1], 1)
                    )
                    const_vec[vert_start:vert_end, :] += block
                else:
                    horiz_offset = var_offsets[id_]
                    if intf.is_scalar(block):
                        block = intf.scalar_value(block)
                        V.append(block)
                        I.append(vert_start)
                        J.append(horiz_offset)
                    else:
                        # Block is a numpy matrix or
                        # scipy CSC sparse matrix.
                        if not intf.is_sparse(block):
                            block = self._SPARSE_INTF.const_to_matrix(block)
                        block = block.tocoo()
                        V.extend(block.data)
                        I.extend(block.row + vert_start)
                        J.extend(block.col + horiz_offset)
            vert_offset += constr.size[0]*constr.size[1]

        # Create the constraints matrix.
        if len(V) > 0:
            matrix = sp.coo_matrix((V, (I, J)), (rows, cols))
            # Convert the constraints matrix to the correct type.
            matrix = matrix_intf.const_to_matrix(matrix, convert_scalars=True)
        else: # Empty matrix.
            matrix = matrix_intf.zeros(rows, cols)
        return (matrix, -const_vec)

    def _merge_nonlin(self, nl_constr, var_offsets, x_length):
        """ TODO: ensure that this works with numpy data structs...
        """
        rows = sum([constr.size[0] * constr.size[1] for constr in nl_constr])
        cols = x_length

        big_x = self._CVXOPT_DENSE_INTF.zeros(cols, 1)
        for constr in nl_constr:
            constr.place_x0(big_x, var_offsets, self._CVXOPT_DENSE_INTF)

        def F(x=None, z=None):
            if x is None:
                return rows, big_x
            big_f = self._CVXOPT_DENSE_INTF.zeros(rows, 1)
            big_Df = self._CVXOPT_SPARSE_INTF.zeros(rows, cols)
            if z:
                big_H = self._CVXOPT_SPARSE_INTF.zeros(cols, cols)

            offset = 0
            for constr in nl_constr:
                constr_entries = constr.size[0]*constr.size[1]
                local_x = constr.extract_variables(x, var_offsets,
                                                   self._CVXOPT_DENSE_INTF)
                if z:
                    f, Df, H = constr.f(local_x,
                                        z[offset:offset + constr_entries])
                else:
                    result = constr.f(local_x)
                    if result:
                        f, Df = result
                    else:
                        return None
                big_f[offset:offset + constr_entries] = f
                constr.place_Df(big_Df, Df, var_offsets,
                                offset, self._CVXOPT_SPARSE_INTF)
                if z:
                    constr.place_H(big_H, H, var_offsets,
                                   self._CVXOPT_SPARSE_INTF)
                offset += constr_entries

            if z is None:
                return big_f, big_Df
            return big_f, big_Df, big_H
        return F

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "Problem(%s, %s)" % (repr(self.objective),
                                    repr(self.constraints))

########NEW FILE########
__FILENAME__ = settings
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Constants for operators.
PLUS = "+"
MINUS = "-"
MUL = "*"

# Prefix for default named variables.
VAR_PREFIX = "var"
# Prefix for default named parameters.
PARAM_PREFIX = "param"

# Used to trick Numpy so cvxpy can overload ==.
NP_EQUAL_STR = "equal"

# Constraint types
EQ_CONSTR = "=="
INEQ_CONSTR = "<="

# Solver Constants
OPTIMAL = "optimal"
INFEASIBLE = "infeasible"
UNBOUNDED = "unbounded"
SOLVER_ERROR = "solver_error"

# Map of solver status to cvxpy status.
CVXOPT = "CVXOPT"
CVXOPT_STATUS = {'optimal': OPTIMAL,
                 'primal infeasible': INFEASIBLE,
                 'dual infeasible': UNBOUNDED,
                 'unknown': SOLVER_ERROR}
ECOS = "ECOS"
ECOS_STATUS = {0: OPTIMAL,
               1: INFEASIBLE,
               2: UNBOUNDED,
               3: SOLVER_ERROR,
               10: OPTIMAL,
               -1: SOLVER_ERROR,
               -2: SOLVER_ERROR,
               -3: SOLVER_ERROR,
               -7: SOLVER_ERROR}

SCS = "SCS"
SCS_STATUS = {"Solved": OPTIMAL,
              "Solved/Inaccurate": OPTIMAL,
              "Unbounded": UNBOUNDED,
              "Unbounded/Inaccurate": SOLVER_ERROR,
              "Infeasible": INFEASIBLE,
              "Infeasible/Inaccurate": SOLVER_ERROR,
              "Failure": SOLVER_ERROR,
              "Indeterminate": SOLVER_ERROR}

SOLVER_STATUS = {CVXOPT: CVXOPT_STATUS,
                 ECOS: ECOS_STATUS,
                 SCS: SCS_STATUS}

# Solver capabilities.
SDP_CAPABLE = [CVXOPT, SCS]
EXP_CAPABLE = [CVXOPT, SCS]
SOCP_CAPABLE = [ECOS, CVXOPT, SCS]

# Map of constraint types.
EQ, LEQ, SOC, SOC_EW, SDP, EXP = range(6)

########NEW FILE########
__FILENAME__ = base_test
# Base class for unit tests.
import unittest
import numpy as np

class BaseTest(unittest.TestCase):
    # AssertAlmostEqual for lists.
    def assertItemsAlmostEqual(self, a, b, places=4):
        a = self.mat_to_list(a)
        b = self.mat_to_list(b)
        for i in range(len(a)):
            self.assertAlmostEqual(a[i], b[i], places)

    # Overriden method to assume lower accuracy.
    def assertAlmostEqual(self, a, b, places=5):
        super(BaseTest, self).assertAlmostEqual(a,b,places=places)

    def mat_to_list(self, mat):
    	"""Convert a numpy matrix to a list.
    	"""
    	if isinstance(mat, (np.matrix, np.ndarray)):
    		return np.asarray(mat).flatten('F').tolist()
    	else:
    		return mat
########NEW FILE########
__FILENAME__ = test_atoms
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms import *
from cvxpy.expressions.variables import Variable
from cvxpy.expressions.constants import Parameter
import cvxpy.utilities as u
import cvxpy.interface.matrix_utilities as intf
import numpy as np
import unittest

class TestAtoms(unittest.TestCase):
    """ Unit tests for the atoms module. """
    def setUp(self):
        self.a = Variable(name='a')

        self.x = Variable(2, name='x')
        self.y = Variable(2, name='y')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # Test the norm wrapper.
    def test_norm(self):
        with self.assertRaises(Exception) as cm:
            norm(self.C, 3)
        self.assertEqual(str(cm.exception),
            "Invalid value 3 for p.")

    # Test the normInf class.
    def test_normInf(self):
        exp = self.x+self.y
        atom = normInf(exp)
        # self.assertEquals(atom.name(), "normInf(x + y)")
        self.assertEquals(atom.size, (1,1))
        self.assertEquals(atom.curvature, u.Curvature.CONVEX_KEY)
        assert atom.is_convex()
        assert (-atom).is_concave()
        self.assertEquals(normInf(atom).curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(normInf(-atom).curvature, u.Curvature.CONVEX_KEY)

    # Test the norm1 class.
    def test_norm1(self):
        exp = self.x+self.y
        atom = norm1(exp)
        # self.assertEquals(atom.name(), "norm1(x + y)")
        self.assertEquals(atom.size, (1,1))
        self.assertEquals(atom.curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(norm1(atom).curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(norm1(-atom).curvature, u.Curvature.CONVEX_KEY)

    # Test the norm2 class.
    def test_norm2(self):
        exp = self.x+self.y
        atom = norm2(exp)
        # self.assertEquals(atom.name(), "norm2(x + y)")
        self.assertEquals(atom.size, (1,1))
        self.assertEquals(atom.curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(norm2(atom).curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(norm2(-atom).curvature, u.Curvature.CONVEX_KEY)

    def test_quad_over_lin(self):
        # Test quad_over_lin DCP.
        atom = quad_over_lin(square(self.x), self.a)
        self.assertEquals(atom.curvature, u.Curvature.CONVEX_KEY)
        atom = quad_over_lin(-square(self.x), self.a)
        self.assertEquals(atom.curvature, u.Curvature.CONVEX_KEY)
        atom = quad_over_lin(sqrt(self.x), self.a)
        self.assertEquals(atom.curvature, u.Curvature.UNKNOWN_KEY)
        assert not atom.is_dcp()

        # Test quad_over_lin size validation.
        with self.assertRaises(Exception) as cm:
            quad_over_lin(self.x, self.x)
        self.assertEqual(str(cm.exception),
            "The second argument to quad_over_lin must be a scalar")

    def test_elemwise_arg_count(self):
        """Test arg count for max and min variants.
        """
        with self.assertRaises(Exception) as cm:
            max_elemwise(1)
        self.assertEqual(str(cm.exception),
            "__init__() takes at least 3 arguments (2 given)")

        with self.assertRaises(Exception) as cm:
            min_elemwise(1)
        self.assertEqual(str(cm.exception),
            "__init__() takes at least 3 arguments (2 given)")

    def test_max_entries_sign(self):
        """Test sign for max_entries.
        """
        # One arg.
        self.assertEquals(max_entries(1).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(max_entries(-2).sign, u.Sign.NEGATIVE_KEY)
        self.assertEquals(max_entries(Variable()).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(max_entries(0).sign, u.Sign.ZERO_KEY)

    def test_min_entries_sign(self):
        """Test sign for min_entries.
        """
        # One arg.
        self.assertEquals(min_entries(1).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(min_entries(-2).sign, u.Sign.NEGATIVE_KEY)
        self.assertEquals(min_entries(Variable()).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(min_entries(0).sign, u.Sign.ZERO_KEY)

    # Test sign logic for max_elemwise.
    def test_max_elemwise_sign(self):
        # Two args.
        self.assertEquals(max_elemwise(1, 2).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(max_elemwise(1, Variable()).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(max_elemwise(1, -2).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(max_elemwise(1, 0).sign, u.Sign.POSITIVE_KEY)

        self.assertEquals(max_elemwise(Variable(), 0).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(max_elemwise(Variable(), Variable()).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(max_elemwise(Variable(), -2).sign, u.Sign.UNKNOWN_KEY)

        self.assertEquals(max_elemwise(0, 0).sign, u.Sign.ZERO_KEY)
        self.assertEquals(max_elemwise(0, -2).sign, u.Sign.ZERO_KEY)

        self.assertEquals(max_elemwise(-3, -2).sign, u.Sign.NEGATIVE_KEY)

        # Many args.
        self.assertEquals(max_elemwise(-2, Variable(), 0, -1, Variable(), 1).sign,
                          u.Sign.POSITIVE_KEY)

    # Test sign logic for min_elemwise.
    def test_min_elemwise_sign(self):
        # Two args.
        self.assertEquals(min_elemwise(1, 2).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(min_elemwise(1, Variable()).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(min_elemwise(1, -2).sign, u.Sign.NEGATIVE_KEY)
        self.assertEquals(min_elemwise(1, 0).sign, u.Sign.ZERO_KEY)

        self.assertEquals(min_elemwise(Variable(), 0).sign, u.Sign.NEGATIVE_KEY)
        self.assertEquals(min_elemwise(Variable(), Variable()).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(min_elemwise(Variable(), -2).sign, u.Sign.NEGATIVE_KEY)

        self.assertEquals(min_elemwise(0, 0).sign, u.Sign.ZERO_KEY)
        self.assertEquals(min_elemwise(0, -2).sign, u.Sign.NEGATIVE_KEY)

        self.assertEquals(min_elemwise(-3, -2).sign, u.Sign.NEGATIVE_KEY)

        # Many args.
        self.assertEquals(min_elemwise(-2, Variable(), 0, -1, Variable(), 1).sign,
                          u.Sign.NEGATIVE_KEY)

    def test_sum_entries(self):
        """Test the sum_entries atom.
        """
        self.assertEquals(sum_entries(1).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(sum_entries([1, -1]).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(sum_entries([1, -1]).curvature, u.Curvature.CONSTANT_KEY)
        self.assertEquals(sum_entries(Variable(2)).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(sum_entries(Variable(2)).size, (1, 1))
        self.assertEquals(sum_entries(Variable(2)).curvature, u.Curvature.AFFINE_KEY)
        # Mixed curvature.
        mat = np.mat("1 -1")
        self.assertEquals(sum_entries(mat*square(Variable(2))).curvature, u.Curvature.UNKNOWN_KEY)


    def test_mul_elemwise(self):
        """Test the mul_elemwise atom.
        """
        self.assertEquals(mul_elemwise([1, -1], self.x).sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(mul_elemwise([1, -1], self.x).curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(mul_elemwise([1, -1], self.x).size, (2, 1))
        pos_param = Parameter(2, sign="positive")
        neg_param = Parameter(2, sign="negative")
        self.assertEquals(mul_elemwise(pos_param, pos_param).sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(mul_elemwise(pos_param, neg_param).sign, u.Sign.NEGATIVE_KEY)
        self.assertEquals(mul_elemwise(neg_param, neg_param).sign, u.Sign.POSITIVE_KEY)

        self.assertEquals(mul_elemwise(neg_param, square(self.x)).curvature, u.Curvature.CONCAVE_KEY)

        # Test promotion.
        self.assertEquals(mul_elemwise([1, -1], 1).size, (2, 1))
        self.assertEquals(mul_elemwise(1, self.C).size, self.C.size)

        with self.assertRaises(Exception) as cm:
            mul_elemwise(self.x, [1, -1])
        self.assertEqual(str(cm.exception),
            "The first argument to mul_elemwise must be constant.")

    # Test the vstack class.
    def test_vstack(self):
        atom = vstack(self.x, self.y, self.x)
        self.assertEquals(atom.name(), "vstack(x, y, x)")
        self.assertEquals(atom.size, (6,1))

        atom = vstack(self.A, self.C, self.B)
        self.assertEquals(atom.name(), "vstack(A, C, B)")
        self.assertEquals(atom.size, (7,2))

        entries = []
        for i in range(self.x.size[0]):
            for j in range(self.x.size[1]):
                entries.append(self.x[i, j])
        atom = vstack(*entries)
        # self.assertEqual(atom[1,0].name(), "vstack(x[0,0], x[1,0])[1,0]")

        with self.assertRaises(Exception) as cm:
            vstack(self.C, 1)
        self.assertEqual(str(cm.exception),
            "All arguments to vstack must have the same number of columns.")

        with self.assertRaises(Exception) as cm:
            vstack()
        self.assertEqual(str(cm.exception),
            "No arguments given to vstack.")

    def test_reshape(self):
        """Test the reshape class.
        """
        expr = reshape(self.A, 4, 1)
        self.assertEquals(expr.sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(expr.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(expr.size, (4, 1))

        expr = reshape(expr, 2, 2)
        self.assertEquals(expr.size, (2, 2))

        expr = reshape(square(self.x), 1, 2)
        self.assertEquals(expr.sign, u.Sign.POSITIVE_KEY)
        self.assertEquals(expr.curvature, u.Curvature.CONVEX_KEY)
        self.assertEquals(expr.size, (1, 2))

        with self.assertRaises(Exception) as cm:
            reshape(self.C, 5, 4)
        self.assertEqual(str(cm.exception),
            "Invalid reshape dimensions (5, 4).")

########NEW FILE########
__FILENAME__ = test_constant_atoms
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Tests atoms by calling them with a constant value.
from cvxpy.settings import SCS, ECOS, CVXOPT, OPTIMAL
from cvxpy.atoms import *
from cvxpy.atoms.affine.binary_operators import MulExpression
from cvxpy.problems.objective import *
from cvxpy.problems.problem import Problem
from cvxpy.expressions.variables import Variable
from cvxpy.expressions.constants import Constant, Parameter
from cvxpy.utilities.ordered_set import OrderedSet
import cvxopt
import math
from nose.tools import assert_raises

SOLVER_TO_TOL = {SCS: 1e-1,
                 ECOS: 1e-4,
                 CVXOPT: 1e-4}

v = cvxopt.matrix([-1,2,-2], tc='d')

# Atom, solver pairs known to fail.
KNOWN_SOLVER_ERRORS = [(lambda_min, SCS),
                       (lambda_max, SCS),
]

atoms = [
    ([
        (abs([[-5,2],[-3,1]]), Constant([[5,2],[3,1]])),
        (exp([[1, 0],[2, -1]]), Constant([[math.e, 1],[math.e**2, 1.0/math.e]])),
        (huber([[0.5, -1.5],[4, 0]]), Constant([[0.25, 2],[7, 0]])),
        (huber([[0.5, -1.5],[4, 0]], 2.5), Constant([[0.25, 2.25],[13.75, 0]])),
        (inv_pos([[1,2],[3,4]]), Constant([[1,1.0/2],[1.0/3,1.0/4]])),
        (kl_div(math.e, 1), Constant([1])),
        (kl_div(math.e, math.e), Constant([0])),
        (lambda_max([[2,0],[0,1]]), Constant([2])),
        (lambda_max([[5,7],[7,-3]]), Constant([9.06225775])),
        (log_sum_exp([[5, 7], [0, -3]]), Constant([7.1277708268])),
        (max_elemwise([-5,2],[-3,1],0,[-1,2]), Constant([0,2])),
        (max_elemwise([[-5,2],[-3,1]],0,[[5,4],[-1,2]]), Constant([[5,4],[0,2]])),
        (max_entries([[-5,2],[-3,1]]), Constant([2])),
        (max_entries([-5,-10]), Constant([-5])),
        #(norm(v), 3),
        (norm(v, 2), Constant([3])),
        (norm([[-1, 2],[3, -4]], "fro"), Constant([5.47722557])),
        (norm(v,1), Constant([5])),
        (norm([[-1, 2], [3, -4]],1), Constant([10])),
        (norm(v,"inf"), Constant([2])),
        (norm([[-1, 2], [3, -4]],"inf"), Constant([4])),
        (norm([[2,0],[0,1]],"nuc"), Constant([3])),
        (norm([[3,4,5],[6,7,8],[9,10,11]],"nuc"), Constant([23.1733])),
        (pos(8), Constant([8])),
        (pos([-3,2]), Constant([0,2])),
        (neg([-3,3]), Constant([3,0])),
        #(pow_rat(4,1,1), 4),
        #(pow_rat(2,2,1), 4),
        #(pow_rat(4,2,2), 4),
        #(pow_rat(2,3,1), 8),
        #(pow_rat(4,3,2), 8),
        #(pow_rat(4,3,3), 4),
        #(pow_rat(2,4,1), 16),
        #(pow_rat(4,4,2), 16),
        #(pow_rat(8,4,3), 16),
        #(pow_rat(8,4,4), 8),
        (quad_over_lin([[-1,2,-2], [-1,2,-2]], 2), Constant([2*4.5])),
        (quad_over_lin(v, 2), Constant([4.5])),
        #(square_over_lin(2,4), 1),
        (norm([[2,0],[0,1]], 2), Constant([2])),
        (norm([[3,4,5],[6,7,8],[9,10,11]], 2), Constant([22.3686])),
        (square([[-5,2],[-3,1]]), Constant([[25,4],[9,1]])),
        (sum_squares([[-1, 2],[3, -4]]), Constant([30])),
    ], Minimize),
    ([
        (entr([[1, math.e],[math.e**2, 1.0/math.e]]),
         Constant([[0, -math.e], [-2*math.e**2, 1.0/math.e]])),
        #(entr(0), Constant([0])),
        (log_det([[20, 8, 5, 2],
                  [8, 16, 2, 4],
                  [5, 2, 5, 2],
                  [2, 4, 2, 4]]), Constant([7.7424])),
        (geo_mean(4,1), Constant([2])),
        (geo_mean(2,2), Constant([2])),
        (lambda_min([[2,0],[0,1]]), Constant([1])),
        (lambda_min([[5,7],[7,-3]]), Constant([-7.06225775])),
        (log([[1, math.e],[math.e**2, 1.0/math.e]]), Constant([[0, 1],[2, -1]])),
        (min_elemwise([-5,2],[-3,1],0,[1,2]), Constant([-5,0])),
        (min_elemwise([[-5,2],[-3,-1]],0,[[5,4],[-1,2]]), Constant([[-5,0],[-3,-1]])),
        (min_entries([[-5,2],[-3,1]]), Constant([-5])),
        (min_entries([-5,-10]), Constant([-10])),
        #(pow_rat(4,1,2), 2),
        #(pow_rat(8,1,3), 2),
        #(pow_rat(16,1,4),2),
        #(pow_rat(8,2,3), 4),
        #(pow_rat(4,2,4), 2),
        #(pow_rat(16,3,4),8),
        (sqrt([[2,4],[16,1]]), Constant([[1.414213562373095,2],[4,1]])),
    ], Maximize),
]

def check_solver(prob, solver):
    """Can the solver solve the problem?
    """
    objective, constr_map = prob.canonicalize()
    try:
        prob._validate_solver(constr_map, solver)
        return True
    except Exception, e:
        return False

# Tests numeric version of atoms.
def run_atom(atom, problem, obj_val, solver):
    assert problem.is_dcp()
    print problem.objective
    print problem.constraints
    if check_solver(problem, solver):
        print "solver", solver
        tolerance = SOLVER_TO_TOL[solver]
        result = problem.solve(solver=solver)
        if problem.status is OPTIMAL:
            print result
            print obj_val
            assert( -tolerance <= result - obj_val <= tolerance )
        else:
            assert (type(atom), solver) in KNOWN_SOLVER_ERRORS

def test_atom():
    for atom_list, objective_type in atoms:
        for atom, obj_val in atom_list:
            for row in xrange(atom.size[0]):
                for col in xrange(atom.size[1]):
                    for solver in [ECOS, SCS, CVXOPT]:
                        # Atoms with Constant arguments.
                        yield (run_atom,
                               atom,
                               Problem(objective_type(atom[row,col])),
                               obj_val[row,col].value,
                               solver)
                        # Atoms with Variable arguments.
                        variables = []
                        constraints = []
                        for idx, expr in enumerate(atom.subexpressions):
                            # Special case for MulExpr because
                            # can't multiply two variables.
                            if (idx == 0 and isinstance(atom, MulExpression)):
                                variables.append(expr)
                            else:
                                variables.append( Variable(*expr.size) )
                                constraints.append( variables[-1] == expr)
                        atom_func = atom.__class__
                        objective = objective_type(atom_func(*variables)[row,col])
                        yield (run_atom,
                               atom,
                               Problem(objective, constraints),
                               obj_val[row,col].value,
                               solver)
                        # Atoms with Parameter arguments.
                        parameters = []
                        for expr in atom.subexpressions:
                            parameters.append( Parameter(*expr.size) )
                            parameters[-1].value = expr.value
                        objective = objective_type(atom_func(*parameters)[row,col])
                        yield (run_atom,
                               atom,
                               Problem(objective),
                               obj_val[row,col].value,
                               solver)

########NEW FILE########
__FILENAME__ = test_constraints
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.expressions.variables import Variable
from cvxpy.constraints.second_order import SOC
import unittest

class TestConstraints(unittest.TestCase):
    """ Unit tests for the expression/expression module. """
    def setUp(self):
        self.a = Variable(name='a')
        self.b = Variable(name='b')

        self.x = Variable(2, name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(2, name='z')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # Test the EqConstraint class.
    def test_eq_constraint(self):
        constr = self.x == self.z
        self.assertEqual(constr.name(), "x == z")
        self.assertEqual(constr.size, (2,1))
        # self.assertItemsEqual(constr.variables().keys(), [self.x.id, self.z.id])
        # Test value and dual_value.
        assert constr.dual_value is None
        assert constr.value is None
        self.x.save_value(2)
        self.z.save_value(2)
        assert constr.value
        self.x.save_value(3)
        assert not constr.value

        with self.assertRaises(Exception) as cm:
            (self.x == self.y)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 1) (3, 1)")

    # Test the LeqConstraint class.
    def test_leq_constraint(self):
        constr = self.x <= self.z
        self.assertEqual(constr.name(), "x <= z")
        self.assertEqual(constr.size, (2,1))
        # Test value and dual_value.
        assert constr.dual_value is None
        assert constr.value is None
        self.x.save_value(1)
        self.z.save_value(2)
        assert constr.value
        self.x.save_value(3)
        assert not constr.value
        # self.assertItemsEqual(constr.variables().keys(), [self.x.id, self.z.id])

        with self.assertRaises(Exception) as cm:
            (self.x <= self.y)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 1) (3, 1)")

    # Test the SOC class.
    def test_soc_constraint(self):
        exp = self.x + self.z
        scalar_exp = self.a + self.b
        constr = SOC(scalar_exp, [exp])
        self.assertEqual(constr.size, (3,1))
        self.assertEqual(len(constr.format()), 2)

    # Test the SDC class.
    def test_sdc_constraint(self):
        exp = self.x + self.z
        scalar_exp = self.a + self.b
        constr = SOC(scalar_exp, [exp])
        self.assertEqual(constr.size, (3,1))
        self.assertEqual(len(constr.format()), 2)

########NEW FILE########
__FILENAME__ = test_convolution
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
import cvxpy.settings as s
from cvxpy.lin_ops.tree_mat import mul, tmul, prune_constants
import cvxpy.problems.iterative as iterative
from cvxpy.utilities import Curvature
from cvxpy.utilities import Sign
from base_test import BaseTest
import numpy as np

class TestConvolution(BaseTest):
    """ Unit tests for convolution. """

    def test_1D_conv(self):
        """Test 1D convolution.
        """
        n = 3
        x = Variable(n)
        f = [1, 2, 3]
        g = [0, 1, 0.5]
        f_conv_g = [ 0., 1., 2.5,  4., 1.5]
        expr = conv(f, g)
        assert expr.is_constant()
        self.assertEquals(expr.size, (5, 1))
        self.assertItemsAlmostEqual(expr.value, f_conv_g)

        expr = conv(f, x)
        assert expr.is_affine()
        self.assertEquals(expr.size, (5, 1))
        # Matrix stuffing.
        t = Variable()
        prob = Problem(Minimize(norm(expr, 1)),
            [x == g])
        result = prob.solve()
        self.assertAlmostEqual(result, sum(f_conv_g))
        self.assertItemsAlmostEqual(expr.value, f_conv_g)

        # # Expression trees.
        # prob = Problem(Minimize(norm(expr, 1)))
        # self.prob_mat_vs_mul_funcs(prob)
        # result = prob.solve(solver=SCS, expr_tree=True, verbose=True)
        # self.assertAlmostEqual(result, 0, places=1)

    def prob_mat_vs_mul_funcs(self, prob):
        data, dims = prob.get_problem_data(solver=SCS)
        A = data["A"]
        objective, constr_map, dims, solver = prob.canonicalize(SCS)

        all_ineq = constr_map[s.EQ] + constr_map[s.LEQ]
        var_offsets, var_sizes, x_length = prob._get_var_offsets(objective,
                                                                 all_ineq)
        opts = {}
        constraints = constr_map[s.EQ] + constr_map[s.LEQ]
        constraints = prune_constants(constraints)
        Amul, ATmul = iterative.get_mul_funcs(constraints, dims,
                                              var_offsets, var_sizes,
                                              x_length)
        vec = np.array(range(1, x_length+1))
        # A*vec
        result = np.zeros(A.shape[0])
        Amul(vec, result)
        mul_mat = self.mat_from_func(Amul, A.shape[0], A.shape[1])
        self.assertItemsAlmostEqual(A*vec, result)
        Amul(vec, result)
        self.assertItemsAlmostEqual(2*A*vec, result)
        # A.T*vec
        vec = np.array(range(A.shape[0]))
        result = np.zeros(A.shape[1])
        ATmul(vec, result)
        self.assertItemsAlmostEqual(A.T*vec, result)
        ATmul(vec, result)
        self.assertItemsAlmostEqual(2*A.T*vec, result)

    def mat_from_func(self, func, rows, cols):
        """Convert a multiplier function to a matrix.
        """
        test_vec = np.zeros(cols)
        result = np.zeros(rows)
        matrix = np.zeros((rows, cols))
        for i in range(cols):
            test_vec[i] = 1.0
            func(test_vec, result)
            matrix[:, i] = result
            test_vec *= 0
            result *= 0

        return matrix

########NEW FILE########
__FILENAME__ = test_curvature
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities import Curvature
from cvxpy.utilities import Sign
from nose.tools import assert_equals

class TestCurvature(object):
    """ Unit tests for the expression/curvature class. """
    def test_add(self):
        assert_equals(Curvature.CONSTANT + Curvature.CONVEX, Curvature.CONVEX)
        assert_equals(Curvature.UNKNOWN + Curvature.CONCAVE, Curvature.UNKNOWN)
        assert_equals(Curvature.CONVEX + Curvature.CONCAVE, Curvature.UNKNOWN)
        assert_equals(Curvature.CONVEX + Curvature.CONVEX, Curvature.CONVEX)
        assert_equals(Curvature.AFFINE + Curvature.CONCAVE, Curvature.CONCAVE)

    def test_sub(self):
        assert_equals(Curvature.CONSTANT - Curvature.CONVEX, Curvature.CONCAVE)
        assert_equals(Curvature.UNKNOWN - Curvature.CONCAVE, Curvature.UNKNOWN)
        assert_equals(Curvature.CONVEX - Curvature.CONCAVE, Curvature.CONVEX)
        assert_equals(Curvature.CONVEX - Curvature.CONVEX, Curvature.UNKNOWN)
        assert_equals(Curvature.AFFINE - Curvature.CONCAVE, Curvature.CONVEX)

    def test_sign_mult(self):
        assert_equals(Curvature.sign_mul(Sign.ZERO, Curvature.CONVEX), Curvature.CONSTANT)
        assert_equals(Curvature.sign_mul(Sign.NEGATIVE, Curvature.CONVEX), Curvature.CONCAVE)
        assert_equals(Curvature.sign_mul(Sign.NEGATIVE, Curvature.CONCAVE), Curvature.CONVEX)
        assert_equals(Curvature.sign_mul(Sign.NEGATIVE, Curvature.UNKNOWN), Curvature.UNKNOWN)
        assert_equals(Curvature.sign_mul(Sign.POSITIVE, Curvature.AFFINE), Curvature.AFFINE)
        assert_equals(Curvature.sign_mul(Sign.POSITIVE, Curvature.CONCAVE), Curvature.CONCAVE)
        assert_equals(Curvature.sign_mul(Sign.UNKNOWN, Curvature.CONSTANT), Curvature.CONSTANT)
        assert_equals(Curvature.sign_mul(Sign.UNKNOWN, Curvature.CONCAVE), Curvature.UNKNOWN)

    def test_neg(self):
        assert_equals(-Curvature.CONVEX, Curvature.CONCAVE)
        assert_equals(-Curvature.AFFINE, Curvature.AFFINE)

    # Tests the is_affine, is_convex, and is_concave methods
    def test_is_curvature(self):
        assert Curvature.CONSTANT.is_affine()
        assert Curvature.AFFINE.is_affine()
        assert not Curvature.CONVEX.is_affine()
        assert not Curvature.CONCAVE.is_affine()
        assert not Curvature.UNKNOWN.is_affine()

        assert Curvature.CONSTANT.is_convex()
        assert Curvature.AFFINE.is_convex()
        assert Curvature.CONVEX.is_convex()
        assert not Curvature.CONCAVE.is_convex()
        assert not Curvature.UNKNOWN.is_convex()

        assert Curvature.CONSTANT.is_concave()
        assert Curvature.AFFINE.is_concave()
        assert not Curvature.CONVEX.is_concave()
        assert Curvature.CONCAVE.is_concave()
        assert not Curvature.UNKNOWN.is_concave()
########NEW FILE########
__FILENAME__ = test_examples
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
import cvxpy.interface as intf
import numpy as np
from base_test import BaseTest
import cvxopt
import numbers

class TestExamples(BaseTest):
    """ Unit tests using example problems. """

    # Overriden method to handle lists and lower accuracy.
    def assertAlmostEqual(self, a, b, interface=intf.DEFAULT_INTERFACE):
        try:
            a = list(a)
            b = list(b)
            for i in range(len(a)):
                self.assertAlmostEqual(a[i], b[i])
        except Exception:
            super(TestExamples, self).assertAlmostEqual(a,b,places=4)

    # Find the largest Euclidean ball in the polyhedron.
    def test_chebyshev_center(self):
        # The goal is to find the largest Euclidean ball (i.e. its center and
        # radius) that lies in a polyhedron described by linear inequalites in this
        # fashion: P = {x : a_i'*x <= b_i, i=1,...,m} where x is in R^2

        # Generate the input data
        a1 = np.matrix("2; 1")
        a2 = np.matrix(" 2; -1")
        a3 = np.matrix("-1;  2")
        a4 = np.matrix("-1; -2")
        b = np.ones([4,1])

        # Create and solve the model
        r = Variable(name='r')
        x_c = Variable(2,name='x_c')
        obj = Maximize(r)
        constraints = [ #TODO have atoms compute values for constants.
            a1.T*x_c + np.linalg.norm(a1)*r <= b[0],
            a2.T*x_c + np.linalg.norm(a2)*r <= b[1],
            a3.T*x_c + np.linalg.norm(a3)*r <= b[2],
            a4.T*x_c + np.linalg.norm(a4)*r <= b[3],
        ]

        p = Problem(obj, constraints)
        result = p.solve()
        self.assertAlmostEqual(result, 0.4472)
        self.assertAlmostEqual(r.value, result)
        self.assertItemsAlmostEqual(x_c.value, [0,0])

    # Test issue with numpy scalars.
    def test_numpy_scalars(self):
        n = 6
        eps = 1e-6
        cvxopt.setseed(10)
        P0 = cvxopt.normal(n, n)
        eye = cvxopt.spmatrix(1.0, range(n), range(n))
        P0 = P0.T * P0 + eps * eye

        print P0

        P1 = cvxopt.normal(n, n)
        P1 = P1.T*P1
        P2 = cvxopt.normal(n, n)
        P2 = P2.T*P2
        P3 = cvxopt.normal(n, n)
        P3 = P3.T*P3

        q0 = cvxopt.normal(n, 1)
        q1 = cvxopt.normal(n, 1)
        q2 = cvxopt.normal(n, 1)
        q3 = cvxopt.normal(n, 1)

        r0 = cvxopt.normal(1, 1)
        r1 = cvxopt.normal(1, 1)
        r2 = cvxopt.normal(1, 1)
        r3 = cvxopt.normal(1, 1)

        slack = Variable()
        # Form the problem
        x = Variable(n)
        objective = Minimize( 0.5*quad_form(x,P0) + q0.T*x + r0 + slack)
        constraints = [0.5*quad_form(x,P1) + q1.T*x + r1 <= slack,
                       0.5*quad_form(x,P2) + q2.T*x + r2 <= slack,
                       0.5*quad_form(x,P3) + q3.T*x + r3 <= slack,
        ]

        # We now find the primal result and compare it to the dual result
        # to check if strong duality holds i.e. the duality gap is effectively zero
        p = Problem(objective, constraints)
        primal_result = p.solve()

        # Note that since our data is random, we may need to run this program multiple times to get a feasible primal
        # When feasible, we can print out the following values
        print x.value # solution
        lam1 = constraints[0].dual_value
        lam2 = constraints[1].dual_value
        lam3 = constraints[2].dual_value
        print type(lam1)

        P_lam = P0 + lam1*P1 + lam2*P2 + lam3*P3
        q_lam = q0 + lam1*q1 + lam2*q2 + lam3*q3
        r_lam = r0 + lam1*r1 + lam2*r2 + lam3*r3
        dual_result = -0.5*q_lam.T.dot(P_lam).dot(q_lam) + r_lam
        print dual_result.shape
        self.assertEquals(intf.size(dual_result), (1,1))

    # Tests examples from the README.
    def test_readme_examples(self):
        import cvxopt
        import numpy

        # Problem data.
        m = 30
        n = 20
        A = cvxopt.normal(m,n)
        b = cvxopt.normal(m)

        # Construct the problem.
        x = Variable(n)
        objective = Minimize(sum_entries(square(A*x - b)))
        constraints = [0 <= x, x <= 1]
        p = Problem(objective, constraints)

        # The optimal objective is returned by p.solve().
        result = p.solve()
        # The optimal value for x is stored in x.value.
        print x.value
        # The optimal Lagrange multiplier for a constraint
        # is stored in constraint.dual_value.
        print constraints[0].dual_value

        ####################################################

        # Scalar variable.
        a = Variable()

        # Column vector variable of length 5.
        x = Variable(5)

        # Matrix variable with 4 rows and 7 columns.
        A = Variable(4, 7)

        ####################################################

        # Positive scalar parameter.
        m = Parameter(sign="positive")

        # Column vector parameter with unknown sign (by default).
        c = Parameter(5)

        # Matrix parameter with negative entries.
        G = Parameter(4, 7, sign="negative")

        # Assigns a constant value to G.
        G.value = -numpy.ones((4, 7))

        # Raises an error for assigning a value with invalid sign.
        with self.assertRaises(Exception) as cm:
            G.value = numpy.ones((4,7))
        self.assertEqual(str(cm.exception), "Invalid sign for Parameter value.")

        ####################################################
        a = Variable()
        x = Variable(5)

        # expr is an Expression object after each assignment.
        expr = 2*x
        expr = expr - a
        expr = sum_entries(expr) + norm(x, 2)

        ####################################################

        import numpy as np
        import cvxopt
        from multiprocessing import Pool

        # Problem data.
        n = 10
        m = 5
        A = cvxopt.normal(n,m)
        b = cvxopt.normal(n)
        gamma = Parameter(sign="positive")

        # Construct the problem.
        x = Variable(m)
        objective = Minimize(sum_entries(square(A*x - b)) + gamma*norm(x, 1))
        p = Problem(objective)

        # Assign a value to gamma and find the optimal x.
        def get_x(gamma_value):
            gamma.value = gamma_value
            result = p.solve()
            return x.value

        gammas = np.logspace(-1, 2, num=2)
        # Serial computation.
        x_values = [get_x(value) for value in gammas]

        ####################################################
        n = 10

        mu = cvxopt.normal(1, n)
        sigma = cvxopt.normal(n,n)
        sigma = sigma.T*sigma
        gamma = Parameter(sign="positive")
        gamma.value = 1
        x = Variable(n)

        # Constants:
        # mu is the vector of expected returns.
        # sigma is the covariance matrix.
        # gamma is a Parameter that trades off risk and return.

        # Variables:
        # x is a vector of stock holdings as fractions of total assets.

        expected_return = mu*x
        risk = quad_form(x, sigma)

        objective = Maximize(expected_return - gamma*risk)
        p = Problem(objective, [sum_entries(x) == 1])
        result = p.solve()

        # The optimal expected return.
        print expected_return.value

        # The optimal risk.
        print risk.value

        ###########################################

        N = 50
        M = 40
        n = 10
        data = []
        for i in range(N):
            data += [(1, cvxopt.normal(n, mean=1.0, std=2.0))]
        for i in range(M):
            data += [(-1, cvxopt.normal(n, mean=-1.0, std=2.0))]

        # Construct problem.
        gamma = Parameter(sign="positive")
        gamma.value = 0.1
        # 'a' is a variable constrained to have at most 6 non-zero entries.
        a = Variable(n)#mi.SparseVar(n, nonzeros=6)
        b = Variable()

        slack = [pos(1 - label*(sample.T*a - b)) for (label, sample) in data]
        objective = Minimize(norm(a, 2) + gamma*sum(slack))
        p = Problem(objective)
        # Extensions can attach new solve methods to the CVXPY Problem class.
        #p.solve(method="admm")
        p.solve()

        # Count misclassifications.
        errors = 0
        for label, sample in data:
            if label*(sample.T*a - b).value < 0:
                errors += 1

        print "%s misclassifications" % errors
        print a.value
        print b.value

    def test_log_det(self):
        # Generate data
        x = np.matrix("0.55  0.0;"
                      "0.25  0.35;"
                      "-0.2   0.2;"
                      "-0.25 -0.1;"
                      "-0.0  -0.3;"
                      "0.4  -0.2").T
        (n, m) = x.shape

        # Create and solve the model
        A = Variable(n, n);
        b = Variable(n);
        obj = Maximize( log_det(A) )
        constraints = []
        for i in range(m):
            constraints.append( norm(A*x[:, i] + b) <= 1 )
        p = Problem(obj, constraints)
        result = p.solve()
        self.assertAlmostEqual(result, 1.9746)

    def test_portfolio_problem(self):
        """Test portfolio problem that caused dcp_attr errors.
        """
        import numpy as np
        import scipy.sparse as sp
        np.random.seed(5)
        n = 100#10000
        m = 10#100
        pbar = (np.ones((n, 1)) * .03 +
                np.matrix(np.append(np.random.rand(n - 1, 1), 0)).T * .12)

        F = sp.rand(m, n, density=0.01)
        F.data = np.ones(len(F.data))
        D = sp.eye(n).tocoo()
        D.data = np.random.randn(len(D.data))**2
        Z = np.random.randn(m, 1)
        Z = Z.dot(Z.T)

        x = Variable(n)
        y = x.__rmul__(F)
        mu = 1
        ret = pbar.T * x
        # DCP attr causes error because not all the curvature
        # matrices are reduced to constants when an atom
        # is scalar.
        risk = square(norm(x.__rmul__(D))) + square(Z*y)

    def test_intro(self):
        """Test examples from cvxpy.org introduction.
        """
        import numpy

        # Problem data.
        m = 30
        n = 20
        numpy.random.seed(1)
        A = numpy.random.randn(m, n)
        b = numpy.random.randn(m)

        # Construct the problem.
        x = Variable(n)
        objective = Minimize(sum_squares(A*x - b))
        constraints = [0 <= x, x <= 1]
        prob = Problem(objective, constraints)

        # The optimal objective is returned by p.solve().
        result = prob.solve()
        # The optimal value for x is stored in x.value.
        print x.value
        # The optimal Lagrange multiplier for a constraint
        # is stored in constraint.dual_value.
        print constraints[0].dual_value

        ########################################

        # Create two scalar variables.
        x = Variable()
        y = Variable()

        # Create two constraints.
        constraints = [x + y == 1,
                       x - y >= 1]

        # Form objective.
        obj = Minimize(square(x - y))

        # Form and solve problem.
        prob = Problem(obj, constraints)
        prob.solve()  # Returns the optimal value.
        print "status:", prob.status
        print "optimal value", prob.value
        print "optimal var", x.value, y.value

        ########################################

        import cvxpy as cvx

        # Create two scalar variables.
        x = cvx.Variable()
        y = cvx.Variable()

        # Create two constraints.
        constraints = [x + y == 1,
                       x - y >= 1]

        # Form objective.
        obj = cvx.Minimize(cvx.square(x - y))

        # Form and solve problem.
        prob = cvx.Problem(obj, constraints)
        prob.solve()  # Returns the optimal value.
        print "status:", prob.status
        print "optimal value", prob.value
        print "optimal var", x.value, y.value

        self.assertEqual(prob.status, OPTIMAL)
        self.assertAlmostEqual(prob.value, 1.0)
        self.assertAlmostEqual(x.value, 1.0)
        self.assertAlmostEqual(y.value, 0)

        ########################################

        # Replace the objective.
        prob.objective = Maximize(x + y)
        print "optimal value", prob.solve()

        self.assertAlmostEqual(prob.value, 1.0)

        # Replace the constraint (x + y == 1).
        prob.constraints[0] = (x + y <= 3)
        print "optimal value", prob.solve()

        self.assertAlmostEqual(prob.value, 3.0)

        ########################################

        x = Variable()

        # An infeasible problem.
        prob = Problem(Minimize(x), [x >= 1, x <= 0])
        prob.solve()
        print "status:", prob.status
        print "optimal value", prob.value

        self.assertEquals(prob.status, INFEASIBLE)
        self.assertAlmostEqual(prob.value, np.inf)

        # An unbounded problem.
        prob = Problem(Minimize(x))
        prob.solve()
        print "status:", prob.status
        print "optimal value", prob.value

        self.assertEquals(prob.status, UNBOUNDED)
        self.assertAlmostEqual(prob.value, -np.inf)

        ########################################

        # A scalar variable.
        a = Variable()

        # Column vector variable of length 5.
        x = Variable(5)

        # Matrix variable with 4 rows and 7 columns.
        A = Variable(4, 7)

        ########################################
        import numpy

        # Problem data.
        m = 10
        n = 5
        numpy.random.seed(1)
        A = numpy.random.randn(m, n)
        b = numpy.random.randn(m)

        # Construct the problem.
        x = Variable(n)
        objective = Minimize(sum_entries(square(A*x - b)))
        constraints = [0 <= x, x <= 1]
        prob = Problem(objective, constraints)

        print "Optimal value", prob.solve()
        print "Optimal var"
        print x.value # A numpy matrix.

        self.assertAlmostEqual(prob.value, 4.14133859146)

        ########################################
        # Positive scalar parameter.
        m = Parameter(sign="positive")

        # Column vector parameter with unknown sign (by default).
        c = Parameter(5)

        # Matrix parameter with negative entries.
        G = Parameter(4, 7, sign="negative")

        # Assigns a constant value to G.
        G.value = -numpy.ones((4, 7))
        ########################################

        import numpy

        # Problem data.
        n = 15
        m = 10
        numpy.random.seed(1)
        A = numpy.random.randn(n, m)
        b = numpy.random.randn(n)
        # gamma must be positive due to DCP rules.
        gamma = Parameter(sign="positive")

        # Construct the problem.
        x = Variable(m)
        sum_of_squares = sum_entries(square(A*x - b))
        obj = Minimize(sum_of_squares + gamma*norm(x, 1))
        prob = Problem(obj)

        # Construct a trade-off curve of ||Ax-b||^2 vs. ||x||_1
        sq_penalty = []
        l1_penalty = []
        x_values = []
        gamma_vals = numpy.logspace(-4, 6)
        for val in gamma_vals:
            gamma.value = val
            prob.solve()
            # Use expr.value to get the numerical value of
            # an expression in the problem.
            sq_penalty.append(sum_of_squares.value)
            l1_penalty.append(norm(x, 1).value)
            x_values.append(x.value)

        ########################################
        import numpy

        X = Variable(5, 4)
        A = numpy.ones((3, 5))

        # Use expr.size to get the dimensions.
        print "dimensions of X:", X.size
        print "dimensions of sum_entries(X):", sum_entries(X).size
        print "dimensions of A*X:", (A*X).size

        # ValueError raised for invalid dimensions.
        try:
            A + X
        except ValueError, e:
            print e

    # # Risk return tradeoff curve
    # def test_risk_return_tradeoff(self):
    #     from math import sqrt
    #     from cvxopt import matrix
    #     from cvxopt.blas import dot
    #     from cvxopt.solvers import qp, options
    #     import scipy

    #     n = 4
    #     S = matrix( [[ 4e-2,  6e-3, -4e-3,   0.0 ],
    #                  [ 6e-3,  1e-2,  0.0,    0.0 ],
    #                  [-4e-3,  0.0,   2.5e-3, 0.0 ],
    #                  [ 0.0,   0.0,   0.0,    0.0 ]] )
    #     pbar = matrix([.12, .10, .07, .03])

    #     N = 100
    #     # CVXPY
    #     Sroot = numpy.asmatrix(scipy.linalg.sqrtm(S))
    #     x = cp.Variable(n, name='x')
    #     mu = cp.Parameter(name='mu')
    #     mu.value = 1 # TODO cp.Parameter("positive")
    #     objective = cp.Minimize(-pbar*x + mu*quad_over_lin(Sroot*x,1))
    #     constraints = [sum_entries(x) == 1, x >= 0]
    #     p = cp.Problem(objective, constraints)

    #     mus = [ 10**(5.0*t/N-1.0) for t in range(N) ]
    #     xs = []
    #     for mu_val in mus:
    #         mu.value = mu_val
    #         p.solve()
    #         xs.append(x.value)
    #     returns = [ dot(pbar,x) for x in xs ]
    #     risks = [ sqrt(dot(x, S*x)) for x in xs ]

    #     # QP solver
########NEW FILE########
__FILENAME__ = test_expressions
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms.affine.add_expr import AddExpression
from cvxpy.expressions.expression import *
from cvxpy.expressions.variables import Variable
from cvxpy.expressions.constants import Constant
from cvxpy.expressions.constants import Parameter
import cvxpy.utilities as u
import cvxpy.interface.matrix_utilities as intf
import cvxpy.settings as s
from collections import deque
import unittest
from cvxopt import matrix
import numpy as np

class TestExpressions(unittest.TestCase):
    """ Unit tests for the expression/expression module. """
    def setUp(self):
        self.a = Variable(name='a')

        self.x = Variable(2, name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(2, name='z')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')
        self.intf = intf.DEFAULT_INTERFACE

    # Test the Variable class.
    def test_variable(self):
        x = Variable(2)
        y = Variable(2)
        assert y.name() != x.name()

        x = Variable(2, name='x')
        y = Variable()
        self.assertEqual(x.name(), 'x')
        self.assertEqual(x.size, (2,1))
        self.assertEqual(y.size, (1,1))
        self.assertEqual(x.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(x.canonical_form[0].size, (2,1))
        self.assertEqual(x.canonical_form[1], [])

        # # Scalar variable
        # coeff = self.a.coefficients()
        # self.assertEqual(coeff[self.a.id], [1])

        # # Vector variable.
        # coeffs = x.coefficients()
        # self.assertItemsEqual(coeffs.keys(), [x.id])
        # vec = coeffs[x.id][0]
        # self.assertEqual(vec.shape, (2,2))
        # self.assertEqual(vec[0,0], 1)

        # # Matrix variable.
        # coeffs = self.A.coefficients()
        # self.assertItemsEqual(coeffs.keys(), [self.A.id])
        # self.assertEqual(len(coeffs[self.A.id]), 2)
        # mat = coeffs[self.A.id][1]
        # self.assertEqual(mat.shape, (2,4))
        # self.assertEqual(mat[0,2], 1)

    # Test tranposing variables.
    def test_transpose_variable(self):
        var = self.a.T
        self.assertEquals(var.name(), "a")
        self.assertEquals(var.size, (1,1))

        self.a.save_value(2)
        self.assertEquals(var.value, 2)

        var = self.x.T
        self.assertEquals(var.name(), "x.T")
        self.assertEquals(var.size, (1,2))

        self.x.save_value( matrix([1,2]) )
        self.assertEquals(var.value[0,0], 1)
        self.assertEquals(var.value[0,1], 2)

        var = self.C.T
        self.assertEquals(var.name(), "C.T")
        self.assertEquals(var.size, (2,3))

        # coeffs = var.canonical_form[0].coefficients()
        # mat = coeffs.values()[0][0]
        # self.assertEqual(mat.size, (2,6))
        # self.assertEqual(mat[1,3], 1)

        index = var[1,0]
        self.assertEquals(index.name(), "C.T[1, 0]")
        self.assertEquals(index.size, (1,1))

        var = self.x.T.T
        self.assertEquals(var.name(), "x.T.T")
        self.assertEquals(var.size, (2,1))

    # Test the Constant class.
    def test_constants(self):
        c = Constant(2)
        self.assertEqual(c.name(), str(2))

        c = Constant(2)
        self.assertEqual(c.value, 2)
        self.assertEqual(c.size, (1,1))
        self.assertEqual(c.curvature, u.Curvature.CONSTANT_KEY)
        self.assertEqual(c.sign, u.Sign.POSITIVE_KEY)
        self.assertEqual(Constant(-2).sign, u.Sign.NEGATIVE_KEY)
        self.assertEqual(Constant(0).sign, u.Sign.ZERO_KEY)
        self.assertEqual(c.canonical_form[0].size, (1,1))
        self.assertEqual(c.canonical_form[1], [])

        # coeffs = c.coefficients()
        # self.assertEqual(coeffs.keys(), [s.CONSTANT])
        # self.assertEqual(coeffs[s.CONSTANT], [2])

        # Test the sign.
        c = Constant([[2], [2]])
        self.assertEqual(c.size, (1, 2))
        self.assertEqual(c.sign, u.Sign.UNKNOWN_KEY)

        # Test sign of a complex expression.
        c = Constant([1, 2])
        A = Constant([[1,1],[1,1]])
        exp = c.T*A*c
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual((c.T*c).sign, u.Sign.UNKNOWN_KEY)
        exp = c.T.T
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        exp = c.T*self.A
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)

    # Test the Parameter class.
    def test_parameters(self):
        p = Parameter(name='p')
        self.assertEqual(p.name(), "p")
        self.assertEqual(p.size, (1,1))

        p = Parameter(4, 3, sign="positive")
        with self.assertRaises(Exception) as cm:
            p.value = 1
        self.assertEqual(str(cm.exception), "Invalid dimensions (1,1) for Parameter value.")

        val = -np.ones((4,3))
        val[0,0] = 2

        p = Parameter(4, 3, sign="positive")
        with self.assertRaises(Exception) as cm:
            p.value = val
        self.assertEqual(str(cm.exception), "Invalid sign for Parameter value.")

        p = Parameter(4, 3, sign="negative")
        with self.assertRaises(Exception) as cm:
            p.value = val
        self.assertEqual(str(cm.exception), "Invalid sign for Parameter value.")

        # No error for unknown sign.
        p = Parameter(4, 3)
        p.value = val

    # Test the AddExpresion class.
    def test_add_expression(self):
        # Vectors
        c = Constant([2,2])
        exp = self.x + c
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(exp.canonical_form[0].size, (2,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), self.x.name() + " + " + c.name())
        self.assertEqual(exp.size, (2,1))

        z = Variable(2, name='z')
        exp = exp + z + self.x

        with self.assertRaises(Exception) as cm:
            (self.x + self.y)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 1) (3, 1)")

        # Matrices
        exp = self.A + self.B
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.size, (2,2))

        with self.assertRaises(Exception) as cm:
            (self.A + self.C)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 2) (3, 2)")

        with self.assertRaises(Exception) as cm:
            AddExpression([self.A, self.C])
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 2) (3, 2)")

        # Test that sum is flattened.
        exp = self.x + c + self.x
        self.assertEqual(len(exp.args), 3)

    # Test the SubExpresion class.
    def test_sub_expression(self):
        # Vectors
        c = Constant([2,2])
        exp = self.x - c
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(exp.canonical_form[0].size, (2,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), self.x.name() + " - " + Constant([2,2]).name())
        self.assertEqual(exp.size, (2,1))

        z = Variable(2, name='z')
        exp = exp - z - self.x

        with self.assertRaises(Exception) as cm:
            (self.x - self.y)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 1) (3, 1)")

        # Matrices
        exp = self.A - self.B
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.size, (2,2))

        with self.assertRaises(Exception) as cm:
            (self.A - self.C)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 2) (3, 2)")

    # Test the MulExpresion class.
    def test_mul_expression(self):
        # Vectors
        c = Constant([[2],[2]])
        exp = c*self.x
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual((c[0]*self.x).sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(exp.canonical_form[0].size, (1,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), c.name() + " * " + self.x.name())
        self.assertEqual(exp.size, (1,1))

        with self.assertRaises(Exception) as cm:
            ([2,2,3]*self.x)
        self.assertEqual(str(cm.exception), "Incompatible dimensions (3, 1) (2, 1)")

        # Matrices
        with self.assertRaises(Exception) as cm:
            Constant([[2, 1],[2, 2]]) * self.C
        self.assertEqual(str(cm.exception), "Incompatible dimensions (2, 2) (3, 2)")

        with self.assertRaises(Exception) as cm:
            (self.A * self.B)
        self.assertEqual(str(cm.exception), "Cannot multiply two non-constants.")

        # Constant expressions
        T = Constant([[1,2,3],[3,5,5]])
        exp = (T + T) * self.B
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.size, (3,2))

        # Expression that would break sign multiplication without promotion.
        c = Constant([[2], [2], [-2]])
        exp = [[1], [2]] + c*self.C
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)

        # Scalar constants on the right should be moved left
        # instead of taking the transpose.
        expr = self.C*2
        self.assertEqual(expr.args[0].value, 2)

    # Test the DivExpresion class.
    def test_div_expression(self):
        # Vectors
        exp = self.x/2
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(exp.canonical_form[0].size, (2,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), c.name() + " * " + self.x.name())
        self.assertEqual(exp.size, (2,1))

        with self.assertRaises(Exception) as cm:
            (self.x/[2,2,3])
        print cm.exception
        self.assertEqual(str(cm.exception), "Can only divide by a scalar constant.")

        # Constant expressions.
        c = Constant(2)
        exp = c/(3 - 5)
        self.assertEqual(exp.curvature, u.Curvature.CONSTANT_KEY)
        self.assertEqual(exp.size, (1,1))
        self.assertEqual(exp.sign, u.Sign.NEGATIVE_KEY)

        # Parameters.
        p = Parameter(sign="positive")
        exp = 2/p
        p.value = 2
        self.assertEquals(exp.value, 1)

    # Test the NegExpression class.
    def test_neg_expression(self):
        # Vectors
        exp = -self.x
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        assert exp.is_affine()
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        assert not exp.is_positive()
        self.assertEqual(exp.canonical_form[0].size, (2,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), "-%s" % self.x.name())
        self.assertEqual(exp.size, self.x.size)

        # Matrices
        exp = -self.C
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.size, (3,2))

    # Test promotion of scalar constants.
    def test_scalar_const_promotion(self):
        # Vectors
        exp = self.x + 2
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        assert exp.is_affine()
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        assert not exp.is_negative()
        self.assertEqual(exp.canonical_form[0].size, (2,1))
        self.assertEqual(exp.canonical_form[1], [])
        # self.assertEqual(exp.name(), self.x.name() + " + " + Constant(2).name())
        self.assertEqual(exp.size, (2,1))

        self.assertEqual((4 - self.x).size, (2,1))
        self.assertEqual((4 * self.x).size, (2,1))
        self.assertEqual((4 <= self.x).size, (2,1))
        self.assertEqual((4 == self.x).size, (2,1))
        self.assertEqual((self.x >= 4).size, (2,1))

        # Matrices
        exp = (self.A + 2) + 4
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual((3 * self.A).size, (2,2))

        self.assertEqual(exp.size, (2,2))

    # Test indexing expression.
    def test_index_expression(self):
        # Tuple of integers as key.
        exp = self.x[1,0]
        # self.assertEqual(exp.name(), "x[1,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        assert exp.is_affine()
        self.assertEquals(exp.size, (1,1))
        # coeff = exp.canonical_form[0].coefficients()[self.x][0]
        # self.assertEqual(coeff[0,1], 1)
        self.assertEqual(exp.value, None)

        exp = self.x[1,0].T
        # self.assertEqual(exp.name(), "x[1,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        with self.assertRaises(Exception) as cm:
            (self.x[2,0])
        self.assertEqual(str(cm.exception), "Index/slice out of bounds.")

        # Slicing
        exp = self.C[0:2,1]
        # self.assertEquals(exp.name(), "C[0:2,1]")
        self.assertEquals(exp.size, (2,1))
        exp = self.C[0:,0:2]
        # self.assertEquals(exp.name(), "C[0:,0:2]")
        self.assertEquals(exp.size, (3,2))
        exp = self.C[0::2,0::2]
        # self.assertEquals(exp.name(), "C[0::2,0::2]")
        self.assertEquals(exp.size, (2,1))
        exp = self.C[:3,:1:2]
        # self.assertEquals(exp.name(), "C[0:3,0]")
        self.assertEquals(exp.size, (3,1))
        exp = self.C[0:,0]
        # self.assertEquals(exp.name(), "C[0:,0]")
        self.assertEquals(exp.size, (3,1))

        c = Constant([[1,-2],[0,4]])
        exp = c[1, 1]
        self.assertEqual(exp.curvature, u.Curvature.CONSTANT_KEY)
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(c[0,1].sign, u.Sign.UNKNOWN_KEY)
        self.assertEqual(c[1,0].sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(exp.size, (1,1))
        self.assertEqual(exp.value, 4)

        c = Constant([[1,-2,3],[0,4,5],[7,8,9]])
        exp = c[0:3,0:4:2]
        self.assertEqual(exp.curvature, u.Curvature.CONSTANT_KEY)
        assert exp.is_constant()
        self.assertEquals(exp.size, (3,2))
        self.assertEqual(exp[0,1].value, 7)

        # Slice of transpose
        exp = self.C.T[0:2,1]
        self.assertEquals(exp.size, (2,1))

        # Arithmetic expression indexing
        exp = (self.x + self.z)[1,0]
        # self.assertEqual(exp.name(), "x[1,0] + z[1,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEqual(exp.sign, u.Sign.UNKNOWN_KEY)
        self.assertEquals(exp.size, (1,1))

        exp = (self.x + self.a)[1,0]
        # self.assertEqual(exp.name(), "x[1,0] + a")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        exp = (self.x - self.z)[1,0]
        # self.assertEqual(exp.name(), "x[1,0] - z[1,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        exp = (self.x - self.a)[1,0]
        # self.assertEqual(exp.name(), "x[1,0] - a")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        exp = (-self.x)[1,0]
        # self.assertEqual(exp.name(), "-x[1,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        c = Constant([[1,2],[3,4]])
        exp = (c*self.x)[1,0]
        # self.assertEqual(exp.name(), "[[2], [4]] * x[0:,0]")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

        c = Constant([[1,2],[3,4]])
        exp = (c*self.a)[1,0]
        # self.assertEqual(exp.name(), "2 * a")
        self.assertEqual(exp.curvature, u.Curvature.AFFINE_KEY)
        self.assertEquals(exp.size, (1,1))

########NEW FILE########
__FILENAME__ = test_interfaces
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.interface as intf
from cvxpy.utilities import Sign
import numpy as np
import scipy.sparse as sp
import cvxopt
import scipy
import unittest

class TestInterfaces(unittest.TestCase):
    """ Unit tests for matrix interfaces. """
    def setUp(self):
        pass

    def sign_for_intf(self, interface):
        """Test sign for a given interface.
        """
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals(intf.sign(mat), Sign.POSITIVE)
        self.assertEquals(intf.sign(-mat), Sign.NEGATIVE)
        self.assertEquals(intf.sign(0*mat), Sign.ZERO)
        mat = interface.const_to_matrix([[-1,2,3,4],[3,4,5,6]])
        self.assertEquals(intf.sign(mat), Sign.UNKNOWN)

    # Test cvxopt dense interface.
    def test_cvxopt_dense(self):
        interface = intf.get_matrix_interface(cvxopt.matrix)
        # const_to_matrix
        mat = interface.const_to_matrix([1,2,3])
        self.assertEquals(interface.size(mat), (3,1))
        sp_mat = sp.coo_matrix(([1,2], ([3,4], [2,1])), (5, 5))
        mat = interface.const_to_matrix(sp_mat)
        self.assertEquals(interface.size(mat), (5,5))
        # identity
        mat = interface.identity(4)
        cmp_mat = interface.const_to_matrix(np.eye(4))
        self.assertEquals(type(mat), type(cmp_mat))
        self.assertEquals(interface.size(mat), interface.size(cmp_mat))
        assert not mat - cmp_mat
        # scalar_matrix
        mat = interface.scalar_matrix(2,4,3)
        self.assertEquals(interface.size(mat), (4,3))
        self.assertEquals(interface.index(mat, (1,2)), 2)
        # reshape
        mat = interface.const_to_matrix([[1,2,3],[3,4,5]])
        mat = interface.reshape(mat, (6,1))
        self.assertEquals(interface.index(mat, (4,0)), 4)
        # index
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals( interface.index(mat, (0,1)), 3)
        mat = interface.index(mat, (slice(1,4,2), slice(0,2,None)))
        self.assertEquals(list(mat), [2,4,4,6])
        # Sign
        self.sign_for_intf(interface)

    # Test cvxopt sparse interface.
    def test_cvxopt_sparse(self):
        interface = intf.get_matrix_interface(cvxopt.spmatrix)
        # const_to_matrix
        mat = interface.const_to_matrix([1,2,3])
        self.assertEquals(interface.size(mat), (3,1))
        # identity
        mat = interface.identity(4)
        cmp_mat = interface.const_to_matrix(np.eye(4))
        self.assertEquals(interface.size(mat), interface.size(cmp_mat))
        assert not mat - cmp_mat
        assert intf.is_sparse(mat)
        # scalar_matrix
        mat = interface.scalar_matrix(2,4,3)
        self.assertEquals(interface.size(mat), (4,3))
        self.assertEquals(interface.index(mat, (1,2)), 2)
        # reshape
        mat = interface.const_to_matrix([[1,2,3],[3,4,5]])
        mat = interface.reshape(mat, (6,1))
        self.assertEquals(interface.index(mat, (4,0)), 4)
        # Test scalars.
        scalar = interface.scalar_matrix(1, 1, 1)
        self.assertEquals(type(scalar), cvxopt.spmatrix)
        scalar = interface.scalar_matrix(1, 1, 3)
        self.assertEquals(scalar.size, (1,3))
        # index
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals( interface.index(mat, (0,1)), 3)
        mat = interface.index(mat, (slice(1,4,2), slice(0,2,None)))
        self.assertEquals(list(mat), [2,4,4,6])
        # Sign
        self.sign_for_intf(interface)

    # Test numpy ndarray interface.
    def test_ndarray(self):
        interface = intf.get_matrix_interface(np.ndarray)
        # const_to_matrix
        mat = interface.const_to_matrix([1,2,3])
        self.assertEquals(interface.size(mat), (3,1))
        mat = interface.const_to_matrix([1,2])
        self.assertEquals(interface.size(mat), (2,1))
        # CVXOPT sparse conversion
        tmp = intf.get_matrix_interface(cvxopt.spmatrix).const_to_matrix([1,2,3])
        mat = interface.const_to_matrix(tmp)
        assert (mat == interface.const_to_matrix([1,2,3])).all()
        # identity
        mat = interface.identity(4)
        cvxopt_dense = intf.get_matrix_interface(cvxopt.matrix)
        cmp_mat = interface.const_to_matrix(cvxopt_dense.identity(4))
        self.assertEquals(interface.size(mat), interface.size(cmp_mat))
        assert (mat == cmp_mat).all()
        # scalar_matrix
        mat = interface.scalar_matrix(2,4,3)
        self.assertEquals(interface.size(mat), (4,3))
        self.assertEquals(interface.index(mat, (1,2)), 2)
        # reshape
        mat = interface.const_to_matrix([[1,2,3],[3,4,5]])
        mat = interface.reshape(mat, (6,1))
        self.assertEquals(interface.index(mat, (4,0)), 4)
        # index
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals( interface.index(mat, (0,1)), 3)
        mat = interface.index(mat, (slice(1,4,2), slice(0,2,None)))
        self.assertEquals(list(mat.flatten('C')), [2,4,4,6])
        # Scalars and matrices.
        scalar = interface.const_to_matrix(2)
        mat = interface.const_to_matrix([1,2,3])
        assert (scalar*mat == interface.const_to_matrix([2,4,6])).all()
        assert (scalar - mat == interface.const_to_matrix([1,0,-1])).all()
        # Sign
        self.sign_for_intf(interface)

    # Test numpy matrix interface.
    def test_numpy_matrix(self):
        interface = intf.get_matrix_interface(np.matrix)
        # const_to_matrix
        mat = interface.const_to_matrix([1,2,3])
        self.assertEquals(interface.size(mat), (3,1))
        mat = interface.const_to_matrix([[1],[2],[3]])
        self.assertEquals(mat[0,0], 1)
        # identity
        mat = interface.identity(4)
        cvxopt_dense = intf.get_matrix_interface(cvxopt.matrix)
        cmp_mat = interface.const_to_matrix(cvxopt_dense.identity(4))
        self.assertEquals(interface.size(mat), interface.size(cmp_mat))
        assert not (mat - cmp_mat).any()
        # scalar_matrix
        mat = interface.scalar_matrix(2,4,3)
        self.assertEquals(interface.size(mat), (4,3))
        self.assertEquals(interface.index(mat, (1,2)), 2)
        # reshape
        mat = interface.const_to_matrix([[1,2,3],[3,4,5]])
        mat = interface.reshape(mat, (6,1))
        self.assertEquals(interface.index(mat, (4,0)), 4)
        # index
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals( interface.index(mat, (0,1)), 3)
        mat = interface.index(mat, (slice(1,4,2), slice(0,2,None)))
        assert not (mat - np.matrix("2 4; 4 6")).any()
        # Sign
        self.sign_for_intf(interface)

    # Test cvxopt sparse interface.
    def test_scipy_sparse(self):
        interface = intf.get_matrix_interface(sp.csc_matrix)
        # const_to_matrix
        mat = interface.const_to_matrix([1,2,3])
        self.assertEquals(interface.size(mat), (3,1))
        C = cvxopt.spmatrix([1,1,1,1,1],[0,1,2,0,0,],[0,0,0,1,2])
        mat = interface.const_to_matrix(C)
        self.assertEquals(interface.size(mat), (3, 3))
        # identity
        mat = interface.identity(4)
        cmp_mat = interface.const_to_matrix(np.eye(4))
        self.assertEquals(interface.size(mat), interface.size(cmp_mat))
        assert (mat - cmp_mat).nnz == 0
        # scalar_matrix
        mat = interface.scalar_matrix(2,4,3)
        self.assertEquals(interface.size(mat), (4,3))
        self.assertEquals(interface.index(mat, (1,2)), 2)
        # reshape
        mat = interface.const_to_matrix([[1,2,3],[3,4,5]])
        mat = interface.reshape(mat, (6,1))
        self.assertEquals(interface.index(mat, (4,0)), 4)
        # Test scalars.
        scalar = interface.scalar_matrix(1, 1, 1)
        self.assertEquals(type(scalar), np.ndarray)
        scalar = interface.scalar_matrix(1, 1, 3)
        self.assertEquals(scalar.shape, (1,3))
        # index
        mat = interface.const_to_matrix([[1,2,3,4],[3,4,5,6]])
        self.assertEquals( interface.index(mat, (0,1)), 3)
        mat = interface.index(mat, (slice(1,4,2), slice(0,2,None)))
        assert not (mat - np.matrix("2 4; 4 6")).any()
        # scalar value
        mat = sp.eye(1)
        self.assertEqual(intf.scalar_value(mat), 1.0)
        # Sign
        self.sign_for_intf(interface)

########NEW FILE########
__FILENAME__ = test_lin_ops
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.lin_ops.lin_to_matrix import get_coefficients
from cvxpy.lin_ops.lin_utils import *
from cvxpy.lin_ops.lin_op import *
from cvxpy.expressions.constants import Parameter
import cvxpy.interface as intf
import numpy as np
import scipy.sparse as sp
import unittest
from base_test import BaseTest

class test_lin_ops(BaseTest):
    """ Unit tests for the lin_ops module. """

    def test_variables(self):
        """Test creating a variable.
        """
        var = create_var((5, 4), var_id=1)
        self.assertEqual(var.size, (5, 4))
        self.assertEqual(var.data, 1)
        self.assertEqual(len(var.args), 0)
        self.assertEqual(var.type, VARIABLE)

    def test_param(self):
        """Test creating a parameter.
        """
        A = Parameter(5, 4)
        var = create_param(A, (5, 4))
        self.assertEqual(var.size, (5, 4))
        self.assertEqual(len(var.args), 0)
        self.assertEqual(var.type, PARAM)

    def test_constant(self):
        """Test creating a constant.
        """
        # Scalar constant.
        size = (1, 1)
        mat = create_const(1.0, size)
        self.assertEqual(mat.size, size)
        self.assertEqual(len(mat.args), 0)
        self.assertEqual(mat.type, SCALAR_CONST)
        assert mat.data == 1.0

        # Dense matrix constant.
        size = (5, 4)
        mat = create_const(np.ones(size), size)
        self.assertEqual(mat.size, size)
        self.assertEqual(len(mat.args), 0)
        self.assertEqual(mat.type, DENSE_CONST)
        assert (mat.data == np.ones(size)).all()

        # Sparse matrix constant.
        size = (5, 5)
        mat = create_const(sp.eye(5), size, sparse=True)
        self.assertEqual(mat.size, size)
        self.assertEqual(len(mat.args), 0)
        self.assertEqual(mat.type, SPARSE_CONST)
        assert (mat.data.todense() == sp.eye(5).todense()).all()

    def test_add_expr(self):
        """Test adding lin expr.
        """
        size = (5, 4)
        x = create_var(size)
        y = create_var(size)
        # Expanding dict.
        add_expr = sum_expr([x, y])
        self.assertEqual(add_expr.size, size)
        assert len(add_expr.args) == 2

    def test_get_vars(self):
        """Test getting vars from an expression.
        """
        size = (5, 4)
        x = create_var(size)
        y = create_var(size)
        A = create_const(np.ones(size), size)
        # Expanding dict.
        add_expr = sum_expr([x, y, A])
        vars_ = get_expr_vars(add_expr)
        self.assertItemsEqual(vars_, [(x.data, size), (y.data, size)])

    def test_neg_expr(self):
        """Test negating an expression.
        """
        size = (5, 4)
        var = create_var(size)
        expr = neg_expr(var)
        assert len(expr.args) == 1
        self.assertEqual(expr.size, size)
        self.assertEqual(expr.type, NEG)

    def test_eq_constr(self):
        """Test creating an equality constraint.
        """
        size = (5, 5)
        x = create_var(size)
        y = create_var(size)
        lh_expr = sum_expr([x, y])
        value = np.ones(size)
        rh_expr = create_const(value, size)
        constr = create_eq(lh_expr, rh_expr)
        self.assertEqual(constr.size, size)
        vars_ = get_expr_vars(constr.expr)
        self.assertItemsEqual(vars_, [(x.data, size), (y.data, size)])

    def test_leq_constr(self):
        """Test creating a less than or equal constraint.
        """
        size = (5, 5)
        x = create_var(size)
        y = create_var(size)
        lh_expr = sum_expr([x, y])
        value = np.ones(size)
        rh_expr = create_const(value, size)
        constr = create_leq(lh_expr, rh_expr)
        self.assertEqual(constr.size, size)
        vars_ = get_expr_vars(constr.expr)
        self.assertItemsEqual(vars_, [(x.data, size), (y.data, size)])

    def test_get_coefficients(self):
        """Test the get_coefficients function.
        """
        size = (5, 4)
        # Eye
        x = create_var(size)
        coeffs = get_coefficients(x)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(id_, x.data)
        self.assertEqual(var_size, size)
        self.assertItemsAlmostEqual(mat.todense(), sp.eye(20).todense())
        # Eye with scalar mult.
        x = create_var(size)
        A = create_const(5, (1, 1))
        coeffs = get_coefficients(mul_expr(A, x, size))
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertItemsAlmostEqual(mat.todense(), 5*sp.eye(20).todense())
        # Promoted
        x = create_var((1, 1))
        A = create_const(np.ones(size), size)
        coeffs = get_coefficients(mul_expr(A, x, size))
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (20, 1))
        self.assertItemsAlmostEqual(mat, np.ones((20, 1)))
        # Normal
        size = (5, 5)
        x = create_var((5, 1))
        A = create_const(np.ones(size), size)
        coeffs = get_coefficients(mul_expr(A, x, (5, 1)))
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (5, 5))
        self.assertItemsAlmostEqual(mat, A.data)
        # Blocks
        size = (5, 5)
        x = create_var(size)
        A = create_const(np.ones(size), size)
        coeffs = get_coefficients(mul_expr(A, x, size))
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (25, 25))
        self.assertItemsAlmostEqual(mat.todense(),
         sp.block_diag(5*[np.ones(size)]).todense())
        # Scalar constant
        size = (1, 1)
        A = create_const(5, size)
        coeffs = get_coefficients(A)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(intf.size(mat), (1, 1))
        self.assertEqual(mat, 5)
        # Dense constant
        size = (5, 4)
        A = create_const(np.ones(size), size)
        coeffs = get_coefficients(A)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, size)
        self.assertItemsAlmostEqual(mat, np.ones(size))
        # Sparse constant
        size = (5, 5)
        A = create_const(sp.eye(5), size)
        coeffs = get_coefficients(A)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, size)
        self.assertItemsAlmostEqual(mat.todense(), sp.eye(5).todense())
        # Parameter
        size = (5, 4)
        param = Parameter(*size)
        param.value = np.ones(size)
        A = create_param(param, size)
        coeffs = get_coefficients(A)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, size)
        self.assertItemsAlmostEqual(mat, param.value)

    def test_transpose(self):
        """Test transpose op and coefficients.
        """
        size = (5, 4)
        x = create_var(size)
        expr, constr = transpose(x)
        assert len(constr) == 0
        self.assertEqual(expr.size, (4, 5))
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        test_mat = np.mat(range(20)).T
        self.assertItemsAlmostEqual((mat*test_mat).reshape((4, 5), order='F'),
            test_mat.reshape(size, order='F').T)

    def test_index(self):
        """Test the get_coefficients function for index.
        """
        size = (5, 4)
        # Eye
        key = (slice(0,2,None), slice(0,2,None))
        x = create_var(size)
        expr = index(x, (2, 2), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(id_, x.data)
        self.assertEqual(var_size, size)
        self.assertEqual(mat.shape, (4, 20))
        test_mat = np.mat(range(20)).T
        self.assertItemsAlmostEqual((mat*test_mat).reshape((2, 2), order='F'),
            test_mat.reshape(size, order='F')[key])
        # Eye with scalar mult.
        key = (slice(0,2,None), slice(0,2,None))
        x = create_var(size)
        A = create_const(5, (1, 1))
        expr = mul_expr(A, x, size)
        expr = index(expr, (2, 2), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        test_mat = np.mat(range(20)).T
        self.assertItemsAlmostEqual((mat*test_mat).reshape((2, 2), order='F'),
            5*test_mat.reshape(size, order='F')[key])
        # Promoted
        key = (slice(0,2,None), slice(0,2,None))
        x = create_var((1, 1))
        value = np.array(range(20)).reshape(size)
        A = create_const(value, size)
        expr = mul_expr(A, x, size)
        expr = index(expr, (2, 2), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (4, 1))
        self.assertItemsAlmostEqual(mat.todense(), value[key])
        # Normal
        size = (5, 5)
        key = (slice(0,2,None), slice(0,1,None))
        x = create_var((5, 1))
        A = create_const(np.ones(size), size)
        expr = mul_expr(A, x, (5, 1))
        expr = index(expr, (2, 1), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (2, 5))
        self.assertItemsAlmostEqual(mat, A.data[slice(0,2,None)])
        # Blocks
        size = (5, 5)
        key = (slice(0,2,None), slice(0,2,None))
        x = create_var(size)
        value = np.array(range(25)).reshape(size)
        A = create_const(value, size)
        expr = mul_expr(A, x, size)
        expr = index(expr, (2, 2), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (4, 25))
        test_mat = np.mat(range(25)).T
        self.assertItemsAlmostEqual((mat*test_mat).reshape((2, 2), order='F'),
            (A.data*test_mat.reshape(size, order='F'))[key])
        # Scalar constant
        size = (1, 1)
        A = create_const(5, size)
        key = (slice(0,1,None), slice(0,1,None))
        expr = index(A, (1, 1), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(intf.size(mat), (1, 1))
        self.assertEqual(mat, 5)
        # Dense constant
        size = (5, 4)
        key = (slice(0,2,None), slice(0,1,None))
        value = np.array(range(20)).reshape(size)
        A = create_const(value, size)
        expr = index(A, (2, 1), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (2, 1))
        self.assertItemsAlmostEqual(mat, value[key])
        # Sparse constant
        size = (5, 5)
        key = (slice(0,2,None), slice(0,1,None))
        A = create_const(sp.eye(5), size)
        expr = index(A, (2, 1), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (2, 1))
        self.assertItemsAlmostEqual(mat.todense(), sp.eye(5).todense()[key])
        # Parameter
        size = (5, 4)
        key = (slice(0,2,None), slice(0,1,None))
        param = Parameter(*size)
        value = np.array(range(20)).reshape(size)
        param.value = value
        A = create_param(param, size)
        expr = index(A, (2, 1), key)
        coeffs = get_coefficients(expr)
        assert len(coeffs) == 1
        id_, var_size, mat = coeffs[0]
        self.assertEqual(mat.shape, (2, 1))
        self.assertItemsAlmostEqual(mat, param.value[key])


    def test_sum_entries(self):
        """Test sum entries op.
        """
        size = (5, 5)
        x = create_var(size)
        expr = sum_entries(x)
        self.assertEqual(expr.size, (1, 1))
        self.assertEqual(len(expr.args), 1)
        self.assertEqual(expr.type, lo.SUM_ENTRIES)

########NEW FILE########
__FILENAME__ = test_matrices
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms import *
from cvxpy.expressions.expression import *
from cvxpy.expressions.constants import *
from cvxpy.expressions.variables import Variable
from cvxpy.problems.objective import *
from cvxpy.problems.problem import Problem
import cvxpy.interface.matrix_utilities as intf
import cvxpy.interface.numpy_wrapper
import numpy
import cvxopt
import scipy
import scipy.sparse as sp
import unittest

class TestMatrices(unittest.TestCase):
    """ Unit tests for testing different forms of matrices as constants. """
    def setUp(self):
        self.a = Variable(name='a')
        self.b = Variable(name='b')
        self.c = Variable(name='c')

        self.x = Variable(2, name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(2, name='z')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # Test numpy arrays
    def test_numpy_arrays(self):
        # Vector
        v = numpy.arange(2).reshape((2,1))
        self.assertEquals((self.x + v).size, (2,1))
        self.assertEquals((v + self.x).size, (2,1))
        self.assertEquals((self.x - v).size, (2,1))
        self.assertEquals((v - self.x).size, (2,1))
        self.assertEquals((self.x <= v).size, (2,1))
        self.assertEquals((v <= self.x).size, (2,1))
        self.assertEquals((self.x == v).size, (2,1))
        self.assertEquals((v == self.x).size, (2,1))
        # Matrix
        A = numpy.arange(8).reshape((4,2))
        self.assertEquals((A*self.x).size, (4,1))

    # Test numpy matrices
    def test_numpy_matrices(self):
        # Vector
        v = numpy.matrix( numpy.arange(2).reshape((2,1)) )
        self.assertEquals((self.x + v).size, (2,1))
        self.assertEquals((v + v + self.x).size, (2,1))
        self.assertEquals((self.x - v).size, (2,1))
        self.assertEquals((v - v - self.x).size, (2,1))
        self.assertEquals((self.x <= v).size, (2,1))
        self.assertEquals((v <= self.x).size, (2,1))
        self.assertEquals((self.x == v).size, (2,1))
        self.assertEquals((v == self.x).size, (2,1))
        # Matrix
        A = numpy.matrix( numpy.arange(8).reshape((4,2)) )
        self.assertEquals((A*self.x).size, (4,1))
        self.assertEquals(( (A.T*A) * self.x).size, (2,1))

    def test_numpy_scalars(self):
        """Test numpy scalars."""
        v = numpy.float64(2.0)
        self.assertEquals((self.x + v).size, (2,1))
        self.assertEquals((v + self.x).size, (2,1))
        self.assertEquals((v * self.x).size, (2,1))
        self.assertEquals((self.x - v).size, (2,1))
        self.assertEquals((v - v - self.x).size, (2,1))
        self.assertEquals((self.x <= v).size, (2,1))
        self.assertEquals((v <= self.x).size, (2,1))
        self.assertEquals((self.x == v).size, (2,1))
        self.assertEquals((v == self.x).size, (2,1))

    # Test cvxopt sparse matrices.
    def test_cvxopt_sparse(self):
        m = 100
        n = 20

        mu = cvxopt.exp( cvxopt.normal(m) )
        F = cvxopt.normal(m, n)
        D = cvxopt.spdiag( cvxopt.uniform(m) )
        x = Variable(m)
        exp = square(norm2(D*x))

    # def test_scipy_sparse(self):
    #     """Test scipy sparse matrices."""
    #     # Constants.
    #     A = numpy.matrix( numpy.arange(8).reshape((4,2)) )
    #     A = sp.csc_matrix(A)
    #     A = sp.eye(2).tocsc()
    #     key = (slice(0, 1, None), slice(None, None, None))
    #     Aidx = intf.index(A, (slice(0, 2, None), slice(None, None, None)))
    #     Aidx = intf.index(Aidx, key)
    #     self.assertEquals(Aidx.shape, (1, 2))
    #     self.assertEqual(Aidx[0,0], 1)
    #     self.assertEqual(Aidx[0,1], 0)

    #     # Linear ops.
    #     var = Variable(4, 2)
    #     A = numpy.matrix( numpy.arange(8).reshape((4,2)) )
    #     A = sp.csc_matrix(A)
    #     B = sp.hstack([A, A])
    #     self.assertEquals((var + A).size, (4, 2))
    #     self.assertEquals((A + var).size, (4, 2))
    #     self.assertEquals((B * var).size, (4, 2))
    #     self.assertEquals((var - A).size, (4, 2))
    #     self.assertEquals((A - A - var).size, (4, 2))
    #     self.assertEquals((var <= A).size, (4, 2))
    #     self.assertEquals((A <= var).size, (4, 2))
    #     self.assertEquals((var == A).size, (4, 2))
    #     self.assertEquals((A == var).size, (4, 2))

########NEW FILE########
__FILENAME__ = test_monotonicity
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities import Curvature, Sign
import cvxpy.utilities.monotonicity as m
from nose.tools import *

class TestMonotonicity(object):
    """ Unit tests for the utilities/monotonicity class. """
    # Test application of DCP composition rules to determine curvature.
    def test_dcp_curvature(self):
        assert_equals(m.dcp_curvature(m.INCREASING,
                                      Curvature.AFFINE,
                                                 Sign.POSITIVE,
                                                 Curvature.CONVEX),
                      Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.NONMONOTONIC, Curvature.AFFINE,
                                                   Sign.POSITIVE,
                                                   Curvature.AFFINE),
                    Curvature.AFFINE)
        assert_equals(m.dcp_curvature(m.DECREASING, Curvature.UNKNOWN,
                                                 Sign.POSITIVE,
                                                 Curvature.CONSTANT),
                      Curvature.CONSTANT)

        assert_equals(m.dcp_curvature(m.INCREASING, Curvature.CONVEX,
                                                            Sign.POSITIVE,
                                                            Curvature.CONVEX),
                       Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.DECREASING, Curvature.CONVEX,
                                                            Sign.POSITIVE,
                                                            Curvature.CONCAVE),
                       Curvature.CONVEX)

        assert_equals(m.dcp_curvature(m.INCREASING, Curvature.CONCAVE,
                                                            Sign.POSITIVE,
                                                            Curvature.CONCAVE),
                      Curvature.CONCAVE)
        assert_equals(m.dcp_curvature(m.DECREASING, Curvature.CONCAVE,
                                                            Sign.POSITIVE,
                                                            Curvature.CONVEX),
                      Curvature.CONCAVE)

        assert_equals(m.dcp_curvature(m.INCREASING, Curvature.CONCAVE,
                                                            Sign.POSITIVE,
                                                            Curvature.CONVEX),
                      Curvature.UNKNOWN)
        assert_equals(m.dcp_curvature(m.NONMONOTONIC, Curvature.CONCAVE,
                                                              Sign.POSITIVE,
                                                              Curvature.AFFINE),
                      Curvature.CONCAVE)

        assert_equals(m.dcp_curvature(m.NONMONOTONIC, Curvature.CONSTANT,
                                                              Sign.POSITIVE,
                                                              Curvature.UNKNOWN),
                      Curvature.UNKNOWN)

    # Test DCP composition rules with signed monotonicity.
    def test_signed_curvature(self):
        # Convex argument.
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.POSITIVE,
                                                        Curvature.CONVEX),
                      Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.NEGATIVE,
                                                        Curvature.CONVEX),
                      Curvature.UNKNOWN)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.UNKNOWN,
                                                        Curvature.CONVEX),
                      Curvature.UNKNOWN)
        # Concave argument.
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.POSITIVE,
                                                        Curvature.CONCAVE),
                      Curvature.UNKNOWN)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.NEGATIVE,
                                                        Curvature.CONCAVE),
                      Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.UNKNOWN,
                                                        Curvature.CONCAVE),
                      Curvature.UNKNOWN)
        # Affine argument.
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.POSITIVE,
                                                        Curvature.AFFINE),
                      Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.NEGATIVE,
                                                        Curvature.AFFINE),
                      Curvature.CONVEX)
        assert_equals(m.dcp_curvature(m.SIGNED, Curvature.CONVEX,
                                                        Sign.UNKNOWN,
                                                        Curvature.AFFINE),
                      Curvature.CONVEX)
########NEW FILE########
__FILENAME__ = test_nonlinear_atoms
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
import cvxpy.atoms.elementwise.log as cvxlog
from base_test import BaseTest
import cvxopt.solvers
import cvxopt
import unittest
import math
import numpy as np

class TestNonlinearAtoms(BaseTest):
    """ Unit tests for the nonlinear atoms module. """
    def setUp(self):
        self.x = Variable(2, name='x')
        self.y = Variable(2, name='y')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # def test_log(self):
    #     """ Test that minimize -sum(log(x)) s.t. x <= 1 yields 0.

    #         Rewritten by hand.

    #         neg_log_func implements

    #             t1 - log(t2) <= 0

    #         Implemented as

    #             minimize [-1,-1,0,0] * [t1; t2]
    #                 t1 - log(t2) <= 0
    #                 [0 0 -1 0;
    #                  0 0 0 -1] * [t1; t2] <= [-1; -1]
    #     """
    #     F = cvxlog.neg_log_func(2)
    #     h = cvxopt.matrix([1.,1.])
    #     G = cvxopt.spmatrix([1.,1.], [0,1], [2,3], (2,4), tc='d')
    #     sol = cvxopt.solvers.cpl(cvxopt.matrix([-1.0,-1.0,0,0]), F, G, h)

    #     self.assertEqual(sol['status'], 'optimal')
    #     self.assertAlmostEqual(sol['x'][0], 0.)
    #     self.assertAlmostEqual(sol['x'][1], 0.)
    #     self.assertAlmostEqual(sol['x'][2], 1.)
    #     self.assertAlmostEqual(sol['x'][3], 1.)
    #     self.assertAlmostEqual(sol['primal objective'], 0.0)

    def test_log_problem(self):
        # Log in objective.
        obj = Maximize(sum_entries(log(self.x)))
        constr = [self.x <= [1, math.e]]
        p = Problem(obj, constr)
        result = p.solve(solver=CVXOPT)
        self.assertAlmostEqual(result, 1)
        self.assertItemsAlmostEqual(self.x.value, [1, math.e])

        # Log in constraint.
        obj = Minimize(sum_entries(self.x))
        constr = [log(self.x) >= 0, self.x <= [1,1]]
        p = Problem(obj, constr)
        result = p.solve(solver=CVXOPT)
        self.assertAlmostEqual(result, 2)
        self.assertItemsAlmostEqual(self.x.value, [1,1])

        # Index into log.
        obj = Maximize(log(self.x)[1])
        constr = [self.x <= [1, math.e]]
        p = Problem(obj,constr)
        result = p.solve(solver=CVXOPT)
        self.assertAlmostEqual(result, 1)

    def test_entr(self):
        """Test the entr atom.
        """
        self.assertEqual(entr(0).value, 0)
        assert np.isneginf(entr(-1).value)

    def test_kl_div(self):
        """Test a problem with kl_div.
        """
        import numpy as np
        import cvxpy as cp

        kK=50
        kSeed=10

        prng=np.random.RandomState(kSeed)
        #Generate a random reference distribution
        npSPriors=prng.uniform(0.0,1.0,kK)
        npSPriors=npSPriors/np.sum(npSPriors)

        #Reference distribution
        p_refProb=cp.Parameter(kK,1,sign='positive')
        #Distribution to be estimated
        v_prob=cp.Variable(kK,1)
        objkl=0.0
        for k in xrange(kK):
            objkl += cp.kl_div(v_prob[k,0],p_refProb[k,0])

        constrs=[__builtins__['sum']([v_prob[k,0] for k in xrange(kK)])==1]
        klprob=cp.Problem(cp.Minimize(objkl),constrs)
        p_refProb.value=npSPriors
        result = klprob.solve(solver=CVXOPT, verbose=True)
        self.assertItemsAlmostEqual(v_prob.value, npSPriors)
        result = klprob.solve(solver=SCS, verbose=True)
        self.assertItemsAlmostEqual(v_prob.value, npSPriors, places=3)

    def test_entr(self):
        """Test a problem with entr.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Maximize(sum_entries(entr(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=CVXOPT, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n], places=3)

    def test_exp(self):
        """Test a problem with exp.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Minimize(sum_entries(exp(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=CVXOPT, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n], places=3)

    def test_log(self):
        """Test a problem with log.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Maximize(sum_entries(log(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=CVXOPT, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n], places=3)

    # def test_kl_div(self):
    #     """Test the kl_div atom.
    #     """
    #     self.assertEqual(kl_div(0, 0).value, 0)
    #     self.assertEqual(kl_div(1, 0).value, np.inf)
    #     self.assertEqual(kl_div(0, 1).value, np.inf)
    #     self.assertEqual(kl_div(-1, -1).value, np.inf)


########NEW FILE########
__FILENAME__ = test_objectives
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.atoms import *
from cvxpy.expressions.variables import Variable
from cvxpy.problems.objective import *
import unittest

class TestObjectives(unittest.TestCase):
    """ Unit tests for the expression/expression module. """
    def setUp(self):
        self.x = Variable(name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(name='z')

    # Test the Minimize class.
    def test_minimize(self):
        exp = self.x + self.z
        obj = Minimize(exp)
        self.assertEqual(str(obj), "minimize %s" % exp.name())
        new_obj,constraints = obj.canonical_form
        #self.assertEqual(constraints[0].name(), (new_obj == exp).name())
        # for affine objectives, there should be no constraints
        self.assertEqual(len(constraints), 0)

        with self.assertRaises(Exception) as cm:
            Minimize(self.y).canonical_form
        self.assertEqual(str(cm.exception),
            "The 'minimize' objective must resolve to a scalar.")

    # Test the Maximize class.
    def test_maximize(self):
        exp = self.x + self.z
        obj = Maximize(exp)
        self.assertEqual(str(obj), "maximize %s" % exp.name())
        new_obj,constraints = obj.canonical_form
        #self.assertEqual(constraints[0].name(), (new_obj == exp).name())
        # for affine objectives, there should be no constraints
        self.assertEqual(len(constraints), 0)

        with self.assertRaises(Exception) as cm:
            Maximize(self.y).canonical_form
        self.assertEqual(str(cm.exception),
            "The 'maximize' objective must resolve to a scalar.")

    # Test is_dcp for Minimize and Maximize
    def test_is_dcp(self):
        self.assertEqual(Minimize(normInf(self.x)).is_dcp(), True)
        self.assertEqual(Minimize(-normInf(self.x)).is_dcp(), False)

        self.assertEqual(Maximize(normInf(self.x)).is_dcp(), False)
        self.assertEqual(Maximize(-normInf(self.x)).is_dcp(), True)
########NEW FILE########
__FILENAME__ = test_problem
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import cvxpy.settings as s
from cvxpy.atoms import *
from cvxpy.expressions.constants import Constant, Parameter
from cvxpy.expressions.variables import Variable
from cvxpy.problems.objective import *
from cvxpy.problems.problem import Problem
import cvxpy.interface as intf
import cvxpy.lin_ops.lin_utils as lu
from base_test import BaseTest
from cvxopt import matrix
from numpy import linalg as LA
import numpy
import unittest
import math
import sys
from cStringIO import StringIO

class TestProblem(BaseTest):
    """ Unit tests for the expression/expression module. """
    def setUp(self):
        self.a = Variable(name='a')
        self.b = Variable(name='b')
        self.c = Variable(name='c')

        self.x = Variable(2, name='x')
        self.y = Variable(3, name='y')
        self.z = Variable(2, name='z')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    def test_variables(self):
        """Test the variables method.
        """
        p = Problem(Minimize(self.a), [self.a <= self.x, self.b <= self.A + 2])
        vars_ = p.variables()
        self.assertItemsEqual(vars_, [self.a, self.x, self.b, self.A])

    def test_parameters(self):
        """Test the parameters method.
        """
        p1 = Parameter()
        p2 = Parameter(3, sign="negative")
        p3 = Parameter(4, 4, sign="positive")
        p = Problem(Minimize(p1), [self.a + p1 <= p2, self.b <= p3 + p3 + 2])
        params = p.parameters()
        self.assertItemsEqual(params, [p1, p2, p3])

    def test_get_problem_data(self):
        """Test get_problem_data method.
        """
        with self.assertRaises(Exception) as cm:
            Problem(Maximize(exp(self.a))).get_problem_data(s.ECOS)
        self.assertEqual(str(cm.exception), "The solver ECOS cannot solve the problem.")

        with self.assertRaises(Exception) as cm:
            Problem(Maximize(exp(self.a))).get_problem_data(s.CVXOPT)
        self.assertEqual(str(cm.exception), "Cannot return problem data for the solver CVXOPT.")

        args = Problem(Maximize(exp(self.a) + 2)).get_problem_data(s.SCS)
        data, dims = args
        self.assertEqual(dims['ep'], 1)
        self.assertEqual(data["c"].shape, (2,))
        self.assertEqual(data["A"].shape, (3, 2))

        args = Problem(Minimize(norm(self.x) + 3)).get_problem_data(s.ECOS)
        c, G, h, dims, A, b = args
        self.assertEqual(dims["q"], [3])
        self.assertEqual(c.shape, (3,))
        self.assertEqual(A.shape, (0, 3))
        self.assertEqual(G.shape, (3, 3))

        args = Problem(Minimize(norm(self.x) + 3)).get_problem_data(s.CVXOPT)
        c, G, h, dims, A, b = args
        self.assertEqual(dims["q"], [3])
        self.assertEqual(c.size, (3, 1))
        self.assertEqual(A.size, (0, 3))
        self.assertEqual(G.size, (3, 3))

    # Test silencing and enabling solver messages.
    def test_verbose(self):
        # From http://stackoverflow.com/questions/5136611/capture-stdout-from-a-script-in-python
        # setup the environment
        outputs = {True: [], False: []}
        backup = sys.stdout

        # ####
        for verbose in [True, False]:
            for solver in [s.ECOS, s.CVXOPT, s.SCS]:
                sys.stdout = StringIO()     # capture output
                p = Problem(Minimize(self.a), [self.a >= 2])
                p.solve(verbose=verbose, solver=solver)
                if solver != s.ECOS:
                    p = Problem(Minimize(self.a), [log(self.a) >= 2])
                    p.solve(verbose=verbose, solver=solver)
                out = sys.stdout.getvalue() # release output
                outputs[verbose].append(out.upper())
        # ####

        sys.stdout.close()  # close the stream
        sys.stdout = backup # restore original stdout

        for output in outputs[True]:
            assert len(output) > 0
        for output in outputs[False]:
            assert len(output) == 0

    # Test registering other solve methods.
    def test_register_solve(self):
        Problem.register_solve("test",lambda self: 1)
        p = Problem(Minimize(1))
        result = p.solve(method="test")
        self.assertEqual(result, 1)

        def test(self, a, b=2):
            return (a,b)
        Problem.register_solve("test", test)
        p = Problem(Minimize(0))
        result = p.solve(1,b=3,method="test")
        self.assertEqual(result, (1,3))
        result = p.solve(1,method="test")
        self.assertEqual(result, (1,2))
        result = p.solve(1,method="test",b=4)
        self.assertEqual(result, (1,4))

    def test_consistency(self):
        """Test that variables and constraints keep a consistent order.
        """
        import itertools
        num_solves = 4
        vars_lists = []
        ineqs_lists = []
        var_ids_order_created = []
        for k in range(num_solves):
            sum = 0
            constraints = []
            var_ids = []
            for i in range(100):
                var = Variable(name=str(i))
                var_ids.append(var.id)
                sum += var
                constraints.append(var >= i)
            var_ids_order_created.append(var_ids)
            obj = Minimize(sum)
            p = Problem(obj, constraints)
            objective, constr_map = p.canonicalize()
            all_ineq = itertools.chain(constr_map[s.EQ], constr_map[s.LEQ])
            var_offsets, var_sizes, x_length = p._get_var_offsets(objective, all_ineq)
            # Sort by offset.
            vars_ = sorted(var_offsets.items(), key=lambda (var_id, offset): offset)
            vars_ = [var_id for (var_id, offset) in vars_]
            vars_lists.append(vars_)
            ineqs_lists.append(constr_map[s.LEQ])

        # Verify order of variables is consistent.
        for i in range(num_solves):
            self.assertEqual(var_ids_order_created[i],
                vars_lists[i])
        for i in range(num_solves):
            for idx, constr in enumerate(ineqs_lists[i]):
                var_id, _ = lu.get_expr_vars(constr.expr)[0]
                self.assertEqual(var_ids_order_created[i][idx],
                    var_id)

    # Test removing duplicate constraint objects.
    def test_duplicate_constraints(self):
        eq = (self.x == 2)
        le = (self.x <= 2)
        obj = 0
        def test(self):
            objective, constr_map  = self.canonicalize()
            dims = self._format_for_solver(constr_map, s.ECOS)
            return (len(constr_map[s.EQ]),len(constr_map[s.LEQ]))
        Problem.register_solve("test", test)
        p = Problem(Minimize(obj),[eq,eq,le,le])
        result = p.solve(method="test")
        self.assertEqual(result, (1,1))

        # Internal constraints.
        z = hstack(self.x, self.x)
        obj = sum_entries(z[:,0] + z[:,1])
        p = Problem(Minimize(obj))
        result = p.solve(method="test")
        self.assertEqual(result, (2,0))

    # Test the is_dcp method.
    def test_is_dcp(self):
        p = Problem(Minimize(normInf(self.a)))
        self.assertEqual(p.is_dcp(), True)

        p = Problem(Maximize(normInf(self.a)))
        self.assertEqual(p.is_dcp(), False)
        with self.assertRaises(Exception) as cm:
            p.solve()
        self.assertEqual(str(cm.exception), "Problem does not follow DCP rules.")
        p.solve(ignore_dcp=True)

    # Test problems involving variables with the same name.
    def test_variable_name_conflict(self):
        var = Variable(name='a')
        p = Problem(Maximize(self.a + var), [var == 2 + self.a, var <= 3])
        result = p.solve()
        self.assertAlmostEqual(result, 4.0)
        self.assertAlmostEqual(self.a.value, 1)
        self.assertAlmostEqual(var.value, 3)

    # Test scalar LP problems.
    def test_scalar_lp(self):
        p = Problem(Minimize(3*self.a), [self.a >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 6)
        self.assertAlmostEqual(self.a.value, 2)

        p = Problem(Maximize(3*self.a - self.b),
            [self.a <= 2, self.b == self.a, self.b <= 5])
        result = p.solve()
        self.assertAlmostEqual(result, 4.0)
        self.assertAlmostEqual(self.a.value, 2)
        self.assertAlmostEqual(self.b.value, 2)

        # With a constant in the objective.
        p = Problem(Minimize(3*self.a - self.b + 100),
            [self.a >= 2,
             self.b + 5*self.c - 2 == self.a,
             self.b <= 5 + self.c])
        result = p.solve()
        self.assertAlmostEqual(result, 101 + 1.0/6)
        self.assertAlmostEqual(self.a.value, 2)
        self.assertAlmostEqual(self.b.value, 5-1.0/6)
        self.assertAlmostEqual(self.c.value, -1.0/6)

        # Test status and value.
        exp = Maximize(self.a)
        p = Problem(exp, [self.a <= 2])
        result = p.solve(solver=s.ECOS)
        self.assertEqual(result, p.value)
        self.assertEqual(p.status, s.OPTIMAL)
        assert self.a.value is not None
        assert p.constraints[0].dual_value is not None

        # Unbounded problems.
        p = Problem(Maximize(self.a), [self.a >= 2])
        p.solve(solver=s.ECOS)
        self.assertEqual(p.status, s.UNBOUNDED)
        assert numpy.isinf(p.value)
        assert p.value > 0
        assert self.a.value is None
        assert p.constraints[0].dual_value is None

        p = Problem(Minimize(-self.a), [self.a >= 2])
        result = p.solve(solver=s.CVXOPT)
        self.assertEqual(result, p.value)
        self.assertEqual(p.status, s.UNBOUNDED)
        assert numpy.isinf(p.value)
        assert p.value < 0

        # Infeasible problems.
        p = Problem(Maximize(self.a), [self.a >= 2, self.a <= 1])
        self.a.save_value(2)
        p.constraints[0].save_value(2)

        result = p.solve(solver=s.ECOS)
        self.assertEqual(result, p.value)
        self.assertEqual(p.status, s.INFEASIBLE)
        assert numpy.isinf(p.value)
        assert p.value < 0
        assert self.a.value is None
        assert p.constraints[0].dual_value is None

        p = Problem(Minimize(-self.a), [self.a >= 2, self.a <= 1])
        result = p.solve(solver=s.ECOS)
        self.assertEqual(result, p.value)
        self.assertEqual(p.status, s.INFEASIBLE)
        assert numpy.isinf(p.value)
        assert p.value > 0

    # Test vector LP problems.
    def test_vector_lp(self):
        c = matrix([1,2])
        p = Problem(Minimize(c.T*self.x), [self.x >= c])
        result = p.solve()
        self.assertAlmostEqual(result, 5)
        self.assertItemsAlmostEqual(self.x.value, [1,2])

        A = matrix([[3,5],[1,2]])
        I = Constant([[1,0],[0,1]])
        p = Problem(Minimize(c.T*self.x + self.a),
            [A*self.x >= [-1,1],
             4*I*self.z == self.x,
             self.z >= [2,2],
             self.a >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 26, places=3)
        obj = c.T*self.x.value + self.a.value
        self.assertAlmostEqual(obj[0], result)
        self.assertItemsAlmostEqual(self.x.value, [8,8], places=3)
        self.assertItemsAlmostEqual(self.z.value, [2,2], places=3)

    def test_ecos_noineq(self):
        """Test ECOS with no inequality constraints.
        """
        T = matrix(1, (2, 2))
        p = Problem(Minimize(1), [self.A == T])
        result = p.solve(solver=s.ECOS)
        self.assertAlmostEqual(result, 1)
        self.assertItemsAlmostEqual(self.A.value, T)

    # Test matrix LP problems.
    def test_matrix_lp(self):
        T = matrix(1, (2, 2))
        p = Problem(Minimize(1), [self.A == T])
        result = p.solve()
        self.assertAlmostEqual(result, 1)
        self.assertItemsAlmostEqual(self.A.value, T)

        T = matrix(2,(2,3))
        c = matrix([3,4])
        p = Problem(Minimize(1), [self.A >= T*self.C,
            self.A == self.B, self.C == T.T])
        result = p.solve()
        self.assertAlmostEqual(result, 1)
        self.assertItemsAlmostEqual(self.A.value, self.B.value)
        self.assertItemsAlmostEqual(self.C.value, T)
        assert (self.A.value >= T*self.C.value).all()

        # Test variables are dense.
        self.assertEqual(type(self.A.value), p._DENSE_INTF.TARGET_MATRIX)

    # Test variable promotion.
    def test_variable_promotion(self):
        p = Problem(Minimize(self.a), [self.x <= self.a, self.x == [1,2]])
        result = p.solve()
        self.assertAlmostEqual(result, 2)
        self.assertAlmostEqual(self.a.value, 2)

        p = Problem(Minimize(self.a),
            [self.A <= self.a,
             self.A == [[1,2],[3,4]]
             ])
        result = p.solve()
        self.assertAlmostEqual(result, 4)
        self.assertAlmostEqual(self.a.value, 4)

        # Promotion must happen before the multiplication.
        p = Problem(Minimize([[1],[1]]*(self.x + self.a + 1)),
            [self.a + self.x >= [1,2]])
        result = p.solve()
        self.assertAlmostEqual(result, 5)

    # Test parameter promotion.
    def test_parameter_promotion(self):
        a = Parameter()
        exp = [[1,2],[3,4]]*a
        a.value = 2
        assert not (exp.value - 2*numpy.array([[1,2],[3,4]]).T).any()

    def test_parameter_problems(self):
        """Test problems with parameters.
        """
        p1 = Parameter()
        p2 = Parameter(3, sign="negative")
        p3 = Parameter(4, 4, sign="positive")
        p = Problem(Maximize(p1*self.a), [self.a + p1 <= p2, self.b <= p3 + p3 + 2])
        p1.value = 2
        p2.value = -numpy.ones(3)
        p3.value = numpy.ones((4, 4))
        result = p.solve()
        self.assertAlmostEqual(result, -6)

    # Test problems with normInf
    def test_normInf(self):
        # Constant argument.
        p = Problem(Minimize(normInf(-2)))
        result = p.solve()
        self.assertAlmostEqual(result, 2)

        # Scalar arguments.
        p = Problem(Minimize(normInf(self.a)), [self.a >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 2)
        self.assertAlmostEqual(self.a.value, 2)

        p = Problem(Minimize(3*normInf(self.a + 2*self.b) + self.c),
            [self.a >= 2, self.b <= -1, self.c == 3])
        result = p.solve()
        self.assertAlmostEqual(result, 3)
        self.assertAlmostEqual(self.a.value + 2*self.b.value, 0)
        self.assertAlmostEqual(self.c.value, 3)

        # Maximize
        p = Problem(Maximize(-normInf(self.a)), [self.a <= -2])
        result = p.solve()
        self.assertAlmostEqual(result, -2)
        self.assertAlmostEqual(self.a.value, -2)

        # Vector arguments.
        p = Problem(Minimize(normInf(self.x - self.z) + 5),
            [self.x >= [2,3], self.z <= [-1,-4]])
        result = p.solve()
        self.assertAlmostEqual(result, 12)
        self.assertAlmostEqual(list(self.x.value)[1] - list(self.z.value)[1], 7)

    # Test problems with norm1
    def test_norm1(self):
        # Constant argument.
        p = Problem(Minimize(norm1(-2)))
        result = p.solve()
        self.assertAlmostEqual(result, 2)

        # Scalar arguments.
        p = Problem(Minimize(norm1(self.a)), [self.a <= -2])
        result = p.solve()
        self.assertAlmostEqual(result, 2)
        self.assertAlmostEqual(self.a.value, -2)

        # Maximize
        p = Problem(Maximize(-norm1(self.a)), [self.a <= -2])
        result = p.solve()
        self.assertAlmostEqual(result, -2)
        self.assertAlmostEqual(self.a.value, -2)

        # Vector arguments.
        p = Problem(Minimize(norm1(self.x - self.z) + 5),
            [self.x >= [2,3], self.z <= [-1,-4]])
        result = p.solve()
        self.assertAlmostEqual(result, 15)
        self.assertAlmostEqual(list(self.x.value)[1] - list(self.z.value)[1], 7)

    # Test problems with norm2
    def test_norm2(self):
        # Constant argument.
        p = Problem(Minimize(norm2(-2)))
        result = p.solve()
        self.assertAlmostEqual(result, 2)

        # Scalar arguments.
        p = Problem(Minimize(norm2(self.a)), [self.a <= -2])
        result = p.solve()
        self.assertAlmostEqual(result, 2)
        self.assertAlmostEqual(self.a.value, -2)

        # Maximize
        p = Problem(Maximize(-norm2(self.a)), [self.a <= -2])
        result = p.solve()
        self.assertAlmostEqual(result, -2)
        self.assertAlmostEqual(self.a.value, -2)

        # Vector arguments.
        p = Problem(Minimize(norm2(self.x - self.z) + 5),
            [self.x >= [2,3], self.z <= [-1,-4]])
        result = p.solve()
        self.assertAlmostEqual(result, 12.61577)
        self.assertItemsAlmostEqual(self.x.value, [2,3])
        self.assertItemsAlmostEqual(self.z.value, [-1,-4])

        # Row  arguments.
        p = Problem(Minimize(norm2((self.x - self.z).T) + 5),
            [self.x >= [2,3], self.z <= [-1,-4]])
        result = p.solve()
        self.assertAlmostEqual(result, 12.61577)
        self.assertItemsAlmostEqual(self.x.value, [2,3])
        self.assertItemsAlmostEqual(self.z.value, [-1,-4])

    # Test problems with abs
    def test_abs(self):
        p = Problem(Minimize(sum_entries(abs(self.A))), [-2 >= self.A])
        result = p.solve()
        self.assertAlmostEqual(result, 8)
        self.assertItemsAlmostEqual(self.A.value, [-2,-2,-2,-2])

    # Test problems with quad_form.
    def test_quad_form(self):
        with self.assertRaises(Exception) as cm:
            Problem(Minimize(quad_form(self.x, self.A))).solve()
        self.assertEqual(str(cm.exception), "At least one argument to quad_form must be constant.")

        with self.assertRaises(Exception) as cm:
            Problem(Minimize(quad_form(1, self.A))).solve()
        self.assertEqual(str(cm.exception), "Invalid dimensions for arguments.")

        with self.assertRaises(Exception) as cm:
            Problem(Minimize(quad_form(self.x, [[-1, 0], [0, 9]]))).solve()
        self.assertEqual(str(cm.exception), "P has both positive and negative eigenvalues.")

        P = [[4, 0], [0, 9]]
        p = Problem(Minimize(quad_form(self.x, P)), [self.x >= 1])
        result = p.solve()
        self.assertAlmostEqual(result, 13, places=3)

        c = [1,2]
        p = Problem(Minimize(quad_form(c, self.A)), [self.A >= 1])
        result = p.solve()
        self.assertAlmostEqual(result, 9)

        c = [1,2]
        P = [[4, 0], [0, 9]]
        p = Problem(Minimize(quad_form(c, P)))
        result = p.solve()
        self.assertAlmostEqual(result, 40)

    # Test combining atoms
    def test_mixed_atoms(self):
        p = Problem(Minimize(norm2(5 + norm1(self.z)
                                  + norm1(self.x) +
                                  normInf(self.x - self.z) ) ),
            [self.x >= [2,3], self.z <= [-1,-4], norm2(self.x + self.z) <= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 22)
        self.assertItemsAlmostEqual(self.x.value, [2,3])
        self.assertItemsAlmostEqual(self.z.value, [-1,-4])

    # Test multiplying by constant atoms.
    def test_mult_constant_atoms(self):
        p = Problem(Minimize(norm2([3,4])*self.a), [self.a >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertAlmostEqual(self.a.value, 2)

    # Test recovery of dual variables.
    def test_dual_variables(self):
        p = Problem(Minimize( norm1(self.x + self.z) ),
            [self.x >= [2,3],
             [[1,2],[3,4]]*self.z == [-1,-4],
             norm2(self.x + self.z) <= 100])
        result = p.solve()
        self.assertAlmostEqual(result, 4)
        self.assertItemsAlmostEqual(self.x.value, [4,3])
        self.assertItemsAlmostEqual(self.z.value, [-4,1])
        # Dual values
        self.assertItemsAlmostEqual(p.constraints[0].dual_value, [0, 1])
        self.assertItemsAlmostEqual(p.constraints[1].dual_value, [-1, 0.5])
        self.assertAlmostEqual(p.constraints[2].dual_value, 0)

        T = matrix(2, (2, 3))
        c = matrix([3,4])
        p = Problem(Minimize(1),
            [self.A >= T*self.C,
             self.A == self.B,
             self.C == T.T])
        result = p.solve()
        # Dual values
        self.assertItemsAlmostEqual(p.constraints[0].dual_value, 4*[0])
        self.assertItemsAlmostEqual(p.constraints[1].dual_value, 4*[0])
        self.assertItemsAlmostEqual(p.constraints[2].dual_value, 6*[0])

    # Test problems with indexing.
    def test_indexing(self):
        # Vector variables
        p = Problem(Maximize(self.x[0,0]), [self.x[0,0] <= 2, self.x[1,0] == 3])
        result = p.solve()
        self.assertAlmostEqual(result, 2)
        self.assertItemsAlmostEqual(self.x.value, [2,3])

        n = 10
        A = matrix(range(n*n), (n,n))
        x = Variable(n,n)
        p = Problem(Minimize(sum_entries(x)), [x == A])
        result = p.solve()
        answer = n*n*(n*n+1)/2 - n*n
        self.assertAlmostEqual(result, answer)

        # Matrix variables
        p = Problem(Maximize( sum(self.A[i,i] + self.A[i,1-i] for i in range(2)) ),
                             [self.A <= [[1,-2],[-3,4]]])
        result = p.solve()
        self.assertAlmostEqual(result, 0)
        self.assertItemsAlmostEqual(self.A.value, [1,-2,-3,4])

        # Indexing arithmetic expressions.
        exp = [[1,2],[3,4]]*self.z + self.x
        p = Problem(Minimize(exp[1,0]), [self.x == self.z, self.z == [1,2]])
        result = p.solve()
        self.assertAlmostEqual(result, 12)
        self.assertItemsAlmostEqual(self.x.value, self.z.value)

    # Test problems with slicing.
    def test_slicing(self):
        p = Problem(Maximize(sum_entries(self.C)), [self.C[1:3,:] <= 2, self.C[0,:] == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(self.C.value, 2*[1,2,2])

        p = Problem(Maximize(sum_entries(self.C[0:3:2,1])),
            [self.C[1:3,:] <= 2, self.C[0,:] == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 3)
        self.assertItemsAlmostEqual(self.C.value[0:3:2,1], [1,2])

        p = Problem(Maximize(sum_entries( (self.C[0:2,:] + self.A)[:,0:2] )),
            [self.C[1:3,:] <= 2, self.C[0,:] == 1,
             (self.A + self.B)[:,0] == 3, (self.A + self.B)[:,1] == 2,
             self.B == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 12)
        self.assertItemsAlmostEqual(self.C.value[0:2,:], [1,2,1,2])
        self.assertItemsAlmostEqual(self.A.value, [2,2,1,1])

        p = Problem(Maximize( [[3],[4]]*(self.C[0:2,:] + self.A)[:,0] ),
            [self.C[1:3,:] <= 2, self.C[0,:] == 1,
             [[1],[2]]*(self.A + self.B)[:,0] == 3, (self.A + self.B)[:,1] == 2,
             self.B == 1, 3*self.A[:,0] <= 3])
        result = p.solve()
        self.assertAlmostEqual(result, 12)
        self.assertItemsAlmostEqual(self.C.value[0:2,0], [1,2])
        self.assertItemsAlmostEqual(self.A.value, [1,-.5,1,1])

        p = Problem(Minimize(norm2((self.C[0:2,:] + self.A)[:,0] )),
            [self.C[1:3,:] <= 2, self.C[0,:] == 1,
             (self.A + self.B)[:,0] == 3, (self.A + self.B)[:,1] == 2,
             self.B == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 3)
        self.assertItemsAlmostEqual(self.C.value[0:2,0], [1,-2])
        self.assertItemsAlmostEqual(self.A.value, [2,2,1,1])

        # Transpose of slice.
        p = Problem(Maximize(sum_entries(self.C)), [self.C[1:3,:].T <= 2, self.C[0,:].T == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(self.C.value, 2*[1,2,2])

    # Test the vstack atom.
    def test_vstack(self):
        c = matrix(1, (1,5))
        p = Problem(Minimize(c * vstack(self.x, self.y)),
            [self.x == [1,2],
            self.y == [3,4,5]])
        result = p.solve()
        self.assertAlmostEqual(result, 15)

        c = matrix(1, (1,4))
        p = Problem(Minimize(c * vstack(self.x, self.x)),
            [self.x == [1,2]])
        result = p.solve()
        self.assertAlmostEqual(result, 6)


        c = matrix(1, (2,2))
        p = Problem( Minimize( sum_entries(vstack(self.A, self.C)) ),
            [self.A >= 2*c,
            self.C == -2])
        result = p.solve()
        self.assertAlmostEqual(result, -4)

        c = matrix(1, (1,2))
        p = Problem( Minimize( sum_entries(vstack(c*self.A, c*self.B)) ),
            [self.A >= 2,
            self.B == -2])
        result = p.solve()
        self.assertAlmostEqual(result, 0)

        c = matrix([1,-1])
        p = Problem( Minimize( c.T * vstack(square(self.a), sqrt(self.b))),
            [self.a == 2,
             self.b == 16])
        with self.assertRaises(Exception) as cm:
            p.solve()
        self.assertEqual(str(cm.exception), "Problem does not follow DCP rules.")

    # Test the hstack atom.
    def test_hstack(self):
        c = matrix(1, (1,5))
        p = Problem(Minimize(c * hstack(self.x.T, self.y.T).T),
            [self.x == [1,2],
            self.y == [3,4,5]])
        result = p.solve()
        self.assertAlmostEqual(result, 15)

        c = matrix(1, (1,4))
        p = Problem(Minimize(c * hstack(self.x.T, self.x.T).T),
            [self.x == [1,2]])
        result = p.solve()
        self.assertAlmostEqual(result, 6)


        c = matrix(1, (2,2))
        p = Problem( Minimize( sum_entries(hstack(self.A.T, self.C.T)) ),
            [self.A >= 2*c,
            self.C == -2])
        result = p.solve()
        self.assertAlmostEqual(result, -4)

        c = matrix(1, (1,2))
        p = Problem( Minimize( sum_entries(hstack(c*self.A, c*self.B)) ),
            [self.A >= 2,
            self.B == -2])
        result = p.solve()
        self.assertAlmostEqual(result, 0)

        c = matrix([1,-1])
        p = Problem( Minimize( c.T * hstack(square(self.a).T, sqrt(self.b).T).T),
            [self.a == 2,
             self.b == 16])
        with self.assertRaises(Exception) as cm:
            p.solve()
        self.assertEqual(str(cm.exception), "Problem does not follow DCP rules.")

    # Test variable transpose.
    def test_transpose(self):
        p = Problem(Minimize(sum_entries(self.x)), [self.x.T >= matrix([1,2]).T])
        result = p.solve()
        self.assertAlmostEqual(result, 3)
        self.assertItemsAlmostEqual(self.x.value, [1,2])

        p = Problem(Minimize(sum_entries(self.C)), [matrix([1,1]).T*self.C.T >= matrix([0,1,2]).T])
        result = p.solve()
        value = self.C.value

        constraints = [1*self.C[i,0] + 1*self.C[i,1] >= i for i in range(3)]
        p = Problem(Minimize(sum_entries(self.C)), constraints)
        result2 = p.solve()
        self.assertAlmostEqual(result, result2)
        self.assertItemsAlmostEqual(self.C.value, value)

        p = Problem(Minimize(self.A[0,1] - self.A.T[1,0]),
                    [self.A == [[1,2],[3,4]]])
        result = p.solve()
        self.assertAlmostEqual(result, 0)

        exp = (-self.x).T
        p = Problem(Minimize(sum_entries(self.x)), [(-self.x).T <= 1])
        result = p.solve()
        self.assertAlmostEqual(result, -2)

        c = matrix([1,-1])
        p = Problem(Minimize(max_elemwise(c.T, 2, 2 + c.T)[1]))
        result = p.solve()
        self.assertAlmostEqual(result, 2)

        c = matrix([[1,-1,2],[1,-1,2]])
        p = Problem(Minimize(sum_entries(max_elemwise(c, 2, 2 + c).T[:,0])))
        result = p.solve()
        self.assertAlmostEqual(result, 6)

        c = matrix([[1,-1,2],[1,-1,2]])
        p = Problem(Minimize(sum_entries(square(c.T).T[:,0])))
        result = p.solve()
        self.assertAlmostEqual(result, 6)

        # Slice of transpose.
        p = Problem(Maximize(sum_entries(self.C)), [self.C.T[:,1:3] <= 2, self.C.T[:,0] == 1])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(self.C.value, 2*[1,2,2])

    # Test multiplication on the left by a non-constant.
    def test_multiplication_on_left(self):
        c = matrix([1,2])
        p = Problem(Minimize(c.T*self.A*c), [self.A >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 18)

        p = Problem(Minimize(self.a*2), [self.a >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 4)

        p = Problem(Minimize(self.x.T*c), [self.x >= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 6)

        p = Problem(Minimize((self.x.T + self.z.T)*c),
            [self.x >= 2, self.z >= 1])
        result = p.solve()
        self.assertAlmostEqual(result, 9)

    # Test redundant constraints in cvxopt.
    def test_redundant_constraints(self):
        obj = Minimize(sum_entries(self.x))
        constraints = [self.x == 2, self.x == 2, self.x.T == 2, self.x[0] == 2]
        p = Problem(obj, constraints)
        result = p.solve(solver=s.CVXOPT)
        self.assertAlmostEqual(result, 4)

        obj = Minimize(sum_entries(square(self.x)))
        constraints = [self.x == self.x]
        p = Problem(obj, constraints)
        result = p.solve(solver=s.CVXOPT)
        self.assertAlmostEqual(result, 0)

    # Test that symmetry is enforced.
    def test_sdp_symmetry(self):
        # TODO should these raise exceptions?
        # with self.assertRaises(Exception) as cm:
        #     lambda_max([[1,2],[3,4]])
        # self.assertEqual(str(cm.exception), "lambda_max called on non-symmetric matrix.")

        # with self.assertRaises(Exception) as cm:
        #     lambda_min([[1,2],[3,4]])
        # self.assertEqual(str(cm.exception), "lambda_min called on non-symmetric matrix.")

        p = Problem(Minimize(lambda_max(self.A)), [self.A >= 2])
        result = p.solve()
        self.assertItemsAlmostEqual(self.A.value, self.A.value.T)

        p = Problem(Minimize(lambda_max(self.A)), [self.A == [[1,2],[3,4]]])
        result = p.solve()
        self.assertEqual(p.status, s.INFEASIBLE)

    # Test SDP
    def test_sdp(self):
        # Ensure sdp constraints enforce transpose.
        obj = Maximize(self.A[1,0] - self.A[0,1])
        p = Problem(obj, [lambda_max(self.A) <= 100,
                          self.A[0,0] == 2,
                          self.A[1,1] == 2,
                          self.A[1,0] == 2])
        result = p.solve()
        self.assertAlmostEqual(result, 0)

    # Test getting values for expressions.
    def test_expression_values(self):
        diff_exp = self.x - self.z
        inf_exp = normInf(diff_exp)
        sum_entries_exp = 5 + norm1(self.z) + norm1(self.x) + inf_exp
        constr_exp = norm2(self.x + self.z)
        obj = norm2(sum_entries_exp)
        p = Problem(Minimize(obj),
            [self.x >= [2,3], self.z <= [-1,-4], constr_exp <= 2])
        result = p.solve()
        self.assertAlmostEqual(result, 22)
        self.assertItemsAlmostEqual(self.x.value, [2,3])
        self.assertItemsAlmostEqual(self.z.value, [-1,-4])
        # Expression values.
        self.assertItemsAlmostEqual(diff_exp.value, self.x.value - self.z.value)
        self.assertAlmostEqual(inf_exp.value,
            LA.norm(self.x.value - self.z.value, numpy.inf))
        self.assertAlmostEqual(sum_entries_exp.value,
            5 + LA.norm(self.z.value, 1) + LA.norm(self.x.value, 1) + \
            LA.norm(self.x.value - self.z.value, numpy.inf))
        self.assertAlmostEqual(constr_exp.value,
            LA.norm(self.x.value + self.z.value, 2))
        self.assertAlmostEqual(obj.value, result)

    def test_mult_by_zero(self):
        """Test multiplication by zero.
        """
        exp = 0*self.a
        self.assertEqual(exp.value, 0)
        obj = Minimize(exp)
        p = Problem(obj)
        result = p.solve()
        self.assertAlmostEqual(result, 0)
        assert self.a.value is not None

    def test_div(self):
        """Tests a problem with division.
        """
        obj = Minimize(normInf(self.A/5))
        p = Problem(obj, [self.A >= 5])
        result = p.solve()
        self.assertAlmostEqual(result, 1)

    def test_mul_elemwise(self):
        """Tests problems with mul_elemwise.
        """
        c = [[1, -1], [2, -2]]
        expr = mul_elemwise(c, self.A)
        obj = Minimize(normInf(expr))
        p = Problem(obj, [self.A == 5])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(expr.value, [5, -5] + [10, -10])

        # Test with a sparse matrix.
        import cvxopt
        interface = intf.get_matrix_interface(cvxopt.spmatrix)
        c = interface.const_to_matrix([1,2])
        expr = mul_elemwise(c, self.x)
        obj = Minimize(normInf(expr))
        p = Problem(obj, [self.x == 5])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(expr.value, [5, 10])

        # Test promotion.
        c = [[1, -1], [2, -2]]
        expr = mul_elemwise(c, self.a)
        obj = Minimize(normInf(expr))
        p = Problem(obj, [self.a == 5])
        result = p.solve()
        self.assertAlmostEqual(result, 10)
        self.assertItemsAlmostEqual(expr.value, [5, -5] + [10, -10])

    def test_invalid_solvers(self):
        """Tests that errors occur when you use an invalid solver.
        """
        with self.assertRaises(Exception) as cm:
            Problem(Minimize(-log(self.a))).solve(solver=s.ECOS)
        self.assertEqual(str(cm.exception),
            "The solver ECOS cannot solve the problem.")

        with self.assertRaises(Exception) as cm:
            Problem(Minimize(lambda_max(self.a))).solve(solver=s.ECOS)
        self.assertEqual(str(cm.exception),
            "The solver ECOS cannot solve the problem.")

        with self.assertRaises(Exception) as cm:
            Problem(Minimize(self.a)).solve(solver=s.SCS)
        self.assertEqual(str(cm.exception),
            "The solver SCS cannot solve the problem.")

    def test_reshape(self):
        """Tests problems with reshape.
        """
        # Test on scalars.
        self.assertEqual(reshape(1, 1, 1).value, 1)

        # Test vector to matrix.
        x = Variable(4)
        mat = matrix([[1,-1], [2, -2]])
        vec = matrix([1, 2, 3, 4])
        vec_mat = matrix([[1, 2], [3, 4]])
        expr = reshape(x, 2, 2)
        obj = Minimize(sum_entries(mat*expr))
        prob = Problem(obj, [x == vec])
        result = prob.solve()
        self.assertAlmostEqual(result, sum(mat*vec_mat))

        # Test on matrix to vector.
        c = [1, 2, 3, 4]
        expr = reshape(self.A, 4, 1)
        obj = Minimize(expr.T*c)
        constraints = [self.A == [[-1, -2], [3, 4]]]
        prob = Problem(obj, constraints)
        result = prob.solve()
        self.assertAlmostEqual(result, 20)
        self.assertItemsAlmostEqual(expr.value, [-1, -2, 3, 4])
        self.assertItemsAlmostEqual(reshape(expr, 2, 2).value, [-1, -2, 3, 4])

        # Test matrix to matrix.
        expr = reshape(self.C, 2, 3)
        mat = numpy.matrix([[1,-1], [2, -2]])
        C_mat = numpy.matrix([[1, 4], [2, 5], [3, 6]])
        obj = Minimize(sum_entries(mat*expr))
        prob = Problem(obj, [self.C == C_mat])
        result = prob.solve()
        reshaped = numpy.reshape(C_mat, (2, 3), 'F')
        self.assertAlmostEqual(result, (mat.dot(reshaped)).sum())
        self.assertItemsAlmostEqual(expr.value, C_mat)

        # Test promoted expressions.
        c = matrix([[1,-1], [2, -2]])
        expr = reshape(c*self.a, 1, 4)
        obj = Minimize(expr*[1, 2, 3, 4])
        prob = Problem(obj, [self.a == 2])
        result = prob.solve()
        self.assertAlmostEqual(result, -6)
        self.assertItemsAlmostEqual(expr.value, 2*c)

        expr = reshape(c*self.a, 4, 1)
        obj = Minimize(expr.T*[1, 2, 3, 4])
        prob = Problem(obj, [self.a == 2])
        result = prob.solve()
        self.assertAlmostEqual(result, -6)
        self.assertItemsAlmostEqual(expr.value, 2*c)

########NEW FILE########
__FILENAME__ = test_scs
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
import cvxpy.atoms.elementwise.log as cvxlog
from base_test import BaseTest
import cvxopt
import unittest
import math
import numpy as np

class TestSCS(BaseTest):
    """ Unit tests for the nonlinear atoms module. """
    def setUp(self):
        self.x = Variable(2, name='x')
        self.y = Variable(2, name='y')

        self.A = Variable(2,2,name='A')
        self.B = Variable(2,2,name='B')
        self.C = Variable(3,2,name='C')

    # Overriden method to assume lower accuracy.
    def assertItemsAlmostEqual(self, a, b, places=2):
        super(TestSCS, self).assertItemsAlmostEqual(a,b,places=places)

    # Overriden method to assume lower accuracy.
    def assertAlmostEqual(self, a, b, places=2):
        super(TestSCS, self).assertAlmostEqual(a, b, places=places)

    # def test_log(self):
    #     """ Test that minimize -sum(log(x)) s.t. x <= 1 yields 0.

    #         Rewritten by hand.

    #         neg_log_func implements

    #             t1 - log(t2) <= 0

    #         Implemented as

    #             minimize [-1,-1,0,0] * [t1; t2]
    #                 t1 - log(t2) <= 0
    #                 [0 0 -1 0;
    #                  0 0 0 -1] * [t1; t2] <= [-1; -1]
    #     """
    #     F = cvxlog.neg_log_func(2)
    #     h = cvxopt.matrix([1.,1.])
    #     G = cvxopt.spmatrix([1.,1.], [0,1], [2,3], (2,4), tc='d')
    #     sol = cvxopt.solver.cpl(cvxopt.matrix([-1.0,-1.0,0,0]), F, G, h)

    #     self.assertEqual(sol['status'], 'optimal')
    #     self.assertAlmostEqual(sol['x'][0], 0.)
    #     self.assertAlmostEqual(sol['x'][1], 0.)
    #     self.assertAlmostEqual(sol['x'][2], 1.)
    #     self.assertAlmostEqual(sol['x'][3], 1.)
    #     self.assertAlmostEqual(sol['primal objective'], 0.0)

    def test_log_problem(self):
        # Log in objective.
        obj = Maximize(sum_entries(log(self.x)))
        constr = [self.x <= [1, math.e]]
        p = Problem(obj, constr)
        result = p.solve(solver=SCS)
        self.assertAlmostEqual(result, 1)
        self.assertItemsAlmostEqual(self.x.value, [1, math.e])

        # Log in constraint.
        obj = Minimize(sum_entries(self.x))
        constr = [log(self.x) >= 0, self.x <= [1,1]]
        p = Problem(obj, constr)
        result = p.solve(solver=SCS)
        self.assertAlmostEqual(result, 2)
        self.assertItemsAlmostEqual(self.x.value, [1,1])

        # Index into log.
        obj = Maximize(log(self.x)[1])
        constr = [self.x <= [1, math.e]]
        p = Problem(obj,constr)
        result = p.solve(solver=SCS)
        self.assertAlmostEqual(result, 1)

    def test_entr(self):
        """Test the entr atom.
        """
        self.assertEqual(entr(0).value, 0)
        assert np.isneginf(entr(-1).value)

    def test_kl_div(self):
        """Test a problem with kl_div.
        """
        import numpy as np
        import cvxpy as cp

        kK=50
        kSeed=10

        prng=np.random.RandomState(kSeed)
        #Generate a random reference distribution
        npSPriors=prng.uniform(0.0,1.0,kK)
        npSPriors=npSPriors/sum(npSPriors)

        #Reference distribution
        p_refProb=cp.Parameter(kK,1,sign='positive')
        #Distribution to be estimated
        v_prob=cp.Variable(kK,1)
        objkl=0.0
        for k in xrange(kK):
            objkl += cp.kl_div(v_prob[k,0],p_refProb[k,0])

        constrs=[sum([v_prob[k,0] for k in xrange(kK)])==1]
        klprob=cp.Problem(cp.Minimize(objkl),constrs)
        p_refProb.value=npSPriors
        result = klprob.solve(solver=SCS, verbose=True)
        self.assertItemsAlmostEqual(v_prob.value, npSPriors)

    def test_entr(self):
        """Test a problem with entr.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Maximize(sum_entries(entr(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])

    def test_exp(self):
        """Test a problem with exp.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Minimize(sum_entries(exp(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])

    def test_log(self):
        """Test a problem with log.
        """
        for n in [5, 10, 25]:
            print n
            x = Variable(n)
            obj = Maximize(sum_entries(log(x)))
            p = Problem(obj, [sum_entries(x) == 1])
            p.solve(solver=SCS, verbose=True)
            self.assertItemsAlmostEqual(x.value, n*[1./n])

    def test_consistency(self):
        """Test case for non-deterministic behavior in cvxopt.
        """
        import cvxpy

        xs = [0, 1, 2, 3]
        ys = [51, 60, 70, 75]

        eta1 = cvxpy.Variable()
        eta2 = cvxpy.Variable()
        eta3 = cvxpy.Variable()
        theta1s = [eta1 + eta3*x for x in xs]
        lin_parts = [theta1 * y + eta2 * y**2 for (theta1, y) in zip(theta1s, ys)]
        g_parts = [-cvxpy.quad_over_lin(theta1, -4*eta2) + 0.5 * cvxpy.log(-2 * eta2)
                   for theta1 in theta1s]
        objective = reduce(lambda x,y: x+y, lin_parts + g_parts)
        problem = cvxpy.Problem(cvxpy.Maximize(objective))
        problem.solve(verbose=True, solver=cvxpy.SCS)
        assert problem.status == cvxpy.OPTIMAL, problem.status
        return [eta1.value, eta2.value, eta3.value]

    # def test_kl_div(self):
    #     """Test the kl_div atom.
    #     """
    #     self.assertEqual(kl_div(0, 0).value, 0)
    #     self.assertEqual(kl_div(1, 0).value, np.inf)
    #     self.assertEqual(kl_div(0, 1).value, np.inf)
    #     self.assertEqual(kl_div(-1, -1).value, np.inf)


########NEW FILE########
__FILENAME__ = test_semidefinite_vars
"""
Copyright 2013 Steven Diamond, Eric Chu

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
from cvxpy.expressions.variables import semidefinite
from cvxopt import matrix
import numpy as np
from base_test import BaseTest
import unittest

def diag(X):
    """ Get the diagonal elements of a matrix.

        ECHU: Not sure if we implemented this somewhere already.
    """
    for i in X.size[0]:
        yield X[i,i]

def trace(X):
    """ Compute the trace of a matrix.

        ECHU: Not sure if we implemented this somewhere already.
    """
    return sum(diag(X))


class TestSemidefiniteVariable(BaseTest):
    """ Unit tests for the expressions/shape module. """
    def setUp(self):
        self.X = semidefinite(2)
        self.Y = Variable(2,2)
        self.F = matrix([[1,0],[0,-1]], tc='d')

    def test_sdp_problem(self):
        # SDP in objective.
        obj = Minimize(sum_entries(square(self.X - self.F)))
        p = Problem(obj,[])
        result = p.solve()
        self.assertAlmostEqual(result, 1)

        self.assertAlmostEqual(self.X.value[0,0], 1, places=3)
        self.assertAlmostEqual(self.X.value[0,1], 0)
        self.assertAlmostEqual(self.X.value[1,0], 0)
        self.assertAlmostEqual(self.X.value[1,1], 0)

        # SDP in constraint.
        # ECHU: note to self, apparently this is a source of redundancy
        obj = Minimize(sum_entries(square(self.Y - self.F)))
        p = Problem(obj, [self.Y == semidefinite(2)])
        result = p.solve()
        self.assertAlmostEqual(result, 1)

        self.assertAlmostEqual(self.Y.value[0,0], 1, places=4)
        self.assertAlmostEqual(self.Y.value[0,1], 0)
        self.assertAlmostEqual(self.Y.value[1,0], 0)
        self.assertAlmostEqual(self.Y.value[1,1], 0)

        # Index into semidef.
        obj = obj = Minimize(square(self.X[0,0] - 1) +
                             square(self.X[1,0] - 2) +
                             square(self.X[0,1] - 3) +
                             square(self.X[1,1] - 4))
        p = Problem(obj,[])
        result = p.solve()
        print self.X.value
        self.assertAlmostEqual(result, 0)

        self.assertAlmostEqual(self.X.value[0,0], 1, places=4)
        self.assertAlmostEqual(self.X.value[0,1], 3, places=4)
        self.assertAlmostEqual(self.X.value[1,0], 2, places=3)
        self.assertAlmostEqual(self.X.value[1,1], 4, places=4)

########NEW FILE########
__FILENAME__ = test_shape
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.expressions.variables import Variable
from cvxpy.utilities import Shape
import unittest

class TestShape(unittest.TestCase):
    """ Unit tests for the expressions/shape module. """
    def setUp(self):
        pass

    # Test the size method.
    def test_size(self):
        self.assertEqual(Shape(1,3).size, (1,3))
        self.assertEqual(Shape(2,1).size, (2,1))

    # Test adding two shapes.
    def test_add(self):
        self.assertEqual((Shape(3,4) + Shape(3,4)).size, (3,4))

        with self.assertRaises(Exception) as cm:
            (Shape(1,3) + Shape(4,3))
        self.assertEqual(str(cm.exception), "Incompatible dimensions (1, 3) (4, 3)")

        # Promotion
        self.assertEqual((Shape(3,4) + Shape(1,1)).size, (3,4))
        self.assertEqual((Shape(1,1) + Shape(3,4)).size, (3,4))

    # Test multiplying two shapes.
    def test_mul(self):
        self.assertEqual((Shape(5,9) * Shape(9,2)).size, (5,2))

        with self.assertRaises(Exception) as cm:
            (Shape(5,3) * Shape(9,2))
        self.assertEqual(str(cm.exception), "Incompatible dimensions (5, 3) (9, 2)")

        # Promotion
        self.assertEqual((Shape(3,4) * Shape(1,1)).size, (3,4))
        self.assertEqual((Shape(1,1) * Shape(3,4)).size, (3,4))
########NEW FILE########
__FILENAME__ = test_sign
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities import Sign
from nose.tools import *

class TestSign(object):
  """ Unit tests for the expression/sign class. """
  @classmethod
  def setup_class(self):
      pass

  def test_add(self):
      assert_equals(Sign.POSITIVE + Sign.NEGATIVE, Sign.UNKNOWN)
      assert_equals(Sign.NEGATIVE + Sign.ZERO, Sign.NEGATIVE)
      assert_equals(Sign.POSITIVE + Sign.POSITIVE, Sign.POSITIVE)
      assert_equals(Sign.UNKNOWN + Sign.ZERO, Sign.UNKNOWN)

  def test_sub(self):
      assert_equals(Sign.POSITIVE - Sign.NEGATIVE, Sign.POSITIVE)
      assert_equals(Sign.NEGATIVE - Sign.ZERO, Sign.NEGATIVE)
      assert_equals(Sign.POSITIVE - Sign.POSITIVE, Sign.UNKNOWN)

  def test_mult(self):
      assert_equals(Sign.ZERO * Sign.POSITIVE, Sign.ZERO)
      assert_equals(Sign.UNKNOWN * Sign.POSITIVE, Sign.UNKNOWN)
      assert_equals(Sign.POSITIVE * Sign.NEGATIVE, Sign.NEGATIVE)
      assert_equals(Sign.NEGATIVE * Sign.NEGATIVE, Sign.POSITIVE)
      assert_equals(Sign.ZERO * Sign.UNKNOWN, Sign.ZERO)

  def test_neg(self):
      assert_equals(-Sign.ZERO, Sign.ZERO)
      assert_equals(-Sign.POSITIVE, Sign.NEGATIVE)

  # Tests the is_positive and is_negative methods.
  def test_is_sign(self):
      assert Sign.POSITIVE.is_positive()
      assert not Sign.NEGATIVE.is_positive()
      assert not Sign.UNKNOWN.is_positive()
      assert Sign.ZERO.is_positive()

      assert not Sign.POSITIVE.is_negative()
      assert Sign.NEGATIVE.is_negative()
      assert not Sign.UNKNOWN.is_negative()
      assert Sign.ZERO.is_negative()

      assert Sign.ZERO.is_zero()
      assert not Sign.NEGATIVE.is_zero()

      assert Sign.UNKNOWN.is_unknown()

########NEW FILE########
__FILENAME__ = test_singular_quad_form
from __future__ import division, print_function, absolute_import

import numpy as np
from numpy.testing import assert_allclose, assert_equal
from scipy import linalg
import cvxpy

def test_singular_quad_form():
    # Solve a quadratic program.
    np.random.seed(1234)
    for n in (3, 4, 5):
        for i in range(5):

            # construct a random 1d finite distribution
            v = np.exp(np.random.randn(n))
            v = v / np.sum(v)

            # construct a random positive definite matrix
            A = np.random.randn(n, n)
            Q = np.dot(A, A.T)

            # Project onto the orthogonal complement of v.
            # This turns Q into a singular matrix with a known nullspace.
            E = np.identity(n) - np.outer(v, v) / np.inner(v, v)
            Q = np.dot(E, np.dot(Q, E.T))
            observed_rank = np.linalg.matrix_rank(Q)
            desired_rank = n-1
            yield assert_equal, observed_rank, desired_rank

            for action in 'minimize', 'maximize':

                # Look for the extremum of the quadratic form
                # under the simplex constraint.
                x = cvxpy.Variable(n)
                if action == 'minimize':
                    q = cvxpy.quad_form(x, Q)
                    objective = cvxpy.Minimize(q)
                elif action == 'maximize':
                    q = cvxpy.quad_form(x, -Q)
                    objective = cvxpy.Maximize(q)
                constraints = [0 <= x, cvxpy.sum_entries(x) == 1]
                p = cvxpy.Problem(objective, constraints)
                p.solve()

                # check that cvxpy found the right answer
                xopt = x.value.A.flatten()
                yopt = np.dot(xopt, np.dot(Q, xopt))
                assert_allclose(yopt, 0, atol=1e-3)
                assert_allclose(xopt, v, atol=1e-3)

########NEW FILE########
__FILENAME__ = test_tree_mat
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
import cvxpy.settings as s
from cvxpy.lin_ops.tree_mat import mul, tmul, prune_constants
import cvxpy.problems.iterative as iterative
import numpy as np
import scipy.sparse as sp
import scipy.linalg as LA
import unittest
from base_test import BaseTest

class test_tree_mat(BaseTest):
    """ Unit tests for the matrix ops with expression trees. """

    def test_mul(self):
        """Test the mul method.
        """
        n = 2
        ones = np.mat(np.ones((n, n)))
        # Multiplication
        x = Variable(n, n)
        A = np.matrix("1 2; 3 4")
        expr = (A*x).canonical_form[0]

        val_dict = {x.id: ones}

        result = mul(expr, val_dict)
        assert (result == A*ones).all()

        result_dict = tmul(expr, result)
        assert (result_dict[x.id] == A.T*A*ones).all()

        # Multiplication with promotion.
        t = Variable()
        A = np.matrix("1 2; 3 4")
        expr = (A*t).canonical_form[0]

        val_dict = {t.id: 2}

        result = mul(expr, val_dict)
        assert (result == A*2).all()

        result_dict = tmul(expr, result)
        total = 0
        for i in range(A.shape[0]):
            for j in range(A.shape[1]):
                total += A[i, j]*result[i, j]
        assert (result_dict[t.id] == total)

        # Addition
        y = Variable(n, n)
        expr = (y + A*x).canonical_form[0]
        val_dict = {x.id: np.ones((n, n)),
                    y.id: np.ones((n, n))}

        result = mul(expr, val_dict)
        assert (result == A*ones + ones).all()

        result_dict = tmul(expr, result)
        assert (result_dict[y.id] == result).all()
        assert (result_dict[x.id] == A.T*result).all()

        val_dict = {x.id: A,
                    y.id: A}

        # Indexing
        expr = (x[:, 0] + y[:, 1]).canonical_form[0]
        result = mul(expr, val_dict)
        assert (result == A[:, 0] + A[:, 1]).all()

        result_dict = tmul(expr, result)
        mat = ones
        mat[:, 0] = result
        mat[:, 1] = 0
        assert (result_dict[x.id] == mat).all()

        # Negation
        val_dict = {x.id: A}
        expr = (-x).canonical_form[0]

        result = mul(expr, val_dict)
        assert (result == -A).all()

        result_dict = tmul(expr, result)
        assert (result_dict[x.id] == A).all()

        # Transpose
        expr = x.T.canonical_form[0]
        val_dict = {x.id: A}
        result = mul(expr, val_dict)
        assert (result == A.T).all()
        result_dict = tmul(expr, result)
        assert (result_dict[x.id] == A).all()

        # Convolution
        x = Variable(3)
        f = np.array([1, 2, 3])
        g = np.array([0, 1, 0.5])
        f_conv_g = np.array([ 0., 1., 2.5,  4., 1.5])
        expr = conv(f, x).canonical_form[0]
        val_dict = {x.id: g}
        result = mul(expr, val_dict)
        self.assertItemsAlmostEqual(result, f_conv_g)
        value = np.array(range(5))
        result_dict = tmul(expr, value)
        toep = LA.toeplitz(np.array([1,0,0]),
                           np.array([1, 2, 3, 0, 0]))
        x_val = toep.dot(value)
        self.assertItemsAlmostEqual(result_dict[x.id], x_val)

    def test_prune_constants(self):
        """Test pruning constants from constraints.
        """
        x = Variable(2)
        A = np.matrix("1 2; 3 4")
        constraints = (A*x <= 2).canonical_form[1]
        pruned = prune_constants(constraints)
        prod = mul(pruned[0].expr, {})
        self.assertItemsAlmostEqual(prod, np.zeros(A.shape[0]))

        # Test no-op
        constraints = (0*x <= 2).canonical_form[1]
        pruned = prune_constants(constraints)
        prod = mul(pruned[0].expr, {x.id: 1})
        self.assertItemsAlmostEqual(prod, np.zeros(A.shape[0]))

    def test_mul_funcs(self):
        """Test functions to multiply by A, A.T
        """
        n = 10
        x = Variable(n)
        obj = Minimize(norm(x, 1))
        constraints = [x >= 2]
        prob = Problem(obj, constraints)
        data, dims = prob.get_problem_data(solver=SCS)
        A = data["A"]
        objective, constr_map = prob.canonicalize()
        dims = prob._format_for_solver(constr_map, SCS)

        all_ineq = constr_map[s.EQ] + constr_map[s.LEQ]
        var_offsets, var_sizes, x_length = prob._get_var_offsets(objective,
                                                                 all_ineq)
        opts = {}
        constraints = constr_map[s.EQ] + constr_map[s.LEQ]
        constraints = prune_constants(constraints)
        Amul, ATmul = iterative.get_mul_funcs(constraints, dims,
                                              var_offsets, var_sizes,
                                              x_length)
        vec = np.array(range(x_length))
        # A*vec
        result = np.zeros(A.shape[0])
        Amul(vec, result)
        self.assertItemsAlmostEqual(A*vec, result)
        Amul(vec, result)
        self.assertItemsAlmostEqual(2*A*vec, result)
        # A.T*vec
        vec = np.array(range(A.shape[0]))
        result = np.zeros(A.shape[1])
        ATmul(vec, result)
        self.assertItemsAlmostEqual(A.T*vec, result)
        ATmul(vec, result)
        self.assertItemsAlmostEqual(2*A.T*vec, result)

########NEW FILE########
__FILENAME__ = canonical
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import performance_utils as pu

class Canonical(object):
    """
    An interface for objects that can be canonicalized.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        return NotImplemented

    @pu.lazyprop
    def canonical_form(self):
        """The graph implementation of the object stored as a property.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        return self.canonicalize()

    @abc.abstractmethod
    def variables(self):
        """The object's internal variables.

        Returns:
            A list of Variable objects.
        """
        return NotImplemented

    @abc.abstractmethod
    def parameters(self):
        """The object's internal parameters.

        Returns:
            A list of Parameter objects.
        """
        return NotImplemented

########NEW FILE########
__FILENAME__ = curvature
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities.error import Error

class Curvature(object):
    """Curvature for a convex optimization expression.

    Attributes:
        curvature_str: A string representation of the curvature.
    """
    CONSTANT_KEY = 'CONSTANT'
    AFFINE_KEY = 'AFFINE'
    CONVEX_KEY = 'CONVEX'
    CONCAVE_KEY = 'CONCAVE'
    UNKNOWN_KEY = 'UNKNOWN'

    # List of valid curvature strings.
    CURVATURE_STRINGS = [CONSTANT_KEY, AFFINE_KEY, CONVEX_KEY,
                         CONCAVE_KEY, UNKNOWN_KEY]
    # For multiplying curvature by negative sign.
    NEGATION_MAP = {CONVEX_KEY: CONCAVE_KEY, CONCAVE_KEY: CONVEX_KEY}

    def __init__(self, curvature_str):
        """Converts a curvature name to a Curvature object.

        Args:
            curvature_str: A key in the CURVATURE_MAP.

        Returns:
            A Curvature initialized with the selected value from CURVATURE_MAP.
        """
        curvature_str = curvature_str.upper()
        if curvature_str in Curvature.CURVATURE_STRINGS:
            self.curvature_str = curvature_str
        else:
            raise Error("'%s' is not a valid curvature name." %
                        str(curvature_str))

    def __repr__(self):
        return "Curvature('%s')" % self.curvature_str

    def __str__(self):
        return self.curvature_str

    def is_constant(self):
        """Is the expression constant?
        """
        return self == Curvature.CONSTANT

    def is_affine(self):
        """Is the expression affine?
        """
        return self.is_constant() or self == Curvature.AFFINE

    def is_convex(self):
        """Is the expression convex?
        """
        return self.is_affine() or self == Curvature.CONVEX

    def is_concave(self):
        """Is the expression concave?
        """
        return self.is_affine() or self == Curvature.CONCAVE

    def is_unknown(self):
        """Is the expression unknown curvature?
        """
        return self == Curvature.UNKNOWN

    def is_dcp(self):
        """Is the expression DCP compliant? (i.e., no unknown curvatures).
        """
        return not self.is_unknown()

    def __add__(self, other):
        """Handles the logic of adding curvatures.

        Cases:
          CONSTANT + ANYTHING = ANYTHING
          AFFINE + NONCONSTANT = NONCONSTANT
          CONVEX + CONCAVE = UNKNOWN
          SAME + SAME = SAME

        Args:
            self: The Curvature of the left-hand summand.
            other: The Curvature of the right-hand summand.

        Returns:
            The Curvature of the sum.
        """
        if self.is_constant():
            return other
        elif self.is_affine() and other.is_affine():
            return Curvature.AFFINE
        elif self.is_convex() and other.is_convex():
            return Curvature.CONVEX
        elif self.is_concave() and other.is_concave():
            return Curvature.CONCAVE
        else:
            return Curvature.UNKNOWN

    def __sub__(self, other):
        return self + -other

    @staticmethod
    def sign_mul(sign, curv):
        """Handles logic of sign by curvature multiplication.

        Cases:
            ZERO * ANYTHING = CONSTANT
            NON-ZERO * AFFINE/CONSTANT = AFFINE/CONSTANT
            UNKNOWN * NON-AFFINE = UNKNOWN
            POSITIVE * ANYTHING = ANYTHING
            NEGATIVE * CONVEX = CONCAVE
            NEGATIVE * CONCAVE = CONVEX

        Args:
            sign: The Sign of the left-hand multiplier.
            curv: The Curvature of the right-hand multiplier.

        Returns:
            The Curvature of the product.
        """
        if sign.is_zero():
            return Curvature.CONSTANT
        elif sign.is_positive() or curv.is_affine():
            return curv
        elif sign.is_negative():
            curvature_str = Curvature.NEGATION_MAP.get(curv.curvature_str,
                                                       curv.curvature_str)
            return Curvature(curvature_str)
        else: # sign is unknown.
            return Curvature.UNKNOWN

    def __neg__(self):
        """Equivalent to NEGATIVE * self.
        """
        curvature_str = Curvature.NEGATION_MAP.get(self.curvature_str,
                                                   self.curvature_str)
        return Curvature(curvature_str)

    def __eq__(self, other):
        """Are the two curvatures equal?
        """
        return self.curvature_str == other.curvature_str

    def __ne__(self, other):
        """Are the two curvatures not equal?
        """
        return self.curvature_str != other.curvature_str

# Class constants for all curvature types.
Curvature.CONSTANT = Curvature(Curvature.CONSTANT_KEY)
Curvature.AFFINE = Curvature(Curvature.AFFINE_KEY)
Curvature.CONVEX = Curvature(Curvature.CONVEX_KEY)
Curvature.CONCAVE = Curvature(Curvature.CONCAVE_KEY)
Curvature.UNKNOWN = Curvature(Curvature.UNKNOWN_KEY)
Curvature.NONCONVEX = Curvature(Curvature.UNKNOWN_KEY)

########NEW FILE########
__FILENAME__ = dcp_attr
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from curvature import Curvature
import key_utils as ku
from shape import Shape
from sign import Sign

class DCPAttr(object):
    """ A data structure for the sign, curvature, and shape of an expression.

    Attributes:
        sign: The signs of the entries in the matrix expression.
        curvature: The curvatures of the entries in the matrix expression.
        shape: The dimensions of the matrix expression.
    """

    def __init__(self, sign, curvature, shape):
        self.sign = sign
        self.curvature = curvature
        self.shape = shape

    def __add__(self, other):
        """Determines the DCP attributes of two expressions added together.

        Args:
            self: The DCPAttr of the left-hand expression.
            other: The DCPAttr of the right-hand expression.

        Returns:
            The DCPAttr of the sum.
        """
        shape = self.shape + other.shape
        sign = self.sign + other.sign
        curvature = self.curvature + other.curvature
        return DCPAttr(sign, curvature, shape)

    def __sub__(self, other):
        """Determines the DCP attributes of one expression minus another.

        Args:
            self: The DCPAttr of the left-hand expression.
            other: The DCPAttr of the right-hand expression.

        Returns:
            The DCPAttr of the difference.
        """
        shape = self.shape + other.shape
        sign = self.sign - other.sign
        curvature = self.curvature - other.curvature
        return DCPAttr(sign, curvature, shape)

    def __mul__(self, other):
        """Determines the DCP attributes of two expressions multiplied together.

        Assumes one of the arguments has constant curvature.

        Args:
            self: The DCPAttr of the left-hand expression.
            other: The DCPAttr of the right-hand expression.

        Returns:
            The DCPAttr of the product.
        """
        shape = self.shape * other.shape
        sign = self.sign * other.sign
        curvature = Curvature.sign_mul(self.sign, other.curvature)
        return DCPAttr(sign, curvature, shape)

    @staticmethod
    def mul_elemwise(lh_expr, rh_expr):
        """Determines the DCP attributes of expressions multiplied elementwise.

        Assumes the left-hand argument has constant curvature and both
        arguments have the same shape.

        Args:
            lh_expr: The DCPAttr of the left-hand expression.
            rh_expr: The DCPAttr of the right-hand expression.

        Returns:
            The DCPAttr of the product.
        """
        shape = lh_expr.shape + rh_expr.shape
        sign = lh_expr.sign * rh_expr.sign
        curvature = Curvature.sign_mul(lh_expr.sign, rh_expr.curvature)
        return DCPAttr(sign, curvature, shape)

    def __div__(self, other):
        """Determines the DCP attributes of one expression divided by another.

        Assumes one of the arguments has constant curvature.

        Args:
            self: The DCPAttr of the left-hand expression.
            other: The DCPAttr of the right-hand expression.

        Returns:
            The DCPAttr of the product.
        """
        return other*self

    def __neg__(self):
        """Determines the DCP attributes of a negated expression.
        """
        return DCPAttr(-self.sign, -self.curvature, self.shape)

########NEW FILE########
__FILENAME__ = error
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

class Error(Exception):
    """The exception type for the utilities module.
    """
    pass

########NEW FILE########
__FILENAME__ = key_utils
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Utility functions to handle indexing/slicing into an expression.

from error import Error

def validate_key(key, shape):
    """Check if the key is a valid index.

    Args:
        key: The key used to index/slice.
        shape: The shape of the expression.

    Returns:
        The key as a tuple of slices.

    Raises:
        Error: Index/slice out of bounds.
    """
    rows, cols = shape.size
    # Change single indexes for vectors into double indices.
    if not isinstance(key, tuple):
        if rows == 1:
            key = (slice(0, 1, None), key)
        elif cols == 1:
            key = (key, slice(0, 1, None))
        else:
            raise Error("Invalid index/slice.")
    # Change numbers into slices and ensure all slices have a start and step.
    key = tuple(format_slice(slice_) for slice_ in key)
    # Check that index is in bounds.
    if not (0 <= key[0].start and key[0].start < rows and \
            0 <= key[1].start and key[1].start < cols):

        raise Error("Index/slice out of bounds.")
    return key

def format_slice(key_val):
    """Converts part of a key into a slice with a start and step.

    Args:
        key_val: The value to convert into a slice.

    Returns:
        A slice with a start and step.
    """
    if isinstance(key_val, slice):
        start = key_val.start if key_val.start is not None else 0
        step = key_val.step if key_val.step is not None else 1
        return slice(start, key_val.stop, step)
    else:
        return slice(key_val, key_val+1, 1)

def index_to_slice(idx):
    """Converts an index to a slice.

    Args:
        idx: int
            The index.

    Returns:
    slice
        A slice equivalent to the index.
    """
    return slice(idx, idx+1, None)

def slice_to_str(slice_):
    """Converts a slice into a string.
    """
    if is_single_index(slice_):
        return str(slice_.start)
    stop = slice_.stop if slice_.stop is not None else ''
    if slice_.step != 1:
        return "%s:%s:%s" % (slice_.start, stop, slice_.step)
    else:
        return "%s:%s" % (slice_.start, stop)

def is_single_index(slice_):
    """Is the slice equivalent to a single index?
    """
    return slice_.stop is not None and \
    slice_.start + slice_.step >= slice_.stop

def get_stop(slice_, exp_dim):
    """Returns the stopping index for the slice applied to the expression.

    Args:
        slice_: A Slice into the expression.
        exp_dim: The length of the expression along the sliced dimension.

    Returns:
        The stopping index for the slice applied to the expression.
    """
    if slice_.stop is None:
        return exp_dim
    else:
        return min(slice_.stop, exp_dim)

def size(key, shape):
    """Finds the dimensions of a sliced expression.

    Args:
        key: The key used to index/slice.
        shape: The shape of the expression.

    Returns:
        The dimensions of the expression as (rows, cols).
    """
    dims = []
    for i in range(2):
        stop = get_stop(key[i], shape.size[i])
        dims.append(1 + (stop-1-key[i].start)/key[i].step)
    return tuple(dims)

def to_str(key):
    """Converts a key (i.e. two slices) into a string.
    """
    return (slice_to_str(key[0]), slice_to_str(key[1]))

########NEW FILE########
__FILENAME__ = monotonicity
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities.curvature import Curvature

INCREASING = 'INCREASING'
DECREASING = 'DECREASING'
SIGNED = 'SIGNED'
NONMONOTONIC = 'NONMONOTONIC'

def dcp_curvature(monotonicity, func_curvature, arg_sign, arg_curvature):
    """Applies DCP composition rules to determine curvature in each argument.

    Composition rules:
        Key: Function curvature + monotonicity + argument curvature
             == curvature in argument
        anything + anything + constant == constant
        anything + anything + affine == original curvature
        convex/affine + increasing + convex == convex
        convex/affine + decreasing + concave == convex
        concave/affine + increasing + concave == concave
        concave/affine + decreasing + convex == concave
    Notes: Increasing (decreasing) means non-decreasing (non-increasing).
           Any combinations not covered by the rules result in a
           nonconvex expression.

    Args:
        monotonicity: The monotonicity of the function in the given argument.
        func_curvature: The curvature of the function.
        arg_sign: The sign of the given argument.
        arg_curvature: The curvature of the given argument.

    Returns:
        The Curvature of the composition of function and arguments.
    """
    if arg_curvature.is_constant():
        result_curv = Curvature.CONSTANT
    elif arg_curvature.is_affine():
        result_curv = func_curvature
    elif monotonicity == INCREASING:
        result_curv = func_curvature + arg_curvature
    elif monotonicity == DECREASING:
        result_curv = func_curvature - arg_curvature
    # Absolute value style monotonicity.
    elif monotonicity == SIGNED and \
         func_curvature.is_convex():
        if (arg_curvature.is_convex() and arg_sign.is_positive()) or \
           (arg_curvature.is_concave() and arg_sign.is_negative()):
            result_curv = func_curvature
        else:
            result_curv = Curvature.UNKNOWN
    else: # non-monotonic
        result_curv = func_curvature + arg_curvature - arg_curvature

    return result_curv

########NEW FILE########
__FILENAME__ = ordered_set
"""Taken from http://code.activestate.com/recipes/576694/
"""

import collections
import itertools

class OrderedSet(collections.MutableSet):
    """A set with ordered keys.

    Backed by a map and linked list.
    """

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        """Adds the key to the set.

        Args:
            key: A hashable object.
        """
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def concat(self, other):
        """Concatenates two ordered sets.

        Args:
            other: An OrderedSet

        Returns:
            An OrderedSet with self's keys followed by other's keys.
        """
        return OrderedSet(itertools.chain(self, other))

    def discard(self, key):
        """Removes the key from the set.

        Preserves the order of the remaining keys.

        Args:
            key: A hashable object.
        """
        if key in self.map:
            key, prev, next_ = self.map.pop(key)
            prev[2] = next_
            next_[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        """Adds the key to the set.

        Args:
            last: If True returns the last element. If False returns the first.

        Returns:
            The last (or first) element in the set.
        """
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

########NEW FILE########
__FILENAME__ = performance_utils
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

# Taken from
# http://stackoverflow.com/questions/3012421/python-lazy-property-decorator

def lazyprop(func):
    """Wraps a property so it is lazily evaluated.

    Args:
        func: The property to wrap.

    Returns:
        A property that only does computation the first time it is called.
    """
    attr_name = '_lazy_' + func.__name__
    @property
    def _lazyprop(self):
        """A lazily evaluated propery.
        """
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazyprop

########NEW FILE########
__FILENAME__ = shape
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from error import Error

class Shape(object):
    """ Represents the dimensions of a matrix.

    Attributes:
        rows: The number of rows.
        cols: The number of columns.
    """

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        super(Shape, self).__init__()

    @property
    def size(self):
        """Getter for (rows, cols)
        """
        return (self.rows, self.cols)

    def __add__(self, other):
        """Determines the shape of two matrices added together.

        The expression's sizes must match unless one is a scalar,
        in which case it is promoted to the size of the other.

        Args:
            self: The shape of the left-hand matrix.
            other: The shape of the right-hand matrix.

        Returns:
            The shape of the matrix sum.

        Raises:
            Error: Incompatible dimensions.
        """
        if self.size == (1, 1):
            return other
        elif other.size == (1, 1):
            return self
        elif self.size == other.size:
            return self
        else:
            raise ValueError("Incompatible dimensions %s %s" % (self, other))

    def __sub__(self, other):
        """Same as add.
        """
        return self + other

    def __mul__(self, other):
        """Determines the shape of two matrices multiplied together.

        The left-hand columns must match the right-hand rows, unless
        one side is a scalar.

        Args:
            self: The shape of the left-hand matrix.
            other: The shape of the right-hand matrix.

        Returns:
            The shape of the matrix product.

        Raises:
            Error: Incompatible dimensions.
        """
        if self.size == (1, 1):
            return other
        elif other.size == (1, 1):
            return self
        elif self.cols == other.rows:
            return Shape(self.rows, other.cols)
        else:
            raise ValueError("Incompatible dimensions %s %s" % (self, other))

    def __div__(self, other):
        """Determines the shape of a matrix divided by a scalar.

        Args:
            self: The shape of the left-hand matrix.
            other: The shape of the right-hand scalar.

        Returns:
            The shape of the matrix division.
        """
        return self

    def __str__(self):
        return "(%s, %s)" % (self.rows, self.cols)

    def __repr__(self):
        return "Shape(%s, %s)" % (self.rows, self.cols)


########NEW FILE########
__FILENAME__ = sign
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy.utilities.error import Error

class Sign(object):
    """Sign of convex optimization expressions.

    Attributes:
        sign_str: A string representation of the sign.
    """
    POSITIVE_KEY = 'POSITIVE'
    NEGATIVE_KEY = 'NEGATIVE'
    UNKNOWN_KEY = 'UNKNOWN'
    ZERO_KEY = 'ZERO'

    # List of valid sign strings.
    SIGN_STRINGS = [POSITIVE_KEY, NEGATIVE_KEY, UNKNOWN_KEY, ZERO_KEY]

    def __init__(self, sign_str):
        sign_str = sign_str.upper()
        if sign_str in Sign.SIGN_STRINGS:
            self.sign_str = sign_str
        else:
            raise Error("'%s' is not a valid sign name." % str(sign_str))

    @staticmethod
    def val_to_sign(val):
        """Converts a number to a sign.

        Args:
            val: A scalar.

        Returns:
            The Sign of val.
        """
        if val > 0:
            return Sign.POSITIVE
        elif val == 0:
            return Sign.ZERO
        else:
            return Sign.NEGATIVE

    def is_zero(self):
        """Is the expression all zero?
        """
        return self == Sign.ZERO

    def is_positive(self):
        """Is the expression positive?
        """
        return self.is_zero() or self == Sign.POSITIVE

    def is_negative(self):
        """Is the expression negative?
        """
        return self.is_zero() or self == Sign.NEGATIVE

    def is_unknown(self):
        """Is the expression sign unknown?
        """
        return self == Sign.UNKNOWN

    # Arithmetic operators
    def __add__(self, other):
        """Handles the logic of adding signs.

        Cases:
            ZERO + ANYTHING = ANYTHING
            UNKNOWN + ANYTHING = UNKNOWN
            POSITIVE + NEGATIVE = UNKNOWN
            SAME + SAME = SAME

        Args:
            self: The Sign of the left-hand summand.
            other: The Sign of the right-hand summand.

        Returns:
            The Sign of the sum.
        """
        if self.is_zero():
            return other
        elif self == Sign.POSITIVE and other.is_positive():
            return self
        elif self == Sign.NEGATIVE and other.is_negative():
            return self
        else:
            return Sign.UNKNOWN

    def __sub__(self, other):
        return self + -other

    def __mul__(self, other):
        """Handles logic of multiplying signs.

        Cases:
            ZERO * ANYTHING = ZERO
            UNKNOWN * NON-ZERO = UNKNOWN
            POSITIVE * NEGATIVE = NEGATIVE
            POSITIVE * POSITIVE = POSITIVE
            NEGATIVE * NEGATIVE = POSITIVE

        Args:
            self: The Sign of the left-hand multiplier.
            other: The Sign of the right-hand multiplier.

        Returns:
            The Sign of the product.
        """
        if self == Sign.ZERO or other == Sign.ZERO:
            return Sign.ZERO
        elif self == Sign.UNKNOWN or other == Sign.UNKNOWN:
            return Sign.UNKNOWN
        elif self != other:
            return Sign.NEGATIVE
        else:
            return Sign.POSITIVE

    def __neg__(self):
        """Equivalent to NEGATIVE * self.
        """
        return self * Sign.NEGATIVE

    def __eq__(self, other):
        """Checks equality of arguments' attributes.
        """
        return self.sign_str == other.sign_str

    # To string methods.
    def __repr__(self):
        return "Sign('%s')" % self.sign_str

    def __str__(self):
        return self.sign_str

# Class constants for all sign types.
Sign.POSITIVE = Sign(Sign.POSITIVE_KEY)
Sign.NEGATIVE = Sign(Sign.NEGATIVE_KEY)
Sign.ZERO = Sign(Sign.ZERO_KEY)
Sign.UNKNOWN = Sign(Sign.UNKNOWN_KEY)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# CVXPY documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 27 20:47:07 2014.
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
# To import CVXPY:
sys.path.insert(0, os.path.abspath('../..'))
# To import sphinx extensions we've put in the repository:
sys.path.insert(0, os.path.abspath('../sphinxext'))

__version__ = "0.2.0"

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosummary',
'sphinx.ext.doctest', 'sphinx.ext.mathbase',
'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage',
'sphinx.ext.mathjax', 'sphinx.ext.viewcode', 'numpydoc']

# To suppress autodoc/numpydoc warning.
# http://stackoverflow.com/questions/12206334/sphinx-autosummary-toctree-contains-reference-to-nonexisting-document-warnings
numpydoc_show_class_members = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'CVXPY'
copyright = u'2014, Steve Diamond, Eric Chu, Stephen Boyd'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '.'.join(__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags.
release = __version__

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
exclude_patterns = []

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
import alabaster

table_styling_embed_css = False

html_theme_path = [alabaster.get_path(), "../themes"]
extensions += ['alabaster']
html_theme = 'cvxpy_alabaster'
html_sidebars = {
   '**': [
       'about.html', 'navigation.html', 'searchbox.html',
   ]
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
   'github_user': 'cvxgrp',
   'github_repo': 'cvxpy',
   'github_banner': True,
   'travis_button': True,
   'analytics_id': 'UA-50248335-1',
}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = ['../themes']

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
htmlhelp_basename = 'cvxpydoc'


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
  ('index', 'cvxpy.tex', u'CVXPY Documentation',
   u'Steven Diamond, Eric Chu, Stephen Boyd', 'manual'),
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
    ('index', 'cvxpy', u'CVXPY Documentation',
     [u'Steven Diamond, Eric Chu, Stephen Boyd'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'cvxpy', u'CVXPY Documentation',
   u'Steven Diamond, Eric Chu, Stephen Boyd', 'CVXPY', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = docscrape
"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
import pydoc
from StringIO import StringIO
from warnings import warn

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self, docstring, config={}):
        docstring = textwrap.dedent(docstring).split('\n')

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': [''],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Attributes': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'Warnings': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            warn("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ---------- or ==========
        return l2.startswith('-'*len(l1)) or l2.startswith('='*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            desc = dedent_lines(desc)

            params.append((arg_name,arg_type,desc))

        return params


    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)
    def _parse_see_also(self, content):
        """
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []

        for line in content:
            if not line.strip(): continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)
        return items

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse_summary(self):
        """Grab signature (if given) and summary"""
        if self._is_at_section():
            return

        summary = self._doc.read_to_next_empty_line()
        summary_str = " ".join([s.strip() for s in summary]).strip()
        if re.compile('^([\w., ]+=)?\s*[\w\.]+\(.*\)$').match(summary_str):
            self['Signature'] = summary_str
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

    def _parse(self):
        self._doc.reset()
        self._parse_summary()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters', 'Returns', 'Raises', 'Warns',
                           'Other Parameters', 'Attributes', 'Methods'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            elif section == 'See Also':
                self['See Also'] = self._parse_see_also(content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        if self['Signature']:
            return [self['Signature'].replace('*','\*')] + ['']
        else:
            return ['']

    def _str_summary(self):
        if self['Summary']:
            return self['Summary'] + ['']
        else:
            return []

    def _str_extended_summary(self):
        if self['Extended Summary']:
            return self['Extended Summary'] + ['']
        else:
            return []

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_see_also(self, func_role):
        if not self['See Also']: return []
        out = []
        out += self._str_header("See Also")
        last_had_desc = True
        for func, desc, role in self['See Also']:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                out += ['']
                out += [link]
            else:
                out[-1] += ", %s" % link
            if desc:
                out += self._str_indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, func_role=''):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        for param_list in ('Attributes', 'Methods'):
            out += self._str_param_list(param_list)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def dedent_lines(lines):
    """Deindent a list of lines maximally"""
    return textwrap.dedent("\n".join(lines)).split("\n")

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class FunctionDoc(NumpyDocString):
    def __init__(self, func, role='func', doc=None, config={}):
        self._f = func
        self._role = role # e.g. "func" or "meth"

        if doc is None:
            if func is None:
                raise ValueError("No function or docstring given")
            doc = inspect.getdoc(func) or ''
        NumpyDocString.__init__(self, doc)

        if not self['Signature'] and func is not None:
            func, func_name = self.get_func()
            try:
                # try to read signature
                argspec = inspect.getargspec(func)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                signature = '%s%s' % (func_name, argspec)
            except TypeError, e:
                signature = '%s()' % func_name
            self['Signature'] = signature

    def get_func(self):
        func_name = getattr(self._f, '__name__', self.__class__.__name__)
        if inspect.isclass(self._f):
            func = getattr(self._f, '__call__', self._f.__init__)
        else:
            func = self._f
        return func, func_name

    def __str__(self):
        out = ''

        func, func_name = self.get_func()
        signature = self['Signature'].replace('*', '\*')

        roles = {'func': 'function',
                 'meth': 'method'}

        if self._role:
            if not roles.has_key(self._role):
                print "Warning: invalid role %s" % self._role
            out += '.. %s:: %s\n    \n\n' % (roles.get(self._role,''),
                                             func_name)

        out += super(FunctionDoc, self).__str__(func_role=self._role)
        return out


class ClassDoc(NumpyDocString):

    extra_public_methods = ['__call__']

    def __init__(self, cls, doc=None, modulename='', func_doc=FunctionDoc,
                 config={}):
        if not inspect.isclass(cls) and cls is not None:
            raise ValueError("Expected a class or None, but got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename

        if doc is None:
            if cls is None:
                raise ValueError("No class or documentation string given")
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

        if config.get('show_class_members', True):
            if not self['Methods']:
                self['Methods'] = [(name, '', '')
                                   for name in sorted(self.methods)]
            if not self['Attributes']:
                self['Attributes'] = [(name, '', '')
                                      for name in sorted(self.properties)]

    @property
    def methods(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if ((not name.startswith('_')
                     or name in self.extra_public_methods)
                    and callable(func))]

    @property
    def properties(self):
        if self._cls is None:
            return []
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and func is None]

########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
import sphinx
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
    def __init__(self, docstring, config={}):
        self.use_plots = config.get('use_plots', False)
        NumpyDocString.__init__(self, docstring, config=config)

    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['.. rubric:: ' + name, '']

    def _str_field_list(self, name):
        return [':' + name + ':']

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['']
        if self['Signature']:
            return ['``%s``' % self['Signature']] + ['']
        else:
            return ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_field_list(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param.strip(),
                                                          param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    @property
    def _obj(self):
        if hasattr(self, '_cls'):
            return self._cls
        elif hasattr(self, '_f'):
            return self._f
        return None

    def _str_member_list(self, name):
        """
        Generate a member listing, autosummary:: table where possible,
        and a table where not.

        """
        out = []
        if self[name]:
            out += ['.. rubric:: %s' % name, '']
            prefix = getattr(self, '_name', '')

            if prefix:
                prefix = '~%s.' % prefix

            autosum = []
            others = []
            for param, param_type, desc in self[name]:
                param = param.strip()
                if not self._obj or hasattr(self._obj, param):
                    autosum += ["   %s%s" % (prefix, param)]
                else:
                    others.append((param, param_type, desc))

            if autosum:
                out += ['.. autosummary::', '   :toctree:', '']
                out += autosum

            if others:
                maxlen_0 = max([len(x[0]) for x in others])
                maxlen_1 = max([len(x[1]) for x in others])
                hdr = "="*maxlen_0 + "  " + "="*maxlen_1 + "  " + "="*10
                fmt = '%%%ds  %%%ds  ' % (maxlen_0, maxlen_1)
                n_indent = maxlen_0 + maxlen_1 + 4
                out += [hdr]
                for param, param_type, desc in others:
                    out += [fmt % (param.strip(), param_type)]
                    out += self._str_indent(desc, n_indent)
                out += [hdr]
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = textwrap.dedent("\n".join(self[name])).split("\n")
            out += content
            out += ['']
        return out

    def _str_see_also(self, func_role):
        out = []
        if self['See Also']:
            see_also = super(SphinxDocString, self)._str_see_also(func_role)
            out = ['.. seealso::', '']
            out += self._str_indent(see_also[2:])
        return out

    def _str_warnings(self):
        out = []
        if self['Warnings']:
            out = ['.. warning::', '']
            out += self._str_indent(self['Warnings'])
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        if len(idx) == 0:
            return out

        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            elif section == 'refguide':
                out += ['   single: %s' % (', '.join(references))]
            else:
                out += ['   %s: %s' % (section, ','.join(references))]
        return out

    def _str_references(self):
        out = []
        if self['References']:
            out += self._str_header('References')
            if isinstance(self['References'], str):
                self['References'] = [self['References']]
            out.extend(self['References'])
            out += ['']
            # Latex collects all references to a separate bibliography,
            # so we need to insert links to it
            if sphinx.__version__ >= "0.6":
                out += ['.. only:: latex','']
            else:
                out += ['.. latexonly::','']
            items = []
            for line in self['References']:
                m = re.match(r'.. \[([a-z0-9._-]+)\]', line, re.I)
                if m:
                    items.append(m.group(1))
            out += ['   ' + ", ".join(["[%s]_" % item for item in items]), '']
        return out

    def _str_examples(self):
        examples_str = "\n".join(self['Examples'])

        if (self.use_plots and 'import matplotlib' in examples_str
                and 'plot::' not in examples_str):
            out = []
            out += self._str_header('Examples')
            out += ['.. plot::', '']
            out += self._str_indent(self['Examples'])
            out += ['']
            return out
        else:
            return self._str_section('Examples')

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Other Parameters',
                           'Raises', 'Warns'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_examples()
        for param_list in ('Attributes', 'Methods'):
            out += self._str_member_list(param_list)
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    def __init__(self, obj, doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        FunctionDoc.__init__(self, obj, doc=doc, config=config)

class SphinxClassDoc(SphinxDocString, ClassDoc):
    def __init__(self, obj, doc=None, func_doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        ClassDoc.__init__(self, obj, doc=doc, func_doc=None, config=config)

class SphinxObjDoc(SphinxDocString):
    def __init__(self, obj, doc=None, config={}):
        self._f = obj
        SphinxDocString.__init__(self, doc, config=config)

def get_doc_object(obj, what=None, doc=None, config={}):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        return SphinxClassDoc(obj, func_doc=SphinxFunctionDoc, doc=doc,
                              config=config)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, doc=doc, config=config)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxObjDoc(obj, doc, config=config)

########NEW FILE########
__FILENAME__ = numpydoc
"""
========
numpydoc
========

Sphinx extension that handles docstrings in the Numpy standard format. [1]

It will:

- Convert Parameters etc. sections to field lists.
- Convert See Also section to a See also entry.
- Renumber references.
- Extract the signature from the docstring, if it can't be determined otherwise.

.. [1] https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt

"""

import sphinx

if sphinx.__version__ < '1.0.1':
    raise RuntimeError("Sphinx 1.0.1 or newer is required")

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
from sphinx.util.compat import Directive
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):

    cfg = dict(use_plots=app.config.numpydoc_use_plots,
               show_class_members=app.config.numpydoc_show_class_members)

    if what == 'module':
        # Strip top title
        title_re = re.compile(ur'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub(u'', u"\n".join(lines)).split(u"\n")
    else:
        doc = get_doc_object(obj, what, u"\n".join(lines), config=cfg)
        lines[:] = unicode(doc).split(u"\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name=u"%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += [u'', u'.. htmlonly::', '']
        lines += [u'    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for line in lines:
        line = line.strip()
        m = re.match(ur'^.. \[([a-z0-9_.-])\]', line, re.I)
        if m:
            references.append(m.group(1))

    # start renaming from the longest string, to avoid overwriting parts
    references.sort(key=lambda x: -len(x))
    if references:
        for i, line in enumerate(lines):
            for r in references:
                if re.match(ur'^\d+$', r):
                    new_r = u"R%d" % (reference_offset[0] + int(r))
                else:
                    new_r = u"%s%d" % (r, reference_offset[0])
                lines[i] = lines[i].replace(u'[%s]_' % r,
                                            u'[%s]_' % new_r)
                lines[i] = lines[i].replace(u'.. [%s]' % r,
                                            u'.. [%s]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        (not hasattr(obj, '__init__') or
        'initializes x; see ' in pydoc.getdoc(obj.__init__))):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub(u"^[^(]*", u"", doc['Signature'])
        return sig, u''

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_

    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('autodoc-process-signature', mangle_signature)
    app.add_config_value('numpydoc_edit_link', None, False)
    app.add_config_value('numpydoc_use_plots', None, False)
    app.add_config_value('numpydoc_show_class_members', True, True)

    # Extra mangling domains
    app.add_domain(NumpyPythonDomain)
    app.add_domain(NumpyCDomain)

#------------------------------------------------------------------------------
# Docstring-mangling domains
#------------------------------------------------------------------------------

from docutils.statemachine import ViewList
from sphinx.domains.c import CDomain
from sphinx.domains.python import PythonDomain

class ManglingDomainBase(object):
    directive_mangling_map = {}

    def __init__(self, *a, **kw):
        super(ManglingDomainBase, self).__init__(*a, **kw)
        self.wrap_mangling_directives()

    def wrap_mangling_directives(self):
        for name, objtype in self.directive_mangling_map.items():
            self.directives[name] = wrap_mangling_directive(
                self.directives[name], objtype)

class NumpyPythonDomain(ManglingDomainBase, PythonDomain):
    name = 'np'
    directive_mangling_map = {
        'function': 'function',
        'class': 'class',
        'exception': 'class',
        'method': 'function',
        'classmethod': 'function',
        'staticmethod': 'function',
        'attribute': 'attribute',
    }

class NumpyCDomain(ManglingDomainBase, CDomain):
    name = 'np-c'
    directive_mangling_map = {
        'function': 'function',
        'member': 'attribute',
        'macro': 'function',
        'type': 'class',
        'var': 'object',
    }

def wrap_mangling_directive(base_directive, objtype):
    class directive(base_directive):
        def run(self):
            env = self.state.document.settings.env

            name = None
            if self.arguments:
                m = re.match(r'^(.*\s+)?(.*?)(\(.*)?', self.arguments[0])
                name = m.group(2).strip()

            if not name:
                name = self.arguments[0]

            lines = list(self.content)
            mangle_docstrings(env.app, objtype, name, None, None, lines)
            self.content = ViewList(lines, self.content.parent)

            return base_directive.run(self)

    return directive


########NEW FILE########
__FILENAME__ = acent
from cvxpy import Variable, Problem, Minimize, log
import cvxopt

cvxopt.solvers.options['show_progress'] = False

# create problem data
m, n = 5, 10
A = cvxopt.normal(m,n)
tmp = cvxopt.uniform(n,1)
b = A*tmp

x = Variable(n)

p = Problem(
    Minimize(-sum(log(x))),
    [A*x == b]
)
status = p.solve()
cvxpy_x = x.value

def acent(A, b):
    m, n = A.size
    def F(x=None, z=None):
        if x is None: return 0, cvxopt.matrix(1.0, (n,1))
        if min(x) <= 0.0: return None
        f = -sum(cvxopt.log(x))
        Df = -(x**-1).T
        if z is None: return f, Df
        H = cvxopt.spdiag(z[0] * x**-2)
        return f, Df, H
    sol = cvxopt.solvers.cp(F, A=A, b=b)
    return sol['x'], sol['primal objective']

x, obj = acent(A,b)
cvxopt_x = x

if isinstance(status, (float, int)):
    print "difference in solution:", sum((cvxopt_x - cvxpy_x)**2)
    print "difference in objective:", abs(obj - status)
else:
    print "Generated infeasible problem"
    print "  ", status
########NEW FILE########
__FILENAME__ = cheshire_tomography
import cvxpy as cp
import mixed_integer as mi
import ncvx

bv = [] # Boolean variables.
for i in range(26):
	var_row = []
	for j in range(31):
		var_row.append(mi.BoolVar())
	bv.append(var_row)



obj = bv[1][24]+bv[2][5]+bv[2][6]+bv[2][7]+bv[2][23]+bv[2][24]+bv[3][5]+bv[3][7]+bv[3][8]+bv[3][22]+bv[3][25]+bv[4][4]+bv[4][8]+bv[4][9]+bv[4][13]+bv[4][14]+bv[4][15]+bv[4][16]+bv[4][17]+bv[4][18]+bv[4][19]+bv[4][22]+bv[4][25]+bv[5][4]+bv[5][6]+bv[5][9]+bv[5][10]+bv[5][11]+bv[5][12]+bv[5][20]+bv[5][21]+bv[5][22]+bv[5][26]+bv[6][4]+bv[6][6]+bv[6][9]+bv[6][22]+bv[6][24]+bv[6][26]+bv[7][4]+bv[7][6]+bv[7][9]+bv[7][22]+bv[7][24]+bv[7][26]+bv[8][4]+bv[8][22]+bv[8][26]+bv[9][4]+bv[9][23]+bv[9][26]+bv[10][5]+bv[10][25]+bv[10][27]+bv[11][6]+bv[11][27]+bv[12][6]+bv[12][9]+bv[12][10]+bv[12][11]+bv[12][19]+bv[12][20]+bv[12][21]+bv[12][27]+bv[13][6]+bv[13][8]+bv[13][12]+bv[13][18]+bv[13][22]+bv[13][27]+bv[14][1]+bv[14][2]+bv[14][5]+bv[14][8]+bv[14][9]+bv[14][10]+bv[14][12]+bv[14][18]+bv[14][19]+bv[14][20]+bv[14][22]+bv[14][28]+bv[15][3]+bv[15][4]+bv[15][5]+bv[15][8]+bv[15][9]+bv[15][10]+bv[15][11]+bv[15][12]+bv[15][19]+bv[15][20]+bv[15][21]+bv[15][28]+bv[16][5]+bv[16][6]+bv[16][14]+bv[16][16]+bv[16][28]+bv[17][1]+bv[17][2]+bv[17][3]+bv[17][4]+bv[17][14]+bv[17][16]+bv[17][27]+bv[17][28]+bv[17][29]+bv[17][30]+bv[18][4]+bv[18][5]+bv[18][6]+bv[18][7]+bv[18][13]+bv[18][16]+bv[18][23]+bv[18][24]+bv[18][25]+bv[18][26]+bv[18][28]+bv[19][4]+bv[19][14]+bv[19][15]+bv[19][28]+bv[20][5]+bv[20][9]+bv[20][10]+bv[20][22]+bv[20][23]+bv[20][24]+bv[20][25]+bv[20][26]+bv[20][27]+bv[20][28]+bv[20][29]+bv[20][30]+bv[21][6]+bv[21][10]+bv[21][11]+bv[21][12]+bv[21][13]+bv[21][14]+bv[21][27]+bv[22][7]+bv[22][8]+bv[22][12]+bv[22][13]+bv[22][14]+bv[22][15]+bv[22][16]+bv[22][17]+bv[22][18]+bv[22][19]+bv[22][20]+bv[22][21]+bv[22][22]+bv[22][26]+bv[23][9]+bv[23][10]+bv[23][13]+bv[23][14]+bv[23][15]+bv[23][16]+bv[23][17]+bv[23][18]+bv[23][19]+bv[23][24]+bv[23][25]+bv[24][11]+bv[24][21]+bv[24][22]+bv[24][23]+bv[25][12]+bv[25][13]+bv[25][14]+bv[25][15]+bv[25][16]+bv[25][17]+bv[25][18]+bv[25][19]+bv[25][20]+bv[25][21]

constraints = [
bv[1][1]+bv[1][2]+bv[1][3]+bv[1][4]+bv[1][5]+bv[1][6]+bv[1][7]+bv[1][8]+bv[1][9]+bv[1][10]+bv[1][11]+bv[1][12]+bv[1][13]+bv[1][14]+bv[1][15]+bv[1][16]+bv[1][17]+bv[1][18]+bv[1][19]+bv[1][20]+bv[1][21]+bv[1][22]+bv[1][23]+bv[1][24]+bv[1][25]+bv[1][26]+bv[1][27]+bv[1][28]+bv[1][29]+bv[1][30] == 1,
bv[2][1]+bv[2][2]+bv[2][3]+bv[2][4]+bv[2][5]+bv[2][6]+bv[2][7]+bv[2][8]+bv[2][9]+bv[2][10]+bv[2][11]+bv[2][12]+bv[2][13]+bv[2][14]+bv[2][15]+bv[2][16]+bv[2][17]+bv[2][18]+bv[2][19]+bv[2][20]+bv[2][21]+bv[2][22]+bv[2][23]+bv[2][24]+bv[2][25]+bv[2][26]+bv[2][27]+bv[2][28]+bv[2][29]+bv[2][30] == 5,
bv[3][1]+bv[3][2]+bv[3][3]+bv[3][4]+bv[3][5]+bv[3][6]+bv[3][7]+bv[3][8]+bv[3][9]+bv[3][10]+bv[3][11]+bv[3][12]+bv[3][13]+bv[3][14]+bv[3][15]+bv[3][16]+bv[3][17]+bv[3][18]+bv[3][19]+bv[3][20]+bv[3][21]+bv[3][22]+bv[3][23]+bv[3][24]+bv[3][25]+bv[3][26]+bv[3][27]+bv[3][28]+bv[3][29]+bv[3][30] == 5,
bv[4][1]+bv[4][2]+bv[4][3]+bv[4][4]+bv[4][5]+bv[4][6]+bv[4][7]+bv[4][8]+bv[4][9]+bv[4][10]+bv[4][11]+bv[4][12]+bv[4][13]+bv[4][14]+bv[4][15]+bv[4][16]+bv[4][17]+bv[4][18]+bv[4][19]+bv[4][20]+bv[4][21]+bv[4][22]+bv[4][23]+bv[4][24]+bv[4][25]+bv[4][26]+bv[4][27]+bv[4][28]+bv[4][29]+bv[4][30] == 12,
bv[5][1]+bv[5][2]+bv[5][3]+bv[5][4]+bv[5][5]+bv[5][6]+bv[5][7]+bv[5][8]+bv[5][9]+bv[5][10]+bv[5][11]+bv[5][12]+bv[5][13]+bv[5][14]+bv[5][15]+bv[5][16]+bv[5][17]+bv[5][18]+bv[5][19]+bv[5][20]+bv[5][21]+bv[5][22]+bv[5][23]+bv[5][24]+bv[5][25]+bv[5][26]+bv[5][27]+bv[5][28]+bv[5][29]+bv[5][30] == 10,
bv[6][1]+bv[6][2]+bv[6][3]+bv[6][4]+bv[6][5]+bv[6][6]+bv[6][7]+bv[6][8]+bv[6][9]+bv[6][10]+bv[6][11]+bv[6][12]+bv[6][13]+bv[6][14]+bv[6][15]+bv[6][16]+bv[6][17]+bv[6][18]+bv[6][19]+bv[6][20]+bv[6][21]+bv[6][22]+bv[6][23]+bv[6][24]+bv[6][25]+bv[6][26]+bv[6][27]+bv[6][28]+bv[6][29]+bv[6][30] == 6,
bv[7][1]+bv[7][2]+bv[7][3]+bv[7][4]+bv[7][5]+bv[7][6]+bv[7][7]+bv[7][8]+bv[7][9]+bv[7][10]+bv[7][11]+bv[7][12]+bv[7][13]+bv[7][14]+bv[7][15]+bv[7][16]+bv[7][17]+bv[7][18]+bv[7][19]+bv[7][20]+bv[7][21]+bv[7][22]+bv[7][23]+bv[7][24]+bv[7][25]+bv[7][26]+bv[7][27]+bv[7][28]+bv[7][29]+bv[7][30] == 6,
bv[8][1]+bv[8][2]+bv[8][3]+bv[8][4]+bv[8][5]+bv[8][6]+bv[8][7]+bv[8][8]+bv[8][9]+bv[8][10]+bv[8][11]+bv[8][12]+bv[8][13]+bv[8][14]+bv[8][15]+bv[8][16]+bv[8][17]+bv[8][18]+bv[8][19]+bv[8][20]+bv[8][21]+bv[8][22]+bv[8][23]+bv[8][24]+bv[8][25]+bv[8][26]+bv[8][27]+bv[8][28]+bv[8][29]+bv[8][30] == 3,
bv[9][1]+bv[9][2]+bv[9][3]+bv[9][4]+bv[9][5]+bv[9][6]+bv[9][7]+bv[9][8]+bv[9][9]+bv[9][10]+bv[9][11]+bv[9][12]+bv[9][13]+bv[9][14]+bv[9][15]+bv[9][16]+bv[9][17]+bv[9][18]+bv[9][19]+bv[9][20]+bv[9][21]+bv[9][22]+bv[9][23]+bv[9][24]+bv[9][25]+bv[9][26]+bv[9][27]+bv[9][28]+bv[9][29]+bv[9][30] == 3,
bv[10][1]+bv[10][2]+bv[10][3]+bv[10][4]+bv[10][5]+bv[10][6]+bv[10][7]+bv[10][8]+bv[10][9]+bv[10][10]+bv[10][11]+bv[10][12]+bv[10][13]+bv[10][14]+bv[10][15]+bv[10][16]+bv[10][17]+bv[10][18]+bv[10][19]+bv[10][20]+bv[10][21]+bv[10][22]+bv[10][23]+bv[10][24]+bv[10][25]+bv[10][26]+bv[10][27]+bv[10][28]+bv[10][29]+bv[10][30] == 3,
bv[11][1]+bv[11][2]+bv[11][3]+bv[11][4]+bv[11][5]+bv[11][6]+bv[11][7]+bv[11][8]+bv[11][9]+bv[11][10]+bv[11][11]+bv[11][12]+bv[11][13]+bv[11][14]+bv[11][15]+bv[11][16]+bv[11][17]+bv[11][18]+bv[11][19]+bv[11][20]+bv[11][21]+bv[11][22]+bv[11][23]+bv[11][24]+bv[11][25]+bv[11][26]+bv[11][27]+bv[11][28]+bv[11][29]+bv[11][30] == 2,
bv[12][1]+bv[12][2]+bv[12][3]+bv[12][4]+bv[12][5]+bv[12][6]+bv[12][7]+bv[12][8]+bv[12][9]+bv[12][10]+bv[12][11]+bv[12][12]+bv[12][13]+bv[12][14]+bv[12][15]+bv[12][16]+bv[12][17]+bv[12][18]+bv[12][19]+bv[12][20]+bv[12][21]+bv[12][22]+bv[12][23]+bv[12][24]+bv[12][25]+bv[12][26]+bv[12][27]+bv[12][28]+bv[12][29]+bv[12][30] == 8,
bv[13][1]+bv[13][2]+bv[13][3]+bv[13][4]+bv[13][5]+bv[13][6]+bv[13][7]+bv[13][8]+bv[13][9]+bv[13][10]+bv[13][11]+bv[13][12]+bv[13][13]+bv[13][14]+bv[13][15]+bv[13][16]+bv[13][17]+bv[13][18]+bv[13][19]+bv[13][20]+bv[13][21]+bv[13][22]+bv[13][23]+bv[13][24]+bv[13][25]+bv[13][26]+bv[13][27]+bv[13][28]+bv[13][29]+bv[13][30] == 6,
bv[14][1]+bv[14][2]+bv[14][3]+bv[14][4]+bv[14][5]+bv[14][6]+bv[14][7]+bv[14][8]+bv[14][9]+bv[14][10]+bv[14][11]+bv[14][12]+bv[14][13]+bv[14][14]+bv[14][15]+bv[14][16]+bv[14][17]+bv[14][18]+bv[14][19]+bv[14][20]+bv[14][21]+bv[14][22]+bv[14][23]+bv[14][24]+bv[14][25]+bv[14][26]+bv[14][27]+bv[14][28]+bv[14][29]+bv[14][30] == 12,
bv[15][1]+bv[15][2]+bv[15][3]+bv[15][4]+bv[15][5]+bv[15][6]+bv[15][7]+bv[15][8]+bv[15][9]+bv[15][10]+bv[15][11]+bv[15][12]+bv[15][13]+bv[15][14]+bv[15][15]+bv[15][16]+bv[15][17]+bv[15][18]+bv[15][19]+bv[15][20]+bv[15][21]+bv[15][22]+bv[15][23]+bv[15][24]+bv[15][25]+bv[15][26]+bv[15][27]+bv[15][28]+bv[15][29]+bv[15][30] == 12,
bv[16][1]+bv[16][2]+bv[16][3]+bv[16][4]+bv[16][5]+bv[16][6]+bv[16][7]+bv[16][8]+bv[16][9]+bv[16][10]+bv[16][11]+bv[16][12]+bv[16][13]+bv[16][14]+bv[16][15]+bv[16][16]+bv[16][17]+bv[16][18]+bv[16][19]+bv[16][20]+bv[16][21]+bv[16][22]+bv[16][23]+bv[16][24]+bv[16][25]+bv[16][26]+bv[16][27]+bv[16][28]+bv[16][29]+bv[16][30] == 5,
bv[17][1]+bv[17][2]+bv[17][3]+bv[17][4]+bv[17][5]+bv[17][6]+bv[17][7]+bv[17][8]+bv[17][9]+bv[17][10]+bv[17][11]+bv[17][12]+bv[17][13]+bv[17][14]+bv[17][15]+bv[17][16]+bv[17][17]+bv[17][18]+bv[17][19]+bv[17][20]+bv[17][21]+bv[17][22]+bv[17][23]+bv[17][24]+bv[17][25]+bv[17][26]+bv[17][27]+bv[17][28]+bv[17][29]+bv[17][30] == 10,
bv[18][1]+bv[18][2]+bv[18][3]+bv[18][4]+bv[18][5]+bv[18][6]+bv[18][7]+bv[18][8]+bv[18][9]+bv[18][10]+bv[18][11]+bv[18][12]+bv[18][13]+bv[18][14]+bv[18][15]+bv[18][16]+bv[18][17]+bv[18][18]+bv[18][19]+bv[18][20]+bv[18][21]+bv[18][22]+bv[18][23]+bv[18][24]+bv[18][25]+bv[18][26]+bv[18][27]+bv[18][28]+bv[18][29]+bv[18][30] == 11,
bv[19][1]+bv[19][2]+bv[19][3]+bv[19][4]+bv[19][5]+bv[19][6]+bv[19][7]+bv[19][8]+bv[19][9]+bv[19][10]+bv[19][11]+bv[19][12]+bv[19][13]+bv[19][14]+bv[19][15]+bv[19][16]+bv[19][17]+bv[19][18]+bv[19][19]+bv[19][20]+bv[19][21]+bv[19][22]+bv[19][23]+bv[19][24]+bv[19][25]+bv[19][26]+bv[19][27]+bv[19][28]+bv[19][29]+bv[19][30] == 4,
bv[20][1]+bv[20][2]+bv[20][3]+bv[20][4]+bv[20][5]+bv[20][6]+bv[20][7]+bv[20][8]+bv[20][9]+bv[20][10]+bv[20][11]+bv[20][12]+bv[20][13]+bv[20][14]+bv[20][15]+bv[20][16]+bv[20][17]+bv[20][18]+bv[20][19]+bv[20][20]+bv[20][21]+bv[20][22]+bv[20][23]+bv[20][24]+bv[20][25]+bv[20][26]+bv[20][27]+bv[20][28]+bv[20][29]+bv[20][30] == 12,
bv[21][1]+bv[21][2]+bv[21][3]+bv[21][4]+bv[21][5]+bv[21][6]+bv[21][7]+bv[21][8]+bv[21][9]+bv[21][10]+bv[21][11]+bv[21][12]+bv[21][13]+bv[21][14]+bv[21][15]+bv[21][16]+bv[21][17]+bv[21][18]+bv[21][19]+bv[21][20]+bv[21][21]+bv[21][22]+bv[21][23]+bv[21][24]+bv[21][25]+bv[21][26]+bv[21][27]+bv[21][28]+bv[21][29]+bv[21][30] == 7,
bv[22][1]+bv[22][2]+bv[22][3]+bv[22][4]+bv[22][5]+bv[22][6]+bv[22][7]+bv[22][8]+bv[22][9]+bv[22][10]+bv[22][11]+bv[22][12]+bv[22][13]+bv[22][14]+bv[22][15]+bv[22][16]+bv[22][17]+bv[22][18]+bv[22][19]+bv[22][20]+bv[22][21]+bv[22][22]+bv[22][23]+bv[22][24]+bv[22][25]+bv[22][26]+bv[22][27]+bv[22][28]+bv[22][29]+bv[22][30] == 14,
bv[23][1]+bv[23][2]+bv[23][3]+bv[23][4]+bv[23][5]+bv[23][6]+bv[23][7]+bv[23][8]+bv[23][9]+bv[23][10]+bv[23][11]+bv[23][12]+bv[23][13]+bv[23][14]+bv[23][15]+bv[23][16]+bv[23][17]+bv[23][18]+bv[23][19]+bv[23][20]+bv[23][21]+bv[23][22]+bv[23][23]+bv[23][24]+bv[23][25]+bv[23][26]+bv[23][27]+bv[23][28]+bv[23][29]+bv[23][30] == 11,
bv[24][1]+bv[24][2]+bv[24][3]+bv[24][4]+bv[24][5]+bv[24][6]+bv[24][7]+bv[24][8]+bv[24][9]+bv[24][10]+bv[24][11]+bv[24][12]+bv[24][13]+bv[24][14]+bv[24][15]+bv[24][16]+bv[24][17]+bv[24][18]+bv[24][19]+bv[24][20]+bv[24][21]+bv[24][22]+bv[24][23]+bv[24][24]+bv[24][25]+bv[24][26]+bv[24][27]+bv[24][28]+bv[24][29]+bv[24][30] == 4,
bv[25][1]+bv[25][2]+bv[25][3]+bv[25][4]+bv[25][5]+bv[25][6]+bv[25][7]+bv[25][8]+bv[25][9]+bv[25][10]+bv[25][11]+bv[25][12]+bv[25][13]+bv[25][14]+bv[25][15]+bv[25][16]+bv[25][17]+bv[25][18]+bv[25][19]+bv[25][20]+bv[25][21]+bv[25][22]+bv[25][23]+bv[25][24]+bv[25][25]+bv[25][26]+bv[25][27]+bv[25][28]+bv[25][29]+bv[25][30] == 10,
bv[1][1]+bv[2][1]+bv[3][1]+bv[4][1]+bv[5][1]+bv[6][1]+bv[7][1]+bv[8][1]+bv[9][1]+bv[10][1]+bv[11][1]+bv[12][1]+bv[13][1]+bv[14][1]+bv[15][1]+bv[16][1]+bv[17][1]+bv[18][1]+bv[19][1]+bv[20][1]+bv[21][1]+bv[22][1]+bv[23][1]+bv[24][1]+bv[25][1] == 2,
bv[1][2]+bv[2][2]+bv[3][2]+bv[4][2]+bv[5][2]+bv[6][2]+bv[7][2]+bv[8][2]+bv[9][2]+bv[10][2]+bv[11][2]+bv[12][2]+bv[13][2]+bv[14][2]+bv[15][2]+bv[16][2]+bv[17][2]+bv[18][2]+bv[19][2]+bv[20][2]+bv[21][2]+bv[22][2]+bv[23][2]+bv[24][2]+bv[25][2] == 2,
bv[1][3]+bv[2][3]+bv[3][3]+bv[4][3]+bv[5][3]+bv[6][3]+bv[7][3]+bv[8][3]+bv[9][3]+bv[10][3]+bv[11][3]+bv[12][3]+bv[13][3]+bv[14][3]+bv[15][3]+bv[16][3]+bv[17][3]+bv[18][3]+bv[19][3]+bv[20][3]+bv[21][3]+bv[22][3]+bv[23][3]+bv[24][3]+bv[25][3] == 2,
bv[1][4]+bv[2][4]+bv[3][4]+bv[4][4]+bv[5][4]+bv[6][4]+bv[7][4]+bv[8][4]+bv[9][4]+bv[10][4]+bv[11][4]+bv[12][4]+bv[13][4]+bv[14][4]+bv[15][4]+bv[16][4]+bv[17][4]+bv[18][4]+bv[19][4]+bv[20][4]+bv[21][4]+bv[22][4]+bv[23][4]+bv[24][4]+bv[25][4] == 10,
bv[1][5]+bv[2][5]+bv[3][5]+bv[4][5]+bv[5][5]+bv[6][5]+bv[7][5]+bv[8][5]+bv[9][5]+bv[10][5]+bv[11][5]+bv[12][5]+bv[13][5]+bv[14][5]+bv[15][5]+bv[16][5]+bv[17][5]+bv[18][5]+bv[19][5]+bv[20][5]+bv[21][5]+bv[22][5]+bv[23][5]+bv[24][5]+bv[25][5] == 8,
bv[1][6]+bv[2][6]+bv[3][6]+bv[4][6]+bv[5][6]+bv[6][6]+bv[7][6]+bv[8][6]+bv[9][6]+bv[10][6]+bv[11][6]+bv[12][6]+bv[13][6]+bv[14][6]+bv[15][6]+bv[16][6]+bv[17][6]+bv[18][6]+bv[19][6]+bv[20][6]+bv[21][6]+bv[22][6]+bv[23][6]+bv[24][6]+bv[25][6] == 10,
bv[1][7]+bv[2][7]+bv[3][7]+bv[4][7]+bv[5][7]+bv[6][7]+bv[7][7]+bv[8][7]+bv[9][7]+bv[10][7]+bv[11][7]+bv[12][7]+bv[13][7]+bv[14][7]+bv[15][7]+bv[16][7]+bv[17][7]+bv[18][7]+bv[19][7]+bv[20][7]+bv[21][7]+bv[22][7]+bv[23][7]+bv[24][7]+bv[25][7] == 4,
bv[1][8]+bv[2][8]+bv[3][8]+bv[4][8]+bv[5][8]+bv[6][8]+bv[7][8]+bv[8][8]+bv[9][8]+bv[10][8]+bv[11][8]+bv[12][8]+bv[13][8]+bv[14][8]+bv[15][8]+bv[16][8]+bv[17][8]+bv[18][8]+bv[19][8]+bv[20][8]+bv[21][8]+bv[22][8]+bv[23][8]+bv[24][8]+bv[25][8] == 6,
bv[1][9]+bv[2][9]+bv[3][9]+bv[4][9]+bv[5][9]+bv[6][9]+bv[7][9]+bv[8][9]+bv[9][9]+bv[10][9]+bv[11][9]+bv[12][9]+bv[13][9]+bv[14][9]+bv[15][9]+bv[16][9]+bv[17][9]+bv[18][9]+bv[19][9]+bv[20][9]+bv[21][9]+bv[22][9]+bv[23][9]+bv[24][9]+bv[25][9] == 9,
bv[1][10]+bv[2][10]+bv[3][10]+bv[4][10]+bv[5][10]+bv[6][10]+bv[7][10]+bv[8][10]+bv[9][10]+bv[10][10]+bv[11][10]+bv[12][10]+bv[13][10]+bv[14][10]+bv[15][10]+bv[16][10]+bv[17][10]+bv[18][10]+bv[19][10]+bv[20][10]+bv[21][10]+bv[22][10]+bv[23][10]+bv[24][10]+bv[25][10] == 7,
bv[1][11]+bv[2][11]+bv[3][11]+bv[4][11]+bv[5][11]+bv[6][11]+bv[7][11]+bv[8][11]+bv[9][11]+bv[10][11]+bv[11][11]+bv[12][11]+bv[13][11]+bv[14][11]+bv[15][11]+bv[16][11]+bv[17][11]+bv[18][11]+bv[19][11]+bv[20][11]+bv[21][11]+bv[22][11]+bv[23][11]+bv[24][11]+bv[25][11] == 5,
bv[1][12]+bv[2][12]+bv[3][12]+bv[4][12]+bv[5][12]+bv[6][12]+bv[7][12]+bv[8][12]+bv[9][12]+bv[10][12]+bv[11][12]+bv[12][12]+bv[13][12]+bv[14][12]+bv[15][12]+bv[16][12]+bv[17][12]+bv[18][12]+bv[19][12]+bv[20][12]+bv[21][12]+bv[22][12]+bv[23][12]+bv[24][12]+bv[25][12] == 7,
bv[1][13]+bv[2][13]+bv[3][13]+bv[4][13]+bv[5][13]+bv[6][13]+bv[7][13]+bv[8][13]+bv[9][13]+bv[10][13]+bv[11][13]+bv[12][13]+bv[13][13]+bv[14][13]+bv[15][13]+bv[16][13]+bv[17][13]+bv[18][13]+bv[19][13]+bv[20][13]+bv[21][13]+bv[22][13]+bv[23][13]+bv[24][13]+bv[25][13] == 6,
bv[1][14]+bv[2][14]+bv[3][14]+bv[4][14]+bv[5][14]+bv[6][14]+bv[7][14]+bv[8][14]+bv[9][14]+bv[10][14]+bv[11][14]+bv[12][14]+bv[13][14]+bv[14][14]+bv[15][14]+bv[16][14]+bv[17][14]+bv[18][14]+bv[19][14]+bv[20][14]+bv[21][14]+bv[22][14]+bv[23][14]+bv[24][14]+bv[25][14] == 8,
bv[1][15]+bv[2][15]+bv[3][15]+bv[4][15]+bv[5][15]+bv[6][15]+bv[7][15]+bv[8][15]+bv[9][15]+bv[10][15]+bv[11][15]+bv[12][15]+bv[13][15]+bv[14][15]+bv[15][15]+bv[16][15]+bv[17][15]+bv[18][15]+bv[19][15]+bv[20][15]+bv[21][15]+bv[22][15]+bv[23][15]+bv[24][15]+bv[25][15] == 5,
bv[1][16]+bv[2][16]+bv[3][16]+bv[4][16]+bv[5][16]+bv[6][16]+bv[7][16]+bv[8][16]+bv[9][16]+bv[10][16]+bv[11][16]+bv[12][16]+bv[13][16]+bv[14][16]+bv[15][16]+bv[16][16]+bv[17][16]+bv[18][16]+bv[19][16]+bv[20][16]+bv[21][16]+bv[22][16]+bv[23][16]+bv[24][16]+bv[25][16] == 7,
bv[1][17]+bv[2][17]+bv[3][17]+bv[4][17]+bv[5][17]+bv[6][17]+bv[7][17]+bv[8][17]+bv[9][17]+bv[10][17]+bv[11][17]+bv[12][17]+bv[13][17]+bv[14][17]+bv[15][17]+bv[16][17]+bv[17][17]+bv[18][17]+bv[19][17]+bv[20][17]+bv[21][17]+bv[22][17]+bv[23][17]+bv[24][17]+bv[25][17] == 4,
bv[1][18]+bv[2][18]+bv[3][18]+bv[4][18]+bv[5][18]+bv[6][18]+bv[7][18]+bv[8][18]+bv[9][18]+bv[10][18]+bv[11][18]+bv[12][18]+bv[13][18]+bv[14][18]+bv[15][18]+bv[16][18]+bv[17][18]+bv[18][18]+bv[19][18]+bv[20][18]+bv[21][18]+bv[22][18]+bv[23][18]+bv[24][18]+bv[25][18] == 6,
bv[1][19]+bv[2][19]+bv[3][19]+bv[4][19]+bv[5][19]+bv[6][19]+bv[7][19]+bv[8][19]+bv[9][19]+bv[10][19]+bv[11][19]+bv[12][19]+bv[13][19]+bv[14][19]+bv[15][19]+bv[16][19]+bv[17][19]+bv[18][19]+bv[19][19]+bv[20][19]+bv[21][19]+bv[22][19]+bv[23][19]+bv[24][19]+bv[25][19] == 7,
bv[1][20]+bv[2][20]+bv[3][20]+bv[4][20]+bv[5][20]+bv[6][20]+bv[7][20]+bv[8][20]+bv[9][20]+bv[10][20]+bv[11][20]+bv[12][20]+bv[13][20]+bv[14][20]+bv[15][20]+bv[16][20]+bv[17][20]+bv[18][20]+bv[19][20]+bv[20][20]+bv[21][20]+bv[22][20]+bv[23][20]+bv[24][20]+bv[25][20] == 6,
bv[1][21]+bv[2][21]+bv[3][21]+bv[4][21]+bv[5][21]+bv[6][21]+bv[7][21]+bv[8][21]+bv[9][21]+bv[10][21]+bv[11][21]+bv[12][21]+bv[13][21]+bv[14][21]+bv[15][21]+bv[16][21]+bv[17][21]+bv[18][21]+bv[19][21]+bv[20][21]+bv[21][21]+bv[22][21]+bv[23][21]+bv[24][21]+bv[25][21] == 6,
bv[1][22]+bv[2][22]+bv[3][22]+bv[4][22]+bv[5][22]+bv[6][22]+bv[7][22]+bv[8][22]+bv[9][22]+bv[10][22]+bv[11][22]+bv[12][22]+bv[13][22]+bv[14][22]+bv[15][22]+bv[16][22]+bv[17][22]+bv[18][22]+bv[19][22]+bv[20][22]+bv[21][22]+bv[22][22]+bv[23][22]+bv[24][22]+bv[25][22] == 11,
bv[1][23]+bv[2][23]+bv[3][23]+bv[4][23]+bv[5][23]+bv[6][23]+bv[7][23]+bv[8][23]+bv[9][23]+bv[10][23]+bv[11][23]+bv[12][23]+bv[13][23]+bv[14][23]+bv[15][23]+bv[16][23]+bv[17][23]+bv[18][23]+bv[19][23]+bv[20][23]+bv[21][23]+bv[22][23]+bv[23][23]+bv[24][23]+bv[25][23] == 5,
bv[1][24]+bv[2][24]+bv[3][24]+bv[4][24]+bv[5][24]+bv[6][24]+bv[7][24]+bv[8][24]+bv[9][24]+bv[10][24]+bv[11][24]+bv[12][24]+bv[13][24]+bv[14][24]+bv[15][24]+bv[16][24]+bv[17][24]+bv[18][24]+bv[19][24]+bv[20][24]+bv[21][24]+bv[22][24]+bv[23][24]+bv[24][24]+bv[25][24] == 7,
bv[1][25]+bv[2][25]+bv[3][25]+bv[4][25]+bv[5][25]+bv[6][25]+bv[7][25]+bv[8][25]+bv[9][25]+bv[10][25]+bv[11][25]+bv[12][25]+bv[13][25]+bv[14][25]+bv[15][25]+bv[16][25]+bv[17][25]+bv[18][25]+bv[19][25]+bv[20][25]+bv[21][25]+bv[22][25]+bv[23][25]+bv[24][25]+bv[25][25] == 6,
bv[1][26]+bv[2][26]+bv[3][26]+bv[4][26]+bv[5][26]+bv[6][26]+bv[7][26]+bv[8][26]+bv[9][26]+bv[10][26]+bv[11][26]+bv[12][26]+bv[13][26]+bv[14][26]+bv[15][26]+bv[16][26]+bv[17][26]+bv[18][26]+bv[19][26]+bv[20][26]+bv[21][26]+bv[22][26]+bv[23][26]+bv[24][26]+bv[25][26] == 8,
bv[1][27]+bv[2][27]+bv[3][27]+bv[4][27]+bv[5][27]+bv[6][27]+bv[7][27]+bv[8][27]+bv[9][27]+bv[10][27]+bv[11][27]+bv[12][27]+bv[13][27]+bv[14][27]+bv[15][27]+bv[16][27]+bv[17][27]+bv[18][27]+bv[19][27]+bv[20][27]+bv[21][27]+bv[22][27]+bv[23][27]+bv[24][27]+bv[25][27] == 7,
bv[1][28]+bv[2][28]+bv[3][28]+bv[4][28]+bv[5][28]+bv[6][28]+bv[7][28]+bv[8][28]+bv[9][28]+bv[10][28]+bv[11][28]+bv[12][28]+bv[13][28]+bv[14][28]+bv[15][28]+bv[16][28]+bv[17][28]+bv[18][28]+bv[19][28]+bv[20][28]+bv[21][28]+bv[22][28]+bv[23][28]+bv[24][28]+bv[25][28] == 7,
bv[1][29]+bv[2][29]+bv[3][29]+bv[4][29]+bv[5][29]+bv[6][29]+bv[7][29]+bv[8][29]+bv[9][29]+bv[10][29]+bv[11][29]+bv[12][29]+bv[13][29]+bv[14][29]+bv[15][29]+bv[16][29]+bv[17][29]+bv[18][29]+bv[19][29]+bv[20][29]+bv[21][29]+bv[22][29]+bv[23][29]+bv[24][29]+bv[25][29] == 2,
bv[1][30]+bv[2][30]+bv[3][30]+bv[4][30]+bv[5][30]+bv[6][30]+bv[7][30]+bv[8][30]+bv[9][30]+bv[10][30]+bv[11][30]+bv[12][30]+bv[13][30]+bv[14][30]+bv[15][30]+bv[16][30]+bv[17][30]+bv[18][30]+bv[19][30]+bv[20][30]+bv[21][30]+bv[22][30]+bv[23][30]+bv[24][30]+bv[25][30] == 2,
bv[1][1] == 0,
bv[1][2]+bv[2][1] == 0,
bv[1][3]+bv[2][2]+bv[3][1] == 0,
bv[1][4]+bv[2][3]+bv[3][2]+bv[4][1] == 0,
bv[1][5]+bv[2][4]+bv[3][3]+bv[4][2]+bv[5][1] == 0,
bv[1][6]+bv[2][5]+bv[3][4]+bv[4][3]+bv[5][2]+bv[6][1] == 1,
bv[1][7]+bv[2][6]+bv[3][5]+bv[4][4]+bv[5][3]+bv[6][2]+bv[7][1] == 3,
bv[1][8]+bv[2][7]+bv[3][6]+bv[4][5]+bv[5][4]+bv[6][3]+bv[7][2]+bv[8][1] == 2,
bv[1][9]+bv[2][8]+bv[3][7]+bv[4][6]+bv[5][5]+bv[6][4]+bv[7][3]+bv[8][2]+bv[9][1] == 2,
bv[1][10]+bv[2][9]+bv[3][8]+bv[4][7]+bv[5][6]+bv[6][5]+bv[7][4]+bv[8][3]+bv[9][2]+bv[10][1] == 3,
bv[1][11]+bv[2][10]+bv[3][9]+bv[4][8]+bv[5][7]+bv[6][6]+bv[7][5]+bv[8][4]+bv[9][3]+bv[10][2]+bv[11][1] == 3,
bv[1][12]+bv[2][11]+bv[3][10]+bv[4][9]+bv[5][8]+bv[6][7]+bv[7][6]+bv[8][5]+bv[9][4]+bv[10][3]+bv[11][2]+bv[12][1] == 3,
bv[1][13]+bv[2][12]+bv[3][11]+bv[4][10]+bv[5][9]+bv[6][8]+bv[7][7]+bv[8][6]+bv[9][5]+bv[10][4]+bv[11][3]+bv[12][2]+bv[13][1] == 1,
bv[1][14]+bv[2][13]+bv[3][12]+bv[4][11]+bv[5][10]+bv[6][9]+bv[7][8]+bv[8][7]+bv[9][6]+bv[10][5]+bv[11][4]+bv[12][3]+bv[13][2]+bv[14][1] == 4,
bv[1][15]+bv[2][14]+bv[3][13]+bv[4][12]+bv[5][11]+bv[6][10]+bv[7][9]+bv[8][8]+bv[9][7]+bv[10][6]+bv[11][5]+bv[12][4]+bv[13][3]+bv[14][2]+bv[15][1] == 3,
bv[1][16]+bv[2][15]+bv[3][14]+bv[4][13]+bv[5][12]+bv[6][11]+bv[7][10]+bv[8][9]+bv[9][8]+bv[10][7]+bv[11][6]+bv[12][5]+bv[13][4]+bv[14][3]+bv[15][2]+bv[16][1] == 3,
bv[1][17]+bv[2][16]+bv[3][15]+bv[4][14]+bv[5][13]+bv[6][12]+bv[7][11]+bv[8][10]+bv[9][9]+bv[10][8]+bv[11][7]+bv[12][6]+bv[13][5]+bv[14][4]+bv[15][3]+bv[16][2]+bv[17][1] == 4,
bv[1][18]+bv[2][17]+bv[3][16]+bv[4][15]+bv[5][14]+bv[6][13]+bv[7][12]+bv[8][11]+bv[9][10]+bv[10][9]+bv[11][8]+bv[12][7]+bv[13][6]+bv[14][5]+bv[15][4]+bv[16][3]+bv[17][2]+bv[18][1] == 5,
bv[1][19]+bv[2][18]+bv[3][17]+bv[4][16]+bv[5][15]+bv[6][14]+bv[7][13]+bv[8][12]+bv[9][11]+bv[10][10]+bv[11][9]+bv[12][8]+bv[13][7]+bv[14][6]+bv[15][5]+bv[16][4]+bv[17][3]+bv[18][2]+bv[19][1] == 3,
bv[1][20]+bv[2][19]+bv[3][18]+bv[4][17]+bv[5][16]+bv[6][15]+bv[7][14]+bv[8][13]+bv[9][12]+bv[10][11]+bv[11][10]+bv[12][9]+bv[13][8]+bv[14][7]+bv[15][6]+bv[16][5]+bv[17][4]+bv[18][3]+bv[19][2]+bv[20][1] == 5,
bv[1][21]+bv[2][20]+bv[3][19]+bv[4][18]+bv[5][17]+bv[6][16]+bv[7][15]+bv[8][14]+bv[9][13]+bv[10][12]+bv[11][11]+bv[12][10]+bv[13][9]+bv[14][8]+bv[15][7]+bv[16][6]+bv[17][5]+bv[18][4]+bv[19][3]+bv[20][2]+bv[21][1] == 5,
bv[1][22]+bv[2][21]+bv[3][20]+bv[4][19]+bv[5][18]+bv[6][17]+bv[7][16]+bv[8][15]+bv[9][14]+bv[10][13]+bv[11][12]+bv[12][11]+bv[13][10]+bv[14][9]+bv[15][8]+bv[16][7]+bv[17][6]+bv[18][5]+bv[19][4]+bv[20][3]+bv[21][2]+bv[22][1] == 6,
bv[1][23]+bv[2][22]+bv[3][21]+bv[4][20]+bv[5][19]+bv[6][18]+bv[7][17]+bv[8][16]+bv[9][15]+bv[10][14]+bv[11][13]+bv[12][12]+bv[13][11]+bv[14][10]+bv[15][9]+bv[16][8]+bv[17][7]+bv[18][6]+bv[19][5]+bv[20][4]+bv[21][3]+bv[22][2]+bv[23][1] == 3,
bv[1][24]+bv[2][23]+bv[3][22]+bv[4][21]+bv[5][20]+bv[6][19]+bv[7][18]+bv[8][17]+bv[9][16]+bv[10][15]+bv[11][14]+bv[12][13]+bv[13][12]+bv[14][11]+bv[15][10]+bv[16][9]+bv[17][8]+bv[18][7]+bv[19][6]+bv[20][5]+bv[21][4]+bv[22][3]+bv[23][2]+bv[24][1] == 8,
bv[1][25]+bv[2][24]+bv[3][23]+bv[4][22]+bv[5][21]+bv[6][20]+bv[7][19]+bv[8][18]+bv[9][17]+bv[10][16]+bv[11][15]+bv[12][14]+bv[13][13]+bv[14][12]+bv[15][11]+bv[16][10]+bv[17][9]+bv[18][8]+bv[19][7]+bv[20][6]+bv[21][5]+bv[22][4]+bv[23][3]+bv[24][2]+bv[25][1] == 5,
bv[1][26]+bv[2][25]+bv[3][24]+bv[4][23]+bv[5][22]+bv[6][21]+bv[7][20]+bv[8][19]+bv[9][18]+bv[10][17]+bv[11][16]+bv[12][15]+bv[13][14]+bv[14][13]+bv[15][12]+bv[16][11]+bv[17][10]+bv[18][9]+bv[19][8]+bv[20][7]+bv[21][6]+bv[22][5]+bv[23][4]+bv[24][3]+bv[25][2] == 3,
bv[1][27]+bv[2][26]+bv[3][25]+bv[4][24]+bv[5][23]+bv[6][22]+bv[7][21]+bv[8][20]+bv[9][19]+bv[10][18]+bv[11][17]+bv[12][16]+bv[13][15]+bv[14][14]+bv[15][13]+bv[16][12]+bv[17][11]+bv[18][10]+bv[19][9]+bv[20][8]+bv[21][7]+bv[22][6]+bv[23][5]+bv[24][4]+bv[25][3] == 2,
bv[1][28]+bv[2][27]+bv[3][26]+bv[4][25]+bv[5][24]+bv[6][23]+bv[7][22]+bv[8][21]+bv[9][20]+bv[10][19]+bv[11][18]+bv[12][17]+bv[13][16]+bv[14][15]+bv[15][14]+bv[16][13]+bv[17][12]+bv[18][11]+bv[19][10]+bv[20][9]+bv[21][8]+bv[22][7]+bv[23][6]+bv[24][5]+bv[25][4] == 4,
bv[1][29]+bv[2][28]+bv[3][27]+bv[4][26]+bv[5][25]+bv[6][24]+bv[7][23]+bv[8][22]+bv[9][21]+bv[10][20]+bv[11][19]+bv[12][18]+bv[13][17]+bv[14][16]+bv[15][15]+bv[16][14]+bv[17][13]+bv[18][12]+bv[19][11]+bv[20][10]+bv[21][9]+bv[22][8]+bv[23][7]+bv[24][6]+bv[25][5] == 5,
bv[1][30]+bv[2][29]+bv[3][28]+bv[4][27]+bv[5][26]+bv[6][25]+bv[7][24]+bv[8][23]+bv[9][22]+bv[10][21]+bv[11][20]+bv[12][19]+bv[13][18]+bv[14][17]+bv[15][16]+bv[16][15]+bv[17][14]+bv[18][13]+bv[19][12]+bv[20][11]+bv[21][10]+bv[22][9]+bv[23][8]+bv[24][7]+bv[25][6] == 7,
bv[2][30]+bv[3][29]+bv[4][28]+bv[5][27]+bv[6][26]+bv[7][25]+bv[8][24]+bv[9][23]+bv[10][22]+bv[11][21]+bv[12][20]+bv[13][19]+bv[14][18]+bv[15][17]+bv[16][16]+bv[17][15]+bv[18][14]+bv[19][13]+bv[20][12]+bv[21][11]+bv[22][10]+bv[23][9]+bv[24][8]+bv[25][7] == 7,
bv[3][30]+bv[4][29]+bv[5][28]+bv[6][27]+bv[7][26]+bv[8][25]+bv[9][24]+bv[10][23]+bv[11][22]+bv[12][21]+bv[13][20]+bv[14][19]+bv[15][18]+bv[16][17]+bv[17][16]+bv[18][15]+bv[19][14]+bv[20][13]+bv[21][12]+bv[22][11]+bv[23][10]+bv[24][9]+bv[25][8] == 7,
bv[4][30]+bv[5][29]+bv[6][28]+bv[7][27]+bv[8][26]+bv[9][25]+bv[10][24]+bv[11][23]+bv[12][22]+bv[13][21]+bv[14][20]+bv[15][19]+bv[16][18]+bv[17][17]+bv[18][16]+bv[19][15]+bv[20][14]+bv[21][13]+bv[22][12]+bv[23][11]+bv[24][10]+bv[25][9] == 7,
bv[5][30]+bv[6][29]+bv[7][28]+bv[8][27]+bv[9][26]+bv[10][25]+bv[11][24]+bv[12][23]+bv[13][22]+bv[14][21]+bv[15][20]+bv[16][19]+bv[17][18]+bv[18][17]+bv[19][16]+bv[20][15]+bv[21][14]+bv[22][13]+bv[23][12]+bv[24][11]+bv[25][10] == 7,
bv[6][30]+bv[7][29]+bv[8][28]+bv[9][27]+bv[10][26]+bv[11][25]+bv[12][24]+bv[13][23]+bv[14][22]+bv[15][21]+bv[16][20]+bv[17][19]+bv[18][18]+bv[19][17]+bv[20][16]+bv[21][15]+bv[22][14]+bv[23][13]+bv[24][12]+bv[25][11] == 4,
bv[7][30]+bv[8][29]+bv[9][28]+bv[10][27]+bv[11][26]+bv[12][25]+bv[13][24]+bv[14][23]+bv[15][22]+bv[16][21]+bv[17][20]+bv[18][19]+bv[19][18]+bv[20][17]+bv[21][16]+bv[22][15]+bv[23][14]+bv[24][13]+bv[25][12] == 4,
bv[8][30]+bv[9][29]+bv[10][28]+bv[11][27]+bv[12][26]+bv[13][25]+bv[14][24]+bv[15][23]+bv[16][22]+bv[17][21]+bv[18][20]+bv[19][19]+bv[20][18]+bv[21][17]+bv[22][16]+bv[23][15]+bv[24][14]+bv[25][13] == 4,
bv[9][30]+bv[10][29]+bv[11][28]+bv[12][27]+bv[13][26]+bv[14][25]+bv[15][24]+bv[16][23]+bv[17][22]+bv[18][21]+bv[19][20]+bv[20][19]+bv[21][18]+bv[22][17]+bv[23][16]+bv[24][15]+bv[25][14] == 4,
bv[10][30]+bv[11][29]+bv[12][28]+bv[13][27]+bv[14][26]+bv[15][25]+bv[16][24]+bv[17][23]+bv[18][22]+bv[19][21]+bv[20][20]+bv[21][19]+bv[22][18]+bv[23][17]+bv[24][16]+bv[25][15] == 4,
bv[11][30]+bv[12][29]+bv[13][28]+bv[14][27]+bv[15][26]+bv[16][25]+bv[17][24]+bv[18][23]+bv[19][22]+bv[20][21]+bv[21][20]+bv[22][19]+bv[23][18]+bv[24][17]+bv[25][16] == 4,
bv[12][30]+bv[13][29]+bv[14][28]+bv[15][27]+bv[16][26]+bv[17][25]+bv[18][24]+bv[19][23]+bv[20][22]+bv[21][21]+bv[22][20]+bv[23][19]+bv[24][18]+bv[25][17] == 6,
bv[13][30]+bv[14][29]+bv[15][28]+bv[16][27]+bv[17][26]+bv[18][25]+bv[19][24]+bv[20][23]+bv[21][22]+bv[22][21]+bv[23][20]+bv[24][19]+bv[25][18] == 5,
bv[14][30]+bv[15][29]+bv[16][28]+bv[17][27]+bv[18][26]+bv[19][25]+bv[20][24]+bv[21][23]+bv[22][22]+bv[23][21]+bv[24][20]+bv[25][19] == 6,
bv[15][30]+bv[16][29]+bv[17][28]+bv[18][27]+bv[19][26]+bv[20][25]+bv[21][24]+bv[22][23]+bv[23][22]+bv[24][21]+bv[25][20] == 4,
bv[16][30]+bv[17][29]+bv[18][28]+bv[19][27]+bv[20][26]+bv[21][25]+bv[22][24]+bv[23][23]+bv[24][22]+bv[25][21] == 5,
bv[17][30]+bv[18][29]+bv[19][28]+bv[20][27]+bv[21][26]+bv[22][25]+bv[23][24]+bv[24][23]+bv[25][22] == 5,
bv[18][30]+bv[19][29]+bv[20][28]+bv[21][27]+bv[22][26]+bv[23][25]+bv[24][24]+bv[25][23] == 4,
bv[19][30]+bv[20][29]+bv[21][28]+bv[22][27]+bv[23][26]+bv[24][25]+bv[25][24] == 1,
bv[20][30]+bv[21][29]+bv[22][28]+bv[23][27]+bv[24][26]+bv[25][25] == 1,
bv[21][30]+bv[22][29]+bv[23][28]+bv[24][27]+bv[25][26] == 0,
bv[22][30]+bv[23][29]+bv[24][28]+bv[25][27] == 0,
bv[23][30]+bv[24][29]+bv[25][28] == 0,
bv[24][30]+bv[25][29] == 0,
bv[25][30] == 0,
bv[1][30] == 0,
bv[1][29]+bv[2][30] == 0,
bv[1][28]+bv[2][29]+bv[3][30] == 0,
bv[1][27]+bv[2][28]+bv[3][29]+bv[4][30] == 0,
bv[1][26]+bv[2][27]+bv[3][28]+bv[4][29]+bv[5][30] == 0,
bv[1][25]+bv[2][26]+bv[3][27]+bv[4][28]+bv[5][29]+bv[6][30] == 0,
bv[1][24]+bv[2][25]+bv[3][26]+bv[4][27]+bv[5][28]+bv[6][29]+bv[7][30] == 1,
bv[1][23]+bv[2][24]+bv[3][25]+bv[4][26]+bv[5][27]+bv[6][28]+bv[7][29]+bv[8][30] == 2,
bv[1][22]+bv[2][23]+bv[3][24]+bv[4][25]+bv[5][26]+bv[6][27]+bv[7][28]+bv[8][29]+bv[9][30] == 3,
bv[1][21]+bv[2][22]+bv[3][23]+bv[4][24]+bv[5][25]+bv[6][26]+bv[7][27]+bv[8][28]+bv[9][29]+bv[10][30] == 1,
bv[1][20]+bv[2][21]+bv[3][22]+bv[4][23]+bv[5][24]+bv[6][25]+bv[7][26]+bv[8][27]+bv[9][28]+bv[10][29]+bv[11][30] == 2,
bv[1][19]+bv[2][20]+bv[3][21]+bv[4][22]+bv[5][23]+bv[6][24]+bv[7][25]+bv[8][26]+bv[9][27]+bv[10][28]+bv[11][29]+bv[12][30] == 3,
bv[1][18]+bv[2][19]+bv[3][20]+bv[4][21]+bv[5][22]+bv[6][23]+bv[7][24]+bv[8][25]+bv[9][26]+bv[10][27]+bv[11][28]+bv[12][29]+bv[13][30] == 4,
bv[1][17]+bv[2][18]+bv[3][19]+bv[4][20]+bv[5][21]+bv[6][22]+bv[7][23]+bv[8][24]+bv[9][25]+bv[10][26]+bv[11][27]+bv[12][28]+bv[13][29]+bv[14][30] == 3,
bv[1][16]+bv[2][17]+bv[3][18]+bv[4][19]+bv[5][20]+bv[6][21]+bv[7][22]+bv[8][23]+bv[9][24]+bv[10][25]+bv[11][26]+bv[12][27]+bv[13][28]+bv[14][29]+bv[15][30] == 5,
bv[1][15]+bv[2][16]+bv[3][17]+bv[4][18]+bv[5][19]+bv[6][20]+bv[7][21]+bv[8][22]+bv[9][23]+bv[10][24]+bv[11][25]+bv[12][26]+bv[13][27]+bv[14][28]+bv[15][29]+bv[16][30] == 5,
bv[1][14]+bv[2][15]+bv[3][16]+bv[4][17]+bv[5][18]+bv[6][19]+bv[7][20]+bv[8][21]+bv[9][22]+bv[10][23]+bv[11][24]+bv[12][25]+bv[13][26]+bv[14][27]+bv[15][28]+bv[16][29]+bv[17][30] == 3,
bv[1][13]+bv[2][14]+bv[3][15]+bv[4][16]+bv[5][17]+bv[6][18]+bv[7][19]+bv[8][20]+bv[9][21]+bv[10][22]+bv[11][23]+bv[12][24]+bv[13][25]+bv[14][26]+bv[15][27]+bv[16][28]+bv[17][29]+bv[18][30] == 3,
bv[1][12]+bv[2][13]+bv[3][14]+bv[4][15]+bv[5][16]+bv[6][17]+bv[7][18]+bv[8][19]+bv[9][20]+bv[10][21]+bv[11][22]+bv[12][23]+bv[13][24]+bv[14][25]+bv[15][26]+bv[16][27]+bv[17][28]+bv[18][29]+bv[19][30] == 2,
bv[1][11]+bv[2][12]+bv[3][13]+bv[4][14]+bv[5][15]+bv[6][16]+bv[7][17]+bv[8][18]+bv[9][19]+bv[10][20]+bv[11][21]+bv[12][22]+bv[13][23]+bv[14][24]+bv[15][25]+bv[16][26]+bv[17][27]+bv[18][28]+bv[19][29]+bv[20][30] == 4,
bv[1][10]+bv[2][11]+bv[3][12]+bv[4][13]+bv[5][14]+bv[6][15]+bv[7][16]+bv[8][17]+bv[9][18]+bv[10][19]+bv[11][20]+bv[12][21]+bv[13][22]+bv[14][23]+bv[15][24]+bv[16][25]+bv[17][26]+bv[18][27]+bv[19][28]+bv[20][29]+bv[21][30] == 5,
bv[1][9]+bv[2][10]+bv[3][11]+bv[4][12]+bv[5][13]+bv[6][14]+bv[7][15]+bv[8][16]+bv[9][17]+bv[10][18]+bv[11][19]+bv[12][20]+bv[13][21]+bv[14][22]+bv[15][23]+bv[16][24]+bv[17][25]+bv[18][26]+bv[19][27]+bv[20][28]+bv[21][29]+bv[22][30] == 4,
bv[1][8]+bv[2][9]+bv[3][10]+bv[4][11]+bv[5][12]+bv[6][13]+bv[7][14]+bv[8][15]+bv[9][16]+bv[10][17]+bv[11][18]+bv[12][19]+bv[13][20]+bv[14][21]+bv[15][22]+bv[16][23]+bv[17][24]+bv[18][25]+bv[19][26]+bv[20][27]+bv[21][28]+bv[22][29]+bv[23][30] == 4,
bv[1][7]+bv[2][8]+bv[3][9]+bv[4][10]+bv[5][11]+bv[6][12]+bv[7][13]+bv[8][14]+bv[9][15]+bv[10][16]+bv[11][17]+bv[12][18]+bv[13][19]+bv[14][20]+bv[15][21]+bv[16][22]+bv[17][23]+bv[18][24]+bv[19][25]+bv[20][26]+bv[21][27]+bv[22][28]+bv[23][29]+bv[24][30] == 6,
bv[1][6]+bv[2][7]+bv[3][8]+bv[4][9]+bv[5][10]+bv[6][11]+bv[7][12]+bv[8][13]+bv[9][14]+bv[10][15]+bv[11][16]+bv[12][17]+bv[13][18]+bv[14][19]+bv[15][20]+bv[16][21]+bv[17][22]+bv[18][23]+bv[19][24]+bv[20][25]+bv[21][26]+bv[22][27]+bv[23][28]+bv[24][29]+bv[25][30] == 9,
bv[1][5]+bv[2][6]+bv[3][7]+bv[4][8]+bv[5][9]+bv[6][10]+bv[7][11]+bv[8][12]+bv[9][13]+bv[10][14]+bv[11][15]+bv[12][16]+bv[13][17]+bv[14][18]+bv[15][19]+bv[16][20]+bv[17][21]+bv[18][22]+bv[19][23]+bv[20][24]+bv[21][25]+bv[22][26]+bv[23][27]+bv[24][28]+bv[25][29] == 8,
bv[1][4]+bv[2][5]+bv[3][6]+bv[4][7]+bv[5][8]+bv[6][9]+bv[7][10]+bv[8][11]+bv[9][12]+bv[10][13]+bv[11][14]+bv[12][15]+bv[13][16]+bv[14][17]+bv[15][18]+bv[16][19]+bv[17][20]+bv[18][21]+bv[19][22]+bv[20][23]+bv[21][24]+bv[22][25]+bv[23][26]+bv[24][27]+bv[25][28] == 3,
bv[1][3]+bv[2][4]+bv[3][5]+bv[4][6]+bv[5][7]+bv[6][8]+bv[7][9]+bv[8][10]+bv[9][11]+bv[10][12]+bv[11][13]+bv[12][14]+bv[13][15]+bv[14][16]+bv[15][17]+bv[16][18]+bv[17][19]+bv[18][20]+bv[19][21]+bv[20][22]+bv[21][23]+bv[22][24]+bv[23][25]+bv[24][26]+bv[25][27] == 4,
bv[1][2]+bv[2][3]+bv[3][4]+bv[4][5]+bv[5][6]+bv[6][7]+bv[7][8]+bv[8][9]+bv[9][10]+bv[10][11]+bv[11][12]+bv[12][13]+bv[13][14]+bv[14][15]+bv[15][16]+bv[16][17]+bv[17][18]+bv[18][19]+bv[19][20]+bv[20][21]+bv[21][22]+bv[22][23]+bv[23][24]+bv[24][25]+bv[25][26] == 2,
bv[1][1]+bv[2][2]+bv[3][3]+bv[4][4]+bv[5][5]+bv[6][6]+bv[7][7]+bv[8][8]+bv[9][9]+bv[10][10]+bv[11][11]+bv[12][12]+bv[13][13]+bv[14][14]+bv[15][15]+bv[16][16]+bv[17][17]+bv[18][18]+bv[19][19]+bv[20][20]+bv[21][21]+bv[22][22]+bv[23][23]+bv[24][24]+bv[25][25] == 4,
bv[2][1]+bv[3][2]+bv[4][3]+bv[5][4]+bv[6][5]+bv[7][6]+bv[8][7]+bv[9][8]+bv[10][9]+bv[11][10]+bv[12][11]+bv[13][12]+bv[14][13]+bv[15][14]+bv[16][15]+bv[17][16]+bv[18][17]+bv[19][18]+bv[20][19]+bv[21][20]+bv[22][21]+bv[23][22]+bv[24][23]+bv[25][24] == 7,
bv[3][1]+bv[4][2]+bv[5][3]+bv[6][4]+bv[7][5]+bv[8][6]+bv[9][7]+bv[10][8]+bv[11][9]+bv[12][10]+bv[13][11]+bv[14][12]+bv[15][13]+bv[16][14]+bv[17][15]+bv[18][16]+bv[19][17]+bv[20][18]+bv[21][19]+bv[22][20]+bv[23][21]+bv[24][22]+bv[25][23] == 7,
bv[4][1]+bv[5][2]+bv[6][3]+bv[7][4]+bv[8][5]+bv[9][6]+bv[10][7]+bv[11][8]+bv[12][9]+bv[13][10]+bv[14][11]+bv[15][12]+bv[16][13]+bv[17][14]+bv[18][15]+bv[19][16]+bv[20][17]+bv[21][18]+bv[22][19]+bv[23][20]+bv[24][21]+bv[25][22] == 6,
bv[5][1]+bv[6][2]+bv[7][3]+bv[8][4]+bv[9][5]+bv[10][6]+bv[11][7]+bv[12][8]+bv[13][9]+bv[14][10]+bv[15][11]+bv[16][12]+bv[17][13]+bv[18][14]+bv[19][15]+bv[20][16]+bv[21][17]+bv[22][18]+bv[23][19]+bv[24][20]+bv[25][21] == 7,
bv[6][1]+bv[7][2]+bv[8][3]+bv[9][4]+bv[10][5]+bv[11][6]+bv[12][7]+bv[13][8]+bv[14][9]+bv[15][10]+bv[16][11]+bv[17][12]+bv[18][13]+bv[19][14]+bv[20][15]+bv[21][16]+bv[22][17]+bv[23][18]+bv[24][19]+bv[25][20] == 11,
bv[7][1]+bv[8][2]+bv[9][3]+bv[10][4]+bv[11][5]+bv[12][6]+bv[13][7]+bv[14][8]+bv[15][9]+bv[16][10]+bv[17][11]+bv[18][12]+bv[19][13]+bv[20][14]+bv[21][15]+bv[22][16]+bv[23][17]+bv[24][18]+bv[25][19] == 6,
bv[8][1]+bv[9][2]+bv[10][3]+bv[11][4]+bv[12][5]+bv[13][6]+bv[14][7]+bv[15][8]+bv[16][9]+bv[17][10]+bv[18][11]+bv[19][12]+bv[20][13]+bv[21][14]+bv[22][15]+bv[23][16]+bv[24][17]+bv[25][18] == 6,
bv[9][1]+bv[10][2]+bv[11][3]+bv[12][4]+bv[13][5]+bv[14][6]+bv[15][7]+bv[16][8]+bv[17][9]+bv[18][10]+bv[19][11]+bv[20][12]+bv[21][13]+bv[22][14]+bv[23][15]+bv[24][16]+bv[25][17] == 4,
bv[10][1]+bv[11][2]+bv[12][3]+bv[13][4]+bv[14][5]+bv[15][6]+bv[16][7]+bv[17][8]+bv[18][9]+bv[19][10]+bv[20][11]+bv[21][12]+bv[22][13]+bv[23][14]+bv[24][15]+bv[25][16] == 5,
bv[11][1]+bv[12][2]+bv[13][3]+bv[14][4]+bv[15][5]+bv[16][6]+bv[17][7]+bv[18][8]+bv[19][9]+bv[20][10]+bv[21][11]+bv[22][12]+bv[23][13]+bv[24][14]+bv[25][15] == 7,
bv[12][1]+bv[13][2]+bv[14][3]+bv[15][4]+bv[16][5]+bv[17][6]+bv[18][7]+bv[19][8]+bv[20][9]+bv[21][10]+bv[22][11]+bv[23][12]+bv[24][13]+bv[25][14] == 6,
bv[13][1]+bv[14][2]+bv[15][3]+bv[16][4]+bv[17][5]+bv[18][6]+bv[19][7]+bv[20][8]+bv[21][9]+bv[22][10]+bv[23][11]+bv[24][12]+bv[25][13] == 4,
bv[14][1]+bv[15][2]+bv[16][3]+bv[17][4]+bv[18][5]+bv[19][6]+bv[20][7]+bv[21][8]+bv[22][9]+bv[23][10]+bv[24][11]+bv[25][12] == 6,
bv[15][1]+bv[16][2]+bv[17][3]+bv[18][4]+bv[19][5]+bv[20][6]+bv[21][7]+bv[22][8]+bv[23][9]+bv[24][10]+bv[25][11] == 4,
bv[16][1]+bv[17][2]+bv[18][3]+bv[19][4]+bv[20][5]+bv[21][6]+bv[22][7]+bv[23][8]+bv[24][9]+bv[25][10] == 5,
bv[17][1]+bv[18][2]+bv[19][3]+bv[20][4]+bv[21][5]+bv[22][6]+bv[23][7]+bv[24][8]+bv[25][9] == 1,
bv[18][1]+bv[19][2]+bv[20][3]+bv[21][4]+bv[22][5]+bv[23][6]+bv[24][7]+bv[25][8] == 0,
bv[19][1]+bv[20][2]+bv[21][3]+bv[22][4]+bv[23][5]+bv[24][6]+bv[25][7] == 0,
bv[20][1]+bv[21][2]+bv[22][3]+bv[23][4]+bv[24][5]+bv[25][6] == 0,
bv[21][1]+bv[22][2]+bv[23][3]+bv[24][4]+bv[25][5] == 0,
bv[22][1]+bv[23][2]+bv[24][3]+bv[25][4] == 0,
bv[23][1]+bv[24][2]+bv[25][3] == 0,
bv[24][1]+bv[25][2] == 0,
bv[25][1] == 0,
]

p = cp.Problem(cp.Minimize(obj), constraints)
result = p.solve()
print result

result = p.solve(method="admm", iterations=5, solver="ecos")
print result

obj = bv[1][24].z.value[0]+bv[2][5].z.value[0]+bv[2][6].z.value[0]+bv[2][7].z.value[0]+bv[2][23].z.value[0]+bv[2][24].z.value[0]+bv[3][5].z.value[0]+bv[3][7].z.value[0]+bv[3][8].z.value[0]+bv[3][22].z.value[0]+bv[3][25].z.value[0]+bv[4][4].z.value[0]+bv[4][8].z.value[0]+bv[4][9].z.value[0]+bv[4][13].z.value[0]+bv[4][14].z.value[0]+bv[4][15].z.value[0]+bv[4][16].z.value[0]+bv[4][17].z.value[0]+bv[4][18].z.value[0]+bv[4][19].z.value[0]+bv[4][22].z.value[0]+bv[4][25].z.value[0]+bv[5][4].z.value[0]+bv[5][6].z.value[0]+bv[5][9].z.value[0]+bv[5][10].z.value[0]+bv[5][11].z.value[0]+bv[5][12].z.value[0]+bv[5][20].z.value[0]+bv[5][21].z.value[0]+bv[5][22].z.value[0]+bv[5][26].z.value[0]+bv[6][4].z.value[0]+bv[6][6].z.value[0]+bv[6][9].z.value[0]+bv[6][22].z.value[0]+bv[6][24].z.value[0]+bv[6][26].z.value[0]+bv[7][4].z.value[0]+bv[7][6].z.value[0]+bv[7][9].z.value[0]+bv[7][22].z.value[0]+bv[7][24].z.value[0]+bv[7][26].z.value[0]+bv[8][4].z.value[0]+bv[8][22].z.value[0]+bv[8][26].z.value[0]+bv[9][4].z.value[0]+bv[9][23].z.value[0]+bv[9][26].z.value[0]+bv[10][5].z.value[0]+bv[10][25].z.value[0]+bv[10][27].z.value[0]+bv[11][6].z.value[0]+bv[11][27].z.value[0]+bv[12][6].z.value[0]+bv[12][9].z.value[0]+bv[12][10].z.value[0]+bv[12][11].z.value[0]+bv[12][19].z.value[0]+bv[12][20].z.value[0]+bv[12][21].z.value[0]+bv[12][27].z.value[0]+bv[13][6].z.value[0]+bv[13][8].z.value[0]+bv[13][12].z.value[0]+bv[13][18].z.value[0]+bv[13][22].z.value[0]+bv[13][27].z.value[0]+bv[14][1].z.value[0]+bv[14][2].z.value[0]+bv[14][5].z.value[0]+bv[14][8].z.value[0]+bv[14][9].z.value[0]+bv[14][10].z.value[0]+bv[14][12].z.value[0]+bv[14][18].z.value[0]+bv[14][19].z.value[0]+bv[14][20].z.value[0]+bv[14][22].z.value[0]+bv[14][28].z.value[0]+bv[15][3].z.value[0]+bv[15][4].z.value[0]+bv[15][5].z.value[0]+bv[15][8].z.value[0]+bv[15][9].z.value[0]+bv[15][10].z.value[0]+bv[15][11].z.value[0]+bv[15][12].z.value[0]+bv[15][19].z.value[0]+bv[15][20].z.value[0]+bv[15][21].z.value[0]+bv[15][28].z.value[0]+bv[16][5].z.value[0]+bv[16][6].z.value[0]+bv[16][14].z.value[0]+bv[16][16].z.value[0]+bv[16][28].z.value[0]+bv[17][1].z.value[0]+bv[17][2].z.value[0]+bv[17][3].z.value[0]+bv[17][4].z.value[0]+bv[17][14].z.value[0]+bv[17][16].z.value[0]+bv[17][27].z.value[0]+bv[17][28].z.value[0]+bv[17][29].z.value[0]+bv[17][30].z.value[0]+bv[18][4].z.value[0]+bv[18][5].z.value[0]+bv[18][6].z.value[0]+bv[18][7].z.value[0]+bv[18][13].z.value[0]+bv[18][16].z.value[0]+bv[18][23].z.value[0]+bv[18][24].z.value[0]+bv[18][25].z.value[0]+bv[18][26].z.value[0]+bv[18][28].z.value[0]+bv[19][4].z.value[0]+bv[19][14].z.value[0]+bv[19][15].z.value[0]+bv[19][28].z.value[0]+bv[20][5].z.value[0]+bv[20][9].z.value[0]+bv[20][10].z.value[0]+bv[20][22].z.value[0]+bv[20][23].z.value[0]+bv[20][24].z.value[0]+bv[20][25].z.value[0]+bv[20][26].z.value[0]+bv[20][27].z.value[0]+bv[20][28].z.value[0]+bv[20][29].z.value[0]+bv[20][30].z.value[0]+bv[21][6].z.value[0]+bv[21][10].z.value[0]+bv[21][11].z.value[0]+bv[21][12].z.value[0]+bv[21][13].z.value[0]+bv[21][14].z.value[0]+bv[21][27].z.value[0]+bv[22][7].z.value[0]+bv[22][8].z.value[0]+bv[22][12].z.value[0]+bv[22][13].z.value[0]+bv[22][14].z.value[0]+bv[22][15].z.value[0]+bv[22][16].z.value[0]+bv[22][17].z.value[0]+bv[22][18].z.value[0]+bv[22][19].z.value[0]+bv[22][20].z.value[0]+bv[22][21].z.value[0]+bv[22][22].z.value[0]+bv[22][26].z.value[0]+bv[23][9].z.value[0]+bv[23][10].z.value[0]+bv[23][13].z.value[0]+bv[23][14].z.value[0]+bv[23][15].z.value[0]+bv[23][16].z.value[0]+bv[23][17].z.value[0]+bv[23][18].z.value[0]+bv[23][19].z.value[0]+bv[23][24].z.value[0]+bv[23][25].z.value[0]+bv[24][11].z.value[0]+bv[24][21].z.value[0]+bv[24][22].z.value[0]+bv[24][23].z.value[0]+bv[25][12].z.value[0]+bv[25][13].z.value[0]+bv[25][14].z.value[0]+bv[25][15].z.value[0]+bv[25][16].z.value[0]+bv[25][17].z.value[0]+bv[25][18].z.value[0]+bv[25][19].z.value[0]+bv[25][20].z.value[0]+bv[25][21].z.value[0]

constraints = [
bv[1][1].z.value[0]+bv[1][2].z.value[0]+bv[1][3].z.value[0]+bv[1][4].z.value[0]+bv[1][5].z.value[0]+bv[1][6].z.value[0]+bv[1][7].z.value[0]+bv[1][8].z.value[0]+bv[1][9].z.value[0]+bv[1][10].z.value[0]+bv[1][11].z.value[0]+bv[1][12].z.value[0]+bv[1][13].z.value[0]+bv[1][14].z.value[0]+bv[1][15].z.value[0]+bv[1][16].z.value[0]+bv[1][17].z.value[0]+bv[1][18].z.value[0]+bv[1][19].z.value[0]+bv[1][20].z.value[0]+bv[1][21].z.value[0]+bv[1][22].z.value[0]+bv[1][23].z.value[0]+bv[1][24].z.value[0]+bv[1][25].z.value[0]+bv[1][26].z.value[0]+bv[1][27].z.value[0]+bv[1][28].z.value[0]+bv[1][29].z.value[0]+bv[1][30].z.value[0] == 1,
bv[2][1].z.value[0]+bv[2][2].z.value[0]+bv[2][3].z.value[0]+bv[2][4].z.value[0]+bv[2][5].z.value[0]+bv[2][6].z.value[0]+bv[2][7].z.value[0]+bv[2][8].z.value[0]+bv[2][9].z.value[0]+bv[2][10].z.value[0]+bv[2][11].z.value[0]+bv[2][12].z.value[0]+bv[2][13].z.value[0]+bv[2][14].z.value[0]+bv[2][15].z.value[0]+bv[2][16].z.value[0]+bv[2][17].z.value[0]+bv[2][18].z.value[0]+bv[2][19].z.value[0]+bv[2][20].z.value[0]+bv[2][21].z.value[0]+bv[2][22].z.value[0]+bv[2][23].z.value[0]+bv[2][24].z.value[0]+bv[2][25].z.value[0]+bv[2][26].z.value[0]+bv[2][27].z.value[0]+bv[2][28].z.value[0]+bv[2][29].z.value[0]+bv[2][30].z.value[0] == 5,
bv[3][1].z.value[0]+bv[3][2].z.value[0]+bv[3][3].z.value[0]+bv[3][4].z.value[0]+bv[3][5].z.value[0]+bv[3][6].z.value[0]+bv[3][7].z.value[0]+bv[3][8].z.value[0]+bv[3][9].z.value[0]+bv[3][10].z.value[0]+bv[3][11].z.value[0]+bv[3][12].z.value[0]+bv[3][13].z.value[0]+bv[3][14].z.value[0]+bv[3][15].z.value[0]+bv[3][16].z.value[0]+bv[3][17].z.value[0]+bv[3][18].z.value[0]+bv[3][19].z.value[0]+bv[3][20].z.value[0]+bv[3][21].z.value[0]+bv[3][22].z.value[0]+bv[3][23].z.value[0]+bv[3][24].z.value[0]+bv[3][25].z.value[0]+bv[3][26].z.value[0]+bv[3][27].z.value[0]+bv[3][28].z.value[0]+bv[3][29].z.value[0]+bv[3][30].z.value[0] == 5,
bv[4][1].z.value[0]+bv[4][2].z.value[0]+bv[4][3].z.value[0]+bv[4][4].z.value[0]+bv[4][5].z.value[0]+bv[4][6].z.value[0]+bv[4][7].z.value[0]+bv[4][8].z.value[0]+bv[4][9].z.value[0]+bv[4][10].z.value[0]+bv[4][11].z.value[0]+bv[4][12].z.value[0]+bv[4][13].z.value[0]+bv[4][14].z.value[0]+bv[4][15].z.value[0]+bv[4][16].z.value[0]+bv[4][17].z.value[0]+bv[4][18].z.value[0]+bv[4][19].z.value[0]+bv[4][20].z.value[0]+bv[4][21].z.value[0]+bv[4][22].z.value[0]+bv[4][23].z.value[0]+bv[4][24].z.value[0]+bv[4][25].z.value[0]+bv[4][26].z.value[0]+bv[4][27].z.value[0]+bv[4][28].z.value[0]+bv[4][29].z.value[0]+bv[4][30].z.value[0] == 12,
bv[5][1].z.value[0]+bv[5][2].z.value[0]+bv[5][3].z.value[0]+bv[5][4].z.value[0]+bv[5][5].z.value[0]+bv[5][6].z.value[0]+bv[5][7].z.value[0]+bv[5][8].z.value[0]+bv[5][9].z.value[0]+bv[5][10].z.value[0]+bv[5][11].z.value[0]+bv[5][12].z.value[0]+bv[5][13].z.value[0]+bv[5][14].z.value[0]+bv[5][15].z.value[0]+bv[5][16].z.value[0]+bv[5][17].z.value[0]+bv[5][18].z.value[0]+bv[5][19].z.value[0]+bv[5][20].z.value[0]+bv[5][21].z.value[0]+bv[5][22].z.value[0]+bv[5][23].z.value[0]+bv[5][24].z.value[0]+bv[5][25].z.value[0]+bv[5][26].z.value[0]+bv[5][27].z.value[0]+bv[5][28].z.value[0]+bv[5][29].z.value[0]+bv[5][30].z.value[0] == 10,
bv[6][1].z.value[0]+bv[6][2].z.value[0]+bv[6][3].z.value[0]+bv[6][4].z.value[0]+bv[6][5].z.value[0]+bv[6][6].z.value[0]+bv[6][7].z.value[0]+bv[6][8].z.value[0]+bv[6][9].z.value[0]+bv[6][10].z.value[0]+bv[6][11].z.value[0]+bv[6][12].z.value[0]+bv[6][13].z.value[0]+bv[6][14].z.value[0]+bv[6][15].z.value[0]+bv[6][16].z.value[0]+bv[6][17].z.value[0]+bv[6][18].z.value[0]+bv[6][19].z.value[0]+bv[6][20].z.value[0]+bv[6][21].z.value[0]+bv[6][22].z.value[0]+bv[6][23].z.value[0]+bv[6][24].z.value[0]+bv[6][25].z.value[0]+bv[6][26].z.value[0]+bv[6][27].z.value[0]+bv[6][28].z.value[0]+bv[6][29].z.value[0]+bv[6][30].z.value[0] == 6,
bv[7][1].z.value[0]+bv[7][2].z.value[0]+bv[7][3].z.value[0]+bv[7][4].z.value[0]+bv[7][5].z.value[0]+bv[7][6].z.value[0]+bv[7][7].z.value[0]+bv[7][8].z.value[0]+bv[7][9].z.value[0]+bv[7][10].z.value[0]+bv[7][11].z.value[0]+bv[7][12].z.value[0]+bv[7][13].z.value[0]+bv[7][14].z.value[0]+bv[7][15].z.value[0]+bv[7][16].z.value[0]+bv[7][17].z.value[0]+bv[7][18].z.value[0]+bv[7][19].z.value[0]+bv[7][20].z.value[0]+bv[7][21].z.value[0]+bv[7][22].z.value[0]+bv[7][23].z.value[0]+bv[7][24].z.value[0]+bv[7][25].z.value[0]+bv[7][26].z.value[0]+bv[7][27].z.value[0]+bv[7][28].z.value[0]+bv[7][29].z.value[0]+bv[7][30].z.value[0] == 6,
bv[8][1].z.value[0]+bv[8][2].z.value[0]+bv[8][3].z.value[0]+bv[8][4].z.value[0]+bv[8][5].z.value[0]+bv[8][6].z.value[0]+bv[8][7].z.value[0]+bv[8][8].z.value[0]+bv[8][9].z.value[0]+bv[8][10].z.value[0]+bv[8][11].z.value[0]+bv[8][12].z.value[0]+bv[8][13].z.value[0]+bv[8][14].z.value[0]+bv[8][15].z.value[0]+bv[8][16].z.value[0]+bv[8][17].z.value[0]+bv[8][18].z.value[0]+bv[8][19].z.value[0]+bv[8][20].z.value[0]+bv[8][21].z.value[0]+bv[8][22].z.value[0]+bv[8][23].z.value[0]+bv[8][24].z.value[0]+bv[8][25].z.value[0]+bv[8][26].z.value[0]+bv[8][27].z.value[0]+bv[8][28].z.value[0]+bv[8][29].z.value[0]+bv[8][30].z.value[0] == 3,
bv[9][1].z.value[0]+bv[9][2].z.value[0]+bv[9][3].z.value[0]+bv[9][4].z.value[0]+bv[9][5].z.value[0]+bv[9][6].z.value[0]+bv[9][7].z.value[0]+bv[9][8].z.value[0]+bv[9][9].z.value[0]+bv[9][10].z.value[0]+bv[9][11].z.value[0]+bv[9][12].z.value[0]+bv[9][13].z.value[0]+bv[9][14].z.value[0]+bv[9][15].z.value[0]+bv[9][16].z.value[0]+bv[9][17].z.value[0]+bv[9][18].z.value[0]+bv[9][19].z.value[0]+bv[9][20].z.value[0]+bv[9][21].z.value[0]+bv[9][22].z.value[0]+bv[9][23].z.value[0]+bv[9][24].z.value[0]+bv[9][25].z.value[0]+bv[9][26].z.value[0]+bv[9][27].z.value[0]+bv[9][28].z.value[0]+bv[9][29].z.value[0]+bv[9][30].z.value[0] == 3,
bv[10][1].z.value[0]+bv[10][2].z.value[0]+bv[10][3].z.value[0]+bv[10][4].z.value[0]+bv[10][5].z.value[0]+bv[10][6].z.value[0]+bv[10][7].z.value[0]+bv[10][8].z.value[0]+bv[10][9].z.value[0]+bv[10][10].z.value[0]+bv[10][11].z.value[0]+bv[10][12].z.value[0]+bv[10][13].z.value[0]+bv[10][14].z.value[0]+bv[10][15].z.value[0]+bv[10][16].z.value[0]+bv[10][17].z.value[0]+bv[10][18].z.value[0]+bv[10][19].z.value[0]+bv[10][20].z.value[0]+bv[10][21].z.value[0]+bv[10][22].z.value[0]+bv[10][23].z.value[0]+bv[10][24].z.value[0]+bv[10][25].z.value[0]+bv[10][26].z.value[0]+bv[10][27].z.value[0]+bv[10][28].z.value[0]+bv[10][29].z.value[0]+bv[10][30].z.value[0] == 3,
bv[11][1].z.value[0]+bv[11][2].z.value[0]+bv[11][3].z.value[0]+bv[11][4].z.value[0]+bv[11][5].z.value[0]+bv[11][6].z.value[0]+bv[11][7].z.value[0]+bv[11][8].z.value[0]+bv[11][9].z.value[0]+bv[11][10].z.value[0]+bv[11][11].z.value[0]+bv[11][12].z.value[0]+bv[11][13].z.value[0]+bv[11][14].z.value[0]+bv[11][15].z.value[0]+bv[11][16].z.value[0]+bv[11][17].z.value[0]+bv[11][18].z.value[0]+bv[11][19].z.value[0]+bv[11][20].z.value[0]+bv[11][21].z.value[0]+bv[11][22].z.value[0]+bv[11][23].z.value[0]+bv[11][24].z.value[0]+bv[11][25].z.value[0]+bv[11][26].z.value[0]+bv[11][27].z.value[0]+bv[11][28].z.value[0]+bv[11][29].z.value[0]+bv[11][30].z.value[0] == 2,
bv[12][1].z.value[0]+bv[12][2].z.value[0]+bv[12][3].z.value[0]+bv[12][4].z.value[0]+bv[12][5].z.value[0]+bv[12][6].z.value[0]+bv[12][7].z.value[0]+bv[12][8].z.value[0]+bv[12][9].z.value[0]+bv[12][10].z.value[0]+bv[12][11].z.value[0]+bv[12][12].z.value[0]+bv[12][13].z.value[0]+bv[12][14].z.value[0]+bv[12][15].z.value[0]+bv[12][16].z.value[0]+bv[12][17].z.value[0]+bv[12][18].z.value[0]+bv[12][19].z.value[0]+bv[12][20].z.value[0]+bv[12][21].z.value[0]+bv[12][22].z.value[0]+bv[12][23].z.value[0]+bv[12][24].z.value[0]+bv[12][25].z.value[0]+bv[12][26].z.value[0]+bv[12][27].z.value[0]+bv[12][28].z.value[0]+bv[12][29].z.value[0]+bv[12][30].z.value[0] == 8,
bv[13][1].z.value[0]+bv[13][2].z.value[0]+bv[13][3].z.value[0]+bv[13][4].z.value[0]+bv[13][5].z.value[0]+bv[13][6].z.value[0]+bv[13][7].z.value[0]+bv[13][8].z.value[0]+bv[13][9].z.value[0]+bv[13][10].z.value[0]+bv[13][11].z.value[0]+bv[13][12].z.value[0]+bv[13][13].z.value[0]+bv[13][14].z.value[0]+bv[13][15].z.value[0]+bv[13][16].z.value[0]+bv[13][17].z.value[0]+bv[13][18].z.value[0]+bv[13][19].z.value[0]+bv[13][20].z.value[0]+bv[13][21].z.value[0]+bv[13][22].z.value[0]+bv[13][23].z.value[0]+bv[13][24].z.value[0]+bv[13][25].z.value[0]+bv[13][26].z.value[0]+bv[13][27].z.value[0]+bv[13][28].z.value[0]+bv[13][29].z.value[0]+bv[13][30].z.value[0] == 6,
bv[14][1].z.value[0]+bv[14][2].z.value[0]+bv[14][3].z.value[0]+bv[14][4].z.value[0]+bv[14][5].z.value[0]+bv[14][6].z.value[0]+bv[14][7].z.value[0]+bv[14][8].z.value[0]+bv[14][9].z.value[0]+bv[14][10].z.value[0]+bv[14][11].z.value[0]+bv[14][12].z.value[0]+bv[14][13].z.value[0]+bv[14][14].z.value[0]+bv[14][15].z.value[0]+bv[14][16].z.value[0]+bv[14][17].z.value[0]+bv[14][18].z.value[0]+bv[14][19].z.value[0]+bv[14][20].z.value[0]+bv[14][21].z.value[0]+bv[14][22].z.value[0]+bv[14][23].z.value[0]+bv[14][24].z.value[0]+bv[14][25].z.value[0]+bv[14][26].z.value[0]+bv[14][27].z.value[0]+bv[14][28].z.value[0]+bv[14][29].z.value[0]+bv[14][30].z.value[0] == 12,
bv[15][1].z.value[0]+bv[15][2].z.value[0]+bv[15][3].z.value[0]+bv[15][4].z.value[0]+bv[15][5].z.value[0]+bv[15][6].z.value[0]+bv[15][7].z.value[0]+bv[15][8].z.value[0]+bv[15][9].z.value[0]+bv[15][10].z.value[0]+bv[15][11].z.value[0]+bv[15][12].z.value[0]+bv[15][13].z.value[0]+bv[15][14].z.value[0]+bv[15][15].z.value[0]+bv[15][16].z.value[0]+bv[15][17].z.value[0]+bv[15][18].z.value[0]+bv[15][19].z.value[0]+bv[15][20].z.value[0]+bv[15][21].z.value[0]+bv[15][22].z.value[0]+bv[15][23].z.value[0]+bv[15][24].z.value[0]+bv[15][25].z.value[0]+bv[15][26].z.value[0]+bv[15][27].z.value[0]+bv[15][28].z.value[0]+bv[15][29].z.value[0]+bv[15][30].z.value[0] == 12,
bv[16][1].z.value[0]+bv[16][2].z.value[0]+bv[16][3].z.value[0]+bv[16][4].z.value[0]+bv[16][5].z.value[0]+bv[16][6].z.value[0]+bv[16][7].z.value[0]+bv[16][8].z.value[0]+bv[16][9].z.value[0]+bv[16][10].z.value[0]+bv[16][11].z.value[0]+bv[16][12].z.value[0]+bv[16][13].z.value[0]+bv[16][14].z.value[0]+bv[16][15].z.value[0]+bv[16][16].z.value[0]+bv[16][17].z.value[0]+bv[16][18].z.value[0]+bv[16][19].z.value[0]+bv[16][20].z.value[0]+bv[16][21].z.value[0]+bv[16][22].z.value[0]+bv[16][23].z.value[0]+bv[16][24].z.value[0]+bv[16][25].z.value[0]+bv[16][26].z.value[0]+bv[16][27].z.value[0]+bv[16][28].z.value[0]+bv[16][29].z.value[0]+bv[16][30].z.value[0] == 5,
bv[17][1].z.value[0]+bv[17][2].z.value[0]+bv[17][3].z.value[0]+bv[17][4].z.value[0]+bv[17][5].z.value[0]+bv[17][6].z.value[0]+bv[17][7].z.value[0]+bv[17][8].z.value[0]+bv[17][9].z.value[0]+bv[17][10].z.value[0]+bv[17][11].z.value[0]+bv[17][12].z.value[0]+bv[17][13].z.value[0]+bv[17][14].z.value[0]+bv[17][15].z.value[0]+bv[17][16].z.value[0]+bv[17][17].z.value[0]+bv[17][18].z.value[0]+bv[17][19].z.value[0]+bv[17][20].z.value[0]+bv[17][21].z.value[0]+bv[17][22].z.value[0]+bv[17][23].z.value[0]+bv[17][24].z.value[0]+bv[17][25].z.value[0]+bv[17][26].z.value[0]+bv[17][27].z.value[0]+bv[17][28].z.value[0]+bv[17][29].z.value[0]+bv[17][30].z.value[0] == 10,
bv[18][1].z.value[0]+bv[18][2].z.value[0]+bv[18][3].z.value[0]+bv[18][4].z.value[0]+bv[18][5].z.value[0]+bv[18][6].z.value[0]+bv[18][7].z.value[0]+bv[18][8].z.value[0]+bv[18][9].z.value[0]+bv[18][10].z.value[0]+bv[18][11].z.value[0]+bv[18][12].z.value[0]+bv[18][13].z.value[0]+bv[18][14].z.value[0]+bv[18][15].z.value[0]+bv[18][16].z.value[0]+bv[18][17].z.value[0]+bv[18][18].z.value[0]+bv[18][19].z.value[0]+bv[18][20].z.value[0]+bv[18][21].z.value[0]+bv[18][22].z.value[0]+bv[18][23].z.value[0]+bv[18][24].z.value[0]+bv[18][25].z.value[0]+bv[18][26].z.value[0]+bv[18][27].z.value[0]+bv[18][28].z.value[0]+bv[18][29].z.value[0]+bv[18][30].z.value[0] == 11,
bv[19][1].z.value[0]+bv[19][2].z.value[0]+bv[19][3].z.value[0]+bv[19][4].z.value[0]+bv[19][5].z.value[0]+bv[19][6].z.value[0]+bv[19][7].z.value[0]+bv[19][8].z.value[0]+bv[19][9].z.value[0]+bv[19][10].z.value[0]+bv[19][11].z.value[0]+bv[19][12].z.value[0]+bv[19][13].z.value[0]+bv[19][14].z.value[0]+bv[19][15].z.value[0]+bv[19][16].z.value[0]+bv[19][17].z.value[0]+bv[19][18].z.value[0]+bv[19][19].z.value[0]+bv[19][20].z.value[0]+bv[19][21].z.value[0]+bv[19][22].z.value[0]+bv[19][23].z.value[0]+bv[19][24].z.value[0]+bv[19][25].z.value[0]+bv[19][26].z.value[0]+bv[19][27].z.value[0]+bv[19][28].z.value[0]+bv[19][29].z.value[0]+bv[19][30].z.value[0] == 4,
bv[20][1].z.value[0]+bv[20][2].z.value[0]+bv[20][3].z.value[0]+bv[20][4].z.value[0]+bv[20][5].z.value[0]+bv[20][6].z.value[0]+bv[20][7].z.value[0]+bv[20][8].z.value[0]+bv[20][9].z.value[0]+bv[20][10].z.value[0]+bv[20][11].z.value[0]+bv[20][12].z.value[0]+bv[20][13].z.value[0]+bv[20][14].z.value[0]+bv[20][15].z.value[0]+bv[20][16].z.value[0]+bv[20][17].z.value[0]+bv[20][18].z.value[0]+bv[20][19].z.value[0]+bv[20][20].z.value[0]+bv[20][21].z.value[0]+bv[20][22].z.value[0]+bv[20][23].z.value[0]+bv[20][24].z.value[0]+bv[20][25].z.value[0]+bv[20][26].z.value[0]+bv[20][27].z.value[0]+bv[20][28].z.value[0]+bv[20][29].z.value[0]+bv[20][30].z.value[0] == 12,
bv[21][1].z.value[0]+bv[21][2].z.value[0]+bv[21][3].z.value[0]+bv[21][4].z.value[0]+bv[21][5].z.value[0]+bv[21][6].z.value[0]+bv[21][7].z.value[0]+bv[21][8].z.value[0]+bv[21][9].z.value[0]+bv[21][10].z.value[0]+bv[21][11].z.value[0]+bv[21][12].z.value[0]+bv[21][13].z.value[0]+bv[21][14].z.value[0]+bv[21][15].z.value[0]+bv[21][16].z.value[0]+bv[21][17].z.value[0]+bv[21][18].z.value[0]+bv[21][19].z.value[0]+bv[21][20].z.value[0]+bv[21][21].z.value[0]+bv[21][22].z.value[0]+bv[21][23].z.value[0]+bv[21][24].z.value[0]+bv[21][25].z.value[0]+bv[21][26].z.value[0]+bv[21][27].z.value[0]+bv[21][28].z.value[0]+bv[21][29].z.value[0]+bv[21][30].z.value[0] == 7,
bv[22][1].z.value[0]+bv[22][2].z.value[0]+bv[22][3].z.value[0]+bv[22][4].z.value[0]+bv[22][5].z.value[0]+bv[22][6].z.value[0]+bv[22][7].z.value[0]+bv[22][8].z.value[0]+bv[22][9].z.value[0]+bv[22][10].z.value[0]+bv[22][11].z.value[0]+bv[22][12].z.value[0]+bv[22][13].z.value[0]+bv[22][14].z.value[0]+bv[22][15].z.value[0]+bv[22][16].z.value[0]+bv[22][17].z.value[0]+bv[22][18].z.value[0]+bv[22][19].z.value[0]+bv[22][20].z.value[0]+bv[22][21].z.value[0]+bv[22][22].z.value[0]+bv[22][23].z.value[0]+bv[22][24].z.value[0]+bv[22][25].z.value[0]+bv[22][26].z.value[0]+bv[22][27].z.value[0]+bv[22][28].z.value[0]+bv[22][29].z.value[0]+bv[22][30].z.value[0] == 14,
bv[23][1].z.value[0]+bv[23][2].z.value[0]+bv[23][3].z.value[0]+bv[23][4].z.value[0]+bv[23][5].z.value[0]+bv[23][6].z.value[0]+bv[23][7].z.value[0]+bv[23][8].z.value[0]+bv[23][9].z.value[0]+bv[23][10].z.value[0]+bv[23][11].z.value[0]+bv[23][12].z.value[0]+bv[23][13].z.value[0]+bv[23][14].z.value[0]+bv[23][15].z.value[0]+bv[23][16].z.value[0]+bv[23][17].z.value[0]+bv[23][18].z.value[0]+bv[23][19].z.value[0]+bv[23][20].z.value[0]+bv[23][21].z.value[0]+bv[23][22].z.value[0]+bv[23][23].z.value[0]+bv[23][24].z.value[0]+bv[23][25].z.value[0]+bv[23][26].z.value[0]+bv[23][27].z.value[0]+bv[23][28].z.value[0]+bv[23][29].z.value[0]+bv[23][30].z.value[0] == 11,
bv[24][1].z.value[0]+bv[24][2].z.value[0]+bv[24][3].z.value[0]+bv[24][4].z.value[0]+bv[24][5].z.value[0]+bv[24][6].z.value[0]+bv[24][7].z.value[0]+bv[24][8].z.value[0]+bv[24][9].z.value[0]+bv[24][10].z.value[0]+bv[24][11].z.value[0]+bv[24][12].z.value[0]+bv[24][13].z.value[0]+bv[24][14].z.value[0]+bv[24][15].z.value[0]+bv[24][16].z.value[0]+bv[24][17].z.value[0]+bv[24][18].z.value[0]+bv[24][19].z.value[0]+bv[24][20].z.value[0]+bv[24][21].z.value[0]+bv[24][22].z.value[0]+bv[24][23].z.value[0]+bv[24][24].z.value[0]+bv[24][25].z.value[0]+bv[24][26].z.value[0]+bv[24][27].z.value[0]+bv[24][28].z.value[0]+bv[24][29].z.value[0]+bv[24][30].z.value[0] == 4,
bv[25][1].z.value[0]+bv[25][2].z.value[0]+bv[25][3].z.value[0]+bv[25][4].z.value[0]+bv[25][5].z.value[0]+bv[25][6].z.value[0]+bv[25][7].z.value[0]+bv[25][8].z.value[0]+bv[25][9].z.value[0]+bv[25][10].z.value[0]+bv[25][11].z.value[0]+bv[25][12].z.value[0]+bv[25][13].z.value[0]+bv[25][14].z.value[0]+bv[25][15].z.value[0]+bv[25][16].z.value[0]+bv[25][17].z.value[0]+bv[25][18].z.value[0]+bv[25][19].z.value[0]+bv[25][20].z.value[0]+bv[25][21].z.value[0]+bv[25][22].z.value[0]+bv[25][23].z.value[0]+bv[25][24].z.value[0]+bv[25][25].z.value[0]+bv[25][26].z.value[0]+bv[25][27].z.value[0]+bv[25][28].z.value[0]+bv[25][29].z.value[0]+bv[25][30].z.value[0] == 10,
bv[1][1].z.value[0]+bv[2][1].z.value[0]+bv[3][1].z.value[0]+bv[4][1].z.value[0]+bv[5][1].z.value[0]+bv[6][1].z.value[0]+bv[7][1].z.value[0]+bv[8][1].z.value[0]+bv[9][1].z.value[0]+bv[10][1].z.value[0]+bv[11][1].z.value[0]+bv[12][1].z.value[0]+bv[13][1].z.value[0]+bv[14][1].z.value[0]+bv[15][1].z.value[0]+bv[16][1].z.value[0]+bv[17][1].z.value[0]+bv[18][1].z.value[0]+bv[19][1].z.value[0]+bv[20][1].z.value[0]+bv[21][1].z.value[0]+bv[22][1].z.value[0]+bv[23][1].z.value[0]+bv[24][1].z.value[0]+bv[25][1].z.value[0] == 2,
bv[1][2].z.value[0]+bv[2][2].z.value[0]+bv[3][2].z.value[0]+bv[4][2].z.value[0]+bv[5][2].z.value[0]+bv[6][2].z.value[0]+bv[7][2].z.value[0]+bv[8][2].z.value[0]+bv[9][2].z.value[0]+bv[10][2].z.value[0]+bv[11][2].z.value[0]+bv[12][2].z.value[0]+bv[13][2].z.value[0]+bv[14][2].z.value[0]+bv[15][2].z.value[0]+bv[16][2].z.value[0]+bv[17][2].z.value[0]+bv[18][2].z.value[0]+bv[19][2].z.value[0]+bv[20][2].z.value[0]+bv[21][2].z.value[0]+bv[22][2].z.value[0]+bv[23][2].z.value[0]+bv[24][2].z.value[0]+bv[25][2].z.value[0] == 2,
bv[1][3].z.value[0]+bv[2][3].z.value[0]+bv[3][3].z.value[0]+bv[4][3].z.value[0]+bv[5][3].z.value[0]+bv[6][3].z.value[0]+bv[7][3].z.value[0]+bv[8][3].z.value[0]+bv[9][3].z.value[0]+bv[10][3].z.value[0]+bv[11][3].z.value[0]+bv[12][3].z.value[0]+bv[13][3].z.value[0]+bv[14][3].z.value[0]+bv[15][3].z.value[0]+bv[16][3].z.value[0]+bv[17][3].z.value[0]+bv[18][3].z.value[0]+bv[19][3].z.value[0]+bv[20][3].z.value[0]+bv[21][3].z.value[0]+bv[22][3].z.value[0]+bv[23][3].z.value[0]+bv[24][3].z.value[0]+bv[25][3].z.value[0] == 2,
bv[1][4].z.value[0]+bv[2][4].z.value[0]+bv[3][4].z.value[0]+bv[4][4].z.value[0]+bv[5][4].z.value[0]+bv[6][4].z.value[0]+bv[7][4].z.value[0]+bv[8][4].z.value[0]+bv[9][4].z.value[0]+bv[10][4].z.value[0]+bv[11][4].z.value[0]+bv[12][4].z.value[0]+bv[13][4].z.value[0]+bv[14][4].z.value[0]+bv[15][4].z.value[0]+bv[16][4].z.value[0]+bv[17][4].z.value[0]+bv[18][4].z.value[0]+bv[19][4].z.value[0]+bv[20][4].z.value[0]+bv[21][4].z.value[0]+bv[22][4].z.value[0]+bv[23][4].z.value[0]+bv[24][4].z.value[0]+bv[25][4].z.value[0] == 10,
bv[1][5].z.value[0]+bv[2][5].z.value[0]+bv[3][5].z.value[0]+bv[4][5].z.value[0]+bv[5][5].z.value[0]+bv[6][5].z.value[0]+bv[7][5].z.value[0]+bv[8][5].z.value[0]+bv[9][5].z.value[0]+bv[10][5].z.value[0]+bv[11][5].z.value[0]+bv[12][5].z.value[0]+bv[13][5].z.value[0]+bv[14][5].z.value[0]+bv[15][5].z.value[0]+bv[16][5].z.value[0]+bv[17][5].z.value[0]+bv[18][5].z.value[0]+bv[19][5].z.value[0]+bv[20][5].z.value[0]+bv[21][5].z.value[0]+bv[22][5].z.value[0]+bv[23][5].z.value[0]+bv[24][5].z.value[0]+bv[25][5].z.value[0] == 8,
bv[1][6].z.value[0]+bv[2][6].z.value[0]+bv[3][6].z.value[0]+bv[4][6].z.value[0]+bv[5][6].z.value[0]+bv[6][6].z.value[0]+bv[7][6].z.value[0]+bv[8][6].z.value[0]+bv[9][6].z.value[0]+bv[10][6].z.value[0]+bv[11][6].z.value[0]+bv[12][6].z.value[0]+bv[13][6].z.value[0]+bv[14][6].z.value[0]+bv[15][6].z.value[0]+bv[16][6].z.value[0]+bv[17][6].z.value[0]+bv[18][6].z.value[0]+bv[19][6].z.value[0]+bv[20][6].z.value[0]+bv[21][6].z.value[0]+bv[22][6].z.value[0]+bv[23][6].z.value[0]+bv[24][6].z.value[0]+bv[25][6].z.value[0] == 10,
bv[1][7].z.value[0]+bv[2][7].z.value[0]+bv[3][7].z.value[0]+bv[4][7].z.value[0]+bv[5][7].z.value[0]+bv[6][7].z.value[0]+bv[7][7].z.value[0]+bv[8][7].z.value[0]+bv[9][7].z.value[0]+bv[10][7].z.value[0]+bv[11][7].z.value[0]+bv[12][7].z.value[0]+bv[13][7].z.value[0]+bv[14][7].z.value[0]+bv[15][7].z.value[0]+bv[16][7].z.value[0]+bv[17][7].z.value[0]+bv[18][7].z.value[0]+bv[19][7].z.value[0]+bv[20][7].z.value[0]+bv[21][7].z.value[0]+bv[22][7].z.value[0]+bv[23][7].z.value[0]+bv[24][7].z.value[0]+bv[25][7].z.value[0] == 4,
bv[1][8].z.value[0]+bv[2][8].z.value[0]+bv[3][8].z.value[0]+bv[4][8].z.value[0]+bv[5][8].z.value[0]+bv[6][8].z.value[0]+bv[7][8].z.value[0]+bv[8][8].z.value[0]+bv[9][8].z.value[0]+bv[10][8].z.value[0]+bv[11][8].z.value[0]+bv[12][8].z.value[0]+bv[13][8].z.value[0]+bv[14][8].z.value[0]+bv[15][8].z.value[0]+bv[16][8].z.value[0]+bv[17][8].z.value[0]+bv[18][8].z.value[0]+bv[19][8].z.value[0]+bv[20][8].z.value[0]+bv[21][8].z.value[0]+bv[22][8].z.value[0]+bv[23][8].z.value[0]+bv[24][8].z.value[0]+bv[25][8].z.value[0] == 6,
bv[1][9].z.value[0]+bv[2][9].z.value[0]+bv[3][9].z.value[0]+bv[4][9].z.value[0]+bv[5][9].z.value[0]+bv[6][9].z.value[0]+bv[7][9].z.value[0]+bv[8][9].z.value[0]+bv[9][9].z.value[0]+bv[10][9].z.value[0]+bv[11][9].z.value[0]+bv[12][9].z.value[0]+bv[13][9].z.value[0]+bv[14][9].z.value[0]+bv[15][9].z.value[0]+bv[16][9].z.value[0]+bv[17][9].z.value[0]+bv[18][9].z.value[0]+bv[19][9].z.value[0]+bv[20][9].z.value[0]+bv[21][9].z.value[0]+bv[22][9].z.value[0]+bv[23][9].z.value[0]+bv[24][9].z.value[0]+bv[25][9].z.value[0] == 9,
bv[1][10].z.value[0]+bv[2][10].z.value[0]+bv[3][10].z.value[0]+bv[4][10].z.value[0]+bv[5][10].z.value[0]+bv[6][10].z.value[0]+bv[7][10].z.value[0]+bv[8][10].z.value[0]+bv[9][10].z.value[0]+bv[10][10].z.value[0]+bv[11][10].z.value[0]+bv[12][10].z.value[0]+bv[13][10].z.value[0]+bv[14][10].z.value[0]+bv[15][10].z.value[0]+bv[16][10].z.value[0]+bv[17][10].z.value[0]+bv[18][10].z.value[0]+bv[19][10].z.value[0]+bv[20][10].z.value[0]+bv[21][10].z.value[0]+bv[22][10].z.value[0]+bv[23][10].z.value[0]+bv[24][10].z.value[0]+bv[25][10].z.value[0] == 7,
bv[1][11].z.value[0]+bv[2][11].z.value[0]+bv[3][11].z.value[0]+bv[4][11].z.value[0]+bv[5][11].z.value[0]+bv[6][11].z.value[0]+bv[7][11].z.value[0]+bv[8][11].z.value[0]+bv[9][11].z.value[0]+bv[10][11].z.value[0]+bv[11][11].z.value[0]+bv[12][11].z.value[0]+bv[13][11].z.value[0]+bv[14][11].z.value[0]+bv[15][11].z.value[0]+bv[16][11].z.value[0]+bv[17][11].z.value[0]+bv[18][11].z.value[0]+bv[19][11].z.value[0]+bv[20][11].z.value[0]+bv[21][11].z.value[0]+bv[22][11].z.value[0]+bv[23][11].z.value[0]+bv[24][11].z.value[0]+bv[25][11].z.value[0] == 5,
bv[1][12].z.value[0]+bv[2][12].z.value[0]+bv[3][12].z.value[0]+bv[4][12].z.value[0]+bv[5][12].z.value[0]+bv[6][12].z.value[0]+bv[7][12].z.value[0]+bv[8][12].z.value[0]+bv[9][12].z.value[0]+bv[10][12].z.value[0]+bv[11][12].z.value[0]+bv[12][12].z.value[0]+bv[13][12].z.value[0]+bv[14][12].z.value[0]+bv[15][12].z.value[0]+bv[16][12].z.value[0]+bv[17][12].z.value[0]+bv[18][12].z.value[0]+bv[19][12].z.value[0]+bv[20][12].z.value[0]+bv[21][12].z.value[0]+bv[22][12].z.value[0]+bv[23][12].z.value[0]+bv[24][12].z.value[0]+bv[25][12].z.value[0] == 7,
bv[1][13].z.value[0]+bv[2][13].z.value[0]+bv[3][13].z.value[0]+bv[4][13].z.value[0]+bv[5][13].z.value[0]+bv[6][13].z.value[0]+bv[7][13].z.value[0]+bv[8][13].z.value[0]+bv[9][13].z.value[0]+bv[10][13].z.value[0]+bv[11][13].z.value[0]+bv[12][13].z.value[0]+bv[13][13].z.value[0]+bv[14][13].z.value[0]+bv[15][13].z.value[0]+bv[16][13].z.value[0]+bv[17][13].z.value[0]+bv[18][13].z.value[0]+bv[19][13].z.value[0]+bv[20][13].z.value[0]+bv[21][13].z.value[0]+bv[22][13].z.value[0]+bv[23][13].z.value[0]+bv[24][13].z.value[0]+bv[25][13].z.value[0] == 6,
bv[1][14].z.value[0]+bv[2][14].z.value[0]+bv[3][14].z.value[0]+bv[4][14].z.value[0]+bv[5][14].z.value[0]+bv[6][14].z.value[0]+bv[7][14].z.value[0]+bv[8][14].z.value[0]+bv[9][14].z.value[0]+bv[10][14].z.value[0]+bv[11][14].z.value[0]+bv[12][14].z.value[0]+bv[13][14].z.value[0]+bv[14][14].z.value[0]+bv[15][14].z.value[0]+bv[16][14].z.value[0]+bv[17][14].z.value[0]+bv[18][14].z.value[0]+bv[19][14].z.value[0]+bv[20][14].z.value[0]+bv[21][14].z.value[0]+bv[22][14].z.value[0]+bv[23][14].z.value[0]+bv[24][14].z.value[0]+bv[25][14].z.value[0] == 8,
bv[1][15].z.value[0]+bv[2][15].z.value[0]+bv[3][15].z.value[0]+bv[4][15].z.value[0]+bv[5][15].z.value[0]+bv[6][15].z.value[0]+bv[7][15].z.value[0]+bv[8][15].z.value[0]+bv[9][15].z.value[0]+bv[10][15].z.value[0]+bv[11][15].z.value[0]+bv[12][15].z.value[0]+bv[13][15].z.value[0]+bv[14][15].z.value[0]+bv[15][15].z.value[0]+bv[16][15].z.value[0]+bv[17][15].z.value[0]+bv[18][15].z.value[0]+bv[19][15].z.value[0]+bv[20][15].z.value[0]+bv[21][15].z.value[0]+bv[22][15].z.value[0]+bv[23][15].z.value[0]+bv[24][15].z.value[0]+bv[25][15].z.value[0] == 5,
bv[1][16].z.value[0]+bv[2][16].z.value[0]+bv[3][16].z.value[0]+bv[4][16].z.value[0]+bv[5][16].z.value[0]+bv[6][16].z.value[0]+bv[7][16].z.value[0]+bv[8][16].z.value[0]+bv[9][16].z.value[0]+bv[10][16].z.value[0]+bv[11][16].z.value[0]+bv[12][16].z.value[0]+bv[13][16].z.value[0]+bv[14][16].z.value[0]+bv[15][16].z.value[0]+bv[16][16].z.value[0]+bv[17][16].z.value[0]+bv[18][16].z.value[0]+bv[19][16].z.value[0]+bv[20][16].z.value[0]+bv[21][16].z.value[0]+bv[22][16].z.value[0]+bv[23][16].z.value[0]+bv[24][16].z.value[0]+bv[25][16].z.value[0] == 7,
bv[1][17].z.value[0]+bv[2][17].z.value[0]+bv[3][17].z.value[0]+bv[4][17].z.value[0]+bv[5][17].z.value[0]+bv[6][17].z.value[0]+bv[7][17].z.value[0]+bv[8][17].z.value[0]+bv[9][17].z.value[0]+bv[10][17].z.value[0]+bv[11][17].z.value[0]+bv[12][17].z.value[0]+bv[13][17].z.value[0]+bv[14][17].z.value[0]+bv[15][17].z.value[0]+bv[16][17].z.value[0]+bv[17][17].z.value[0]+bv[18][17].z.value[0]+bv[19][17].z.value[0]+bv[20][17].z.value[0]+bv[21][17].z.value[0]+bv[22][17].z.value[0]+bv[23][17].z.value[0]+bv[24][17].z.value[0]+bv[25][17].z.value[0] == 4,
bv[1][18].z.value[0]+bv[2][18].z.value[0]+bv[3][18].z.value[0]+bv[4][18].z.value[0]+bv[5][18].z.value[0]+bv[6][18].z.value[0]+bv[7][18].z.value[0]+bv[8][18].z.value[0]+bv[9][18].z.value[0]+bv[10][18].z.value[0]+bv[11][18].z.value[0]+bv[12][18].z.value[0]+bv[13][18].z.value[0]+bv[14][18].z.value[0]+bv[15][18].z.value[0]+bv[16][18].z.value[0]+bv[17][18].z.value[0]+bv[18][18].z.value[0]+bv[19][18].z.value[0]+bv[20][18].z.value[0]+bv[21][18].z.value[0]+bv[22][18].z.value[0]+bv[23][18].z.value[0]+bv[24][18].z.value[0]+bv[25][18].z.value[0] == 6,
bv[1][19].z.value[0]+bv[2][19].z.value[0]+bv[3][19].z.value[0]+bv[4][19].z.value[0]+bv[5][19].z.value[0]+bv[6][19].z.value[0]+bv[7][19].z.value[0]+bv[8][19].z.value[0]+bv[9][19].z.value[0]+bv[10][19].z.value[0]+bv[11][19].z.value[0]+bv[12][19].z.value[0]+bv[13][19].z.value[0]+bv[14][19].z.value[0]+bv[15][19].z.value[0]+bv[16][19].z.value[0]+bv[17][19].z.value[0]+bv[18][19].z.value[0]+bv[19][19].z.value[0]+bv[20][19].z.value[0]+bv[21][19].z.value[0]+bv[22][19].z.value[0]+bv[23][19].z.value[0]+bv[24][19].z.value[0]+bv[25][19].z.value[0] == 7,
bv[1][20].z.value[0]+bv[2][20].z.value[0]+bv[3][20].z.value[0]+bv[4][20].z.value[0]+bv[5][20].z.value[0]+bv[6][20].z.value[0]+bv[7][20].z.value[0]+bv[8][20].z.value[0]+bv[9][20].z.value[0]+bv[10][20].z.value[0]+bv[11][20].z.value[0]+bv[12][20].z.value[0]+bv[13][20].z.value[0]+bv[14][20].z.value[0]+bv[15][20].z.value[0]+bv[16][20].z.value[0]+bv[17][20].z.value[0]+bv[18][20].z.value[0]+bv[19][20].z.value[0]+bv[20][20].z.value[0]+bv[21][20].z.value[0]+bv[22][20].z.value[0]+bv[23][20].z.value[0]+bv[24][20].z.value[0]+bv[25][20].z.value[0] == 6,
bv[1][21].z.value[0]+bv[2][21].z.value[0]+bv[3][21].z.value[0]+bv[4][21].z.value[0]+bv[5][21].z.value[0]+bv[6][21].z.value[0]+bv[7][21].z.value[0]+bv[8][21].z.value[0]+bv[9][21].z.value[0]+bv[10][21].z.value[0]+bv[11][21].z.value[0]+bv[12][21].z.value[0]+bv[13][21].z.value[0]+bv[14][21].z.value[0]+bv[15][21].z.value[0]+bv[16][21].z.value[0]+bv[17][21].z.value[0]+bv[18][21].z.value[0]+bv[19][21].z.value[0]+bv[20][21].z.value[0]+bv[21][21].z.value[0]+bv[22][21].z.value[0]+bv[23][21].z.value[0]+bv[24][21].z.value[0]+bv[25][21].z.value[0] == 6,
bv[1][22].z.value[0]+bv[2][22].z.value[0]+bv[3][22].z.value[0]+bv[4][22].z.value[0]+bv[5][22].z.value[0]+bv[6][22].z.value[0]+bv[7][22].z.value[0]+bv[8][22].z.value[0]+bv[9][22].z.value[0]+bv[10][22].z.value[0]+bv[11][22].z.value[0]+bv[12][22].z.value[0]+bv[13][22].z.value[0]+bv[14][22].z.value[0]+bv[15][22].z.value[0]+bv[16][22].z.value[0]+bv[17][22].z.value[0]+bv[18][22].z.value[0]+bv[19][22].z.value[0]+bv[20][22].z.value[0]+bv[21][22].z.value[0]+bv[22][22].z.value[0]+bv[23][22].z.value[0]+bv[24][22].z.value[0]+bv[25][22].z.value[0] == 11,
bv[1][23].z.value[0]+bv[2][23].z.value[0]+bv[3][23].z.value[0]+bv[4][23].z.value[0]+bv[5][23].z.value[0]+bv[6][23].z.value[0]+bv[7][23].z.value[0]+bv[8][23].z.value[0]+bv[9][23].z.value[0]+bv[10][23].z.value[0]+bv[11][23].z.value[0]+bv[12][23].z.value[0]+bv[13][23].z.value[0]+bv[14][23].z.value[0]+bv[15][23].z.value[0]+bv[16][23].z.value[0]+bv[17][23].z.value[0]+bv[18][23].z.value[0]+bv[19][23].z.value[0]+bv[20][23].z.value[0]+bv[21][23].z.value[0]+bv[22][23].z.value[0]+bv[23][23].z.value[0]+bv[24][23].z.value[0]+bv[25][23].z.value[0] == 5,
bv[1][24].z.value[0]+bv[2][24].z.value[0]+bv[3][24].z.value[0]+bv[4][24].z.value[0]+bv[5][24].z.value[0]+bv[6][24].z.value[0]+bv[7][24].z.value[0]+bv[8][24].z.value[0]+bv[9][24].z.value[0]+bv[10][24].z.value[0]+bv[11][24].z.value[0]+bv[12][24].z.value[0]+bv[13][24].z.value[0]+bv[14][24].z.value[0]+bv[15][24].z.value[0]+bv[16][24].z.value[0]+bv[17][24].z.value[0]+bv[18][24].z.value[0]+bv[19][24].z.value[0]+bv[20][24].z.value[0]+bv[21][24].z.value[0]+bv[22][24].z.value[0]+bv[23][24].z.value[0]+bv[24][24].z.value[0]+bv[25][24].z.value[0] == 7,
bv[1][25].z.value[0]+bv[2][25].z.value[0]+bv[3][25].z.value[0]+bv[4][25].z.value[0]+bv[5][25].z.value[0]+bv[6][25].z.value[0]+bv[7][25].z.value[0]+bv[8][25].z.value[0]+bv[9][25].z.value[0]+bv[10][25].z.value[0]+bv[11][25].z.value[0]+bv[12][25].z.value[0]+bv[13][25].z.value[0]+bv[14][25].z.value[0]+bv[15][25].z.value[0]+bv[16][25].z.value[0]+bv[17][25].z.value[0]+bv[18][25].z.value[0]+bv[19][25].z.value[0]+bv[20][25].z.value[0]+bv[21][25].z.value[0]+bv[22][25].z.value[0]+bv[23][25].z.value[0]+bv[24][25].z.value[0]+bv[25][25].z.value[0] == 6,
bv[1][26].z.value[0]+bv[2][26].z.value[0]+bv[3][26].z.value[0]+bv[4][26].z.value[0]+bv[5][26].z.value[0]+bv[6][26].z.value[0]+bv[7][26].z.value[0]+bv[8][26].z.value[0]+bv[9][26].z.value[0]+bv[10][26].z.value[0]+bv[11][26].z.value[0]+bv[12][26].z.value[0]+bv[13][26].z.value[0]+bv[14][26].z.value[0]+bv[15][26].z.value[0]+bv[16][26].z.value[0]+bv[17][26].z.value[0]+bv[18][26].z.value[0]+bv[19][26].z.value[0]+bv[20][26].z.value[0]+bv[21][26].z.value[0]+bv[22][26].z.value[0]+bv[23][26].z.value[0]+bv[24][26].z.value[0]+bv[25][26].z.value[0] == 8,
bv[1][27].z.value[0]+bv[2][27].z.value[0]+bv[3][27].z.value[0]+bv[4][27].z.value[0]+bv[5][27].z.value[0]+bv[6][27].z.value[0]+bv[7][27].z.value[0]+bv[8][27].z.value[0]+bv[9][27].z.value[0]+bv[10][27].z.value[0]+bv[11][27].z.value[0]+bv[12][27].z.value[0]+bv[13][27].z.value[0]+bv[14][27].z.value[0]+bv[15][27].z.value[0]+bv[16][27].z.value[0]+bv[17][27].z.value[0]+bv[18][27].z.value[0]+bv[19][27].z.value[0]+bv[20][27].z.value[0]+bv[21][27].z.value[0]+bv[22][27].z.value[0]+bv[23][27].z.value[0]+bv[24][27].z.value[0]+bv[25][27].z.value[0] == 7,
bv[1][28].z.value[0]+bv[2][28].z.value[0]+bv[3][28].z.value[0]+bv[4][28].z.value[0]+bv[5][28].z.value[0]+bv[6][28].z.value[0]+bv[7][28].z.value[0]+bv[8][28].z.value[0]+bv[9][28].z.value[0]+bv[10][28].z.value[0]+bv[11][28].z.value[0]+bv[12][28].z.value[0]+bv[13][28].z.value[0]+bv[14][28].z.value[0]+bv[15][28].z.value[0]+bv[16][28].z.value[0]+bv[17][28].z.value[0]+bv[18][28].z.value[0]+bv[19][28].z.value[0]+bv[20][28].z.value[0]+bv[21][28].z.value[0]+bv[22][28].z.value[0]+bv[23][28].z.value[0]+bv[24][28].z.value[0]+bv[25][28].z.value[0] == 7,
bv[1][29].z.value[0]+bv[2][29].z.value[0]+bv[3][29].z.value[0]+bv[4][29].z.value[0]+bv[5][29].z.value[0]+bv[6][29].z.value[0]+bv[7][29].z.value[0]+bv[8][29].z.value[0]+bv[9][29].z.value[0]+bv[10][29].z.value[0]+bv[11][29].z.value[0]+bv[12][29].z.value[0]+bv[13][29].z.value[0]+bv[14][29].z.value[0]+bv[15][29].z.value[0]+bv[16][29].z.value[0]+bv[17][29].z.value[0]+bv[18][29].z.value[0]+bv[19][29].z.value[0]+bv[20][29].z.value[0]+bv[21][29].z.value[0]+bv[22][29].z.value[0]+bv[23][29].z.value[0]+bv[24][29].z.value[0]+bv[25][29].z.value[0] == 2,
bv[1][30].z.value[0]+bv[2][30].z.value[0]+bv[3][30].z.value[0]+bv[4][30].z.value[0]+bv[5][30].z.value[0]+bv[6][30].z.value[0]+bv[7][30].z.value[0]+bv[8][30].z.value[0]+bv[9][30].z.value[0]+bv[10][30].z.value[0]+bv[11][30].z.value[0]+bv[12][30].z.value[0]+bv[13][30].z.value[0]+bv[14][30].z.value[0]+bv[15][30].z.value[0]+bv[16][30].z.value[0]+bv[17][30].z.value[0]+bv[18][30].z.value[0]+bv[19][30].z.value[0]+bv[20][30].z.value[0]+bv[21][30].z.value[0]+bv[22][30].z.value[0]+bv[23][30].z.value[0]+bv[24][30].z.value[0]+bv[25][30].z.value[0] == 2,
bv[1][1].z.value[0] == 0,
bv[1][2].z.value[0]+bv[2][1].z.value[0] == 0,
bv[1][3].z.value[0]+bv[2][2].z.value[0]+bv[3][1].z.value[0] == 0,
bv[1][4].z.value[0]+bv[2][3].z.value[0]+bv[3][2].z.value[0]+bv[4][1].z.value[0] == 0,
bv[1][5].z.value[0]+bv[2][4].z.value[0]+bv[3][3].z.value[0]+bv[4][2].z.value[0]+bv[5][1].z.value[0] == 0,
bv[1][6].z.value[0]+bv[2][5].z.value[0]+bv[3][4].z.value[0]+bv[4][3].z.value[0]+bv[5][2].z.value[0]+bv[6][1].z.value[0] == 1,
bv[1][7].z.value[0]+bv[2][6].z.value[0]+bv[3][5].z.value[0]+bv[4][4].z.value[0]+bv[5][3].z.value[0]+bv[6][2].z.value[0]+bv[7][1].z.value[0] == 3,
bv[1][8].z.value[0]+bv[2][7].z.value[0]+bv[3][6].z.value[0]+bv[4][5].z.value[0]+bv[5][4].z.value[0]+bv[6][3].z.value[0]+bv[7][2].z.value[0]+bv[8][1].z.value[0] == 2,
bv[1][9].z.value[0]+bv[2][8].z.value[0]+bv[3][7].z.value[0]+bv[4][6].z.value[0]+bv[5][5].z.value[0]+bv[6][4].z.value[0]+bv[7][3].z.value[0]+bv[8][2].z.value[0]+bv[9][1].z.value[0] == 2,
bv[1][10].z.value[0]+bv[2][9].z.value[0]+bv[3][8].z.value[0]+bv[4][7].z.value[0]+bv[5][6].z.value[0]+bv[6][5].z.value[0]+bv[7][4].z.value[0]+bv[8][3].z.value[0]+bv[9][2].z.value[0]+bv[10][1].z.value[0] == 3,
bv[1][11].z.value[0]+bv[2][10].z.value[0]+bv[3][9].z.value[0]+bv[4][8].z.value[0]+bv[5][7].z.value[0]+bv[6][6].z.value[0]+bv[7][5].z.value[0]+bv[8][4].z.value[0]+bv[9][3].z.value[0]+bv[10][2].z.value[0]+bv[11][1].z.value[0] == 3,
bv[1][12].z.value[0]+bv[2][11].z.value[0]+bv[3][10].z.value[0]+bv[4][9].z.value[0]+bv[5][8].z.value[0]+bv[6][7].z.value[0]+bv[7][6].z.value[0]+bv[8][5].z.value[0]+bv[9][4].z.value[0]+bv[10][3].z.value[0]+bv[11][2].z.value[0]+bv[12][1].z.value[0] == 3,
bv[1][13].z.value[0]+bv[2][12].z.value[0]+bv[3][11].z.value[0]+bv[4][10].z.value[0]+bv[5][9].z.value[0]+bv[6][8].z.value[0]+bv[7][7].z.value[0]+bv[8][6].z.value[0]+bv[9][5].z.value[0]+bv[10][4].z.value[0]+bv[11][3].z.value[0]+bv[12][2].z.value[0]+bv[13][1].z.value[0] == 1,
bv[1][14].z.value[0]+bv[2][13].z.value[0]+bv[3][12].z.value[0]+bv[4][11].z.value[0]+bv[5][10].z.value[0]+bv[6][9].z.value[0]+bv[7][8].z.value[0]+bv[8][7].z.value[0]+bv[9][6].z.value[0]+bv[10][5].z.value[0]+bv[11][4].z.value[0]+bv[12][3].z.value[0]+bv[13][2].z.value[0]+bv[14][1].z.value[0] == 4,
bv[1][15].z.value[0]+bv[2][14].z.value[0]+bv[3][13].z.value[0]+bv[4][12].z.value[0]+bv[5][11].z.value[0]+bv[6][10].z.value[0]+bv[7][9].z.value[0]+bv[8][8].z.value[0]+bv[9][7].z.value[0]+bv[10][6].z.value[0]+bv[11][5].z.value[0]+bv[12][4].z.value[0]+bv[13][3].z.value[0]+bv[14][2].z.value[0]+bv[15][1].z.value[0] == 3,
bv[1][16].z.value[0]+bv[2][15].z.value[0]+bv[3][14].z.value[0]+bv[4][13].z.value[0]+bv[5][12].z.value[0]+bv[6][11].z.value[0]+bv[7][10].z.value[0]+bv[8][9].z.value[0]+bv[9][8].z.value[0]+bv[10][7].z.value[0]+bv[11][6].z.value[0]+bv[12][5].z.value[0]+bv[13][4].z.value[0]+bv[14][3].z.value[0]+bv[15][2].z.value[0]+bv[16][1].z.value[0] == 3,
bv[1][17].z.value[0]+bv[2][16].z.value[0]+bv[3][15].z.value[0]+bv[4][14].z.value[0]+bv[5][13].z.value[0]+bv[6][12].z.value[0]+bv[7][11].z.value[0]+bv[8][10].z.value[0]+bv[9][9].z.value[0]+bv[10][8].z.value[0]+bv[11][7].z.value[0]+bv[12][6].z.value[0]+bv[13][5].z.value[0]+bv[14][4].z.value[0]+bv[15][3].z.value[0]+bv[16][2].z.value[0]+bv[17][1].z.value[0] == 4,
bv[1][18].z.value[0]+bv[2][17].z.value[0]+bv[3][16].z.value[0]+bv[4][15].z.value[0]+bv[5][14].z.value[0]+bv[6][13].z.value[0]+bv[7][12].z.value[0]+bv[8][11].z.value[0]+bv[9][10].z.value[0]+bv[10][9].z.value[0]+bv[11][8].z.value[0]+bv[12][7].z.value[0]+bv[13][6].z.value[0]+bv[14][5].z.value[0]+bv[15][4].z.value[0]+bv[16][3].z.value[0]+bv[17][2].z.value[0]+bv[18][1].z.value[0] == 5,
bv[1][19].z.value[0]+bv[2][18].z.value[0]+bv[3][17].z.value[0]+bv[4][16].z.value[0]+bv[5][15].z.value[0]+bv[6][14].z.value[0]+bv[7][13].z.value[0]+bv[8][12].z.value[0]+bv[9][11].z.value[0]+bv[10][10].z.value[0]+bv[11][9].z.value[0]+bv[12][8].z.value[0]+bv[13][7].z.value[0]+bv[14][6].z.value[0]+bv[15][5].z.value[0]+bv[16][4].z.value[0]+bv[17][3].z.value[0]+bv[18][2].z.value[0]+bv[19][1].z.value[0] == 3,
bv[1][20].z.value[0]+bv[2][19].z.value[0]+bv[3][18].z.value[0]+bv[4][17].z.value[0]+bv[5][16].z.value[0]+bv[6][15].z.value[0]+bv[7][14].z.value[0]+bv[8][13].z.value[0]+bv[9][12].z.value[0]+bv[10][11].z.value[0]+bv[11][10].z.value[0]+bv[12][9].z.value[0]+bv[13][8].z.value[0]+bv[14][7].z.value[0]+bv[15][6].z.value[0]+bv[16][5].z.value[0]+bv[17][4].z.value[0]+bv[18][3].z.value[0]+bv[19][2].z.value[0]+bv[20][1].z.value[0] == 5,
bv[1][21].z.value[0]+bv[2][20].z.value[0]+bv[3][19].z.value[0]+bv[4][18].z.value[0]+bv[5][17].z.value[0]+bv[6][16].z.value[0]+bv[7][15].z.value[0]+bv[8][14].z.value[0]+bv[9][13].z.value[0]+bv[10][12].z.value[0]+bv[11][11].z.value[0]+bv[12][10].z.value[0]+bv[13][9].z.value[0]+bv[14][8].z.value[0]+bv[15][7].z.value[0]+bv[16][6].z.value[0]+bv[17][5].z.value[0]+bv[18][4].z.value[0]+bv[19][3].z.value[0]+bv[20][2].z.value[0]+bv[21][1].z.value[0] == 5,
bv[1][22].z.value[0]+bv[2][21].z.value[0]+bv[3][20].z.value[0]+bv[4][19].z.value[0]+bv[5][18].z.value[0]+bv[6][17].z.value[0]+bv[7][16].z.value[0]+bv[8][15].z.value[0]+bv[9][14].z.value[0]+bv[10][13].z.value[0]+bv[11][12].z.value[0]+bv[12][11].z.value[0]+bv[13][10].z.value[0]+bv[14][9].z.value[0]+bv[15][8].z.value[0]+bv[16][7].z.value[0]+bv[17][6].z.value[0]+bv[18][5].z.value[0]+bv[19][4].z.value[0]+bv[20][3].z.value[0]+bv[21][2].z.value[0]+bv[22][1].z.value[0] == 6,
bv[1][23].z.value[0]+bv[2][22].z.value[0]+bv[3][21].z.value[0]+bv[4][20].z.value[0]+bv[5][19].z.value[0]+bv[6][18].z.value[0]+bv[7][17].z.value[0]+bv[8][16].z.value[0]+bv[9][15].z.value[0]+bv[10][14].z.value[0]+bv[11][13].z.value[0]+bv[12][12].z.value[0]+bv[13][11].z.value[0]+bv[14][10].z.value[0]+bv[15][9].z.value[0]+bv[16][8].z.value[0]+bv[17][7].z.value[0]+bv[18][6].z.value[0]+bv[19][5].z.value[0]+bv[20][4].z.value[0]+bv[21][3].z.value[0]+bv[22][2].z.value[0]+bv[23][1].z.value[0] == 3,
bv[1][24].z.value[0]+bv[2][23].z.value[0]+bv[3][22].z.value[0]+bv[4][21].z.value[0]+bv[5][20].z.value[0]+bv[6][19].z.value[0]+bv[7][18].z.value[0]+bv[8][17].z.value[0]+bv[9][16].z.value[0]+bv[10][15].z.value[0]+bv[11][14].z.value[0]+bv[12][13].z.value[0]+bv[13][12].z.value[0]+bv[14][11].z.value[0]+bv[15][10].z.value[0]+bv[16][9].z.value[0]+bv[17][8].z.value[0]+bv[18][7].z.value[0]+bv[19][6].z.value[0]+bv[20][5].z.value[0]+bv[21][4].z.value[0]+bv[22][3].z.value[0]+bv[23][2].z.value[0]+bv[24][1].z.value[0] == 8,
bv[1][25].z.value[0]+bv[2][24].z.value[0]+bv[3][23].z.value[0]+bv[4][22].z.value[0]+bv[5][21].z.value[0]+bv[6][20].z.value[0]+bv[7][19].z.value[0]+bv[8][18].z.value[0]+bv[9][17].z.value[0]+bv[10][16].z.value[0]+bv[11][15].z.value[0]+bv[12][14].z.value[0]+bv[13][13].z.value[0]+bv[14][12].z.value[0]+bv[15][11].z.value[0]+bv[16][10].z.value[0]+bv[17][9].z.value[0]+bv[18][8].z.value[0]+bv[19][7].z.value[0]+bv[20][6].z.value[0]+bv[21][5].z.value[0]+bv[22][4].z.value[0]+bv[23][3].z.value[0]+bv[24][2].z.value[0]+bv[25][1].z.value[0] == 5,
bv[1][26].z.value[0]+bv[2][25].z.value[0]+bv[3][24].z.value[0]+bv[4][23].z.value[0]+bv[5][22].z.value[0]+bv[6][21].z.value[0]+bv[7][20].z.value[0]+bv[8][19].z.value[0]+bv[9][18].z.value[0]+bv[10][17].z.value[0]+bv[11][16].z.value[0]+bv[12][15].z.value[0]+bv[13][14].z.value[0]+bv[14][13].z.value[0]+bv[15][12].z.value[0]+bv[16][11].z.value[0]+bv[17][10].z.value[0]+bv[18][9].z.value[0]+bv[19][8].z.value[0]+bv[20][7].z.value[0]+bv[21][6].z.value[0]+bv[22][5].z.value[0]+bv[23][4].z.value[0]+bv[24][3].z.value[0]+bv[25][2].z.value[0] == 3,
bv[1][27].z.value[0]+bv[2][26].z.value[0]+bv[3][25].z.value[0]+bv[4][24].z.value[0]+bv[5][23].z.value[0]+bv[6][22].z.value[0]+bv[7][21].z.value[0]+bv[8][20].z.value[0]+bv[9][19].z.value[0]+bv[10][18].z.value[0]+bv[11][17].z.value[0]+bv[12][16].z.value[0]+bv[13][15].z.value[0]+bv[14][14].z.value[0]+bv[15][13].z.value[0]+bv[16][12].z.value[0]+bv[17][11].z.value[0]+bv[18][10].z.value[0]+bv[19][9].z.value[0]+bv[20][8].z.value[0]+bv[21][7].z.value[0]+bv[22][6].z.value[0]+bv[23][5].z.value[0]+bv[24][4].z.value[0]+bv[25][3].z.value[0] == 2,
bv[1][28].z.value[0]+bv[2][27].z.value[0]+bv[3][26].z.value[0]+bv[4][25].z.value[0]+bv[5][24].z.value[0]+bv[6][23].z.value[0]+bv[7][22].z.value[0]+bv[8][21].z.value[0]+bv[9][20].z.value[0]+bv[10][19].z.value[0]+bv[11][18].z.value[0]+bv[12][17].z.value[0]+bv[13][16].z.value[0]+bv[14][15].z.value[0]+bv[15][14].z.value[0]+bv[16][13].z.value[0]+bv[17][12].z.value[0]+bv[18][11].z.value[0]+bv[19][10].z.value[0]+bv[20][9].z.value[0]+bv[21][8].z.value[0]+bv[22][7].z.value[0]+bv[23][6].z.value[0]+bv[24][5].z.value[0]+bv[25][4].z.value[0] == 4,
bv[1][29].z.value[0]+bv[2][28].z.value[0]+bv[3][27].z.value[0]+bv[4][26].z.value[0]+bv[5][25].z.value[0]+bv[6][24].z.value[0]+bv[7][23].z.value[0]+bv[8][22].z.value[0]+bv[9][21].z.value[0]+bv[10][20].z.value[0]+bv[11][19].z.value[0]+bv[12][18].z.value[0]+bv[13][17].z.value[0]+bv[14][16].z.value[0]+bv[15][15].z.value[0]+bv[16][14].z.value[0]+bv[17][13].z.value[0]+bv[18][12].z.value[0]+bv[19][11].z.value[0]+bv[20][10].z.value[0]+bv[21][9].z.value[0]+bv[22][8].z.value[0]+bv[23][7].z.value[0]+bv[24][6].z.value[0]+bv[25][5].z.value[0] == 5,
bv[1][30].z.value[0]+bv[2][29].z.value[0]+bv[3][28].z.value[0]+bv[4][27].z.value[0]+bv[5][26].z.value[0]+bv[6][25].z.value[0]+bv[7][24].z.value[0]+bv[8][23].z.value[0]+bv[9][22].z.value[0]+bv[10][21].z.value[0]+bv[11][20].z.value[0]+bv[12][19].z.value[0]+bv[13][18].z.value[0]+bv[14][17].z.value[0]+bv[15][16].z.value[0]+bv[16][15].z.value[0]+bv[17][14].z.value[0]+bv[18][13].z.value[0]+bv[19][12].z.value[0]+bv[20][11].z.value[0]+bv[21][10].z.value[0]+bv[22][9].z.value[0]+bv[23][8].z.value[0]+bv[24][7].z.value[0]+bv[25][6].z.value[0] == 7,
bv[2][30].z.value[0]+bv[3][29].z.value[0]+bv[4][28].z.value[0]+bv[5][27].z.value[0]+bv[6][26].z.value[0]+bv[7][25].z.value[0]+bv[8][24].z.value[0]+bv[9][23].z.value[0]+bv[10][22].z.value[0]+bv[11][21].z.value[0]+bv[12][20].z.value[0]+bv[13][19].z.value[0]+bv[14][18].z.value[0]+bv[15][17].z.value[0]+bv[16][16].z.value[0]+bv[17][15].z.value[0]+bv[18][14].z.value[0]+bv[19][13].z.value[0]+bv[20][12].z.value[0]+bv[21][11].z.value[0]+bv[22][10].z.value[0]+bv[23][9].z.value[0]+bv[24][8].z.value[0]+bv[25][7].z.value[0] == 7,
bv[3][30].z.value[0]+bv[4][29].z.value[0]+bv[5][28].z.value[0]+bv[6][27].z.value[0]+bv[7][26].z.value[0]+bv[8][25].z.value[0]+bv[9][24].z.value[0]+bv[10][23].z.value[0]+bv[11][22].z.value[0]+bv[12][21].z.value[0]+bv[13][20].z.value[0]+bv[14][19].z.value[0]+bv[15][18].z.value[0]+bv[16][17].z.value[0]+bv[17][16].z.value[0]+bv[18][15].z.value[0]+bv[19][14].z.value[0]+bv[20][13].z.value[0]+bv[21][12].z.value[0]+bv[22][11].z.value[0]+bv[23][10].z.value[0]+bv[24][9].z.value[0]+bv[25][8].z.value[0] == 7,
bv[4][30].z.value[0]+bv[5][29].z.value[0]+bv[6][28].z.value[0]+bv[7][27].z.value[0]+bv[8][26].z.value[0]+bv[9][25].z.value[0]+bv[10][24].z.value[0]+bv[11][23].z.value[0]+bv[12][22].z.value[0]+bv[13][21].z.value[0]+bv[14][20].z.value[0]+bv[15][19].z.value[0]+bv[16][18].z.value[0]+bv[17][17].z.value[0]+bv[18][16].z.value[0]+bv[19][15].z.value[0]+bv[20][14].z.value[0]+bv[21][13].z.value[0]+bv[22][12].z.value[0]+bv[23][11].z.value[0]+bv[24][10].z.value[0]+bv[25][9].z.value[0] == 7,
bv[5][30].z.value[0]+bv[6][29].z.value[0]+bv[7][28].z.value[0]+bv[8][27].z.value[0]+bv[9][26].z.value[0]+bv[10][25].z.value[0]+bv[11][24].z.value[0]+bv[12][23].z.value[0]+bv[13][22].z.value[0]+bv[14][21].z.value[0]+bv[15][20].z.value[0]+bv[16][19].z.value[0]+bv[17][18].z.value[0]+bv[18][17].z.value[0]+bv[19][16].z.value[0]+bv[20][15].z.value[0]+bv[21][14].z.value[0]+bv[22][13].z.value[0]+bv[23][12].z.value[0]+bv[24][11].z.value[0]+bv[25][10].z.value[0] == 7,
bv[6][30].z.value[0]+bv[7][29].z.value[0]+bv[8][28].z.value[0]+bv[9][27].z.value[0]+bv[10][26].z.value[0]+bv[11][25].z.value[0]+bv[12][24].z.value[0]+bv[13][23].z.value[0]+bv[14][22].z.value[0]+bv[15][21].z.value[0]+bv[16][20].z.value[0]+bv[17][19].z.value[0]+bv[18][18].z.value[0]+bv[19][17].z.value[0]+bv[20][16].z.value[0]+bv[21][15].z.value[0]+bv[22][14].z.value[0]+bv[23][13].z.value[0]+bv[24][12].z.value[0]+bv[25][11].z.value[0] == 4,
bv[7][30].z.value[0]+bv[8][29].z.value[0]+bv[9][28].z.value[0]+bv[10][27].z.value[0]+bv[11][26].z.value[0]+bv[12][25].z.value[0]+bv[13][24].z.value[0]+bv[14][23].z.value[0]+bv[15][22].z.value[0]+bv[16][21].z.value[0]+bv[17][20].z.value[0]+bv[18][19].z.value[0]+bv[19][18].z.value[0]+bv[20][17].z.value[0]+bv[21][16].z.value[0]+bv[22][15].z.value[0]+bv[23][14].z.value[0]+bv[24][13].z.value[0]+bv[25][12].z.value[0] == 4,
bv[8][30].z.value[0]+bv[9][29].z.value[0]+bv[10][28].z.value[0]+bv[11][27].z.value[0]+bv[12][26].z.value[0]+bv[13][25].z.value[0]+bv[14][24].z.value[0]+bv[15][23].z.value[0]+bv[16][22].z.value[0]+bv[17][21].z.value[0]+bv[18][20].z.value[0]+bv[19][19].z.value[0]+bv[20][18].z.value[0]+bv[21][17].z.value[0]+bv[22][16].z.value[0]+bv[23][15].z.value[0]+bv[24][14].z.value[0]+bv[25][13].z.value[0] == 4,
bv[9][30].z.value[0]+bv[10][29].z.value[0]+bv[11][28].z.value[0]+bv[12][27].z.value[0]+bv[13][26].z.value[0]+bv[14][25].z.value[0]+bv[15][24].z.value[0]+bv[16][23].z.value[0]+bv[17][22].z.value[0]+bv[18][21].z.value[0]+bv[19][20].z.value[0]+bv[20][19].z.value[0]+bv[21][18].z.value[0]+bv[22][17].z.value[0]+bv[23][16].z.value[0]+bv[24][15].z.value[0]+bv[25][14].z.value[0] == 4,
bv[10][30].z.value[0]+bv[11][29].z.value[0]+bv[12][28].z.value[0]+bv[13][27].z.value[0]+bv[14][26].z.value[0]+bv[15][25].z.value[0]+bv[16][24].z.value[0]+bv[17][23].z.value[0]+bv[18][22].z.value[0]+bv[19][21].z.value[0]+bv[20][20].z.value[0]+bv[21][19].z.value[0]+bv[22][18].z.value[0]+bv[23][17].z.value[0]+bv[24][16].z.value[0]+bv[25][15].z.value[0] == 4,
bv[11][30].z.value[0]+bv[12][29].z.value[0]+bv[13][28].z.value[0]+bv[14][27].z.value[0]+bv[15][26].z.value[0]+bv[16][25].z.value[0]+bv[17][24].z.value[0]+bv[18][23].z.value[0]+bv[19][22].z.value[0]+bv[20][21].z.value[0]+bv[21][20].z.value[0]+bv[22][19].z.value[0]+bv[23][18].z.value[0]+bv[24][17].z.value[0]+bv[25][16].z.value[0] == 4,
bv[12][30].z.value[0]+bv[13][29].z.value[0]+bv[14][28].z.value[0]+bv[15][27].z.value[0]+bv[16][26].z.value[0]+bv[17][25].z.value[0]+bv[18][24].z.value[0]+bv[19][23].z.value[0]+bv[20][22].z.value[0]+bv[21][21].z.value[0]+bv[22][20].z.value[0]+bv[23][19].z.value[0]+bv[24][18].z.value[0]+bv[25][17].z.value[0] == 6,
bv[13][30].z.value[0]+bv[14][29].z.value[0]+bv[15][28].z.value[0]+bv[16][27].z.value[0]+bv[17][26].z.value[0]+bv[18][25].z.value[0]+bv[19][24].z.value[0]+bv[20][23].z.value[0]+bv[21][22].z.value[0]+bv[22][21].z.value[0]+bv[23][20].z.value[0]+bv[24][19].z.value[0]+bv[25][18].z.value[0] == 5,
bv[14][30].z.value[0]+bv[15][29].z.value[0]+bv[16][28].z.value[0]+bv[17][27].z.value[0]+bv[18][26].z.value[0]+bv[19][25].z.value[0]+bv[20][24].z.value[0]+bv[21][23].z.value[0]+bv[22][22].z.value[0]+bv[23][21].z.value[0]+bv[24][20].z.value[0]+bv[25][19].z.value[0] == 6,
bv[15][30].z.value[0]+bv[16][29].z.value[0]+bv[17][28].z.value[0]+bv[18][27].z.value[0]+bv[19][26].z.value[0]+bv[20][25].z.value[0]+bv[21][24].z.value[0]+bv[22][23].z.value[0]+bv[23][22].z.value[0]+bv[24][21].z.value[0]+bv[25][20].z.value[0] == 4,
bv[16][30].z.value[0]+bv[17][29].z.value[0]+bv[18][28].z.value[0]+bv[19][27].z.value[0]+bv[20][26].z.value[0]+bv[21][25].z.value[0]+bv[22][24].z.value[0]+bv[23][23].z.value[0]+bv[24][22].z.value[0]+bv[25][21].z.value[0] == 5,
bv[17][30].z.value[0]+bv[18][29].z.value[0]+bv[19][28].z.value[0]+bv[20][27].z.value[0]+bv[21][26].z.value[0]+bv[22][25].z.value[0]+bv[23][24].z.value[0]+bv[24][23].z.value[0]+bv[25][22].z.value[0] == 5,
bv[18][30].z.value[0]+bv[19][29].z.value[0]+bv[20][28].z.value[0]+bv[21][27].z.value[0]+bv[22][26].z.value[0]+bv[23][25].z.value[0]+bv[24][24].z.value[0]+bv[25][23].z.value[0] == 4,
bv[19][30].z.value[0]+bv[20][29].z.value[0]+bv[21][28].z.value[0]+bv[22][27].z.value[0]+bv[23][26].z.value[0]+bv[24][25].z.value[0]+bv[25][24].z.value[0] == 1,
bv[20][30].z.value[0]+bv[21][29].z.value[0]+bv[22][28].z.value[0]+bv[23][27].z.value[0]+bv[24][26].z.value[0]+bv[25][25].z.value[0] == 1,
bv[21][30].z.value[0]+bv[22][29].z.value[0]+bv[23][28].z.value[0]+bv[24][27].z.value[0]+bv[25][26].z.value[0] == 0,
bv[22][30].z.value[0]+bv[23][29].z.value[0]+bv[24][28].z.value[0]+bv[25][27].z.value[0] == 0,
bv[23][30].z.value[0]+bv[24][29].z.value[0]+bv[25][28].z.value[0] == 0,
bv[24][30].z.value[0]+bv[25][29].z.value[0] == 0,
bv[25][30].z.value[0] == 0,
bv[1][30].z.value[0] == 0,
bv[1][29].z.value[0]+bv[2][30].z.value[0] == 0,
bv[1][28].z.value[0]+bv[2][29].z.value[0]+bv[3][30].z.value[0] == 0,
bv[1][27].z.value[0]+bv[2][28].z.value[0]+bv[3][29].z.value[0]+bv[4][30].z.value[0] == 0,
bv[1][26].z.value[0]+bv[2][27].z.value[0]+bv[3][28].z.value[0]+bv[4][29].z.value[0]+bv[5][30].z.value[0] == 0,
bv[1][25].z.value[0]+bv[2][26].z.value[0]+bv[3][27].z.value[0]+bv[4][28].z.value[0]+bv[5][29].z.value[0]+bv[6][30].z.value[0] == 0,
bv[1][24].z.value[0]+bv[2][25].z.value[0]+bv[3][26].z.value[0]+bv[4][27].z.value[0]+bv[5][28].z.value[0]+bv[6][29].z.value[0]+bv[7][30].z.value[0] == 1,
bv[1][23].z.value[0]+bv[2][24].z.value[0]+bv[3][25].z.value[0]+bv[4][26].z.value[0]+bv[5][27].z.value[0]+bv[6][28].z.value[0]+bv[7][29].z.value[0]+bv[8][30].z.value[0] == 2,
bv[1][22].z.value[0]+bv[2][23].z.value[0]+bv[3][24].z.value[0]+bv[4][25].z.value[0]+bv[5][26].z.value[0]+bv[6][27].z.value[0]+bv[7][28].z.value[0]+bv[8][29].z.value[0]+bv[9][30].z.value[0] == 3,
bv[1][21].z.value[0]+bv[2][22].z.value[0]+bv[3][23].z.value[0]+bv[4][24].z.value[0]+bv[5][25].z.value[0]+bv[6][26].z.value[0]+bv[7][27].z.value[0]+bv[8][28].z.value[0]+bv[9][29].z.value[0]+bv[10][30].z.value[0] == 1,
bv[1][20].z.value[0]+bv[2][21].z.value[0]+bv[3][22].z.value[0]+bv[4][23].z.value[0]+bv[5][24].z.value[0]+bv[6][25].z.value[0]+bv[7][26].z.value[0]+bv[8][27].z.value[0]+bv[9][28].z.value[0]+bv[10][29].z.value[0]+bv[11][30].z.value[0] == 2,
bv[1][19].z.value[0]+bv[2][20].z.value[0]+bv[3][21].z.value[0]+bv[4][22].z.value[0]+bv[5][23].z.value[0]+bv[6][24].z.value[0]+bv[7][25].z.value[0]+bv[8][26].z.value[0]+bv[9][27].z.value[0]+bv[10][28].z.value[0]+bv[11][29].z.value[0]+bv[12][30].z.value[0] == 3,
bv[1][18].z.value[0]+bv[2][19].z.value[0]+bv[3][20].z.value[0]+bv[4][21].z.value[0]+bv[5][22].z.value[0]+bv[6][23].z.value[0]+bv[7][24].z.value[0]+bv[8][25].z.value[0]+bv[9][26].z.value[0]+bv[10][27].z.value[0]+bv[11][28].z.value[0]+bv[12][29].z.value[0]+bv[13][30].z.value[0] == 4,
bv[1][17].z.value[0]+bv[2][18].z.value[0]+bv[3][19].z.value[0]+bv[4][20].z.value[0]+bv[5][21].z.value[0]+bv[6][22].z.value[0]+bv[7][23].z.value[0]+bv[8][24].z.value[0]+bv[9][25].z.value[0]+bv[10][26].z.value[0]+bv[11][27].z.value[0]+bv[12][28].z.value[0]+bv[13][29].z.value[0]+bv[14][30].z.value[0] == 3,
bv[1][16].z.value[0]+bv[2][17].z.value[0]+bv[3][18].z.value[0]+bv[4][19].z.value[0]+bv[5][20].z.value[0]+bv[6][21].z.value[0]+bv[7][22].z.value[0]+bv[8][23].z.value[0]+bv[9][24].z.value[0]+bv[10][25].z.value[0]+bv[11][26].z.value[0]+bv[12][27].z.value[0]+bv[13][28].z.value[0]+bv[14][29].z.value[0]+bv[15][30].z.value[0] == 5,
bv[1][15].z.value[0]+bv[2][16].z.value[0]+bv[3][17].z.value[0]+bv[4][18].z.value[0]+bv[5][19].z.value[0]+bv[6][20].z.value[0]+bv[7][21].z.value[0]+bv[8][22].z.value[0]+bv[9][23].z.value[0]+bv[10][24].z.value[0]+bv[11][25].z.value[0]+bv[12][26].z.value[0]+bv[13][27].z.value[0]+bv[14][28].z.value[0]+bv[15][29].z.value[0]+bv[16][30].z.value[0] == 5,
bv[1][14].z.value[0]+bv[2][15].z.value[0]+bv[3][16].z.value[0]+bv[4][17].z.value[0]+bv[5][18].z.value[0]+bv[6][19].z.value[0]+bv[7][20].z.value[0]+bv[8][21].z.value[0]+bv[9][22].z.value[0]+bv[10][23].z.value[0]+bv[11][24].z.value[0]+bv[12][25].z.value[0]+bv[13][26].z.value[0]+bv[14][27].z.value[0]+bv[15][28].z.value[0]+bv[16][29].z.value[0]+bv[17][30].z.value[0] == 3,
bv[1][13].z.value[0]+bv[2][14].z.value[0]+bv[3][15].z.value[0]+bv[4][16].z.value[0]+bv[5][17].z.value[0]+bv[6][18].z.value[0]+bv[7][19].z.value[0]+bv[8][20].z.value[0]+bv[9][21].z.value[0]+bv[10][22].z.value[0]+bv[11][23].z.value[0]+bv[12][24].z.value[0]+bv[13][25].z.value[0]+bv[14][26].z.value[0]+bv[15][27].z.value[0]+bv[16][28].z.value[0]+bv[17][29].z.value[0]+bv[18][30].z.value[0] == 3,
bv[1][12].z.value[0]+bv[2][13].z.value[0]+bv[3][14].z.value[0]+bv[4][15].z.value[0]+bv[5][16].z.value[0]+bv[6][17].z.value[0]+bv[7][18].z.value[0]+bv[8][19].z.value[0]+bv[9][20].z.value[0]+bv[10][21].z.value[0]+bv[11][22].z.value[0]+bv[12][23].z.value[0]+bv[13][24].z.value[0]+bv[14][25].z.value[0]+bv[15][26].z.value[0]+bv[16][27].z.value[0]+bv[17][28].z.value[0]+bv[18][29].z.value[0]+bv[19][30].z.value[0] == 2,
bv[1][11].z.value[0]+bv[2][12].z.value[0]+bv[3][13].z.value[0]+bv[4][14].z.value[0]+bv[5][15].z.value[0]+bv[6][16].z.value[0]+bv[7][17].z.value[0]+bv[8][18].z.value[0]+bv[9][19].z.value[0]+bv[10][20].z.value[0]+bv[11][21].z.value[0]+bv[12][22].z.value[0]+bv[13][23].z.value[0]+bv[14][24].z.value[0]+bv[15][25].z.value[0]+bv[16][26].z.value[0]+bv[17][27].z.value[0]+bv[18][28].z.value[0]+bv[19][29].z.value[0]+bv[20][30].z.value[0] == 4,
bv[1][10].z.value[0]+bv[2][11].z.value[0]+bv[3][12].z.value[0]+bv[4][13].z.value[0]+bv[5][14].z.value[0]+bv[6][15].z.value[0]+bv[7][16].z.value[0]+bv[8][17].z.value[0]+bv[9][18].z.value[0]+bv[10][19].z.value[0]+bv[11][20].z.value[0]+bv[12][21].z.value[0]+bv[13][22].z.value[0]+bv[14][23].z.value[0]+bv[15][24].z.value[0]+bv[16][25].z.value[0]+bv[17][26].z.value[0]+bv[18][27].z.value[0]+bv[19][28].z.value[0]+bv[20][29].z.value[0]+bv[21][30].z.value[0] == 5,
bv[1][9].z.value[0]+bv[2][10].z.value[0]+bv[3][11].z.value[0]+bv[4][12].z.value[0]+bv[5][13].z.value[0]+bv[6][14].z.value[0]+bv[7][15].z.value[0]+bv[8][16].z.value[0]+bv[9][17].z.value[0]+bv[10][18].z.value[0]+bv[11][19].z.value[0]+bv[12][20].z.value[0]+bv[13][21].z.value[0]+bv[14][22].z.value[0]+bv[15][23].z.value[0]+bv[16][24].z.value[0]+bv[17][25].z.value[0]+bv[18][26].z.value[0]+bv[19][27].z.value[0]+bv[20][28].z.value[0]+bv[21][29].z.value[0]+bv[22][30].z.value[0] == 4,
bv[1][8].z.value[0]+bv[2][9].z.value[0]+bv[3][10].z.value[0]+bv[4][11].z.value[0]+bv[5][12].z.value[0]+bv[6][13].z.value[0]+bv[7][14].z.value[0]+bv[8][15].z.value[0]+bv[9][16].z.value[0]+bv[10][17].z.value[0]+bv[11][18].z.value[0]+bv[12][19].z.value[0]+bv[13][20].z.value[0]+bv[14][21].z.value[0]+bv[15][22].z.value[0]+bv[16][23].z.value[0]+bv[17][24].z.value[0]+bv[18][25].z.value[0]+bv[19][26].z.value[0]+bv[20][27].z.value[0]+bv[21][28].z.value[0]+bv[22][29].z.value[0]+bv[23][30].z.value[0] == 4,
bv[1][7].z.value[0]+bv[2][8].z.value[0]+bv[3][9].z.value[0]+bv[4][10].z.value[0]+bv[5][11].z.value[0]+bv[6][12].z.value[0]+bv[7][13].z.value[0]+bv[8][14].z.value[0]+bv[9][15].z.value[0]+bv[10][16].z.value[0]+bv[11][17].z.value[0]+bv[12][18].z.value[0]+bv[13][19].z.value[0]+bv[14][20].z.value[0]+bv[15][21].z.value[0]+bv[16][22].z.value[0]+bv[17][23].z.value[0]+bv[18][24].z.value[0]+bv[19][25].z.value[0]+bv[20][26].z.value[0]+bv[21][27].z.value[0]+bv[22][28].z.value[0]+bv[23][29].z.value[0]+bv[24][30].z.value[0] == 6,
bv[1][6].z.value[0]+bv[2][7].z.value[0]+bv[3][8].z.value[0]+bv[4][9].z.value[0]+bv[5][10].z.value[0]+bv[6][11].z.value[0]+bv[7][12].z.value[0]+bv[8][13].z.value[0]+bv[9][14].z.value[0]+bv[10][15].z.value[0]+bv[11][16].z.value[0]+bv[12][17].z.value[0]+bv[13][18].z.value[0]+bv[14][19].z.value[0]+bv[15][20].z.value[0]+bv[16][21].z.value[0]+bv[17][22].z.value[0]+bv[18][23].z.value[0]+bv[19][24].z.value[0]+bv[20][25].z.value[0]+bv[21][26].z.value[0]+bv[22][27].z.value[0]+bv[23][28].z.value[0]+bv[24][29].z.value[0]+bv[25][30].z.value[0] == 9,
bv[1][5].z.value[0]+bv[2][6].z.value[0]+bv[3][7].z.value[0]+bv[4][8].z.value[0]+bv[5][9].z.value[0]+bv[6][10].z.value[0]+bv[7][11].z.value[0]+bv[8][12].z.value[0]+bv[9][13].z.value[0]+bv[10][14].z.value[0]+bv[11][15].z.value[0]+bv[12][16].z.value[0]+bv[13][17].z.value[0]+bv[14][18].z.value[0]+bv[15][19].z.value[0]+bv[16][20].z.value[0]+bv[17][21].z.value[0]+bv[18][22].z.value[0]+bv[19][23].z.value[0]+bv[20][24].z.value[0]+bv[21][25].z.value[0]+bv[22][26].z.value[0]+bv[23][27].z.value[0]+bv[24][28].z.value[0]+bv[25][29].z.value[0] == 8,
bv[1][4].z.value[0]+bv[2][5].z.value[0]+bv[3][6].z.value[0]+bv[4][7].z.value[0]+bv[5][8].z.value[0]+bv[6][9].z.value[0]+bv[7][10].z.value[0]+bv[8][11].z.value[0]+bv[9][12].z.value[0]+bv[10][13].z.value[0]+bv[11][14].z.value[0]+bv[12][15].z.value[0]+bv[13][16].z.value[0]+bv[14][17].z.value[0]+bv[15][18].z.value[0]+bv[16][19].z.value[0]+bv[17][20].z.value[0]+bv[18][21].z.value[0]+bv[19][22].z.value[0]+bv[20][23].z.value[0]+bv[21][24].z.value[0]+bv[22][25].z.value[0]+bv[23][26].z.value[0]+bv[24][27].z.value[0]+bv[25][28].z.value[0] == 3,
bv[1][3].z.value[0]+bv[2][4].z.value[0]+bv[3][5].z.value[0]+bv[4][6].z.value[0]+bv[5][7].z.value[0]+bv[6][8].z.value[0]+bv[7][9].z.value[0]+bv[8][10].z.value[0]+bv[9][11].z.value[0]+bv[10][12].z.value[0]+bv[11][13].z.value[0]+bv[12][14].z.value[0]+bv[13][15].z.value[0]+bv[14][16].z.value[0]+bv[15][17].z.value[0]+bv[16][18].z.value[0]+bv[17][19].z.value[0]+bv[18][20].z.value[0]+bv[19][21].z.value[0]+bv[20][22].z.value[0]+bv[21][23].z.value[0]+bv[22][24].z.value[0]+bv[23][25].z.value[0]+bv[24][26].z.value[0]+bv[25][27].z.value[0] == 4,
bv[1][2].z.value[0]+bv[2][3].z.value[0]+bv[3][4].z.value[0]+bv[4][5].z.value[0]+bv[5][6].z.value[0]+bv[6][7].z.value[0]+bv[7][8].z.value[0]+bv[8][9].z.value[0]+bv[9][10].z.value[0]+bv[10][11].z.value[0]+bv[11][12].z.value[0]+bv[12][13].z.value[0]+bv[13][14].z.value[0]+bv[14][15].z.value[0]+bv[15][16].z.value[0]+bv[16][17].z.value[0]+bv[17][18].z.value[0]+bv[18][19].z.value[0]+bv[19][20].z.value[0]+bv[20][21].z.value[0]+bv[21][22].z.value[0]+bv[22][23].z.value[0]+bv[23][24].z.value[0]+bv[24][25].z.value[0]+bv[25][26].z.value[0] == 2,
bv[1][1].z.value[0]+bv[2][2].z.value[0]+bv[3][3].z.value[0]+bv[4][4].z.value[0]+bv[5][5].z.value[0]+bv[6][6].z.value[0]+bv[7][7].z.value[0]+bv[8][8].z.value[0]+bv[9][9].z.value[0]+bv[10][10].z.value[0]+bv[11][11].z.value[0]+bv[12][12].z.value[0]+bv[13][13].z.value[0]+bv[14][14].z.value[0]+bv[15][15].z.value[0]+bv[16][16].z.value[0]+bv[17][17].z.value[0]+bv[18][18].z.value[0]+bv[19][19].z.value[0]+bv[20][20].z.value[0]+bv[21][21].z.value[0]+bv[22][22].z.value[0]+bv[23][23].z.value[0]+bv[24][24].z.value[0]+bv[25][25].z.value[0] == 4,
bv[2][1].z.value[0]+bv[3][2].z.value[0]+bv[4][3].z.value[0]+bv[5][4].z.value[0]+bv[6][5].z.value[0]+bv[7][6].z.value[0]+bv[8][7].z.value[0]+bv[9][8].z.value[0]+bv[10][9].z.value[0]+bv[11][10].z.value[0]+bv[12][11].z.value[0]+bv[13][12].z.value[0]+bv[14][13].z.value[0]+bv[15][14].z.value[0]+bv[16][15].z.value[0]+bv[17][16].z.value[0]+bv[18][17].z.value[0]+bv[19][18].z.value[0]+bv[20][19].z.value[0]+bv[21][20].z.value[0]+bv[22][21].z.value[0]+bv[23][22].z.value[0]+bv[24][23].z.value[0]+bv[25][24].z.value[0] == 7,
bv[3][1].z.value[0]+bv[4][2].z.value[0]+bv[5][3].z.value[0]+bv[6][4].z.value[0]+bv[7][5].z.value[0]+bv[8][6].z.value[0]+bv[9][7].z.value[0]+bv[10][8].z.value[0]+bv[11][9].z.value[0]+bv[12][10].z.value[0]+bv[13][11].z.value[0]+bv[14][12].z.value[0]+bv[15][13].z.value[0]+bv[16][14].z.value[0]+bv[17][15].z.value[0]+bv[18][16].z.value[0]+bv[19][17].z.value[0]+bv[20][18].z.value[0]+bv[21][19].z.value[0]+bv[22][20].z.value[0]+bv[23][21].z.value[0]+bv[24][22].z.value[0]+bv[25][23].z.value[0] == 7,
bv[4][1].z.value[0]+bv[5][2].z.value[0]+bv[6][3].z.value[0]+bv[7][4].z.value[0]+bv[8][5].z.value[0]+bv[9][6].z.value[0]+bv[10][7].z.value[0]+bv[11][8].z.value[0]+bv[12][9].z.value[0]+bv[13][10].z.value[0]+bv[14][11].z.value[0]+bv[15][12].z.value[0]+bv[16][13].z.value[0]+bv[17][14].z.value[0]+bv[18][15].z.value[0]+bv[19][16].z.value[0]+bv[20][17].z.value[0]+bv[21][18].z.value[0]+bv[22][19].z.value[0]+bv[23][20].z.value[0]+bv[24][21].z.value[0]+bv[25][22].z.value[0] == 6,
bv[5][1].z.value[0]+bv[6][2].z.value[0]+bv[7][3].z.value[0]+bv[8][4].z.value[0]+bv[9][5].z.value[0]+bv[10][6].z.value[0]+bv[11][7].z.value[0]+bv[12][8].z.value[0]+bv[13][9].z.value[0]+bv[14][10].z.value[0]+bv[15][11].z.value[0]+bv[16][12].z.value[0]+bv[17][13].z.value[0]+bv[18][14].z.value[0]+bv[19][15].z.value[0]+bv[20][16].z.value[0]+bv[21][17].z.value[0]+bv[22][18].z.value[0]+bv[23][19].z.value[0]+bv[24][20].z.value[0]+bv[25][21].z.value[0] == 7,
bv[6][1].z.value[0]+bv[7][2].z.value[0]+bv[8][3].z.value[0]+bv[9][4].z.value[0]+bv[10][5].z.value[0]+bv[11][6].z.value[0]+bv[12][7].z.value[0]+bv[13][8].z.value[0]+bv[14][9].z.value[0]+bv[15][10].z.value[0]+bv[16][11].z.value[0]+bv[17][12].z.value[0]+bv[18][13].z.value[0]+bv[19][14].z.value[0]+bv[20][15].z.value[0]+bv[21][16].z.value[0]+bv[22][17].z.value[0]+bv[23][18].z.value[0]+bv[24][19].z.value[0]+bv[25][20].z.value[0] == 11,
bv[7][1].z.value[0]+bv[8][2].z.value[0]+bv[9][3].z.value[0]+bv[10][4].z.value[0]+bv[11][5].z.value[0]+bv[12][6].z.value[0]+bv[13][7].z.value[0]+bv[14][8].z.value[0]+bv[15][9].z.value[0]+bv[16][10].z.value[0]+bv[17][11].z.value[0]+bv[18][12].z.value[0]+bv[19][13].z.value[0]+bv[20][14].z.value[0]+bv[21][15].z.value[0]+bv[22][16].z.value[0]+bv[23][17].z.value[0]+bv[24][18].z.value[0]+bv[25][19].z.value[0] == 6,
bv[8][1].z.value[0]+bv[9][2].z.value[0]+bv[10][3].z.value[0]+bv[11][4].z.value[0]+bv[12][5].z.value[0]+bv[13][6].z.value[0]+bv[14][7].z.value[0]+bv[15][8].z.value[0]+bv[16][9].z.value[0]+bv[17][10].z.value[0]+bv[18][11].z.value[0]+bv[19][12].z.value[0]+bv[20][13].z.value[0]+bv[21][14].z.value[0]+bv[22][15].z.value[0]+bv[23][16].z.value[0]+bv[24][17].z.value[0]+bv[25][18].z.value[0] == 6,
bv[9][1].z.value[0]+bv[10][2].z.value[0]+bv[11][3].z.value[0]+bv[12][4].z.value[0]+bv[13][5].z.value[0]+bv[14][6].z.value[0]+bv[15][7].z.value[0]+bv[16][8].z.value[0]+bv[17][9].z.value[0]+bv[18][10].z.value[0]+bv[19][11].z.value[0]+bv[20][12].z.value[0]+bv[21][13].z.value[0]+bv[22][14].z.value[0]+bv[23][15].z.value[0]+bv[24][16].z.value[0]+bv[25][17].z.value[0] == 4,
bv[10][1].z.value[0]+bv[11][2].z.value[0]+bv[12][3].z.value[0]+bv[13][4].z.value[0]+bv[14][5].z.value[0]+bv[15][6].z.value[0]+bv[16][7].z.value[0]+bv[17][8].z.value[0]+bv[18][9].z.value[0]+bv[19][10].z.value[0]+bv[20][11].z.value[0]+bv[21][12].z.value[0]+bv[22][13].z.value[0]+bv[23][14].z.value[0]+bv[24][15].z.value[0]+bv[25][16].z.value[0] == 5,
bv[11][1].z.value[0]+bv[12][2].z.value[0]+bv[13][3].z.value[0]+bv[14][4].z.value[0]+bv[15][5].z.value[0]+bv[16][6].z.value[0]+bv[17][7].z.value[0]+bv[18][8].z.value[0]+bv[19][9].z.value[0]+bv[20][10].z.value[0]+bv[21][11].z.value[0]+bv[22][12].z.value[0]+bv[23][13].z.value[0]+bv[24][14].z.value[0]+bv[25][15].z.value[0] == 7,
bv[12][1].z.value[0]+bv[13][2].z.value[0]+bv[14][3].z.value[0]+bv[15][4].z.value[0]+bv[16][5].z.value[0]+bv[17][6].z.value[0]+bv[18][7].z.value[0]+bv[19][8].z.value[0]+bv[20][9].z.value[0]+bv[21][10].z.value[0]+bv[22][11].z.value[0]+bv[23][12].z.value[0]+bv[24][13].z.value[0]+bv[25][14].z.value[0] == 6,
bv[13][1].z.value[0]+bv[14][2].z.value[0]+bv[15][3].z.value[0]+bv[16][4].z.value[0]+bv[17][5].z.value[0]+bv[18][6].z.value[0]+bv[19][7].z.value[0]+bv[20][8].z.value[0]+bv[21][9].z.value[0]+bv[22][10].z.value[0]+bv[23][11].z.value[0]+bv[24][12].z.value[0]+bv[25][13].z.value[0] == 4,
bv[14][1].z.value[0]+bv[15][2].z.value[0]+bv[16][3].z.value[0]+bv[17][4].z.value[0]+bv[18][5].z.value[0]+bv[19][6].z.value[0]+bv[20][7].z.value[0]+bv[21][8].z.value[0]+bv[22][9].z.value[0]+bv[23][10].z.value[0]+bv[24][11].z.value[0]+bv[25][12].z.value[0] == 6,
bv[15][1].z.value[0]+bv[16][2].z.value[0]+bv[17][3].z.value[0]+bv[18][4].z.value[0]+bv[19][5].z.value[0]+bv[20][6].z.value[0]+bv[21][7].z.value[0]+bv[22][8].z.value[0]+bv[23][9].z.value[0]+bv[24][10].z.value[0]+bv[25][11].z.value[0] == 4,
bv[16][1].z.value[0]+bv[17][2].z.value[0]+bv[18][3].z.value[0]+bv[19][4].z.value[0]+bv[20][5].z.value[0]+bv[21][6].z.value[0]+bv[22][7].z.value[0]+bv[23][8].z.value[0]+bv[24][9].z.value[0]+bv[25][10].z.value[0] == 5,
bv[17][1].z.value[0]+bv[18][2].z.value[0]+bv[19][3].z.value[0]+bv[20][4].z.value[0]+bv[21][5].z.value[0]+bv[22][6].z.value[0]+bv[23][7].z.value[0]+bv[24][8].z.value[0]+bv[25][9].z.value[0] == 1,
bv[18][1].z.value[0]+bv[19][2].z.value[0]+bv[20][3].z.value[0]+bv[21][4].z.value[0]+bv[22][5].z.value[0]+bv[23][6].z.value[0]+bv[24][7].z.value[0]+bv[25][8].z.value[0] == 0,
bv[19][1].z.value[0]+bv[20][2].z.value[0]+bv[21][3].z.value[0]+bv[22][4].z.value[0]+bv[23][5].z.value[0]+bv[24][6].z.value[0]+bv[25][7].z.value[0] == 0,
bv[20][1].z.value[0]+bv[21][2].z.value[0]+bv[22][3].z.value[0]+bv[23][4].z.value[0]+bv[24][5].z.value[0]+bv[25][6].z.value[0] == 0,
bv[21][1].z.value[0]+bv[22][2].z.value[0]+bv[23][3].z.value[0]+bv[24][4].z.value[0]+bv[25][5].z.value[0] == 0,
bv[22][1].z.value[0]+bv[23][2].z.value[0]+bv[24][3].z.value[0]+bv[25][4].z.value[0] == 0,
bv[23][1].z.value[0]+bv[24][2].z.value[0]+bv[25][3].z.value[0] == 0,
bv[24][1].z.value[0]+bv[25][2].z.value[0] == 0,
bv[25][1].z.value[0] == 0,
]
print len(constraints)
print len(constraints) - sum(constraints)
print obj
########NEW FILE########
__FILENAME__ = circuits
# An object oriented model of a circuit.
from cvxpy import *
import abc

class Node(object):
    """ A node connecting devices. """
    def __init__(self):
        self.voltage = Variable()
        self.current_flows = []

    # The current entering a node equals the current leaving the node.
    def constraints(self):
        return [sum(f for f in self.current_flows) == 0]

class Ground(Node):
    """ A node at 0 volts. """
    def constraints(self):
        return [self.voltage == 0] + super(Ground, self).constraints()
    
class Device(object):
    __metaclass__ = abc.ABCMeta
    """ A device on a circuit. """
    def __init__(self, pos_node, neg_node):
        self.pos_node = pos_node
        self.pos_node.current_flows.append(-self.current())
        self.neg_node = neg_node
        self.neg_node.current_flows.append(self.current())

    # The voltage drop on the device.
    @abc.abstractmethod
    def voltage(self):
        return NotImplemented

    # The current through the device.
    @abc.abstractmethod
    def current(self):
        return NotImplemented

    # Every path between two nodes has the same voltage drop.
    def constraints(self):
        return [self.pos_node.voltage - self.voltage() == self.neg_node.voltage]

class Resistor(Device):
    """ A resistor with V = R*I. """
    def __init__(self, pos_node, neg_node, resistance):
        self._current = Variable()
        self.resistance = resistance
        super(Resistor, self).__init__(pos_node, neg_node)

    def voltage(self):
        return -self.resistance*self.current()

    def current(self):
        return self._current

class VoltageSource(Device):
    """ A constant source of voltage. """
    def __init__(self, pos_node, neg_node, voltage):
        self._current = Variable()
        self._voltage = voltage
        super(VoltageSource, self).__init__(pos_node, neg_node)

    def voltage(self):
        return self._voltage

    def current(self):
        return self._current

class CurrentSource(Device):
    """ A constant source of current. """
    def __init__(self, pos_node, neg_node, current):
        self._current = current
        self._voltage = Variable()
        super(CurrentSource, self).__init__(pos_node, neg_node)

    def voltage(self):
        return self._voltage

    def current(self):
        return self._current

# # Create a simple circuit and find the current and voltage.
nodes = [Ground(),Node(),Node()]
# A 5 V battery
devices = [VoltageSource(nodes[0], nodes[2], 10)]
# A series of pairs of parallel resistors.
# 1/4 Ohm resistor and a 1 Ohm resistor in parallel.
devices.append( Resistor(nodes[0], nodes[1], 0.25) )
devices.append( Resistor(nodes[0], nodes[1], 1) )
# 4 Ohm resistor and a 1 Ohm resistor in parallel.
devices.append( Resistor(nodes[1], nodes[2], 4) )
devices.append( Resistor(nodes[1], nodes[2], 1) )

# Create the problem.
constraints = []
for obj in nodes + devices:
    constraints += obj.constraints()
Problem(Minimize(0), constraints).solve()
for node in nodes:
    print node.voltage.value
########NEW FILE########
__FILENAME__ = image_processing
from cvxpy import *
from itertools import izip, imap
import cvxopt
import pylab
import math

# create simple image
n = 32
img = cvxopt.matrix(0.0,(n,n))
img[1:2,1:2] = 0.5

# add noise
img = img + 0.1*cvxopt.uniform(n,n)

# show the image
plt = pylab.imshow(img)
plt.set_cmap('gray')
pylab.show()

# define the gradient functions
def grad(img, direction):
    m, n = img.size
    for i in range(m):
        for j in range(n):
            if direction == 'y' and j > 0 and j < m-1:
                yield img[i,j+1] - img[i,j-1]
            elif direction == 'x' and i > 0 and i < n-1:
                yield img[i+1,j] - img[i-1,j]
            else:
                yield 0.0

# take the gradients
img_gradx, img_grady = grad(img,'x'), grad(img,'y')

# filter them (remove ones with small magnitude)

def denoise(gradx, grady, thresh):
    for dx, dy in izip(gradx, grady):
         if math.sqrt(dx*dx + dy*dy) >= thresh: yield (dx,dy)
         else: yield (0.0,0.0)

denoise_gradx, denoise_grady = izip(*denoise(img_gradx, img_grady, 0.2))

# function to get boundary of image
def boundary(img):
    m, n = img.size
    for i in range(m):
        for j in range(n):
            if i == 0 or j == 0 or i == n-1 or j == n-1:
                yield img[i,j]

# now, reconstruct the image by solving a constrained least-squares problem
new_img = Variable(n,n)
gradx_obj = imap(square, (fx - gx for fx, gx in izip(grad(new_img,'x'),denoise_gradx)))
grady_obj = imap(square, (fy - gy for fy, gy in izip(grad(new_img,'y'),denoise_grady)))

p = Problem(
    Minimize(sum(gradx_obj) + sum(grady_obj)),
    list(px == 0 for px in boundary(new_img)))
p.solve()

# show the reconstructed image
plt = pylab.imshow(new_img.value)
plt.set_cmap('gray')
pylab.show()

print new_img.value
########NEW FILE########
__FILENAME__ = numpy_test
import numpy
import abc
class Meta(object):
    def __subclasscheck__(cls, subclass):
        print "hello"

    def __array_finalize__(self, obj):
        return 1

class Test(numpy.ndarray):
    def __init__(self, shape):
        pass

    def __coerce__(self, other):
        print other
        return (self,self)

    def __radd__(self, other):
        print other

    def __getattribute__(self, name):
        import pdb; pdb.set_trace()
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            raise AttributeError("'Test' object has no attribute 'affa'")

print issubclass(Test, Meta)
print issubclass(Meta, numpy.ndarray)
print issubclass(Test, numpy.ndarray)
print issubclass(numpy.ndarray, Test)

a = numpy.arange(2)
t = Test(1)
a + t
import pdb; pdb.set_trace()
########NEW FILE########
__FILENAME__ = optimal_control
from cvxpy import *
import cvxopt
# Problem data
T = 10
n,p = (10,5)
A = cvxopt.normal(n,n)
B = cvxopt.normal(n,p)
x_init = cvxopt.normal(n)
x_final = cvxopt.normal(n)

# Object oriented optimal control problem.
class Stage(object):
    def __init__(self, A, B, x_prev):
        self.x = Variable(n)
        self.u = Variable(p)
        self.cost = sum(square(self.u)) + sum(abs(self.x))
        self.constraint = (self.x == A*x_prev + B*self.u)

stages = [Stage(A, B, x_init)] 
for i in range(T):
    stages.append(Stage(A, B, stages[-1].x))

obj = sum(s.cost for s in stages)
constraints = [stages[-1].x == x_final]
map(constraints.append, (s.constraint for s in stages))
print Problem(Minimize(obj), constraints).solve()
########NEW FILE########
__FILENAME__ = stock_tradeoff
import cvxopt
import numpy
from cvxpy import *
from multiprocessing import Pool
from pylab import figure, show
import math

num_assets = 100
num_factors = 20

mu = cvxopt.exp( cvxopt.normal(num_assets) )
F = cvxopt.normal(num_assets, num_factors)
D = cvxopt.spdiag( cvxopt.uniform(num_assets) )
x = Variable(num_assets)
gamma = Parameter(sign="positive")

expected_return = mu.T * x
variance = square(norm2(F.T*x)) + square(norm2(D*x))

# construct portfolio optimization problem *once*
p = Problem(
    Maximize(expected_return - gamma * variance),
    [sum(x) == 1, x >= 0]
)

# encapsulate the allocation function
def allocate(gamma_value):
    gamma.value = gamma_value
    p.solve()
    w = x.value
    expected_return, risk = mu.T*w, w.T*(F*F.T + D*D)*w
    return (expected_return[0], math.sqrt(risk[0]))

# create a pool of workers and a grid of gamma values
pool = Pool(processes = 4)
gammas = numpy.logspace(-1, 2, num=100)

# compute allocation in parallel
mu, sqrt_sigma = zip(*pool.map(allocate, gammas))

# plot the result
fig = figure(1)
ax = fig.add_subplot(111)
ax.plot(sqrt_sigma, mu)
ax.set_ylabel('expected return')
ax.set_xlabel('portfolio risk')

show()
########NEW FILE########
__FILENAME__ = test
from cvxpy import *

import cvxopt
import numpy as np


# # Problem data.
# m = 100
# n = 30
# A = cvxopt.normal(m,n)
# b = cvxopt.normal(m)

# import cProfile
# # Construct the problem.
# x = Variable(n)
# u = m*[[1]]
# t = Variable(m,m)

# # objective = Minimize( sum(t) )
# # constraints = [0 <= t, t <= 1]
# # p = Problem(objective, constraints)

# # The optimal objective is returned by p.solve().
# cProfile.run("""
# sum(t)
# """)
# # The optimal value for x is stored in x.value.
# #print x.value
# # The optimal Lagrange multiplier for a constraint
# # is stored in constraint.dual_value.
# #print constraints[0].dual_value

class MyMeta(type):
    def __getitem__(self, key):
        print key
        return 2

    def __len__(self):
        return 1

    def __contains__(self, obj):
        print "hello"
        return 0


class Exp(object):
    def __add__(self, other):
        return 0

    def __radd__(self, other):
        return 1

    def __rmul__(self, other):
        print 1

    __array_priority__ = 100

import numpy as np
a = np.random.random((2,2))


class Bar1(object):
    __metaclass__ = MyMeta
    def __add__(self, rhs): return 0
    def __radd__(self, rhs): return 1
    def __lt__(self, rhs): return 0
    def __le__(self, rhs): return 1
    def __eq__(self, rhs): return 2
    def __ne__(self, rhs): return 3
    def __gt__(self, rhs): return 4
    def __ge__(self, rhs): return 5

    def __array_prepare__(self):
        print "hello"
        return self
    def __array_wrap__(self): 
        return self

    def __array__(self):
        print "Afafaf"
        arr = np.array([self], dtype="object")
        return arr

    __array_priority__ = 100

def override(name):
    if name == "equal":
        def ufunc(x, y):
            print y
            if isinstance(y, Bar1) or \
               isinstance(y, np.ndarray) and isinstance(y[0], Bar1):
                return NotImplemented
            return getattr(np, name)(x, y)
        return ufunc
    else:
        def ufunc(x, y):
            print y
            if isinstance(y, Bar1): 
                return NotImplemented
            return getattr(np, name)(x, y)
        return ufunc

np.set_numeric_ops(
    ** {
        ufunc : override(ufunc) for ufunc in (
            "less_equal", "equal", "greater_equal"
        )
    }
)

b = Bar1()
print a == b
print a <= b
print a + b
########NEW FILE########
__FILENAME__ = chebyshev
from __future__ import division

import cvxopt
import numpy as np
from pylab import *
import math

# from cvxpy import numpy as my_numpy

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Example: Compute and display the Chebyshev center of a 2D polyhedron
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe, "Convex Optimization"
# Joelle Skaf - 08/16/05
# (a figure is generated)
#
# The goal is to find the largest Euclidean ball (i.e. its center and
# radius) that lies in a polyhedron described by linear inequalites in this
# fashion: P = { x : a_i'*x <= b_i, i=1,...,m } where x is in R^2

# Create the problem

# variables
radius = Variable(1)
center = Variable(2)

# constraints
a1 = cvxopt.matrix([2,1], (2,1))
a2 = cvxopt.matrix([2,-1], (2,1))
a3 = cvxopt.matrix([-1,2], (2,1))
a4 = cvxopt.matrix([-1,-2], (2,1))

b = cvxopt.matrix(1, (4,1))


constraints = [ a1.T*center + np.linalg.norm(a1, 2)*radius <= b[0],
				a2.T*center + np.linalg.norm(a2, 2)*radius <= b[1],
				a3.T*center + np.linalg.norm(a3, 2)*radius <= b[2],
				a4.T*center + np.linalg.norm(a4, 2)*radius <= b[3] ]


# objective
objective = Maximize(radius)

p = Problem(objective, constraints)
# The optimal objective is returned by p.solve().
result = p.solve()
# The optimal value
print radius.value
print center.value
# Convert to 1D array.
center_val = np.asarray(center.value[:,0])


# Now let's plot it
x = np.linspace(-2, 2, 256,endpoint=True)
theta = np.linspace(0,2*np.pi,100)

# plot the constraints
plot( x, -x*a1[0]/a1[1] + b[0]/a1[1])
plot( x, -x*a2[0]/a2[1] + b[0]/a2[1])
plot( x, -x*a3[0]/a3[1] + b[0]/a3[1])
plot( x, -x*a4[0]/a4[1] + b[0]/a4[1])


# plot the solution
plot( center_val[0] + radius.value*cos(theta), center_val[1] + radius.value*sin(theta) )
plot( center_val[0], center_val[1], 'x', markersize=10 )

# label
title('Chebyshev Centering')
xlabel('x1')
ylabel('x2')

axis([-1, 1, -1, 1])

show()
########NEW FILE########
__FILENAME__ = deadzone
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Section 6.1.2: Residual minimization with deadzone penalty
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe "Convex Optimization"
# Joelle Skaf - 08/17/05
#
# The penalty function approximation problem has the form:
#               minimize    sum(deadzone(Ax - b))
# where 'deadzone' is the deadzone penalty function
#               deadzone(y) = max(abs(y)-1,0)

# Input data
m = 16
n = 8
A = cvxopt.normal(m,n)
b = cvxopt.normal(m,1)

# Formulate the problem
x = Variable(n)
objective = Minimize( sum_entries(max_elemwise( abs(A*x -b) - 1 , 0 )) )
p = Problem(objective, [])

# Solve it
print 'Computing the optimal solution of the deadzone approximation problem:'
p.solve()

print 'Optimal vector:'
print x.value

print 'Residual vector:'
print A*x.value - b


########NEW FILE########
__FILENAME__ = 1D_convolution
#!/usr/bin/env python

from cvxpy import *
import numpy as np
import random

from math import pi, sqrt, exp

def gauss(n=11,sigma=1):
    r = range(-int(n/2),int(n/2)+1)
    return [1 / (sigma * sqrt(2*pi)) * exp(-float(x)**2/(2*sigma**2)) for x in r]

np.random.seed(5)
random.seed(5)
DENSITY = 0.008
n = 1000
x = Variable(n)
# Create sparse signal.
signal = np.zeros(n)
nnz = 0
for i in range(n):
    if random.random() < DENSITY:
        signal[i] = random.uniform(0, 100)
        nnz += 1

# Gaussian kernel.
m = 51
kernel = gauss(m)

# Noisy signal.
std = 1
noise = np.random.normal(scale=std, size=n+m-1)
noisy_signal = conv(kernel, signal) + noise

gamma = Parameter(sign="positive")
fit = norm(conv(kernel, x) - noisy_signal, 2)
regularization = norm(x, 1)
constraints = [x >= 0]
gamma.value = 0.06
prob = Problem(Minimize(fit + gamma*regularization), constraints)
solver_options = {"NORMALIZE": True, "MAX_ITERS": 2500}
result = prob.solve(solver=SCS,
                    verbose=True,
                    solver_specific_opts=solver_options)
# Get problem matrix.
data, dims = prob.get_problem_data(solver=SCS)

# Plot result and fit.
import matplotlib.pyplot as plt
plt.plot(range(1000), signal, label="true signal")
plt.plot(range(1000), np.asarray(noisy_signal.value[:1000, 0]), label="noisy convolution")
plt.plot(range(1000), np.asarray(x.value[:,0]), label="recovered signal")
plt.legend(loc='upper right')
plt.show()

########NEW FILE########
__FILENAME__ = helloworld
#!/usr/bin/env python

from cvxpy import *
import numpy as np
import random

from math import pi, sqrt, exp

def gauss(n=11,sigma=1):
    r = range(-int(n/2),int(n/2)+1)
    return [1 / (sigma * sqrt(2*pi)) * exp(-float(x)**2/(2*sigma**2)) for x in r]

np.random.seed(5)
random.seed(5)
DENSITY = 0.1
n = 1000
x = Variable(n)
# Create sparse signal.
signal = np.zeros(n)
for i in range(n):
    if random.random() < DENSITY:
        signal[i] = random.uniform(1, 100)

# Gaussian kernel.
m = 100
kernel = gauss(m)

# Noisy signal.
noisy_signal = conv(kernel, signal).value + np.random.normal(n+m-1)

obj = norm(conv(kernel, x) - noisy_signal)
constraints = [x >= 0]
prob = Problem(Minimize(obj), constraints)
result = prob.solve(solver=SCS, verbose=True)

print norm(signal - x.value, 1).value
########NEW FILE########
__FILENAME__ = inpainting
from scipy import misc
import matplotlib.pyplot as plt
import numpy as np

l = misc.lena()
l = l.astype(np.float64, copy=False)
l = l/np.max(l) #rescale pixels into [0,1]

plt.imshow(l, cmap=plt.cm.gray)
#plt.show()

from PIL import Image, ImageDraw

num_lines = 5
width = 5
imshape = l.shape

def drawRandLine(draw,width):
    x = [np.random.randint(0,im.size[0]) for i in range(2)]
    y = [np.random.randint(0,im.size[1]) for i in range(2)]
    xy = zip(x,y)
    #fill gives the color
    draw.line(xy,fill=255,width=width)

im = Image.new("L",imshape)
draw = ImageDraw.Draw(im)
for i in range(num_lines):
    drawRandLine(draw,width)
del draw
# im.show()

err = np.asarray(im,dtype=np.bool)
r = l.copy()
r[err] = 1.0
plt.imshow(r, cmap=plt.cm.gray)

import itertools
idx2pair = np.nonzero(err)
idx2pair = zip(idx2pair[0].tolist(), idx2pair[1].tolist())
pair2idx = dict(itertools.izip(idx2pair, xrange(len(idx2pair))))
idx2pair = np.array(idx2pair) #convert back to numpy array

import scipy.sparse as sp
from cvxopt import spmatrix

def involvedpairs(pairs):
    ''' Get all the pixel pairs whose gradient involves an unknown pixel.
        Input should be a set or dictionary of pixel pair tuples
    '''
    for pair in pairs: #loop through unknown pixels
        yield pair

        left = (pair[0],pair[1]-1)
        if left[1] >= 0 and left not in pairs: #if 'left' in picture, and not already unknown
            yield left

        top = (pair[0]-1,pair[1])
        topright = (pair[0]-1,pair[1]+1)
        #if not on top boundary, top is fixed, and top not already touched by upper right pixel
        if pair[0] > 0 and top not in pairs and topright not in pairs:
            yield top

def formCOO(pair2idx, img):
    m, n = img.shape
    Is, Js, Vs, bs = [[],[]], [[],[]], [[],[]], [[],[]]
    row = 0

    for pixel1 in involvedpairs(pair2idx):
        bottom = (pixel1[0]+1,pixel1[1])
        right= (pixel1[0],pixel1[1]+1)

        for i, pixel2 in enumerate([bottom, right]):

            if pixel2[0] >= m or pixel2[1] >= n:
                bs[i].append(0)
                continue

            b = 0
            for j, pix in enumerate([pixel2, pixel1]):
                if pix in pair2idx: #unknown pixel
                    Is[i].append(row)
                    Js[i].append(pair2idx[pix])
                    Vs[i].append(pow(-1,j))
                else: #known pixel
                    b += pow(-1,j)*img[pix]
            bs[i].append(b)

        row += 1

    '''
        Form Gx and Gy such that the x-component of the gradient is Gx*x + bx,
        where x is an array representing the unknown pixel values.
    '''
    m = len(bs[0])
    n = len(pair2idx)

    Gx = spmatrix(Vs[1], Is[1], Js[1],(m,n))
    Gy = spmatrix(Vs[0], Is[0], Js[0],(m,n))

    bx = np.array(bs[1])
    by = np.array(bs[0])

    return Gx, Gy, bx, by


Gx, Gy, bx, by = formCOO(pair2idx, r)
import cvxpy as cp
m, n = Gx.size
x = cp.Variable(n)

#z = cp.vstack((x.__rmul__(Gx) + bx).T, (x.__rmul__(Gy) + by).T)
#z = cp.hstack(x.__rmul__(Gx) + bx, x.__rmul__(Gy) + by)
z = cp.Variable(m, 2)
constraints = [z[:, 0] == x.__rmul__(Gx) + bx,
               z[:, 1] == x.__rmul__(Gy) + by]

objective = cp.Minimize(sum([cp.norm(z[i,:]) for i in range(m)]))
p = cp.Problem(objective, constraints)
import cProfile
cProfile.run("""
result = p.solve(solver=cp.ECOS, verbose=True)
""")


########NEW FILE########
__FILENAME__ = performance
from cvxpy import *
from collections import namedtuple
import scipy.sparse as sp
n = 100
x = Variable(n*n)
# class testClass(object):
#   def __init__(self, x, y, z):
#       self.x = x
#       self.y = y
#       self.z = z
obj = Minimize(sum_entries(exp(x)))
prob = Problem(obj)
prob.solve(verbose=True)
# import cProfile
# # Point = namedtuple('Point', ['x', 'y', 'z'])
# cProfile.run("prob.solve()")
# cProfile.run("prob.solve()")
#cProfile.run("sp.eye(n*n).tocsc()")
#cProfile.run("[sp.eye(n*n).tolil()[0:1000,:] for i in range(n)] ")
# cProfile.run("[Point(i, i, i) for i in xrange(n*n)]")

# from qcml import QCML
# import numpy as np
# import ecos
# p = QCML()
# s = """
# dimensions m n

# variable x(n)
# parameter mu(n)
# parameter gamma positive
# parameter F(n,m)
# parameter D(n,n)
# maximize (mu'*x - gamma*(square(norm(F'*x)) + square(norm(D*x))))
#     sum(x) == 1
#     x >= 0
# """
# p.parse(s)
# p.canonicalize()
# n = 1000
# m = 1000
# F = np.random.randn(n, m)
# D = np.random.randn(n, n)
# p.dims = {'m': m}
# p.codegen('python')
# socp_data = p.prob2socp({'mu':1, 'gamma':1,'F':F,'D':D}, {'n': n})
# sol = ecos.solve(**socp_data)
# my_vars = p.socp2prob(sol['x'], {'n': n})

# import cvxpy as cvx
# import numpy as np
# n = 1000
# m = 1000
# F = np.random.randn(n, m)
# D = np.random.randn(n, n)
# x = cvx.Variable(n)
# obj = cvx.sum(x + cvx.square(cvx.norm(F.T*x)) + cvx.square(cvx.norm(D*x)))
# prob = cvx.Problem(cvx.Minimize(obj), [cvx.sum(x) == 1, x >= 0])
# import cProfile
# cProfile.run("""
# prob.solve(verbose=True)
# """)
########NEW FILE########
__FILENAME__ = portfolio
# simple_portfolio_data
from cvxpy import *
import numpy as np
np.random.seed(5)
n = 8000
pbar = (np.ones((n, 1)) * .03 +
        np.matrix(np.append(np.random.rand(n - 1, 1), 0)).T * .12)
S = np.matrix(np.random.randn(n, n))
S = S.T * S
S = S / np.max(np.abs(np.diag(S))) * .2
S[:, n - 1] = np.matrix(np.zeros((n, 1)))
S[n - 1, :] = np.matrix(np.zeros((1, n)))
x_unif = np.matrix(np.ones((n, 1))) / n

x = Variable(n)
mu = 1
ret = pbar.T * x
risk = quad_form(x, S)
objective = Minimize( -ret + mu * risk )

constraints_longonly = [sum_entries(x) == 1, x >= 0]

prob = Problem(objective, constraints_longonly)
#constraints_totalshort = [sum_entries(x) == 1, one.T * max(-x, 0) <= 0.5]
import time
print "starting problems"

start = time.clock()
prob.solve(verbose=True, solver=SCS)
elapsed = (time.clock() - start)
print "SCS time:", elapsed
print prob.value

start = time.clock()
prob.solve(verbose=True, solver=ECOS)
elapsed = (time.clock() - start)
print "ECOS time:", elapsed
print prob.value

start = time.clock()
prob.solve(verbose=True, solver=CVXOPT)
elapsed = (time.clock() - start)
print "CVXOPT time:", elapsed
print prob.value

# Results:
# n = 500, total 0.647 (SCS)
# parse 0.22
# SCS 0.429, ECOS 1.806, CVXOPT 2.434 (total)
# n = 1000, total 17.03892 (ECOS)
# parse .96
# ECOS 16.079496, CVXOPT 15.485536 (w/ parse), SCS 2.09
# n = 2000, total 14.488 (SCS)
# parse 3.8
# SCS 10.7, ECOS failed after 140.4, CVXOPT 121.834
# n = 4000, total 80.56 (SCS)
# parse 15.7
# SCS 64.8
# n = 8000
# CVXOPT time: 8082.954368
# ECOS time: 12651.672262 (12587.26)
# SCS time: 351.276727 (2.84e+02s)

########NEW FILE########
__FILENAME__ = portfolio_profiler
# simple_portfolio_data
from cvxpy import *
import numpy as np
import scipy.sparse as sp
np.random.seed(5)
n = 10000
m = 100
pbar = (np.ones((n, 1)) * .03 +
        np.matrix(np.append(np.random.rand(n - 1, 1), 0)).T * .12)

F = sp.rand(m, n, density=0.01)
F.data = np.ones(len(F.data))
D = sp.eye(n).tocoo()
D.data = np.random.randn(len(D.data))**2
# num_points=100 # number of points in each vector
# num_vects=m-1
# vals=[]
# for _ in range(num_vects):
#     vals.append(np.random.normal(size=num_points))
# vals.append(np.ones(num_points)*.03)
# Z = np.cov(vals)
Z = np.random.normal(size=(m, m))
Z = Z.T.dot(Z)
print Z.shape

x = Variable(n)
y = x.__rmul__(F)
mu = 1
ret = pbar.T * x
risk = square(norm(x.__rmul__(D))) + quad_form(y, Z)
objective = Minimize( -ret + mu * risk )

constraints_longonly = [sum_entries(x) == 1, x >= 0]

prob = Problem(objective, constraints_longonly)
#constraints_totalshort = [sum_entries(x) == 1, one.T * max(-x, 0) <= 0.5]
import time
print "starting problems"

start = time.clock()
prob.solve(verbose=True, solver=SCS)
elapsed = (time.clock() - start)
print "SCS time:", elapsed
print prob.value

start = time.clock()
prob.solve(verbose=True, solver=ECOS)
elapsed = (time.clock() - start)
print "ECOS time:", elapsed
print prob.value

start = time.clock()
prob.solve(verbose=True, solver=CVXOPT)
elapsed = (time.clock() - start)
print "CVXOPT time:", elapsed
print prob.value


########NEW FILE########
__FILENAME__ = feature_selection
from cvxpy import *
from mixed_integer import *
import cvxopt

# Feature selection on a linear kernel SVM classifier.
# Uses the Alternating Direction Method of Multipliers
# with a (non-convex) cardinality constraint.

# Generate data.
cvxopt.setseed(1)
N = 50
M = 40
n = 10
data = []
for i in range(N):
    data += [(1,cvxopt.normal(n, mean=1.0, std=2.0))]
for i in range(M):
    data += [(-1,cvxopt.normal(n, mean=-1.0, std=2.0))]

# Construct problem.
gamma = Parameter(sign="positive")
gamma.value = 0.1
# 'a' is a variable constrained to have at most 6 non-zero entries.
a = SparseVar(n,nonzeros=6)
b = Variable()

slack = [pos(1 - label*(sample.T*a - b)) for (label,sample) in data]
objective = Minimize(norm2(a) + gamma*sum(slack))
p = Problem(objective)
# Extensions can attach new solve methods to the CVXPY Problem class. 
p.solve(method="admm")

# Count misclassifications.
error = 0
for label,sample in data:
    if not label*(a.value.T*sample - b.value)[0] >= 0:
        error += 1

print "%s misclassifications" % error
print a.value
print b.value
########NEW FILE########
__FILENAME__ = integer_ls
from cvxpy import *
from ncvx.boolean import Boolean
import ncvx.branch_and_bound
import cvxopt

x = Boolean(3, name='x')
A = cvxopt.matrix([1,2,3,4,5,6,7,8,9], (3,3), tc='d')
z = cvxopt.matrix([3, 7, 9])

p = Problem(Minimize(sum(square(A*x - z)))).solve(method="branch and bound")

print x.value
print p

# even a simple problem like this introduces too many variables
# y = Boolean()
# Problem(Minimize(square(y - 0.5))).branch_and_bound()

########NEW FILE########
__FILENAME__ = admm_problem
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from noncvx_variable import NonCvxVariable
import cvxpy as cp
from cvxpy import settings as s

# Use ADMM to attempt non-convex problem.
def admm(self, rho=0.5, iterations=5, solver=cp.ECOS):
    objective,constr_map,dims = self.canonicalize()
    var_offsets,x_length = self.variables(objective, 
                                          constr_map[s.EQ] + constr_map[s.INEQ])
    noncvx_vars = [obj for obj in var_offsets.keys() if isinstance(obj, NonCvxVariable)]
    # Form ADMM problem.
    obj = self.objective.expr
    for var in noncvx_vars:
        obj = obj + (rho/2)*sum(cp.square(var - var.z + var.u))
    p = cp.Problem(cp.Minimize(obj), self.constraints)
    # ADMM loop
    for i in range(iterations):
        result = p.solve(solver=solver)
        for var in noncvx_vars:
            var.z.value = var.round(var.value + var.u.value)
            var.u.value = var.value - var.z.value
    # Fix noncvx variables and solve.
    fix_constr = []
    for var in noncvx_vars:
        fix_constr += var.fix(var.z.value)
    p = cp.Problem(self.objective, self.constraints + fix_constr)
    return p.solve(solver=solver)

# Add admm method to cp Problem.
cp.Problem.register_solve("admm", admm)
########NEW FILE########
__FILENAME__ = boolean
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from noncvx_variable import NonCvxVariable
from cvxpy.constraints.affine import AffLeqConstraint
import cvxopt

class BoolVar(NonCvxVariable):
    """ A boolean variable. """
    # Sets the initial z value to a matrix of 0.5's.
    def init_z(self):
        self.z.value = cvxopt.matrix(0.5, self.size, tc='d')

    # All values set rounded to zero or 1.
    def _round(self, matrix):
        for i,v in enumerate(matrix):
            matrix[i] = 0 if v < 0.5 else 1
        return matrix

    # Constrain all entries to be the value in the matrix.
    def _fix(self, matrix):
        return [self == matrix]

    # In the relaxation, we have 0 <= var <= 1.
    def _constraints(self):
        return [AffLeqConstraint(0, self._objective()),
                AffLeqConstraint(self._objective(), 1)]
########NEW FILE########
__FILENAME__ = choose
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from boolean import BoolVar
from cvxpy.constraints.affine import AffLeqConstraint, AffEqConstraint
import cvxopt

class SparseBoolVar(BoolVar):
    """ A variable with k 1's and all other entries 0. """
    def __init__(self, rows=1, cols=1, nonzeros=None, *args, **kwargs):
        self.k = nonzeros
        super(SparseBoolVar, self).__init__(rows, cols, *args, **kwargs)

    # Sets the initial z value to the expected value of each entry.
    def init_z(self):
        num_entries = float(self.size[0]*self.size[1])
        self.z.value = cvxopt.matrix(num_entries/self.k, self.size, tc='d')

    # The k-largest values are set to 1. The remainder are set to 0.
    def _round(self, matrix):
        v_ind = sorted(enumerate(matrix), key=lambda v: -v[1])
        for v in v_ind[0:self.k]:
            matrix[v[0]] = 1
        for v in v_ind[self.k:]:
            matrix[v[0]] = 0
        return matrix
########NEW FILE########
__FILENAME__ = integer
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from noncvx_variable import NonCvxVariable
from cvxpy.constraints.affine import AffLeqConstraint

class IntVar(NonCvxVariable):
    """ An integer variable. """
    # All values set rounded to the nearest integer.
    def _round(self, matrix):
        for i,v in enumerate(matrix):
            matrix[i] = round(v)
        return matrix

    # Constrain all entries to be the value in the matrix.
    def _fix(self, matrix):
        return [self == matrix]
########NEW FILE########
__FILENAME__ = noncvx_variable
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

import abc
import cvxpy
import cvxpy.interface as intf
import cvxopt

class NonCvxVariable(cvxpy.Variable):
    __metaclass__ = abc.ABCMeta
    def __init__(self, *args, **kwargs):
        super(NonCvxVariable, self).__init__(*args, **kwargs)
        self.z = cvxpy.Parameter(*self.size)
        self.init_z()
        self.u = cvxpy.Parameter(*self.size)
        self.u.value = cvxopt.matrix(0, self.size, tc='d')

    # Initializes the value of the replicant variable.
    def init_z(self):
        self.z.value = cvxopt.matrix(0, self.size, tc='d')

    # Verify that the matrix has the same dimensions as the variable.
    def validate_matrix(self, matrix):
        if self.size != intf.size(matrix):
            raise Exception(("The argument's dimensions must match "
                             "the variable's dimensions."))

    # Wrapper to validate matrix.
    def round(self, matrix):
        self.validate_matrix(matrix)
        return self._round(matrix)

    # Project the matrix into the space defined by the non-convex constraint.
    # Returns the updated matrix.
    @abc.abstractmethod
    def _round(matrix):
        return NotImplemented

    # Wrapper to validate matrix and update curvature.
    def fix(self, matrix):
        matrix = self.round(matrix)
        return self._fix(matrix)

    # Fix the variable so it obeys the non-convex constraint.
    @abc.abstractmethod
    def _fix(self, matrix):
        return NotImplemented
########NEW FILE########
__FILENAME__ = permutation
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from noncvx_variable import NonCvxVariable
from cvxpy.constraints.affine import AffLeqConstraint, AffEqConstraint
from itertools import product

class permutation(NonCvxVariable):
    """ A permutation matrix. """
    def __init__(self, size, *args, **kwargs):
        super(permutation, self).__init__(rows=size, cols=size, *args, **kwargs)

    # Recursively set the largest value to 1 and zero out the
    # rest of that value's row and column.
    def _round(self, matrix):
        dims = range(self.size[0])
        ind_val = [(i,j,matrix[i,j]) for (i,j) in product(dims, dims)]
        chosen = self.get_largest(ind_val, [])
        matrix *= 0 # Zero out the matrix.
        for i,j,v in chosen:
            matrix[i,j] = 1
        return matrix

    # Get the index of the largest value by magnitude, filter out
    # all entries in the same row or column, and recurse.
    def get_largest(self, ind_val, chosen):
        # The final list will have 1 entry per row/col.
        if len(ind_val) == 0:
            return chosen
        largest = max(ind_val, key=lambda tup: abs(tup[2]))
        ind_val = [tup for tup in ind_val if \
                   tup[0] != largest[0] and tup[1] != largest[1]]
        return self.get_largest(ind_val, chosen + [largest])

    # Constrain all entries to be zero that correspond to
    # zeros in the matrix.
    def _fix(self, matrix):
        return [self == matrix]

    # In the relaxation, 0 <= var <= 1 and sum(var) == k.
    def constraints(self):
        constraints = [AffLeqConstraint(0, self._objective()),
                       AffLeqConstraint(self._objective(), 1)]
        for i in range(self.size[0]):
            row_sum = sum(self[i,j] for j in range(self.size[0]))
            col_sum = sum(self[j,i] for j in range(self.size[0]))
            constraints += [AffEqConstraint(row_sum, 1),
                            AffEqConstraint(col_sum, 1)]
        return constraints

########NEW FILE########
__FILENAME__ = sparse_var
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from noncvx_variable import NonCvxVariable
import cvxpy.interface.matrix_utilities as intf

class SparseVar(NonCvxVariable):
    """ A variable with constrained cardinality. """
    # k - the maximum cardinality of the variable.
    def __init__(self, rows=1, cols=1, nonzeros=None, *args, **kwargs):
        self.k = nonzeros
        super(SparseVar, self).__init__(rows, cols, *args, **kwargs)

    # All values except k-largest (by magnitude) set to zero.
    def _round(self, matrix):
        v_ind = sorted(enumerate(matrix), key=lambda v: -abs(v[1]))
        for v in v_ind[self.k:]:
           matrix[v[0]] = 0
        return matrix

    # Constrain all entries to be zero that correspond to
    # zeros in the matrix.
    def _fix(self, matrix):
        constraints = []
        rows,cols = intf.size(matrix)
        for i in range(rows):
            for j in range(cols):
                if matrix[i,j] == 0:
                    constraints.append(self[i,j] == 0)
        return constraints
########NEW FILE########
__FILENAME__ = test_vars
"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import *
from mixed_integer import *
import cvxopt
import unittest

class TestVars(unittest.TestCase):
    """ Unit tests for the variable types. """
    def setUp(self):
        pass

    # Overriden method to handle lists and lower accuracy.
    def assertAlmostEqual(self, a, b):
        try:
            a = list(a)
            b = list(b)
            for i in range(len(a)):
                self.assertAlmostEqual(a[i], b[i])
        except Exception:
            super(TestVars, self).assertAlmostEqual(a,b,places=3)

    # Test boolean variable.
    def test_boolean(self):
        x = Variable(5,4)
        p = Problem(Minimize(sum(1-x) + sum(x)), [x == BoolVar(5,4)])
        result = p.solve(method="admm", solver="cvxopt")
        self.assertAlmostEqual(result, 20)
        for v in x.value:
            self.assertAlmostEqual(v*(1-v), 0)

        x = Variable()
        p = Problem(Minimize(sum(1-x) + sum(x)), [x == BoolVar(5,4)[0,0]])
        result = p.solve(method="admm", solver="cvxopt")
        self.assertAlmostEqual(result, 1)
        self.assertAlmostEqual(x.value*(1-x.value), 0)

    # Test choose variable.
    def test_choose(self):
        x = Variable(5,4)
        p = Problem(Minimize(sum(1-x) + sum(x)), 
                    [x == SparseBoolVar(5,4,nonzeros=4)])
        result = p.solve(method="admm", solver="cvxopt")
        self.assertAlmostEqual(result, 20)
        for v in x.value:
            self.assertAlmostEqual(v*(1-v), 0)
        self.assertAlmostEqual(sum(x.value), 4)

    # Test card variable.
    def test_card(self):
        x = SparseVar(5,nonzeros=3)
        p = Problem(Maximize(sum(x)),
            [x <= 1, x >= 0])
        result = p.solve(method="admm")
        self.assertAlmostEqual(result, 3)
        for v in x.value:
            self.assertAlmostEqual(v*(1-v), 0)
        self.assertAlmostEqual(sum(x.value), 3)

        #should be equivalent to x == choose
        x = Variable(5,4)
        c = SparseVar(5,4,nonzeros=4)
        b = BoolVar(5,4)
        p = Problem(Minimize(sum(1-x) + sum(x)), 
            [x == c, x == b])
        result = p.solve(method="admm")
        self.assertAlmostEqual(result, 20)
        for v in x.value:
            self.assertAlmostEqual(v*(1-v), 0)

    # Test permutation variable.
    def test_permutation(self):
        x = Variable(1,5)
        c = cvxopt.matrix([1,2,3,4,5]).T
        perm = permutation(5)
        p = Problem(Minimize(sum(x)), [x == c*perm])
        result = p.solve(method="admm")
        print perm.value
        print x.value
        self.assertAlmostEqual(result, 15)
        self.assertAlmostEqual(sorted(x.value), c)
########NEW FILE########
__FILENAME__ = boolean
from cvxpy.expressions.variables import Variable, IndexVariable
from cvxpy.expressions.constants import Parameter
import cvxpy.constraints.affine as aff
import cvxopt

class Boolean(Variable):
    def __init__(self, rows=1, cols=1, *args, **kwargs):
        self._LB = Parameter(rows, cols)
        self._LB.value = cvxopt.matrix(0,(rows, cols), tc='d')
        self._UB = Parameter(rows, cols)
        self._UB.value = cvxopt.matrix(1,(rows, cols), tc='d')
        self._fix_values = cvxopt.matrix(False,(rows, cols))
        super(Boolean, self).__init__(rows, cols, *args, **kwargs)

    # return a scalar view into a matrix of boolean variables
    def index_object(self, key):
        return IndexBoolean(self, key)

    def round(self):
        self.LB = cvxopt.matrix(self._rounded, self.size)
        self.UB = cvxopt.matrix(self._rounded, self.size)

    def relax(self):
        # if fix_value is true, do not change LB and UB
        for i, fixed in enumerate(self.fix_values):
            if not fixed:
                self.LB[i] = 0
                self.UB[i] = 1

    def set(self, value):
        if not isinstance(value, bool): raise "Must set to boolean value"
        self.LB = cvxopt.matrix(value, self.size)
        self.UB = cvxopt.matrix(value, self.size)
        self.fix_values = cvxopt.matrix(True, self.size)

    def unset(self):
        self.fix_values = cvxopt.matrix(False, self.size)

    @property
    def _rounded(self):
        # WARNING: attempts to access self.value
        if self.size == (1,1): return round(self.value)
        else: return [round(v) for v in self.value]

    @property
    def LB(self):
        return self._LB.value

    @LB.setter
    def LB(self, value):
        self._LB.value = value

    @property
    def UB(self):
        return self._UB.value

    @UB.setter
    def UB(self, value):
        self._UB.value = value

    @property
    def fix_values(self):
        return self._fix_values

    @fix_values.setter
    def fix_values(self, value):
        self._fix_values = value

class IndexBoolean(IndexVariable, Boolean):
    def __init__(self, parent, key):
        super(IndexBoolean, self).__init__(parent, key)
        self._LB = self.parent._LB[self.key]
        self._UB = self.parent._UB[self.key]

    def relax(self):
        if not self.fix_values:
            self.LB = 0
            self.UB = 1

    @property
    def LB(self):
        return self.parent._LB.value[self.key]

    @LB.setter
    def LB(self, value):
        self.parent._LB.value[self.key] = value

    @property
    def UB(self):
        return self.parent._UB.value[self.key]

    @UB.setter
    def UB(self, value):
        self.parent._UB.value[self.key] = value

    @property
    def fix_values(self):
        return self.parent._fix_values[self.key]

    @fix_values.setter
    def fix_values(self, value):
        self.parent._fix_values[self.key] = value

########NEW FILE########
__FILENAME__ = branch_and_bound
import cvxopt
import cvxpy.problems.problem as problem
import cvxpy.settings as s
from boolean import Boolean

def branch(booleans):
    bool_vals = (vi for b in booleans for vi in b if not vi.fix_values)
    # pick *a* boolean variable to branch on
    # choose the most ambivalent one (smallest distance to 0.5)
    # NOTE: if there are no boolean variables, will never branch
    return min(bool_vals, key=lambda x: abs(x.value - 0.5))

def bound(prob, booleans):
    # relax boolean constraints
    for bool_var in booleans: bool_var.relax()
    # solves relaxation
    lower_bound = prob._solve()
    if isinstance(lower_bound, str):
        lower_bound = float('inf')

    # round boolean variables and re-solve to obtain upper bound
    for bool_var in booleans: bool_var.round()
    upper_bound = prob._solve()
    if isinstance(upper_bound, str):
        upper_bound = float('inf')

    return {'gap': upper_bound - lower_bound,
            'ub': upper_bound,
            'lb': lower_bound,
            'obj': upper_bound,
            'sol': map(lambda x: x.value, booleans)}

def solve_wrapper(prob, i, booleans, depth, epsilon):
    if i > depth: return None

    # branch
    branch_var = branch(booleans)

    # try true branch
    branch_var.set(True)
    true_branch = bound(prob, booleans)

    # try false branch
    branch_var.set(False)
    false_branch = bound(prob, booleans)

    # keep track of best objective so far
    if true_branch['obj'] < false_branch['obj']:
        solution = true_branch
    else:
        solution = false_branch

    # update the bound
    solution['lb'] = min(true_branch['lb'],false_branch['lb'])
    solution['ub'] = min(true_branch['ub'],false_branch['ub'])

    # check if gap is small enough
    solution['gap'] = solution['ub'] - solution['lb']
    if solution['gap'] < epsilon:
        branch_var.unset()
        return solution

    # if the gap isn't small enough, we will choose a branch to go down
    def take_branch(true_or_false):
        branch_var.set(true_or_false)
        if true_or_false is True: branch_bools = true_branch['sol']
        else: branch_bools = false_branch['sol']
        # restore the values into the set of booleans
        for b, value in zip(booleans,branch_bools):
            b.save_value(value)
        return solve_wrapper(prob, i+1, booleans, depth, epsilon)

    # partition based on lower bounds
    if true_branch['lb'] < false_branch['lb']:
        true_subtree = take_branch(True)
        false_subtree = take_branch(False)
    else:
        false_subtree = take_branch(False)
        true_subtree = take_branch(True)

    # propagate best solution up the tree
    if true_subtree and false_subtree:
        if true_subtree['obj'] < false_subtree['obj']:
            return true_subtree
        return false_subtree
    if not false_subtree and true_subtree: return true_subtree
    if not true_subtree and false_subtree: return false_subtree

    # return best guess so far
    return solution

def branch_and_bound(self, depth=5, epsilon=1e-3):
    objective,constr_map, dims = self.canonicalize()

    variables = objective.variables()
    for constr in constr_map[s.EQ]:
        variables += constr.variables()
    for constr in constr_map[s.INEQ]:
        variables += constr.variables()

    booleans = [v for v in variables if isinstance(v, Boolean)]

    self.constraints.extend(b._LB <= b for b in booleans)
    self.constraints.extend(b <= b._UB for b in booleans)

    result = bound(self, booleans)

    # check if gap is small enough
    if result['gap'] < epsilon:
        return result['obj']
    result = solve_wrapper(self, 0, booleans, depth, epsilon)

    # set the boolean values to the solution
    for b, value in zip(booleans,result['sol']):
        b.save_value(value)
        b.fix_values = cvxopt.matrix(True, b.size)

    return result['obj']

# add branch and bound a solution method
problem.Problem.register_solve("branch and bound", branch_and_bound)

########NEW FILE########
__FILENAME__ = sudoku
from cvxpy import *
from ncvx.boolean import Boolean
import ncvx.branch_and_bound
import cvxopt
import cProfile, pstats

n = 9
# 9x9 sudoku grid
numbers = [Boolean(n,n), Boolean(n,n), Boolean(n,n),
           Boolean(n,n), Boolean(n,n), Boolean(n,n),
           Boolean(n,n), Boolean(n,n), Boolean(n,n)]

# TODO: 9*[Boolean(9,9)] doesn't work....

solution = cvxopt.matrix([
    [0, 5, 2, 3, 7, 1, 8, 6, 4],
    [6, 3, 7, 8, 0, 4, 5, 2, 1],
    [1, 4, 8, 5, 2 ,6, 3, 0, 7],
    [4, 7, 1, 2, 3, 0, 6, 5, 8],
    [3, 6, 5, 1, 4, 8, 0, 7, 2],
    [8, 2, 0, 6, 5, 7, 4, 1, 3],
    [5, 1, 6, 7, 8, 3, 2, 4, 0],
    [7, 0, 3, 4, 6, 2, 1, 8, 5],
    [2, 8, 4, 0, 1, 5, 7, 3, 6]
])


# partial grid
known =[(0,6), (0,7), (1,4), (1,5), (1,8), (2,0), (2,2), (2,7), (2,8),
        (3,0), (3,1), (4,0), (4,2), (4,4), (4,6), (4,8), (5,7), (5,8),
        (6,0), (6,1), (6,6), (6,8), (7,0), (7,3), (7,4), (8,1), (8,2)]

def row(x,r):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            if i == r: yield x[i,j]

def col(x,c):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            if j == c: yield x[i,j]

def block(x,b):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            # 0 block is r = 0,1, c = 0,1
            # 1 block is r = 0,1, c = 2,3
            # 2 block is r = 2,3, c = 0,1
            # 3 block is r = 2,3, c = 2,3
            if i // 3 == b // 3 and j // 3 == b % 3:
                yield x[i,j]

pr = cProfile.Profile()
pr.enable()
# create the suboku constraints
constraints = [sum(numbers) == 1]
for i in range(n):
    for num in range(n):
        constraints.append(sum(row(numbers[num], i)) == 1)
        constraints.append(sum(col(numbers[num], i)) == 1)
        constraints.append(sum(block(numbers[num], i)) == 1)
constraints.extend(numbers[solution[k]][k] == 1 for k in known)

# attempt to solve

p = Problem(Minimize(sum(map(square, [num[0,0] for num in numbers]))), constraints)
p.solve(method="branch and bound")
pr.disable()

ps = pstats.Stats(pr)
ps.sort_stats('tottime').print_stats(.5)

A = cvxopt.matrix(0,(n,n))
for i, num in enumerate(numbers):
    A += i * cvxopt.matrix(map(lambda x: int(round(x)),num.value), (9,9),tc='i')

print sum(A - solution)

########NEW FILE########
__FILENAME__ = sudoku_admm
from cvxpy import *
from mixed_integer import *
import cvxopt

n = 9
# 9x9 sudoku grid
numbers = Variable(n,n)

# TODO: 9*[Boolean(9,9)] doesn't work....

solution = cvxopt.matrix([
    [0, 5, 2, 3, 7, 1, 8, 6, 4],
    [6, 3, 7, 8, 0, 4, 5, 2, 1],
    [1, 4, 8, 5, 2 ,6, 3, 0, 7],
    [4, 7, 1, 2, 3, 0, 6, 5, 8],
    [3, 6, 5, 1, 4, 8, 0, 7, 2],
    [8, 2, 0, 6, 5, 7, 4, 1, 3],
    [5, 1, 6, 7, 8, 3, 2, 4, 0],
    [7, 0, 3, 4, 6, 2, 1, 8, 5],
    [2, 8, 4, 0, 1, 5, 7, 3, 6]
])


# partial grid
known =[(0,6), (0,7), (1,4), (1,5), (1,8), (2,0), (2,2), (2,7), (2,8),
        (3,0), (3,1), (4,0), (4,2), (4,4), (4,6), (4,8), (5,7), (5,8),
        (6,0), (6,1), (6,6), (6,8), (7,0), (7,3), (7,4), (8,1), (8,2)]

def row(x,r):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            if i == r: yield x[i,j]

def col(x,c):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            if j == c: yield x[i,j]

def block(x,b):
    m, n = x.size
    for i in xrange(m):
        for j in xrange(n):
            # 0 block is r = 0,1, c = 0,1
            # 1 block is r = 0,1, c = 2,3
            # 2 block is r = 2,3, c = 0,1
            # 3 block is r = 2,3, c = 2,3
            if i // 3 == b // 3 and j // 3 == b % 3:
                yield x[i,j]


# create the suboku constraints
perms = cvxopt.matrix(range(1,10)).T * permutation(n)
constraints = []
for i in range(n):
    constraints += [x == v for (x,v) in zip(row(numbers, i), perms)]
    constraints += [x == v for (x,v) in zip(row(numbers, i), perms)]
    constraints += [x == v for (x,v) in zip(block(numbers, i), perms)]
constraints.extend(numbers[k] == solution[k] for k in known)

# attempt to solve
p = Problem(Minimize(sum(abs(numbers-solution))), constraints)
p.solve(method="admm")
print sum(numbers.value - solution)
########NEW FILE########
__FILENAME__ = three_sat
from cvxpy import *
from mixed_integer import *
import random 

# 3-SAT problem solved with non-convex ADMM
# TODO initialize z's at 0.5
EPSILON = 1e-8
MAX_ITER = 10

# Randomly generate a feasible 3-SAT problem.
VARIABLES = 30
CLAUSES_PER_VARIABLE = 3

# The 3-SAT solution.
solution = [random.random() < 0.5 for i in range(VARIABLES)]

# The 3-SAT clauses.
clauses = []
for i in range(VARIABLES*CLAUSES_PER_VARIABLE):
    clause_vars = random.sample(range(VARIABLES), 3)
    # Which variables are negated in the clause?
    while True:
        negated = [random.random() < 0.5 for j in range(3)]
        # Must be consistent with the solution.
        result = False
        for index,negation in zip(clause_vars,negated):
            result |= negation ^ solution[index]
        if result:
            break
    clauses.append( (clause_vars, negated) )

# The 3-SAT variables.
vars = [BoolVar() for i in range(VARIABLES)]

# The 3-SAT constraints.
constraints = []
for clause_vars,negated in clauses:
    terms = []
    for index,negation in zip(clause_vars,negated):
        if negation:
            terms.append( (1-vars[index]) )
        else:
            terms.append(vars[index])
    constraints.append(sum(terms) >= 1)

best_values = VARIABLES*[0]
best_match = 0
best_rho = 0
for i in range(MAX_ITER):
    p = Problem(Minimize(0), constraints)
    rho = random.random()
    result = p.solve(method="admm", rho=rho, 
                     iterations=2, solver="cvxopt")

    # Store the result.
    values = [vars[i].value for i in range(VARIABLES)]

    # What percentage of the clauses were satisfied?
    satisfied = []
    for clause_vars,negated in clauses:
        result = False
        for index,negation in zip(clause_vars,negated):
            if negation:
                result |= vars[index].value <= EPSILON
            else:
                result |= vars[index].value > EPSILON
        satisfied.append(result)

    if sum(satisfied) > best_match:
        best_values = values
        best_match = sum(satisfied)
        best_rho = rho
    if best_match == len(clauses): break

percent_satisfied = 100*best_match/len(clauses)
print "%s%% of the clauses were satisfied." % percent_satisfied
########NEW FILE########
__FILENAME__ = ex_4_3
# for decimal division
from __future__ import division

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Example: CVX Textbook exercise 4.3: Solve a simple QP with inequality constraints
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below


# From Boyd & Vandenberghe, "Convex Optimization"
# Joelle Skaf - 09/26/05
#
# Solves the following QP with inequality constraints:
#           minimize    1/2x'*P*x + q'*x + r
#               s.t.    -1 <= x_i <= 1      for i = 1,2,3
# Also shows that the given x_star is indeed optimal

# Generate data
n = 3
P = cvxopt.matrix([	13, 12, -2,
					12, 17, 6,
					-2, 6, 12], (n,n))
q = cvxopt.matrix([-22, -14.5, 13], (n,1))
r = 1
x_star = cvxopt.matrix([1, 1/2, -1], (n,1))

# Frame and solve the problem

x = Variable(n)
objective = Minimize(  0.5 * quad_form(x, P)  + q.T * x + r )
constraints = [ x >= -1, x <= 1]

p = Problem(objective, constraints)
# The optimal objective is returned by p.solve().
result = p.solve()

########NEW FILE########
__FILENAME__ = ex_5_1
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

from multiprocessing import Pool

# Taken from CVX website http://cvxr.com/cvx/examples/
# Exercise 5.1d: Sensitivity analysis for a simple QCQP
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe, "Convex Optimization"
# Joelle Skaf - 08/29/05
# (a figure is generated)
#
# Let p_star(u) denote the optimal value of:
#           minimize    x^2 + 1
#               s.t.    (x-2)(x-2)<=u
# Finds p_star(u) and plots it versus u

u = Parameter()
x = Variable()

objective = Minimize( quad_form(x,1) + 1 )
constraint = [ quad_form(x,1) - 6*x + 8 <= u ]
p = Problem(objective, constraint)

# Assign a value to gamma and find the optimal x.
def get_x(u_value):
    u.value = u_value
    result = p.solve()
    return x.value

u_values = np.linspace(-0.9,10,num=50);
# Serial computation.
x_values = [get_x(value) for value in u_values]

# Parallel computation.
pool = Pool(processes = 4)
x_values = pool.map(get_x, u_values)

# Plot the tradeoff curve
plot(u_values, x_values)
# label
title('Sensitivity Analysis: p*(u) vs u')
xlabel('u')
ylabel('p*(u)')
axis([-2, 10, -1, 3])
show()
########NEW FILE########
__FILENAME__ = ex_5_33
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

from multiprocessing import Pool

# Taken from CVX website http://cvxr.com/cvx/examples/
# Exercise 5.33: Parametrized l1-norm approximation
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe "Convex Optimization"
# Joelle Skaf - 08/29/05
# (a figure is generated)
#
# Let p_star(epsilon) be the optimal value of the following problem:
#               minimize    ||Ax + b + epsilon*d||_1
# Plots p_star(epsilon) versus epsilon and demonstrates the fact that it's
# affine on an interval that includes epsilon = 0.

# Input data
m = 6
n = 3
A = cvxopt.matrix([ -2, 7, 1,
					-5, -1, 3,
					-7, 3, -5,
					-1, 4, -4,
					1, 5, 5,
					2, -5, -1 ], (m,n))
					
b = cvxopt.matrix([-4, 3, 9, 0, -11, 5], (m,1))
d = cvxopt.matrix([-10, -13, -27, -10, -7, 14], (m,1))
epsilon = Parameter()

# The problem
x = Variable(n)
objective = Minimize( norm( A*x + b + epsilon*d , 1 ) )
p = Problem(objective, [])

# Assign a value to gamma and find the optimal x
def get_p(e_value):
    epsilon.value = e_value
    result = p.solve()
    return result
# Range of epsilon values
e_values = np.linspace(-1,1,41)

# Solve serially if desired
# x_values = [get_p(value) for value in e_values]

# Solve in parallel
print 'Computing p*(epsilon) for -1 <= epsilon <= 1 ...'
pool = Pool(processes = 4)
p_values = pool.map(get_p, e_values)
print 'Done!'

# Plots
plot(e_values, p_values)
title('p*($\epsilon$) vs $\epsilon$')
xlabel('$\epsilon$')
ylabel('p*($\epsilon$)')
show()
########NEW FILE########
__FILENAME__ = fig6_9
from __future__ import division
import sys

import cvxopt
import numpy as np
from scipy import sparse
from pylab import *
import math

from cvxpy import *
from multiprocessing import Pool

# Taken from CVX website http://cvxr.com/cvx/examples/
# Figure 6.9: An optimal tradeoff curve
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Section 6.3.3
# Boyd & Vandenberghe "Convex Optimization"
# Original by Lieven Vandenberghe
# Adapted for CVX Joelle Skaf - 09/29/05
# (a figure is generated)
#
# Plots the optimal trade-off curve between ||Dx||_2 and ||x-x_cor||_2 by
# solving the following problem for different values of delta:
#           minimize    ||x - x_cor||^2 + delta*||Dx||^2
# where x_cor is the a problem parameter, ||Dx|| is a measure of smoothness

# Input data
n = 400
t = np.array(range(0,n))

exact = 0.5*sin(2*np.pi*t/n) * sin(0.01*t)
corrupt = exact + 0.05 * np.random.randn(len(exact))
corrupt = cvxopt.matrix(corrupt)

e = np.ones(n).T
ee = np.column_stack((-e,e)).T
D = sparse.spdiags(ee, range(-1,1), n, n)
D = D.todense()
D = cvxopt.matrix(D)

# Solve in parallel
nopts = 10
lambdas = np.linspace(0, 50, nopts)
# Frame the problem with a parameter
lamb = Parameter(sign="positive")
x = Variable(n)
p = Problem( Minimize( norm(x-corrupt) + norm(D*x) * lamb ) )


# For a value of lambda g, we solve the problem
# Returns [ ||Dx||_2 and ||x-x_cor||_2 ]
def get_value(g):
	lamb.value = g
	result = p.solve()
	return [np.linalg.norm( x.value - corrupt ), np.linalg.norm(D*x.value) ]


pool = Pool(processes = 4)
# compute allocation in parallel
norms1, norms2 = zip(*pool.map(get_value, lambdas))

plot(norms1, norms2)
xlabel('||x - x_{cor}||_2')
ylabel('||Dx||_2')
title('Optimal trade-off curve')
show()

########NEW FILE########
__FILENAME__ = floor_packing
from cvxpy import *
import pylab
import math

# Based on http://cvxopt.org/examples/book/floorplan.html
class Box(object):
    """ A box in a floor packing problem. """
    ASPECT_RATIO = 5.0
    def __init__(self, min_area):
        self.min_area = min_area
        self.height = Variable()
        self.width = Variable()
        self.x = Variable()
        self.y = Variable()

    @property
    def position(self):
        return (round(self.x.value,2), round(self.y.value,2))

    @property
    def size(self):
        return (round(self.width.value,2), round(self.height.value,2))

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y

    @property
    def top(self):
        return self.y + self.height

class FloorPlan(object):
    """ A minimum perimeter floor plan. """
    MARGIN = 1.0
    ASPECT_RATIO = 5.0
    def __init__(self, boxes):
        self.boxes = boxes
        self.height = Variable()
        self.width = Variable()
        self.horizontal_orderings = []
        self.vertical_orderings = []

    @property
    def size(self):
        return (round(self.width.value,2), round(self.height.value,2))

    # Return constraints for the ordering.
    @staticmethod
    def _order(boxes, horizontal):
        if len(boxes) == 0: return
        constraints = []
        curr = boxes[0]
        for box in boxes[1:]:
            if horizontal:
                constraints.append(curr.right + FloorPlan.MARGIN <= box.left)
            else:
                constraints.append(curr.top + FloorPlan.MARGIN <= box.bottom)
            curr = box
        return constraints

    # Compute minimum perimeter layout.
    def layout(self):
        constraints = []
        for box in self.boxes:
            # Enforce that boxes lie in bounding box.
            constraints += [box.bottom >= FloorPlan.MARGIN, 
                            box.top + FloorPlan.MARGIN <= self.height]
            constraints += [box.left >= FloorPlan.MARGIN, 
                            box.right + FloorPlan.MARGIN <= self.width]
            # Enforce aspect ratios.
            constraints += [(1/box.ASPECT_RATIO)*box.height <= box.width,
                            box.width <= box.ASPECT_RATIO*box.height]
            # Enforce minimum area
            constraints += [
            geo_mean(box.width, box.height) >= math.sqrt(box.min_area)
            ]

        # Enforce the relative ordering of the boxes.
        for ordering in self.horizontal_orderings:
            constraints += self._order(ordering, True)
        for ordering in self.vertical_orderings:
            constraints += self._order(ordering, False)
        p = Problem(Minimize(2*(self.height + self.width)), constraints)
        return p.solve()

    # Show the layout with matplotlib
    def show(self):
        pylab.figure(facecolor='w')
        for k in range(len(self.boxes)):
            box = self.boxes[k]
            x,y = box.position
            w,h = box.size
            pylab.fill([x, x, x + w, x + w],
                       [y, y+h, y+h, y],
                       facecolor = '#D0D0D0')
            pylab.text(x+.5*w, y+.5*h, "%d" %(k+1))
        x,y = self.size
        pylab.axis([0, x, 0, y])
        pylab.xticks([])
        pylab.yticks([])

        pylab.show()

boxes = [Box(180), Box(80), Box(80), Box(80), Box(80)]
fp = FloorPlan(boxes)
fp.horizontal_orderings.append( [boxes[0], boxes[2], boxes[4]] )
fp.horizontal_orderings.append( [boxes[1], boxes[2]] )
fp.horizontal_orderings.append( [boxes[3], boxes[4]] )
fp.vertical_orderings.append( [boxes[1], boxes[0], boxes[3]] )
fp.vertical_orderings.append( [boxes[2], boxes[3]] )
fp.layout()
fp.show()
########NEW FILE########
__FILENAME__ = commodity_flow
from cvxpy import *
import create_graph as g
from max_flow import Edge, Node
import pickle
import random as r
import cvxopt

# Multi-commodity flow.
COMMODITIES = 5 # Number of commodities.
r.seed(1)

class MultiEdge(Edge):
    """ An undirected, capacity limited edge with multiple commodities. """
    def __init__(self, capacity):
        self.capacity = capacity
        self.in_flow = Variable(COMMODITIES)
        self.out_flow = Variable(COMMODITIES)

    # Returns the edge's internal constraints.
    def constraints(self):
        return [self.in_flow + self.out_flow == 0,
                sum(abs(self.in_flow)) <= self.capacity]

class MultiNode(Node):
    """ A node with a target flow accumulation and a capacity. """
    def __init__(self, capacity=0):
        self.capacity = capacity
        self.edge_flows = []

    # The total accumulation of flow.
    def accumulation(self):
        return sum(f for f in self.edge_flows)
    
    def constraints(self):
        return [abs(self.accumulation()) <= self.capacity]


if __name__ == "__main__":
    # Read a graph from a file.
    f = open(g.FILE, 'r')
    data = pickle.load(f)
    f.close()

    # Construct nodes.
    node_count = data[g.NODE_COUNT_KEY]
    nodes = [MultiNode() for i in range(node_count)]
    # Add a source and sink for each commodity.
    sources = []
    sinks = []
    for i in range(COMMODITIES):
        source,sink = r.sample(nodes, 2)
        # Only count accumulation of a single commodity.
        commodity_vec = cvxopt.matrix(0,(COMMODITIES,1))
        commodity_vec[i] = 1
        # Initialize the source.
        source.capacity = commodity_vec*Variable()
        sources.append(source)
        # Initialize the sink.
        sink.capacity = commodity_vec*Variable()
        sinks.append(sink)

    # Construct edges.
    edges = []
    for n1,n2,capacity in data[g.EDGES_KEY]:
        edges.append(MultiEdge(capacity))
        edges[-1].connect(nodes[n1], nodes[n2])

    # Construct the problem.
    objective = Maximize(sum(sum(s.accumulation() for s in sinks)))
    constraints = []
    for o in nodes + edges:
        constraints += o.constraints()
    p = Problem(objective, constraints)
    result = p.solve()
    print "Objective value = %s" % result
    # Show how the flow for each commodity.
    for i,s in enumerate(sinks):
        accumulation = sum(f.value[i] for f in s.edge_flows)
        print "Accumulation of commodity %s = %s" % (i, accumulation)
########NEW FILE########
__FILENAME__ = create_graph
# Construct a random connected graph and stores it as tuples of 
# (start node #, end node #, capacity).
from random import choice, sample, random
import pickle

# Constants
FILE = "graph_data"
NODE_COUNT_KEY = "node_count"
EDGES_KEY = "edges"

if __name__ == "__main__":
    N = 20
    E = N*(N-1)/2
    c = 10
    edges = []
    # Start with a line.
    for i in range(1,N):
        edges.append( (i-1,i,c*random()) )
    # Add additional edges.
    for i in range(N,E):
        n1,n2 = sample(range(N), 2)
        edges.append( (n1,n2,c) )
    # Pickle the graph data.
    data = {NODE_COUNT_KEY: N, 
            EDGES_KEY: edges}
    f = open(FILE, 'w')
    pickle.dump(data, f)
    f.close()
########NEW FILE########
__FILENAME__ = incidence_matrix
# Incidence matrix approach.
from cvxpy import *
import create_graph as g
import pickle
import cvxopt

# Read a graph from a file.
f = open(g.FILE, 'r')
data = pickle.load(f)
f.close()

# Construct incidence matrix and capacities vector.
node_count = data[g.NODE_COUNT_KEY]
edges = data[g.EDGES_KEY]
E = 2*len(edges)
A = cvxopt.matrix(0,(node_count, E+2), tc='d')
c = cvxopt.matrix(1000,(E,1), tc='d')
for i,(n1,n2,capacity) in enumerate(edges):
    A[n1,2*i] = -1
    A[n2,2*i] = 1
    A[n1,2*i+1] = 1
    A[n2,2*i+1] = -1
    c[2*i] = capacity
    c[2*i+1] = capacity
# Add source.
A[0,E] = 1
# Add sink.
A[-1,E+1] = -1
# Construct the problem.
flows = Variable(E)
source = Variable()
sink = Variable()
p = Problem(Maximize(source),
            [A*vstack(flows,source,sink) == 0,
             0 <= flows,
             flows <= c])
result = p.solve()
print result
########NEW FILE########
__FILENAME__ = leaky_edges
from cvxpy import *
import create_graph as g
from max_flow import Node, Edge
import pickle

# Max-flow with different kinds of edges.
class Directed(Edge):
    """ A directed, capacity limited edge """
    # Returns the edge's internal constraints.
    def constraints(self):
        return [self.flow >= 0, self.flow <= self.capacity]

class LeakyDirected(Directed):
    """ A directed edge that leaks flow. """
    EFFICIENCY = .95
    # Connects two nodes via the edge.
    def connect(self, in_node, out_node):
        in_node.edge_flows.append(-self.flow)
        out_node.edge_flows.append(self.EFFICIENCY*self.flow)

class LeakyUndirected(Edge):
    """ An undirected edge that leaks flow. """
    # Model a leaky undirected edge as two leaky directed
    # edges pointing in opposite directions.
    def __init__(self, capacity):
        self.forward = LeakyDirected(capacity)
        self.backward = LeakyDirected(capacity)

    # Connects two nodes via the edge.
    def connect(self, in_node, out_node):
        self.forward.connect(in_node, out_node)
        self.backward.connect(out_node, in_node)

    def constraints(self):
        return self.forward.constraints() + self.backward.constraints()

if __name__ == "__main__":
    # Read a graph from a file.
    f = open(g.FILE, 'r')
    data = pickle.load(f)
    f.close()

    # Construct nodes.
    node_count = data[g.NODE_COUNT_KEY]
    nodes = [Node() for i in range(node_count)]
    # Add source.
    nodes[0].accumulation = Variable()
    # Add sink.
    nodes[-1].accumulation = Variable()

    # Construct edges.
    edges = []
    for n1,n2,capacity in data[g.EDGES_KEY]:
        edges.append(LeakyUndirected(capacity))
        edges[-1].connect(nodes[n1], nodes[n2])

    # Construct the problem.
    constraints = []
    for o in nodes + edges:
        constraints += o.constraints()
    p = Problem(Maximize(nodes[-1].accumulation), constraints)
    result = p.solve()
    print result
########NEW FILE########
__FILENAME__ = max_flow
from cvxpy import *
import create_graph as g
import pickle

# An object oriented max-flow problem.
class Edge(object):
    """ An undirected, capacity limited edge. """
    def __init__(self, capacity):
        self.capacity = capacity
        self.flow = Variable()

    # Connects two nodes via the edge.
    def connect(self, in_node, out_node):
        in_node.edge_flows.append(-self.flow)
        out_node.edge_flows.append(self.flow)

    # Returns the edge's internal constraints.
    def constraints(self):
        return [abs(self.flow) <= self.capacity]

class Node(object):
    """ A node with accumulation. """
    def __init__(self, accumulation=0):
        self.accumulation = accumulation
        self.edge_flows = []

    # Returns the node's internal constraints.
    def constraints(self):
        return [sum(f for f in self.edge_flows) == self.accumulation]

if __name__ == "__main__":
    # Read a graph from a file.
    f = open(g.FILE, 'r')
    data = pickle.load(f)
    f.close()

    # Construct nodes.
    node_count = data[g.NODE_COUNT_KEY]
    nodes = [Node() for i in range(node_count)]
    # Add source.
    nodes[0].accumulation = Variable()
    # Add sink.
    nodes[-1].accumulation = Variable()

    # Construct edges.
    edges = []
    for n1,n2,capacity in data[g.EDGES_KEY]:
        edges.append(Edge(capacity))
        edges[-1].connect(nodes[n1], nodes[n2])
    # Construct the problem.
    constraints = []
    for o in nodes + edges:
        constraints += o.constraints()
    p = Problem(Maximize(nodes[-1].accumulation), constraints)
    result = p.solve()
    print result
########NEW FILE########
__FILENAME__ = convex_sets
# An object oriented approach to geometric problems with convex sets.
# Convex sets can be used as Variables.

import cvxpy as cp
import numpy.linalg as la

class ConvexSet(cp.Variable):
    # elem - a Variable representing an element of the set.
    # constr_func - a function that takes an affine objective and
    #               returns a list of affine constraints.
    def __init__(self, rows, cols, constr_func):
        self.constr_func = constr_func
        super(ConvexSet, self).__init__(rows, cols)

    # Applies the objective to the constr_func to get the affine constraints.
    def canonicalize(self):
        return (self, self.constr_func(self))

# Returns whether the value is contained in the set.
def contains(cvx_set, value):
    p = cp.Problem(cp.Minimize(0), [cvx_set == value])
    p.solve(solver=cp.CVXOPT)
    return p.status == cp.OPTIMAL

# Returns whether the set is empty.
def is_empty(cvx_set):
    return not contains(cvx_set, cvx_set)

# Returns the Euclidean distance between two sets.
def dist(lh_set, rh_set):
    objective = cp.Minimize(cp.norm(lh_set - rh_set, 2))
    return cp.Problem(objective).solve(solver=cp.CVXOPT)

# Returns the Euclidean projection of the value onto the set.
def proj(cvx_set, value):
    objective = cp.Minimize(cp.norm(cvx_set - value, 2))
    cp.Problem(objective).solve(solver=cp.CVXOPT)
    return cvx_set.value

# Returns a separating hyperplane between two sets
# in the form (normal,offset) where normal.T*x == offset
# for all x on the hyperplane.
def sep_hyp(lh_set, rh_set):
    w = cp.Variable(*lh_set.size)
    p = cp.Problem(cp.Minimize(cp.norm(w, 2)), [lh_set - rh_set == w])
    p.solve(solver=cp.CVXOPT)
    # Normal vector to the hyperplane.
    normal = p.constraints[0].dual_value
    # A point on the hyperplane.
    point = (lh_set.value + rh_set.value)/2
    # The offset of the hyperplane.
    offset = normal.T*point
    return (normal, offset[0])

# Returns the intersection of two sets.
def intersect(lh_set, rh_set):
    def constr_func(aff_obj):
        # Combine the constraints from both sides and add an equality constraint.
        lh_obj,lh_constr = lh_set.canonical_form
        rh_obj,rh_constr = rh_set.canonical_form
        constraints = [aff_obj == lh_obj,
                       aff_obj == rh_obj,
        ]
        return constraints + lh_constr + rh_constr
    return ConvexSet(lh_set.size[0], lh_set.size[1], constr_func)

class Polyhedron(ConvexSet):
    # The set defined by Ax == b, Gx <= h.
    # G,h,A,b are numpy matrices or ndarrays.
    # The arguments A and b are optional.
    def __init__(self, G, h, A=None, b=None):
        G = self.cast_to_const(G)
        def constr_func(aff_obj):
            constraints = [G*aff_obj <= h]
            if A is not None:
                constraints += [A*aff_obj == b]
            return constraints
        super(Polyhedron, self).__init__(G.size[1], 1, constr_func)

class ConvexHull(ConvexSet):
    # The convex hull of a list of values.
    def __init__(self, values):
        values = map(self.cast_to_const, values)
        rows,cols = values[0].size
        def constr_func(aff_obj):
            theta = cp.Variable(len(values))
            convex_combo = sum(v*t for (t,v) in zip(theta, values))
            constraints = [aff_obj == convex_combo,
                           sum(theta) == 1,
                           0 <= theta]
            return constraints
        super(ConvexHull, self).__init__(rows,cols,constr_func)

########NEW FILE########
__FILENAME__ = separating_polyhedra
# Finds the separating hyperplane between two polyhedra.
# Data from Section 8.2.2: Separating polyhedra in 2D in http://cvxr.com/cvx/examples/

import convex_sets as cs
import numpy as np
import matplotlib.pyplot as plt

n = 2
m = 2*n
A1 = np.matrix("1 1; 1 -1; -1 1; -1 -1")
A2 = np.matrix("1 0; -1 0; 0 1; 0 -1")
b1 = 2*np.ones((m,1))
b2 = np.matrix("5; -3; 4; -2")

poly1 = cs.Polyhedron(A1, b1)
poly2 = cs.Polyhedron(A2, b2)

# Separating hyperplane.
normal,offset = cs.sep_hyp(poly1, poly2)
print normal, offset

# Plotting
t = np.linspace(-3,6,100);
p = -normal[0]*t/normal[1] + offset/normal[1]
p = np.array(p).flatten()
plt.fill([-2, 0, 2, 0],[0,2,0,-2],'b', [3,5,5,3],[2,2,4,4],'r')
plt.axis([-3, 6, -3, 6])
plt.axes().set_aspect('equal', 'box')
plt.plot(t,p)
plt.title('Separating 2 polyhedra by a hyperplane')
plt.show()
########NEW FILE########
__FILENAME__ = tests
# Problems involving polyhedra.

import convex_sets as cs
import numpy as np

n = 2
m = 2*n
A1 = np.matrix("1 1; 1 -1; -1 1; -1 -1")
A2 = np.matrix("1 0; -1 0; 0 1; 0 -1")
b1 = 2*np.ones((m,1))
b2 = np.matrix("5; -3; 4; -2")

poly1 = cs.Polyhedron(A1, b1)
poly2 = cs.Polyhedron(A2, b2)

assert cs.contains(poly1, [1,1])
# TODO distance should be an expression, i.e. norm2(poly1 - poly2)
print cs.dist(poly1, poly2)
elem = cs.proj(poly1, poly2)
assert cs.contains(poly1, elem)
assert cs.dist(poly1, elem) < 1e-6

hull = cs.ConvexHull([b1, b2])
print cs.contains(hull, b1)
print cs.contains(hull, 0.3*b1 + 0.7*b2)

print cs.dist(poly1, 5*hull[0:2] + 2)
print cs.dist(poly1, np.matrix("1 5; -1 3")*poly2 + [1,5])
d1 = cs.dist(poly1, np.matrix("1 0; 0 1")*poly2 + [1,5])
d2 = cs.dist(poly2, poly1 - [1,5])
assert abs(d1 - d2) < 1e-6

poly_hull = hull[0:2] + poly1 + poly2
assert cs.dist(poly_hull, poly1) > 0
intersection = cs.intersect(poly_hull, poly1)
assert cs.is_empty(intersection)
assert not cs.is_empty(poly1)
########NEW FILE########
__FILENAME__ = lasso
from cvxpy import *
import numpy as np
import cvxopt
from multiprocessing import Pool

# Problem data.
n = 10
m = 5
A = cvxopt.normal(n,m)
b = cvxopt.normal(n)
gamma = Parameter(sign="positive")

# Construct the problem.
x = Variable(m)
objective = Minimize(sum_squares(A*x - b) + gamma*norm(x, 1))
p = Problem(objective)

# Assign a value to gamma and find the optimal x.
def get_x(gamma_value):
    gamma.value = gamma_value
    result = p.solve()
    return x.value

gammas = np.logspace(-1, 2, num=100)
# Serial computation.
x_values = [get_x(value) for value in gammas]

# Parallel computation.
pool = Pool(processes = 4)
par_x = pool.map(get_x, gammas)

for v1,v2 in zip(x_values, par_x):
    if np.linalg.norm(v1 - v2) > 1e-5:
        print "error"
########NEW FILE########
__FILENAME__ = matrix_games_LP
# for decimal division
from __future__ import division

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Example: Section 5.2.5: Mixed strategies for matrix games (LP formulation)
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below


# Boyd & Vandenberghe, "Convex Optimization"
# Joelle Skaf - 08/24/05
#
# Player 1 wishes to choose u to minimize his expected payoff u'Pv, while
# player 2 wishes to choose v to maximize u'Pv, where P is the payoff
# matrix, u and v are the probability distributions of the choices of each
# player (i.e. u>=0, v>=0, sum(u_i)=1, sum(v_i)=1)
# LP formulation:   minimize    t
#                       s.t.    u >=0 , sum(u) = 1, P'*u <= t*1
#                   maximize    t
#                       s.t.    v >=0 , sum(v) = 1, P*v >= t*1

# Input data
n = 12
m = 12
P = cvxopt.normal(n,m)

# Variables for two players
x = Variable(n)
y = Variable(m)
t1 = Variable()
t2 = Variable()

# Note in one case we are maximizing; in the other we are minimizing
objective1 = Minimize(t1)
objective2 = Maximize(t2)

constraints1 = [ x>=0, sum_entries(x)==1, P.T*x <= t1 ]
constraints2 = [ y>=0, sum_entries(y)==1, P*y >= t2 ]


p1 = Problem(objective1, constraints1)
p2 = Problem(objective2, constraints2)

# Optimal strategy for Player 1
print 'Computing the optimal strategy for player 1 ... '
result1 = p1.solve()
print 'Done!'

# Optimal strategy for Player 2
print 'Computing the optimal strategy for player 2 ... '
result2 = p2.solve()
print 'Done!'

# Displaying results
print '------------------------------------------------------------------------'
print 'The optimal strategies for players 1 and 2 are respectively: '
print x.value, y.value
print 'The expected payoffs for player 1 and player 2 respectively are: '
print result1, result2
print 'They are equal as expected!'
## ISSUE: THEY AREN'T EXACTLY EQUAL FOR SOME REASON!

########NEW FILE########
__FILENAME__ = norm_approx
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Examples 5.6,5.8: An l_p norm approximation problem
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe "Convex Optimization"
# Joelle Skaf - 08/23/05
#
# The goal is to show the following problem formulations give all the same
# optimal residual norm ||Ax - b||:
# 1)        minimize    ||Ax - b||
# 2)        minimize    ||y||
#               s.t.    Ax - b = y
# 3)        maximize    b'v
#               s.t.    ||v||* <= 1  , A'v = 0
# 4)        minimize    1/2 ||y||^2
#               s.t.    Ax - b = y
# 5)        maximize    -1/2||v||*^2 + b'v
#               s.t.    A'v = 0
# where ||.||* denotes the dual norm of ||.||

# Input data
n = 4
m = 2*n
A = cvxopt.normal(m,n)
b = cvxopt.normal(m,1)
p = 2
q = p/(p-1)


# Original problem
x = Variable(n)
objective1 = Minimize( norm ( A*x - b , p) )
p1 = Problem(objective1, [])
print 'Computing the optimal solution of problem 1... '
opt1 = p1.solve()

# Reformulation 1
x = Variable(n)
y = Variable(m)
objective2 = Minimize ( norm( y, p ) )
p2 = Problem(objective2, [ A*x - b == y ])
print 'Computing the optimal solution of problem 2... '
opt2 = p2.solve()

# Dual of reformulation 1
nu = Variable(m)
objective3 = Maximize( b.T * nu )
p3 = Problem(objective3, [ norm( nu, q) <= 1, A.T*nu == 0 ])
print 'Computing the optimal solution of problem 3... '
opt3 = p3.solve()

# Reformulation 2
x = Variable(n)
y = Variable(m)
objective4 = Minimize( 0.5*square( norm(y, p) ) )
p4 = Problem(objective4, [ A*x - b == y ] )
print 'Computing the optimal solution of problem 4... '
opt4 = math.sqrt(2*p4.solve())

# Dual of reformulation 2
nu = Variable(m)
objective5 = Maximize( -0.5*square( norm(nu,q) ) + b.T*nu )
p5 = Problem(objective5, [ A.T*nu==0 ])
print 'Computing the optimal solution of problem 5... '
opt5 = math.sqrt(2*p5.solve())

# Display results
print '------------------------------------------------------------------------'
print 'The optimal residual values for problems 1,2,3,4 and 5 are respectively:'
print opt1, opt2, opt3, opt4, opt5
print 'They are equal as expected!'
########NEW FILE########
__FILENAME__ = functions
# List of atoms for functions table in tutorial.
ATOM_DEFINITIONS = [
  {"name":"abs",
   "usage": "abs(x)",
   "meaning": "$ |x| $",
   "domain": "$ x \in \mathbf{R} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
  },
  # {"name":"berhu",
  #  "arguments": ("Takes a single expression followed by a parameter as arguments. "
  #                "The parameter must be a positive number. "
  #                "The default value for the parameter is 1."),
  #  "meaning":
  #       ("\operatorname{berhu}(x,M) = \\begin{cases} |x| &\mbox{if } |x| \le M \\\\ "
  #        "\left(|x|^{2} + M^{2} \\right)/2M & \mbox{if } |x| > M \end{cases} \\\\"
  #        " \mbox{ where } x \in \mathbf{R}."),
  #  "curvature": "Convex",
  #  "sign": "Positive",
  #  "monotonicity": ["Increasing for $ x \geq 0 $",
  #                   "Decreasing for $ x \leq 0 $"],
  #  "example": "berhu(x, 1)",
  # },
  {"name":"entr",
   "usage": "entr(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning":
        ("$ \\begin{cases} -x \log (x) & x > 0 \\\\ "
         "0 & x = 0 \end{cases} \\\\ $"),

   "domain": "$ x \geq 0 $",
   "curvature": "Concave",
   "sign": "Unknown",
   "monotonicity": ["None"],
   "example": "entr(x)",
  },
  {"name":"exp",
   "usage": "exp(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ e^{x} $",
   "domain": "$ x \in \mathbf{R} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "exp(x)",
  },
  {"name":"geo_mean",
   "usage": "geo_mean(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions as arguments. "
                 "These are interpreted as a vector."),
   "meaning": "$ (x_{1} \cdots x_{k})^{1/k} $",
   "domain": "$ x_{i} \geq 0 $",
   "curvature": "Concave",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "geo_mean(x, y)",
  },
  {"name":"huber",
   "usage": "huber(x)",
   "arguments": ("Takes a single expression followed by a parameter as arguments. "
                 "The parameter must be a positive number. "
                 "The default value for the parameter is 1."),
   "meaning":
        ("$ \\begin{cases} 2|x|-1 & |x| \ge 1 \\\\ "
         " |x|^{2} & |x| < 1 \end{cases} \\\\ $"),
   "domain": "$ x \in \mathbf{R} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
   "cvx_equivalent": "huber, huber_pos, huber_circ",
  },
  {"name":"inv_pos",
   "usage": "inv_pos(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ 1/x $",
   "domain": "$ x > 0 $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Decreasing"],
   "example": "inv_pos(x)",
  },
  {"name":"kl_div",
   "usage": "kl_div(x,y)",
   "arguments": "Takes two expressions as arguments.",
   "meaning": "$ x \log (x/y)-x+y $",
   "domain": "$ x,y > 0 $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["None"],
   "example": "kl_div(x, y)",
  },
  {"name":"log",
   "usage": "log(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ \log(x) $",
   "domain": "$ x > 0 $",
   "curvature": "Concave",
   "sign": "Unknown",
   "monotonicity": ["Increasing"],
   "example": "log(x)",
  },
  {"name":"log_sum_exp",
   "usage": "log_sum_exp(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions as arguments. "
                 "These are interpreted as a vector."),
   "meaning": "$ \log \left(e^{x_{1}} + \cdots + e^{x_{k}} \\right) $",
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Convex",
   "sign": "Unknown",
   "monotonicity": ["Increasing"],
   "example": "log_sum_exp(x, y)",
  },
  {"name":"max",
   "usage": "max(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions as arguments. "
                 "These are interpreted as a vector."),
   "meaning": "$ \max \left\{ x_{1}, \ldots , x_{k} \\right\} $",
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Convex",
   "sign": "max(sign(arguments))",
   "monotonicity": ["Increasing"],
   "example": "max(x, y)",
  },
  {"name":"min",
   "usage": "min(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions as arguments. "
                 "These are interpreted as a vector."),
   "meaning": "$ \min \left\{ x_{1}, \ldots , x_{k} \\right\} $",
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Concave",
   "sign": "min(sign(arguments))",
   "monotonicity": ["Increasing"],
   "example": "min(x, y)",
  },
  # {"name":"norm",
  #  "arguments": ("Takes a variable number of expressions followed by a parameter as arguments. "
  #                "The expressions are interpreted as a vector. "
  #                "The parameter must either be a number p with p >= 1 or be Inf. "
  #                "The default parameter is 2."),
  #  "mathematical_definition": ("\\begin{aligned} "
  #                              " \operatorname{norm}(x,p) &= \left( \sum_{k=1}^{n} |x_{k}|^{p}} \\right)^{1/p} \\\\"
  #                              " \operatorname{norm}(x,\mbox{Inf}) &= \max \left\{ \left| x_{k} \\right| | k \in \{1,...,n \} \\right\} \\\\"
  #                              " \mbox{ where } x \in \mathbf{R}^{n}."
  #                              " \end{aligned} "),
  #  "curvature": "Convex",
  #  "sign": "Positive",
  #  "monotonicity": [("For all arguments], non-decreasing if the argument is positive"
  #                   " and non-increasing if the argument is negative.")],
  #  "example": "norm(x, y, 1)",
  # },
  {"name":"norm2",
   "usage": "norm2(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions followed by a parameter as arguments. "
                 "The expressions are interpreted as a vector. "
                 "The parameter must either be a number p with p >= 1 or be Inf. "
                 "The default parameter is 2."),
   "meaning": ("$ \sqrt{x_{1}^{2} + \cdots + x_{k}^{2}} $"),
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
   "example": "norm(x, y, 1)",
  },
  {"name":"norm1",
   "usage": "norm1(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions followed by a parameter as arguments. "
                 "The expressions are interpreted as a vector. "
                 "The parameter must either be a number p with p >= 1 or be Inf. "
                 "The default parameter is 2."),
   "meaning": ("$ |x_{1}| + \cdots + |x_{k}| $"),
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
   "example": "norm(x, y, 1)",
  },
  {"name":"norm_inf",
   "usage": "norm_inf(x1,...,xk)",
   "arguments": ("Takes a variable number of expressions followed by a parameter as arguments. "
                 "The expressions are interpreted as a vector. "
                 "The parameter must either be a number p with p >= 1 or be Inf. "
                 "The default parameter is 2."),
   "meaning": ("$ \max \left\{ |x_{1}|, \ldots, |x_{k}| \\right\} $"),
   "domain": "$ x \in \mathbf{R}^{k} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
   "example": "norm(x, y, 1)",
  },
  {"name":"pos",
   "usage": "pos(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ \max \{x,0\} $",
   "domain": "$ x \in \mathbf{R}$",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "pos(x)",
  },
  {"name":"quad_over_lin",
   "usage": "quad_over_lin(x,y)",
   "arguments": "Takes two expressions as arguments.",
   "meaning": "$ x^{2}/y $",
   "domain": "$x \in \mathbf{R}$, y > 0",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $",
                    "Decreasing in y"],
   "example": "quad_over_lin(x, y)",
  },
  {"name":"sqrt",
   "usage": "sqrt(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ \sqrt{x} $",
   "domain": "$ x \geq 0 $",
   "curvature": "Concave",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "sqrt(x)",
  },
  {"name":"square",
   "usage": "square(x)",
   "arguments": "Takes a single expression as an argument.",
   "meaning": "$ x^{2} $",
   "domain": "$ x \in \mathbf{R} $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing for $ x \geq 0 $",
                    "Decreasing for $ x \leq 0 $"],
   "cvx_equivalent": "square, square_pos, square_abs",
  },
  # {"name":"pow",
  #  "arguments": ("Takes a single expression followed by a parameter as arguments. "
  #                "The parameter must be a number. "),
  #  "mathematical_definition":
  #       ("\\begin{aligned} "
  #       " p &\le 0: \operatorname{pow}(x,p) &= "
  #       "\\begin{cases} x^{p} &\mbox{if } x > 0 \\\\"
  #       " +\infty &\mbox{if } x \le 0 \end{cases} \\\\"
  #       " 0 < p &< 1: \operatorname{pow}(x,p) &= "
  #       "\\begin{cases} x^{p} &\mbox{if } x \ge 0 \\\\"
  #       " -\infty &\mbox{if } x < 0 \end{cases}\\\\"
  #       " p &\ge 1: \operatorname{pow}(x,p) &= "
  #       "\\begin{cases} x^{p} &\mbox{if } x \ge 0 \\\\"
  #       " +\infty &\mbox{if } x < 0 \end{cases}\\\\"
  #       " \mbox{ where } x \in \mathbf{R}^{n}."
  #       " \end{aligned} "),
  #  "curvature": "Concave for 0 < p < 1. Otherwise convex.",
  #  "sign": "The argument's sign for 0 < p < 1. Otherwise positive.",
  #  "monotonicity": [("Non-increasing for p <= 0. Non-decreasing for 0 < p < 1. "
  #                   "If p >= 1, increasing for positive arguments and non-increasing for negative arguments.")],
  #  "example": "pow(x, 3)",
  #  "cvx_equivalent": "pow_p",
  # },
  {"name":"pow",
   "usage": "pow(x,p), $\\text{ } p \geq 1 $",
   "arguments": ("Takes a single expression followed by a parameter as arguments. "
                 "The parameter must be a number. "),
   "meaning": "$ x^{p} $",
   "domain": "$ x \geq 0 $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "pow(x, 3)",
   "cvx_equivalent": "pow_p",
  },
  {"name":"pow",
   "usage": "pow(x,p), $\\text{ } 0 < p < 1 $",
   "arguments": ("Takes a single expression followed by a parameter as arguments. "
                 "The parameter must be a number. "),
   "meaning": "$ x^{p} $",
   "domain": "$ x \geq 0 $",
   "curvature": "Concave",
   "sign": "Positive",
   "monotonicity": ["Increasing"],
   "example": "pow(x, 3)",
   "cvx_equivalent": "pow_p",
  },
  {"name":"pow",
   "usage": "pow(x,p), $\\text{ } p \leq 0 $",
   "arguments": ("Takes a single expression followed by a parameter as arguments. "
                 "The parameter must be a number. "),
   "meaning": "$ x^{p} $",
   "domain": "$ x > 0 $",
   "curvature": "Convex",
   "sign": "Positive",
   "monotonicity": ["Decreasing"],
   "example": "pow(x, 3)",
   "cvx_equivalent": "pow_p",
  },
]
########NEW FILE########
__FILENAME__ = simple_portfolio_data
# simple_portfolio_data
import numpy as np
np.random.seed(5)
n = 20
pbar = (np.ones((n, 1)) * .03 +
        np.matrix(np.append(np.random.rand(n - 1, 1), 0)).T * .12)
S = np.matrix(np.random.randn(n, n))
S = S.T * S
S = S / np.max(np.abs(np.diag(S))) * .2
S[:, n - 1] = np.matrix(np.zeros((n, 1)))
S[n - 1, :] = np.matrix(np.zeros((1, n)))
x_unif = np.matrix(np.ones((n, 1))) / n

########NEW FILE########
__FILENAME__ = penalty_comp_cvx
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Figure 6.2: Penalty function approximation
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Section 6.1.2
# Boyd & Vandenberghe "Convex Optimization"
# Original by Lieven Vandenberghe
# Adapted for CVX Argyris Zymnis - 10/2005
#
# Comparison of the ell1, ell2, deadzone-linear and log-barrier
# penalty functions for the approximation problem:
#       minimize phi(A*x-b),
#
# where phi(x) is the penalty function

# Generate input data
m, n = 100, 30
A = cvxopt.normal(m,n) #np.random.randn(m,n)
b = cvxopt.normal(m,1) #np.random.randn(m,1)

# l-1 approximation
x1 = Variable(n)
objective1 = Minimize( norm(A*x1-b, 1) )
p1 = Problem(objective1, [])
#p1 = Problem(Minimize( norm(A*x1-b, 1), []))

# l-2 approximation
x2 = Variable(n)
objective2 = Minimize( norm(A*x2-b, 2) )
p2 = Problem(objective2, [])

# deadzone approximation
# minimize sum(deadzone(Ax+b,0.5))
# deadzone(y,z) = max(abs(y)-z,0)
def deadzone(y,z):
	return pos(abs(y)-z)

dz = 0.5
xdz = Variable(n)
objective3 = Minimize( sum_entries( deadzone(A*xdz+b, dz) ) )
p3 = Problem(objective3, [])

# Solve the problems
p1.solve()
p2.solve()
p3.solve()

# Plot histogram of residuals
range_max=2.0
#rr = np.arange(-range_max, range_max, 1e-2)
rr = np.linspace(-2, 3, 20)



# l-1 plot
subplot(3, 1, 1)
n, bins, patches = hist(A*x1.value-b, 50, range=[-2, 2])
plot(bins, np.abs(bins)*35/3, '-') # multiply by scaling factor for plot
ylabel('l-1 norm')
title('Penalty function approximation')

# l-2 plot
subplot(3, 1, 2)
n, bins, patches = hist(A*x2.value-b, 50,  range=[-2, 2])
plot(bins, np.power(bins, 2)*2, '-')
ylabel('l-2 norm')

# deadzone plot
subplot(3, 1, 3)
n, bins, patches = hist(A*xdz.value+b, 50, range=[-2, 2])
zeros = np.array([0 for x in bins])
plot(bins, np.maximum((np.abs(bins)-dz)*35/3, zeros), '-')
ylabel('deadzone')

show()
########NEW FILE########
__FILENAME__ = qcqp
# for decimal division
from __future__ import division
import sys

import cvxopt
import numpy as np
from pylab import *
import math

from cvxpy import *

# Taken from CVX website http://cvxr.com/cvx/examples/
# Example: Finding the fastest mixing Markov chain on a graph
# Ported from cvx matlab to cvxpy by Misrab Faizullah-Khan
# Original comments below

# Boyd & Vandenberghe, "Convex Optimization"
# Joelle Skaf - 08/23/05
#
# Solved a QCQP with 3 inequalities:
#           minimize    1/2 x'*P0*x + q0'*r + r0
#               s.t.    1/2 x'*Pi*x + qi'*r + ri <= 0   for i=1,2,3
# and verifies that strong duality holds.

# Input data
n = 6
eps = sys.float_info.epsilon

P0 = cvxopt.normal(n, n)
eye = cvxopt.spmatrix(1.0, range(n), range(n))
P0 = P0.T * P0 + eps * eye

print P0

P1 = cvxopt.normal(n, n)
P1 = P1.T*P1
P2 = cvxopt.normal(n, n)
P2 = P2.T*P2
P3 = cvxopt.normal(n, n)
P3 = P3.T*P3

q0 = cvxopt.normal(n, 1)
q1 = cvxopt.normal(n, 1)
q2 = cvxopt.normal(n, 1)
q3 = cvxopt.normal(n, 1)

r0 = cvxopt.normal(1, 1)
r1 = cvxopt.normal(1, 1)
r2 = cvxopt.normal(1, 1)
r3 = cvxopt.normal(1, 1)

# Form the problem
x = Variable(n)
objective = Minimize( 0.5*quad_form(x,P0) + q0.T*x + r0 )
constraints = [ 0.5*quad_form(x,P1) + q1.T*x + r1 <= 0,
                0.5*quad_form(x,P2) + q2.T*x + r2 <= 0,
                0.5*quad_form(x,P3) + q3.T*x + r3 <= 0
               ]

# We now find the primal result and compare it to the dual result
# to check if strong duality holds i.e. the duality gap is effectively zero
p = Problem(objective, constraints)
primal_result = p.solve()

if p.status is OPTIMAL:
    # Note that since our data is random, we may need to run this program multiple times to get a feasible primal
    # When feasible, we can print out the following values
    print x.value # solution
    lam1 = constraints[0].dual_value
    lam2 = constraints[1].dual_value
    lam3 = constraints[2].dual_value


    P_lam = P0 + lam1*P1 + lam2*P2 + lam3*P3
    q_lam = q0 + lam1*q1 + lam2*q2 + lam3*q3
    r_lam = r0 + lam1*r1 + lam2*r2 + lam3*r3
    dual_result = -0.5*q_lam.T*P_lam*q_lam + r_lam
    # ISSUE: dual result is matrix for some reason

    print 'Our duality gap is:'
    print (primal_result - dual_result)

########NEW FILE########
__FILENAME__ = sdp
"""
This script finds a PSD matrix that is closest to a given symmetric,
real matrix, as measured by the Frobenius norm. That is, for
a given matrix P, it solves:
   minimize   || Z - P ||_F
   subject to Z >= 0

Adapted from an example provided in the SeDuMi documentation and CVX examples.
Unlike those examples, the data is real (not complex) and the result is only
required to be PSD (instead of also Toeplitz)
"""
# import cvxpy as cvx
# import numpy as np
# import cvxopt
#
# # create data P
# P = cvxopt.matrix(np.matrix('4 1 3; 1 3.5 0.8; 3 0.8 1'))
# Z = cvx.Variable(3,3)

# objective = cvx.Minimize( sum(cvx.square(P - Z)) )
# constr = [cvx.constraints.semi_definite.SDP(P)]
# prob = cvx.Problem(objective, constr)
# prob.solve()

import cvxpy as cp
import numpy as np
import cvxopt

# create data P
P = cp.Parameter(3,3)
Z = cp.semidefinite(3)

objective = cp.Minimize( cp.lambda_max(P) - cp.lambda_min(P - Z) )
prob = cp.Problem(objective, 10*[Z >= 0])
P.value = cvxopt.matrix(np.matrix('4 1 3; 1 3.5 0.8; 3 0.8 1'))
prob.solve()



# [ 4,     1+2*j,     3-j       ; ...
#       1-2*j, 3.5,       0.8+2.3*j ; ...
#       3+j,   0.8-2.3*j, 4         ];
#
# % Construct and solve the model
# n = size( P, 1 );
# cvx_begin sdp
#     variable Z(n,n) hermitian toeplitz
#     dual variable Q
#     minimize( norm( Z - P, 'fro' ) )
#     Z >= 0 : Q;
# cvx_end
########NEW FILE########
__FILENAME__ = pylint_settings
[MASTER]

# Specify a configuration file.
#rcfile=

# Python code to execute, usually for sys.path manipulation such as
# pygtk.require().
#init-hook=

# Profiled execution.
profile=no

# Add files or directories to the blacklist. They should be base names, not
# paths.
ignore=CVS

# Pickle collected data for later comparisons.
persistent=yes

# List of plugins (as comma separated values of python modules names) to load,
# usually to register additional checkers.
load-plugins=


[MESSAGES CONTROL]

# Enable the message, report, category or checker with the given id(s). You can
# either give multiple identifier separated by comma (,) or put this option
# multiple time. See also the "--disable" option for examples.
#enable=

# Disable the message, report, category or checker with the given id(s). You
# can either give multiple identifiers separated by comma (,) or put this
# option multiple times (only on the command line, not in the configuration
# file where it should appear only once).You can also use "--disable=all" to
# disable everything first and then reenable specific checks. For example, if
# you want to run only the similarities checker, you can use "--disable=all
# --enable=similarities". If you want to run only the classes checker, but have
# no Warning level messages displayed, use"--disable=all --enable=classes
# --disable=W"
disable=star-args,no-member,too-few-public-methods


[REPORTS]

# Set the output format. Available formats are text, parseable, colorized, msvs
# (visual studio) and html. You can also give a reporter class, eg
# mypackage.mymodule.MyReporterClass.
output-format=text

# Put messages in a separate file for each module / package specified on the
# command line instead of printing them on stdout. Reports (if any) will be
# written in a file name "pylint_global.[txt|html]".
files-output=no

# Tells whether to display a full report or only the messages
reports=yes

# Python expression which should return a note less than 10 (10 is the highest
# note). You have access to the variables errors warning, statement which
# respectively contain the number of errors / warnings messages and the total
# number of statements analyzed. This is used by the global evaluation report
# (RP0004).
evaluation=10.0 - ((float(5 * error + warning + refactor + convention) / statement) * 10)

# Add a comment according to your evaluation note. This is used by the global
# evaluation report (RP0004).
comment=no

# Template used to display messages. This is a python new-style format string
# used to format the massage information. See doc for all details
#msg-template=


[BASIC]

# Required attributes for module, separated by a comma
required-attributes=

# List of builtins function names that should not be used, separated by a comma
bad-functions=map,filter,apply,input

# Regular expression which should only match correct module names
module-rgx=(([a-z_][a-z0-9_]*)|([A-Z][a-zA-Z0-9]+))$

# Regular expression which should only match correct module level names
const-rgx=(([A-Z_][A-Z0-9_]*)|(__.*__))$

# Regular expression which should only match correct class names
class-rgx=[A-Z_][a-zA-Z0-9]+$

# Regular expression which should only match correct function names
function-rgx=[a-z_][a-z0-9_]{2,30}$

# Regular expression which should only match correct method names
method-rgx=[a-z_][a-z0-9_]{2,30}$

# Regular expression which should only match correct instance attribute names
attr-rgx=[a-z_][a-z0-9_]{2,30}$

# Regular expression which should only match correct argument names
argument-rgx=[a-z_][a-z0-9_]{2,30}$

# Regular expression which should only match correct variable names
variable-rgx=[a-z_][a-z0-9_]{2,30}$

# Regular expression which should only match correct attribute names in class
# bodies
class-attribute-rgx=([A-Za-z_][A-Za-z0-9_]{2,30}|(__.*__))$

# Regular expression which should only match correct list comprehension /
# generator expression variable names
inlinevar-rgx=[A-Za-z_][A-Za-z0-9_]*$

# Good variable names which should always be accepted, separated by a comma
good-names=i,j,k,ex,Run,_,T

# Bad variable names which should always be refused, separated by a comma
bad-names=foo,bar,baz,toto,tutu,tata

# Regular expression which should only match function or class names that do
# not require a docstring.
no-docstring-rgx=__.*__

# Minimum line length for functions/classes that require docstrings, shorter
# ones are exempt.
docstring-min-length=-1


[FORMAT]

# Maximum number of characters on a single line.
max-line-length=80

# Regexp for a line that is allowed to be longer than the limit.
ignore-long-lines=^\s*(# )?<?https?://\S+>?$

# Maximum number of lines in a module
max-module-lines=1000

# String used as indentation unit. This is usually " " (4 spaces) or "\t" (1
# tab).
indent-string='    '


[MISCELLANEOUS]

# List of note tags to take in consideration, separated by a comma.
notes=FIXME,XXX,TODO


[SIMILARITIES]

# Minimum lines number of a similarity.
min-similarity-lines=4

# Ignore comments when computing similarities.
ignore-comments=yes

# Ignore docstrings when computing similarities.
ignore-docstrings=yes

# Ignore imports when computing similarities.
ignore-imports=no


[TYPECHECK]

# Tells whether missing members accessed in mixin class should be ignored. A
# mixin class is detected if its name ends with "mixin" (case insensitive).
ignore-mixin-members=yes

# List of classes names for which member attributes should not be checked
# (useful for classes with attributes dynamically set).
ignored-classes=SQLObject

# When zope mode is activated, add a predefined set of Zope acquired attributes
# to generated-members.
zope=no

# List of members which are set dynamically and missed by pylint inference
# system, and so shouldn't trigger E0201 when accessed. Python regular
# expressions are accepted.
generated-members=REQUEST,acl_users,aq_parent


[VARIABLES]

# Tells whether we should check for unused import in __init__ files.
init-import=no

# A regular expression matching the beginning of the name of dummy variables
# (i.e. not used).
dummy-variables-rgx=_$|dummy

# List of additional names supposed to be defined in builtins. Remember that
# you should avoid to define new builtins when possible.
additional-builtins=


[CLASSES]

# List of interface methods to ignore, separated by a comma. This is used for
# instance to not check methods defines in Zope's Interface base class.
ignore-iface-methods=isImplementedBy,deferred,extends,names,namesAndDescriptions,queryDescriptionFor,getBases,getDescriptionFor,getDoc,getName,getTaggedValue,getTaggedValueTags,isEqualOrExtendedBy,setTaggedValue,isImplementedByInstancesOf,adaptWith,is_implemented_by

# List of method names used to declare (i.e. assign) instance attributes.
defining-attr-methods=__init__,__new__,setUp

# List of valid names for the first argument in a class method.
valid-classmethod-first-arg=cls

# List of valid names for the first argument in a metaclass class method.
valid-metaclass-classmethod-first-arg=mcs


[DESIGN]

# Maximum number of arguments for function / method
max-args=5

# Argument names that match this expression will be ignored. Default to name
# with leading underscore
ignored-argument-names=_.*

# Maximum number of locals for function / method body
max-locals=15

# Maximum number of return / yield for function / method body
max-returns=6

# Maximum number of branch for function / method body
max-branches=12

# Maximum number of statements in function / method body
max-statements=50

# Maximum number of parents for a class (see R0901).
max-parents=7

# Maximum number of attributes for a class (see R0902).
max-attributes=7

# Minimum number of public methods for a class (see R0903).
min-public-methods=2

# Maximum number of public methods for a class (see R0904).
max-public-methods=20


[IMPORTS]

# Deprecated modules which should not be used, separated by a comma
deprecated-modules=regsub,TERMIOS,Bastion,rexec

# Create a graph of every (i.e. internal and external) dependencies in the
# given file (report RP0402 must not be disabled)
import-graph=

# Create a graph of external dependencies in the given file (report RP0402 must
# not be disabled)
ext-import-graph=

# Create a graph of internal dependencies in the given file (report RP0402 must
# not be disabled)
int-import-graph=


[EXCEPTIONS]

# Exceptions that will emit a warning when being caught. Defaults to
# "Exception"
overgeneral-exceptions=Exception

########NEW FILE########
