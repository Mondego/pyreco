__FILENAME__ = engine
# CSSPrefixer
# Copyright 2010-2012 Greg V. <floatboth@me.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cssutils
import re
from rules import rules as tr_rules
from rules import prefixRegex


keyframesRegex = re.compile(r'@keyframes\s?\w+\s?{(.*)}')
blockRegex = re.compile(r'\w+\s?\{(.*)\}')


def magic(ruleset, debug, minify, filt, parser):
    if isinstance(ruleset, cssutils.css.CSSUnknownRule):
        if ruleset.cssText.startswith('@keyframes'):
            inner = parser.parseString(keyframesRegex.split(ruleset.cssText.replace('\n', ''))[1])
            # BUG: doesn't work when minified
            s = '' if minify else '\n'
            return '@-webkit-keyframes {' + s + \
            ''.join([magic(rs, debug, minify, ['webkit'], parser) for rs in inner]) \
            + '}' + s + '@-moz-keyframes {' + s + \
            ''.join([magic(rs, debug, minify, ['moz'], parser) for rs in inner]) \
            + '}' + s + ruleset.cssText
        elif ruleset.cssText.startswith('from') or ruleset.cssText.startswith('to'):
            return ''.join([magic(rs, debug, minify, filt, parser)
                for rs in parser.parseString(blockRegex.sub(r'\1', ruleset.cssText.replace('\n', ''))[1])])
        else:
            return
    elif hasattr(ruleset, 'style'):  # Comments don't
        ruleSet = set()
        rules = list()
        children = list(ruleset.style.children())
        ruleset.style = cssutils.css.CSSStyleDeclaration()  # clear out the styles that were there
        for rule in children:
            if not hasattr(rule, 'name'):  # comments don't have name
                rules.append(rule)
                continue
            name = prefixRegex.sub('', rule.name)
            if name in tr_rules:
                rule.name = name
            if rule.cssText in ruleSet:
                continue
            ruleSet.add(rule.cssText)
            rules.append(rule)

        ruleset.style.seq._readonly = False
        for rule in rules:
            if not hasattr(rule, 'name'):
                ruleset.style.seq.append(rule, 'Comment')
                continue
            processor = None
            try:  # try except so if anything goes wrong we don't lose the original property
                if rule.name in tr_rules:
                    processor = tr_rules[rule.name](rule)
                    [ruleset.style.seq.append(prop, 'Property') for prop in processor.get_prefixed_props(filt) if prop]
                # always add the original rule
                if processor and hasattr(processor, 'get_base_prop'):
                    ruleset.style.seq.append(processor.get_base_prop(), 'Property')
                else:
                    ruleset.style.seq.append(rule, 'Property')
            except:
                if debug:
                    print 'warning with ' + str(rule)
                ruleset.style.seq.append(rule, 'Property')
        ruleset.style.seq._readonly = True
    elif hasattr(ruleset, 'cssRules'):
        for subruleset in ruleset:
            magic(subruleset, debug, minify, filt, parser)
    cssText = ruleset.cssText
    if not cssText:  # blank rules return None so return an empty string
        return
    if minify or not hasattr(ruleset, 'style'):
        return unicode(cssText)
    return unicode(cssText) + '\n'


def process(string, debug=False, minify=False, filt=['webkit', 'moz', 'o', 'ms'], **prefs):
    loglevel = 'DEBUG' if debug else 'ERROR'
    parser = cssutils.CSSParser(loglevel=loglevel)
    if minify:
        cssutils.ser.prefs.useMinified()
    else:
        cssutils.ser.prefs.useDefaults()

    # use the passed in prefs
    for key, value in prefs.iteritems():
        if hasattr(cssutils.ser.prefs, key):
            cssutils.ser.prefs.__dict__[key] = value

    results = []
    sheet = parser.parseString(string)
    for ruleset in sheet.cssRules:
        cssText = magic(ruleset, debug, minify, filt, parser)
        if cssText:
            results.append(cssText)

    # format with newlines based on minify
    joinStr = '' if minify else '\n'

    # Not using sheet.cssText - it's buggy:
    # it skips some prefixed properties.
    return joinStr.join(results).rstrip()

