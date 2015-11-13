__FILENAME__ = AimlParser
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import Locator
import sys
import xml.sax
import xml.sax.handler

from LangSupport import splitChinese

class AimlParserError(Exception): pass

class AimlHandler(ContentHandler):
        # The legal states of the AIML parser
        _STATE_OutsideAiml    = 0
        _STATE_InsideAiml     = 1
        _STATE_InsideCategory = 2
        _STATE_InsidePattern  = 3
        _STATE_AfterPattern   = 4
        _STATE_InsideThat     = 5
        _STATE_AfterThat      = 6
        _STATE_InsideTemplate = 7
        _STATE_AfterTemplate  = 8

        def __init__(self, encoding = "UTF-8"):
                self.categories = {}
                self._encoding = encoding
                self._state = self._STATE_OutsideAiml
                self._version = ""
                self._namespace = ""
                self._forwardCompatibleMode = False
                self._currentPattern = ""
                self._currentThat    = ""
                self._currentTopic   = ""
                self._insideTopic = False
                self._currentUnknown = "" # the name of the current unknown element

                # This is set to true when a parse error occurs in a category.
                self._skipCurrentCategory = False

                # Counts the number of parse errors in a particular AIML document.
                # query with getNumErrors().  If 0, the document is AIML-compliant.
                self._numParseErrors = 0

                # TODO: select the proper validInfo table based on the version number.
                self._validInfo = self._validationInfo101

                # This stack of bools is used when parsing <li> elements inside
                # <condition> elements, to keep track of whether or not an
                # attribute-less "default" <li> element has been found yet.  Only
                # one default <li> is allowed in each <condition> element.  We need
                # a stack in order to correctly handle nested <condition> tags.
                self._foundDefaultLiStack = []

                # This stack of strings indicates what the current whitespace-handling
                # behavior should be.  Each string in the stack is either "default" or
                # "preserve".  When a new AIML element is encountered, a new string is
                # pushed onto the stack, based on the value of the element's "xml:space"
                # attribute (if absent, the top of the stack is pushed again).  When
                # ending an element, pop an object off the stack.
                self._whitespaceBehaviorStack = ["default"]

                self._elemStack = []
                self._locator = Locator()
                self.setDocumentLocator(self._locator)

        def getNumErrors(self):
                "Return the number of errors found while parsing the current document."
                return self._numParseErrors

        def setEncoding(self, encoding):
                """Set the text encoding to use when encoding strings read from XML.

                Defaults to 'UTF-8'.

                """
                self._encoding = encoding

        def _location(self):
                "Return a string describing the current location in the source file."
                line = self._locator.getLineNumber()
                column = self._locator.getColumnNumber()
                return "(line %d, column %d)" % (line, column)

        def _pushWhitespaceBehavior(self, attr):
                """Push a new string onto the whitespaceBehaviorStack.

                The string's value is taken from the "xml:space" attribute, if it exists
                and has a legal value ("default" or "preserve").  Otherwise, the previous
                stack element is duplicated.

                """
                assert len(self._whitespaceBehaviorStack) > 0, "Whitespace behavior stack should never be empty!"
                try:
                        if attr["xml:space"] == "default" or attr["xml:space"] == "preserve":
                                self._whitespaceBehaviorStack.append(attr["xml:space"])
                        else:
                                raise AimlParserError, "Invalid value for xml:space attribute "+self._location()
                except KeyError:
                        self._whitespaceBehaviorStack.append(self._whitespaceBehaviorStack[-1])

        def startElementNS(self, name, qname, attr):
                print "QNAME:", qname
                print "NAME:", name
                uri,elem = name
                if (elem == "bot"): print "name:", attr.getValueByQName("name"), "a'ite?"
                self.startElement(elem, attr)
                pass

        def startElement(self, name, attr):
                # Wrapper around _startElement, which catches errors in _startElement()
                # and keeps going.

                # If we're inside an unknown element, ignore everything until we're
                # out again.
                if self._currentUnknown != "":
                        return
                # If we're skipping the current category, ignore everything until
                # it's finished.
                if self._skipCurrentCategory:
                        return

                # process this start-element.
                try: self._startElement(name, attr)
                except AimlParserError, msg:
                        # Print the error message
                        sys.stderr.write("PARSE ERROR: %s\n" % msg)

                        self._numParseErrors += 1 # increment error count
                        # In case of a parse error, if we're inside a category, skip it.
                        if self._state >= self._STATE_InsideCategory:
                                self._skipCurrentCategory = True

        def _startElement(self, name, attr):
                if name == "aiml":
                        # <aiml> tags are only legal in the OutsideAiml state
                        if self._state != self._STATE_OutsideAiml:
                                raise AimlParserError, "Unexpected <aiml> tag "+self._location()
                        self._state = self._STATE_InsideAiml
                        self._insideTopic = False
                        self._currentTopic = u""
                        try: self._version = attr["version"]
                        except KeyError:
                                # This SHOULD be a syntax error, but so many AIML sets out there are missing
                                # "version" attributes that it just seems nicer to let it slide.
                                #raise AimlParserError, "Missing 'version' attribute in <aiml> tag "+self._location()
                                #print "WARNING: Missing 'version' attribute in <aiml> tag "+self._location()
                                #print "         Defaulting to version 1.0"
                                self._version = "1.0"
                        self._forwardCompatibleMode = (self._version != "1.0.1")
                        self._pushWhitespaceBehavior(attr)
                        # Not sure about this namespace business yet...
                        #try:
                        #	self._namespace = attr["xmlns"]
                        #	if self._version == "1.0.1" and self._namespace != "http://alicebot.org/2001/AIML-1.0.1":
                        #		raise AimlParserError, "Incorrect namespace for AIML v1.0.1 "+self._location()
                        #except KeyError:
                        #	if self._version != "1.0":
                        #		raise AimlParserError, "Missing 'version' attribute(s) in <aiml> tag "+self._location()
                elif self._state == self._STATE_OutsideAiml:
                        # If we're outside of an AIML element, we ignore all tags.
                        return
                elif name == "topic":
                        # <topic> tags are only legal in the InsideAiml state, and only
                        # if we're not already inside a topic.
                        if (self._state != self._STATE_InsideAiml) or self._insideTopic:
                                raise AimlParserError, "Unexpected <topic> tag", self._location()
                        try: self._currentTopic = unicode(attr['name'])
                        except KeyError:
                                raise AimlParserError, "Required \"name\" attribute missing in <topic> element "+self._location()
                        self._insideTopic = True
                elif name == "category":
                        # <category> tags are only legal in the InsideAiml state
                        if self._state != self._STATE_InsideAiml:
                                raise AimlParserError, "Unexpected <category> tag "+self._location()
                        self._state = self._STATE_InsideCategory
                        self._currentPattern = u""
                        self._currentThat = u""
                        # If we're not inside a topic, the topic is implicitly set to *
                        if not self._insideTopic: self._currentTopic = u"*"
                        self._elemStack = []
                        self._pushWhitespaceBehavior(attr)
                elif name == "pattern":
                        # <pattern> tags are only legal in the InsideCategory state
                        if self._state != self._STATE_InsideCategory:
                                raise AimlParserError, "Unexpected <pattern> tag "+self._location()
                        self._state = self._STATE_InsidePattern
                elif name == "that" and self._state == self._STATE_AfterPattern:
                        # <that> are legal either inside a <template> element, or
                        # inside a <category> element, between the <pattern> and the
                        # <template> elements.  This clause handles the latter case.
                        self._state = self._STATE_InsideThat
                elif name == "template":
                        # <template> tags are only legal in the AfterPattern and AfterThat
                        # states
                        if self._state not in [self._STATE_AfterPattern, self._STATE_AfterThat]:
                                raise AimlParserError, "Unexpected <template> tag "+self._location()
                        # if no <that> element was specified, it is implicitly set to *
                        if self._state == self._STATE_AfterPattern:
                                self._currentThat = u"*"
                        self._state = self._STATE_InsideTemplate
                        self._elemStack.append(['template',{}])
                        self._pushWhitespaceBehavior(attr)
                elif self._state == self._STATE_InsidePattern:
                        # Certain tags are allowed inside <pattern> elements.
                        if name == "bot" and attr.has_key("name") and attr["name"] == u"name":
                                # Insert a special character string that the PatternMgr will
                                # replace with the bot's name.
                                self._currentPattern += u" BOT_NAME "
                        else:
                                raise AimlParserError, ("Unexpected <%s> tag " % name)+self._location()
                elif self._state == self._STATE_InsideThat:
                        # Certain tags are allowed inside <that> elements.
                        if name == "bot" and attr.has_key("name") and attr["name"] == u"name":
                                # Insert a special character string that the PatternMgr will
                                # replace with the bot's name.
                                self._currentThat += u" BOT_NAME "
                        else:
                                raise AimlParserError, ("Unexpected <%s> tag " % name)+self._location()
                elif self._state == self._STATE_InsideTemplate and self._validInfo.has_key(name):
                        # Starting a new element inside the current pattern. First
                        # we need to convert 'attr' into a native Python dictionary,
                        # so it can later be marshaled.
                        attrDict = {}
                        for k,v in attr.items():
                                #attrDict[k[1].encode(self._encoding)] = v.encode(self._encoding)
                                attrDict[k.encode(self._encoding)] = unicode(v)
                        self._validateElemStart(name, attrDict, self._version)
                        # Push the current element onto the element stack.
                        self._elemStack.append([name.encode(self._encoding),attrDict])
                        self._pushWhitespaceBehavior(attr)
                        # If this is a condition element, push a new entry onto the
                        # foundDefaultLiStack
                        if name == "condition":
                                self._foundDefaultLiStack.append(False)
                else:
                        # we're now inside an unknown element.
                        if self._forwardCompatibleMode:
                                # In Forward Compatibility Mode, we ignore the element and its
                                # contents.
                                self._currentUnknown = name
                        else:
                                # Otherwise, unknown elements are grounds for error!
                                raise AimlParserError, ("Unexpected <%s> tag " % name)+self._location()

        def characters(self, ch):
                # Wrapper around _characters which catches errors in _characters()
                # and keeps going.
                if self._state == self._STATE_OutsideAiml:
                        # If we're outside of an AIML element, we ignore all text
                        return
                if self._currentUnknown != "":
                        # If we're inside an unknown element, ignore all text
                        return
                if self._skipCurrentCategory:
                        # If we're skipping the current category, ignore all text.
                        return
                try: self._characters(ch)
                except AimlParserError, msg:
                        # Print the message
                        sys.stderr.write("PARSE ERROR: %s\n" % msg)
                        self._numParseErrors += 1 # increment error count
                        # In case of a parse error, if we're inside a category, skip it.
                        if self._state >= self._STATE_InsideCategory:
                                self._skipCurrentCategory = True

        def _characters(self, ch):
                text = unicode(ch)
                if self._state == self._STATE_InsidePattern:
                        # TODO: text inside patterns must be upper-case!
                        self._currentPattern += text
                elif self._state == self._STATE_InsideThat:
                        self._currentThat += text
                elif self._state == self._STATE_InsideTemplate:
                        # First, see whether the element at the top of the element stack
                        # is permitted to contain text.
                        try:
                                parent = self._elemStack[-1][0]
                                parentAttr = self._elemStack[-1][1]
                                required, optional, canBeParent = self._validInfo[parent]
                                nonBlockStyleCondition = (parent == "condition" and not (parentAttr.has_key("name") and parentAttr.has_key("value")))
                                if not canBeParent:
                                        raise AimlParserError, ("Unexpected text inside <%s> element "%parent)+self._location()
                                elif parent == "random" or nonBlockStyleCondition:
                                        # <random> elements can only contain <li> subelements. However,
                                        # there's invariably some whitespace around the <li> that we need
                                        # to ignore. Same for non-block-style <condition> elements (i.e.
                                        # those which don't have both a "name" and a "value" attribute).
                                        if len(text.strip()) == 0:
                                                # ignore whitespace inside these elements.
                                                return
                                        else:
                                                # non-whitespace text inside these elements is a syntax error.
                                                raise AimlParserError, ("Unexpected text inside <%s> element "%parent)+self._location()
                        except IndexError:
                                # the element stack is empty. This should never happen.
                                raise AimlParserError, "Element stack is empty while validating text "+self._location()

                        # Add a new text element to the element at the top of the element
                        # stack. If there's already a text element there, simply append the
                        # new characters to its contents.
                        try: textElemOnStack = (self._elemStack[-1][-1][0] == "text")
                        except IndexError: textElemOnStack = False
                        except KeyError: textElemOnStack = False
                        if textElemOnStack:
                                self._elemStack[-1][-1][2] += text
                        else:
                                self._elemStack[-1].append(["text", {"xml:space": self._whitespaceBehaviorStack[-1]}, text])
                else:
                        # all other text is ignored
                        pass

        def endElementNS(self, name, qname):
                uri, elem = name
                self.endElement(elem)

        def endElement(self, name):
                """Wrapper around _endElement which catches errors in _characters()
                and keeps going.

                """
                if self._state == self._STATE_OutsideAiml:
                        # If we're outside of an AIML element, ignore all tags
                        return
                if self._currentUnknown != "":
                        # see if we're at the end of an unknown element.  If so, we can
                        # stop ignoring everything.
                        if name == self._currentUnknown:
                                self._currentUnknown = ""
                        return
                if self._skipCurrentCategory:
                        # If we're skipping the current category, see if it's ending. We
                        # stop on ANY </category> tag, since we're not keeping track of
                        # state in ignore-mode.
                        if name == "category":
                                self._skipCurrentCategory = False
                                self._state = self._STATE_InsideAiml
                        return
                try: self._endElement(name)
                except AimlParserError, msg:
                        # Print the message
                        sys.stderr.write("PARSE ERROR: %s\n" % msg)
                        self._numParseErrors += 1 # increment error count
                        # In case of a parse error, if we're inside a category, skip it.
                        if self._state >= self._STATE_InsideCategory:
                                self._skipCurrentCategory = True

        def _endElement(self, name):
                """Verify that an AIML end element is valid in the current
                context.

                Raises an AimlParserError if an illegal end element is encountered.

                """
                if name == "aiml":
                        # </aiml> tags are only legal in the InsideAiml state
                        if self._state != self._STATE_InsideAiml:
                                raise AimlParserError, "Unexpected </aiml> tag "+self._location()
                        self._state = self._STATE_OutsideAiml
                        self._whitespaceBehaviorStack.pop()
                elif name == "topic":
                        # </topic> tags are only legal in the InsideAiml state, and
                        # only if _insideTopic is true.
                        if self._state != self._STATE_InsideAiml or not self._insideTopic:
                                raise AimlParserError, "Unexpected </topic> tag "+self._location()
                        self._insideTopic = False
                        self._currentTopic = u""
                elif name == "category":
                        # </category> tags are only legal in the AfterTemplate state
                        if self._state != self._STATE_AfterTemplate:
                                raise AimlParserError, "Unexpected </category> tag "+self._location()
                        self._state = self._STATE_InsideAiml
                        # End the current category.  Store the current pattern/that/topic and
                        # element in the categories dictionary.
                        self._currentPattern = u' '.join(splitChinese(self._currentPattern))
                        key = (self._currentPattern.strip(), self._currentThat.strip(),self._currentTopic.strip())
                        self.categories[key] = self._elemStack[-1]
                        self._whitespaceBehaviorStack.pop()
                elif name == "pattern":
                        # </pattern> tags are only legal in the InsidePattern state
                        if self._state != self._STATE_InsidePattern:
                                raise AimlParserError, "Unexpected </pattern> tag "+self._location()
                        self._state = self._STATE_AfterPattern
                elif name == "that" and self._state == self._STATE_InsideThat:
                        # </that> tags are only allowed inside <template> elements or in
                        # the InsideThat state.  This clause handles the latter case.
                        self._state = self._STATE_AfterThat
                elif name == "template":
                        # </template> tags are only allowed in the InsideTemplate state.
                        if self._state != self._STATE_InsideTemplate:
                                raise AimlParserError, "Unexpected </template> tag "+self._location()
                        self._state = self._STATE_AfterTemplate
                        self._whitespaceBehaviorStack.pop()
                elif self._state == self._STATE_InsidePattern:
                        # Certain tags are allowed inside <pattern> elements.
                        if name not in ["bot"]:
                                raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()
                elif self._state == self._STATE_InsideThat:
                        # Certain tags are allowed inside <that> elements.
                        if name not in ["bot"]:
                                raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()
                elif self._state == self._STATE_InsideTemplate:
                        # End of an element inside the current template.  Append the
                        # element at the top of the stack onto the one beneath it.
                        elem = self._elemStack.pop()
                        self._elemStack[-1].append(elem)
                        self._whitespaceBehaviorStack.pop()
                        # If the element was a condition, pop an item off the
                        # foundDefaultLiStack as well.
                        if elem[0] == "condition": self._foundDefaultLiStack.pop()
                else:
                        # Unexpected closing tag
                        raise AimlParserError, ("Unexpected </%s> tag " % name)+self._location()

        # A dictionary containing a validation information for each AIML
        # element. The keys are the names of the elements.  The values are a
        # tuple of three items. The first is a list containing the names of
        # REQUIRED attributes, the second is a list of OPTIONAL attributes,
        # and the third is a boolean value indicating whether or not the
        # element can contain other elements and/or text (if False, the
        # element can only appear in an atomic context, such as <date/>).
        _validationInfo101 = {
                "bot":          ( ["name"], [], False ),
                "condition":    ( [], ["name", "value"], True ), # can only contain <li> elements
                "date":         ( [], [], False ),
                "formal":       ( [], [], True ),
                "gender":       ( [], [], True ),
                "get":          ( ["name"], [], False ),
                "gossip":		( [], [], True ),
                "id":           ( [], [], False ),
                "input":        ( [], ["index"], False ),
                "javascript":	( [], [], True ),
                "learn":        ( [], [], True ),
                "li":           ( [], ["name", "value"], True ),
                "lowercase":    ( [], [], True ),
                "person":       ( [], [], True ),
                "person2":      ( [], [], True ),
                "random":       ( [], [], True ), # can only contain <li> elements
                "sentence":     ( [], [], True ),
                "set":          ( ["name"], [], True),
                "size":         ( [], [], False ),
                "sr":           ( [], [], False ),
                "srai":         ( [], [], True ),
                "star":         ( [], ["index"], False ),
                "system":       ( [], [], True ),
                "template":		( [], [], True ), # needs to be in the list because it can be a parent.
                "that":         ( [], ["index"], False ),
                "thatstar":     ( [], ["index"], False ),
                "think":        ( [], [], True ),
                "topicstar":    ( [], ["index"], False ),
                "uppercase":    ( [], [], True ),
                "version":      ( [], [], False ),
        }

        def _validateElemStart(self, name, attr, version):
                """Test the validity of an element starting inside a <template>
                element.

                This function raises an AimlParserError exception if it the tag is
                invalid.  Otherwise, no news is good news.

                """
                # Check the element's attributes.  Make sure that all required
                # attributes are present, and that any remaining attributes are
                # valid options.
                required, optional, canBeParent = self._validInfo[name]
                for a in required:
                        if a not in attr and not self._forwardCompatibleMode:
                                raise AimlParserError, ("Required \"%s\" attribute missing in <%s> element " % (a,name))+self._location()
                for a in attr:
                        if a in required: continue
                        if a[0:4] == "xml:": continue # attributes in the "xml" namespace can appear anywhere
                        if a not in optional and not self._forwardCompatibleMode:
                                raise AimlParserError, ("Unexpected \"%s\" attribute in <%s> element " % (a,name))+self._location()

                # special-case: several tags contain an optional "index" attribute.
                # This attribute's value must be a positive integer.
                if name in ["star", "thatstar", "topicstar"]:
                        for k,v in attr.items():
                                if k == "index":
                                        temp = 0
                                        try: temp = int(v)
                                        except:
                                                raise AimlParserError, ("Bad type for \"%s\" attribute (expected integer, found \"%s\") " % (k,v))+self._location()
                                        if temp < 1:
                                                raise AimlParserError, ("\"%s\" attribute must have non-negative value " % (k))+self._location()

                # See whether the containing element is permitted to contain
                # subelements. If not, this element is invalid no matter what it is.
                try:
                        parent = self._elemStack[-1][0]
                        parentAttr = self._elemStack[-1][1]
                except IndexError:
                        # If the stack is empty, no parent is present.  This should never
                        # happen.
                        raise AimlParserError, ("Element stack is empty while validating <%s> " % name)+self._location()
                required, optional, canBeParent = self._validInfo[parent]
                nonBlockStyleCondition = (parent == "condition" and not (parentAttr.has_key("name") and parentAttr.has_key("value")))
                if not canBeParent:
                        raise AimlParserError, ("<%s> elements cannot have any contents "%parent)+self._location()
                # Special-case test if the parent element is <condition> (the
                # non-block-style variant) or <random>: these elements can only
                # contain <li> subelements.
                elif (parent == "random" or nonBlockStyleCondition) and name!="li":
                        raise AimlParserError, ("<%s> elements can only contain <li> subelements "%parent)+self._location()
                # Special-case test for <li> elements, which can only be contained
                # by non-block-style <condition> and <random> elements, and whose
                # required attributes are dependent upon which attributes are
                # present in the <condition> parent.
                elif name=="li":
                        if not (parent=="random" or nonBlockStyleCondition):
                                raise AimlParserError, ("Unexpected <li> element contained by <%s> element "%parent)+self._location()
                        if nonBlockStyleCondition:
                                if parentAttr.has_key("name"):
                                        # Single-predicate condition.  Each <li> element except the
                                        # last must have a "value" attribute.
                                        if len(attr) == 0:
                                                # This could be the default <li> element for this <condition>,
                                                # unless we've already found one.
                                                if self._foundDefaultLiStack[-1]:
                                                        raise AimlParserError, "Unexpected default <li> element inside <condition> "+self._location()
                                                else:
                                                        self._foundDefaultLiStack[-1] = True
                                        elif len(attr) == 1 and attr.has_key("value"):
                                                pass # this is the valid case
                                        else:
                                                raise AimlParserError, "Invalid <li> inside single-predicate <condition> "+self._location()
                                elif len(parentAttr) == 0:
                                        # Multi-predicate condition.  Each <li> element except the
                                        # last must have a "name" and a "value" attribute.
                                        if len(attr) == 0:
                                                # This could be the default <li> element for this <condition>,
                                                # unless we've already found one.
                                                if self._foundDefaultLiStack[-1]:
                                                        raise AimlParserError, "Unexpected default <li> element inside <condition> "+self._location()
                                                else:
                                                        self._foundDefaultLiStack[-1] = True
                                        elif len(attr) == 2 and attr.has_key("value") and attr.has_key("name"):
                                                pass # this is the valid case
                                        else:
                                                raise AimlParserError, "Invalid <li> inside multi-predicate <condition> "+self._location()
                # All is well!
                return True

