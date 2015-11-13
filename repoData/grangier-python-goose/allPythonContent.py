__FILENAME__ = article
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class Article(object):

    def __init__(self):
        # title of the article
        self.title = None

        # stores the lovely, pure text from the article,
        # stripped of html, formatting, etc...
        # just raw text with paragraphs separated by newlines.
        # This is probably what you want to use.
        self.cleaned_text = u""

        # meta description field in HTML source
        self.meta_description = u""

        # meta lang field in HTML source
        self.meta_lang = u""

        # meta favicon field in HTML source
        self.meta_favicon = u""

        # meta keywords field in the HTML source
        self.meta_keywords = u""

        # The canonical link of this article if found in the meta data
        self.canonical_link = u""

        # holds the domain of this article we're parsing
        self.domain = u""

        # holds the top Element we think
        # is a candidate for the main body of the article
        self.top_node = None

        # holds the top Image object that
        # we think represents this article
        self.top_image = None

        # holds a set of tags that may have
        # been in the artcle, these are not meta keywords
        self.tags = set()

        # holds a list of any movies
        # we found on the page like youtube, vimeo
        self.movies = []

        # stores the final URL that we're going to try
        # and fetch content against, this would be expanded if any
        self.final_url = u""

        # stores the MD5 hash of the url
        # to use for various identification tasks
        self.link_hash = ""

        # stores the RAW HTML
        # straight from the network connection
        self.raw_html = u""

        # the lxml Document object
        self.doc = None

        # this is the original JSoup document that contains
        # a pure object from the original HTML without any cleaning
        # options done on it
        self.raw_doc = None

        # Sometimes useful to try and know when
        # the publish date of an article was
        self.publish_date = None

        # A property bucket for consumers of goose to store custom data extractions.
        self.additional_data = {}

########NEW FILE########
__FILENAME__ = cleaners
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from goose.utils import ReplaceSequence


class DocumentCleaner(object):

    def __init__(self, config, article):
        # config
        self.config = config

        # parser
        self.parser = self.config.get_parser()

        # article
        self.article = article

        # nodes to remove regexp
        self.remove_nodes_re = (
        "^side$|combx|retweet|mediaarticlerelated|menucontainer|"
        "navbar|storytopbar-bucket|utility-bar|inline-share-tools"
        "|comment|PopularQuestions|contact|foot|footer|Footer|footnote"
        "|cnn_strycaptiontxt|cnn_html_slideshow|cnn_strylftcntnt"
        "|links|meta$|shoutbox|sponsor"
        "|tags|socialnetworking|socialNetworking|cnnStryHghLght"
        "|cnn_stryspcvbx|^inset$|pagetools|post-attributes"
        "|welcome_form|contentTools2|the_answers"
        "|communitypromo|runaroundLeft|subscribe|vcard|articleheadings"
        "|date|^print$|popup|author-dropdown|tools|socialtools|byline"
        "|konafilter|KonaFilter|breadcrumbs|^fn$|wp-caption-text"
        "|legende|ajoutVideo|timestamp|js_replies"
        )
        self.regexp_namespace = "http://exslt.org/regular-expressions"
        self.nauthy_ids_re = "//*[re:test(@id, '%s', 'i')]" % self.remove_nodes_re
        self.nauthy_classes_re = "//*[re:test(@class, '%s', 'i')]" % self.remove_nodes_re
        self.nauthy_names_re = "//*[re:test(@name, '%s', 'i')]" % self.remove_nodes_re
        self.div_to_p_re = r"<(a|blockquote|dl|div|img|ol|p|pre|table|ul)"
        self.caption_re = "^caption$"
        self.google_re = " google "
        self.entries_re = "^[^entry-]more.*$"
        self.facebook_re = "[^-]facebook"
        self.facebook_braodcasting_re = "facebook-broadcasting"
        self.twitter_re = "[^-]twitter"
        self.tablines_replacements = ReplaceSequence()\
                                            .create("\n", "\n\n")\
                                            .append("\t")\
                                            .append("^\\s+$")

    def clean(self):
        doc_to_clean = self.article.doc
        doc_to_clean = self.clean_body_classes(doc_to_clean)
        doc_to_clean = self.clean_article_tags(doc_to_clean)
        doc_to_clean = self.clean_em_tags(doc_to_clean)
        doc_to_clean = self.remove_drop_caps(doc_to_clean)
        doc_to_clean = self.remove_scripts_styles(doc_to_clean)
        doc_to_clean = self.clean_bad_tags(doc_to_clean)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.caption_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.google_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.entries_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.facebook_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.facebook_braodcasting_re)
        doc_to_clean = self.remove_nodes_regex(doc_to_clean, self.twitter_re)
        doc_to_clean = self.clean_para_spans(doc_to_clean)
        doc_to_clean = self.div_to_para(doc_to_clean, 'div')
        doc_to_clean = self.div_to_para(doc_to_clean, 'span')
        return doc_to_clean

    def clean_body_classes(self, doc):
        # we don't need body classes
        # in case it matches an unwanted class all the document
        # will be empty
        elements = self.parser.getElementsByTag(doc, tag="body")
        if elements:
            self.parser.delAttribute(elements[0], attr="class")
        return doc

    def clean_article_tags(self, doc):
        articles = self.parser.getElementsByTag(doc, tag='article')
        for article in articles:
            for attr in ['id', 'name', 'class']:
                self.parser.delAttribute(article, attr=attr)
        return doc

    def clean_em_tags(self, doc):
        ems = self.parser.getElementsByTag(doc, tag='em')
        for node in ems:
            images = self.parser.getElementsByTag(node, tag='img')
            if len(images) == 0:
                self.parser.drop_tag(node)
        return doc

    def remove_drop_caps(self, doc):
        items = self.parser.css_select(doc, "span[class~=dropcap], span[class~=drop_cap]")
        for item in items:
            self.parser.drop_tag(item)

        return doc

    def remove_scripts_styles(self, doc):
        # remove scripts
        scripts = self.parser.getElementsByTag(doc, tag='script')
        for item in scripts:
            self.parser.remove(item)

        # remove styles
        styles = self.parser.getElementsByTag(doc, tag='style')
        for item in styles:
            self.parser.remove(item)

        # remove comments
        comments = self.parser.getComments(doc)
        for item in comments:
            self.parser.remove(item)

        return doc

    def clean_bad_tags(self, doc):
        # ids
        naughty_list = self.parser.xpath_re(doc, self.nauthy_ids_re)
        for node in naughty_list:
            self.parser.remove(node)

        # class
        naughty_classes = self.parser.xpath_re(doc, self.nauthy_classes_re)
        for node in naughty_classes:
            self.parser.remove(node)

        # name
        naughty_names = self.parser.xpath_re(doc, self.nauthy_names_re)
        for node in naughty_names:
            self.parser.remove(node)

        return doc

    def remove_nodes_regex(self, doc, pattern):
        for selector in ['id', 'class']:
            reg = "//*[re:test(@%s, '%s', 'i')]" % (selector, pattern)
            naughty_list = self.parser.xpath_re(doc, reg)
            for node in naughty_list:
                self.parser.remove(node)
        return doc

    def clean_para_spans(self, doc):
        spans = self.parser.css_select(doc, 'p span')
        for item in spans:
            self.parser.drop_tag(item)
        return doc

    def get_flushed_buffer(self, replacement_text, doc):
        return self.parser.textToPara(replacement_text)

    def get_replacement_nodes(self, doc, div):
        replacement_text = []
        nodes_to_return = []
        nodes_to_remove = []
        childs = self.parser.childNodesWithText(div)

        for kid in childs:
            # node is a p
            # and already have some replacement text
            if self.parser.getTag(kid) == 'p' and len(replacement_text) > 0:
                newNode = self.get_flushed_buffer(''.join(replacement_text), doc)
                nodes_to_return.append(newNode)
                replacement_text = []
                nodes_to_return.append(kid)
            # node is a text node
            elif self.parser.isTextNode(kid):
                kid_text_node = kid
                kid_text = self.parser.getText(kid)
                replace_text = self.tablines_replacements.replaceAll(kid_text)
                if(len(replace_text)) > 1:
                    previous_sibling_node = self.parser.previousSibling(kid_text_node)
                    while previous_sibling_node is not None \
                        and self.parser.getTag(previous_sibling_node) == "a" \
                        and self.parser.getAttribute(previous_sibling_node, 'grv-usedalready') != 'yes':
                        outer = " " + self.parser.outerHtml(previous_sibling_node) + " "
                        replacement_text.append(outer)
                        nodes_to_remove.append(previous_sibling_node)
                        self.parser.setAttribute(previous_sibling_node,
                                    attr='grv-usedalready', value='yes')
                        prev = self.parser.previousSibling(previous_sibling_node)
                        previous_sibling_node = prev if prev is not None else None
                    # append replace_text
                    replacement_text.append(replace_text)
                    #
                    next_sibling_node = self.parser.nextSibling(kid_text_node)
                    while next_sibling_node is not None \
                        and self.parser.getTag(next_sibling_node) == "a" \
                        and self.parser.getAttribute(next_sibling_node, 'grv-usedalready') != 'yes':
                        outer = " " + self.parser.outerHtml(next_sibling_node) + " "
                        replacement_text.append(outer)
                        nodes_to_remove.append(next_sibling_node)
                        self.parser.setAttribute(next_sibling_node,
                                    attr='grv-usedalready', value='yes')
                        next = self.parser.nextSibling(next_sibling_node)
                        previous_sibling_node = next if next is not None else None

            # otherwise
            else:
                nodes_to_return.append(kid)

        # flush out anything still remaining
        if(len(replacement_text) > 0):
            new_node = self.get_flushed_buffer(''.join(replacement_text), doc)
            nodes_to_return.append(new_node)
            replacement_text = []

        for n in nodes_to_remove:
            self.parser.remove(n)

        return nodes_to_return

    def replace_with_para(self, doc, div):
        self.parser.replaceTag(div, 'p')

    def div_to_para(self, doc, dom_type):
        bad_divs = 0
        else_divs = 0
        divs = self.parser.getElementsByTag(doc, tag=dom_type)
        tags = ['a', 'blockquote', 'dl', 'div', 'img', 'ol', 'p', 'pre', 'table', 'ul']

        for div in divs:
            items = self.parser.getElementsByTags(div, tags)
            if div is not None and len(items) == 0:
                self.replace_with_para(doc, div)
                bad_divs += 1
            elif div is not None:
                replaceNodes = self.get_replacement_nodes(doc, div)
                div.clear()

                for c, n in enumerate(replaceNodes):
                    div.insert(c, n)

                else_divs += 1

        return doc


class StandardDocumentCleaner(DocumentCleaner):
    pass

########NEW FILE########
__FILENAME__ = configuration
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import tempfile
from goose.text import StopWords
from goose.parsers import Parser
from goose.parsers import ParserSoup
from goose.version import __version__


