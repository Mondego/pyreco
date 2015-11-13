__FILENAME__ = compiler
#!/usr/bin/env python3

"""Compiler module

Acts as the command line interface to the compiler components. When given a
source file, the compilation process will be executed.

Author: Evan Sneath
License: Open Software License v3.0

Functions:
    parse_arguments: Parses incoming command line arguments.
    run_compiler: Executes the complete compilation process.
"""

# Import standard libraries
import argparse
import subprocess
import sys

# Import custom compiler libraries
from lib.parser import Parser


def parse_arguments():
    """Parse Arguments

    Parses all command line arguments for the compiler program.

    Returns:
        An object containing all expected command line arguments.
    """
    # Parse the command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug',
                        help='print comments in generated code',
                        action='store_true')
    parser.add_argument('source',
                        help='source file to compile')
    parser.add_argument('-o', '--out',
                        help='target path for the compiled code',
                        action='store',
                        default='a.out')
    args = parser.parse_args()

    return args


def run_compiler(source, target, debug=False):
    """Run Compiler

    Executes the compilation process given a source file path.

    Arguments:
        source: The source file to compile.
        target: The destination binary executable file.
        debug: If True, verbose parsing details are shown. (Default: False)

    Returns:
        True on success, False otherwise.
    """
    # Define a temporary location for the intermediate C code
    TMP_CODE_FILE = './ir.c'

    # Create a Parser object to parse the inputted source file
    parser = Parser(debug)

    # Parse the source file to the temporary code file
    if not parser.parse(source, TMP_CODE_FILE):
        print('Error while parsing "%s"' % source)
        return False

    # Set up gcc compilation command
    gcc_cmd = ['gcc', '-m32', '-o', target, TMP_CODE_FILE]

    # Compile the temporary file with gcc. Output to the target location
    if subprocess.call(gcc_cmd) != 0:
        print('Error while compiling "%s"' % target)
        return False

    return True


if __name__ == '__main__':
    # Parse compiler arguments
    args = parse_arguments()

    # Run compilation process
    result = run_compiler(args.source, args.out, debug=args.debug)

    # Terminate program
    sys.exit(not result)

########NEW FILE########
__FILENAME__ = codegenerator
#!/usr/bin/env python3

"""CodeGenerator module

Provides functionality for code output to a attached destination file.

Author: Evan Sneath
License: Open Software License v3.0

Classes:
    CodeGenerator: A code generator interface for destination file outputting.
"""


