__FILENAME__ = FBDebugCommands
#!/usr/bin/python

import lldb
import fblldbbase as fb
import fblldbobjcruntimehelpers as objc

import re

def lldbcommands():
  return [
    FBWatchInstanceVariableCommand(),
    FBMethodBreakpointCommand(),
  ]

class FBWatchInstanceVariableCommand(fb.FBCommand):
  def name(self):
    return 'wivar'

  def description(self):
    return "Set a watchpoint for an object's instance variable."

  def args(self):
    return [
      fb.FBCommandArgument(arg='object', type='id', help='Object expression to be evaluated.'),
      fb.FBCommandArgument(arg='ivarName', help='Name of the instance variable to watch.')
    ]

  def run(self, arguments, options):
    commandForObject, ivarName = arguments

    objectAddress = int(fb.evaluateObjectExpression(commandForObject), 0)

    ivarOffsetCommand = '(ptrdiff_t)ivar_getOffset((Ivar)object_getInstanceVariable((id){}, "{}", 0))'.format(objectAddress, ivarName)
    ivarOffset = fb.evaluateIntegerExpression(ivarOffsetCommand)

    # A multi-statement command allows for variables scoped to the command, not permanent in the session like $variables.
    ivarSizeCommand = ('unsigned int size = 0;'
                       'char *typeEncoding = (char *)ivar_getTypeEncoding((Ivar)class_getInstanceVariable((Class)object_getClass((id){}), "{}"));'
                       '(char *)NSGetSizeAndAlignment(typeEncoding, &size, 0);'
                       'size').format(objectAddress, ivarName)
    ivarSize = int(fb.evaluateExpression(ivarSizeCommand), 0)

    error = lldb.SBError()
    watchpoint = lldb.debugger.GetSelectedTarget().WatchAddress(objectAddress + ivarOffset, ivarSize, False, True, error)

    if error.Success():
      print 'Remember to delete the watchpoint using: watchpoint delete {}'.format(watchpoint.GetID())
    else:
      print 'Could not create the watchpoint: {}'.format(error.GetCString())

class FBMethodBreakpointCommand(fb.FBCommand):
  def name(self):
    return 'bmessage'

  def description(self):
    return "Set a breakpoint for a selector on a class, even if the class itself doesn't override that selector. It walks the hierarchy until it finds a class that does implement the selector and sets a conditional breakpoint there."

  def args(self):
    return [
      fb.FBCommandArgument(arg='expression', type='string', help='Expression to set a breakpoint on, e.g. "-[MyView setFrame:]", "+[MyView awesomeClassMethod]" or "-[0xabcd1234 setFrame:]"'),
    ]

  def run(self, arguments, options):
    expression = arguments[0]

    match = re.match(r'([-+])*\[(.*) (.*)\]', expression)

    if not match:
      print 'Failed to parse expression. Do you even Objective-C?!'
      return

    expressionForSelf = objc.functionPreambleExpressionForSelf()
    if not expressionForSelf:
      print 'Your architecture, {}, is truly fantastic. However, I don\'t currently support it.'.format(arch)
      return

    methodTypeCharacter = match.group(1)
    classNameOrExpression = match.group(2)
    selector = match.group(3)

    methodIsClassMethod = (methodTypeCharacter == '+')

    if not methodIsClassMethod:
      # The default is instance method, and methodTypeCharacter may not actually be '-'.
      methodTypeCharacter = '-'

    targetIsClass = False
    targetObject = fb.evaluateObjectExpression('({})'.format(classNameOrExpression), False)

    if not targetObject:
      # If the expression didn't yield anything then it's likely a class. Assume it is.
      # We will check again that the class does actually exist anyway.
      targetIsClass = True
      targetObject = fb.evaluateObjectExpression('[{} class]'.format(classNameOrExpression), False)

    targetClass = fb.evaluateObjectExpression('[{} class]'.format(targetObject), False)

    if not targetClass or int(targetClass, 0) == 0:
      print 'Couldn\'t find a class from the expression "{}". Did you typo?'.format(classNameOrExpression)
      return

    if methodIsClassMethod:
      targetClass = objc.object_getClass(targetClass)

    found = False
    nextClass = targetClass

    while not found and int(nextClass, 0) > 0:
      if classItselfImplementsSelector(nextClass, selector):
        found = True
      else:
        nextClass = objc.class_getSuperclass(nextClass)

    if not found:
      print 'There doesn\'t seem to be an implementation of {} in the class hierarchy. Made a boo boo with the selector name?'.format(selector)
      return

    breakpointClassName = objc.class_getName(nextClass)
    breakpointFullName = '{}[{} {}]'.format(methodTypeCharacter, breakpointClassName, selector)

    breakpointCondition = None
    if targetIsClass:
      breakpointCondition = '(void*)object_getClass({}) == {}'.format(expressionForSelf, targetClass)
    else:
      breakpointCondition = '(void*){} == {}'.format(expressionForSelf, targetObject)

    print 'Setting a breakpoint at {} with condition {}'.format(breakpointFullName, breakpointCondition)

    lldb.debugger.HandleCommand('breakpoint set --fullname "{}" --condition "{}"'.format(breakpointFullName, breakpointCondition))

def classItselfImplementsSelector(klass, selector):
  thisMethod = objc.class_getInstanceMethod(klass, selector)
  if thisMethod == 0:
    return False

  superklass = objc.class_getSuperclass(klass)
  superMethod = objc.class_getInstanceMethod(superklass, selector)
  if thisMethod == superMethod:
    return False
  else:
    return True

########NEW FILE########
__FILENAME__ = FBDisplayCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb
import os
import time

import fblldbviewhelpers as viewHelpers
import fblldbbase as fb

def lldbcommands():
  return [
    FBCoreAnimationFlushCommand(),
    FBDrawBorderCommand(),
    FBRemoveBorderCommand(),
    FBMaskViewCommand(),
    FBUnmaskViewCommand(),
    FBShowViewCommand(),
    FBHideViewCommand(),
  ]


class FBDrawBorderCommand(fb.FBCommand):
  def name(self):
    return 'border'

  def description(self):
    return 'Draws a border around <viewOrLayer>. Color and width can be optionally provided.'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to border.') ]

  def options(self):
    return [
      fb.FBCommandArgument(short='-c', long='--color', arg='color', type='string', default='red', help='A color name such as \'red\', \'green\', \'magenta\', etc.'),
      fb.FBCommandArgument(short='-w', long='--width', arg='width', type='CGFloat', default=2.0, help='Desired width of border.')
    ]

  def run(self, args, options):
    layer = viewHelpers.convertToLayer(args[0])
    lldb.debugger.HandleCommand('expr (void)[%s setBorderWidth:(CGFloat)%s]' % (layer, options.width))
    lldb.debugger.HandleCommand('expr (void)[%s setBorderColor:(CGColorRef)[(id)[UIColor %sColor] CGColor]]' % (layer, options.color))
    lldb.debugger.HandleCommand('caflush')


class FBRemoveBorderCommand(fb.FBCommand):
  def name(self):
    return 'unborder'

  def description(self):
    return 'Removes border around <viewOrLayer>.'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to unborder.') ]

  def run(self, args, options):
    layer = viewHelpers.convertToLayer(args[0])
    lldb.debugger.HandleCommand('expr (void)[%s setBorderWidth:(CGFloat)%s]' % (layer, 0))
    lldb.debugger.HandleCommand('caflush')