__all__ = ['process']
########NEW FILE########
__FILENAME__ = rules
# CSSPrefixer
# Copyright 2010-2012 Greg V. <floatboth@me.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import cssutils

prefixRegex = re.compile('^(-o-|-ms-|-moz-|-webkit-)')


class BaseReplacementRule(object):
    vendor_prefixes = ['moz', 'webkit']

    def __init__(self, prop):
        self.prop = prop

    def get_prefixed_props(self, filt):
        for prefix in [p for p in self.vendor_prefixes if p in filt]:
            yield cssutils.css.Property(
                    name='-%s-%s' % (prefix, self.prop.name),
                    value=self.prop.value,
                    priority=self.prop.priority
                    )

    @staticmethod
    def should_prefix():
        return True


class FullReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['o', 'ms'])


class BaseAndIEReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['ms'])


class BaseAndOperaReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['o'])


class WebkitReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['webkit']


class OperaAndIEReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['ms', 'o']


class MozReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz']


class BorderRadiusReplacementRule(BaseReplacementRule):
    """
    Mozilla's Gecko engine uses different syntax for rounded corners.
    """
    vendor_prefixes = ['webkit']

    def get_prefixed_props(self, filt):
        for prop in BaseReplacementRule.get_prefixed_props(self, filt):
            yield prop
        if 'moz' in filt:
            name = '-moz-' + self.prop.name.replace('top-left-radius', 'radius-topleft') \
                   .replace('top-right-radius', 'radius-topright') \
                   .replace('bottom-right-radius', 'radius-bottomright') \
                   .replace('bottom-left-radius', 'radius-bottomleft')
            yield cssutils.css.Property(
                    name=name,
                    value=self.prop.value,
                    priority=self.prop.priority
                    )


class CursorReplacementRule(BaseReplacementRule):
    """
    Experimental cursor values.
    """
    def get_prefixed_props(self, filt):
        if self.prop.value in ('zoom-in', 'zoom-out'):
            for prefix in [p for p in self.vendor_prefixes if p in filt]:
                yield cssutils.css.Property(
                        name='cursor',
                        value='-%s-%s' % (prefix, self.prop.value),
                        priority=self.prop.priority
                        )


class DisplayReplacementRule(BaseReplacementRule):
    """
    Flexible Box Model stuff.
    CSSUtils parser doesn't support duplicate properties, so that's dirty.
    """
    def get_prefixed_props(self, filt):
        if self.prop.value == 'box':  # only add prefixes if the value is box
            for prefix in [p for p in self.vendor_prefixes if p in filt]:
                yield cssutils.css.Property(
                        name='display',
                        value='-%s-box' % prefix,
                        priority=self.prop.priority
                        )


class TransitionReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz', 'o', 'webkit']

    def __get_prefixed_prop(self, prefix=None):
        name = self.prop.name
        if prefix:
            name = '-%s-%s' % (prefix, self.prop.name)
        newValues = []
        for value in self.prop.value.split(','):
            parts = value.strip().split(' ')
            parts[0] = prefixRegex.sub('', parts[0])
            if parts[0] in rules and prefix and rules[parts[0]].should_prefix():
                parts[0] = '-%s-%s' % (prefix, parts[0])
            newValues.append(' '.join(parts))
        return cssutils.css.Property(
                name=name,
                value=', '.join(newValues),
                priority=self.prop.priority
                )

    def get_prefixed_props(self, filt):
        for prefix in [p for p in self.vendor_prefixes if p in filt]:
            yield self.__get_prefixed_prop(prefix)

    def get_base_prop(self):
        return self.__get_prefixed_prop()


class GradientReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz', 'o', 'webkit']

    def __iter_values(self):
        valueSplit = self.prop.value.split(',')
        index = 0
        # currentString = ''
        while(True):
            if index >= len(valueSplit):
                break
            rawValue = valueSplit[index].strip()
            snip = prefixRegex.sub('', rawValue)
            if snip.startswith('linear-gradient'):
                values = [re.sub('^linear-gradient\(', '', snip)]
                if valueSplit[index + 1].strip().endswith(')'):
                    values.append(re.sub('\)+$', '', valueSplit[index + 1].strip()))
                else:
                    values.append(valueSplit[index + 1].strip())
                    values.append(re.sub('\)+$', '', valueSplit[index + 2].strip()))
                if len(values) == 2:
                    yield {
                        'start': values[0],
                        'end': values[1]
                        }
                else:
                    yield {
                        'pos': values[0],
                        'start': values[1],
                        'end': values[2]
                        }
                index += len(values)
            elif snip.startswith('gradient'):
                yield {
                    'start': re.sub('\)+$', '', valueSplit[index + 4].strip()),
                    'end': re.sub('\)+$', '', valueSplit[index + 6].strip()),
                    }
                index += 7
            else:
                # not a gradient so just yield the raw string
                yield rawValue
                index += 1

    def __get_prefixed_prop(self, values, prefix=None):
        gradientName = 'linear-gradient'
        if prefix:
            gradientName = '-%s-%s' % (prefix, gradientName)
        newValues = []
        for value in values:
            if isinstance(value, dict):
                if 'pos' in value:
                    newValues.append(gradientName + '(%(pos)s, %(start)s, %(end)s)' % value)
                else:
                    newValues.append(gradientName + '(%(start)s, %(end)s)' % value)
            else:
                newValues.append(value)
        return cssutils.css.Property(
                name=self.prop.name,
                value=', '.join(newValues),
                priority=self.prop.priority
                )

    def get_prefixed_props(self, filt):
        values = list(self.__iter_values())
        needPrefix = False
        for value in values:  # check if there are any gradients
            if isinstance(value, dict):
                needPrefix = True
                break
        if needPrefix:
            for prefix in [p for p in self.vendor_prefixes if p in filt]:
                yield self.__get_prefixed_prop(values, prefix)
                if prefix == 'webkit':
                    newValues = []
                    for value in values:
                        if isinstance(value, dict):
                            newValues.append('-webkit-gradient(linear, left top, left bottom, color-stop(0, %(start)s), color-stop(1, %(end)s))' % value)
                        else:
                            newValues.append(value)
                    yield cssutils.css.Property(
                            name=self.prop.name,
                            value=', '.join(newValues),
                            priority=self.prop.priority
                            )
        else:
            yield None

    def get_base_prop(self):
        values = self.__iter_values()
        return self.__get_prefixed_prop(values)

rules = {
    'border-radius': BaseReplacementRule,
    'border-top-left-radius': BorderRadiusReplacementRule,
    'border-top-right-radius': BorderRadiusReplacementRule,
    'border-bottom-right-radius': BorderRadiusReplacementRule,
    'border-bottom-left-radius': BorderRadiusReplacementRule,
    'border-image': FullReplacementRule,
    'box-shadow': BaseReplacementRule,
    'box-sizing': MozReplacementRule,
    'box-orient': BaseAndIEReplacementRule,
    'box-direction': BaseAndIEReplacementRule,
    'box-ordinal-group': BaseAndIEReplacementRule,
    'box-align': BaseAndIEReplacementRule,
    'box-flex': BaseAndIEReplacementRule,
    'box-flex-group': BaseReplacementRule,
    'box-pack': BaseAndIEReplacementRule,
    'box-lines': BaseAndIEReplacementRule,
    'user-select': BaseReplacementRule,
    'user-modify': BaseReplacementRule,
    'margin-start': BaseReplacementRule,
    'margin-end': BaseReplacementRule,
    'padding-start': BaseReplacementRule,
    'padding-end': BaseReplacementRule,
    'column-count': BaseReplacementRule,
    'column-gap': BaseReplacementRule,
    'column-rule': BaseReplacementRule,
    'column-rule-color': BaseReplacementRule,
    'column-rule-style': BaseReplacementRule,
    'column-rule-width': BaseReplacementRule,
    'column-span': WebkitReplacementRule,
    'column-width': BaseReplacementRule,
    'columns': WebkitReplacementRule,

    'background-clip': WebkitReplacementRule,
    'background-origin': WebkitReplacementRule,
    'background-size': WebkitReplacementRule,
    'background-image': GradientReplacementRule,
    'background': GradientReplacementRule,

    'text-overflow': OperaAndIEReplacementRule,

    'transition': TransitionReplacementRule,
    'transition-delay': BaseAndOperaReplacementRule,
    'transition-duration': BaseAndOperaReplacementRule,
    'transition-property': TransitionReplacementRule,
    'transition-timing-function': BaseAndOperaReplacementRule,
    'transform': FullReplacementRule,
    'transform-origin': FullReplacementRule,

    'cursor': CursorReplacementRule,
    'display': DisplayReplacementRule,
    'appearance': WebkitReplacementRule,
    'hyphens': BaseReplacementRule,
}

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# CSSPrefixer
# Copyright 2010-2012 Greg V. <floatboth@me.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import cssprefixer