class CodeGenerator:
    """CodeGenerator class

    This class implements code generator function calls to easily attach a
    destination file, input code to generate, and commit the destination
    file upon successful compilation. This class is designed to be inherited
    the be used during the parsing stage of the compiler.

    Attributes:
        runtime_functions: Details of each runtime function and its params.

    Methods:
        attach_destination: Binds a destination file to the code generator.
        generate_header: Generates overhead code (memory allocation, etc).
        generate_footer: Generates finishing overhead code.
        generate: Formats and stores a given string of code for later output.
        comment: Adds a comment to the generated code with appropriate tabbing.
        tab_push: Increases the tab depth by 1 tab (4 spaces).
        tab_pop: Decreases the tab depth by 1 tab (4 spaces).
        commit: Commits all code generation and writes to the destination file.
        get_mm: Provides a free memory space for global or local variables.
        reset_local_ptr: Resets the value for the local pointer to default.
        reset_param_ptr: Resets the value for the param pointer to default.
        get_reg: Provides a free register for intermediate variable use.
        get_label_id: Returns a unique identifier for the procedure call.
        get_unique_call_id: Returns a unique identifier for multiple calls.
        generate_program_entry: Generates all code associated with setting up
            the program entry and exit point.
        generate_procedure_call: Generates all code associated with managing
            the memory stack during a procedure call.
        generate_procedure_call_end: Generates code to clean up a procedure
            call. This finalizes the call by popping the SP to local stack.
        generate_name: Generates all code associated with name reference.
        generate_assignment: Generates all code associated with id assignment.
        generate_param_push: Generates code to push a param onto the stack.
        generate_param_pop: Generates code to pop a param off the stack.
        generate_param_store: Generates code to save an outgoing parameter
            to an identifier located in main memory.
        generate_number: Generates the code for a number reference.
        generate_return: Generates the code for the 'return' operation.
        generate_operation: Generates operation code given an operation.
    """
    def __init__(self):
        super().__init__()

        # Holds the file path of the attached destination file
        self._dest_path = ''

        # Holds all generated code to be written to the file destination
        self._generated_code = ''

        # Holds allocated size of main memory and num registers
        self._mm_size = 65536
        self._reg_size = 2048
        self._buf_size = 256

        # Holds stack pointer, frame pointer, and heap pointer registers
        self._SP = 1
        self._FP = 2
        self._HP = 3

        # Holds the pointer to the lowest unused register for allocation
        self._reg = 4

        # Holds the local memory pointer which determines the offset from the
        # frame pointer in the current scope.
        self._local_ptr = 0
        self.reset_local_ptr()

        # Holds the param memory pointer which determines the offset from the
        # frame pointer in the current scope.
        self._param_ptr = 0
        self.reset_param_ptr()

        # Holds the tab count of the code. tab_push, tab_pop manipulate this
        self._tab_count = 0

        # Holds an integer used for unique label generation for if/loop
        self._label_id = 0

        # Holds an integer to distinguish multiple calls of a function
        self._unique_id = 0

        # Holds the details of the runtime functions
        self.runtime_functions = {
            'getString': [('my_string', 'string', 'out')],
            'putString': [('my_string', 'string', 'in')],
            'getBool': [('my_bool', 'bool', 'out')],
            'putBool': [('my_bool', 'bool', 'in')],
            'getInteger': [('my_integer', 'integer', 'out')],
            'putInteger': [('my_integer', 'integer', 'in')],
            'getFloat': [('my_float', 'float', 'out')],
            'putFloat': [('my_float', 'float', 'in')],
        }

        return

    def attach_destination(self, dest_path):
        """Attach Destination

        Attaches a destination file to the code generator and prepares the
        file for writing.

        Arguments:
            dest_path: The path to the destination file to write.

        Returns:
            True on success, False otherwise.
        """
        # The target file was attached, store the path
        self._dest_path = dest_path

        return True

    def generate_header(self):
        """Generate Code Header

        Adds all header code to the generated code buffer.
        """
        code = [
            '#include <stdio.h>',
            '#include <string.h>',
            '',
            '#define MM_SIZE  %d' % self._mm_size,
            '#define R_SIZE   %d' % self._reg_size,
            '#define BUF_SIZE %d' % self._buf_size,
            '',
            '// Define register locations of stack/frame ptr',
            '#define SP       %d' % self._SP,
            '#define FP       %d' % self._FP,
            '#define HP       %d' % self._HP,
            '',
            'int main(void)',
            '{',
            '// Allocate main memory and register space',
            'int MM[MM_SIZE];',
            'int R[R_SIZE];',
            '',
            '// SP and FP start at the top of MM',
            'R[SP] = MM_SIZE - 1;',
            'R[FP] = MM_SIZE - 1;',
            '',
            '// HP starts at the bottom of MM',
            'R[HP] = 0;',
            '',
            '// Allocate float registers',
            'float R_FLOAT_1;',
            'float R_FLOAT_2;',
            '',
            '// Allocate space for a string buffer',
            'char STR_BUF[BUF_SIZE];',
            '',
            '////////////////////////////////////////////////////',
            '// PROGRAM START',
            '',
        ]

        self.generate('\n'.join(code), tabs=0)

        return

    def generate_footer(self):
        """Generate Code Footer

        Adds all footer code to the generated code buffer.
        """
        code = [
            '',
            '    // Jump to the program exit',
            '    goto *(void*)MM[R[FP]];',
            '',
            '////////////////////////////////////////////////////',
            '// RUNTIME FUNCTIONS',
            '',
            'putString_1:',
            '    R[0] = MM[R[FP]+2];',
            '    printf("%s\\n", (char*)R[0]);',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'getString_1:',
            '    fgets(STR_BUF, BUF_SIZE, stdin);',
            '    R[0] = strlen(STR_BUF) + 1;',
            '    memcpy(&MM[R[HP]], &STR_BUF, R[0]);',
            '    MM[R[FP]+2] = (int)((char*)&MM[R[HP]]);',
            '    R[HP] = R[HP] + R[0];',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'putBool_1:',
            '    R[0] = MM[R[FP]+2];',
            '    printf("%s\\n", R[0] ? "true" : "false");',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'getBool_1:',
            '    scanf("%d", &R[0]);',
            '    R[0] = R[0] ? 1 : 0;',
            '    MM[R[FP]+2] = R[0];',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'putInteger_1:',
            '    R[0] = MM[R[FP]+2];',
            '    printf("%d\\n", R[0]);',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'getInteger_1:',
            '    scanf("%d", &R[0]);',
            '    MM[R[FP]+2] = R[0];',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'putFloat_1:',
            '    R[0] = MM[R[FP]+2];',
            '    memcpy(&R_FLOAT_1, &R[0], sizeof(float));',
            '    printf("%g\\n", R_FLOAT_1);',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '',
            'getFloat_1:',
            '    scanf("%f", &R_FLOAT_1);',
            '    memcpy(&R[0], &R_FLOAT_1, sizeof(float));',
            '    MM[R[FP]+2] = R[0];',
            '    R[0] = MM[R[FP]];',
            '    goto *(void*)R[0];',
            '}',
        ]

        self.generate('\n'.join(code), tabs=0)

        return

    def generate(self, code, tabs=-1):
        """Generate Code
        
        Adds the given code to the generated code and automatically formats
        it with the appropriate tabs and ending newline.

        Arguments:
            code: The code to add to the generated code buffer.
            tabs: A manual override to determine the number of tabs to place
                in this line of code. If -1, then the number of tabs used will
                correspond to the tab location from tab_push() and tab_pop()
                methods. (Default: -1)
        """
        tabs = tabs if tabs != -1 else self._tab_count
        self._generated_code += ('    ' * tabs) + code + '\n'

        return

    def comment(self, text, is_displayed=False):
        """Generate Comment

        Adds a comment to the generated code.

        Arguments:
            text: The text to display in the comment.
            is_displayed: If True, the comment is written to the generated
                code. (Default: False)
        """
        if is_displayed:
            self.generate('// %s' % text)

        return

    def tab_push(self):
        """Tab Push

        Pushes the tab (increases the indentation by 4 spaces) for pretty
        code output.
        """
        self._tab_count += 1
        return

    def tab_pop(self):
        """Tab Pop

        Pops the tab (decreases the indentation by 4 spaces) for pretty code
        output.
        """
        self._tab_count -= 1 if self._tab_count != 0 else 0
        return

    def commit(self):
        """Commit Code Generation

        Writes the generated code to the destination output file for
        intermediate code if the source is parsed without fatal errors.

        Returns:
            True if file is successfully written, False otherwise.
        """
        try:
            with open(self._dest_path, 'w+') as f:
                f.write(self._generated_code)
        except IOError as e:
            print('Error: "%s"' % self._dest_path)
            print('    Could not write to destination file: %s' % e.strerror)
            return False

        return True

    def get_mm(self, id_size, is_param=False):
        """Get Memory Space

        Gets a space in memory appropriately depending on if the variable is
        a local variable or a parameter to the scope.

        Arguments:
            id_size: The size of the parameter to allocate (used for arrays).
            is_param: True if the identifier is a parameter, False if local or
                global variable. (Default: False)

        Returns:
            An integer denoting the offset corresponding to a stack landmark
            depending on the type of variable. For example, local variables
            and params are offset by the current FP in different directions
            while global variables are offset by the top of main memory.
            See the documentation in README for stack details.
        """
        # Determine size of the identifier
        mem_needed = int(id_size) if id_size is not None else 1
        
        if is_param:
            var_loc = self._param_ptr
            self._param_ptr += mem_needed
        else:
            # Allocate memory in the local variable space
            var_loc = self._local_ptr
            self._local_ptr += mem_needed

        return var_loc

    def reset_local_ptr(self):
        """Reset Local Pointer

        Resets the pointer to the current scope's local variable portion of
        the stack. This is used to properly allocate space for the local
        variables at the start of the scope.
        """
        self._local_ptr = 1
        return

    def reset_param_ptr(self):
        """Reset Param Pointer

        Resets the pointer to the current scope's parameter portion of the
        stack. This is necessary to properly allocate space for the parameters
        as they are being pushed onto the stack.
        """
        self._param_ptr = 1
        return

    def get_reg(self, inc=True):
        """Get Register

        Gets new, unused register from the register list.

        Arguments:
            inc: If True, a new register will be returned. If False, the last
                register allocated will be returned.

        Returns:
            An integer denoting the register number. The register may then be
            referenced as follows: R[<reg_num>]
        """
        # Increment the register if we're getting a brand new one
        self._reg += 1 if inc else 0

        return self._reg

    def get_label_id(self):
        """Get Label Id

        Gets a label id so that no conflicts occur between procedures with
        the same name in difference scopes.

        Returns:
            A label id to append to the procedure label.
        """
        self._label_id += 1

        return self._label_id

    def get_unique_call_id(self):
        """Get Unique Call Id

        Gets a unique call id so that no conflicts occur between return
        labels for procedures with multiple calls.

        Returns:
            A unique id to append to the procedure return label.
        """
        self._unique_id += 1

        return self._unique_id

    def generate_program_entry(self, program_name, program_num, debug):
        """Generate Program Entry

        Generates the code associated with managing the entry point for the
        program. This involves pushing the program return address onto the
        stack, jumping to the entry point, and creating the program exit
        section.

        Arguments:
            program_name: The name of the program.
            program_num: The label id of the program.
            debug: Determines if comments should be written to the code.
        """
        # Push the return address onto the stack
        self.comment('Setting program return address', debug)
        self.generate('MM[R[FP]] = (int)&&%s_%d_end;' %
                      (program_name, program_num))

        # Make the jump to the entry point
        self.generate('goto %s_%d_begin;' % (program_name, program_num))

        # Make the main program return
        self.generate('')
        self.comment('Creating the program exit point', debug)
        self.generate('%s_%d_end:' % (program_name, program_num))
        self.tab_push()
        self.generate('return 0;')
        self.tab_pop()
        self.generate('')

        return

    def generate_procedure_call(self, procedure_name, procedure_num, debug):
        """Generate Procedure Call

        Generates the code associated with managing the stack before and
        after a procedure call. Note that this does not include param
        pushing and popping operations.

        Arguments:
            procedure_name: The name of the procedure to call.
            procedure_num: The label id of the procedure to call.
            debug: Determines if comments should be written to the code.
        """
        # Save the FP to the stack. Set next FP to return address
        self.comment('Setting caller FP', debug)
        self.generate('R[SP] = R[SP] - 1;')
        self.generate('MM[R[SP]] = R[FP];')
        self.comment('Setting return address (current FP)', debug)
        self.generate('R[SP] = R[SP] - 1;')
        self.generate('R[FP] = R[SP];')

        # Generate a new call number so multiple calls do not cause collisions
        call_number = self.get_unique_call_id()

        # Push the return address onto the stack
        self.generate('MM[R[SP]] = (int)&&%s_%d_%d;' %
                (procedure_name, procedure_num, call_number))
                
        # Make the jump to the function call
        self.generate('goto %s_%d;' % (procedure_name, procedure_num))

        # Generate the return label
        self.generate('%s_%d_%d:' % (procedure_name, procedure_num, call_number))

        # The SP now points to the return address. Restore the old FP
        self.comment('Restore caller FP', debug)
        self.generate('R[SP] = R[SP] + 1;')
        self.generate('R[FP] = MM[R[SP]];')

        return

    def generate_procedure_call_end(self, debug):
        """Generate Procedure Call End

        Generates code to leave the procedure on the stack by pushing the
        stack to the lower scope's local stack.

        Arguments:
            debug: Determines if comments are to be written in generated code.
        """
        self.comment('Move to caller local stack', debug)

        # Finalize the function call. Move the SP off the param list
        self.generate('R[SP] = R[SP] + 1;')

        return

    def _generate_get_id_in_mm(self, id_obj, id_location, idx_reg, debug):
        """Generate Get Identifier in Main Memory (Protected)

        Knowing the location in the stack and the offset (mm_ptr) value of
        a given index, code is generated to calculate the exact location of
        the identifier in main memory.

        If identifier is param, offset is the parameter offset.
        If identifier is local, offset is the local offset.
        If identifier is global, offset is the local offset of program scope.

        Arguments:
            id_obj: The Identifier class object containing id data.
            id_location: Either 'global', 'param', or 'local' depending on the
                location in the stack where the identifier resides.
            idx_reg: The register number of the index expression.
            debug: Determines if comments are to be written in generated code.

        Returns:
            The register number of the calculated address of the identifier.
        """
        # Get a new register to calculate the main memory address of this id
        id_reg = self.get_reg()

        self.generate('R[%d] = %d;' % (id_reg, id_obj.mm_ptr))

        if id_obj.size is not None and idx_reg is not None:
            self.generate('R[%d] = R[%d] + R[%d];' %
                    (id_reg, id_reg, idx_reg))

        if id_location == 'param':
            self.comment('Param referenced', debug)
            self.generate('R[%d] = R[FP] + 1 + R[%d];' % (id_reg, id_reg))
        elif id_location == 'global':
            self.comment('Global var referenced', debug)
            self.generate('R[%d] = MM_SIZE - 1 - R[%d];' % (id_reg, id_reg))
        else:
            self.comment('Local var referenced', debug)
            self.generate('R[%d] = R[FP] - R[%d];' % (id_reg, id_reg))

        return id_reg

    def generate_name(self, id_obj, id_location, idx_reg, debug):
        """Generate Name

        Generates all code necessary to place the contents of the memory
        location of a given identifier into a new register for computation.

        Arguments:
            id_obj: The Identifier class object containing id data.
            id_location: Either 'global', 'param', or 'local' depending on the
                location in the stack where the identifier resides.
            idx_reg: The register number of the index expression.
            debug: Determines if comments are to be written in generated code.
        """
        # Calculate the position of the identifier in main memory
        id_reg = self._generate_get_id_in_mm(id_obj, id_location, idx_reg,
                                             debug)

        # Retrieve the main memory location and place it in the last register
        self.generate('R[%d] = MM[R[%d]];' % (id_reg, id_reg))

        return

    def generate_assignment(self, id_obj, id_location, idx_reg, expr_reg,
                            debug):
        """Generate Assignment

        Generates all code necessary to place the outcome of an expression
        into the proper location of the identifier in main memory.

        Arguments:
            id_obj: The Identifier class object containing id data.
            id_location: Either 'global', 'param', or 'local' depending on the
                location in the stack where the identifier resides.
            idx_reg: The register number of the index expression.
            expr_reg: The register number of the expression outcome.
            debug: Determines if comments are to be written in generated code.
        """
        # Calculate the position of the identifier in main memory
        id_reg = self._generate_get_id_in_mm(id_obj, id_location, idx_reg,
                                             debug)

        # Set the main memory value to the value in the expression register
        self.generate('MM[R[%d]] = R[%d];' % (id_reg, expr_reg))

        return

    def generate_param_push(self, expr_reg, debug):
        """Generate Param Push

        Generates code to push a parameter onto the procedure stack given
        a register containing the expression outcome.

        Arguments:
            expr_reg: The register number of the expression outcome.
            debug: Determines if comments are to be written in generated code.
        """
        self.comment('Pushing argument onto the stack', debug)
        self.generate('R[SP] = R[SP] - 1;')
        self.generate('MM[R[SP]] = R[%d];' % expr_reg)

        return

    def generate_param_pop(self, param_name, debug):
        """Generate Param Pop

        Pops a parameter off of the stack (moves the SP) and prints a
        comment stating which parameter this is.

        Arguments:
            param_name: The parameter name to display.
            debug: Determines if comments are to be written in generated code.
        """
        self.comment('Popping "%s" param off the stack' % param_name, debug)
                
        # Move to the next memory space
        self.generate('R[SP] = R[SP] + 1;')

        return

    def generate_param_store(self, id_obj, id_location, debug):
        """Generate Param Store

        Calculates the memory location of the destination and placed the
        value of the popped parameter (at current SP) in that location.

        Arguments:
            id_obj: The Identifier class object containing id data.
            id_location: Either 'global', 'param', or 'local' depending on the
                location in the stack where the identifier resides.
            debug: Determines if comments are to be written in generated code.
        """
        # Calculate the position of the parameter output location in main mem
        id_reg = self._generate_get_id_in_mm(id_obj, id_location, None, debug)

        # Store the parameter in the position pointed to by the SP
        self.generate('MM[R[%d]] = MM[R[SP]];' % id_reg)

        return

    def generate_number(self, number, token_type, negate):
        """Generate Number

        Generates the code to store a parsed number in a new register.

        Arguments:
            number: The parsed number value (this is a string representation).
            token_type: The type of the number (either 'integer' or 'float')
            negate: A boolean to determine whether or not to negate the value.
        """
        reg = self.get_reg()

        if token_type == 'integer':
            # This is an integer value, set it to the register
            if negate:
                self.generate('R[%d] = -%s;' % (reg, number))
            else:
                self.generate('R[%d] = %s;' % (reg, number))
        else:
            # This is a float value, place it in the float buffer and copy it
            # to the register
            if negate:
                self.generate('R_FLOAT_1 = -%s;' % number)
            else:
                self.generate('R_FLOAT_1 = %s;' % number)

            self.generate('memcpy(&R[%d], &R_FLOAT_1, sizeof(float));' % reg)

        return

    def generate_return(self, debug):
        """Generate Return Statement

        Generates code for all operations needed to move to the scope return
        address and execute the jump to the caller scope.

        Arguments:
            debug: Determines if comments should be displayed or not.
        """
        # Smash the local stack
        self.comment('Moving SP to FP (return address)', debug)
        self.generate('R[SP] = R[FP];')

        # Go to the return label to exit the procedure
        self.comment('Return to calling function', debug)
        self.generate('goto *(void*)MM[R[FP]];')

        return

    def generate_operation(self, reg1, type1, reg2, type2, operation):
        """Generate Operation

        Given an operation and operand registers with their types, code is
        generated to perform these operations.

        Arguments:
            reg1: The register of the first operand.
            type1: The type of the first operand.
            reg2: The register of the second operand.
            type2: The type of the second operand.
            operation: The operation symbol to perform.

        Returns:
            The register number where the result of the operation
            is stored.
        """
        # Get a register to hold the operation result
        result = self.get_reg()

        if type1 != 'float' and type2 != 'float':
            self.generate('R[%d] = R[%d] %s R[%d];' %
                          (result, reg1, operation, reg2))
            return result

        if type1 != 'float':
            self.generate('R_FLOAT_1 = R[%d];' % reg1)
        else:
            self.generate('memcpy(&R_FLOAT_1, &R[%d], sizeof(float));' % reg1)

        if type2 != 'float':
            self.generate('R_FLOAT_2 = R[%d];' % reg2)
        else:
            self.generate('memcpy(&R_FLOAT_2, &R[%d], sizeof(float));' % reg2)

        self.generate('R_FLOAT_1 = R_FLOAT_1 %s R_FLOAT_2;' % operation)
        self.generate('memcpy(&R[%d], &R_FLOAT_1, sizeof(float));' % result)
        
        return result