def create_parser():
        """Create and return an AIML parser object."""
        parser = xml.sax.make_parser()
        handler = AimlHandler("UTF-8")
        parser.setContentHandler(handler)
        #parser.setFeature(xml.sax.handler.feature_namespaces, True)
        return parser

########NEW FILE########
__FILENAME__ = DefaultSubs
"""This file contains the default (English) substitutions for the
PyAIML kernel.  These substitutions may be overridden by using the
Kernel.loadSubs(filename) method.  The filename specified should refer
to a Windows-style INI file with the following format:

    # lines that start with '#' are comments

    # The 'gender' section contains the substitutions performed by the
    # <gender> AIML tag, which swaps masculine and feminine pronouns.
    [gender]
    he = she
    she = he
    # and so on...

    # The 'person' section contains the substitutions performed by the
    # <person> AIML tag, which swaps 1st and 2nd person pronouns.
    [person]
    I = you
    you = I
    # and so on...

    # The 'person2' section contains the substitutions performed by
    # the <person2> AIML tag, which swaps 1st and 3nd person pronouns.
    [person2]
    I = he
    he = I
    # and so on...

    # the 'normal' section contains subtitutions run on every input
    # string passed into Kernel.respond().  It's mainly used to
    # correct common misspellings, and to convert contractions
    # ("WHAT'S") into a format that will match an AIML pattern ("WHAT
    # IS").
    [normal]
    what's = what is
"""

