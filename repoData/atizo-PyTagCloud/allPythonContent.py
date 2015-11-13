__FILENAME__ = colors
# -*- coding: utf-8 -*-
COLOR_SCHEMES = {
                 'oldschool': ((59,76,76), (125,140,116), (217,175,95), (127,92,70), (51,36,35)),
                 'citrus': ((34,51,49), (70,102,66), (153,142,61), (229,156,44), (255,116,37)),
                 'goldfish': ((229,106,0), (204,199,148), (153,145,124), (88,89,86), (48,49,51)),
                 'audacity': ((181,40,65), (255,192,81), (255,137,57), (232,95,77), (89,0,81)),
                }

########NEW FILE########
__FILENAME__ = counter
# -*- coding: utf-8 -*-
import re
from pytagcloud.lang.stopwords import StopWords
from operator import itemgetter
from collections import defaultdict

def get_tag_counts(text):
    """
    Search tags in a given text. The language detection is based on stop lists.
    This implementation is inspired by https://github.com/jdf/cue.language. Thanks Jonathan Feinberg.
    """
    words = map(lambda x:x.lower(), re.findall(r"[\w']+", text, re.UNICODE))
    
    s = StopWords()     
    s.load_language(s.guess(words))
    
    counted = defaultdict(int)
    
    for word in words:
        if not s.is_stop_word(word) and len(word) > 1:
            counted[word] += 1
      
    return sorted(counted.iteritems(), key=itemgetter(1), reverse=True)
    

########NEW FILE########
__FILENAME__ = stopwords
# -*- coding: utf-8 -*-
import os

ACTIVE_LISTS = ('german', 'french', 'italian', 'english', 'spanish')

class StopWords(object):
    
    def __init__(self):
        
        self.stop_words_lists = {}
        self.language = None
        
        stop_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stop')
        
        for root, dirs, files in os.walk(stop_dir):
            for file in files:
                if not file in ACTIVE_LISTS:
                    continue
                stop_file = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stop/', file), 'r')                
                self.stop_words_lists[file] = []                
                for stop_word in stop_file:
                    self.stop_words_lists[file].append(stop_word.strip().lower())
                stop_file.close()

    def load_language(self, language):
        self.language = language
                    
    def is_stop_word(self, word):
        if not self.language:
            raise LookupError("No language loaded")
        return word in self.stop_words_lists[self.language]
    
    def guess(self, words):
        currentWinner = ACTIVE_LISTS[0];
        currentMax = 0;
        
        for language, stop_word_list in self.stop_words_lists.items():
            count = 0
            for word in words:
                if word in stop_word_list:
                    count += 1
                    
            if count > currentMax:
                currentWinner = language
                currentMax = count
        
        return currentWinner
    

########NEW FILE########
__FILENAME__ = profile
# -*- coding: utf-8 -*-
from pytagcloud import make_tags, create_tag_image, LAYOUT_MIX
from pytagcloud.colors import COLOR_SCHEMES
from pytagcloud.lang.counter import get_tag_counts
import cProfile
import os
import pstats

tags = None
test_output = None

def init():
    global tags
    global test_output
    
    home_folder = os.getenv('USERPROFILE') or os.getenv('HOME')
    test_output = os.path.join(home_folder, 'pytagclouds')
    
    if not os.path.exists(test_output):
        os.mkdir(test_output )         
    
    hound = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../test/pg2852.txt'), 'r')
    tags = make_tags(get_tag_counts(hound.read())[:50], maxsize=120, colors=COLOR_SCHEMES['audacity'])

def run():
    create_tag_image(tags, os.path.join(test_output, 'cloud_profile.png'), size=(1280, 900), background=(0, 0, 0, 255), layout=LAYOUT_MIX, crop=True, fontname='Lobster', fontzoom=1)

if __name__ == '__main__':
    
    init()

    cProfile.run('run()', 'cloud.profile')
    p = pstats.Stats('cloud.profile')
    p.strip_dirs().sort_stats(-1).print_stats()    
    p.sort_stats('time').print_stats(10)
    p.print_stats()
########NEW FILE########
__FILENAME__ = font_align
# -*- coding: utf-8 -*-
#
# Hierarchical bounding boxes performance test
#

from pygame import font, mask, Surface, SRCALPHA
from pygame.sprite import Sprite, collide_mask, collide_rect
import os
import pygame
import sys
import timeit
import cProfile
import pstats

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts')

pygame.init()