class Configuration(object):

    def __init__(self):
        # What's the minimum bytes for an image we'd accept is,
        # alot of times we want to filter out the author's little images
        # in the beginning of the article
        self.images_min_bytes = 4500

        # set this guy to false if you don't care about getting images,
        # otherwise you can either use the default
        # image extractor to implement the ImageExtractor
        # interface to build your own
        self.enable_image_fetching = True

        # set this valriable to False if you want to force
        # the article language. OtherWise it will attempt to
        # find meta language and use the correct stopwords dictionary
        self.use_meta_language = True

        # default language
        # it will be use as fallback
        # if use_meta_language is set to false, targetlanguage will
        # be use
        self.target_language = 'en'

        # defautl stopwrods class
        self.stopwords_class = StopWords

        # path to your imagemagick convert executable,
        # on the mac using mac ports this is the default listed
        self.imagemagick_convert_path = "/opt/local/bin/convert"

        # path to your imagemagick identify executable
        self.imagemagick_identify_path = "/opt/local/bin/identify"

        # used as the user agent that
        # is sent with your web requests to extract an article
        # self.browser_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2)"\
        #                         " AppleWebKit/534.52.7 (KHTML, like Gecko) "\
        #                         "Version/5.1.2 Safari/534.52.7"
        self.browser_user_agent = 'Goose/%s' % __version__

        # debug mode
        # enable this to have additional debugging information
        # sent to stdout
        self.debug = False

        # TODO
        self.extract_publishdate = None

        # TODO
        self.additional_data_extractor = None

        # Parser type
        self.parser_class = 'lxml'

        # set the local storage path
        # make this configurable
        self.local_storage_path = os.path.join(tempfile.gettempdir(), 'goose')

    def get_parser(self):
        return Parser if self.parser_class == 'lxml' else ParserSoup

    def get_publishdate_extractor(self):
        return self.extract_publishdate

    def set_publishdate_extractor(self, extractor):
        """\
        Pass in to extract article publish dates.
        @param extractor a concrete instance of PublishDateExtractor
        """
        if not extractor:
            raise ValueError("extractor must not be null!")
        self.extract_publishdate = extractor

    def get_additionaldata_extractor(self):
        return self.additional_data_extractor

    def set_additionaldata_extractor(self, extractor):
        """\
        Pass in to extract any additional data not defined within
        @param extractor a concrete instance of AdditionalDataExtractor
        """
        if not extractor:
            raise ValueError("extractor must not be null!")
        self.additional_data_extractor = extractor

########NEW FILE########
__FILENAME__ = crawler
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import glob
from copy import deepcopy
from goose.article import Article
from goose.utils import URLHelper, RawHelper
from goose.extractors import StandardContentExtractor
from goose.cleaners import StandardDocumentCleaner
from goose.outputformatters import StandardOutputFormatter
from goose.images.extractors import UpgradedImageIExtractor
from goose.videos.extractors import VideoExtractor
from goose.network import HtmlFetcher


class CrawlCandidate(object):

    def __init__(self, config, url, raw_html):
        self.config = config
        # parser
        self.parser = self.config.get_parser()
        self.url = url
        self.raw_html = raw_html


class Crawler(object):

    def __init__(self, config):
        # config
        self.config = config
        # parser
        self.parser = self.config.get_parser()

        # article
        self.article = Article()

        # init the extractor
        self.extractor = self.get_extractor()

        # init the document cleaner
        self.cleaner = self.get_cleaner()

        # init the output formatter
        self.formatter = self.get_formatter()

        # video extractor
        self.video_extractor = self.get_video_extractor()

        # image extrator
        self.image_extractor = self.get_image_extractor()

        # html fetcher
        self.htmlfetcher = HtmlFetcher(self.config)

        # TODO : log prefix
        self.logPrefix = "crawler:"

    def crawl(self, crawl_candidate):

        # parser candidate
        parse_candidate = self.get_parse_candidate(crawl_candidate)

        # raw html
        raw_html = self.get_html(crawl_candidate, parse_candidate)

        if raw_html is None:
            return self.article

        # create document
        doc = self.get_document(raw_html)

        # article
        self.article.final_url = parse_candidate.url
        self.article.link_hash = parse_candidate.link_hash
        self.article.raw_html = raw_html
        self.article.doc = doc
        self.article.raw_doc = deepcopy(doc)
        # TODO
        # self.article.publish_date = config.publishDateExtractor.extract(doc)
        # self.article.additional_data = config.get_additionaldata_extractor.extract(doc)
        self.article.title = self.extractor.get_title()
        self.article.meta_lang = self.extractor.get_meta_lang()
        self.article.meta_favicon = self.extractor.get_favicon()
        self.article.meta_description = self.extractor.get_meta_description()
        self.article.meta_keywords = self.extractor.get_meta_keywords()
        self.article.canonical_link = self.extractor.get_canonical_link()
        self.article.domain = self.extractor.get_domain()
        self.article.tags = self.extractor.extract_tags()

        # before we do any calcs on the body itself let's clean up the document
        self.article.doc = self.cleaner.clean()

        # big stuff
        self.article.top_node = self.extractor.calculate_best_node()

        # if we have a top node
        # let's process it
        if self.article.top_node is not None:

            # video handeling
            self.video_extractor.get_videos()

            # image handeling
            if self.config.enable_image_fetching:
                self.get_image()

            # post cleanup
            self.article.top_node = self.extractor.post_cleanup()

            # clean_text
            self.article.cleaned_text = self.formatter.get_formatted_text()

        # cleanup tmp file
        self.relase_resources()

        # return the article
        return self.article

    def get_parse_candidate(self, crawl_candidate):
        if crawl_candidate.raw_html:
            return RawHelper.get_parsing_candidate(crawl_candidate.url, crawl_candidate.raw_html)
        return URLHelper.get_parsing_candidate(crawl_candidate.url)

    def get_image(self):
        doc = self.article.raw_doc
        top_node = self.article.top_node
        self.article.top_image = self.image_extractor.get_best_image(doc, top_node)

    def get_html(self, crawl_candidate, parsing_candidate):
        # we got a raw_tml
        # no need to fetch remote content
        if crawl_candidate.raw_html:
            return crawl_candidate.raw_html

        # fetch HTML
        html = self.htmlfetcher.get_html(parsing_candidate.url)
        self.article.additional_data.update({
            'request': self.htmlfetcher.request,
            'result': self.htmlfetcher.result,
            })
        return html

    def get_image_extractor(self):
        return UpgradedImageIExtractor(self.config, self.article)

    def get_video_extractor(self):
        return VideoExtractor(self.config, self.article)

    def get_formatter(self):
        return StandardOutputFormatter(self.config, self.article)

    def get_cleaner(self):
        return StandardDocumentCleaner(self.config, self.article)

    def get_document(self, raw_html):
        doc = self.parser.fromstring(raw_html)
        return doc

    def get_extractor(self):
        return StandardContentExtractor(self.config, self.article)

    def relase_resources(self):
        path = os.path.join(self.config.local_storage_path, '%s_*' % self.article.link_hash)
        for fname in glob.glob(path):
            try:
                os.remove(fname)
            except OSError:
                # TODO better log handeling
                pass

########NEW FILE########
__FILENAME__ = extractors
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import re
from copy import deepcopy
from urlparse import urlparse, urljoin
from goose.utils import StringSplitter
from goose.utils import StringReplacement
from goose.utils import ReplaceSequence

MOTLEY_REPLACEMENT = StringReplacement("&#65533;", "")
ESCAPED_FRAGMENT_REPLACEMENT = StringReplacement(u"#!", u"?_escaped_fragment_=")
TITLE_REPLACEMENTS = ReplaceSequence().create(u"&raquo;").append(u"»")
PIPE_SPLITTER = StringSplitter("\\|")
DASH_SPLITTER = StringSplitter(" - ")
ARROWS_SPLITTER = StringSplitter("»")
COLON_SPLITTER = StringSplitter(":")
SPACE_SPLITTER = StringSplitter(' ')
NO_STRINGS = set()
A_REL_TAG_SELECTOR = "a[rel=tag]"
A_HREF_TAG_SELECTOR = "a[href*='/tag/'], a[href*='/tags/'], a[href*='/topic/'], a[href*='?keyword=']"
RE_LANG = r'^[A-Za-z]{2}$'