class FBMaskViewCommand(fb.FBCommand):
  def name(self):
    return 'mask'

  def description(self):
    return 'Add a transparent rectangle to the window to reveal a possibly obscured or hidden view or layer\'s bounds'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to mask.') ]

  def options(self):
    return [
      fb.FBCommandArgument(short='-c', long='--color', arg='color', type='string', default='red', help='A color name such as \'red\', \'green\', \'magenta\', etc.'),
      fb.FBCommandArgument(short='-a', long='--alpha', arg='alpha', type='CGFloat', default=0.5, help='Desired alpha of mask.')
    ]

  def run(self, args, options):
    viewOrLayer = fb.evaluateObjectExpression(args[0])
    viewHelpers.maskView(viewOrLayer, options.color, options.alpha)


class FBUnmaskViewCommand(fb.FBCommand):
  def name(self):
    return 'unmask'

  def description(self):
    return 'Remove mask from a view or layer'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to mask.') ]

  def run(self, args, options):
    viewOrLayer = fb.evaluateObjectExpression(args[0])
    viewHelpers.unmaskView(viewOrLayer)


class FBCoreAnimationFlushCommand(fb.FBCommand):
  def name(self):
    return 'caflush'

  def description(self):
    return 'Force Core Animation to flush. This will \'repaint\' the UI but also may mess with ongoing animations.'

  def run(self, arguments, options):
    viewHelpers.flushCoreAnimationTransaction()


class FBShowViewCommand(fb.FBCommand):
  def name(self):
    return 'show'

  def description(self):
    return 'Show a view or layer.'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to show.') ]

  def run(self, args, options):
    viewHelpers.setViewHidden(args[0], False)


class FBHideViewCommand(fb.FBCommand):
  def name(self):
    return 'hide'

  def description(self):
    return 'Hide a view or layer.'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView/CALayer *', help='The view/layer to hide.') ]

  def run(self, args, options):
    viewHelpers.setViewHidden(args[0], True)

########NEW FILE########
__FILENAME__ = FBFindCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import os
import re

import lldb
import fblldbbase as fb
import fblldbviewcontrollerhelpers as vcHelpers
import fblldbobjcruntimehelpers as objc

def lldbcommands():
  return [
    FBFindViewControllerCommand(),
    FBFindViewCommand(),
    FBFindViewByAccessibilityLabelCommand(),
    FBTapLoggerCommand(),
  ]

class FBFindViewControllerCommand(fb.FBCommand):
  def name(self):
    return 'fvc'

  def description(self):
    return 'Find the view controllers whose class names match classNameRegex and puts the address of first on the clipboard.'

  def options(self):
    return [
      fb.FBCommandArgument(short='-n', long='--name', arg='classNameRegex', type='string', help='The view-controller-class regex to search the view controller hierarchy for.'),
      fb.FBCommandArgument(short='-v', long='--view', arg='view', type='UIView', help='This function will print the View Controller that owns this view.')
    ]

  def run(self, arguments, options):
    if options.classNameRegex and options.view:
      print("Do not set both the --name and --view flags")
    elif options.view:
      self.findOwningViewController(options.view)
    else:
      output = vcHelpers.viewControllerRecursiveDescription('(id)[[[UIApplication sharedApplication] keyWindow] rootViewController]')
      searchString = options.classNameRegex if options.classNameRegex else arguments[0]
      printMatchesInViewOutputStringAndCopyFirstToClipboard(searchString, output)

  def findOwningViewController(self, object):
    while object:
      if self.isViewController(object):
        description = fb.evaluateExpressionValue(object).GetObjectDescription()
        print("Found the owning view controller.\n{}".format(description))
        cmd = 'echo {} | tr -d "\n" | pbcopy'.format(object)
        os.system(cmd)
        return
      else:
        object = self.nextResponder(object)
    print("Could not find an owning view controller")

  @staticmethod
  def isViewController(object):
    command = '[(id){} isKindOfClass:[UIViewController class]]'.format(object)
    isVC = fb.evaluateBooleanExpression(command)
    return isVC

  @staticmethod
  def nextResponder(object):
    command = '[((id){}) nextResponder]'.format(object)
    nextResponder = fb.evaluateObjectExpression(command)
    try:
      if int(nextResponder, 0):
        return nextResponder
      else:
        return None
    except:
      return None


class FBFindViewCommand(fb.FBCommand):
  def name(self):
    return 'fv'

  def description(self):
      return 'Find the views whose class names match classNameRegex and puts the address of first on the clipboard.'

  def args(self):
    return [ fb.FBCommandArgument(arg='classNameRegex', type='string', help='The view-class regex to search the view hierarchy for.') ]

  def run(self, arguments, options):
    output = fb.evaluateExpressionValue('(id)[[[UIApplication sharedApplication] keyWindow] recursiveDescription]').GetObjectDescription()
    printMatchesInViewOutputStringAndCopyFirstToClipboard(arguments[0], output)


def printMatchesInViewOutputStringAndCopyFirstToClipboard(needle, haystack):
  first = None
  for match in re.finditer('.*<.*(' + needle + ').*: (0x[0-9a-fA-F]*);.*', haystack, re.IGNORECASE):
    view = match.groups()[-1]
    className = fb.evaluateExpressionValue('(id)[(' + view + ') class]').GetObjectDescription()
    print('{} {}'.format(view, className))
    if first == None:
      first = view
      cmd = 'echo %s | tr -d "\n" | pbcopy' % view
      os.system(cmd)


class FBFindViewByAccessibilityLabelCommand(fb.FBCommand):
  def name(self):
    return 'fa11y'

  def description(self):
      return 'Find the views whose accessibility labels match labelRegex and puts the address of the first result on the clipboard.'

  def args(self):
    return [ fb.FBCommandArgument(arg='labelRegex', type='string', help='The accessibility label regex to search the view hierarchy for.') ]

  def run(self, arguments, options):
    first = None
    haystack = fb.evaluateExpressionValue('(id)[[[UIApplication sharedApplication] keyWindow] recursiveDescription]').GetObjectDescription()
    needle = arguments[0]

    allViews = re.findall('.* (0x[0-9a-fA-F]*);.*', haystack)
    for view in allViews:
      a11yLabel = fb.evaluateExpressionValue('(id)[(' + view + ') accessibilityLabel]').GetObjectDescription()
      if re.match(r'.*' + needle + '.*', a11yLabel, re.IGNORECASE):
        print('{} {}'.format(view, a11yLabel))

        if first == None:
          first = view
          cmd = 'echo %s | tr -d "\n" | pbcopy' % first
          os.system(cmd)