########NEW FILE########
__FILENAME__ = datatypes
#!/usr/bin/env python3

"""Types module

Provides data structures necessary for identifier tracking and handling in the
compilation process as well as tokenizing.

Author: Evan Sneath
License: Open Software License v3.0

Classes:
    Token: A named tuple object containing token information.
    Identifier: A named tuple object containing identifier information.
    Parameter: A named tuple object containing procedure param information.
    IdentifierTable: Extends the list type to provide ID table functionality.
"""

from lib.errors import ParserNameError
from collections import namedtuple


"""Token class

A named tuple object factory containing token information.

Attributes:
    type: The data type of the token to be stored.
    value: The value of the token being stored.
    line: The line number on which the token was encountered.
"""
Token = namedtuple('Token', ['type', 'value', 'line'])


"""Identifier class

A named tuple object factory containing identifier information.

Attributes:
    name: The identifier name. This acts as the dictionary key.
    type: The data type of the identifier.
    size: The number of elements of the identifier if a variable.
        If procedure, program, or non-array type, None is expected.
    params: A list of Parameter class objects describing procedure params.
    mm_ptr: A pointer to the location of the identifier in main memory.
"""
Identifier = namedtuple('Identifier',
        ['name', 'type', 'size', 'params', 'mm_ptr'])


"""Parameter class

A named tuple object factory containing procedure parameter information.

Attributes:
    id: The Identifier named tuple of the parameter.
    direction: The direction ('in' or 'out') of the parameter.
"""
Parameter = namedtuple('Parameter', ['id', 'direction'])


class IdentifierTable(list):
    """IdentifierTable class

    Extends the List built-in type with all methods necessary for identifier
    table management during compilation.

    Methods:
        push_scope: Adds a new scope.
        pop_scope: Removes the highest scope.
        add: Adds a new identifier to the current or global scope.
        find: Determines if an identifier is in the current of global scope.
        get_id_location: Determines where the identifier exists in the scope.
        is_global: Determines if an identifier exists in the global scope.
        is_param: Determines if an identifier is a parameter of the scope.
        get_param_direction: Gets the direction of the parameter in the scope.
        get_current_scope_owner: Gets the program or procedure name from which
            the current scope was created.
    """
    def __init__(self):
        super().__init__()

        # Create the global scope
        self.append({})

        # Create a list of scope parent names (the owner of the scope)
        self._owner_ids = ['global']

        return

    def push_scope(self, owner_id):
        """Push New Identifier Scope

        Creates a new scope on the identifiers table and increases the global
        current scope counter.

        Arguments:
            owner_id: The name of the identifier which has created this scope.
        """
        # Create a brand new scope for the identifiers table
        self.append({})

        # Save the owner of this scope for future lookup
        self._owner_ids.append(owner_id)

        return

    def pop_scope(self):
        """Pop Highest Identifier Scope

        Disposes of the current scope in the identifiers table and decrements
        the global current scope counter.
        """
        # Remove this entire scope from the identifiers table
        self.pop(-1)

        # Remove the identifier from the owner list
        self._owner_ids.pop()

        return

    def add(self, identifier, is_global=False):
        """Add Identifier to Scope

        Adds a new identifier to either the current scope of global.

        Arguments:
            identifier: An Identifier named tuple object describing the new
                identifier to add to the table.
            is_global: Determines whether the identifier should be added to
                the current scope or the global scope. (Default: False)

        Raises:
            ParserNameError if the identifier has been declared at this scope.
        """
        scope = -1 if not is_global else 0

        if is_global and len(self) > 2:
            raise ParserNameError('global name must be defined in program scope')

        if is_global and (identifier.name in self[0] or (len(self) > 1 and
                          identifier.name in self[1])):
            raise ParserNameError('name already declared at this scope')

        if not is_global and identifier.name in self[-1]:
            raise ParserNameError('name already declared at this scope')

        self[scope][identifier.name] = identifier

        return

    def find(self, name):
        """Find Identifier in Scope

        Searches for the given identifier in the current and global scope.

        Arguments:
            name: The identifier name for which to search.

        Returns:
            An Identifier named tuple containing identifier name, type and size
            information if found in the current or global scopes.

        Raises:
            ParserNameError if the given identifier is not found in any valid scope.
        """
        if name in self[-1]:
            identifier = self[-1][name]
        elif name in self[0]:
            identifier = self[0][name]
        else:
            raise ParserNameError()

        return identifier

    def get_id_location(self, name):
        """Get Identifier Location

        Determines the location of the identifier in the stack based on the
        identifier's place in the id table.

        Arguments:
            name: The identifier name for which to search.

        Returns:
            A string value for the location of the identifier in the stack.
            This may be 'global', 'param', or 'local'.
        """
        if self.is_global(name):
            return 'global'
        elif self.is_param(name):
            return 'param'

        return 'local'

    def is_global(self, name):
        """Identifier is Global

        Determines if an identifier exists in the global scope.

        Arguments:
            name: The identifier name for which to search.

        Returns:
            True if the identifier exists in the global scope. False otherwise.
        """
        return name in self[0]

    def is_param(self, name):
        """Identifier is Parameter

        Determines if an identifier is a parameter in the current scope.

        Arguments:
            name: The identifier name for which to search.

        Returns:
            True if the identifier is a scope parameter. False otherwise.
        """
        owner = self.get_current_scope_owner()

        if owner == 'global' or not owner.params:
            return False

        for param in owner.params:
            if name == param.id.name:
                return True

        return False

    def get_param_direction(self, name):
        """Get Parameter Direction

        If the name given is a valid parameter of the scope, the direction
        ('in' or 'out') will be returned.

        Arguments:
            name: The identifier name for which to search.

        Returns:
            'in' or 'out' depending on the parameter direction. None if the
            name given is not a valid parameter of the current scope.
        """
        owner = self.get_current_scope_owner()
        
        if owner == 'global':
            return None

        for param in owner.params:
            if name == param.id.name:
                return param.direction

        return None

    def get_current_scope_owner(self):
        """Get Current Scope Owner

        Returns the Identifier object of the owner of the current scope. This
        owner will either be a 'program' or 'procedure' type.

        Returns:
            The Identifier object of the owner of the current scope. None if
            the current scope is the global scope.
        """
        owner = self._owner_ids[-1]

        # If this is the global scope, return no owner
        return self[-1][self._owner_ids[-1]] if owner != 'global' else None

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python3