class ContentExtractor(object):

    def __init__(self, config, article):
        # config
        self.config = config

        # parser
        self.parser = self.config.get_parser()

        # article
        self.article = article

        # language
        self.language = config.target_language

        # stopwords class
        self.stopwords_class = config.stopwords_class

    def get_title(self):
        """\
        Fetch the article title and analyze it
        """

        title = ''
        doc = self.article.doc

        title_element = self.parser.getElementsByTag(doc, tag='title')
        # no title found
        if title_element is None or len(title_element) == 0:
            return title

        # title elem found
        title_text = self.parser.getText(title_element[0])
        used_delimeter = False

        # split title with |
        if '|' in title_text:
            title_text = self.split_title(title_text, PIPE_SPLITTER)
            used_delimeter = True

        # split title with -
        if not used_delimeter and '-' in title_text:
            title_text = self.split_title(title_text, DASH_SPLITTER)
            used_delimeter = True

        # split title with »
        if not used_delimeter and u'»' in title_text:
            title_text = self.split_title(title_text, ARROWS_SPLITTER)
            used_delimeter = True

        # split title with :
        if not used_delimeter and ':' in title_text:
            title_text = self.split_title(title_text, COLON_SPLITTER)
            used_delimeter = True

        title = MOTLEY_REPLACEMENT.replaceAll(title_text)
        return title

    def split_title(self, title, splitter):
        """\
        Split the title to best part possible
        """
        large_text_length = 0
        large_text_index = 0
        title_pieces = splitter.split(title)

        # find the largest title piece
        for i in range(len(title_pieces)):
            current = title_pieces[i]
            if len(current) > large_text_length:
                large_text_length = len(current)
                large_text_index = i

        # replace content
        title = title_pieces[large_text_index]
        return TITLE_REPLACEMENTS.replaceAll(title).strip()

    def get_favicon(self):
        """\
        Extract the favicon from a website
        http://en.wikipedia.org/wiki/Favicon
        <link rel="shortcut icon" type="image/png" href="favicon.png" />
        <link rel="icon" type="image/png" href="favicon.png" />
        """
        kwargs = {'tag': 'link', 'attr': 'rel', 'value': 'icon'}
        meta = self.parser.getElementsByTag(self.article.doc, **kwargs)
        if meta:
            favicon = self.parser.getAttribute(meta[0], 'href')
            return favicon
        return ''

    def get_meta_lang(self):
        """\
        Extract content language from meta
        """
        # we have a lang attribute in html
        attr = self.parser.getAttribute(self.article.doc, attr='lang')
        if attr is None:
            # look up for a Content-Language in meta
            items = [
                {'tag': 'meta', 'attr': 'http-equiv', 'value': 'content-language'},
                {'tag': 'meta', 'attr': 'name', 'value': 'lang'}
            ]
            for item in items:
                meta = self.parser.getElementsByTag(self.article.doc, **item)
                if meta:
                    attr = self.parser.getAttribute(meta[0], attr='content')
                    break

        if attr:
            value = attr[:2]
            if re.search(RE_LANG, value):
                return value.lower()

        return None

    def get_meta_content(self, doc, metaName):
        """\
        Extract a given meta content form document
        """
        meta = self.parser.css_select(doc, metaName)
        content = None

        if meta is not None and len(meta) > 0:
            content = self.parser.getAttribute(meta[0], 'content')

        if content:
            return content.strip()

        return ''

    def get_meta_description(self):
        """\
        if the article has meta description set in the source, use that
        """
        return self.get_meta_content(self.article.doc, "meta[name=description]")

    def get_meta_keywords(self):
        """\
        if the article has meta keywords set in the source, use that
        """
        return self.get_meta_content(self.article.doc, "meta[name=keywords]")

    def get_canonical_link(self):
        """\
        if the article has meta canonical link set in the url
        """
        if self.article.final_url:
            kwargs = {'tag': 'link', 'attr': 'rel', 'value': 'canonical'}
            meta = self.parser.getElementsByTag(self.article.doc, **kwargs)
            if meta is not None and len(meta) > 0:
                href = self.parser.getAttribute(meta[0], 'href')
                if href:
                    href = href.strip()
                    o = urlparse(href)
                    if not o.hostname:
                        z = urlparse(self.article.final_url)
                        domain = '%s://%s' % (z.scheme, z.hostname)
                        href = urljoin(domain, href)
                    return href
        return self.article.final_url

    def get_domain(self):
        if self.article.final_url:
            o = urlparse(self.article.final_url)
            return o.hostname
        return None

    def extract_tags(self):
        node = self.article.doc

        # node doesn't have chidren
        if len(list(node)) == 0:
            return NO_STRINGS

        elements = self.parser.css_select(node, A_REL_TAG_SELECTOR)
        if not elements:
            elements = self.parser.css_select(node, A_HREF_TAG_SELECTOR)
            if not elements:
                return NO_STRINGS

        tags = []
        for el in elements:
            tag = self.parser.getText(el)
            if tag:
                tags.append(tag)

        return set(tags)

    def calculate_best_node(self):
        doc = self.article.doc
        top_node = None
        nodes_to_check = self.nodes_to_check(doc)

        starting_boost = float(1.0)
        cnt = 0
        i = 0
        parent_nodes = []
        nodes_with_text = []

        for node in nodes_to_check:
            text_node = self.parser.getText(node)
            word_stats = self.stopwords_class(language=self.language).get_stopword_count(text_node)
            high_link_density = self.is_highlink_density(node)
            if word_stats.get_stopword_count() > 2 and not high_link_density:
                nodes_with_text.append(node)

        nodes_number = len(nodes_with_text)
        negative_scoring = 0
        bottom_negativescore_nodes = float(nodes_number) * 0.25

        for node in nodes_with_text:
            boost_score = float(0)
            # boost
            if(self.is_boostable(node)):
                if cnt >= 0:
                    boost_score = float((1.0 / starting_boost) * 50)
                    starting_boost += 1
            # nodes_number
            if nodes_number > 15:
                if (nodes_number - i) <= bottom_negativescore_nodes:
                    booster = float(bottom_negativescore_nodes - (nodes_number - i))
                    boost_score = float(-pow(booster, float(2)))
                    negscore = abs(boost_score) + negative_scoring
                    if negscore > 40:
                        boost_score = float(5)

            text_node = self.parser.getText(node)
            word_stats = self.stopwords_class(language=self.language).get_stopword_count(text_node)
            upscore = int(word_stats.get_stopword_count() + boost_score)

            # parent node
            parent_node = self.parser.getParent(node)
            self.update_score(parent_node, upscore)
            self.update_node_count(parent_node, 1)

            if parent_node not in parent_nodes:
                parent_nodes.append(parent_node)

            # parentparent node
            parent_parent_node = self.parser.getParent(parent_node)
            if parent_parent_node is not None:
                self.update_node_count(parent_parent_node, 1)
                self.update_score(parent_parent_node, upscore / 2)
                if parent_parent_node not in parent_nodes:
                    parent_nodes.append(parent_parent_node)
            cnt += 1
            i += 1

        top_node_score = 0
        for e in parent_nodes:
            score = self.get_score(e)

            if score > top_node_score:
                top_node = e
                top_node_score = score

            if top_node is None:
                top_node = e

        return top_node

    def is_boostable(self, node):
        """\
        alot of times the first paragraph might be the caption under an image
        so we'll want to make sure if we're going to boost a parent node that
        it should be connected to other paragraphs,
        at least for the first n paragraphs so we'll want to make sure that
        the next sibling is a paragraph and has at
        least some substatial weight to it
        """
        para = "p"
        steps_away = 0
        minimum_stopword_count = 5
        max_stepsaway_from_node = 3

        nodes = self.walk_siblings(node)
        for current_node in nodes:
            # p
            current_node_tag = self.parser.getTag(current_node)
            if current_node_tag == para:
                if steps_away >= max_stepsaway_from_node:
                    return False
                paraText = self.parser.getText(current_node)
                word_stats = self.stopwords_class(language=self.language).get_stopword_count(paraText)
                if word_stats.get_stopword_count() > minimum_stopword_count:
                    return True
                steps_away += 1
        return False

    def walk_siblings(self, node):
        current_sibling = self.parser.previousSibling(node)
        b = []
        while current_sibling is not None:
            b.append(current_sibling)
            previousSibling = self.parser.previousSibling(current_sibling)
            current_sibling = None if previousSibling is None else previousSibling
        return b

    def add_siblings(self, top_node):
        baselinescore_siblings_para = self.get_siblings_score(top_node)
        results = self.walk_siblings(top_node)
        for current_node in results:
            ps = self.get_siblings_content(current_node, baselinescore_siblings_para)
            for p in ps:
                top_node.insert(0, p)
        return top_node

    def get_siblings_content(self, current_sibling, baselinescore_siblings_para):
        """\
        adds any siblings that may have a decent score to this node
        """
        if current_sibling.tag == 'p' and len(self.parser.getText(current_sibling)) > 0:
            e0 = current_sibling
            if e0.tail:
                e0 = deepcopy(e0)
                e0.tail = ''
            return [e0]
        else:
            potential_paragraphs = self.parser.getElementsByTag(current_sibling, tag='p')
            if potential_paragraphs is None:
                return None
            else:
                ps = []
                for first_paragraph in potential_paragraphs:
                    text = self.parser.getText(first_paragraph)
                    if len(text) > 0:
                        word_stats = self.stopwords_class(language=self.language).get_stopword_count(text)
                        paragraph_score = word_stats.get_stopword_count()
                        sibling_baseline_score = float(.30)
                        high_link_density = self.is_highlink_density(first_paragraph)
                        score = float(baselinescore_siblings_para * sibling_baseline_score)
                        if score < paragraph_score and not high_link_density:
                            p = self.parser.createElement(tag='p', text=text, tail=None)
                            ps.append(p)
                return ps

    def get_siblings_score(self, top_node):
        """\
        we could have long articles that have tons of paragraphs
        so if we tried to calculate the base score against
        the total text score of those paragraphs it would be unfair.
        So we need to normalize the score based on the average scoring
        of the paragraphs within the top node.
        For example if our total score of 10 paragraphs was 1000
        but each had an average value of 100 then 100 should be our base.
        """
        base = 100000
        paragraphs_number = 0
        paragraphs_score = 0
        nodes_to_check = self.parser.getElementsByTag(top_node, tag='p')

        for node in nodes_to_check:
            text_node = self.parser.getText(node)
            word_stats = self.stopwords_class(language=self.language).get_stopword_count(text_node)
            high_link_density = self.is_highlink_density(node)
            if word_stats.get_stopword_count() > 2 and not high_link_density:
                paragraphs_number += 1
                paragraphs_score += word_stats.get_stopword_count()

        if paragraphs_number > 0:
            base = paragraphs_score / paragraphs_number

        return base

    def update_score(self, node, addToScore):
        """\
        adds a score to the gravityScore Attribute we put on divs
        we'll get the current score then add the score
        we're passing in to the current
        """
        current_score = 0
        score_string = self.parser.getAttribute(node, 'gravityScore')
        if score_string:
            current_score = int(score_string)

        new_score = current_score + addToScore
        self.parser.setAttribute(node, "gravityScore", str(new_score))

    def update_node_count(self, node, add_to_count):
        """\
        stores how many decent nodes are under a parent node
        """
        current_score = 0
        count_string = self.parser.getAttribute(node, 'gravityNodes')
        if count_string:
            current_score = int(count_string)

        new_score = current_score + add_to_count
        self.parser.setAttribute(node, "gravityNodes", str(new_score))

    def is_highlink_density(self, e):
        """\
        checks the density of links within a node,
        is there not much text and most of it contains linky shit?
        if so it's no good
        """
        links = self.parser.getElementsByTag(e, tag='a')
        if links is None or len(links) == 0:
            return False

        text = self.parser.getText(e)
        words = text.split(' ')
        words_number = float(len(words))
        sb = []
        for link in links:
            sb.append(self.parser.getText(link))

        linkText = ''.join(sb)
        linkWords = linkText.split(' ')
        numberOfLinkWords = float(len(linkWords))
        numberOfLinks = float(len(links))
        linkDivisor = float(numberOfLinkWords / words_number)
        score = float(linkDivisor * numberOfLinks)
        if score >= 1.0:
            return True
        return False
        # return True if score > 1.0 else False

    def get_score(self, node):
        """\
        returns the gravityScore as an integer from this node
        """
        return self.get_node_gravity_score(node) or 0

    def get_node_gravity_score(self, node):
        grvScoreString = self.parser.getAttribute(node, 'gravityScore')
        if not grvScoreString:
            return None
        return int(grvScoreString)

    def nodes_to_check(self, doc):
        """\
        returns a list of nodes we want to search
        on like paragraphs and tables
        """
        nodes_to_check = []
        for tag in ['p', 'pre', 'td']:
            items = self.parser.getElementsByTag(doc, tag=tag)
            nodes_to_check += items
        return nodes_to_check

    def is_table_and_no_para_exist(self, e):
        subParagraphs = self.parser.getElementsByTag(e, tag='p')
        for p in subParagraphs:
            txt = self.parser.getText(p)
            if len(txt) < 25:
                self.parser.remove(p)

        subParagraphs2 = self.parser.getElementsByTag(e, tag='p')
        if len(subParagraphs2) == 0 and e.tag is not "td":
            return True
        return False

    def is_nodescore_threshold_met(self, node, e):
        top_node_score = self.get_score(node)
        current_nodeScore = self.get_score(e)
        thresholdScore = float(top_node_score * .08)

        if (current_nodeScore < thresholdScore) and e.tag != 'td':
            return False
        return True

    def post_cleanup(self):
        """\
        remove any divs that looks like non-content,
        clusters of links, or paras with no gusto
        """
        targetNode = self.article.top_node
        node = self.add_siblings(targetNode)
        for e in self.parser.getChildren(node):
            e_tag = self.parser.getTag(e)
            if e_tag != 'p':
                if self.is_highlink_density(e) \
                    or self.is_table_and_no_para_exist(e) \
                    or not self.is_nodescore_threshold_met(node, e):
                    self.parser.remove(e)
        return node


class StandardContentExtractor(ContentExtractor):
    pass

########NEW FILE########
__FILENAME__ = extractors
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import re
import os
from urlparse import urlparse, urljoin
from goose.utils import FileHelper
from goose.images.image import Image
from goose.images.utils import ImageUtils

KNOWN_IMG_DOM_NAMES = [
    "yn-story-related-media",
    "cnn_strylccimg300cntr",
    "big_photo",
    "ap-smallphoto-a",
]


class DepthTraversal(object):

    def __init__(self, node, parent_depth, sibling_depth):
        self.node = node
        self.parent_depth = parent_depth
        self.sibling_depth = sibling_depth


class ImageExtractor(object):
    pass