defaultGender = {
    # masculine -> feminine
    "he": "she",
    "him": "her",
    "his": "her",
    "himself": "herself",

    # feminine -> masculine    
    "she": "he",
    "her": "him",
    "hers": "his",
    "herself": "himself",
}

defaultPerson = {
    # 1st->3rd (masculine)
    "I": "he",
    "me": "him",
    "my": "his",
    "mine": "his",
    "myself": "himself",

    # 3rd->1st (masculine)
    "he":"I",
    "him":"me",
    "his":"my",
    "himself":"myself",
    
    # 3rd->1st (feminine)
    "she":"I",
    "her":"me",
    "hers":"mine",
    "herself":"myself",
}

defaultPerson2 = {
    # 1st -> 2nd
    "I": "you",
    "me": "you",
    "my": "your",
    "mine": "yours",
    "myself": "yourself",

    # 2nd -> 1st
    "you": "me",
    "your": "my",
    "yours": "mine",
    "yourself": "myself",
}


# TODO: this list is far from complete
defaultNormal = {
    "wanna": "want to",
    "gonna": "going to",

    "I'm": "I am",
    "I'd": "I would",
    "I'll": "I will",
    "I've": "I have",
    "you'd": "you would",
    "you're": "you are",
    "you've": "you have",
    "you'll": "you will",
    "he's": "he is",
    "he'd": "he would",
    "he'll": "he will",
    "she's": "she is",
    "she'd": "she would",
    "she'll": "she will",
    "we're": "we are",
    "we'd": "we would",
    "we'll": "we will",
    "we've": "we have",
    "they're": "they are",
    "they'd": "they would",
    "they'll": "they will",
    "they've": "they have",

    "y'all": "you all",    

    "can't": "can not",
    "cannot": "can not",
    "couldn't": "could not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    
    "isn't": "is not",
    "ain't": "is not",
    "don't": "do not",
    "aren't": "are not",
    "won't": "will not",
    "weren't": "were not",
    "wasn't": "was not",
    "didn't": "did not",
    "hasn't": "has not",
    "hadn't": "had not",
    "haven't": "have not",

    "where's": "where is",
    "where'd": "where did",
    "where'll": "where will",
    "who's": "who is",
    "who'd": "who did",
    "who'll": "who will",
    "what's": "what is",
    "what'd": "what did",
    "what'll": "what will",
    "when's": "when is",
    "when'd": "when did",
    "when'll": "when will",
    "why's": "why is",
    "why'd": "why did",
    "why'll": "why will",

    "it's": "it is",
    "it'd": "it would",
    "it'll": "it will",
}

########NEW FILE########
__FILENAME__ = Kernel
# -*- coding: latin-1 -*-
"""This file contains the public interface to the aiml module."""
import AimlParser
import DefaultSubs
import Utils
from PatternMgr import PatternMgr
from WordSub import WordSub
from LangSupport import splitChinese, mergeChineseSpace

from ConfigParser import ConfigParser
import copy
import glob
import os
import random
import re
import string
import sys
import time
import threading
import xml.sax