class FBTapLoggerCommand(fb.FBCommand):
  def name(self):
    return 'taplog'

  def description(self):
    return 'Log tapped view to the console.'

  def run(self, arguments, options):
    parameterExpr = objc.functionPreambleExpressionForObjectParameterAtIndex(0)
    breakpoint = lldb.debugger.GetSelectedTarget().BreakpointCreateByName("-[UIApplication sendEvent:]")
    breakpoint.SetCondition('(int)[' + parameterExpr + ' type] == 0 && (int)[[[' + parameterExpr + ' allTouches] anyObject] phase] == 0')
    breakpoint.SetOneShot(True)
    lldb.debugger.HandleCommand('breakpoint command add -s python -F "sys.modules[\'' + __name__ + '\'].' + self.__class__.__name__ + '.taplog_callback" ' + str(breakpoint.id))
    lldb.debugger.SetAsync(True)
    lldb.debugger.HandleCommand('continue')

  @staticmethod
  def taplog_callback(frame, bp_loc, internal_dict):
    parameterExpr = objc.functionPreambleExpressionForObjectParameterAtIndex(0)
    lldb.debugger.HandleCommand('po [[[%s allTouches] anyObject] view]' % (parameterExpr))
    # We don't want to proceed event (click on button for example), so we just skip it
    lldb.debugger.HandleCommand('thread return')

########NEW FILE########
__FILENAME__ = FBFlickerCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import os
import time

import lldb
import fblldbbase as fb
import fblldbviewhelpers as viewHelpers
import fblldbinputhelpers as inputHelpers

def lldbcommands():
  return [
    FBFlickerViewCommand(),
    FBViewSearchCommand(),
  ]


class FBFlickerViewCommand(fb.FBCommand):
  def name(self):
    return 'flicker'

  def description(self):
    return 'Quickly show and hide a view to quickly help visualize where it is.'

  def args(self):
    return [ fb.FBCommandArgument(arg='viewOrLayer', type='UIView*', help='The view to border.') ]

  def run(self, arguments, options):
    object = fb.evaluateObjectExpression(arguments[0])

    isHidden = fb.evaluateBooleanExpression('[' + object + ' isHidden]')
    shouldHide = not isHidden
    for x in range(0, 2):
      viewHelpers.setViewHidden(object, shouldHide)
      viewHelpers.setViewHidden(object, isHidden)


class FBViewSearchCommand(fb.FBCommand):
  def name(self):
    return 'vs'

  def description(self):
    return 'Interactively search for a view by walking the hierarchy.'

  def args(self):
    return [ fb.FBCommandArgument(arg='view', type='UIView*', help='The view to border.') ]

  def run(self, arguments, options):
    print '\nUse the following and (q) to quit.\n(w) move to superview\n(s) move to first subview\n(a) move to previous sibling\n(d) move to next sibling\n(p) print the hierarchy\n'

    object = fb.evaluateObjectExpression(arguments[0])
    walker = FlickerWalker(object)
    walker.run()

class FlickerWalker:
  def __init__(self, startView):
    self.setCurrentView(startView)

    self.handler = inputHelpers.FBInputHandler(lldb.debugger, self.inputCallback)
    self.handler.start()

  def run(self):
    while self.handler.isValid():
      self.flicker()

  def flicker(self):
    viewHelpers.setViewHidden(self.currentView, True)
    time.sleep(0.1)
    viewHelpers.setViewHidden(self.currentView, False)
    time.sleep(0.3)

  def inputCallback(self, input):
    oldView = self.currentView

    if input == 'q':
      cmd = 'echo %s | tr -d "\n" | pbcopy' % oldView
      os.system(cmd)

      print '\nI hope ' + oldView + ' was what you were looking for. I put it on your clipboard.'

      self.handler.stop()
    elif input == 'w':
      v = superviewOfView(self.currentView)
      if not v:
        print 'There is no superview. Where are you trying to go?!'
      self.setCurrentView(v)
    elif input == 's':
      v = firstSubviewOfView(self.currentView)
      if not v:
        print '\nThe view has no subviews.\n'
      self.setCurrentView(v)
    elif input == 'd':
      v = nthSiblingOfView(self.currentView, -1)
      if v == oldView:
        print '\nThere are no sibling views to this view.\n'
      self.setCurrentView(v)
    elif input == 'a':
      v = nthSiblingOfView(self.currentView, 1)
      if v == oldView:
        print '\nThere are no sibling views to this view.\n'
      self.setCurrentView(v)
    elif input == 'p':
      lldb.debugger.HandleCommand('po [(id)' + oldView + ' recursiveDescription]')
    else:
      print '\nI really have no idea what you meant by \'' + input + '\'... =\\\n'

    viewHelpers.setViewHidden(oldView, False)

  def setCurrentView(self, view):
    if view:
      self.currentView = view
      lldb.debugger.HandleCommand('po (id)' + view)

def superviewOfView(view):
  superview = fb.evaluateObjectExpression('[' + view + ' superview]')
  if int(superview, 16) == 0:
    return None

  return superview

def subviewsOfView(view):
  return fb.evaluateObjectExpression('[' + view + ' subviews]')

def firstSubviewOfView(view):
  subviews = subviewsOfView(view)
  numViews = fb.evaluateIntegerExpression('[(id)' + subviews + ' count]')

  if numViews == 0:
    return None
  else:
    return fb.evaluateObjectExpression('[' + subviews + ' objectAtIndex:0]')

def nthSiblingOfView(view, n):
  subviews = subviewsOfView(superviewOfView(view))
  numViews = fb.evaluateIntegerExpression('[(id)' + subviews + ' count]')

  idx = fb.evaluateIntegerExpression('[(id)' + subviews + ' indexOfObject:' + view + ']')

  newIdx = idx + n
  while newIdx < 0:
    newIdx += numViews
  newIdx = newIdx % numViews

  return fb.evaluateObjectExpression('[(id)' + subviews + ' objectAtIndex:' + str(newIdx) + ']')

########NEW FILE########
__FILENAME__ = FBInvocationCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import re

import lldb
import fblldbbase as fb

def lldbcommands():
  return [
    FBPrintInvocation(),
  ]

class FBPrintInvocation(fb.FBCommand):
  def name(self):
    return 'pinvocation'

  def description(self):
    return 'Print the stack frame, receiver, and arguments of the current invocation. It will fail to print all arguments if any arguments are variadic (varargs).\n\nNOTE: Sadly this is currently only implemented on x86.'

  def options(self):
    return [
            fb.FBCommandArgument(short='-a', long='--all', arg='all', default=False, boolean=True, help='Specify to print the entire stack instead of just the current frame.'),
            ]

  def run(self, arguments, options):
    target = lldb.debugger.GetSelectedTarget()

    if not re.match(r'.*i386.*', target.GetTriple()):
      print 'Only x86 is currently supported (32-bit iOS Simulator or Mac OS X).'
      return

    thread = target.GetProcess().GetSelectedThread()

    if options.all:
      for frame in thread:
        printInvocationForFrame(frame)
        print '---------------------------------'
    else:
      frame = thread.GetSelectedFrame()
      printInvocationForFrame(frame)

def printInvocationForFrame(frame):
  print frame

  symbolName = frame.GetSymbol().GetName()
  if not re.match(r'[-+]\s*\[.*\]', symbolName):
    return

  self = findArgAtIndexFromStackFrame(frame, 0)
  cmd = findArgAtIndexFromStackFrame(frame, 1)

  commandForSignature = '[(id)' + self + ' methodSignatureForSelector:(char *)sel_getName((SEL)' + cmd + ')]'
  signatureValue = fb.evaluateExpressionValue('(id)' + commandForSignature)

  if signatureValue.GetError() is not None and str(signatureValue.GetError()) != 'success':
    print "My sincerest apologies. I couldn't find a method signature for the selector."
    return

  signature = signatureValue.GetValue()

  arg0 = stackStartAddressInSelectedFrame(frame)
  commandForInvocation = '[NSInvocation _invocationWithMethodSignature:(id)' + signature + ' frame:((void *)' + str(arg0) + ')]'
  invocation = fb.evaluateExpression('(id)' + commandForInvocation)

  if invocation:
    prettyPrintInvocation(frame, invocation)
  else:
    print frame