class UpgradedImageIExtractor(ImageExtractor):

    def __init__(self, config, article):
        self.custom_site_mapping = {}
        self.load_customesite_mapping()

        # article
        self.article = article

        # config
        self.config = config

        # parser
        self.parser = self.config.get_parser()

        # What's the minimum bytes for an image we'd accept is
        self.images_min_bytes = 4000

        # the webpage url that we're extracting content from
        self.target_url = article.final_url

        # stores a hash of our url for
        # reference and image processing
        self.link_hash = article.link_hash

        # this lists all the known bad button names that we have
        self.badimages_names_re = re.compile(
            ".html|.gif|.ico|button|twitter.jpg|facebook.jpg|ap_buy_photo"
            "|digg.jpg|digg.png|delicious.png|facebook.png|reddit.jpg"
            "|doubleclick|diggthis|diggThis|adserver|/ads/|ec.atdmt.com"
            "|mediaplex.com|adsatt|view.atdmt"
        )

    def get_best_image(self, doc, topNode):
        image = self.check_known_elements()
        if image:
            return image

        image = self.check_large_images(topNode, 0, 0)
        if image:
            return image

        image = self.check_meta_tag()
        if image:
            return image
        return Image()

    def check_meta_tag(self):
        # check link tag
        image = self.check_link_tag()
        if image:
            return image

        # check opengraph tag
        image = self.check_opengraph_tag()
        if image:
            return image

    def check_large_images(self, node, parent_depth_level, sibling_depth_level):
        """\
        although slow the best way to determine the best image is to download
        them and check the actual dimensions of the image when on disk
        so we'll go through a phased approach...
        1. get a list of ALL images from the parent node
        2. filter out any bad image names that we know of (gifs, ads, etc..)
        3. do a head request on each file to make sure it meets
           our bare requirements
        4. any images left over let's do a full GET request,
           download em to disk and check their dimensions
        5. Score images based on different factors like height/width
           and possibly things like color density
        """
        good_images = self.get_image_candidates(node)

        if good_images:
            scored_images = self.fetch_images(good_images, parent_depth_level)
            if scored_images:
                highscore_image = sorted(scored_images.items(),
                                        key=lambda x: x[1], reverse=True)[0][0]
                main_image = Image()
                main_image.src = highscore_image.src
                main_image.width = highscore_image.width
                main_image.height = highscore_image.height
                main_image.extraction_type = "bigimage"
                main_image.confidence_score = 100 / len(scored_images) \
                                    if len(scored_images) > 0 else 0
                return main_image

        depth_obj = self.get_depth_level(node, parent_depth_level, sibling_depth_level)
        if depth_obj:
            return self.check_large_images(depth_obj.node,
                            depth_obj.parent_depth, depth_obj.sibling_depth)

        return None

    def get_depth_level(self, node, parent_depth, sibling_depth):
        MAX_PARENT_DEPTH = 2
        if parent_depth > MAX_PARENT_DEPTH:
            return None
        else:
            sibling_node = self.parser.previousSibling(node)
            if sibling_node is not None:
                return DepthTraversal(sibling_node, parent_depth, sibling_depth + 1)
            elif node is not None:
                parent = self.parser.getParent(node)
                if parent is not None:
                    return DepthTraversal(parent, parent_depth + 1, 0)
        return None

    def fetch_images(self, images, depth_level):
        """\
        download the images to temp disk and set their dimensions
        - we're going to score the images in the order in which
          they appear so images higher up will have more importance,
        - we'll count the area of the 1st image as a score
          of 1 and then calculate how much larger or small each image after it is
        - we'll also make sure to try and weed out banner
          type ad blocks that have big widths and small heights or vice versa
        - so if the image is 3rd found in the dom it's
          sequence score would be 1 / 3 = .33 * diff
          in area from the first image
        """
        image_results = {}
        initial_area = float(0.0)
        total_score = float(0.0)
        cnt = float(1.0)
        MIN_WIDTH = 50
        for image in images[:30]:
            src = self.parser.getAttribute(image, attr='src')
            src = self.build_image_path(src)
            local_image = self.get_local_image(src)
            width = local_image.width
            height = local_image.height
            src = local_image.src
            file_extension = local_image.file_extension

            if file_extension != '.gif' or file_extension != 'NA':
                if (depth_level >= 1 and local_image.width > 300) or depth_level < 1:
                    if not self.is_banner_dimensions(width, height):
                        if width > MIN_WIDTH:
                            sequence_score = float(1.0 / cnt)
                            area = float(width * height)
                            total_score = float(0.0)

                            if initial_area == 0:
                                initial_area = area * float(1.48)
                                total_score = 1
                            else:
                                area_difference = float(area / initial_area)
                                total_score = sequence_score * area_difference

                            image_results.update({local_image: total_score})
                            cnt += 1
                            cnt += 1
        return image_results

    def get_image(self, element, src, score=100, extraction_type="N/A"):
        # build the Image object
        image = Image()
        image.src = self.build_image_path(src)
        image.extraction_type = extraction_type
        image.confidence_score = score

        # check if we have a local image
        # in order to add more information
        # on the Image object
        local_image = self.get_local_image(image.src)
        if local_image:
            image.bytes = local_image.bytes
            image.height = local_image.height
            image.width = local_image.width

        # return the image
        return image

    def is_banner_dimensions(self, width, height):
        """\
        returns true if we think this is kind of a bannery dimension
        like 600 / 100 = 6 may be a fishy dimension for a good image
        """
        if width == height:
            return False

        if width > height:
            diff = float(width / height)
            if diff > 5:
                return True

        if height > width:
            diff = float(height / width)
            if diff > 5:
                return True

        return False

    def get_node_images(self, node):
        images = self.parser.getElementsByTag(node, tag='img')
        if images is not None and len(images) < 1:
            return None
        return images

    def filter_bad_names(self, images):
        """\
        takes a list of image elements
        and filters out the ones with bad names
        """
        good_images = []
        for image in images:
            if self.is_valid_filename(image):
                good_images.append(image)
        return good_images if len(good_images) > 0 else None

    def is_valid_filename(self, imageNode):
        """\
        will check the image src against a list
        of bad image files we know of like buttons, etc...
        """
        src = self.parser.getAttribute(imageNode, attr='src')

        if not src:
            return False

        if self.badimages_names_re.search(src):
            return False

        return True

    def get_image_candidates(self, node):
        good_images = []
        filtered_images = []
        images = self.get_node_images(node)
        if images:
            filtered_images = self.filter_bad_names(images)
        if filtered_images:
            good_images = self.get_images_bytesize_match(filtered_images)
        return good_images

    def get_images_bytesize_match(self, images):
        """\
        loop through all the images and find the ones
        that have the best bytez to even make them a candidate
        """
        cnt = 0
        MAX_BYTES_SIZE = 15728640
        good_images = []
        for image in images:
            if cnt > 30:
                return good_images
            src = self.parser.getAttribute(image, attr='src')
            src = self.build_image_path(src)
            local_image = self.get_local_image(src)
            if local_image:
                bytes = local_image.bytes
                if (bytes == 0 or bytes > self.images_min_bytes) \
                        and bytes < MAX_BYTES_SIZE:
                    good_images.append(image)
                else:
                    images.remove(image)
            cnt += 1
        return good_images if len(good_images) > 0 else None

    def get_node(self, node):
        return node if node else None

    def check_link_tag(self):
        """\
        checks to see if we were able to
        find open link_src on this page
        """
        node = self.article.raw_doc
        meta = self.parser.getElementsByTag(node, tag='link', attr='rel', value='image_src')
        for item in meta:
            src = self.parser.getAttribute(item, attr='href')
            if src:
                return self.get_image(item, src, extraction_type='linktag')
        return None

    def check_opengraph_tag(self):
        """\
        checks to see if we were able to
        find open graph tags on this page
        """
        node = self.article.raw_doc
        meta = self.parser.getElementsByTag(node, tag='meta', attr='property', value='og:image')
        for item in meta:
            src = self.parser.getAttribute(item, attr='content')
            if src:
                return self.get_image(item, src, extraction_type='opengraph')
        return None

    def get_local_image(self, src):
        """\
        returns the bytes of the image file on disk
        """
        local_image = ImageUtils.store_image(None,
                                    self.link_hash, src, self.config)
        return local_image

    def get_clean_domain(self):
        if self.article.domain:
            return self.article.domain.replace('www.', '')
        return None

    def check_known_elements(self):
        """\
        in here we check for known image contains from sites
        we've checked out like yahoo, techcrunch, etc... that have
        * known  places to look for good images.
        * TODO: enable this to use a series of settings files
          so people can define what the image ids/classes
          are on specific sites
        """
        domain = self.get_clean_domain()
        if domain in self.custom_site_mapping.keys():
            classes = self.custom_site_mapping.get(domain).split('|')
            for classname in classes:
                KNOWN_IMG_DOM_NAMES.append(classname)

        image = None
        doc = self.article.raw_doc

        def _check_elements(elements):
            image = None
            for element in elements:
                tag = self.parser.getTag(element)
                if tag == 'img':
                    image = element
                    return image
                else:
                    images = self.parser.getElementsByTag(element, tag='img')
                    if images:
                        image = images[0]
                        return image
            return image

        # check for elements with known id
        for css in KNOWN_IMG_DOM_NAMES:
            elements = self.parser.getElementsByTag(doc, attr="id", value=css)
            image = _check_elements(elements)
            if image is not None:
                src = self.parser.getAttribute(image, attr='src')
                if src:
                    return self.get_image(image, src, score=90, extraction_type='known')

        # check for elements with known classes
        for css in KNOWN_IMG_DOM_NAMES:
            elements = self.parser.getElementsByTag(doc, attr='class', value=css)
            image = _check_elements(elements)
            if image is not None:
                src = self.parser.getAttribute(image, attr='src')
                if src:
                    return self.get_image(image, src, score=90, extraction_type='known')

        return None

    def build_image_path(self, src):
        """\
        This method will take an image path and build
        out the absolute path to that image
        * using the initial url we crawled
          so we can find a link to the image
          if they use relative urls like ../myimage.jpg
        """
        o = urlparse(src)
        # we have a full url
        if o.hostname:
            return o.geturl()
        # we have a relative url
        return urljoin(self.target_url, src)

    def load_customesite_mapping(self):
        # TODO
        path = os.path.join('images', 'known-image-css.txt')
        data_file = FileHelper.loadResourceFile(path)
        lines = data_file.splitlines()
        for line in lines:
            domain, css = line.split('^')
            self.custom_site_mapping.update({domain: css})

########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class Image(object):

    def __init__(self):
        # holds the Element node of the image we think is top dog
        self.top_image_node = None

        # holds the src of the image
        self.src = ""

        # how confident are we in this image extraction?
        # the most images generally the less confident
        self.confidence_score = float(0.0)

        # Height of the image in pixels
        self.height = 0

        # width of the image in pixels
        self.width = 0

        # what kind of image extraction was used for this?
        # bestGuess, linkTag, openGraph tags?
        self.extraction_type = "NA"

        # stores how many bytes this image is.
        self.bytes = long(0)

    def get_src(self):
        return self.src


class ImageDetails(object):

    def __init__(self):

        # the width of the image
        self.width = 0

        # height of the image
        self.height = 0

        # the mime_type of the image JPEG / PNG
        self.mime_type = None

    def get_width(self):
        return self.width

    def set_width(self, width):
        self.width = width

    def get_height(self):
        return self.height

    def set_height(self, height):
        self.height = height

    def get_mime_type(self):
        return self.mime_type

    def set_mime_type(self, mime_type):
        self.mime_type = mime_type