class Kernel:
    # module constants
    _globalSessionID = "_global" # key of the global session (duh)
    _maxHistorySize = 10 # maximum length of the _inputs and _responses lists
    _maxRecursionDepth = 100 # maximum number of recursive <srai>/<sr> tags before the response is aborted.
    # special predicate keys
    _inputHistory = "_inputHistory"     # keys to a queue (list) of recent user input
    _outputHistory = "_outputHistory"   # keys to a queue (list) of recent responses.
    _inputStack = "_inputStack"         # Should always be empty in between calls to respond()

    def __init__(self, sessionStore=None):
        self._verboseMode = True
        self._version = "PyAIML 0.8.6"
        self._brain = PatternMgr()
        self._respondLock = threading.RLock()
        self._textEncoding = "utf-8"

        # set up the sessions
        if sessionStore is not None:
            self._sessions = sessionStore
        else:
            self._sessions = {}
        self._addSession(self._globalSessionID)

        # Set up the bot predicates
        self._botPredicates = {}
        self.setBotPredicate("name", "Nameless")

        # set up the word substitutors (subbers):
        self._subbers = {}
        self._subbers['gender'] = WordSub(DefaultSubs.defaultGender)
        self._subbers['person'] = WordSub(DefaultSubs.defaultPerson)
        self._subbers['person2'] = WordSub(DefaultSubs.defaultPerson2)
        self._subbers['normal'] = WordSub(DefaultSubs.defaultNormal)

        # set up the element processors
        self._elementProcessors = {
            "bot":          self._processBot,
            "condition":    self._processCondition,
            "date":         self._processDate,
            "formal":       self._processFormal,
            "gender":       self._processGender,
            "get":          self._processGet,
            "gossip":       self._processGossip,
            "id":           self._processId,
            "input":        self._processInput,
            "javascript":   self._processJavascript,
            "learn":        self._processLearn,
            "li":           self._processLi,
            "lowercase":    self._processLowercase,
            "person":       self._processPerson,
            "person2":      self._processPerson2,
            "random":       self._processRandom,
            "text":         self._processText,
            "sentence":     self._processSentence,
            "set":          self._processSet,
            "size":         self._processSize,
            "sr":           self._processSr,
            "srai":         self._processSrai,
            "star":         self._processStar,
            "system":       self._processSystem,
            "template":     self._processTemplate,
            "that":         self._processThat,
            "thatstar":     self._processThatstar,
            "think":        self._processThink,
            "topicstar":    self._processTopicstar,
            "uppercase":    self._processUppercase,
            "version":      self._processVersion,
        }

    def bootstrap(self, brainFile = None, learnFiles = [], commands = []):
        """Prepare a Kernel object for use.

        If a brainFile argument is provided, the Kernel attempts to
        load the brain at the specified filename.

        If learnFiles is provided, the Kernel attempts to load the
        specified AIML files.

        Finally, each of the input strings in the commands list is
        passed to respond().

        """
        start = time.clock()
        if brainFile:
            self.restoreBrain(brainFile)

        # learnFiles might be a string, in which case it should be
        # turned into a single-element list.
        learns = learnFiles
        try: learns = [ learnFiles + "" ]
        except: pass
        for file in learns:
            self.learn(file)

        # ditto for commands
        cmds = commands
        try: cmds = [ commands + "" ]
        except: pass
        for cmd in cmds:
            print self._respond(cmd, self._globalSessionID)

        if self._verboseMode:
            print "Kernel bootstrap completed in %.2f seconds" % (time.clock() - start)

    def verbose(self, isVerbose = True):
        """Enable/disable verbose output mode."""
        self._verboseMode = isVerbose

    def version(self):
        """Return the Kernel's version string."""
        return self._version

    def numCategories(self):
        """Return the number of categories the Kernel has learned."""
        # there's a one-to-one mapping between templates and categories
        return self._brain.numTemplates()

    def resetBrain(self):
        """Reset the brain to its initial state.

        This is essentially equivilant to:
            del(kern)
            kern = aiml.Kernel()

        """
        del(self._brain)
        self.__init__()

    def restoreBrain(self, filename):
        """Attempt to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!

        """
        if self._verboseMode: print "Loading brain from %s..." % filename,
        start = time.clock()
        self._brain.restore(filename)
        if self._verboseMode:
            end = time.clock() - start
            print "done (%d categories in %.2f seconds)" % (self._brain.numTemplates(), end)

    def saveBrain(self, filename):
        """Dump the contents of the bot's brain to a file on disk."""
        if self._verboseMode: print "Saving brain to %s..." % filename,
        start = time.clock()
        self._brain.save(filename)
        if self._verboseMode:
            print "done (%.2f seconds)" % (time.clock() - start)

    def dumpsBrain(self):
        """Dump to a str"""
        return self._brain.dumps()

    def loadsBrain(self, raw):
        """Load from str"""
        self._brain.loads(raw)

    def getPredicate(self, name, sessionID = _globalSessionID):
        """Retrieve the current value of the predicate 'name' from the
        specified session.

        If name is not a valid predicate in the session, the empty
        string is returned.

        """
        try: return self._sessions[sessionID][name]
        except KeyError: return ""

    def setPredicate(self, name, value, sessionID = _globalSessionID):
        """Set the value of the predicate 'name' in the specified
        session.

        If sessionID is not a valid session, it will be created. If
        name is not a valid predicate in the session, it will be
        created.

        """
        self._addSession(sessionID) # add the session, if it doesn't already exist.
        self._sessions[sessionID][name] = value

    def getBotPredicate(self, name):
        """Retrieve the value of the specified bot predicate.

        If name is not a valid bot predicate, the empty string is returned.

        """
        try: return self._botPredicates[name]
        except KeyError: return ""

    def setBotPredicate(self, name, value):
        """Set the value of the specified bot predicate.

        If name is not a valid bot predicate, it will be created.

        """
        self._botPredicates[name] = value
        # Clumsy hack: if updating the bot name, we must update the
        # name in the brain as well
        if name == "name":
            self._brain.setBotName(self.getBotPredicate("name"))

    def setTextEncoding(self, encoding):
        """Set the text encoding used when loading AIML files (Latin-1, UTF-8, etc.)."""
        self._textEncoding = encoding

    def loadSubs(self, filename):
        """Load a substitutions file.

        The file must be in the Windows-style INI format (see the
        standard ConfigParser module docs for information on this
        format).  Each section of the file is loaded into its own
        substituter.

        """
        inFile = file(filename)
        parser = ConfigParser()
        parser.readfp(inFile, filename)
        inFile.close()
        for s in parser.sections():
            # Add a new WordSub instance for this section.  If one already
            # exists, delete it.
            if self._subbers.has_key(s):
                del(self._subbers[s])
            self._subbers[s] = WordSub()
            # iterate over the key,value pairs and add them to the subber
            for k,v in parser.items(s):
                self._subbers[s][unicode(k, self._textEncoding)] = unicode(v, self._textEncoding)

    def _addSession(self, sessionID):
        """Create a new session with the specified ID string."""
        if self._sessions.has_key(sessionID):
            return
        # Create the session.
        self._sessions[sessionID] = {
            # Initialize the special reserved predicates
            self._inputHistory: [],
            self._outputHistory: [],
            self._inputStack: []
        }

    def _deleteSession(self, sessionID):
        """Delete the specified session."""
        if self._sessions.has_key(sessionID):
            _sessions.pop(sessionID)

    def getSessionData(self, sessionID = None):
        """Return a copy of the session data dictionary for the
        specified session.

        If no sessionID is specified, return a dictionary containing
        *all* of the individual session dictionaries.

        """
        s = None
        if sessionID is not None:
            try: s = self._sessions[sessionID]
            except KeyError: s = {}
        else:
            s = self._sessions
        return copy.deepcopy(s)

    def learn(self, filename):
        """Load and learn the contents of the specified AIML file.

        If filename includes wildcard characters, all matching files
        will be loaded and learned.

        """
        for f in glob.glob(filename):
            if self._verboseMode: print "Loading %s..." % f,
            start = time.clock()
            # Load and parse the AIML file.
            parser = AimlParser.create_parser()
            handler = parser.getContentHandler()
            handler.setEncoding(self._textEncoding)
            try: parser.parse(f)
            except xml.sax.SAXParseException, msg:
                err = "\nFATAL PARSE ERROR in file %s:\n%s\n" % (f,msg)
                sys.stderr.write(err)
                continue
            # store the pattern/template pairs in the PatternMgr.
            for key,tem in handler.categories.items():
                self._brain.add(key,tem)
            # Parsing was successful.
            if self._verboseMode:
                print "done (%.2f seconds)" % (time.clock() - start)

    def respond(self, input, sessionID = _globalSessionID):
        """Return the Kernel's response to the input string."""
        if len(input) == 0:
            return ""

        #ensure that input is a unicode string
        try: input = input.decode(self._textEncoding, 'replace')
        except UnicodeError: pass
        except AttributeError: pass

        # prevent other threads from stomping all over us.
        self._respondLock.acquire()

        # Add the session, if it doesn't already exist
        self._addSession(sessionID)

        # split the input into discrete sentences
        sentences = Utils.sentences(input)
        finalResponse = ""

        for s in sentences:
            # Add the input to the history list before fetching the
            # response, so that <input/> tags work properly.
            inputHistory = self.getPredicate(self._inputHistory, sessionID)
            inputHistory.append(s)

            while len(inputHistory) > self._maxHistorySize:
                inputHistory.pop(0)
            self.setPredicate(self._inputHistory, inputHistory, sessionID)

            # Fetch the response
            response = self._respond(s, sessionID)

            # add the data from this exchange to the history lists
            outputHistory = self.getPredicate(self._outputHistory, sessionID)
            outputHistory.append(response)
            while len(outputHistory) > self._maxHistorySize:
                outputHistory.pop(0)
            self.setPredicate(self._outputHistory, outputHistory, sessionID)

            # append this response to the final response.
            finalResponse += (response + "  ")
        finalResponse = finalResponse.strip()
        finalResponse = mergeChineseSpace(unicode(finalResponse, self._textEncoding) if type(finalResponse) == str else finalResponse)
        assert(len(self.getPredicate(self._inputStack, sessionID)) == 0)

        # release the lock and return
        self._respondLock.release()
        try: return finalResponse.encode(self._textEncoding)
        except UnicodeError: return finalResponse

    # This version of _respond() just fetches the response for some input.
    # It does not mess with the input and output histories.  Recursive calls
    # to respond() spawned from tags like <srai> should call this function
    # instead of respond().
    def _respond(self, input, sessionID):
        """Private version of respond(), does the real work."""
        if len(input) == 0:
            return ""
        # guard against infinite recursion
        inputStack = self.getPredicate(self._inputStack, sessionID)
        if len(inputStack) > self._maxRecursionDepth:
            if self._verboseMode:
                err = "WARNING: maximum recursion depth exceeded (input='%s')" % input.encode(self._textEncoding, 'replace')
                sys.stderr.write(err)
            return ""

        # push the input onto the input stack
        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.append(input)
        self.setPredicate(self._inputStack, inputStack, sessionID)

        # run the input through the 'normal' subber
        subbedInput = self._subbers['normal'].sub(input)

        # fetch the bot's previous response, to pass to the match()
        # function as 'that'.
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = outputHistory[-1]
        except IndexError: that = ""
        subbedThat = self._subbers['normal'].sub(that)

        # fetch the current topic
        topic = self.getPredicate("topic", sessionID)
        subbedTopic = self._subbers['normal'].sub(topic)

        # Determine the final response.
        response = ""
        elem = self._brain.match(subbedInput, subbedThat, subbedTopic)
        if elem is None:
            if self._verboseMode:
                err = "WARNING: No match found for input: %s\n" % input.encode(self._textEncoding)
                sys.stderr.write(err)
        else:
            # Process the element into a response string.
            response += self._processElement(elem, sessionID).strip()
            response += " "
        response = response.strip()

        # pop the top entry off the input stack.
        inputStack = self.getPredicate(self._inputStack, sessionID)
        inputStack.pop()
        self.setPredicate(self._inputStack, inputStack, sessionID)

        return response

    def _processElement(self,elem, sessionID):
        """Process an AIML element.

        The first item of the elem list is the name of the element's
        XML tag.  The second item is a dictionary containing any
        attributes passed to that tag, and their values.  Any further
        items in the list are the elements enclosed by the current
        element's begin and end tags; they are handled by each
        element's handler function.

        """
        try:
            handlerFunc = self._elementProcessors[elem[0]]
        except:
            # Oops -- there's no handler function for this element
            # type!
            if self._verboseMode:
                err = "WARNING: No handler found for <%s> element\n" % elem[0].encode(self._textEncoding, 'replace')
                sys.stderr.write(err)
            return ""
        return handlerFunc(elem, sessionID)


    ######################################################
    ### Individual element-processing functions follow ###
    ######################################################

    # <bot>
    def _processBot(self, elem, sessionID):
        """Process a <bot> AIML element.

        Required element attributes:
            name: The name of the bot predicate to retrieve.

        <bot> elements are used to fetch the value of global,
        read-only "bot predicates."  These predicates cannot be set
        from within AIML; you must use the setBotPredicate() function.

        """
        attrName = elem[1]['name']
        return self.getBotPredicate(attrName)

    # <condition>
    def _processCondition(self, elem, sessionID):
        """Process a <condition> AIML element.

        Optional element attributes:
            name: The name of a predicate to test.
            value: The value to test the predicate for.

        <condition> elements come in three flavors.  Each has different
        attributes, and each handles their contents differently.

        The simplest case is when the <condition> tag has both a 'name'
        and a 'value' attribute.  In this case, if the predicate
        'name' has the value 'value', then the contents of the element
        are processed and returned.

        If the <condition> element has only a 'name' attribute, then
        its contents are a series of <li> elements, each of which has
        a 'value' attribute.  The list is scanned from top to bottom
        until a match is found.  Optionally, the last <li> element can
        have no 'value' attribute, in which case it is processed and
        returned if no other match is found.

        If the <condition> element has neither a 'name' nor a 'value'
        attribute, then it behaves almost exactly like the previous
        case, except that each <li> subelement (except the optional
        last entry) must now include both 'name' and 'value'
        attributes.

        """
        attr = None
        response = ""
        attr = elem[1]

        # Case #1: test the value of a specific predicate for a
        # specific value.
        if attr.has_key('name') and attr.has_key('value'):
            val = self.getPredicate(attr['name'], sessionID)
            if val == attr['value']:
                for e in elem[2:]:
                    response += self._processElement(e,sessionID)
                return response
        else:
            # Case #2 and #3: Cycle through <li> contents, testing a
            # name and value pair for each one.
            try:
                name = None
                if attr.has_key('name'):
                    name = attr['name']
                # Get the list of <li> elemnents
                listitems = []
                for e in elem[2:]:
                    if e[0] == 'li':
                        listitems.append(e)
                # if listitems is empty, return the empty string
                if len(listitems) == 0:
                    return ""
                # iterate through the list looking for a condition that
                # matches.
                foundMatch = False
                for li in listitems:
                    try:
                        liAttr = li[1]
                        # if this is the last list item, it's allowed
                        # to have no attributes.  We just skip it for now.
                        if len(liAttr.keys()) == 0 and li == listitems[-1]:
                            continue
                        # get the name of the predicate to test
                        liName = name
                        if liName == None:
                            liName = liAttr['name']
                        # get the value to check against
                        liValue = liAttr['value']
                        # do the test
                        if self.getPredicate(liName, sessionID) == liValue:
                            foundMatch = True
                            response += self._processElement(li,sessionID)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self._verboseMode: print "Something amiss -- skipping listitem", li
                        raise
                if not foundMatch:
                    # Check the last element of listitems.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = listitems[-1]
                        liAttr = li[1]
                        if not (liAttr.has_key('name') or liAttr.has_key('value')):
                            response += self._processElement(li, sessionID)
                    except:
                        # listitems was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self._verboseMode: print "error in default listitem"
                        raise
            except:
                # Some other catastrophic cataclysm
                if self._verboseMode: print "catastrophic condition failure"
                raise
        return response

    # <date>
    def _processDate(self, elem, sessionID):
        """Process a <date> AIML element.

        <date> elements resolve to the current date and time.  The
        AIML specification doesn't require any particular format for
        this information, so I go with whatever's simplest.
        ADDED: format parameter support

        """
        attr = elem[1]
        if 'format' in attr:
            format = attr['format'].encode(self._textEncoding)
            return unicode(time.strftime(format, time.localtime()), self._textEncoding)
        return time.asctime()

    # <formal>
    def _processFormal(self, elem, sessionID):
        """Process a <formal> AIML element.

        <formal> elements process their contents recursively, and then
        capitalize the first letter of each word of the result.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.capwords(response)

    # <gender>
    def _processGender(self,elem, sessionID):
        """Process a <gender> AIML element.

        <gender> elements process their contents, and then swap the
        gender of any third-person singular pronouns in the result.
        This subsitution is handled by the aiml.WordSub module.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return self._subbers['gender'].sub(response)

    # <get>
    def _processGet(self, elem, sessionID):
        """Process a <get> AIML element.

        Required element attributes:
            name: The name of the predicate whose value should be
            retrieved from the specified session and returned.  If the
            predicate doesn't exist, the empty string is returned.

        <get> elements return the value of a predicate from the
        specified session.

        """
        return self.getPredicate(elem[1]['name'], sessionID)

    # <gossip>
    def _processGossip(self, elem, sessionID):
        """Process a <gossip> AIML element.

        <gossip> elements are used to capture and store user input in
        an implementation-defined manner, theoretically allowing the
        bot to learn from the people it chats with.  I haven't
        descided how to define my implementation, so right now
        <gossip> behaves identically to <think>.

        """
        return self._processThink(elem, sessionID)

    # <id>
    def _processId(self, elem, sessionID):
        """ Process an <id> AIML element.

        <id> elements return a unique "user id" for a specific
        conversation.  In PyAIML, the user id is the name of the
        current session.

        """
        return sessionID

    # <input>
    def _processInput(self, elem, sessionID):
        """Process an <input> AIML element.

        Optional attribute elements:
            index: The index of the element from the history list to
            return. 1 means the most recent item, 2 means the one
            before that, and so on.

        <input> elements return an entry from the input history for
        the current session.

        """
        inputHistory = self.getPredicate(self._inputHistory, sessionID)
        try: index = int(elem[1]['index'])
        except: index = 1
        try: return inputHistory[-index]
        except IndexError:
            if self._verboseMode:
                err = "No such index %d while processing <input> element.\n" % index
                sys.stderr.write(err)
            return ""

    # <javascript>
    def _processJavascript(self, elem, sessionID):
        """Process a <javascript> AIML element.

        <javascript> elements process their contents recursively, and
        then run the results through a server-side Javascript
        interpreter to compute the final response.  Implementations
        are not required to provide an actual Javascript interpreter,
        and right now PyAIML doesn't; <javascript> elements are behave
        exactly like <think> elements.

        """
        return self._processThink(elem, sessionID)

    # <learn>
    def _processLearn(self, elem, sessionID):
        """Process a <learn> AIML element.

        <learn> elements process their contents recursively, and then
        treat the result as an AIML file to open and learn.

        """
        filename = ""
        for e in elem[2:]:
            filename += self._processElement(e, sessionID)
        self.learn(filename)
        return ""

    # <li>
    def _processLi(self,elem, sessionID):
        """Process an <li> AIML element.

        Optional attribute elements:
            name: the name of a predicate to query.
            value: the value to check that predicate for.

        <li> elements process their contents recursively and return
        the results. They can only appear inside <condition> and
        <random> elements.  See _processCondition() and
        _processRandom() for details of their usage.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    # <lowercase>
    def _processLowercase(self,elem, sessionID):
        """Process a <lowercase> AIML element.

        <lowercase> elements process their contents recursively, and
        then convert the results to all-lowercase.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.lower(response)

    # <person>
    def _processPerson(self,elem, sessionID):
        """Process a <person> AIML element.

        <person> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 2nd
        person, and vice versa.  This subsitution is handled by the
        aiml.WordSub module.

        If the <person> tag is used atomically (e.g. <person/>), it is
        a shortcut for <person><star/></person>.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        if len(elem[2:]) == 0:  # atomic <person/> = <person><star/></person>
            response = self._processElement(['star',{}], sessionID)
        return self._subbers['person'].sub(response)

    # <person2>
    def _processPerson2(self,elem, sessionID):
        """Process a <person2> AIML element.

        <person2> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 3rd
        person, and vice versa.  This subsitution is handled by the
        aiml.WordSub module.

        If the <person2> tag is used atomically (e.g. <person2/>), it is
        a shortcut for <person2><star/></person2>.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        if len(elem[2:]) == 0:  # atomic <person2/> = <person2><star/></person2>
            response = self._processElement(['star',{}], sessionID)
        return self._subbers['person2'].sub(response)

    # <random>
    def _processRandom(self, elem, sessionID):
        """Process a <random> AIML element.

        <random> elements contain zero or more <li> elements.  If
        none, the empty string is returned.  If one or more <li>
        elements are present, one of them is selected randomly to be
        processed recursively and have its results returned.  Only the
        chosen <li> element's contents are processed.  Any non-<li> contents are
        ignored.

        """
        listitems = []
        for e in elem[2:]:
            if e[0] == 'li':
                listitems.append(e)
        if len(listitems) == 0:
            return ""

        # select and process a random listitem.
        random.shuffle(listitems)
        return self._processElement(listitems[0], sessionID)

    # <sentence>
    def _processSentence(self,elem, sessionID):
        """Process a <sentence> AIML element.

        <sentence> elements process their contents recursively, and
        then capitalize the first letter of the results.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        try:
            response = response.strip()
            words = string.split(response, " ", 1)
            words[0] = string.capitalize(words[0])
            response = string.join(words)
            return response
        except IndexError: # response was empty
            return ""

    # <set>
    def _processSet(self, elem, sessionID):
        """Process a <set> AIML element.

        Required element attributes:
            name: The name of the predicate to set.

        <set> elements process their contents recursively, and assign the results to a predicate
        (given by their 'name' attribute) in the current session.  The contents of the element
        are also returned.

        """
        value = ""
        for e in elem[2:]:
            value += self._processElement(e, sessionID)
        self.setPredicate(elem[1]['name'], value, sessionID)
        return value

    # <size>
    def _processSize(self,elem, sessionID):
        """Process a <size> AIML element.

        <size> elements return the number of AIML categories currently
        in the bot's brain.

        """
        return str(self.numCategories())

    # <sr>
    def _processSr(self,elem,sessionID):
        """Process an <sr> AIML element.

        <sr> elements are shortcuts for <srai><star/></srai>.

        """
        star = self._processElement(['star',{}], sessionID)
        response = self._respond(star, sessionID)
        return response

    # <srai>
    def _processSrai(self,elem, sessionID):
        """Process a <srai> AIML element.

        <srai> elements recursively process their contents, and then
        pass the results right back into the AIML interpreter as a new
        piece of input.  The results of this new input string are
        returned.

        """
        newInput = ""
        for e in elem[2:]:
            newInput += self._processElement(e, sessionID)
        return self._respond(newInput, sessionID)

    # <star>
    def _processStar(self, elem, sessionID):
        """Process a <star> AIML element.

        Optional attribute elements:
            index: Which "*" character in the current pattern should
            be matched?

        <star> elements return the text fragment matched by the "*"
        character in the current input pattern.  For example, if the
        input "Hello Tom Smith, how are you?" matched the pattern
        "HELLO * HOW ARE YOU", then a <star> element in the template
        would evaluate to "Tom Smith".

        """
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("star", input, that, topic, index)
        return response

    # <system>
    def _processSystem(self,elem, sessionID):
        """Process a <system> AIML element.

        <system> elements process their contents recursively, and then
        attempt to execute the results as a shell command on the
        server.  The AIML interpreter blocks until the command is
        complete, and then returns the command's output.

        For cross-platform compatibility, any file paths inside
        <system> tags should use Unix-style forward slashes ("/") as a
        directory separator.

        """
        # build up the command string
        command = ""
        for e in elem[2:]:
            command += self._processElement(e, sessionID)
        # normalize the path to the command.  Under Windows, this
        # switches forward-slashes to back-slashes; all system
        # elements should use unix-style paths for cross-platform
        # compatibility.
        #executable,args = command.split(" ", 1)
        #executable = os.path.normpath(executable)
        #command = executable + " " + args
        command = command.encode(self._textEncoding)
        command = os.path.normpath(command)

        # execute the command.
        response = ""
        try:
            out = os.popen(command)
        except RuntimeError, msg:
            if self._verboseMode:
                err = "WARNING: RuntimeError while processing \"system\" element:\n%s\n" % msg.encode(self._textEncoding, 'replace')
                sys.stderr.write(err)
            return "There was an error while computing my response.  Please inform my botmaster."
        time.sleep(0.01) # I'm told this works around a potential IOError exception.
        for line in out:
            response += line + "\n"
        response = string.join(response.splitlines()).strip()
        response = response.decode(self._textEncoding) # FIXED: multilang term
        return response

    # <template>
    def _processTemplate(self,elem, sessionID):
        """Process a <template> AIML element.

        <template> elements recursively process their contents, and
        return the results.  <template> is the root node of any AIML
        response tree.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return response

    # text
    def _processText(self,elem, sessionID):
        """Process a raw text element.

        Raw text elements aren't really AIML tags. Text elements cannot contain
        other elements; instead, the third item of the 'elem' list is a text
        string, which is immediately returned. They have a single attribute,
        automatically inserted by the parser, which indicates whether whitespace
        in the text should be preserved or not.

        """
        try: elem[2] + ""
        except TypeError: raise TypeError, "Text element contents are not text"

        # If the the whitespace behavior for this element is "default",
        # we reduce all stretches of >1 whitespace characters to a single
        # space.  To improve performance, we do this only once for each
        # text element encountered, and save the results for the future.
        if elem[1]["xml:space"] == "default":
            elem[2] = re.sub("\s+", " ", elem[2])
            elem[1]["xml:space"] = "preserve"
        return elem[2]

    # <that>
    def _processThat(self,elem, sessionID):
        """Process a <that> AIML element.

        Optional element attributes:
            index: Specifies which element from the output history to
            return.  1 is the most recent response, 2 is the next most
            recent, and so on.

        <that> elements (when they appear inside <template> elements)
        are the output equivilant of <input> elements; they return one
        of the Kernel's previous responses.

        """
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        index = 1
        try:
            # According to the AIML spec, the optional index attribute
            # can either have the form "x" or "x,y". x refers to how
            # far back in the output history to go.  y refers to which
            # sentence of the specified response to return.
            index = int(elem[1]['index'].split(',')[0])
        except:
            pass
        try: return outputHistory[-index]
        except IndexError:
            if self._verboseMode:
                err = "No such index %d while processing <that> element.\n" % index
                sys.stderr.write(err)
            return ""

    # <thatstar>
    def _processThatstar(self, elem, sessionID):
        """Process a <thatstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <that> pattern to match.

        <thatstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <thatstar/> returns
        the portion of the previous input string that was matched by a
        "*" in the current category's <that> pattern.

        """
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("thatstar", input, that, topic, index)
        return response

    # <think>
    def _processThink(self,elem, sessionID):
        """Process a <think> AIML element.

        <think> elements process their contents recursively, and then
        discard the results and return the empty string.  They're
        useful for setting predicates and learning AIML files without
        generating any output.

        """
        for e in elem[2:]:
            self._processElement(e, sessionID)
        return ""

    # <topicstar>
    def _processTopicstar(self, elem, sessionID):
        """Process a <topicstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <topic> pattern to match.

        <topicstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <topicstar/>
        returns the portion of current topic string that was matched
        by a "*" in the current category's <topic> pattern.

        """
        try: index = int(elem[1]['index'])
        except KeyError: index = 1
        # fetch the user's last input
        inputStack = self.getPredicate(self._inputStack, sessionID)
        input = self._subbers['normal'].sub(inputStack[-1])
        # fetch the Kernel's last response (for 'that' context)
        outputHistory = self.getPredicate(self._outputHistory, sessionID)
        try: that = self._subbers['normal'].sub(outputHistory[-1])
        except: that = "" # there might not be any output yet
        topic = self.getPredicate("topic", sessionID)
        response = self._brain.star("topicstar", input, that, topic, index)
        return response

    # <uppercase>
    def _processUppercase(self,elem, sessionID):
        """Process an <uppercase> AIML element.

        <uppercase> elements process their contents recursively, and
        return the results with all lower-case characters converted to
        upper-case.

        """
        response = ""
        for e in elem[2:]:
            response += self._processElement(e, sessionID)
        return string.upper(response)

    # <version>
    def _processVersion(self,elem, sessionID):
        """Process a <version> AIML element.

        <version> elements return the version number of the AIML
        interpreter.

        """
        return self.version()