class ParserError(Exception):
    """ParserError class

    The base error class for all other parsing errors. This should be caught
    at resync points.
    """
    pass


class ParserSyntaxError(ParserError):
    """ParserSyntaxError class

    Thrown when a syntax error occurs in the parser.
    """
    pass


class ParserNameError(ParserError):
    """ParserNameError class

    Thrown when a name error occurs in the parser.
    """
    pass


class ParserTypeError(ParserError):
    """ParserTypeError class

    Thrown when a type error occurs in the parser.
    """
    pass


class ParserRuntimeError(ParserError):
    """ParserRuntimeError class

    Thrown when a runtime error occurs in the parser.
    """
    pass

########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/env python3

"""Parser module

Inherits the Scanner module and parses the attached file's tokens as they are
encountered with the target grammar. Code is then generated and written to the
given destination file.

Author: Evan Sneath
License: Open Software License v3.0

Classes:
    Parser: An implementation of a parser for the source language.
"""

from lib.errors import *
from lib.datatypes import Identifier, Parameter, IdentifierTable

from lib.scanner import Scanner
from lib.codegenerator import CodeGenerator


class Parser(Scanner, CodeGenerator):
    """Parser class

    Parses the given source file using the defined language structure.

    Inherits:
        Scanner: The lexer component of the compiler.
        CodeGenerator: The class responsible for output file abstraction.

    Attributes:
        debug: Boolean attribute denoting if successfully parsed tokens should
            be displayed as they are encountered and parsed.

    Methods:
        parse: Parses the given file until a terminal error is encountered or
            the end-of-file token is reached.
    """
    def __init__(self, debug=False):
        super().__init__()

        # Public class attributes
        self.debug = debug

        # Define the previous, current, and future token holder
        self._previous = None
        self._current = None
        self._future = None

        # Define the identifier table to hold all var/program/procedure names
        self._ids = IdentifierTable()

        self._has_errors = False

        return

    def parse(self, src_path, dest_path):
        """Begin Parsing

        Begins the parse of the inputted source file.

        Arguments:
            src_path: The input source file to parse.
            dest_path: The output target file to write.

        Returns:
            True on success, False otherwise.
        """
        # Attach the source file for reading
        if not self.attach_source(src_path):
            return False

        # Attach the destination file for writing
        if not self.attach_destination(dest_path):
            return False

        # Advance the tokens twice to populate both current and future tokens
        self._advance_token()
        self._advance_token()

        # Add all runtime functions
        self._add_runtime()

        # Generate the compiled code header to handle runtime overhead
        self.generate_header()

        # Begin parsing the root <program> language structure
        try:
            self._parse_program()
        except ParserSyntaxError:
            return False

        # Generate the compiled code footer
        self.generate_footer()

        # Make sure there's no junk after the end of program
        if not self._check('eof'):
            self._warning('eof', '')

        # If errors were encountered, don't write code
        if self._has_errors:
            return False

        # Commit the code buffer to the output code file
        self.commit()

        return True

    def _add_runtime(self):
        """Add Runtime Functions

        Adds each runtime function to the list of global functions.
        """
        # The runtime_functions list is defined in the CodeGenerator class
        for func_name in self.runtime_functions:
            # Get all parameters for these functions
            param_ids = []
            param_list = self.runtime_functions[func_name]
            for index, param in enumerate(param_list):
                # Build up each param, add it to the list
                id_obj = Identifier(name=param[0], type=param[1], size=None,
                                    params=None, mm_ptr=(index+1))
                p_obj = Parameter(id=id_obj, direction=param[2])
                param_ids.append(p_obj)

            # Build the function's identifier
            func_id = Identifier(name=func_name, type='procedure', size=None, 
                                 params=param_ids, mm_ptr=1)

            # Add the function to the global scope of the identifier table
            self._ids.add(func_id, is_global=True)

        return

    def _warning(self, msg, line, prefix='Warning'):
        """Print Parser Warning Message (Protected)

        Prints a parser warning message with details about the expected token
        and the current token being parsed.

        Arguments:
            msg: The warning message to display.
            line: The line where the warning has occurred.
            prefix: A string value to be printed at the start of the warning.
                Overwritten for error messages. (Default: 'Warning')
        """
        print('%s: "%s", line %d' % (prefix, self._src_path, line))
        print('    %s' % msg)
        print('    %s' % self._get_line(line))

        return

    def _syntax_error(self, expected):
        """Print Syntax Error Message (Protected)

        Prints a syntax error message with details about the expected token
        and the current token being parsed. After error printing, an exception
        is raised to be caught and resolved by parent nodes.

        Arguments:
            expected: A string containing the expected token type/value.

        Raises:
            ParserSyntaxError: If this method is being called, an error has been
                encountered during parsing.
        """
        token = self._current

        # Print the error message
        msg = ('Expected %s, encountered "%s" (%s)' %
               (expected, token.value, token.type))
        self._warning(msg, token.line, prefix='Error')

        self._has_errors = True
        raise ParserSyntaxError()

    def _name_error(self, msg, name, line):
        """Print Name Error Message (Protected)

        Prints a name error message with details about the encountered
        identifier which caused the error.

        Arguments:
            msg: The reason for the error.
            name: The name of the identifier where the name error occurred.
            line: The line where the name error occurred.
        """
        msg = '%s: %s' % (name, msg)
        self._warning(msg, line, prefix='Error')

        self._has_errors = True
        return

    def _type_error(self, expected, encountered, line):
        """Print Type Error Message (Protected)

        Prints a type error message with details about the expected type an
        the type that was encountered.

        Arguments:
            expected: A string containing the expected token type.
            encountered: A string containing the type encountered.
            line: The line on which the type error occurred.
        """
        msg = 'Expected %s type, encountered %s' % (expected, encountered)
        self._warning(msg, line, prefix='Error')

        self._has_errors = True
        return

    def _runtime_error(self, msg, line):
        """Print Runtime Error Message (Protected)

        Prints a runtime error message with details about the runtime error.

        Arguments:
            msg: The reason for the error.
            line: The line where the runtime error occurred.
        """
        self._warning(msg, line, prefix='Error')

        self._has_errors = True
        return

    def _advance_token(self):
        """Advance Tokens (Protected)

        Populates the 'current' token with the 'future' token and populates
        the 'future' token with the next token in the source file.
        """
        self._previous = self._current
        self._current = self._future

        if self._future is None or self._future.type != 'eof':
            self._future = self.next_token()

        return

    def _check(self, expected_type, expected_value=None, check_future=False):
        """Check Token (Protected)

        Peeks at the token to see if the current token matches the given
        type and value. If it doesn't, don't make a big deal about it.

        Arguments:
            expected_type: The expected type of the token.
            expected_value: The expected value of the token. (Default: None)
            check_future: If True, the future token is checked (Default: False)

        Returns:
            True if the token matches the expected value, False otherwise.
        """
        token = self._current

        if check_future:
            token = self._future

        return (token.type == expected_type and
               (token.value == expected_value or expected_value is None))

    def _accept(self, expected_type, expected_value=None):
        """Accept Token (Protected)

        Compares the token to an expected type and value. If it matches, then
        consume the token. If not, don't make a big deal about it.

        Arguments:
            expected_type: The expected type of the token.
            expected_value: The expected value of the token. (Default: None)

        Returns:
            True if the token matches the expected value, False otherwise.
        """
        if self._check(expected_type, expected_value):
            self._advance_token()
            return True

        return False

    def _match(self, expected_type, expected_value=None):
        """Match Token (Protected)

        Compares the token to an expected type and value. If it matches, then
        consume the token. If not, then throw an error and panic.

        Arguments:
            expected_type: The expected type of the token.
            expected_value: The expected value of the token. (Default: None)

        Returns:
            The matched Token class object if successful.
        """
        # Check the id_type, if we specified debug, print everything matched
        if self._accept(expected_type, expected_value):
            return self._previous

        # Something different than expected was encountered
        if expected_value is not None:
            self._syntax_error('"'+expected_value+'" ('+expected_type+')')
        else:
            self._syntax_error(expected_type)

    def _resync_at_token(self, token_type, token_value=None):
        """Resync at Token

        Finds the next token of the given type and value and moves the
        current token to that point. Code parsing can continue from there.

        Arguments:
            token_type: The id_type of the token to resync.
            token_value: The value of the token to resync. (Default: None)
        """
        while not self._check(token_type, token_value):
            self._advance_token()

        return

    def _parse_program(self):
        """<program> (Protected)

        Parses the <program> language structure.

            <program> ::=
                <program_header> <program_body>
        """
        id_obj = self._parse_program_header()
        self._parse_program_body(id_obj)

        return

    def _parse_program_header(self):
        """<program_header> (Protected)

        Parses the <program_header> language structure.

            <program_header> ::=
                'program' <identifier> 'is'

        Returns:
            The id object with information about the procedure identifier.
        """
        self._match('keyword', 'program')

        id_name = self._current.value
        self._match('identifier')

        # Generate procedure label. This will be stored with the identifier
        # in place of the mm_ptr attribute since it will not be used
        label_id = self.get_label_id()

        # Add the new identifier to the global table
        id_obj = Identifier(id_name, 'program', None, None, label_id)
        self._ids.add(id_obj, is_global=True)

        self._match('keyword', 'is')

        # Generate the program entry point code
        self.generate_program_entry(id_obj.name, id_obj.mm_ptr, self.debug)

        # Push the scope to the program body level
        self._ids.push_scope(id_obj.name)

        # Add the program to the base scope so it can be resolved as owner
        self._ids.add(id_obj)

        return id_obj

    def _parse_program_body(self, program_id):
        """<program_body> (Protected)

        Parses the <program_body> language structure.

            <program_body> ::=
                    ( <declaration> ';' )*
                'begin'
                    ( <statement> ';' )*
                'end' 'program'

        Arguments:
            program_id: The identifier object for the program.
        """
        local_var_size = 0

        while not self._accept('keyword', 'begin'):
            try:
                size = self._parse_declaration()

                if size is not None:
                    local_var_size += int(size)
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

        # Label the entry point for the program
        self.generate('%s_%d_begin:' % (program_id.name, program_id.mm_ptr))
        self.tab_push()

        if local_var_size != 0:
            self.comment('Allocating space for local variables', self.debug)
            self.generate('R[SP] = R[SP] - %d;' % local_var_size)

        while not self._accept('keyword', 'end'):
            try:
                self._parse_statement()
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

        self._match('keyword', 'program')

        # Pop out of the program body scope
        self._ids.pop_scope()
        self.tab_pop()

        return

    def _parse_declaration(self):
        """<declaration> (Protected)

        Parses the <declaration> language structure.

            <declaration> ::=
                [ 'global' ] <procedure_declaration>
                [ 'global' ] <variable_declaration>

        Returns:
            The size of any variable declared. None if procedure.
        """
        is_global = False

        id_obj = None
        size = None

        if self._accept('keyword', 'global'):
            is_global = True

        if self._first_procedure_declaration():
            self._parse_procedure_declaration(is_global=is_global)
        elif self._first_variable_declaration():
            id_obj = self._parse_variable_declaration(is_global=is_global)
        else:
            self._syntax_error('procedure or variable declaration')

        if id_obj is not None:
            size = id_obj.size if id_obj.size is not None else 1

        return size

    def _first_variable_declaration(self):
        """first(<variable_declaration>) (Protected)

        Determines if current token matches the first terminals.

            first(<variable_declaration>) ::=
                integer | float | bool | string

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return (self._check('keyword', 'integer') or
                self._check('keyword', 'float') or
                self._check('keyword', 'bool') or
                self._check('keyword', 'string'))

    def _parse_variable_declaration(self, is_global=False, is_param=False):
        """<variable_declaration> (Protected)

        Parses the <variable_declaration> language structure.

            <variable_declaration> ::=
                <type_mark> <identifier> [ '[' <array_size> ']' ]

        Arguments:
            is_global: Denotes if the variable is to be globally scoped.
                (Default: False)
            id_table_add: Denotes if the variable is to be added to the
                identifier table.

        Returns:
            The Identifier class object of the variable encountered.
        """
        id_type = self._parse_type_mark()

        # Stores the array size of the variable
        var_size = None

        # Formally match the token to an identifier type
        var_token = self._match('identifier')

        if self._accept('symbol', '['):
            index_type = self._parse_number(generate_code=False)

            var_size = self._previous.value
            index_line = self._previous.line

            # Check the type to make sure this is an integer so that we can
            # allocate memory appropriately
            if  index_type != 'integer':
                self._type_error('integer', index_type, index_line)
                raise ParserTypeError()

            self._match('symbol', ']')

        # Get the memory space pointer for this variable.
        mm_ptr = self.get_mm(var_size, is_param=is_param)

        # The declaration was valid, add the identifier to the table
        id_obj = Identifier(var_token.value, id_type, var_size, None, mm_ptr)

        if not is_param:
            try:
                self._ids.add(id_obj, is_global=is_global)
            except ParserNameError as e:
                self._name_error(str(e),
                                 var_token.value, var_token.line)

        return id_obj

    def _parse_type_mark(self):
        """<type_mark> (Protected)

        Parses <type_mark> language structure.

            <type_mark> ::=
                'integer' |
                'float' |
                'bool' |
                'string'

        Returns:
            Type (as string) of the variable being declared.
        """
        id_type = None

        if self._accept('keyword', 'integer'):
            id_type = 'integer'
        elif self._accept('keyword', 'float'):
            id_type = 'float'
        elif self._accept('keyword', 'bool'):
            id_type = 'bool'
        elif self._accept('keyword', 'string'):
            id_type = 'string'
        else:
            self._syntax_error('variable type')

        return id_type

    def _first_procedure_declaration(self):
        """first(<procedure_declarations>) (Protected)

        Determines if current token matches the first terminals.

            first(<procedure_declaration>) ::=
                'procedure'

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('keyword', 'procedure')

    def _parse_procedure_declaration(self, is_global):
        """<procedure_declaration> (Protected)

        Parses the <procedure_declaration> language structure.

            <procedure_declaration> ::=
                <procedure_header> <procedure_body>

        Arguments:
            is_global: Denotes if the procedure is to be globally scoped.
        """
        id_obj = self._parse_procedure_header(is_global=is_global)
        self._parse_procedure_body(id_obj)

        return

    def _parse_procedure_header(self, is_global):
        """<procedure_header> (Protected)

        Parses the <procedure_header> language structure.

            <procedure_header> ::=
                'procedure' <identifier> '(' [ <parameter_list> ] ')'

        Arguments:
            is_global: Denotes if the procedure is to be globally scoped.
        """
        self._match('keyword', 'procedure')

        id_name = self._current.value
        id_line = self._current.line

        self._match('identifier')
        self._match('symbol', '(')

        params = []

        if not self._check('symbol', ')'):
            params = self._parse_parameter_list(params)

        self._match('symbol', ')')

        # Generate procedure label. This will be stored with the identifier
        # in place of the mm_ptr attribute since it will not be used
        label_id = self.get_label_id()

        id_obj = Identifier(id_name, 'procedure', None, params, label_id)

        try:
            # Add the procedure identifier to the parent and its own table
            self._ids.add(id_obj, is_global=is_global)
            self._ids.push_scope(id_obj.name)
            self._ids.add(id_obj)
        except ParserNameError:
            self._name_error('name already declared at this scope', id_name,
                             id_line)

        # Attempt to add each encountered param at the procedure scope
        for param in params:
            try:
                self._ids.add(param.id, is_global=False)
            except ParserNameError:
                self._name_error('name already declared at global scope',
                                 param.id.name, id_line)

        # Define the entry point for the function w/ unique identifier
        self.generate('%s_%d:' % (id_obj.name, id_obj.mm_ptr))
        self.tab_push()

        # Define the beginning of the function body
        self.generate('goto %s_%d_begin;' % (id_obj.name, id_obj.mm_ptr))
        self.generate('')

        return id_obj

    def _parse_procedure_body(self, procedure_id):
        """<procedure_body> (Protected)

        Parses the <procedure_body> language structure.

            <procedure_body> ::=
                    ( <declaration> ';' )*
                'begin'
                    ( <statement> ';' )*
                'end' 'procedure'

        Arguments:
            procedure_id: The identifier object for the procedure.
        """
        local_var_size = 0

        # Reset the local pointer for the local variables.
        self.reset_local_ptr()
        self.reset_param_ptr()

        # Accept any declarations
        while not self._accept('keyword', 'begin'):
            try:
                size = self._parse_declaration()

                # If this was a local var, allocate space for it
                if size is not None:
                    local_var_size += size
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

        # Define the function begin point
        self.generate('%s_%d_begin:' %
                      (procedure_id.name, procedure_id.mm_ptr))

        self.tab_push()

        if local_var_size != 0:
            self.comment('Allocating space for local variables', self.debug)
            self.generate('R[SP] = R[SP] - %d;' % local_var_size)

        # Accept any statements
        while not self._accept('keyword', 'end'):
            try:
                self._parse_statement()
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

        self._match('keyword', 'procedure')

        # Generate code to jump back to the caller scope
        self.generate_return(self.debug)
        self.generate('')

        self.tab_pop()
        self._ids.pop_scope()
        self.tab_pop()

        return

    def _parse_parameter_list(self, params):
        """<parameter_list> (Protected)

        Parse the <parameter_list> language structure.

            <parameter_list> ::=
                <parameter> ',' <parameter_list> |
                <parameter>

        Arguments:
            params: A list of Parameter named tuples associated with the
                procedure.

        Returns:
            An completed list of all Parameter named tuples associated
            with the procedure.
        """
        # Get one parameter
        param = self._parse_parameter()
        params.append(param)

        # Get all following parameters
        if self._accept('symbol', ','):
            params = self._parse_parameter_list(params)

        # All parameters found will be returned in the list
        return params

    def _parse_parameter(self):
        """<parameter> (Protected)

        Parse the <parameter> language structure.

            <parameter> ::=
                <variable_declaration> ( 'in' | 'out' )
        """
        # Return the id object, but don't add it to the identifier table
        # yet or get a memory location for it. This will be done when the
        # procedure is called
        id_obj = self._parse_variable_declaration(is_param=True)

        direction = None

        if self._accept('keyword', 'in'):
            direction = 'in'
        elif self._accept('keyword', 'out'):
            direction = 'out'
        else:
            self._syntax_error('"in" or "out"')

        return Parameter(id_obj, direction)

    def _parse_statement(self):
        """<statement> (Protected)

        Parse the <statement> language structure.

            <statement> ::=
                <assignment_statement> |
                <if_statement> |
                <loop_statement> |
                <return_statement> |
                <procedure_call>
        """
        if self._accept('keyword', 'return'):
            # Go to the return label to exit the procedure/program
            self.generate_return(self.debug)
        elif self._first_if_statement():
            self._parse_if_statement()
        elif self._first_loop_statement():
            self._parse_loop_statement()
        elif self._first_procedure_call():
            self._parse_procedure_call()
        elif self._first_assignment_statement():
            self._parse_assignment_statement()
        else:
            self._syntax_error('statement')

        return

    def _first_assignment_statement(self):
        """first(<assignment_statement>) (Protected)

        Determines if current token matches the first terminals.

            first(<assignment_statement>) ::=
                <identifier>

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('identifier')

    def _parse_assignment_statement(self):
        """<assignment_statement> (Protected)

        Parses the <assignment_statement> language structure.

            <assignment_statement> ::=
                <destination> ':=' <expression>
        """
        id_name = self._current.value
        id_line = self._current.line

        dest_type = self._parse_destination()

        # Grab the last register used in case this variable is an array
        index_reg = self.get_reg(inc=False)

        # Check to make sure this is a valid identifier
        id_obj = self._ids.find(id_name)

        self._match('symbol', ':=')

        expr_type = self._parse_expression()

        # Get the register used for the last expression
        expr_reg = self.get_reg(inc=False)

        if dest_type != expr_type:
            self._type_error(dest_type, expr_type, id_line)

        # Determine the location of the identifier in the stack
        id_location = self._ids.get_id_location(id_name)

        # Verify the direction of the id if it is a param
        if id_location == 'param':
            direction = self._ids.get_param_direction(id_name)
            if direction != 'out':
                self._type_error('\'out\' param',
                                 '\'%s\' param' % direction, id_line)
                raise ParserTypeError()

        # Generate all code associated with retrieving this value
        self.generate_assignment(id_obj, id_location, index_reg, expr_reg,
                self.debug)

        return

    def _first_if_statement(self):
        """first(<if_statement>) (Protected)

        Determines if current token matches the first terminals.

            first(<if_statement>) ::=
                'if'

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('keyword', 'if')

    def _parse_if_statement(self):
        """<if_statement> (Protected)

        Parses the <if_statement> language structure.

            <if_statement> ::=
                'if' '(' <expression> ')' 'then' ( <statement> ';' )+
                [ 'else' ( <statement> ';' )+ ]
                'end' 'if'
        """
        self._match('keyword', 'if')
        self._match('symbol', '(')
        self._parse_expression()
        self._match('symbol', ')')
        self._match('keyword', 'then')

        label_id = self.get_label_id()
        expr_reg = self.get_reg(inc=False)

        self.generate('if (!R[%d]) goto else_%d;' % (expr_reg, label_id))
        self.tab_push()

        while True:
            try:
                self._parse_statement()
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

            if self._check('keyword', 'else') or self._check('keyword', 'end'):
                break

        self.generate('goto endif_%d;' % label_id)

        self.tab_pop()
        self.generate('else_%d:' % label_id)
        self.tab_push()

        if self._accept('keyword', 'else'):
            while True:
                try:
                    self._parse_statement()
                except ParserError:
                    self._resync_at_token('symbol', ';')

                self._match('symbol', ';')

                if self._check('keyword', 'end'):
                    break

        self._match('keyword', 'end')
        self._match('keyword', 'if')

        self.tab_pop()
        self.generate('endif_%d:' % label_id)

        return

    def _first_loop_statement(self):
        """first(<loop_statement>) (Protected)

        Determines if current token matches the first terminals.

            first(<loop_statement>) ::=
                'for'

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('keyword', 'for')

    def _parse_loop_statement(self):
        """<loop_statement> (Protected)

        Parses the <loop_statement> language structure.

            <loop_statement> ::=
                'for' '(' <assignment_statement> ';' <expression> ')'
                    ( <statement> ';' )*
                'end' 'for'
        """
        self._match('keyword', 'for')
        self._match('symbol', '(')

        label_id = self.get_label_id()
        self.generate('loop_%d:' % label_id)
        self.tab_push()

        try:
            self._parse_assignment_statement()
        except ParserError:
            self._resync_at_token('symbol', ';')

        self._match('symbol', ';')

        self._parse_expression()
        self._match('symbol', ')')

        expr_reg = self.get_reg(inc=False)
        self.generate('if (!R[%d]) goto endloop_%d;' % (expr_reg, label_id))

        while not self._accept('keyword', 'end'):
            try:
                self._parse_statement()
            except ParserError:
                self._resync_at_token('symbol', ';')

            self._match('symbol', ';')

        self._match('keyword', 'for')

        self.generate('goto loop_%d;' % label_id)
        self.tab_pop()
        self.generate('endloop_%d:' % label_id)

        return

    def _first_procedure_call(self):
        """first(<procedure_call>) (Protected)

        Determines if current token matches the first terminals. The second
        terminal is checked using the future token in this case to distinguish
        the first(<procedure_call>) from first(<assignment_statement>).

            first(<procedure_call>) ::=
                '('

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('symbol', '(', check_future=True)

    def _parse_procedure_call(self):
        """<procedure_call> (Protected)

        Parses the <procedure_call> language structure.

            <procedure_call> ::=
                <identifier> '(' [ <argument_list> ] ')'
        """
        # Match an identifier, check to make sure the identifier is procedure
        id_name = self._current.value
        id_line = self._current.line

        self._match('identifier')

        try:
            id_obj = self._ids.find(id_name)
        except ParserNameError as e:
            self._name_error('procedure has not been declared', id_name,
                             id_line)
            raise e

        if id_obj.type != 'procedure':
            self._type_error('procedure', id_obj.type, id_line)
            raise ParserTypeError()

        self._match('symbol', '(')

        out_names = []

        if not self._check('symbol', ')'):
            num_args, out_names = self._parse_argument_list(
                id_obj.params,
                out_names,
                index=0)

            # Make sure that too few arguments are not used
            if num_args < len(id_obj.params):
                self._runtime_error(
                    'procedure call accepts %d argument(s), %d given' %
                    (len(id_obj.params), num_args), id_line)

                raise ParserRuntimeError()

        self._match('symbol', ')')

        # Generate all procedure call code
        self.generate_procedure_call(id_obj.name, id_obj.mm_ptr, self.debug)

        # Pop parameters off the stack
        for index, param in enumerate(id_obj.params):
            out_name = out_names[index]

            self.generate_param_pop(param.id.name, self.debug)

            # If this is an outbound parameter, we must write it to its
            # memory location
            if param.direction == 'out':
                # Get the identifier object of the destination
                out_id = self._ids.find(out_name)

                # Determine where on the stack this identifier exists
                out_location = self._ids.get_id_location(out_name)

                # Store the parameter in the appropriate location
                self.generate_param_store(out_id, out_location, self.debug)

        # Finish the procedure call
        self.generate_procedure_call_end(self.debug)

        return

    def _parse_argument_list(self, params, out_names, index=0):
        """<argument_list> (Protected)

        Parses <argument_list> language structure.

            <argument_list> ::=
                <expression> ',' <argument_list> |
                <expression>

        Arguments:
            params: A list of Parameter namedtuple objects allowed in the
                procedure call.
            out_names: A list of identifier names that are being used in this
                procedure call and must be written back.
            index: The index in params with which to match the found param.
                (Default: 0)

        Returns:
            A tuple (index, out_names) consisting of the number of arguments
            encountered and a list of the identifiers used to write back.
        """
        arg_line = self._current.line
        arg_type = None

        # Make sure that too many arguments are not used
        if index > len(params) - 1:
            self._runtime_error('procedure call accepts only %d argument(s)' %
                                len(params), arg_line)
            raise ParserRuntimeError()

        # Get the parameter information for this position in the arg list
        param = params[index]

        if param.direction == 'out':
            # We may only parse a single identifier if the direction is 'out'
            arg_name = self._current.value
            arg_type = self._parse_name()

            out_names.append(arg_name)
        elif param.direction == 'in':
            # This is a 'in' parameter with only one element (not array)
            arg_type = self._parse_expression()

            out_names.append(None)

        # Get the last reg assignment in the expr. This is argument's register
        expr_reg = self.get_reg(inc=False)

        if arg_type != param.id.type:
            self._type_error(param.id.type, arg_type, arg_line)

        index += 1

        if self._accept('symbol', ','):
            index, out_names = self._parse_argument_list(
                params,
                out_names,
                index=index)

        # Push the parameters onto the stack in reverse order. The last param
        # will reach this point first
        self.generate_param_push(expr_reg, self.debug)

        return index, out_names

    def _parse_destination(self):
        """<destination> (Protected)

        Parses the <destination> language structure.

            <destination> ::=
                <identifier> [ '[' <expression> ']' ]

        Returns:
            Type of the destination identifier as a string.
        """
        id_name = self._current.value
        id_line = self._current.line

        self._match('identifier')

        # Make sure that identifier is valid for the scope
        try:
            id_obj = self._ids.find(id_name)
        except ParserNameError as e:
            self._name_error('not declared in this scope', id_name, id_line)
            raise e

        # Check type to make sure it's a variable
        if not id_obj.type in ['integer', 'float', 'bool', 'string']:
            self._type_error('variable', id_obj.type, id_line)
            raise ParserTypeError()

        id_type = id_obj.type

        if self._accept('symbol', '['):
            expr_line = self._current.line
            expr_type = self._parse_expression()

            if expr_type != 'integer':
                self._type_error('integer', expr_type, expr_line)

            self._accept('symbol', ']')
        elif id_obj.size is not None:
            self._runtime_error('%s: array requires index' % id_name, id_line)

        return id_type

    def _parse_expression(self):
        """<expression> (Protected)

        Parses <expression> language structure.

            <expression> ::=
                <expression> '&' <arith_op> |
                <expression> '|' <arith_op> |
                [ 'not' ] <arith_op>

        Returns:
            The type value of the expression.
        """
        self.comment('Parsing expression', self.debug)

        negate = False

        if self._accept('keyword', 'not'):
            negate = True

        line = self._current.line
        id_type = self._parse_arith_op()

        if negate and id_type not in ['integer', 'bool']:
            self._type_error('integer or bool', id_type, line)
            raise ParserTypeError()

        while True:
            operand1 = self.get_reg(inc=False)

            if self._accept('symbol', '&'):
                operation = '&'
            elif self._accept('symbol', '|'):
                operation = '|'
            else:
                break

            if id_type not in ['integer', 'bool']:
                self._type_error('integer or bool', id_type, line)
                raise ParserTypeError()

            next_type = self._parse_arith_op()

            operand2 = self.get_reg(inc=False)

            if next_type not in ['integer', 'bool']:
                self._type_error('integer or bool', next_type, line)
                raise ParserTypeError()

            result = self.generate_operation(operand1, id_type, operand2,
                                             next_type, operation)

            if negate:
                self.generate('R[%d] = ~R[%d];' % (result, result))

        return id_type

    def _parse_arith_op(self):
        """<arith_op> (Protected)

        Parses <arith_op> language structure.

            <arith_op> ::=
                <arith_op> '+' <relation> |
                <arith_op> '-' <relation> |
                <relation>

        Returns:
            The type value of the expression.
        """
        line = self._current.line
        id_type = self._parse_relation()

        while True:
            operand1 = self.get_reg(inc=False)

            if self._accept('symbol', '+'):
                operation = '+'
            elif self._accept('symbol', '-'):
                operation = '-'
            else:
                break

            if id_type not in ['integer', 'float']:
                self._type_error('integer or float', id_type, line)
                raise ParserTypeError()

            next_type = self._parse_relation()

            operand2 = self.get_reg(inc=False)
            
            if next_type not in ['integer', 'float']:
                self._type_error('integer or float', next_type, line)
                raise ParserTypeError()

            self.generate_operation(operand1, id_type, operand2, next_type,
                                    operation)

        return id_type

    def _parse_relation(self):
        """<relation> (Protected)

        Parses <relation> language structure.

            <relation> ::=
                <relation> '<' <term> |
                <relation> '>' <term> |
                <relation> '>=' <term> |
                <relation> '<=' <term> |
                <relation> '==' <term> |
                <relation> '!=' <term> |
                <term>

        Returns:
            The type value of the expression.
        """
        line = self._current.line
        id_type = self._parse_term()

        # Check for relational operators. Note that relational operators
        # are only valid for integer or boolean tokens
        while True:
            operand1 = self.get_reg(inc=False)

            if self._accept('symbol', '<'):
                operation = '<'
            elif self._accept('symbol', '>'):
                operation = '>'
            elif self._accept('symbol', '<='):
                operation = '<='
            elif self._accept('symbol', '>='):
                operation = '>='
            elif self._accept('symbol', '=='):
                operation = '=='
            elif self._accept('symbol', '!='):
                operation = '!='
            else:
                break

            if id_type not in ['integer', 'bool']:
                self._type_error('integer or bool', id_type, line)
                raise ParserTypeError()

            next_type = self._parse_term()

            operand2 = self.get_reg(inc=False)

            if next_type not in ['integer', 'bool']:
                self._type_error('integer or bool', next_type, line)
                raise ParserTypeError()

            self.generate_operation(operand1, id_type, operand2, next_type,
                                    operation)

        return id_type

    def _parse_term(self):
        """<term> (Protected)

        Parses <term> language structure.

            <term> ::=
                <term> '*' <factor> |
                <term> '/' <factor> |
                <factor>

        Returns:
            The type value of the expression.
        """
        line = self._current.line
        id_type = self._parse_factor()

        # Check for multiplication or division operators. Note that these
        # operators are only valid for integer or float values
        while True:
            operand1 = self.get_reg(inc=False)

            if self._accept('symbol', '*'):
                operation = '*'
            elif self._accept('symbol', '/'):
                operation = '/'
            else:
                break

            if id_type not in ['integer', 'float']:
                self._type_error('integer or float', id_type, line)
                raise ParserTypeError()

            line = self._current.line
            next_type = self._parse_factor()

            operand2 = self.get_reg(inc=False)

            if next_type not in ['integer', 'float']:
                self._type_error('integer or float', next_type, line)
                raise ParserTypeError()

            self.generate_operation(operand1, id_type, operand2, next_type,
                                    operation)

        return id_type

    def _parse_factor(self):
        """<factor> (Protected)

        Parses <factor> language structure.

            <factor> ::=
                '(' <expression> ')' |
                [ '-' ] <name> |
                [ '-' ] <number> |
                <string> |
                'true' |
                'false'

        Returns:
            The type value of the expression.
        """
        id_type = None

        if self._accept('symbol', '('):
            id_type = self._parse_expression()
            self._match('symbol', ')')
        elif self._accept('string'):
            id_type = 'string'
            str_val = self._previous.value

            self.generate('R[%d] = (int)"%s";' % (self.get_reg(), str_val))
        elif self._accept('keyword', 'true'):
            id_type = 'bool'

            self.generate('R[%d] = 1;' % (self.get_reg()))
        elif self._accept('keyword', 'false'):
            id_type = 'bool'

            self.generate('R[%d] = 0;' % (self.get_reg()))
        elif self._accept('symbol', '-'):
            if self._first_name():
                id_type = self._parse_name()
            elif self._check('integer') or self._check('float'):
                id_type = self._parse_number(negate=True)
            else:
                self._syntax_error('variable name, integer, or float')
        elif self._first_name():
            id_type = self._parse_name()
        elif self._check('integer') or self._check('float'):
            id_type = self._parse_number(negate=False)
        else:
            self._syntax_error('factor')

        return id_type

    def _first_name(self):
        """first(<name>) (Protected)

        Determines if current token matches the first terminals.

            first(<name>) ::=
                <identifier>

        Returns:
            True if current token matches a first terminal, False otherwise.
        """
        return self._check('identifier')

    def _parse_name(self):
        """<name> (Protected)

        Parses <name> language structure.

            <name> ::=
                <identifier> [ '[' <expression> ']' ]
        """
        id_name = self._current.value
        id_line = self._current.line

        self._match('identifier')

        # Make sure that identifier is valid for the scope
        try:
            id_obj = self._ids.find(id_name)
            id_type = id_obj.type
        except ParserNameError as e:
            self._name_error('not declared in this scope', id_name, id_line)
            raise e

        # Check type to make sure it's a variable
        if not id_type in ['integer', 'float', 'bool', 'string']:
            self._type_error('variable', id_type, id_line)
            raise ParserTypeError()

        if self._accept('symbol', '['):
            index_type = self._parse_expression()

            if not index_type == 'integer':
                self._type_error('integer', index_type, id_line)
                raise ParserTypeError()

            self._match('symbol', ']')
        elif id_obj.size is not None:
            self._runtime_error('%s: array requires index' % id_name, id_line)

        # Get the last register allocated. The index will be here if it's used
        index_reg = self.get_reg(inc=False)

        # Determine the location of the identifier in the stack
        id_location = self._ids.get_id_location(id_name)

        # Verify the direction of the id if it is a param
        if id_location == 'param':
            direction = self._ids.get_param_direction(id_name)
            if direction != 'in':
                self._type_error('\'in\' param',
                                 '\'%s\' param' % direction, id_line)
                raise ParserTypeError()

        # Generate all code associated with retrieving this value
        self.generate_name(id_obj, id_location, index_reg, self.debug)

        return id_type

    def _parse_number(self, negate=False, generate_code=True):
        """Parse Number (Protected)

        Parses the <number> language structure.

            <number> ::=
                [0-9][0-9_]*[.[0-9_]*]

        Arguments:
            negate: Determines if the number should be negated or not.
            generate_code: Determines if code should be generated for the
                parsed number or not.

        Returns:
            The type of the parsed number.
        """
        number = self._current.value
        id_type = self._current.type

        # Parse the number (either float or integer type)
        if not self._accept('integer') and not self._accept('float'):
            self._syntax_error('number')

        # Generate the code for this number if desired
        if generate_code:
            self.generate_number(number, id_type, negate)

        return id_type