if __name__ == '__main__':    
    
    
    for x in xrange(10):
        fsize = 50 + 10 * x
        thefont = font.Font(os.path.join(FONT_DIR, "cantarell-regular-webfont.ttf"), fsize)

        print "Lineheight", thefont.get_linesize()
        print "Size", fsize
        print "Ascent", thefont.get_ascent()
        print "Descent", thefont.get_descent()
        print "Diff", thefont.get_linesize() - (thefont.get_ascent() + abs(thefont.get_descent()))
        text = thefont.render("Cooer", True, (0,0,0))
        print "Text h", text.get_bounding_rect()
        print ""

    metrics =  thefont.metrics("Cooer")
    
    print min([f[2] for f in metrics])
    print max([f[3] for f in metrics])
    print metrics[0]
    
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("PyTagCloud Font Alignment")    
    
    done = False
    clock = pygame.time.Clock()    
    
    while done==False:         
        
        clock.tick(10)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done=True
                
        screen.fill((255,255,255))
        
        screen.blit(text, (100,100))
       
        
        pygame.display.flip()       
        
    pygame.quit()    
########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from pytagcloud import create_tag_image, create_html_data, make_tags, \
    LAYOUT_HORIZONTAL, LAYOUTS
from pytagcloud.colors import COLOR_SCHEMES
from pytagcloud.lang.counter import get_tag_counts
from string import Template
import os
import time
import unittest

class Test(unittest.TestCase):
    """
    Generate tag clouds and save them to <YOURHOME>/pytagclouds/
    Note: All tests are disabled ('_' prefixed) by default
    """
    
    def setUp(self):
        self.test_output = os.path.join(os.getcwd(), 'out')
        self.hound = open(os.path.join(os.getcwd(), 'pg2852.txt'), 'r')
        
        if not os.path.exists(self.test_output):
            os.mkdir(self.test_output )            
            
    def tearDown(self):
        self.hound.close()
        
    def test_tag_counter(self):
        tag_list = get_tag_counts(self.hound.read())[:50]     
        self.assertTrue(('sir', 350) in tag_list)

    def test_make_tags(self):
        mtags = make_tags(get_tag_counts(self.hound.read())[:60])
        found = False
        for tag in mtags:
            if tag['tag'] == 'sir' and tag['size'] == 40:
                found = True
                break
            
        self.assertTrue(found)

    def test_layouts(self):
        start = time.time()
        tags = make_tags(get_tag_counts(self.hound.read())[:80], maxsize=120)
        for layout in LAYOUTS:
            create_tag_image(tags, os.path.join(self.test_output, 'cloud_%s.png' % layout),
                             size=(900, 600),
                             background=(255, 255, 255, 255),
                             layout=layout, fontname='Lobster')
        print "Duration: %d sec" % (time.time() - start)
        
    def test_large_tag_image(self):
        start = time.time()
        tags = make_tags(get_tag_counts(self.hound.read())[:80], maxsize=120, 
                         colors=COLOR_SCHEMES['audacity'])
        create_tag_image(tags, os.path.join(self.test_output, 'cloud_large.png'), 
                         size=(900, 600), background=(0, 0, 0, 255), 
                         layout=LAYOUT_HORIZONTAL, fontname='Lobster')
        print "Duration: %d sec" % (time.time() - start)

    def test_create_html_data(self):
        """
        HTML code sample
        """
        tags = make_tags(get_tag_counts(self.hound.read())[:100], maxsize=120, colors=COLOR_SCHEMES['audacity'])
        data = create_html_data(tags, (440,600), layout=LAYOUT_HORIZONTAL, fontname='PT Sans Regular')
        
        template_file = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web/template.html'), 'r')    
        html_template = Template(template_file.read())
        
        context = {}
        
        tags_template = '<li class="cnt" style="top: %(top)dpx; left: %(left)dpx; height: %(height)dpx;"><a class="tag %(cls)s" href="#%(tag)s" style="top: %(top)dpx;\
        left: %(left)dpx; font-size: %(size)dpx; height: %(height)dpx; line-height:%(lh)dpx;">%(tag)s</a></li>'
        
        context['tags'] = ''.join([tags_template % link for link in data['links']])
        context['width'] = data['size'][0]
        context['height'] = data['size'][1]
        context['css'] = "".join("a.%(cname)s{color:%(normal)s;}\
        a.%(cname)s:hover{color:%(hover)s;}" % 
                                  {'cname':k,
                                   'normal': v[0],
                                   'hover': v[1]} 
                                 for k,v in data['css'].items())
        
        html_text = html_template.substitute(context)
        
        html_file = open(os.path.join(self.test_output, 'cloud.html'), 'w')
        html_file.write(html_text)
        html_file.close()       

if __name__ == "__main__":
    unittest.main()
########NEW FILE########