##################################################
### Self-test functions follow                 ###
##################################################
def _testTag(kern, tag, input, outputList):
    """Tests 'tag' by feeding the Kernel 'input'.  If the result
    matches any of the strings in 'outputList', the test passes.

    """
    global _numTests, _numPassed
    _numTests += 1
    print "Testing <" + tag + ">:",
    response = kern.respond(input).decode(kern._textEncoding)
    if response in outputList:
        print "PASSED"
        _numPassed += 1
        return True
    else:
        print "FAILED (response: '%s')" % response.encode(kern._textEncoding, 'replace')
        return False

if __name__ == "__main__":
    # Run some self-tests
    k = Kernel()
    k.bootstrap(learnFiles="self-test.aiml")

    global _numTests, _numPassed
    _numTests = 0
    _numPassed = 0

    _testTag(k, 'bot', 'test bot', ["My name is Nameless"])

    k.setPredicate('gender', 'male')
    _testTag(k, 'condition test #1', 'test condition name value', ['You are handsome'])
    k.setPredicate('gender', 'female')
    _testTag(k, 'condition test #2', 'test condition name value', [''])
    _testTag(k, 'condition test #3', 'test condition name', ['You are beautiful'])
    k.setPredicate('gender', 'robot')
    _testTag(k, 'condition test #4', 'test condition name', ['You are genderless'])
    _testTag(k, 'condition test #5', 'test condition', ['You are genderless'])
    k.setPredicate('gender', 'male')
    _testTag(k, 'condition test #6', 'test condition', ['You are handsome'])

    # the date test will occasionally fail if the original and "test"
    # times cross a second boundary.  There's no good way to avoid
    # this problem and still do a meaningful test, so we simply
    # provide a friendly message to be printed if the test fails.
    date_warning = """
    NOTE: the <date> test will occasionally report failure even if it
    succeeds.  So long as the response looks like a date/time string,
    there's nothing to worry about.
    """
    if not _testTag(k, 'date', 'test date', ["The date is %s" % time.asctime()]):
        print date_warning

    _testTag(k, 'formal', 'test formal', ["Formal Test Passed"])
    _testTag(k, 'gender', 'test gender', ["He'd told her he heard that her hernia is history"])
    _testTag(k, 'get/set', 'test get and set', ["I like cheese. My favorite food is cheese"])
    _testTag(k, 'gossip', 'test gossip', ["Gossip is not yet implemented"])
    _testTag(k, 'id', 'test id', ["Your id is _global"])
    _testTag(k, 'input', 'test input', ['You just said: test input'])
    _testTag(k, 'javascript', 'test javascript', ["Javascript is not yet implemented"])
    _testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
    _testTag(k, 'person', 'test person', ['HE think i knows that my actions threaten him and his.'])
    _testTag(k, 'person2', 'test person2', ['YOU think me know that my actions threaten you and yours.'])
    _testTag(k, 'person2 (no contents)', 'test person2 I Love Lucy', ['YOU Love Lucy'])
    _testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
    _testTag(k, 'random empty', 'test random empty', ["Nothing here!"])
    _testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
    _testTag(k, 'size', "test size", ["I've learned %d categories" % k.numCategories()])
    _testTag(k, 'sr', "test sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'sr nested', "test nested sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'srai', "test srai", ["srai test passed"])
    _testTag(k, 'srai infinite', "test srai infinite", [""])
    _testTag(k, 'star test #1', 'You should test star begin', ['Begin star matched: You should'])
    _testTag(k, 'star test #2', 'test star creamy goodness middle', ['Middle star matched: creamy goodness'])
    _testTag(k, 'star test #3', 'test star end the credits roll', ['End star matched: the credits roll'])
    _testTag(k, 'star test #4', 'test star having multiple stars in a pattern makes me extremely happy',
             ['Multiple stars matched: having, stars in a pattern, extremely happy'])
    _testTag(k, 'system', "test system", ["The system says hello!"])
    _testTag(k, 'that test #1', "test that", ["I just said: The system says hello!"])
    _testTag(k, 'that test #2', "test that", ["I have already answered this question"])
    _testTag(k, 'thatstar test #1', "test thatstar", ["I say beans"])
    _testTag(k, 'thatstar test #2', "test thatstar", ["I just said \"beans\""])
    _testTag(k, 'thatstar test #3', "test thatstar multiple", ['I say beans and franks for everybody'])
    _testTag(k, 'thatstar test #4', "test thatstar multiple", ['Yes, beans and franks for all!'])
    _testTag(k, 'think', "test think", [""])
    k.setPredicate("topic", "fruit")
    _testTag(k, 'topic', "test topic", ["We were discussing apples and oranges"])
    k.setPredicate("topic", "Soylent Green")
    _testTag(k, 'topicstar test #1', 'test topicstar', ["Solyent Green is made of people!"])
    k.setPredicate("topic", "Soylent Ham and Cheese")
    _testTag(k, 'topicstar test #2', 'test topicstar multiple', ["Both Soylents Ham and Cheese are made of people!"])
    _testTag(k, 'unicode support', u"���Ϻ�", [u"Hey, you speak Chinese! ���Ϻ�"])
    _testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
    _testTag(k, 'version', 'test version', ["PyAIML is version %s" % k.version()])
    _testTag(k, 'whitespace preservation', 'test whitespace', ["Extra   Spaces\n   Rule!   (but not in here!)    But   Here   They   Do!"])

    # Report test results
    print "--------------------"
    if _numTests == _numPassed:
        print "%d of %d tests passed!" % (_numPassed, _numTests)
    else:
        print "%d of %d tests passed (see above for detailed errors)" % (_numPassed, _numTests)

    # Run an interactive interpreter
    #print "\nEntering interactive mode (ctrl-c to exit)"
    #while True: print k.respond(raw_input("> "))