def stackStartAddressInSelectedFrame(frame):
  # Determine if the %ebp register has already had the stack register pushed into it (always the first instruction)
  frameSymbol = frame.GetSymbolContext(0).GetSymbol()
  frameStartAddress = frameSymbol.GetStartAddress().GetLoadAddress(lldb.debugger.GetSelectedTarget())

  currentPC = frame.GetPC()

  offset = currentPC - frameStartAddress

  if offset == 0:
    return int(frame.EvaluateExpression('($esp + 4)').GetValue())
  elif offset == 1:
    return int(frame.EvaluateExpression('($esp + 8)').GetValue())
  else:
    return int(frame.EvaluateExpression('($ebp + 8)').GetValue())
    

def findArgAtIndexFromStackFrame(frame, index):
  return fb.evaluateExpression('*(int *)' + str(findArgAdressAtIndexFromStackFrame(frame, index)))

def findArgAdressAtIndexFromStackFrame(frame, index):
  arg0 = stackStartAddressInSelectedFrame(frame)
  arg = arg0 + 4 * index
  return arg

def prettyPrintInvocation(frame, invocation):
  object = fb.evaluateExpression('(id)[(id)' + invocation + ' target]')
  selector = fb.evaluateExpressionValue('(char *)sel_getName((SEL)[(id)' + invocation + ' selector])').GetSummary()
  selector = re.sub(r'^"|"$', '', selector)

  objectClassValue = fb.evaluateExpressionValue('(id)object_getClass((id)' + object + ')')
  objectClass = objectClassValue.GetObjectDescription()

  description = fb.evaluateExpressionValue('(id)' + invocation).GetObjectDescription()
  argDescriptions = description.splitlines(True)[4:]

  print 'NSInvocation: ' + invocation
  print 'self: ' + fb.evaluateExpression('(id)' + object)

  if len(argDescriptions) > 0:
    print '\n' + str(len(argDescriptions)) + ' Arguments:' if len(argDescriptions) > 1 else '\nArgument:'

    index = 2
    for argDescription in argDescriptions:
      s = re.sub(r'argument [0-9]+: ', '', argDescription)

      lldb.debugger.HandleCommand('expr void *$v')
      lldb.debugger.HandleCommand('expr (void)[' + invocation + ' getArgument:&$v atIndex:' + str(index) + ']')

      address = findArgAdressAtIndexFromStackFrame(frame, index)

      encoding = s.split(' ')[0]
      description = ' '.join(s.split(' ')[1:])

      readableString = argumentAsString(frame, address, encoding)

      if readableString:
        print readableString
      else:
        if encoding[0] == '{':
          encoding = encoding[1:len(encoding)-1]
        print (hex(address) + ', address of ' + encoding + ' ' + description).strip()

      index += 1

def argumentAsString(frame, address, encoding):
  if encoding[0] == '{':
    encoding = encoding[1:len(encoding)-1]

  encodingMap = {
    'c' : 'char',
    'i' : 'int',
    's' : 'short',
    'l' : 'long',
    'q' : 'long long',

    'C' : 'unsigned char',
    'I' : 'unsigned int',
    'S' : 'unsigned short',
    'L' : 'unsigned long',
    'Q' : 'unsigned long long',

    'f' : 'float',
    'd' : 'double',
    'B' : 'bool',
    'v' : 'void',
    '*' : 'char *',
    '@' : 'id',
    '#' : 'Class',
    ':' : 'SEL',
  }

  pointers = ''
  while encoding[0] == '^':
    pointers += '*'
    encoding = encoding[1:]

  type = None
  if encoding in encodingMap:
    type = encodingMap[encoding]

  if type and pointers:
    type = type + ' ' + pointers

  if not type:
    # Handle simple structs: {CGPoint=ff}, {CGSize=ff}, {CGRect={CGPoint=ff}{CGSize=ff}}
    if encoding[0] == '{':
      encoding = encoding[1:]

    type = re.sub(r'=.*', '', encoding)
    if pointers:
      type += ' ' + pointers

  if type:
    value = frame.EvaluateExpression('*(' + type + ' *)' + str(address))

    if value.GetError() is None or str(value.GetError()) == 'success':
      description = None

      if encoding == '@':
        description = value.GetObjectDescription()

      if not description:
        description = value.GetValue()
      if not description:
        description = value.GetSummary()
      if description:
        return type + ': ' + description
  
  return None

########NEW FILE########
__FILENAME__ = FBPrintCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import os
import re

import lldb
import fblldbbase as fb
import fblldbviewcontrollerhelpers as vcHelpers
import fblldbviewhelpers as viewHelpers

def lldbcommands():
  return [
    FBPrintViewHierarchyCommand(),
    FBPrintCoreAnimationTree(),
    FBPrintViewControllerHierarchyCommand(),
    FBPrintIsExecutingInAnimationBlockCommand(),
    FBPrintInheritanceHierarchy(),
    FBPrintUpwardResponderChain(),
    FBPrintOnscreenTableView(),
    FBPrintOnscreenTableViewCells(),
    FBPrintInternals(),
    FBPrintInstanceVariable(),
    FBPrintAutolayoutTrace(),
  ]

class FBPrintViewHierarchyCommand(fb.FBCommand):
  def name(self):
    return 'pviews'

  def description(self):
    return 'Print the recursion description of <aView>.'

  def options(self):
    return [
      fb.FBCommandArgument(short='-u', long='--up', arg='upwards', boolean=True, default=False, help='Print only the hierarchy directly above the view, up to its window.'),
      fb.FBCommandArgument(short='-d', long='--depth', arg='depth', type='int', default="0", help='Print only to a given depth. 0 indicates infinite depth.'),
    ]

  def args(self):
    return [ fb.FBCommandArgument(arg='aView', type='UIView*', help='The view to print the description of.', default='(id)[[UIApplication sharedApplication] keyWindow]') ]

  def run(self, arguments, options):
    maxDepth = int(options.depth)

    if options.upwards:
      view = arguments[0]
      description = viewHelpers.upwardsRecursiveDescription(view, maxDepth)
      if description:
        print description
      else:
        print 'Failed to walk view hierarchy. Make sure you pass a view, not any other kind of object or expression.'
    else:
      description = fb.evaluateExpressionValue('(id)[' + arguments[0] + ' recursiveDescription]').GetObjectDescription()
      if maxDepth > 0:
        separator = re.escape("   | ")
        prefixToRemove = separator * maxDepth + " "
        description += "\n"
        description = re.sub(r'%s.*\n' % (prefixToRemove), r'', description)
      print description


class FBPrintCoreAnimationTree(fb.FBCommand):
  def name(self):
    return 'pca'

  def description(self):
    return 'Print layer tree from the perspective of the render server.'

  def run(self, arguments, options):
    lldb.debugger.HandleCommand('po [NSString stringWithCString:(char *)CARenderServerGetInfo(0, 2, 0)]')