class LocallyStoredImage(object):

    def __init__(self, src='', local_filename='',
        link_hash='', bytes=long(0), file_extension='', height=0, width=0):
        self.src = src
        self.local_filename = local_filename
        self.link_hash = link_hash
        self.bytes = bytes
        self.file_extension = file_extension
        self.height = height
        self.width = width

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import hashlib
import os
import urllib2
from PIL import Image
from goose.utils.encoding import smart_str
from goose.images.image import ImageDetails
from goose.images.image import LocallyStoredImage


class ImageUtils(object):

    @classmethod
    def get_image_dimensions(self, identify_program, path):
        image = Image.open(path)
        image_details = ImageDetails()
        image_details.set_mime_type(image.format)
        width, height = image.size
        image_details.set_width(width)
        image_details.set_height(height)
        return image_details

    @classmethod
    def store_image(self, http_client, link_hash, src, config):
        """\
        Writes an image src http string to disk as a temporary file
        and returns the LocallyStoredImage object
        that has the info you should need on the image
        """
        # check for a cache hit already on disk
        image = self.read_localfile(link_hash, src, config)
        if image:
            return image

        # no cache found download the image
        data = self.fetch(http_client, src)
        if data:
            image = self.write_localfile(data, link_hash, src, config)
            if image:
                return image

        return None

    @classmethod
    def get_mime_type(self, image_details):
        mime_type = image_details.get_mime_type().lower()
        mimes = {
            'png': '.png',
            'jpg': '.jpg',
            'jpeg': '.jpg',
            'gif': '.gif',
        }
        return mimes.get(mime_type, 'NA')

    @classmethod
    def read_localfile(self, link_hash, src, config):
        local_image_name = self.get_localfile_name(link_hash, src, config)
        if os.path.isfile(local_image_name):
            identify = config.imagemagick_identify_path
            image_details = self.get_image_dimensions(identify, local_image_name)
            file_extension = self.get_mime_type(image_details)
            bytes = os.path.getsize(local_image_name)
            return LocallyStoredImage(
                src=src,
                local_filename=local_image_name,
                link_hash=link_hash,
                bytes=bytes,
                file_extension=file_extension,
                height=image_details.get_height(),
                width=image_details.get_width()
            )
        return None

    @classmethod
    def write_localfile(self, entity, link_hash, src, config):
        local_path = self.get_localfile_name(link_hash, src, config)
        f = open(local_path, 'wb')
        f.write(entity)
        f.close()
        return self.read_localfile(link_hash, src, config)

    @classmethod
    def get_localfile_name(self, link_hash, src, config):
        image_hash = hashlib.md5(smart_str(src)).hexdigest()
        return os.path.join(config.local_storage_path, '%s_%s' % (link_hash, image_hash))

    @classmethod
    def clean_src_string(self, src):
        return src.replace(" ", "%20")

    @classmethod
    def fetch(self, http_client, src):
        try:
            req = urllib2.Request(src)
            f = urllib2.urlopen(req)
            data = f.read()
            return data
        except:
            return None

########NEW FILE########
__FILENAME__ = network
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import urllib2


class HtmlFetcher(object):

    def __init__(self, config):
        # set header
        self.headers = {'User-agent': config.browser_user_agent}

    def get_url(self):
        # if we have a result
        # get the final_url
        if self.result is not None:
            return self.result.geturl()
        return None

    def get_html(self, url):
        # utf-8 encode unicode url
        if isinstance(url, unicode):
            url = url.encode('utf-8')

        # set request
        self.request = urllib2.Request(url, headers=self.headers)

        # do request
        try:
            self.result = urllib2.urlopen(self.request)
        except:
            self.result = None

        # read the result content
        if self.result is not None:
            return self.result.read()
        return None

########NEW FILE########
__FILENAME__ = outputformatters
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from HTMLParser import HTMLParser
from goose.text import innerTrim


class OutputFormatter(object):

    def __init__(self, config, article):
        # config
        self.config = config

        # article
        self.article = article

        # parser
        self.parser = self.config.get_parser()

        # stopwords class
        self.stopwords_class = config.stopwords_class

        # top node
        self.top_node = None

    def get_language(self):
        """\
        Returns the language is by the article or
        the configuration language
        """
        # we don't want to force the target laguage
        # so we use the article.meta_lang
        if self.config.use_meta_language == True:
            if self.article.meta_lang:
                return self.article.meta_lang[:2]
        return self.config.target_language

    def get_top_node(self):
        return self.top_node

    def get_formatted_text(self):
        self.top_node = self.article.top_node
        self.remove_negativescores_nodes()
        self.links_to_text()
        self.add_newline_to_br()
        self.replace_with_text()
        self.remove_fewwords_paragraphs()
        return self.convert_to_text()

    def convert_to_text(self):
        txts = []
        for node in list(self.get_top_node()):
            txt = self.parser.getText(node)
            if txt:
                txt = HTMLParser().unescape(txt)
                txt_lis = innerTrim(txt).split(r'\n')
                txts.extend(txt_lis)
        return '\n\n'.join(txts)

    def add_newline_to_br(self):
        for e in self.parser.getElementsByTag(self.top_node, tag='br'):
            e.text = r'\n'

    def links_to_text(self):
        """\
        cleans up and converts any nodes that
        should be considered text into text
        """
        self.parser.stripTags(self.get_top_node(), 'a')

    def remove_negativescores_nodes(self):
        """\
        if there are elements inside our top node
        that have a negative gravity score,
        let's give em the boot
        """
        gravity_items = self.parser.css_select(self.top_node, "*[gravityScore]")
        for item in gravity_items:
            score = self.parser.getAttribute(item, 'gravityScore')
            score = int(score, 0)
            if score < 1:
                item.getparent().remove(item)

    def replace_with_text(self):
        """\
        replace common tags with just
        text so we don't have any crazy formatting issues
        so replace <br>, <i>, <strong>, etc....
        with whatever text is inside them
        code : http://lxml.de/api/lxml.etree-module.html#strip_tags
        """
        self.parser.stripTags(self.get_top_node(), 'b', 'strong', 'i', 'br', 'sup')

    def remove_fewwords_paragraphs(self):
        """\
        remove paragraphs that have less than x number of words,
        would indicate that it's some sort of link
        """
        all_nodes = self.parser.getElementsByTags(self.get_top_node(), ['*'])
        all_nodes.reverse()
        for el in all_nodes:
            tag = self.parser.getTag(el)
            text = self.parser.getText(el)
            stop_words = self.stopwords_class(language=self.get_language()).get_stopword_count(text)
            if (tag != 'br' or text != '\\r') and stop_words.get_stopword_count() < 3 \
                and len(self.parser.getElementsByTag(el, tag='object')) == 0 \
                and len(self.parser.getElementsByTag(el, tag='embed')) == 0:
                self.parser.remove(el)
            # TODO
            # check if it is in the right place
            else:
                trimmed = self.parser.getText(el)
                if trimmed.startswith("(") and trimmed.endswith(")"):
                    self.parser.remove(el)


class StandardOutputFormatter(OutputFormatter):
    pass

########NEW FILE########
__FILENAME__ = parsers
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import lxml.html
from lxml.html import soupparser
from lxml import etree
from copy import deepcopy
from goose.text import innerTrim
from goose.text import encodeValue


class Parser(object):

    @classmethod
    def xpath_re(self, node, expression):
        regexp_namespace = "http://exslt.org/regular-expressions"
        items = node.xpath(expression, namespaces={'re': regexp_namespace})
        return items

    @classmethod
    def drop_tag(self, nodes):
        if isinstance(nodes, list):
            for node in nodes:
                node.drop_tag()
        else:
            nodes.drop_tag()

    @classmethod
    def css_select(self, node, selector):
        return node.cssselect(selector)

    @classmethod
    def fromstring(self, html):
        html = encodeValue(html)
        self.doc = lxml.html.fromstring(html)
        return self.doc

    @classmethod
    def nodeToString(self, node):
        return etree.tostring(node)

    @classmethod
    def replaceTag(self, node, tag):
        node.tag = tag

    @classmethod
    def stripTags(self, node, *tags):
        etree.strip_tags(node, *tags)

    @classmethod
    def getElementById(self, node, idd):
        selector = '//*[@id="%s"]' % idd
        elems = node.xpath(selector)
        if elems:
            return elems[0]
        return None

    @classmethod
    def getElementsByTag(self, node, tag=None, attr=None, value=None, childs=False):
        NS = "http://exslt.org/regular-expressions"
        # selector = tag or '*'
        selector = 'descendant-or-self::%s' % (tag or '*')
        if attr and value:
            selector = '%s[re:test(@%s, "%s", "i")]' % (selector, attr, value)
        elems = node.xpath(selector, namespaces={"re": NS})
        # remove the root node
        # if we have a selection tag
        if node in elems and (tag or childs):
            elems.remove(node)
        return elems

    @classmethod
    def appendChild(self, node, child):
        node.append(child)

    @classmethod
    def childNodes(self, node):
        return list(node)

    @classmethod
    def childNodesWithText(self, node):
        root = node
        # create the first text node
        # if we have some text in the node
        if root.text:
            t = lxml.html.HtmlElement()
            t.text = root.text
            t.tag = 'text'
            root.text = None
            root.insert(0, t)
        # loop childs
        for c, n in enumerate(list(root)):
            idx = root.index(n)
            # don't process texts nodes
            if n.tag == 'text':
                continue
            # create a text node for tail
            if n.tail:
                t = self.createElement(tag='text', text=n.tail, tail=None)
                root.insert(idx + 1, t)
        return list(root)

    @classmethod
    def textToPara(self, text):
        return self.fromstring(text)

    @classmethod
    def getChildren(self, node):
        return node.getchildren()

    @classmethod
    def getElementsByTags(self, node, tags):
        selector = ','.join(tags)
        elems = self.css_select(node, selector)
        # remove the root node
        # if we have a selection tag
        if node in elems:
            elems.remove(node)
        return elems

    @classmethod
    def createElement(self, tag='p', text=None, tail=None):
        t = lxml.html.HtmlElement()
        t.tag = tag
        t.text = text
        t.tail = tail
        return t

    @classmethod
    def getComments(self, node):
        return node.xpath('//comment()')

    @classmethod
    def getParent(self, node):
        return node.getparent()

    @classmethod
    def remove(self, node):
        parent = node.getparent()
        if parent is not None:
            if node.tail:
                prev = node.getprevious()
                if prev is None:
                    if not parent.text:
                        parent.text = ''
                    parent.text += u' ' + node.tail
                else:
                    if not prev.tail:
                        prev.tail = ''
                    prev.tail += u' ' + node.tail
            node.clear()
            parent.remove(node)

    @classmethod
    def getTag(self, node):
        return node.tag

    @classmethod
    def getText(self, node):
        txts = [i for i in node.itertext()]
        return innerTrim(u' '.join(txts).strip())

    @classmethod
    def previousSiblings(self, node):
        nodes = []
        for c, n in enumerate(node.itersiblings(preceding=True)):
            nodes.append(n)
        return nodes

    @classmethod
    def previousSibling(self, node):
        nodes = []
        for c, n in enumerate(node.itersiblings(preceding=True)):
            nodes.append(n)
            if c == 0:
                break
        return nodes[0] if nodes else None

    @classmethod
    def nextSibling(self, node):
        nodes = []
        for c, n in enumerate(node.itersiblings(preceding=False)):
            nodes.append(n)
            if c == 0:
                break
        return nodes[0] if nodes else None

    @classmethod
    def isTextNode(self, node):
        return True if node.tag == 'text' else False

    @classmethod
    def getAttribute(self, node, attr=None):
        if attr:
            return node.attrib.get(attr, None)
        return attr

    @classmethod
    def delAttribute(self, node, attr=None):
        if attr:
            _attr = node.attrib.get(attr, None)
            if _attr:
                del node.attrib[attr]

    @classmethod
    def setAttribute(self, node, attr=None, value=None):
        if attr and value:
            node.set(attr, value)

    @classmethod
    def outerHtml(self, node):
        e0 = node
        if e0.tail:
            e0 = deepcopy(e0)
            e0.tail = None
        return self.nodeToString(e0)