########NEW FILE########
__FILENAME__ = LangSupport
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def isChinese(c):
    # http://www.iteye.com/topic/558050

    r = [
        # 标准CJK文字
        (0x3400, 0x4DB5), (0x4E00, 0x9FA5), (0x9FA6, 0x9FBB), (0xF900, 0xFA2D),
        (0xFA30, 0xFA6A), (0xFA70, 0xFAD9), (0x20000, 0x2A6D6), (0x2F800, 0x2FA1D),
        # 全角ASCII、全角中英文标点、半宽片假名、半宽平假名、半宽韩文字母
        (0xFF00, 0xFFEF),
        # CJK部首补充
        (0x2E80, 0x2EFF),
        # CJK标点符号
        (0x3000, 0x303F),
        # CJK笔划
        (0x31C0, 0x31EF)]
    return any(s <= ord(c) <= e for s, e in r)

def splitChinese(s):

    result = []
    for c in s:
        if isChinese(c):
            result.extend([" ", c, " "])
        else:
            result.append(c)
    ret = ''.join(result)
    return ret.split()


def splitUnicode(s):
    assert type(s) == unicode, "string must be a unicode"
    segs = s.split()
    result = []
    for seg in segs:
        if any(map(isChinese, seg)):
            result.extend(splitChinese(seg))
        else:
            result.append(seg)
    return result

def mergeChineseSpace(s):
    assert type(s) == unicode, "string must be a unicode"
    segs = splitChinese(s)
    result = []
    for seg in segs:
        # English marks
        if seg[0] not in ".,?!":
            try:
                str(seg[0]) and result.append(" ")
            except:
                pass
        result.append(seg)
        try:
            str(seg[-1]) and result.append(" ")
        except:
            pass
    return u''.join(result).strip()

########NEW FILE########
__FILENAME__ = PatternMgr
# This class implements the AIML pattern-matching algorithm described
# by Dr. Richard Wallace at the following site:
# http://www.alicebot.org/documentation/matching.html

import marshal
import pprint
import re
import string
import sys