class FBPrintViewControllerHierarchyCommand(fb.FBCommand):
  def name(self):
    return 'pvc'

  def description(self):
    return 'Print the recursion description of <aViewController>.'

  def args(self):
    return [ fb.FBCommandArgument(arg='aViewController', type='UIViewController*', help='The view controller to print the description of.', default='(id)[(id)[[UIApplication sharedApplication] keyWindow] rootViewController]') ]

  def run(self, arguments, options):
    print vcHelpers.viewControllerRecursiveDescription(arguments[0])


class FBPrintIsExecutingInAnimationBlockCommand(fb.FBCommand):
  def name(self):
    return 'panim'

  def description(self):
    return 'Prints if the code is currently execution with a UIView animation block.'

  def run(self, arguments, options):
    lldb.debugger.HandleCommand('p (BOOL)[UIView _isInAnimationBlock]')


def _printIterative(initialValue, generator):
  indent = 0
  for currentValue in generator(initialValue):
    print '   | '*indent + currentValue
    indent += 1


class FBPrintInheritanceHierarchy(fb.FBCommand):
  def name(self):
    return 'pclass'

  def description(self):
    return 'Print the inheritance starting from an instance of any class.'

  def args(self):
    return [ fb.FBCommandArgument(arg='object', type='id', help='The instance to examine.') ]

  def run(self, arguments, options):
    _printIterative(arguments[0], _inheritanceHierarchy)

def _inheritanceHierarchy(instanceOfAClass):
  instanceAddress = fb.evaluateExpression(instanceOfAClass)
  instanceClass = fb.evaluateExpression('(id)[(id)' + instanceAddress + ' class]')
  while int(instanceClass, 16):
    yield fb.evaluateExpressionValue(instanceClass).GetObjectDescription()
    instanceClass = fb.evaluateExpression('(id)[(id)' + instanceClass + ' superclass]')


class FBPrintUpwardResponderChain(fb.FBCommand):
  def name(self):
    return 'presponder'

  def description(self):
    return 'Print the responder chain starting from a specific responder.'

  def args(self):
    return [ fb.FBCommandArgument(arg='startResponder', type='UIResponder *', help='The responder to use to start walking the chain.') ]

  def run(self, arguments, options):
    startResponder = arguments[0]
    if not fb.evaluateBooleanExpression('(BOOL)[(id)' + startResponder + ' isKindOfClass:[UIResponder class]]'):
      print 'Whoa, ' + startResponder + ' is not a UIResponder. =('
      return

    _printIterative(startResponder, _responderChain)

def _responderChain(startResponder):
  responderAddress = fb.evaluateExpression(startResponder)
  while int(responderAddress, 16):
    yield fb.evaluateExpressionValue(responderAddress).GetObjectDescription()
    responderAddress = fb.evaluateExpression('(id)[(id)' + responderAddress + ' nextResponder]')


def tableViewInHierarchy():
  viewDescription = fb.evaluateExpressionValue('(id)[(id)[[UIApplication sharedApplication] keyWindow] recursiveDescription]').GetObjectDescription()

  searchView = None

  # Try to find an instance of
  classPattern = re.compile(r'UITableView: (0x[0-9a-fA-F]+);')
  for match in re.finditer(classPattern, viewDescription):
    searchView = match.group(1)
    break

  # Try to find a direct subclass
  if not searchView:
    subclassPattern = re.compile(r'(0x[0-9a-fA-F]+); baseClass = UITableView;')
    for match in re.finditer(subclassPattern, viewDescription):
      searchView = match.group(1)
      break

  # SLOW: check every pointer in town
  if not searchView:
    pattern = re.compile(r'(0x[0-9a-fA-F]+)[;>]')
    for (view) in re.findall(pattern, viewDescription):
      if fb.evaluateBooleanExpression('[' + view + ' isKindOfClass:(id)[UITableView class]]'):
        searchView = view
        break

  return searchView

class FBPrintOnscreenTableView(fb.FBCommand):
  def name(self):
    return 'ptv'

  def description(self):
    return 'Print the highest table view in the hierarchy.'

  def run(self, arguments, options):
    tableView = tableViewInHierarchy()
    if tableView:
      viewValue = fb.evaluateExpressionValue(tableView)
      print viewValue.GetObjectDescription()
      cmd = 'echo %s | tr -d "\n" | pbcopy' % tableView
      os.system(cmd)
    else:
      print 'Sorry, chump. I couldn\'t find a table-view. :\'('

class FBPrintOnscreenTableViewCells(fb.FBCommand):
  def name(self):
    return 'pcells'

  def description(self):
    return 'Print the visible cells of the highest table view in the hierarchy.'

  def run(self, arguments, options):
    tableView = tableViewInHierarchy()
    print fb.evaluateExpressionValue('(id)[(id)' + tableView + ' visibleCells]').GetObjectDescription()


class FBPrintInternals(fb.FBCommand):
  def name(self):
    return 'pinternals'

  def description(self):
    return 'Show the internals of an object by dereferencing it as a pointer.'

  def args(self):
    return [ fb.FBCommandArgument(arg='object', type='id', help='Object expression to be evaluated.') ]

  def run(self, arguments, options):
    object = fb.evaluateObjectExpression(arguments[0])
    objectClass = fb.evaluateExpressionValue('(id)[(id)(' + object + ') class]').GetObjectDescription()

    command = 'p *(({} *)((id){}))'.format(objectClass, object)
    lldb.debugger.HandleCommand(command)


class FBPrintInstanceVariable(fb.FBCommand):
  def name(self):
    return 'pivar'

  def description(self):
    return "Print the value of an object's named instance variable."

  def args(self):
    return [
      fb.FBCommandArgument(arg='object', type='id', help='Object expression to be evaluated.'),
      fb.FBCommandArgument(arg='ivarName', help='Name of instance variable to print.')
    ]

  def run(self, arguments, options):
    commandForObject, ivarName = arguments

    object = fb.evaluateObjectExpression(commandForObject)
    objectClass = fb.evaluateExpressionValue('(id)[(' + object + ') class]').GetObjectDescription()

    ivarTypeCommand = '((char *)ivar_getTypeEncoding((Ivar)object_getInstanceVariable((id){}, \"{}\", 0)))[0]'.format(object, ivarName)
    ivarTypeEncodingFirstChar = fb.evaluateExpression(ivarTypeCommand)

    printCommand = 'po' if ('@' in ivarTypeEncodingFirstChar) else 'p'
    lldb.debugger.HandleCommand('{} (({} *)({}))->{}'.format(printCommand, objectClass, object, ivarName))


class FBPrintAutolayoutTrace(fb.FBCommand):
  def name(self):
    return 'paltrace'

  def description(self):
    return "Print the Auto Layout trace for the given view. Defaults to the key window."

  def args(self):
    return [ fb.FBCommandArgument(arg='view', type='UIView *', help='The view to print the Auto Layout trace for.', default='(id)[[UIApplication sharedApplication] keyWindow]') ]

  def run(self, arguments, options):
    lldb.debugger.HandleCommand('po (id)[{} _autolayoutTrace]'.format(arguments[0]))

########NEW FILE########
__FILENAME__ = FBVisualizationCommands
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb
import os
import time
import errno
import fblldbbase as fb
import fblldbobjecthelpers as objectHelpers