class ParserSoup(Parser):

    @classmethod
    def fromstring(self, html):
        html = encodeValue(html)
        self.doc = soupparser.fromstring(html)
        return self.doc

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import re
import string
from goose.utils import FileHelper
from goose.utils.encoding import smart_unicode
from goose.utils.encoding import smart_str
from goose.utils.encoding import DjangoUnicodeDecodeError

TABSSPACE = re.compile(r'[\s\t]+')


def innerTrim(value):
    if isinstance(value, (unicode, str)):
        # remove tab and white space
        value = re.sub(TABSSPACE, ' ', value)
        value = ''.join(value.splitlines())
        return value.strip()
    return ''


def encodeValue(value):
    string_org = value
    try:
        value = smart_unicode(value)
    except (UnicodeEncodeError, DjangoUnicodeDecodeError):
        value = smart_str(value)
    except:
        value = string_org
    return value


class WordStats(object):

    def __init__(self):
        # total number of stopwords or
        # good words that we can calculate
        self.stop_word_count = 0

        # total number of words on a node
        self.word_count = 0

        # holds an actual list
        # of the stop words we found
        self.stop_words = []

    def get_stop_words(self):
        return self.stop_words

    def set_stop_words(self, words):
        self.stop_words = words

    def get_stopword_count(self):
        return self.stop_word_count

    def set_stopword_count(self, wordcount):
        self.stop_word_count = wordcount

    def get_word_count(self):
        return self.word_count

    def set_word_count(self, cnt):
        self.word_count = cnt


class StopWords(object):

    PUNCTUATION = re.compile("[^\\p{Ll}\\p{Lu}\\p{Lt}\\p{Lo}\\p{Nd}\\p{Pc}\\s]")
    TRANS_TABLE = string.maketrans('', '')
    _cached_stop_words = {}

    def __init__(self, language='en'):
        # TODO replace 'x' with class
        # to generate dynamic path for file to load
        if not language in self._cached_stop_words:
            path = os.path.join('text', 'stopwords-%s.txt' % language)
            self._cached_stop_words[language] = set(FileHelper.loadResourceFile(path).splitlines())
        self.STOP_WORDS = self._cached_stop_words[language]

    def remove_punctuation(self, content):
        # code taken form
        # http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        return content.translate(self.TRANS_TABLE, string.punctuation)

    def candiate_words(self, stripped_input):
        return stripped_input.split(' ')

    def get_stopword_count(self, content):
        if not content:
            return WordStats()
        ws = WordStats()
        stripped_input = self.remove_punctuation(content)
        candiate_words = self.candiate_words(stripped_input)
        overlapping_stopwords = []
        c = 0
        for w in candiate_words:
            c += 1
            if w.lower() in self.STOP_WORDS:
                overlapping_stopwords.append(w.lower())

        ws.set_word_count(c)
        ws.set_stopword_count(len(overlapping_stopwords))
        ws.set_stop_words(overlapping_stopwords)
        return ws


class StopWordsChinese(StopWords):
    """
    Chinese segmentation
    """
    def __init__(self, language='zh'):
        # force zh languahe code
        super(StopWordsChinese, self).__init__(language='zh')

    def candiate_words(self, stripped_input):
        # jieba build a tree that takes sometime
        # avoid building the tree if we don't use
        # chinese language
        import jieba
        return jieba.cut(stripped_input, cut_all=True)


class StopWordsArabic(StopWords):
    """
    Arabic segmentation
    """
    def __init__(self, language='ar'):
        # force ar languahe code
        super(StopWordsArabic, self).__init__(language='ar')

    def remove_punctuation(self, content):
        return content

    def candiate_words(self, stripped_input):
        import nltk
        s = nltk.stem.isri.ISRIStemmer()
        words = []
        for word in nltk.tokenize.wordpunct_tokenize(stripped_input):
            words.append(s.stem(word))
        return words


class StopWordsKorean(StopWords):
    """
    Korean segmentation
    """
    def __init__(self, language='ko'):
        super(StopWordsKorean, self).__init__(language='ko')

    def get_stopword_count(self, content):
        if not content:
            return WordStats()
        ws = WordStats()
        stripped_input = self.remove_punctuation(content)
        candiate_words = self.candiate_words(stripped_input)
        overlapping_stopwords = []
        c = 0
        for w in candiate_words:
            c += 1
            for stop_word in self.STOP_WORDS:
                overlapping_stopwords.append(stop_word)

        ws.set_word_count(c)
        ws.set_stopword_count(len(overlapping_stopwords))
        ws.set_stop_words(overlapping_stopwords)
        return ws

########NEW FILE########
__FILENAME__ = encoding
# -*- coding: utf-8 -*-
import types
import datetime
from decimal import Decimal


class DjangoUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))


class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a UTF-8 bytestring.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode('utf-8')


def smart_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # if isinstance(s, Promise):
    #     # The input is the result of a gettext_lazy() call.
    #     return s
    return force_unicode(s, encoding, strings_only, errors)


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )


def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% in performance when s
    # is an instance of unicode. This function gets called often in that
    # setting.
    if isinstance(s, unicode):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = u' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise DjangoUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = u' '.join([force_unicode(arg, encoding, strings_only,
                    errors) for arg in s])
    return s


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    # if isinstance(s, Promise):
    #     return unicode(s).encode(encoding, errors)
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

version_info = (1, 0, 18)
__version__ = ".".join(map(str, version_info))

########NEW FILE########
__FILENAME__ = extractors
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from goose.videos.videos import Video

VIDEOS_TAGS = ['iframe', 'embed', 'object', 'video']
VIDEO_PROVIDERS = ['youtube', 'vimeo', 'dailymotion', 'kewego']


class VideoExtractor(object):
    """\
    Extracts a list of video from Article top node
    """
    def __init__(self, config, article):
        # article
        self.article = article

        # config
        self.config = config

        # parser
        self.parser = self.config.get_parser()

        # candidates
        self.candidates = []

        # movies
        self.movies = []

    def get_embed_code(self, node):
        return "".join([line.strip() for line in self.parser.nodeToString(node).splitlines()])

    def get_embed_type(self, node):
        return self.parser.getTag(node)

    def get_width(self, node):
        return self.parser.getAttribute(node, 'width')

    def get_height(self, node):
        return self.parser.getAttribute(node, 'height')

    def get_src(self, node):
        return self.parser.getAttribute(node, 'src')

    def get_provider(self, src):
        if src:
            for provider in VIDEO_PROVIDERS:
                if provider in src:
                    return provider
        return None

    def get_video(self, node):
        """
        Create a video object from a video embed
        """
        video = Video()
        video.embed_code = self.get_embed_code(node)
        video.embed_type = self.get_embed_type(node)
        video.width = self.get_width(node)
        video.height = self.get_height(node)
        video.src = self.get_src(node)
        video.provider = self.get_provider(video.src)
        return video

    def get_iframe_tag(self, node):
        return self.get_video(node)

    def get_video_tag(self, node):
        """extract html video tags"""
        return Video()

    def get_embed_tag(self, node):
        # embed node may have an object node as parent
        # in this case we want to retrieve the object node
        # instead of the embed
        parent = self.parser.getParent(node)
        if parent is not None:
            parent_tag = self.parser.getTag(parent)
            if parent_tag == 'object':
                return self.get_object_tag(node)
        return self.get_video(node)

    def get_object_tag(self, node):
        # test if object tag has en embed child
        # in this case we want to remove the embed from
        # the candidate list to avoid parsing it twice
        child_embed_tag = self.parser.getElementsByTag(node, 'embed')
        if child_embed_tag and child_embed_tag[0] in self.candidates:
            self.candidates.remove(child_embed_tag[0])

        # get the object source
        # if wa don't have a src node don't coninue
        src_node = self.parser.getElementsByTag(node, tag="param", attr="name", value="movie")
        if not src_node:
            return None

        src = self.parser.getAttribute(src_node[0], "value")

        # check provider
        provider = self.get_provider(src)
        if not provider:
            return None

        video = self.get_video(node)
        video.provider = provider
        video.src = src
        return video

    def get_videos(self):
        # candidates node
        self.candidates = self.parser.getElementsByTags(self.article.top_node, VIDEOS_TAGS)

        # loop all candidates
        # and check if src attribute belongs to a video provider
        for candidate in self.candidates:
            tag = self.parser.getTag(candidate)
            attr = "get_%s_tag" % tag
            if hasattr(self, attr):
                movie = getattr(self, attr)(candidate)
                if movie is not None and movie.provider is not None:
                    self.movies.append(movie)

        # append movies list to article
        self.article.movies = list(self.movies)

########NEW FILE########
__FILENAME__ = videos
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

class Video(object):
    """\
    Video object
    """

    def __init__(self):

        # type of embed
        # embed, object, iframe
        self.embed_type = None

        # video provider name
        self.provider = None

        # width
        self.width = None

        # height
        self.height = None

        # embed code
        self.embed_code = None

        # src
        self.src = None

########NEW FILE########
__FILENAME__ = article
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import unittest
from goose.article import Article


class TestArticle(unittest.TestCase):

    def test_instance(self):
        a = Article()
        self.assertEqual(isinstance(a, Article), True)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import urllib2
import unittest
import socket

from StringIO import StringIO


# Response
class MockResponse():
    """\
    Base mock response class
    """
    code = 200
    msg = "OK"

    def __init__(self, cls):
        self.cls = cls

    def content(self):
        return "response"

    def response(self, req):
        data = self.content(req)
        url = req.get_full_url()
        resp = urllib2.addinfourl(StringIO(data), data, url)
        resp.code = self.code
        resp.msg = self.msg
        return resp


class MockHTTPHandler(urllib2.HTTPHandler, urllib2.HTTPSHandler):
    """\
    Mocked HTTPHandler in order to query APIs locally
    """
    cls = None

    def https_open(self, req):
        return self.http_open(req)

    def http_open(self, req):
        r = self.cls.callback(self.cls)
        return r.response(req)

    @staticmethod
    def patch(cls):
        opener = urllib2.build_opener(MockHTTPHandler)
        urllib2.install_opener(opener)
        # dirty !
        for h in opener.handlers:
            if isinstance(h, MockHTTPHandler):
                h.cls = cls
        return [h for h in opener.handlers if isinstance(h, MockHTTPHandler)][0]

    @staticmethod
    def unpatch():
        # urllib2
        urllib2._opener = None


class BaseMockTests(unittest.TestCase):
    """\
    Base Mock test case
    """
    callback = MockResponse

    def setUp(self):
        # patch DNS
        self.original_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = self.new_getaddrinfo
        MockHTTPHandler.patch(self)

    def tearDown(self):
        MockHTTPHandler.unpatch()
        # DNS
        socket.getaddrinfo = self.original_getaddrinfo

    def new_getaddrinfo(self, *args):
        return [(2, 1, 6, '', ('127.0.0.1', 0))]

    def _get_current_testname(self):
        return self.id().split('.')[-1:][0]