class PatternMgr:
        # special dictionary keys
        _UNDERSCORE = 0
        _STAR       = 1
        _TEMPLATE   = 2
        _THAT       = 3
        _TOPIC		= 4
        _BOT_NAME   = 5

        def __init__(self):
                self._root = {}
                self._templateCount = 0
                self._botName = u"Nameless"
                punctuation = u"\"`~!@#$%^&*()-_=+[{]}\|;:',<.>/?"
                self._puncStripRE = re.compile("[" + re.escape(punctuation) + "]", re.U) # FIXED: chinese unicode
                self._whitespaceRE = re.compile("\s+", re.LOCALE | re.UNICODE)

        def numTemplates(self):
                """Return the number of templates currently stored."""
                return self._templateCount

        def setBotName(self, name):
                """Set the name of the bot, used to match <bot name="name"> tags in
                patterns.  The name must be a single word!

                """
                # Collapse a multi-word name into a single word
                self._botName = unicode(string.join(name.split()))

        def dump(self):
                """Print all learned patterns, for debugging purposes."""
                pprint.pprint(self._root)

        def dumps(self):
                """Dump current patterns to a string for saving."""
                try:
                        data = [self._templateCount, self._botName, self._root]
                        return marshal.dumps(data)
                except Exception, e:
                        print "Error dumping to str"
                        raise Exception, e

        def loads(self, raw):
                """Load patterns from a previously dumps()d patterns."""
                try:
                        data = marshal.loads(raw)
                        self._templateCount = data[0]
                        self._botName = data[1]
                        self._root = data[2]
                except Exception, e:
                        print "Error loading from str"
                        raise Exception, e

        def save(self, filename):
                """Dump the current patterns to the file specified by filename.  To
                restore later, use restore().

                """
                try:
                        outFile = open(filename, "wb")
                        marshal.dump(self._templateCount, outFile)
                        marshal.dump(self._botName, outFile)
                        marshal.dump(self._root, outFile)
                        outFile.close()
                except Exception, e:
                        print "Error saving PatternMgr to file %s:" % filename
                        raise Exception, e

        def restore(self, filename):
                """Restore a previously save()d collection of patterns."""
                try:
                        inFile = open(filename, "rb")
                        self._templateCount = marshal.load(inFile)
                        self._botName = marshal.load(inFile)
                        self._root = marshal.load(inFile)
                        inFile.close()
                except Exception, e:
                        print "Error restoring PatternMgr from file %s:" % filename
                        raise Exception, e

        def add(self, (pattern,that,topic), template):
                """Add a [pattern/that/topic] tuple and its corresponding template
                to the node tree.

                """
                # TODO: make sure words contains only legal characters
                # (alphanumerics,*,_)

                # Navigate through the node tree to the template's location, adding
                # nodes if necessary.
                node = self._root
                for word in string.split(pattern):
                        key = word
                        if key == u"_":
                                key = self._UNDERSCORE
                        elif key == u"*":
                                key = self._STAR
                        elif key == u"BOT_NAME":
                                key = self._BOT_NAME
                        if not node.has_key(key):
                                node[key] = {}
                        node = node[key]

                # navigate further down, if a non-empty "that" pattern was included
                if len(that) > 0:
                        if not node.has_key(self._THAT):
                                node[self._THAT] = {}
                        node = node[self._THAT]
                        for word in string.split(that):
                                key = word
                                if key == u"_":
                                        key = self._UNDERSCORE
                                elif key == u"*":
                                        key = self._STAR
                                if not node.has_key(key):
                                        node[key] = {}
                                node = node[key]

                # navigate yet further down, if a non-empty "topic" string was included
                if len(topic) > 0:
                        if not node.has_key(self._TOPIC):
                                node[self._TOPIC] = {}
                        node = node[self._TOPIC]
                        for word in string.split(topic):
                                key = word
                                if key == u"_":
                                        key = self._UNDERSCORE
                                elif key == u"*":
                                        key = self._STAR
                                if not node.has_key(key):
                                        node[key] = {}
                                node = node[key]


                # add the template.
                if not node.has_key(self._TEMPLATE):
                        self._templateCount += 1
                node[self._TEMPLATE] = template

        def match(self, pattern, that, topic):
                """Return the template which is the closest match to pattern. The
                'that' parameter contains the bot's previous response. The 'topic'
                parameter contains the current topic of conversation.

                Returns None if no template is found.

                """
                if len(pattern) == 0:
                        return None
                # Mutilate the input.  Remove all punctuation and convert the
                # text to all caps.
                input = string.upper(pattern)
                input = re.sub(self._puncStripRE, " ", input)
                if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT" # 'that' must never be empty
                thatInput = string.upper(that)
                thatInput = re.sub(self._puncStripRE, " ", thatInput)
                thatInput = re.sub(self._whitespaceRE, " ", thatInput)
                if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC" # 'topic' must never be empty
                topicInput = string.upper(topic)
                topicInput = re.sub(self._puncStripRE, " ", topicInput)
                # Pass the input off to the recursive call
                patMatch, template = self._match(input.split(), thatInput.split(), topicInput.split(), self._root)
                return template

        def star(self, starType, pattern, that, topic, index):
                """Returns a string, the portion of pattern that was matched by a *.

                The 'starType' parameter specifies which type of star to find.
                Legal values are:
                 - 'star': matches a star in the main pattern.
                 - 'thatstar': matches a star in the that pattern.
                 - 'topicstar': matches a star in the topic pattern.

                """
                # Mutilate the input.  Remove all punctuation and convert the
                # text to all caps.
                input = string.upper(pattern)
                input = re.sub(self._puncStripRE, " ", input)
                input = re.sub(self._whitespaceRE, " ", input)
                if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT" # 'that' must never be empty
                thatInput = string.upper(that)
                thatInput = re.sub(self._puncStripRE, " ", thatInput)
                thatInput = re.sub(self._whitespaceRE, " ", thatInput)
                if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC" # 'topic' must never be empty
                topicInput = string.upper(topic)
                topicInput = re.sub(self._puncStripRE, " ", topicInput)
                topicInput = re.sub(self._whitespaceRE, " ", topicInput)

                # Pass the input off to the recursive pattern-matcher
                patMatch, template = self._match(input.split(), thatInput.split(), topicInput.split(), self._root)
                if template == None:
                        return ""

                # Extract the appropriate portion of the pattern, based on the
                # starType argument.
                words = None
                if starType == 'star':
                        patMatch = patMatch[:patMatch.index(self._THAT)]
                        words = input.split()
                elif starType == 'thatstar':
                        patMatch = patMatch[patMatch.index(self._THAT)+1 : patMatch.index(self._TOPIC)]
                        words = thatInput.split()
                elif starType == 'topicstar':
                        patMatch = patMatch[patMatch.index(self._TOPIC)+1 :]
                        words = topicInput.split()
                else:
                        # unknown value
                        raise ValueError, "starType must be in ['star', 'thatstar', 'topicstar']"
                # compare the input string to the matched pattern, word by word.
                # At the end of this loop, if foundTheRightStar is true, start and
                # end will contain the start and end indices (in "words") of
                # the substring that the desired star matched.
                foundTheRightStar = False
                start = end = j = numStars = k = 0
                for i in range(len(words)):
                        # This condition is true after processing a star
                        # that ISN'T the one we're looking for.
                        if i < k:
                                continue
                        # If we're reached the end of the pattern, we're done.
                        if j == len(patMatch):
                                break
                        if not foundTheRightStar:
                                if patMatch[j] in [self._STAR, self._UNDERSCORE]: #we got a star
                                        numStars += 1
                                        if numStars == index:
                                                # This is the star we care about.
                                                foundTheRightStar = True
                                        start = i
                                        # Iterate through the rest of the string.
                                        for k in range (i, len(words)):
                                                # If the star is at the end of the pattern,
                                                # we know exactly where it ends.
                                                if j+1  == len (patMatch):
                                                        end = len (words)
                                                        break
                                                # If the words have started matching the
                                                # pattern again, the star has ended.
                                                # FIXED: for pattch "* A B", "A C A B" will match
                                                # and this is a bug
                                                if patMatch[j+1] == words[k]:
                                                        tj = j+1 + 1
                                                        tk = k + 1
                                                        ok = True
                                                        while tj < len(patMatch) and tk < len(words):
                                                                if patMatch[tj] in [self._STAR, self._UNDERSCORE]:
                                                                        break
                                                                if patMatch[tj] != words[tk]:
                                                                        ok = False
                                                                        break
                                                                tj += 1
                                                                tk += 1
                                                        if ok:
                                                                end = k - 1
                                                                i = k
                                                                break
                                # If we just finished processing the star we cared
                                # about, we exit the loop early.
                                if foundTheRightStar:
                                        break
                        # Move to the next element of the pattern.
                        j += 1

                # extract the star words from the original, unmutilated input.
                if foundTheRightStar:
                        if starType == 'star': return string.join(pattern.split()[start:end+1])
                        elif starType == 'thatstar': return string.join(that.split()[start:end+1])
                        elif starType == 'topicstar': return string.join(topic.split()[start:end+1])
                else: return ""

        def _match(self, words, thatWords, topicWords, root):
                """Return a tuple (pat, tem) where pat is a list of nodes, starting
                at the root and leading to the matching pattern, and tem is the
                matched template.

                """
                # base-case: if the word list is empty, return the current node's
                # template.
                if len(words) == 0:
                        # we're out of words.
                        pattern = []
                        template = None
                        if len(thatWords) > 0:
                                # If thatWords isn't empty, recursively
                                # pattern-match on the _THAT node with thatWords as words.
                                try:
                                        pattern, template = self._match(thatWords, [], topicWords, root[self._THAT])
                                        if pattern != None:
                                                pattern = [self._THAT] + pattern
                                except KeyError:
                                        pattern = []
                                        template = None
                        elif len(topicWords) > 0:
                                # If thatWords is empty and topicWords isn't, recursively pattern
                                # on the _TOPIC node with topicWords as words.
                                try:
                                        pattern, template = self._match(topicWords, [], [], root[self._TOPIC])
                                        if pattern != None:
                                                pattern = [self._TOPIC] + pattern
                                except KeyError:
                                        pattern = []
                                        template = None
                        if template == None:
                                # we're totally out of input.  Grab the template at this node.
                                pattern = []
                                try: template = root[self._TEMPLATE]
                                except KeyError: template = None
                        return (pattern, template)

                first = words[0]
                suffix = words[1:]

                # Check underscore.
                # Note: this is causing problems in the standard AIML set, and is
                # currently disabled.
                if root.has_key(self._UNDERSCORE):
                        # Must include the case where suf is [] in order to handle the case
                        # where a * or _ is at the end of the pattern.
                        for j in range(len(suffix)+1):
                                suf = suffix[j:]
                                pattern, template = self._match(suf, thatWords, topicWords, root[self._UNDERSCORE])
                                if template is not None:
                                        newPattern = [self._UNDERSCORE] + pattern
                                        return (newPattern, template)

                # Check first
                if root.has_key(first):
                        pattern, template = self._match(suffix, thatWords, topicWords, root[first])
                        if template is not None:
                                newPattern = [first] + pattern
                                return (newPattern, template)

                # check bot name
                if root.has_key(self._BOT_NAME) and first == self._botName:
                        pattern, template = self._match(suffix, thatWords, topicWords, root[self._BOT_NAME])
                        if template is not None:
                                newPattern = [first] + pattern
                                return (newPattern, template)

                # check star
                if root.has_key(self._STAR):
                        # Must include the case where suf is [] in order to handle the case
                        # where a * or _ is at the end of the pattern.
                        for j in range(len(suffix)+1):
                                suf = suffix[j:]
                                pattern, template = self._match(suf, thatWords, topicWords, root[self._STAR])
                                if template is not None:
                                        newPattern = [self._STAR] + pattern
                                        return (newPattern, template)

                # No matches were found.
                return (None, None)