def lldbcommands():
  return [
    FBVisualizeCommand()
  ]

def _showImage(commandForImage):
  imageDirectory = '/tmp/xcode_debug_images/'

  imageName = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ".png"
  imagePath = imageDirectory + imageName

  try:
    os.makedirs(imageDirectory)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(imageDirectory):
      pass
    else:
      raise

  imageDataAddress = fb.evaluateObjectExpression('UIImagePNGRepresentation((id)' + commandForImage +')')
  imageBytesStartAddress = fb.evaluateExpression('(void *)[(id)' + imageDataAddress + ' bytes]')
  imageBytesLength = fb.evaluateExpression('(NSUInteger)[(id)' + imageDataAddress + ' length]')

  address = int(imageBytesStartAddress,16)
  length = int(imageBytesLength)
  
  if not (address or length):
    print 'Could not get image data.'
    return

  process = lldb.debugger.GetSelectedTarget().GetProcess()
  error = lldb.SBError()
  mem = process.ReadMemory(address, length, error)
  
  if error is not None and str(error) != 'success':
    print error
  else:
    imgFile = open(imagePath, 'wb')
    imgFile.write(mem)
    imgFile.close()
    os.system('open ' + imagePath)

def _showLayer(layer):
  layer = '(' + layer + ')'

  lldb.debugger.HandleCommand('expr (void)UIGraphicsBeginImageContextWithOptions(((CGRect)[(id)' + layer + ' bounds]).size, NO, 0.0)')
  lldb.debugger.HandleCommand('expr (void)[(id)' + layer + ' renderInContext:(void *)UIGraphicsGetCurrentContext()]')

  frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
  result = frame.EvaluateExpression('(UIImage *)UIGraphicsGetImageFromCurrentImageContext()')
  if result.GetError() is not None and str(result.GetError()) != 'success':
    print result.GetError()
  else:
    image = result.GetValue()
    _showImage(image)

  lldb.debugger.HandleCommand('expr (void)UIGraphicsEndImageContext()')

def _dataIsImage(data):
  data = '(' + data + ')'

  frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
  result = frame.EvaluateExpression('(id)[UIImage imageWithData:' + data + ']');

  if result.GetError() is not None and str(result.GetError()) != 'success':
    return 0;
  else:
    isImage = result.GetValueAsUnsigned() != 0;
    if isImage:
      return 1;
    else:
      return 0;

def _dataIsString(data):
  data = '(' + data + ')'

  frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
  result = frame.EvaluateExpression('(NSString*)[[NSString alloc] initWithData:' + data + ' encoding:4]');

  if result.GetError() is not None and str(result.GetError()) != 'success':
    return 0;
  else:
    isString = result.GetValueAsUnsigned() != 0;
    if isString:
      return 1;
    else:
      return 0;

def _visualize(target):
  target = '(' + target + ')'
  
  if fb.evaluateBooleanExpression('(unsigned long)CFGetTypeID((CFTypeRef)' + target + ') == (unsigned long)CGImageGetTypeID()'):
    _showImage('(id)[UIImage imageWithCGImage:' + target + ']')
  else:
    if objectHelpers.isKindOfClass(target, 'UIImage'):
      _showImage(target)
    elif objectHelpers.isKindOfClass(target, 'UIView'):
      _showLayer('[(id)' + target + ' layer]')
    elif objectHelpers.isKindOfClass(target, 'CALayer'):
      _showLayer(target)
    elif objectHelpers.isKindOfClass(target, 'NSData'):
      if _dataIsImage(target):
        _showImage('(id)[UIImage imageWithData:' + target + ']');
      elif _dataIsString(target):
        lldb.debugger.HandleCommand('po (NSString*)[[NSString alloc] initWithData:' + target + ' encoding:4]')
      else:
        print 'Data isn\'t an image and isn\'t a string.';
    else:
      print '{} isn\'t supported. You can visualize UIImage, CGImageRef, UIView, CALayer or NSData.'.format(objectHelpers.className(target))

class FBVisualizeCommand(fb.FBCommand):
  def name(self):
    return 'visualize'

  def description(self):
    return 'Open a UIImage, CGImageRef, UIView, or CALayer in Preview.app on your Mac.'

  def args(self):
    return [ fb.FBCommandArgument(arg='target', type='(id)', help='The object to visualize.') ]

  def run(self, arguments, options):
    _visualize(arguments[0])

########NEW FILE########
__FILENAME__ = fblldb
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb

import imp
import os
import shlex
import sys
from optparse import OptionParser

import fblldbbase as fb

def __lldb_init_module(debugger, dict):
  filePath = os.path.realpath(__file__)
  lldbHelperDir = os.path.dirname(filePath)

  commandsDirectory = os.path.join(lldbHelperDir, 'commands')
  loadCommandsInDirectory(commandsDirectory)

def loadCommandsInDirectory(commandsDirectory):
  for file in os.listdir(commandsDirectory):
    fileName, fileExtension = os.path.splitext(file)
    if fileExtension == '.py':
      module = imp.load_source(fileName, os.path.join(commandsDirectory, file))

      if hasattr(module, 'lldbinit'):
        module.lldbinit()

      if hasattr(module, 'lldbcommands'):
        module._loadedFunctions = {}
        for command in module.lldbcommands():
          loadCommand(module, command, commandsDirectory, fileName, fileExtension)

def loadCommand(module, command, directory, filename, extension):
  func = makeRunCommand(command, os.path.join(directory, filename + extension))
  name = command.name()

  key = filename + '_' + name

  module._loadedFunctions[key] = func

  functionName = '__' + key

  lldb.debugger.HandleCommand('script ' + functionName + ' = sys.modules[\'' + module.__name__ + '\']._loadedFunctions[\'' + key + '\']')
  lldb.debugger.HandleCommand('command script add -f ' + functionName + ' ' + name)

def makeRunCommand(command, filename):
  def runCommand(debugger, input, result, dict):
    splitInput = shlex.split(input)
    options = None
    args = None

    # OptionParser will throw in the case where you want just one big long argument and no
    # options and you enter something that starts with '-' in the argument. e.g.:
    #     somecommand -[SomeClass someSelector:]
    # This solves that problem by prepending a '--' so that OptionParser does the right
    # thing.
    options = command.options()
    if len(options) == 0:
      if not '--' in splitInput:
        splitInput.insert(0, '--')

    parser = optionParserForCommand(command)
    (options, args) = parser.parse_args(splitInput)

    # When there are more args than the command has declared, assume
    # the initial args form an expression and combine them into a single arg.
    if len(args) > len(command.args()):
      overhead = len(args) - len(command.args())
      head = args[:overhead+1] # Take N+1 and reduce to 1.
      args = [' '.join(head)] + args[-overhead:]

    if validateArgsForCommand(args, command):
      command.run(args, options)

  runCommand.__doc__ = helpForCommand(command, filename)
  return runCommand

def validateArgsForCommand(args, command):
  if len(args) < len(command.args()):
    defaultArgs = [arg.default for arg in command.args()]
    defaultArgsToAppend = defaultArgs[len(args):]

    index = len(args)
    for defaultArg in defaultArgsToAppend:
      if not defaultArg:
        arg = command.args()[index]
        print 'Whoops! You are missing the <' + arg.argName + '> argument.'
        print '\nUsage: ' + usageForCommand(command)
        return
      index += 1

    args.extend(defaultArgsToAppend)
  return True