########NEW FILE########
__FILENAME__ = configuration
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import tempfile
import unittest

from goose import Goose


class TestTempDir(unittest.TestCase):

    def test_tmp_defaut(self):
        g = Goose()
        default_local_storage_path = os.path.join(tempfile.gettempdir(), 'goose')
        self.assertEquals(g.config.local_storage_path, default_local_storage_path)

    def test_tmp_overwritten(self):
        path = '/tmp/bla'
        g = Goose({'local_storage_path': path})
        self.assertEquals(g.config.local_storage_path, path)

########NEW FILE########
__FILENAME__ = extractors
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import json

from base import BaseMockTests, MockResponse

from goose import Goose
from goose.utils import FileHelper
from goose.configuration import Configuration
from goose.text import StopWordsChinese
from goose.text import StopWordsArabic
from goose.text import StopWordsKorean


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class MockResponseExtractors(MockResponse):
    def content(self, req):
        current_test = self.cls._get_current_testname()
        path = os.path.join(CURRENT_PATH, "data", "extractors", "%s.html" % current_test)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        return content


class TestExtractionBase(BaseMockTests):
    """\
    Extraction test case
    """
    callback = MockResponseExtractors

    def getRawHtml(self):
        suite, module, cls, func = self.id().split('.')
        path = os.path.join(CURRENT_PATH, "data", module, "%s.html" % func)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        return content

    def loadData(self):
        """\

        """
        suite, module, cls, func = self.id().split('.')
        path = os.path.join(CURRENT_PATH, "data", module, "%s.json" % func)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        self.data = json.loads(content)

    def assert_cleaned_text(self, field, expected_value, result_value):
        """\

        """
        # # TODO : handle verbose level in tests
        # print "\n=======================::. ARTICLE REPORT %s .::======================\n" % self.id()
        # print 'expected_value (%s) \n' % len(expected_value)
        # print expected_value
        # print "-------"
        # print 'result_value (%s) \n' % len(result_value)
        # print result_value

        # cleaned_text is Null
        msg = u"Resulting article text was NULL!"
        self.assertNotEqual(result_value, None, msg=msg)

        # cleaned_text length
        msg = u"Article text was not as long as expected beginning!"
        self.assertTrue(len(expected_value) <= len(result_value), msg=msg)

        # clean_text value
        result_value = result_value[0:len(expected_value)]
        msg = u"The beginning of the article text was not as expected!"
        self.assertEqual(expected_value, result_value, msg=msg)

    def assert_tags(self, field, expected_value, result_value):
        """\

        """
        # as we have a set in expected_value and a list in result_value
        # make result_value a set
        expected_value = set(expected_value)

        # check if both have the same number of items
        msg = (u"expected tags set and result tags set"
                u"don't have the same number of items")
        self.assertEqual(len(result_value), len(expected_value), msg=msg)

        # check if each tag in result_value is in expected_value
        for tag in result_value:
            self.assertTrue(tag in expected_value)

    def runArticleAssertions(self, article, fields):
        """\

        """
        for field in fields:
            expected_value = self.data['expected'][field]
            result_value = getattr(article, field, None)

            # custom assertion for a given field
            assertion = 'assert_%s' % field
            if hasattr(self, assertion):
                getattr(self, assertion)(field, expected_value, result_value)
                continue

            # default assertion
            msg = u"Error %s" % field
            self.assertEqual(expected_value, result_value, msg=msg)

    def extract(self, instance):
        article = instance.extract(url=self.data['url'])
        return article

    def getConfig(self):
        config = Configuration()
        config.enable_image_fetching = False
        return config

    def getArticle(self):
        """\

        """
        # load test case data
        self.loadData()

        # basic configuration
        # no image fetching
        config = self.getConfig()
        self.parser = config.get_parser()

        # target language
        # needed for non english language most of the time
        target_language = self.data.get('target_language')
        if target_language:
            config.target_language = target_language
            config.use_meta_language = False

        # run goose
        g = Goose(config=config)
        return self.extract(g)