class PrefixerTestCase(unittest.TestCase):
    def test_common(self):
        self.assertEqual(cssprefixer.process('a{border-radius: 1em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}')

    def test_common_and_opera(self):
        self.assertEqual(cssprefixer.process('a{transform: rotate(10deg)}', minify=True),
                         'a{-moz-transform:rotate(10deg);-ms-transform:rotate(10deg);-o-transform:rotate(10deg);-webkit-transform:rotate(10deg);transform:rotate(10deg)}')

    def test_undefined(self):
        #test prefixed styles that don't have a rule yet, we use a fake property
        #for this test becuase we will never have a rule for this
        self.assertEqual(cssprefixer.process('a{-webkit-faker: black}', minify=True),
                         'a{-webkit-faker:black}')

    def test_webkit(self):
        self.assertEqual(cssprefixer.process('a{background-clip: padding-box}', minify=True),
                         'a{-webkit-background-clip:padding-box;background-clip:padding-box}')

    def test_appearance(self):
        #test prefixed styles that don't have a rule yet, we use a fake property
        #for this test becuase we will never have a rule for this
        self.assertEqual(cssprefixer.process('a{-webkit-appearance: none;}', minify=True),
                         'a{-webkit-appearance:none;appearance:none}')

    def test_ie_and_opera(self):
        self.assertEqual(cssprefixer.process('a{text-overflow: ellipsis}', minify=True),
                         'a{-ms-text-overflow:ellipsis;-o-text-overflow:ellipsis;text-overflow:ellipsis}')

    def test_moz_border_radius(self):
        self.assertEqual(cssprefixer.process('a{border-top-left-radius: 1em;border-top-right-radius: 1em;border-bottom-right-radius: 1em;border-bottom-left-radius: 1em;}', minify=True),
                         'a{-webkit-border-top-left-radius:1em;-moz-border-radius-topleft:1em;border-top-left-radius:1em;-webkit-border-top-right-radius:1em;-moz-border-radius-topright:1em;border-top-right-radius:1em;-webkit-border-bottom-right-radius:1em;-moz-border-radius-bottomright:1em;border-bottom-right-radius:1em;-webkit-border-bottom-left-radius:1em;-moz-border-radius-bottomleft:1em;border-bottom-left-radius:1em}')

    def test_cursor_zoom_in(self):
        self.assertEqual(cssprefixer.process('a{cursor: zoom-in;}', minify=True),
                         'a{cursor:-moz-zoom-in;cursor:-webkit-zoom-in;cursor:zoom-in}')

    def test_cursor_zoom_out(self):
        self.assertEqual(cssprefixer.process('a{cursor: zoom-out;}', minify=True),
                         'a{cursor:-moz-zoom-out;cursor:-webkit-zoom-out;cursor:zoom-out}')

    def test_flexbox(self):
        self.assertEqual(cssprefixer.process('a{display: box;}', minify=True),
                         'a{display:-moz-box;display:-webkit-box;display:box}')

    def test_displaybox(self):
        self.assertEqual(cssprefixer.process('a{display: display;}', minify=True),
                         'a{display:display}')

    def test_mq(self):
        self.assertEqual(cssprefixer.process('@media screen and (min-width:480px){a{color:red}}', minify=True),
                         '@media screen and (min-width:480px){a{color:red}}')

    def test_mq_common(self):
        self.assertEqual(cssprefixer.process('@media screen and (min-width:480px){a{border-radius: 1em}}', minify=True),
                         '@media screen and (min-width:480px){a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}}')

    def test_duplicate_common(self):
        self.assertEqual(cssprefixer.process('a{border-radius: 1em;border-radius: 2em;border-radius: 3em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em;-moz-border-radius:2em;-webkit-border-radius:2em;border-radius:2em;-moz-border-radius:3em;-webkit-border-radius:3em;border-radius:3em}')

    def test_mixed_common(self):
        self.assertEqual(cssprefixer.process('a{-moz-border-radius: 1em;border-radius: 2em;-webkit-border-radius: 3em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em;-moz-border-radius:2em;-webkit-border-radius:2em;border-radius:2em;-moz-border-radius:3em;-webkit-border-radius:3em;border-radius:3em}')

    def test_mixed_duplicate(self):
        self.assertEqual(cssprefixer.process('a{-moz-border-radius: 1em;border-radius: 1em;-webkit-border-radius: 1em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}')

    def test_transition(self):
        self.assertEqual(cssprefixer.process('''div {
      -webkit-transition: color .25s linear, -webkit-transform .15s linear .1s;
    }''', minify=False), '''div {
    -moz-transition: color 0.25s linear, -moz-transform 0.15s linear 0.1s;
    -o-transition: color 0.25s linear, -o-transform 0.15s linear 0.1s;
    -webkit-transition: color 0.25s linear, -webkit-transform 0.15s linear 0.1s;
    transition: color 0.25s linear, transform 0.15s linear 0.1s
    }''')

    def test_multi_transition(self):
        self.assertEqual(cssprefixer.process('''div {
    transition: color .25s linear;
    transition: background-color .15s linear .1;
    }''', minify=False), '''div {
    -moz-transition: color 0.25s linear;
    -o-transition: color 0.25s linear;
    -webkit-transition: color 0.25s linear;
    transition: color 0.25s linear;
    -moz-transition: background-color 0.15s linear 0.1;
    -o-transition: background-color 0.15s linear 0.1;
    -webkit-transition: background-color 0.15s linear 0.1;
    transition: background-color 0.15s linear 0.1
    }''')

    def test_transition_property(self):
        self.assertEqual(cssprefixer.process('''div {
    -webkit-transition-property: -webkit-transform, opacity, left;
    -webkit-transition-duration: rotatey(45deg), 2s, 4s;
    }''', minify=False), '''div {
    -moz-transition-property: -moz-transform, opacity, left;
    -o-transition-property: -o-transform, opacity, left;
    -webkit-transition-property: -webkit-transform, opacity, left;
    transition-property: transform, opacity, left;
    -moz-transition-duration: rotatey(45deg), 2s, 4s;
    -o-transition-duration: rotatey(45deg), 2s, 4s;
    -webkit-transition-duration: rotatey(45deg), 2s, 4s;
    transition-duration: rotatey(45deg), 2s, 4s
    }''')

    def test_no_mini(self):
        self.assertEqual(cssprefixer.process('''.my-class, #my-id {
    border-radius: 1em;
    transition: all 1s ease;
    box-shadow: #123456 0 0 10px;
    display: box;
}''', minify=False), '''.my-class, #my-id {
    -moz-border-radius: 1em;
    -webkit-border-radius: 1em;
    border-radius: 1em;
    -moz-transition: all 1s ease;
    -o-transition: all 1s ease;
    -webkit-transition: all 1s ease;
    transition: all 1s ease;
    -moz-box-shadow: #123456 0 0 10px;
    -webkit-box-shadow: #123456 0 0 10px;
    box-shadow: #123456 0 0 10px;
    display: -moz-box;
    display: -webkit-box;
    display: box
    }''')

    def test_empty(self):
        self.assertEqual(cssprefixer.process('a{}', minify=True), '')
        self.assertEqual(cssprefixer.process('a{}', minify=False), '')

    def test_media_no_mini(self):
        self.assertEqual(cssprefixer.process('''@media screen and (max-device-width: 480px){
    #book{
        border-radius: 1em;
    }
}''', minify=False), '''@media screen and (max-device-width: 480px) {
    #book {
        -moz-border-radius: 1em;
        -webkit-border-radius: 1em;
        border-radius: 1em
        }
    }''')

    def test_comment(self):
        self.assertEqual(cssprefixer.process('''/* HTML5 display-role reset for older browsers */
article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    display: block
    }''', minify=False), '''/* HTML5 display-role reset for older browsers */
article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    display: block
    }''')

    def test_inline_comment(self):
        #TODO: it would be nice if comments on the same line remained there, but this may not be possible because
        #cssutils tears everything apart into objects and then we rebuild it.
        self.assertEqual(cssprefixer.process('''article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    display: block;/* HTML5 display-role reset for older browsers */
    }''', minify=False), '''article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    display: block;
    /* HTML5 display-role reset for older browsers */
    }''')
        self.assertEqual(cssprefixer.process('''article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    /* HTML5 display-role reset for older browsers */
    display: block;
    }''', minify=False), '''article, aside, details, figcaption, figure, footer, header, hgroup, menu, nav, section {
    /* HTML5 display-role reset for older browsers */
    display: block
    }''')

class WebkitPrefixerTestCase(unittest.TestCase):
    def test_common(self):
        self.assertEqual(cssprefixer.process('a{-webkit-border-radius: 1em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}')

    def test_common_and_opera(self):
        self.assertEqual(cssprefixer.process('a{-webkit-transform: rotate(10deg)}', minify=True),
                         'a{-moz-transform:rotate(10deg);-ms-transform:rotate(10deg);-o-transform:rotate(10deg);-webkit-transform:rotate(10deg);transform:rotate(10deg)}')

    def test_webkit(self):
        self.assertEqual(cssprefixer.process('a{-webkit-background-clip: padding-box}', minify=True),
                         'a{-webkit-background-clip:padding-box;background-clip:padding-box}')

    def test_moz_border_radius(self):
        self.assertEqual(cssprefixer.process('a{-webkit-border-top-left-radius: 1em;-webkit-border-top-right-radius: 1em;-webkit-border-bottom-right-radius: 1em;-webkit-border-bottom-left-radius: 1em;}', minify=True),
                         'a{-webkit-border-top-left-radius:1em;-moz-border-radius-topleft:1em;border-top-left-radius:1em;-webkit-border-top-right-radius:1em;-moz-border-radius-topright:1em;border-top-right-radius:1em;-webkit-border-bottom-right-radius:1em;-moz-border-radius-bottomright:1em;border-bottom-right-radius:1em;-webkit-border-bottom-left-radius:1em;-moz-border-radius-bottomleft:1em;border-bottom-left-radius:1em}')

    def test_flexbox(self):
        self.assertEqual(cssprefixer.process('a{-webkit-display: box;}', minify=True),
                         'a{display:-moz-box;display:-webkit-box;display:box}')

    def test_mq_common(self):
        self.assertEqual(cssprefixer.process('@media screen and (min-width:480px){a{-webkit-border-radius: 1em}}', minify=True),
                         '@media screen and (min-width:480px){a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}}')

class MozPrefixerTestCase(unittest.TestCase):
    def test_common(self):
        self.assertEqual(cssprefixer.process('a{-moz-border-radius: 1em}', minify=True),
                         'a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}')

    def test_common_and_opera(self):
        self.assertEqual(cssprefixer.process('a{-moz-transform: rotate(10deg)}', minify=True),
                         'a{-moz-transform:rotate(10deg);-ms-transform:rotate(10deg);-o-transform:rotate(10deg);-webkit-transform:rotate(10deg);transform:rotate(10deg)}')

    def test_moz_border_radius(self):
        self.assertEqual(cssprefixer.process('a{-moz-border-top-left-radius: 1em;-moz-border-top-right-radius: 1em;-moz-border-bottom-right-radius: 1em;-moz-border-bottom-left-radius: 1em;}', minify=True),
                         'a{-webkit-border-top-left-radius:1em;-moz-border-radius-topleft:1em;border-top-left-radius:1em;-webkit-border-top-right-radius:1em;-moz-border-radius-topright:1em;border-top-right-radius:1em;-webkit-border-bottom-right-radius:1em;-moz-border-radius-bottomright:1em;border-bottom-right-radius:1em;-webkit-border-bottom-left-radius:1em;-moz-border-radius-bottomleft:1em;border-bottom-left-radius:1em}')

    def test_flexbox(self):
        self.assertEqual(cssprefixer.process('a{-moz-display: box;}', minify=True),
                         'a{display:-moz-box;display:-webkit-box;display:box}')

    def test_mq_common(self):
        self.assertEqual(cssprefixer.process('@media screen and (min-width:480px){a{-moz-border-radius: 1em}}', minify=True),
                         '@media screen and (min-width:480px){a{-moz-border-radius:1em;-webkit-border-radius:1em;border-radius:1em}}')

class OperaPrefixerTestCase(unittest.TestCase):
    def test_common_and_opera(self):
        self.assertEqual(cssprefixer.process('a{-o-transform: rotate(10deg)}', minify=True),
                         'a{-moz-transform:rotate(10deg);-ms-transform:rotate(10deg);-o-transform:rotate(10deg);-webkit-transform:rotate(10deg);transform:rotate(10deg)}')

    def test_ie_and_opera(self):
        self.assertEqual(cssprefixer.process('a{-o-text-overflow: ellipsis}', minify=True),
                         'a{-ms-text-overflow:ellipsis;-o-text-overflow:ellipsis;text-overflow:ellipsis}')

class IePrefixerTestCase(unittest.TestCase):
    def test_ie_and_opera(self):
        self.assertEqual(cssprefixer.process('a{-ms-text-overflow: ellipsis}', minify=True),
                         'a{-ms-text-overflow:ellipsis;-o-text-overflow:ellipsis;text-overflow:ellipsis}')

class GradientTestCase(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: linear-gradient(top, #444444, #999999);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(top, #444, #999);
    background-image: -o-linear-gradient(top, #444, #999);
    background-image: -webkit-linear-gradient(top, #444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(top, #444, #999)
    }''')

    def test_linear_no_pos(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: linear-gradient(#444444, #999999);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(#444, #999);
    background-image: -o-linear-gradient(#444, #999);
    background-image: -webkit-linear-gradient(#444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(#444, #999)
    }''')

    def test_webkit(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -webkit-linear-gradient(top, #444444, #999999);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(top, #444, #999);
    background-image: -o-linear-gradient(top, #444, #999);
    background-image: -webkit-linear-gradient(top, #444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(top, #444, #999)
    }''')

    def test_webkit_mixed(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -webkit-linear-gradient(top, #444444, #999999), linear-gradient(top, black, white);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(top, #444, #999), -moz-linear-gradient(top, black, white);
    background-image: -o-linear-gradient(top, #444, #999), -o-linear-gradient(top, black, white);
    background-image: -webkit-linear-gradient(top, #444, #999), -webkit-linear-gradient(top, black, white);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999)), -webkit-gradient(linear, left top, left bottom, color-stop(0, black), color-stop(1, white));
    background-image: linear-gradient(top, #444, #999), linear-gradient(top, black, white)
    }''')

    def test_moz(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -moz-linear-gradient(top, #444444, #999999);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(top, #444, #999);
    background-image: -o-linear-gradient(top, #444, #999);
    background-image: -webkit-linear-gradient(top, #444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(top, #444, #999)
    }''')

    def test_o(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -o-linear-gradient(top, #444444, #999999);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(top, #444, #999);
    background-image: -o-linear-gradient(top, #444, #999);
    background-image: -webkit-linear-gradient(top, #444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(top, #444, #999)
    }''')

    def test_webkit_gradient(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(#444, #999);
    background-image: -o-linear-gradient(#444, #999);
    background-image: -webkit-linear-gradient(#444, #999);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background-image: linear-gradient(#444, #999)
    }''')

    def test_webkit_gradient_mixed(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999)), -webkit-linear-gradient(top, black, white);
    }''', minify=False), '''.box_gradient {
    background-image: -moz-linear-gradient(#444, #999), -moz-linear-gradient(top, black, white);
    background-image: -o-linear-gradient(#444, #999), -o-linear-gradient(top, black, white);
    background-image: -webkit-linear-gradient(#444, #999), -webkit-linear-gradient(top, black, white);
    background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999)), -webkit-gradient(linear, left top, left bottom, color-stop(0, black), color-stop(1, white));
    background-image: linear-gradient(#444, #999), linear-gradient(top, black, white)
    }''')

    def test_image(self):
        #I don't think this test produces valid css but it shows that data and order is being preserved.
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image: url(images/background.png), linear-gradient(top, black, white);
    }''', minify=False), '''.box_gradient {
    background-image: url(images/background.png), -moz-linear-gradient(top, black, white);
    background-image: url(images/background.png), -o-linear-gradient(top, black, white);
    background-image: url(images/background.png), -webkit-linear-gradient(top, black, white);
    background-image: url(images/background.png), -webkit-gradient(linear, left top, left bottom, color-stop(0, black), color-stop(1, white));
    background-image: url(images/background.png), linear-gradient(top, black, white)
    }''')

    def test_background_multiple_images(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background: url(images/cross.png), url(images/gradient.png) top center no-repeat, url(images/background.png);
    }''', minify=False), '''.box_gradient {
    background: url(images/cross.png), url(images/gradient.png) top center no-repeat, url(images/background.png)
    }''')

    def test_background_multiple_images_and_gradient(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background: linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png);
    }''', minify=False), '''.box_gradient {
    background: -moz-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png);
    background: -o-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png);
    background: -webkit-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png);
    background: -webkit-gradient(linear, left top, left bottom, color-stop(0, black), color-stop(1, white)), url(images/gradient.png) top center no-repeat, url(images/background.png);
    background: linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png)
    }''')

    def test_background_multiple_images_and_gradients(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background: linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png), -moz-linear-gradient(top, #444444, #999999);
    }''', minify=False), '''.box_gradient {
    background: -moz-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png), -moz-linear-gradient(top, #444, #999);
    background: -o-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png), -o-linear-gradient(top, #444, #999);
    background: -webkit-linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png), -webkit-linear-gradient(top, #444, #999);
    background: -webkit-gradient(linear, left top, left bottom, color-stop(0, black), color-stop(1, white)), url(images/gradient.png) top center no-repeat, url(images/background.png), -webkit-gradient(linear, left top, left bottom, color-stop(0, #444), color-stop(1, #999));
    background: linear-gradient(top, black, white), url(images/gradient.png) top center no-repeat, url(images/background.png), linear-gradient(top, #444, #999)
    }''')

    #cssutils cannot parse this rule
    def _test_background_multiple_images_and_gradients(self):
        self.assertEqual(cssprefixer.process('''.box_gradient {
    background-image:
        url('../img/arrow.png'),
        -webkit-gradient(
        linear,
        left top,
        left bottom,
        from(rgb(240, 240, 240)),
        to(rgb(210, 210, 210))
    )}''', minify=False), '''.box_gradient {
    }''')

    def test_keyframes(self):
        self.assertEqual(cssprefixer.process('''@keyframes round {
    from {border-radius: 2px}
    to {border-radius: 10px}
    }''', minify=False), "@-webkit-keyframes {\nfrom {\n    -webkit-border-radius: 2px;\n    border-radius: 2px\n    }\nto {\n    -webkit-border-radius: 10px;\n    border-radius: 10px\n    }\n}\n@-moz-keyframes {\nfrom {\n    -moz-border-radius: 2px;\n    border-radius: 2px\n    }\nto {\n    -moz-border-radius: 10px;\n    border-radius: 10px\n    }\n}\n@keyframes round {\n    from {\n        border-radius: 2px\n        } to {\n        border-radius: 10px\n        }\n    }")

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