def optionParserForCommand(command):
  parser = OptionParser()

  for argument in command.options():
    if argument.boolean:
      parser.add_option(argument.shortName, argument.longName, dest=argument.argName,
                        help=argument.help, action=("store_false" if argument.default else "store_true"))
    else:
      parser.add_option(argument.shortName, argument.longName, dest=argument.argName,
                        help=argument.help, default=argument.default)

  return parser

def helpForCommand(command, filename):
  help = command.description()

  argSyntax = ''
  optionSyntax = ''

  if command.args():
    help += '\n\nArguments:'
    for arg in command.args():
      help += '\n  <' + arg.argName + '>; Type: ' + arg.argType + '; ' + arg.help
      argSyntax += ' <' + arg.argName + '>'

  if command.options():
    help += '\n\nOptions:'
    for option in command.options():

      optionFlag = ''
      if option.longName and option.shortName:
        optionFlag = option.longName + '/' + option.shortName
      elif option.longName:
        optionFlag = option.longName
      else:
        optionFlag = optiob.shortName

      help += '\n  ' + optionFlag + ' '

      if not option.boolean:
        help += '<' + option.argName + '>; Type: ' + option.argType

      help += '; ' + option.help

      optionSyntax += ' [{name}{arg}]'.format(
        name= option.longName or option.shortName,
        arg = '' if option.boolean else ('=' + option.argName)
      )

  help += '\n\nSyntax: ' + command.name() + optionSyntax + argSyntax

  help += '\n\nThis command is implemented as %s in %s.' % (command.__class__.__name__, filename)

  help += '\n\n(LLDB adds the next line, sorry...)'

  return help

def usageForCommand(command):
  usage = command.name()
  for arg in command.args():
    if arg.default:
      usage += ' [' + arg.argName + ']'
    else:
      usage += ' ' + arg.argName

  return usage


########NEW FILE########
__FILENAME__ = fblldbbase
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb

class FBCommandArgument:
  def __init__(self, short='', long='', arg='', type='', help='', default='', boolean=False):
    self.shortName = short
    self.longName = long
    self.argName = arg
    self.argType = type
    self.help = help
    self.default = default
    self.boolean = boolean

class FBCommand:
  def name(self):
    return None

  def options(self):
    return []

  def args(self):
    return []

  def description(self):
    return ''

  def run(self, arguments, option):
    pass


def evaluateExpressionValue(expression, printErrors = True):
  # lldb.frame is supposed to contain the right frame, but it doesnt :/ so do the dance
  frame = lldb.debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
  value = frame.EvaluateExpression(expression)
  if printErrors and value.GetError() is not None and str(value.GetError()) != 'success':
    print value.GetError()
  return value

def evaluateIntegerExpression(expression, printErrors = True):
  output = evaluateExpression('(int)(' + expression + ')', printErrors).replace('\'', '')
  if output.startswith('\\x'): # Booleans may display as \x01 (Hex)
    output = output[2:]
  elif output.startswith('\\'): # Or as \0 (Dec)
    output = output[1:]
  return int(output, 16)

def evaluateBooleanExpression(expression, printErrors = True):
  return (int(evaluateIntegerExpression('(BOOL)(' + expression + ')', printErrors)) != 0)

def evaluateExpression(expression, printErrors = True):
  return evaluateExpressionValue(expression, printErrors).GetValue()

def evaluateObjectExpression(expression, printErrors = True):
  return evaluateExpression('(id)(' + expression + ')', printErrors)

########NEW FILE########
__FILENAME__ = fblldbinputhelpers
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb

class FBInputHandler:
  def __init__(self, debugger, callback):
    self.debugger = debugger
    self.callback = callback
    self.inputReader = lldb.SBInputReader()
    self.inputReader.Initialize(
                                debugger,
                                self.handleInput,
                                lldb.eInputReaderGranularityLine,
                                None,
                                None, # prompt
                                True # echo
                                )

  def isValid(self):
    return not self.inputReader.IsDone()

  def start(self):
    self.debugger.PushInputReader(self.inputReader)

  def stop(self):
    self.inputReader.SetIsDone(True)

  def handleInput(self, inputReader, notification, bytes):
    if (notification == lldb.eInputReaderGotToken):
      self.callback(bytes)
    elif (notification == lldb.eInputReaderInterrupt):
      self.stop()
    
    return len(bytes)

########NEW FILE########
__FILENAME__ = fblldbobjcruntimehelpers
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb
import fblldbbase as fb
import re

def objc_getClass(className):
  command = '(void*)objc_getClass("{}")'.format(className)
  value = fb.evaluateExpression(command)
  return value

def object_getClass(object):
  command = '(void*)object_getClass({})'.format(object)
  value = fb.evaluateExpression(command)
  return value

def class_getName(klass):
  command = '(const char*)class_getName((Class){})'.format(klass)
  value = fb.evaluateExpressionValue(command).GetSummary().strip('"')
  return value

def class_getSuperclass(klass):
  command = '(void*)class_getSuperclass((Class){})'.format(klass)
  value = fb.evaluateExpression(command)
  return value

def class_getInstanceMethod(klass, selector):
  command = '(void*)class_getInstanceMethod((Class){}, @selector({}))'.format(klass, selector)
  value = fb.evaluateExpression(command)
  return value

def currentArch():
  targetTriple = lldb.debugger.GetSelectedTarget().GetTriple()
  arch = targetTriple.split('-')[0]
  return arch

def functionPreambleExpressionForSelf():
  arch = currentArch()
  expressionForSelf = None
  if arch == 'i386':
    expressionForSelf = '*(id*)($esp+4)'
  elif arch == 'x86_64':
    expressionForSelf = '(id)$rdi'
  elif arch == 'arm64':
    expressionForSelf = '(id)$x0'
  elif re.match(r'^armv.*$', arch):
    expressionForSelf = '(id)$r0'
  return expressionForSelf

def functionPreambleExpressionForObjectParameterAtIndex(parameterIndex):
  arch = currentArch()
  expresssion = None
  if arch == 'i386':
    expresssion = '*(id*)($esp + ' + str(12 + parameterIndex * 4) + ')'
  elif arch == 'x86_64':
    if (parameterIndex > 3):
      raise Exception("Current implementation can not return object at index greater than 3 for arc x86_64")
    registersList = ['rdx', 'rcx', 'r8', 'r9']
    expresssion = '(id)$' + registersList[parameterIndex]
  elif arch == 'arm64':
    if (parameterIndex > 5):
      raise Exception("Current implementation can not return object at index greater than 5 for arm64")  
    expresssion = '(id)$x' + str(parameterIndex + 2)
  elif re.match(r'^armv.*$', arch):
    if (parameterIndex > 3):
      raise Exception("Current implementation can not return object at index greater than 1 for arm32")
    expresssion = '(id)$r' + str(parameterIndex + 2)
  return expresssion

########NEW FILE########
__FILENAME__ = fblldbobjecthelpers
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb
import fblldbbase as fb

def isKindOfClass(obj, className):
  isKindOfClassStr = '[' + obj + 'isKindOfClass:[{} class]]'
  return fb.evaluateBooleanExpression(isKindOfClassStr.format(className))