class TestExtractions(TestExtractionBase):

    def test_allnewlyrics1(self):
        article = self.getArticle()
        fields = ['title', 'cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_cnn1(self):
        article = self.getArticle()
        fields = ['title', 'cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessWeek1(self):
        article = self.getArticle()
        fields = ['title', 'cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessWeek2(self):
        article = self.getArticle()
        fields = ['title', 'cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessWeek3(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_cbslocal(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_elmondo1(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_elpais(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_liberation(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_lefigaro(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_techcrunch1(self):
        article = self.getArticle()
        fields = ['title', 'cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_foxNews(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_aolNews(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_huffingtonPost2(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_testHuffingtonPost(self):
        article = self.getArticle()
        fields = ['cleaned_text', 'meta_description', 'title', ]
        self.runArticleAssertions(article=article, fields=fields)

    def test_espn(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_engadget(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_msn1(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    # #########################################
    # # FAIL CHECK
    # # UNICODE
    # def test_guardian1(self):
    #     article = self.getArticle()
    #     fields = ['cleaned_text']
    #     self.runArticleAssertions(article=article, fields=fields)
    def test_time(self):
        article = self.getArticle()
        fields = ['cleaned_text', 'title']
        self.runArticleAssertions(article=article, fields=fields)

    def test_time2(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_cnet(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_yahoo(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_politico(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessinsider1(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessinsider2(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_businessinsider3(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_cnbc1(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_marketplace(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_issue24(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_issue25(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_issue28(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_issue32(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_issue4(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_gizmodo1(self):
        article = self.getArticle()
        fields = ['cleaned_text', 'meta_description', 'meta_keywords']
        self.runArticleAssertions(article=article, fields=fields)

    def test_mashable_issue_74(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)

    def test_usatoday_issue_74(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)


class TestExtractWithUrl(TestExtractionBase):

    def test_get_canonical_url(self):
        article = self.getArticle()
        fields = ['cleaned_text', 'canonical_link']
        self.runArticleAssertions(article=article, fields=fields)


class TestExtractChinese(TestExtractionBase):

    def getConfig(self):
        config = super(TestExtractChinese, self).getConfig()
        config.stopwords_class = StopWordsChinese
        return config

    def test_bbc_chinese(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)


class TestExtractArabic(TestExtractionBase):

    def getConfig(self):
        config = super(TestExtractArabic, self).getConfig()
        config.stopwords_class = StopWordsArabic
        return config

    def test_cnn_arabic(self):
        article = self.getArticle()
        fields = ['cleaned_text']
        self.runArticleAssertions(article=article, fields=fields)


class TestExtractKorean(TestExtractionBase):

    def getConfig(self):
        config = super(TestExtractKorean, self).getConfig()
        config.stopwords_class = StopWordsKorean
        return config

    def test_donga_korean(self):
        article = self.getArticle()
        fields = ['cleaned_text', 'meta_description', 'meta_keywords']
        self.runArticleAssertions(article=article, fields=fields)


class TestExtractionsRaw(TestExtractions):

    def extract(self, instance):
        article = instance.extract(raw_html=self.getRawHtml())
        return article


class TestArticleTags(TestExtractionBase):

    def test_tags_kexp(self):
        article = self.getArticle()
        fields = ['tags']
        self.runArticleAssertions(article=article, fields=fields)

    def test_tags_deadline(self):
        article = self.getArticle()
        fields = ['tags']
        self.runArticleAssertions(article=article, fields=fields)

    def test_tags_wnyc(self):
        article = self.getArticle()
        fields = ['tags']
        self.runArticleAssertions(article=article, fields=fields)

    def test_tags_cnet(self):
        article = self.getArticle()
        fields = ['tags']
        self.runArticleAssertions(article=article, fields=fields)

    def test_tags_abcau(self):
        """
        Test ABC Australia page with "topics" tags
        """
        article = self.getArticle()
        fields = ['tags']
        self.runArticleAssertions(article=article, fields=fields)

########NEW FILE########
__FILENAME__ = images
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import json
import hashlib
import unittest

from base import MockResponse
from extractors import TestExtractionBase

from goose.configuration import Configuration
from goose.images.image import Image
from goose.images.image import ImageDetails
from goose.images.utils import ImageUtils
from goose.utils import FileHelper

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class MockResponseImage(MockResponse):

    def image_content(self, req):
        md5_hash = hashlib.md5(req.get_full_url()).hexdigest()
        current_test = self.cls._get_current_testname()
        path = os.path.join(CURRENT_PATH, "data", "images", current_test, md5_hash)
        path = os.path.abspath(path)
        f = open(path, 'rb')
        content = f.read()
        f.close()
        return content

    def html_content(self, req):
        current_test = self.cls._get_current_testname()
        path = os.path.join(CURRENT_PATH, "data", "images", current_test, "%s.html" % current_test)
        path = os.path.abspath(path)
        return FileHelper.loadResourceFile(path)

    def content(self, req):
        if self.cls.data['url'] == req.get_full_url():
            return self.html_content(req)
        return self.image_content(req)


class ImageExtractionTests(TestExtractionBase):
    """\
    Base Mock test case
    """
    callback = MockResponseImage

    def loadData(self):
        """\

        """
        suite, module, cls, func = self.id().split('.')
        path = os.path.join(CURRENT_PATH, "data", module, func, "%s.json" % func)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        self.data = json.loads(content)

    def getConfig(self):
        config = Configuration()
        config.enable_image_fetching = True
        return config

    def getExpectedImage(self, expected_value):
        image = Image()
        for k, v in expected_value.items():
            setattr(image, k, v)
        return image

    def assert_top_image(self, fields, expected_value, result_image):
        # test if the result value
        # is an Goose Image instance
        msg = u"Result value is not a Goose Image instance"
        self.assertTrue(isinstance(result_image, Image), msg=msg)

        # expected image
        expected_image = self.getExpectedImage(expected_value)
        msg = u"Expected value is not a Goose Image instance"
        self.assertTrue(isinstance(expected_image, Image), msg=msg)

        # check
        msg = u"Returned Image is not the one expected"
        self.assertEqual(expected_image.src, result_image.src, msg=msg)

        fields = vars(expected_image)
        for k, v in fields.items():
            msg = u"Returned Image attribute %s is not the one expected" % k
            self.assertEqual(getattr(expected_image, k), getattr(result_image, k), msg=msg)

    def test_basic_image(self):
        article = self.getArticle()
        fields = ['top_image']
        self.runArticleAssertions(article=article, fields=fields)

    def _test_known_image_css(self, article):
        # check if we have an image in article.top_node
        images = self.parser.getElementsByTag(article.top_node,  tag='img')
        self.assertEqual(len(images), 0)

        # we dont' have an image in article.top_node
        # check if the correct image was retrieved
        # using the known-image-css.txt
        fields = ['cleaned_text', 'top_image']
        self.runArticleAssertions(article=article, fields=fields)

    def test_known_image_name_parent(self):
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_known_image_css_parent_class(self):
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_known_image_css_parent_id(self):
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_known_image_css_class(self):
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_known_image_css_id(self):
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_known_image_empty_src(self):
        'Tests that img tags for known image sources with empty src attributes are skipped.'
        article = self.getArticle()
        self._test_known_image_css(article)

    def test_opengraph_tag(self):
        article = self.getArticle()
        self._test_known_image_css(article)


class ImageUtilsTests(unittest.TestCase):

    def setUp(self):
        self.path = 'tests/data/images/test_basic_image/50850547cc7310bc53e30e802c6318f1'
        self.expected_results = {
            'width': 476,
            'height': 317,
            'mime_type': 'JPEG'
        }

    def test_utils_get_image_dimensions(self):
        image_detail = ImageUtils.get_image_dimensions(None, self.path)

        # test if we have an ImageDetails instance
        self.assertTrue(isinstance(image_detail, ImageDetails))

        # test image_detail attribute
        for k, v in self.expected_results.items():
            self.assertEqual(getattr(image_detail, k), v)

    def test_detail(self):
        image_detail = ImageUtils.get_image_dimensions(None, self.path)

        # test if we have an ImageDetails instance
        self.assertTrue(isinstance(image_detail, ImageDetails))

        # test image_detail attribute
        for k, v in self.expected_results.items():
            self.assertEqual(getattr(image_detail, k), v)

        # test image_detail get_ methode
        for k, v in self.expected_results.items():
            attr = 'get_%s' % k
            self.assertEqual(getattr(image_detail, attr)(), v)

        # test image_detail set_ methode
        expected_results = {
            'width': 10,
            'height': 10,
            'mime_type': 'PNG'
        }

        for k, v in expected_results.items():
            attr = 'set_%s' % k
            getattr(image_detail, attr)(v)

        for k, v in expected_results.items():
            attr = 'get_%s' % k
            self.assertEqual(getattr(image_detail, attr)(), v)

########NEW FILE########
__FILENAME__ = parsers
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import unittest

from goose.utils import FileHelper
from goose.parsers import Parser
from goose.parsers import ParserSoup

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class ParserBase(unittest.TestCase):

    def setUp(self):
        self.parser = Parser

    def get_html(self, filename):
        path = os.path.join(CURRENT_PATH, 'data', filename)
        path = os.path.abspath(path)
        return FileHelper.loadResourceFile(path)

    def test_cssselect(self):
        html = '<html><body>'
        html += '<p class="link">this is a test <a class="link">link</a> and this is <strong class="foo">strong</strong></p>'
        html += '<p>this is a test and this is <strong class="link">strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        # find node with a class attribute
        items_result = self.parser.css_select(doc, "*[class]")
        self.assertEqual(len(items_result), 4)

        # find p nodes
        items_result = self.parser.css_select(doc, "p")
        self.assertEqual(len(items_result), 2)

        # find nodes with attribute class equal to link
        items_result = self.parser.css_select(doc, "*[class=link]")
        self.assertEqual(len(items_result), 3)

        # find p nodes with class attribute
        items_result = self.parser.css_select(doc, "p[class]")
        self.assertEqual(len(items_result), 1)

        # find p nodes with class attribute link
        items_result = self.parser.css_select(doc, "p[class=link]")
        self.assertEqual(len(items_result), 1)

        # find strong nodes with class attribute link or foo
        items_result = self.parser.css_select(doc, "strong[class=link], strong[class=foo]")
        self.assertEqual(len(items_result), 2)

        # find strong nodes with class attribute link or foo
        items_result = self.parser.css_select(doc, "p > a")
        self.assertEqual(len(items_result), 1)

    def test_childNodesWithText(self):
        html = '<html><body>'
        html += '<p>this is a test <a class="link">link</a> and this is <strong class="link">strong</strong></p>'
        html += '<p>this is a test and this is <strong class="link">strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        p = self.parser.getElementsByTag(doc, tag='p')[0]

    def test_replacetag(self):
        html = self.get_html('parser/test1.html')
        doc = self.parser.fromstring(html)

        # replace all p with div
        ps = self.parser.getElementsByTag(doc, tag='p')
        divs = self.parser.getElementsByTag(doc, tag='div')
        pcount = len(ps)
        divcount = len(divs)
        for p in ps:
            self.parser.replaceTag(p, 'div')
        divs2 = self.parser.getElementsByTag(doc, tag='div')
        divcount2 = len(divs2)
        self.assertEqual(divcount2, pcount + divcount)

        # replace first div span with center
        spans = self.parser.getElementsByTag(doc, tag='span')
        spanscount = len(spans)
        div = self.parser.getElementsByTag(doc, tag='div')[0]
        span = self.parser.getElementsByTag(div, tag='span')
        self.assertEqual(len(span), 1)
        self.parser.replaceTag(span[0], 'center')
        span = self.parser.getElementsByTag(div, tag='span')
        self.assertEqual(len(span), 0)
        centers = self.parser.getElementsByTag(div, tag='center')
        self.assertEqual(len(centers), 1)

    def test_droptag(self):
        # test with 1 node
        html = '<html><body><div>Hello <b>World!</b></div></body></html>'
        expecte_html = '<html><body><div>Hello World!</div></body></html>'
        doc = self.parser.fromstring(html)
        nodes = self.parser.css_select(doc, "b")
        self.assertEqual(len(nodes), 1)
        self.parser.drop_tag(nodes)

        nodes = self.parser.css_select(doc, "b")
        self.assertEqual(len(nodes), 0)

        result_html = self.parser.nodeToString(doc)
        self.assertEqual(expecte_html, result_html)

        # test with 2 nodes
        html = '<html><body><div>Hello <b>World!</b> bla <b>World!</b></div></body></html>'
        expecte_html = '<html><body><div>Hello World! bla World!</div></body></html>'
        doc = self.parser.fromstring(html)
        nodes = self.parser.css_select(doc, "b")
        self.assertEqual(len(nodes), 2)
        self.parser.drop_tag(nodes)

        nodes = self.parser.css_select(doc, "b")
        self.assertEqual(len(nodes), 0)

        result_html = self.parser.nodeToString(doc)
        self.assertEqual(expecte_html, result_html)

    def test_tostring(self):
        html = '<html><body>'
        html += '<p>this is a test <a>link</a> and this is <strong>strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        result = self.parser.nodeToString(doc)
        self.assertEqual(html, result)

    def test_striptags(self):
        html = '<html><body>'
        html += '<p>this is a test <a>link</a> and this is <strong>strong</strong></p>'
        html += '</body></html>'
        expected = '<html><body>'
        expected += '<p>this is a test link and this is strong</p>'
        expected += '</body></html>'
        doc = self.parser.fromstring(html)
        self.parser.stripTags(doc, 'a', 'strong')
        result = self.parser.nodeToString(doc)
        self.assertEqual(expected, result)

    def test_getElementsByTags(self):
        html = '<html><body>'
        html += '<p>this is a test <a class="link">link</a> and this is <strong class="link">strong</strong></p>'
        html += '<p>this is a test and this is <strong class="link">strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        elements = self.parser.getElementsByTags(doc, ['p', 'a', 'strong'])
        self.assertEqual(len(elements), 5)

        # find childs within the first p
        p = self.parser.getElementsByTag(doc, tag='p')[0]
        elements = self.parser.getElementsByTags(p, ['p', 'a', 'strong'])
        self.assertEqual(len(elements), 2)

    def test_getElementsByTag(self):
        html = '<html><body>'
        html += '<p>this is a test <a>link</a> and this is <strong>strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        # find all tags
        elements = self.parser.getElementsByTag(doc)
        self.assertEqual(len(elements), 5)

        # find all p
        elements = self.parser.getElementsByTag(doc, tag='p')
        self.assertEqual(len(elements), 1)

        html = '<html><body>'
        html += '<p>this is a test <a class="link classB classc">link</a> and this is <strong class="link">strong</strong></p>'
        html += '<p>this is a test and this is <strong class="Link">strong</strong></p>'
        html += '</body></html>'
        doc = self.parser.fromstring(html)
        # find all p
        elements = self.parser.getElementsByTag(doc, tag='p')
        self.assertEqual(len(elements), 2)

        # find all a
        elements = self.parser.getElementsByTag(doc, tag='a')
        self.assertEqual(len(elements), 1)

        # find all strong
        elements = self.parser.getElementsByTag(doc, tag='strong')
        self.assertEqual(len(elements), 2)

        # find first p
        # and find strong elemens within the p
        elem = self.parser.getElementsByTag(doc, tag='p')[0]
        elements = self.parser.getElementsByTag(elem, tag='strong')
        self.assertEqual(len(elements), 1)

        # test if the first p in taken in account
        elem = self.parser.getElementsByTag(doc, tag='p')[0]
        elements = self.parser.getElementsByTag(elem, tag='p')
        self.assertEqual(len(elements), 0)

        # find elem with class "link"
        elements = self.parser.getElementsByTag(doc, attr="class", value="link")
        self.assertEqual(len(elements), 3)

        # find elem with class "classB"
        elements = self.parser.getElementsByTag(doc, attr="class", value="classB")
        self.assertEqual(len(elements), 1)

        # find elem with class "classB"
        elements = self.parser.getElementsByTag(doc, attr="class", value="classc")
        self.assertEqual(len(elements), 1)

        # find elem with class "link" with tag strong
        elements = self.parser.getElementsByTag(doc, tag="strong", attr="class", value="link")
        self.assertEqual(len(elements), 2)

        # find elem with class "link" with tag strong
        # within the second p
        elem = self.parser.getElementsByTag(doc, tag='p')[1]
        elements = self.parser.getElementsByTag(elem, tag="strong", attr="class", value="link")
        self.assertEqual(len(elements), 1)

    def test_delAttribute(self):
        html = self.get_html('parser/test1.html')
        doc = self.parser.fromstring(html)

        # find div element with class foo
        elements = self.parser.getElementsByTag(doc, tag="div", attr="class", value="foo")
        self.assertEqual(len(elements), 1)

        # remove the attribute class
        div = elements[0]
        self.parser.delAttribute(div,  attr="class")

        # find div element with class foo
        elements = self.parser.getElementsByTag(doc, tag="div", attr="class", value="foo")
        self.assertEqual(len(elements), 0)

        # remove an unexistant attribute
        self.parser.delAttribute(div,  attr="bla")


class TestParser(ParserBase):
    pass


class TestParserSoup(ParserBase):
    def setUp(self):
        self.parser = ParserSoup

########NEW FILE########
__FILENAME__ = videos
# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import json

from .base import MockResponse
from .extractors import TestExtractionBase

from goose.utils import FileHelper

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))


class MockResponseVideos(MockResponse):
    def content(self, req):
        current_test = self.cls._get_current_testname()
        path = os.path.join(CURRENT_PATH, "data", "videos", "%s.html" % current_test)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        return content


class ImageExtractionTests(TestExtractionBase):
    """\
    Base Mock test case
    """
    callback = MockResponseVideos

    def assert_movies(self, field, expected_value, result_value):
        # check if result_value is a list
        self.assertTrue(isinstance(result_value, list))
        # check number of videos
        self.assertEqual(len(expected_value), len(result_value))

        # check values
        for c, video in enumerate(result_value):
            expected = expected_value[c]
            for k, v in expected.items():
                r = getattr(video, k)
                self.assertEqual(r, v)

    def loadData(self):
        """\

        """
        suite, module, cls, func = self.id().split('.')
        path = os.path.join(CURRENT_PATH, "data", module, "%s.json" % func)
        path = os.path.abspath(path)
        content = FileHelper.loadResourceFile(path)
        self.data = json.loads(content)

    def test_embed(self):
        article = self.getArticle()
        fields = ['movies']
        self.runArticleAssertions(article=article, fields=fields)

    def test_iframe(self):
        article = self.getArticle()
        fields = ['movies']
        self.runArticleAssertions(article=article, fields=fields)

    def test_object(self):
        article = self.getArticle()
        fields = ['movies']
        self.runArticleAssertions(article=article, fields=fields)

########NEW FILE########