########NEW FILE########
__FILENAME__ = Utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from LangSupport import splitChinese

"""This file contains assorted general utility functions used by other
modules in the PyAIML package.

"""

# TODO: andelf, add chinese sentence support
def sentences(s):
    """Split the string s into a list of sentences."""
    try: s+""
    except: raise TypeError, "s must be a string"
    pos = 0
    sentenceList = []
    l = len(s)
    while pos < l:
        try: p = s.index('.', pos)
        except: p = l+1
        try: q = s.index('?', pos)
        except: q = l+1
        try: e = s.index('!', pos)
        except: e = l+1
        end = min(p,q,e)
        sentenceList.append( s[pos:end].strip() )
        pos = end+1
    # If no sentences were found, return a one-item list containing
    # the entire input string.
    if len(sentenceList) == 0: sentenceList.append(s)
    # auto convert chinese
    return map(lambda s: u' '.join(splitChinese(s)), sentenceList)

# Self test
if __name__ == "__main__":
    # sentences
    sents = sentences("First.  Second, still?  Third and Final!  Well, not really")
    assert(len(sents) == 4)

########NEW FILE########
__FILENAME__ = WordSub
"""This module implements the WordSub class, modelled after a recipe
in "Python Cookbook" (Recipe 3.14, "Replacing Multiple Patterns in a
Single Pass" by Xavier Defrang).

Usage:
Use this class like a dictionary to add before/after pairs:
    > subber = TextSub()
    > subber["before"] = "after"
    > subber["begin"] = "end"
Use the sub() method to perform the substitution:
    > print subber.sub("before we begin")
    after we end
All matching is intelligently case-insensitive:
    > print subber.sub("Before we BEGIN")
    After we END
The 'before' words must be complete words -- no prefixes.
The following example illustrates this point:
    > subber["he"] = "she"
    > print subber.sub("he says he'd like to help her")
    she says she'd like to help her
Note that "he" and "he'd" were replaced, but "help" and "her" were
not.
"""

# 'dict' objects weren't available to subclass from until version 2.2.
# Get around this by importing UserDict.UserDict if the built-in dict
# object isn't available.
try: dict
except: from UserDict import UserDict as dict

import ConfigParser
import re
import string

class WordSub(dict):
    """All-in-one multiple-string-substitution class."""

    def _wordToRegex(self, word):
        """Convert a word to a regex object which matches the word."""
        if word != "" and word[0].isalpha() and word[-1].isalpha():
            return "\\b%s\\b" % re.escape(word)
        else: 
            return r"\b%s\b" % re.escape(word)
    
    def _update_regex(self):
        """Build re object based on the keys of the current
        dictionary.

        """
        self._regex = re.compile("|".join(map(self._wordToRegex, self.keys())))
        self._regexIsDirty = False

    def __init__(self, defaults = {}):
        """Initialize the object, and populate it with the entries in
        the defaults dictionary.

        """
        self._regex = None
        self._regexIsDirty = True
        for k,v in defaults.items():
            self[k] = v

    def __call__(self, match):
        """Handler invoked for each regex match."""
        return self[match.group(0)]

    def __setitem__(self, i, y):
        self._regexIsDirty = True
        # for each entry the user adds, we actually add three entrys:
        super(type(self),self).__setitem__(string.lower(i),string.lower(y)) # key = value
        super(type(self),self).__setitem__(string.capwords(i), string.capwords(y)) # Key = Value
        super(type(self),self).__setitem__(string.upper(i), string.upper(y)) # KEY = VALUE

    def sub(self, text):
        """Translate text, returns the modified text."""
        if self._regexIsDirty:
            self._update_regex()
        return self._regex.sub(self, text)

# self-test
if __name__ == "__main__":
    subber = WordSub()
    subber["apple"] = "banana"
    subber["orange"] = "pear"
    subber["banana" ] = "apple"
    subber["he"] = "she"
    subber["I'd"] = "I would"

    # test case insensitivity
    inStr =  "I'd like one apple, one Orange and one BANANA."
    outStr = "I Would like one banana, one Pear and one APPLE."
    if subber.sub(inStr) == outStr: print "Test #1 PASSED"    
    else: print "Test #1 FAILED: '%s'" % subber.sub(inStr)

    inStr = "He said he'd like to go with me"
    outStr = "She said she'd like to go with me"
    if subber.sub(inStr) == outStr: print "Test #2 PASSED"    
    else: print "Test #2 FAILED: '%s'" % subber.sub(inStr)

########NEW FILE########
__FILENAME__ = simple
import sys
sys.path.insert(0, "../")

import aiml

# The Kernel object is the public interface to
# the AIML interpreter.
k = aiml.Kernel()

# Use the 'learn' method to load the contents
# of an AIML file into the Kernel.
k.learn("cn-startup.xml")

# Use the 'respond' method to compute the response
# to a user's input string.  respond() returns
# the interpreter's response, which in this case
# we ignore.
k.respond("load aiml cn")

# Loop forever, reading user input from the command
# line and printing responses.
while True: print k.respond(raw_input("> "))

########NEW FILE########
__FILENAME__ = getweather
#!/usr/bin/env python
# -*- coding: utf-8 -*-


# http://toy.weather.com.cn/SearchBox/searchBox?_=1362892474803&language=zh&keyword=%E5%8C%97%E4%BA%AC

import urllib
import sys
import json

ENCODING = 'utf-8'


def queryLocation(term):
    term = term.encode(ENCODING) if type(term) == unicode else term
    url = "http://toy.weather.com.cn/SearchBox/searchBox?language=zh&keyword=" + urllib.quote(term)
    resp = urllib.urlopen(url)
    data = json.load(resp)
    if not data:
        print u"找不到地点".encode(ENCODING)
    for d in data["i"]:
        code = d['i']
        break
    return code

def queryRealTimeWeatherInfo(code):
    #url = "http://m.weather.com.cn/data/%s.html" % code
    url = "http://www.weather.com.cn/data/sk/%s.html" % code
    resp = urllib.urlopen(url)
    data = json.load(resp)
    if not data:
        print u"天气预报还没出来".encode(ENCODING)
    return data['weatherinfo']

def showRealTimeWeatherInfo(info):
    template = u"{city} {time} 天气实况: 气温{temp}℃, {WD}{WS}, 湿度{SD}"
    print template.format(**info).encode(ENCODING)


def main():
    assert len(sys.argv) >= 3
    function = sys.argv[1]
    term = ''.join(sys.argv[2:])
    if function == 'realtime':
        # 实时
        showRealTimeWeatherInfo(queryRealTimeWeatherInfo(queryLocation(term)))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = simple
#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
sys.path.insert(0, "../")

import aiml

# The Kernel object is the public interface to
# the AIML interpreter.
k = aiml.Kernel()

# Use the 'learn' method to load the contents
# of an AIML file into the Kernel.
k.learn("cn-startup.xml")

# Use the 'respond' method to compute the response
# to a user's input string.  respond() returns
# the interpreter's response, which in this case
# we ignore.
k.respond("load aiml cnask")

# Loop forever, reading user input from the command
# line and printing responses.
while True: print k.respond(raw_input("> "))

########NEW FILE########
__FILENAME__ = continue
import sys
sys.path.insert(0, "../")
import shelve

import aiml
import copy

# use any dict like obj here
db = copy.deepcopy(dict(shelve.open("session.db", "c")))
# The Kernel object is the public interface to
# the AIML interpreter.

k = aiml.Kernel(sessionStore=db)

# load from a saved brain
k.restoreBrain("brain.sav")

# Loop forever, reading user input from the command
# line and printing responses.
while True:
    print k.respond(raw_input("> "))
    #db.sync()

########NEW FILE########
__FILENAME__ = start
import sys
import atexit
sys.path.insert(0, "../")
import shelve

import aiml


db = shelve.open("session.db", "c", writeback=True)

atexit.register(lambda : k.saveBrain('brain.sav'))

# The Kernel object is the public interface to
# the AIML interpreter.
k = aiml.Kernel(sessionStore=db)

# Use the 'learn' method to load the contents
# of an AIML file into the Kernel.
k.learn("cn-startup.xml")

# Use the 'respond' method to compute the response
# to a user's input string.  respond() returns
# the interpreter's response, which in this case
# we ignore.
k.respond("load aiml cn")


# Loop forever, reading user input from the command
# line and printing responses.
while True:
    print k.respond(raw_input("> "))
    db.sync()

########NEW FILE########
__FILENAME__ = learn


import sys
sys.path.insert(0, "../")
import codecs
import shelve

from aiml.LangSupport import mergeChineseSpace


db = shelve.open("simple_rules.db", "c", writeback=True)

template = """<?xml version="1.0" encoding="UTF-8"?>
<aiml version="1.0">

<meta name="author" content="autogen"/>
<meta name="language" content="zh"/>
{rules}
</aiml>
"""

category_template = """
<category>
<pattern>{pattern}</pattern>
<template>
{answer}
</template>
</category>
"""

#print sys.argv
if len(sys.argv) == 3:
    _, rule, temp = sys.argv
    rule = mergeChineseSpace(unicode(rule, 'utf8')).encode('utf8')
    temp = mergeChineseSpace(unicode(temp, 'utf8')).encode('utf8')
    db[rule] = temp
    db.sync()
    rules = []
    for r in db:
        rules.append(category_template.format(pattern=r,
                                              answer=db[r]))
    content = template.format(rules = '\n'.join(rules))
    with open("auto-gen.aiml", 'w') as fp:
        fp.write(content)

########NEW FILE########
__FILENAME__ = simple
import sys
sys.path.insert(0, "../")

import aiml

# The Kernel object is the public interface to
# the AIML interpreter.
k = aiml.Kernel()

k.loadSubs('./subbers.ini')

# Use the 'learn' method to load the contents
# of an AIML file into the Kernel.
k.learn("cn-startup.xml")


# Use the 'respond' method to compute the response
# to a user's input string.  respond() returns
# the interpreter's response, which in this case
# we ignore.
k.respond("load aiml cn")

# Loop forever, reading user input from the command
# line and printing responses.
while True: print k.respond(raw_input("> "))

########NEW FILE########