def className(obj):
  return fb.evaluateExpressionValue('(id)[(' + obj + ') class]').GetObjectDescription()
########NEW FILE########
__FILENAME__ = fblldbviewcontrollerhelpers
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb
import fblldbbase as fb

def viewControllerRecursiveDescription(vc):
  return _recursiveViewControllerDescriptionWithPrefixAndChildPrefix(fb.evaluateObjectExpression(vc), '', '', '')

def _viewControllerDescription(viewController):
  vc = '(%s)' % (viewController)

  if fb.evaluateBooleanExpression('[(id)%s isViewLoaded]' % (vc)):
    result = fb.evaluateExpressionValue('(id)[[NSString alloc] initWithFormat:@"<%%@: %%p; view = <%%@; %%p>; frame = (%%g, %%g; %%g, %%g)>", (id)NSStringFromClass((id)[(id)%s class]), %s, (id)[(id)[(id)%s view] class], (id)[(id)%s view], ((CGRect)[(id)[(id)%s view] frame]).origin.x, ((CGRect)[(id)[(id)%s view] frame]).origin.y, ((CGRect)[(id)[(id)%s view] frame]).size.width, ((CGRect)[(id)[(id)%s view] frame]).size.height]' % (vc, vc, vc, vc, vc, vc, vc, vc))
  else:
    result = fb.evaluateExpressionValue('(id)[[NSString alloc] initWithFormat:@"<%%@: %%p; view not loaded>", (id)NSStringFromClass((id)[(id)%s class]), %s]' % (vc, vc))

  if result.GetError() is not None and str(result.GetError()) != 'success':
    return '[Error getting description.]'
  else:
    return result.GetObjectDescription()


def _recursiveViewControllerDescriptionWithPrefixAndChildPrefix(vc, string, prefix, childPrefix):
  s = '%s%s%s\n' % (prefix, '' if prefix == '' else ' ', _viewControllerDescription(vc))

  nextPrefix = childPrefix + '   |'

  numChildViewControllers = fb.evaluateIntegerExpression('(int)[(id)[%s childViewControllers] count]' % (vc))
  childViewControllers = fb.evaluateExpression('(id)[%s childViewControllers]' % (vc))

  for i in range(0, numChildViewControllers):
    viewController = fb.evaluateExpression('(id)[(id)[%s childViewControllers] objectAtIndex:%d]' % (vc, i))
    s += _recursiveViewControllerDescriptionWithPrefixAndChildPrefix(viewController, string, nextPrefix, nextPrefix)

  isModal = fb.evaluateBooleanExpression('%s != nil && ((id)[(id)[(id)%s presentedViewController] presentingViewController]) == %s' % (vc, vc, vc))

  if isModal:
    modalVC = fb.evaluateObjectExpression('(id)[(id)%s presentedViewController]' % (vc))
    s += _recursiveViewControllerDescriptionWithPrefixAndChildPrefix(modalVC, string, childPrefix + '  *M' , nextPrefix)
    s += '\n// \'*M\' means the view controller is presented modally.'

  return string + s
########NEW FILE########
__FILENAME__ = fblldbviewhelpers
#!/usr/bin/python

# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import lldb

import fblldbbase as fb

def flushCoreAnimationTransaction():
  lldb.debugger.HandleCommand('expr (void)[CATransaction flush]')

def setViewHidden(object, hidden):
  lldb.debugger.HandleCommand('expr (void)[' + object + ' setHidden:' + str(int(hidden)) + ']')
  flushCoreAnimationTransaction()

def maskView(viewOrLayer, color, alpha):
  unmaskView(viewOrLayer)
  window = fb.evaluateExpression('(UIWindow *)[[UIApplication sharedApplication] keyWindow]')
  origin = convertPoint(0, 0, viewOrLayer, window)
  size = fb.evaluateExpressionValue('(CGSize)((CGRect)[(id)%s frame]).size' % viewOrLayer)

  rectExpr = '(CGRect){{%s, %s}, {%s, %s}}' % (origin.GetChildMemberWithName('x').GetValue(),
                                               origin.GetChildMemberWithName('y').GetValue(),
                                               size.GetChildMemberWithName('width').GetValue(),
                                               size.GetChildMemberWithName('height').GetValue())
  mask = fb.evaluateExpression('[((UIView *)[UIView alloc]) initWithFrame:%s]' % rectExpr)

  lldb.debugger.HandleCommand('expr (void)[%s setTag:(NSInteger)%s]' % (mask, viewOrLayer))
  lldb.debugger.HandleCommand('expr (void)[%s setBackgroundColor:[UIColor %sColor]]' % (mask, color))
  lldb.debugger.HandleCommand('expr (void)[%s setAlpha:(CGFloat)%s]' % (mask, alpha))
  lldb.debugger.HandleCommand('expr (void)[%s addSubview:%s]' % (window, mask))
  flushCoreAnimationTransaction()

def unmaskView(viewOrLayer):
  window = fb.evaluateExpression('(UIWindow *)[[UIApplication sharedApplication] keyWindow]')
  mask = fb.evaluateExpression('(UIView *)[%s viewWithTag:(NSInteger)%s]' % (window, viewOrLayer))
  lldb.debugger.HandleCommand('expr (void)[%s removeFromSuperview]' % mask)
  flushCoreAnimationTransaction()

def convertPoint(x, y, fromViewOrLayer, toViewOrLayer):
  fromLayer = convertToLayer(fromViewOrLayer)
  toLayer = convertToLayer(toViewOrLayer)
  return fb.evaluateExpressionValue('(CGPoint)[%s convertPoint:(CGPoint){ .x = %s, .y = %s } toLayer:(CALayer *)%s]' % (fromLayer, x, y, toLayer))

def convertToLayer(viewOrLayer):
  if fb.evaluateBooleanExpression('[(id)%s isKindOfClass:(Class)[CALayer class]]' % viewOrLayer):
    return viewOrLayer
  elif fb.evaluateBooleanExpression('[(id)%s respondsToSelector:(SEL)@selector(layer)]' % viewOrLayer):
    return fb.evaluateExpression('(CALayer *)[%s layer]' % viewOrLayer)
  else:
    raise Exception('Argument must be a CALayer or a UIView')

def upwardsRecursiveDescription(view, maxDepth=0):
  if not fb.evaluateBooleanExpression('[(id)%s isKindOfClass:(Class)[UIView class]]' % view):
    return None
  
  currentView = view
  recursiveDescription = []
  depth = 0
  
  while currentView and (maxDepth <= 0 or depth <= maxDepth):
    depth += 1

    viewDescription = fb.evaluateExpressionValue('(id)[%s debugDescription]' % (currentView)).GetObjectDescription()
    currentView = fb.evaluateExpression('(void*)[%s superview]' % (currentView))
    try:
      if int(currentView, 0) == 0:
        currentView = None
    except:
      currentView = None
    
    if viewDescription:
      recursiveDescription.insert(0, viewDescription)

  if len(viewDescription) == 0:
  	return None
  
  currentPrefix = ""
  builder = ""
  for viewDescription in recursiveDescription:
    builder += currentPrefix + viewDescription + "\n"
    currentPrefix += "   | "
  
  return builder

########NEW FILE########