########NEW FILE########
__FILENAME__ = scanner
#!/usr/bin/env python3

"""Scanner module

With any attached file, the Scanner class will scan the file token-by-token
until an end-of-file is encountered.

Author: Evan Sneath
License: Open Software License v3.0

Classes:
    Scanner: An implementation of a scanner for the source language.
"""

from os.path import isfile

from lib.datatypes import Token


class Scanner:
    """Scanner class

    This class implements a scanner object to scan a source code file in the
    compilation process. This class is designed to be inherited to be used
    during the parsing stage of the compiler.

    Attributes:
        keywords: A list of valid keywords in the language.
        symbols: A list of valid symbols in the language.

    Methods:
        attach_source: Binds a source file to the scanner to begin scanning.
        next_token: Returns the next token of the attached file. This token
            will be of the Token named tuple class.
    """
    # Define all language keywords
    keywords = [
        'string', 'integer', 'bool', 'float', 'global', 'is', 'in', 'out',
        'if', 'then', 'else', 'for', 'and', 'or', 'not', 'program',
        'procedure', 'begin', 'return', 'end', 'true', 'false',
    ]

    # Define all language symbols
    symbols = [
        ':', ';', ',', '+', '-', '*', '/', '(', ')', '<', '<=', '>', '>=',
        '!', '!=', '=', '==', ':=', '[', ']', '&', '|',
    ]

    def __init__(self):
        super().__init__()

        # Holds the file path of the attached source file
        self._src_path = ''

        # Holds all source file data (code) to be scanned
        self._src = ''

        # Holds the location of the next character to scan in the source file
        self._line_pos = 0
        self._char_pos = 0

        return

    def attach_source(self, src_path):
        """Attach Source 

        Attach a source file to the scanner and prepare for token collection.

        Arguments:
            src_path: The path to the source file to scan.

        Returns:
            True on success, False otherwise.
        """
        # Make sure the inputted file is a actual file
        if not isfile(src_path):
            print('Error: "%s"' % src_path)
            print('    Inputted path is not a file')
            return False

        # Try to read all data from the file and split by line
        try:
            with open(src_path) as f:
                keepends = True
                self._src = f.read().splitlines(keepends)
        except IOError:
            print('Error: "%s"' % src_path)
            print('    Could not read inputted file')
            return False

        # The file was attached and read successfully, store the path
        self._src_path = src_path

        return True

    def next_token(self):
        """Scan For Next Token

        Scans the source code for the next token. The next token is then
        returned for parsing.

        Returns:
            The next token object in the source code.
        """
        # Get the first character, narrow down the data type possibilities
        char = self._next_word()

        if char is None:
            return Token('eof', None, self._line_pos)

        # Use the first character to choose the token type to expect
        if char == '"':
            value, token_type = self._expect_string()
        elif char.isdigit():
            value, token_type = self._expect_number(char)
        elif char.isalpha():
            value, token_type = self._expect_identifier(char)
        elif char in self.symbols:
            value, token_type = self._expect_symbol(char)
        else:
            # We've run across a character that shouldn't be here
            msg = 'Invalid character \'%s\' encountered' % char
            self._scan_warning(msg, hl=self._char_pos-1)

            # Run this function again until we find something good
            return self.next_token()

        if token_type == 'comment':
            # If we find a comment, get a token on the next line
            self._next_line()
            return self.next_token()

        # Build the new token object
        new_token = Token(token_type, value, self._line_pos+1)

        return new_token

    def _get_line(self, line_number):
        """Get Line (Protected)

        Returns a line stripped of leading and trailing whitespace given a
        line number.

        Arguments:
            line_number: The line number of the attached source file to print.

        Returns:
            The requested line number from the source, None on invalid line.
        """
        if 0 < line_number <= len(self._src):
            return self._src[line_number-1].strip()

    def _scan_warning(self, msg, hl=-1):
        """Print Scanner Warning Message (Protected)

        Prints a formatted warning message.

        Arguments:
            msg: The warning message to display
            hl: If not -1, there will be an pointer (^) under a
                character in the line to be highlighted. (Default: -1)
        """
        line = self._src[self._line_pos][0:-1]

        print('Warning: "', self._src_path, '", ', sep='', end='')
        print('line ', self._line_pos+1, sep='')
        print('    ', msg, '\n    ', line.strip(), sep='')

        if hl != -1:
            left_spaces = line.find(line.strip()[0])
            print('    %s^' % (' '*(abs(hl)-left_spaces)))

        return

    def _next_word(self):
        """Get Next Word Character (Protected)

        Move the cursor to the start of the next non-space character in the
        file.

        Returns:
            The first non-space character encountered. None if the end of
            file was reached.
        """
        char = ''

        while True:
            char = self._src[self._line_pos][self._char_pos]

            # React according to spaces and newlines
            if char == '\n':
                if not self._next_line():
                    return None
            elif char in ' \t':
                self._char_pos += 1
            else:
                break

        # Increment to the next character
        self._char_pos += 1
        return char

    def _next_line(self):
        """Travel to Next Line (Protected)

        Move the cursor to the start of the next line safely.

        Returns:
            True on success, False if end of file is encountered
        """
        self._line_pos += 1
        self._char_pos = 0

        # Check to make sure this isn't the end of file
        if self._line_pos == len(self._src):
            return False

        return True

    def _next_char(self, peek=False):
        """Get Next Character (Protected)

        Move the cursor to the next character in the file.

        Arguments:
            peek: If True, the character position pointer will not be
                incremented. Set by default to False.

        Returns:
            The next character encountered. None if the end of line
            was reached.
        """
        # Get the next pointed character
        char = self._src[self._line_pos][self._char_pos]

        # Return None if we hit a line ending
        if char == '\n':
            return None

        # Increment to the next character
        if not peek:
            self._char_pos += 1

        return char

    def _expect_string(self):
        """Expect String Token (Protected)

        Parses the following characters in hope of a valid string. If an
        invalid string is encountered, all attempts are made to make it valid.

        Returns:
            (value, token_type) - A tuple describing the final parsed token.
            The resulting token type will be 'string'.
        """
        hanging_quote = False

        # We know this is a string. Find the next quotation and return it
        string_end = self._src[self._line_pos].find('"', self._char_pos)

        # If we have a hanging quotation, assume quote ends at end of line
        if string_end == -1:
            hanging_quote = True
            string_end = len(self._src[self._line_pos]) - 1
            self._scan_warning('No closing quotation in string', hl=string_end)

        value = self._src[self._line_pos][self._char_pos:string_end]

        # Check for illegal characters, send a warning if encountered
        for i, char in enumerate(value):
            if not char.isalnum() and char not in ' _,;:.\'':
                value = value.replace(char, ' ', 1)
                msg = 'Invalid character \'%s\' in string' % char
                self._scan_warning(msg, hl=self._char_pos+i)

        self._char_pos += len(value)
        if not hanging_quote:
            self._char_pos += 1

        return value, 'string'

    def _expect_number(self, char):
        """Expect Number Token (Protected)

        Parses the following characters in hope of a valid integer or float.

        Arguments:
            char: The first character already picked for the value.

        Returns:
            (value, token_type) - A tuple describing the final parsed token.
            The resulting token type will either be 'int' indicating a valid
            integer or 'float' indicating a valid floating point value.
        """
        value = '' + char
        token_type = 'integer'

        is_float = False

        while True:
            char = self._next_char(peek=True)

            if char is None:
                break
            elif char == '.' and not is_float:
                # We found a decimal point. Move to float mode
                is_float = True
                token_type = 'float'
            elif not char.isdigit() and char != '_':
                break

            value += char
            self._char_pos += 1

        # Remove all underscores in the int/float. These serve no purpose
        value = value.replace('_', '')

        # If nothing was given after the decimal point assume 0
        if is_float and value.split('.')[-1] == '':
            value += '0'

        return value, token_type

    def _expect_identifier(self, char):
        """Expect Identifier Token (Protected)

        Parses the following characters in hope of a valid identifier.

        Arguments:
            char: The first character already picked for the value.

        Returns:
            (value, token_type) - A tuple describing the final parsed token.
            The resulting token type will either be 'identifier' indicating a
            valid identifier or 'keyword' indicating a valid keyword.
        """
        value = '' + char
        token_type = 'identifier'

        while True:
            char = self._next_char(peek=True)

            if char is None:
                break
            elif not char.isalnum() and char != '_':
                break

            value += char
            self._char_pos += 1

        if value in self.keywords:
            token_type = 'keyword'

        return value, token_type

    def _expect_symbol(self, char):
        """Expect Symbol Token (Protected)

        Parses the following characters in hope of a valid symbol.

        Arguments:
            char: The first character already picked for the value.

        Returns:
            (value, token_type) - A tuple describing the final parsed token.
            The resulting token type will either be 'symbol' indicating a
            valid identifier or 'comment' indicating a comment until line end.
        """
        value = '' + char

        while True:
            char = self._next_char(peek=True)

            if char is None:
                break
            elif value + str(char) == '//':
                return None, 'comment'
            elif value + str(char) not in self.symbols:
                break

            value += char
            self._char_pos += 1

        return value, 'symbol'

########NEW FILE########
