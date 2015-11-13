__FILENAME__ = obfuscate
#!/usr/bin/python

import curses.ascii
import hashlib
import random
import sys
import os

from PIL import Image
from PIL import ImageDraw

from pyocr.builders import Box
from pyocr.builders import LineBox

from paperwork.backend import config
from paperwork.backend import docsearch
from paperwork.backend import util
from paperwork.backend.img.doc import ImgDoc
from paperwork.backend.img.page import ImgPage


def get_chars(doc):
    chars = set()
    for page in doc.pages:
        for line in page.text:
            for char in line:
                if char == u"\n":
                    continue
                chars.add(char)
    return chars


def gen_salt():
    alphabet = [chr(x) for x in xrange(ord("0"), ord("9"))]
    alphabet += [chr(x) for x in xrange(ord("a"), ord("z"))]
    alphabet += [chr(x) for x in xrange(ord("A"), ord("Z"))]
    chars=[]
    for i in xrange(512):
        chars.append(random.choice(alphabet))
    return "".join(chars)


def generate_mapping(chars):
    # make sure we have some basic chars in the set
    for rng in [
            xrange(ord('a'), ord('z')),
            xrange(ord('A'), ord('Z')),
            xrange(ord('0'), ord('9')),
        ]:
        for ch in rng:
            chars.add(chr(ch))

    chars = [x for x in chars]
    chars.sort()
    shuffled = chars[:]
    random.shuffle(shuffled)

    mapping = {}
    for char_idx in xrange(0, len(chars)):
        mapping[chars[char_idx]] = shuffled[char_idx]
    return mapping


def print_mapping(mapping):
    print("==========================")
    print("Mapping that will be used:")
    for (i, t) in mapping.iteritems():
        print("  %s --> %s" % (i.encode("utf-8"), t.encode("utf-8")))
    print("==========================")


def clone_box(src_box, mapping, salt):
    src_content = src_box.content

    content = u""
    for char in src_content:
        if char in mapping:
            content += mapping[char]
        else:
            content += char

    content_hash = hashlib.sha512()
    content_hash.update(salt)
    content_hash.update(content.encode("utf-8"))

    dst_content = u""
    sha = content_hash.digest()
    for char_pos in xrange(0, len(src_content)):
        if not src_content[char_pos] in mapping:
            dst_content += char
        char = ord(sha[char_pos])
        char_idx = char % len(mapping)
        dst_content += mapping.values()[char_idx]

    dst_content = dst_content[:len(src_content)]

    return Box(dst_content, src_box.position)


def clone_img(src_img):
    # we just reuse the size
    img_size = src_img.size
    dst_img = Image.new("RGB", img_size, color="#ffffff")
    draw = ImageDraw.Draw(dst_img)
    if img_size[0] > 200 and img_size[1] > 200:
        draw.rectangle((100, 100, img_size[0] - 100, img_size[1] - 100),
                       fill="#333333")
        draw.line((100, 100, img_size[0] - 100, img_size[1] - 100),
                  fill="#ffffff", width=5)
        draw.line((img_size[0] - 100, 100,
                        100, img_size[1] - 100),
                  fill="#ffffff", width=5)
    return dst_img


def clone_page_content(src_page, dst_page, mapping, salt):
    src_boxes_lines = src_page.boxes
    dst_boxes_lines = []
    for src_boxes_line in src_boxes_lines:
        src_boxes = src_boxes_line.word_boxes
        dst_boxes_line = [clone_box(box, mapping, salt) for box in src_boxes]
        dst_boxes_line = LineBox(dst_boxes_line, src_boxes_line.position)
        dst_boxes_lines.append(dst_boxes_line)
    dst_page.boxes = dst_boxes_lines
    dst_page.img = clone_img(src_page.img)


def clone_doc_content(src_doc, dst_doc, mapping, salt):
    dst_pages = dst_doc.pages
    for src_page in src_doc.pages:
        dst_page = ImgPage(dst_doc)
        clone_page_content(src_page, dst_page, mapping, salt)
        dst_pages.add(dst_page)
        sys.stdout.write("%d " % src_page.page_nb)
        sys.stdout.flush()


def main(src_dir, dst_dir):
    sys.stdout.write("Loading document %s ... " % src_dir)
    sys.stdout.flush()
    src_doc = ImgDoc(src_dir, os.path.basename(src_dir))
    sys.stdout.write("Done\n")

    if (src_doc.nb_pages <= 0):
        raise Exception("No pages found. Is this an image doc ?")

    sys.stdout.write("Analyzing document ... ")
    sys.stdout.flush()
    chars = get_chars(src_doc)
    sys.stdout.write("Done\n")

    sys.stdout.write("Generating salt ... ")
    sys.stdout.flush()
    salt = gen_salt()
    sys.stdout.write("Done\n")
    print("Will use [%s] as salt for the hash" % salt)

    sys.stdout.write("Generating char mapping ... ")
    sys.stdout.flush()
    mapping = generate_mapping(chars)
    sys.stdout.write("Done\n")

    print_mapping(mapping)

    os.mkdir(dst_dir)

    sys.stdout.write("Generating document %s ... " % dst_dir)
    sys.stdout.flush()
    dst_doc = ImgDoc(dst_dir, os.path.basename(dst_dir))
    clone_doc_content(src_doc, dst_doc, mapping, salt)
    sys.stdout.write("... Done\n")

    print("All done")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage:")
        print("  %s <src_dir> <out_dir>" % sys.argv[0])
        print("")
        print("  src_dir : document to anonymize")
        print("  out_dir : directory in which to write the anonymized version")
        print("")
        print("Images will be replaced by a dummy image")
        print("Words are replaced by pieces of their hash (SHA512)")
        print("")
        print("Example:")
        print("  %s ~/papers/20100730_0000_01 ~/tmp/20100730_0000_01.anonymized"
              % sys.argv[0])
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2]
    main(src, dst)
    sys.exit(0)

########NEW FILE########
__FILENAME__ = stats
#!/usr/bin/env python

import sys

import paperwork.backend.config as config
import paperwork.backend.docsearch as docsearch
import paperwork.backend.util as util


def main():
    pconfig = config.PaperworkConfig()
    pconfig.read()
    print("Opening docs (%s)" % pconfig.settings['workdir'].value)
    print("====================")
    dsearch = docsearch.DocSearch(pconfig.settings['workdir'].value)

    nb_words = 0
    nb_docs = (len(dsearch.docs))
    nb_pages = 0
    max_pages = 0

    total_word_len = 0
    max_word_len = 0

    words = set()
    total_nb_unique_words = 0
    total_nb_unique_words_per_doc = 0

    print("")
    print("Analysis")
    print("========")

    all_labels = set([l.name for l in dsearch.label_list])
    label_keys = [ 'global', 'positive', 'negative' ]  # for the order
    total_label_accuracy = {
        'global': 0,
        'positive': 0,
        'negative': 0,
    }
    total_labels = {
        'global': 0,
        'positive': 0,
        'negative': 0,
    }

    for doc in dsearch.docs:
        sys.stdout.write(str(doc) + ": ")
        sys.stdout.flush()

        doc_words = set()

        if doc.nb_pages > max_pages:
            max_pages = doc.nb_pages

        ### Keyword stats
        for page in doc.pages:
            sys.stdout.write("%d " % (page.page_nb + 1))
            sys.stdout.flush()
            nb_pages += 1

            for line in page.text:
                for word in util.split_words(line):
                    # ignore words too short to be useful
                    if (len(word) < 4):
                        continue
                    if not word in words:
                        words.add(word)
                        total_nb_unique_words += 1
                    if not word in doc_words:
                        doc_words.add(word)
                        total_nb_unique_words_per_doc += 1

                    nb_words += 1
                    total_word_len += len(word)
                    if max_word_len < len(word):
                        max_word_len = len(word)

        ### Label predictions stats
        doc_labels = set([l.name for l in doc.labels])
        predicated_labels = set(dsearch.predict_label_list(doc))
        accurate = {
            'global': 0,
            'negative': 0,
            'positive': 0,
        }
        nb_labels = {
            'global': len(all_labels),
            'positive': len(doc_labels),
            'negative': len(all_labels) - len(doc_labels),
        }
        for key in label_keys:
            total_labels[key] += nb_labels[key]
        for label in all_labels:
            if not ((label in doc_labels) ^ (label in predicated_labels)):
                accurate['global'] += 1
                total_label_accuracy['global'] += 1
                if label in doc_labels:
                    accurate['positive'] += 1
                    total_label_accuracy['positive'] += 1
                else:
                    accurate['negative'] += 1
                    total_label_accuracy['negative'] += 1
        for key in label_keys:
            total = nb_labels[key]
            value = accurate[key]
            if total == 0:
                continue
            value = accurate[key]
            sys.stdout.write("\n\t- label prediction accuracy (%s): %d%%"
                             % (key, (100 * accurate[key] / total)))

        sys.stdout.write("\n")

    print("")
    print("Statistics")
    print("==========")
    print("Total number of documents: %d" % nb_docs)
    print("Total number of pages: %d" % nb_pages)
    print("Total number of words: %d" % nb_words)
    print("Total words len: %d" % total_word_len)
    print("Total number of unique words: %d" % total_nb_unique_words)
    print("===")
    print("Maximum number of pages in one document: %d" % max_pages)
    print("Maximum word length: %d" % max_word_len)
    print("Average word length: %f" % (float(total_word_len) / float(nb_words)))
    print ("Average number of words per page: %f"
           % (float(nb_words) / float(nb_pages)))
    print ("Average number of words per document: %f"
           % (float(nb_words) / float(nb_docs)))
    print ("Average number of pages per document: %f"
           % (float(nb_pages) / float(nb_docs)))
    print ("Average number of unique words per document: %f"
           % (float(total_nb_unique_words_per_doc) / float(nb_docs)))
    for key in label_keys:
        total = total_labels[key]
        value = total_label_accuracy[key]
        print ("Average accuracy of label prediction (%s): %d%%"
               % (key, (100 * value / total)))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = launcher
#!/usr/bin/env python
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

# just here to run a non-installed version

import sys

sys.path += ['src']

from paperwork.paperwork import main

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = doc
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import codecs
import datetime
import gettext
import logging
import os.path
import time
import hashlib

from scipy import sparse
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

from paperwork.backend.common.page import BasicPage
from paperwork.backend.labels import Label
from paperwork.backend.util import dummy_progress_cb
from paperwork.backend.util import rm_rf
from paperwork.backend.util import strip_accents


_ = gettext.gettext
logger = logging.getLogger(__name__)


class BasicDoc(object):
    LABEL_FILE = "labels"
    DOCNAME_FORMAT = "%Y%m%d_%H%M_%S"
    EXTRA_TEXT_FILE = "extra.txt"
    FEATURES_DIR = "features"
    FEATURES_FILE = "features.jbl"
    FEATURES_VER = 1

    pages = []
    can_edit = False

    def __init__(self, docpath, docid=None):
        """
        Basic init of common parts of doc.

        Note regarding subclassing: *do not* load the document
        content in __init__(). It would reduce in a huge performance loose
        and thread-safety issues. Load the content on-the-fly when requested.
        """
        if docid is None:
            # new empty doc
            # we must make sure we use an unused id
            basic_docid = time.strftime(self.DOCNAME_FORMAT)
            extra = 0
            docid = basic_docid
            path = os.path.join(docpath, docid)
            while os.access(path, os.F_OK):
                extra += 1
                docid = "%s_%d" % (basic_docid, extra)
                path = os.path.join(docpath, docid)

            self.__docid = docid
            self.path = path
        else:
            self.__docid = docid
            self.path = docpath
        self.__cache = {}

    def drop_cache(self):
        self.__cache = {}

    def __str__(self):
        return self.__docid

    def __get_last_mod(self):
        raise NotImplementedError()

    last_mod = property(__get_last_mod)

    def __get_nb_pages(self):
        if not 'nb_pages' in self.__cache:
            self.__cache['nb_pages'] = self._get_nb_pages()
        return self.__cache['nb_pages']

    nb_pages = property(__get_nb_pages)

    def print_page_cb(self, print_op, print_context, page_nb):
        raise NotImplementedError()

    def __get_doctype(self):
        raise NotImplementedError()

    def get_docfilehash(self):
        raise NotImplementedError()

    doctype = property(__get_doctype)

    def __get_keywords(self):
        """
        Yield all the keywords contained in the document.
        """
        for page in self.pages:
            for keyword in page.keywords:
                yield(keyword)

    keywords = property(__get_keywords)

    def destroy(self):
        """
        Delete the document. The *whole* document. There will be no survivors.
        """
        logger.info("Destroying doc: %s" % self.path)
        rm_rf(self.path)
        logger.info("Done")
        self.drop_cache()
        self.__cache['new'] = False

    def add_label(self, label):
        """
        Add a label on the document.
        """
        if label in self.labels:
            return
        with codecs.open(os.path.join(self.path, self.LABEL_FILE), 'a',
                         encoding='utf-8') as file_desc:
            file_desc.write("%s,%s\n" % (label.name, label.get_color_str()))
        self.drop_cache()

    def remove_label(self, to_remove):
        """
        Remove a label from the document. (-> rewrite the label file)
        """
        if not to_remove in self.labels:
            return
        labels = self.labels
        labels.remove(to_remove)
        with codecs.open(os.path.join(self.path, self.LABEL_FILE), 'w',
                         encoding='utf-8') as file_desc:
            for label in labels:
                file_desc.write("%s,%s\n" % (label.name,
                                             label.get_color_str()))
        self.drop_cache()

    def __get_labels(self):
        """
        Read the label file of the documents and extract all the labels

        Returns:
            An array of labels.Label objects
        """
        if not 'labels' in self.__cache:
            labels = []
            try:
                with codecs.open(os.path.join(self.path, self.LABEL_FILE), 'r',
                                 encoding='utf-8') as file_desc:
                    for line in file_desc.readlines():
                        line = line.strip()
                        (label_name, label_color) = line.split(",")
                        labels.append(Label(name=label_name,
                                            color=label_color))
            except IOError:
                pass
            self.__cache['labels'] = labels
        return self.__cache['labels']

    labels = property(__get_labels)

    def get_index_text(self):
        txt = u""
        for page in self.pages:
            txt += u"\n".join([unicode(line) for line in page.text])
        extra_txt = self.extra_text
        if extra_txt != u"":
            txt += extra_txt + u"\n"
        txt = txt.strip()
        txt = strip_accents(txt)
        if txt == u"":
            # make sure the text field is not empty. Whoosh doesn't like that
            txt = u"empty"
        return txt

    def _get_text(self):
        txt = u""
        for page in self.pages:
            txt += u"\n".join([unicode(line) for line in page.text])
        txt = txt.strip()
        return txt

    text = property(_get_text)

    def get_features(self):
        """
        return an array of features extracted from this doc for the sklearn estimators
        Concatenate features from the text and the image
        """
        if 'features' in self.__cache:
            return self.__cache['features']

        features = []

        # add the words count. norm='l2', analyzer='char_wb', ngram_range=(3,3) are empirical
        hash_vectorizer = HashingVectorizer(norm='l2', analyzer='char_wb', ngram_range=(3,3))
        features.append(hash_vectorizer.fit_transform([self.get_index_text()]))

        # add image info
        image_features = normalize(self.pages[0].extract_features(), norm='l1')
        features.append(image_features*0.3)

        # concatenate all the features
        features = sparse.hstack(features)
        features = features.tocsr()

        self.__cache['features'] = features

        return features

    def delete_features_files(self):
        rm_rf(os.path.join(self.path, self.FEATURES_DIR))

    def get_index_labels(self):
        return u",".join([strip_accents(unicode(label.name))
                            for label in self.labels])

    def update_label(self, old_label, new_label):
        """
        Update a label

        Will go on each document, and replace 'old_label' by 'new_label'
        """
        logger.info("%s : Updating label ([%s] -> [%s])"
                    % (str(self), old_label.name, new_label.name))
        labels = self.labels
        try:
            labels.remove(old_label)
        except ValueError:
            # this document doesn't have this label
            return

        logger.info("%s : Updating label ([%s] -> [%s])"
               % (str(self), old_label.name, new_label.name))
        labels.append(new_label)
        with codecs.open(os.path.join(self.path, self.LABEL_FILE), 'w',
                         encoding='utf-8') as file_desc:
            for label in labels:
                file_desc.write("%s,%s\n" % (label.name,
                                             label.get_color_str()))
        self.drop_cache()

    @staticmethod
    def get_export_formats():
        raise NotImplementedError()

    def build_exporter(self, file_format='pdf'):
        """
        Returns:
            Returned object must implement the following methods/attributes:
            .can_change_quality = (True|False)
            .set_quality(quality_pourcent)
            .estimate_size() : returns the size in bytes
            .get_img() : returns a Pillow Image
            .get_mime_type()
            .get_file_extensions()
            .save(file_path)
        """
        raise NotImplementedError()

    def __doc_cmp(self, other):
        """
        Comparison function. Can be used to sort docs alphabetically.
        """
        if other is None:
            return -1
        if self.is_new and other.is_new:
            return 0
        return cmp(self.__docid, other.__docid)

    def __lt__(self, other):
        return self.__doc_cmp(other) < 0

    def __gt__(self, other):
        return self.__doc_cmp(other) > 0

    def __eq__(self, other):
        return self.__doc_cmp(other) == 0

    def __le__(self, other):
        return self.__doc_cmp(other) <= 0

    def __ge__(self, other):
        return self.__doc_cmp(other) >= 0

    def __ne__(self, other):
        return self.__doc_cmp(other) != 0

    def __hash__(self):
        return hash(self.__docid)

    def __is_new(self):
        if 'new' in self.__cache:
            return self.__cache['new']
        self.__cache['new'] = not os.access(self.path, os.F_OK)
        return self.__cache['new']

    is_new = property(__is_new)

    def __get_name(self):
        """
        Returns the localized name of the document (see l10n)
        """
        if self.is_new:
            return _("New document")
        try:
            split = self.__docid.split("_")
            short_docid = "_".join(split[:3])
            datetime_obj = datetime.datetime.strptime(
                short_docid, self.DOCNAME_FORMAT)
            final = datetime_obj.strftime("%x")
            return final
        except Exception, exc:
            logger.error("Unable to parse document id [%s]: %s"
                    % (self.docid, exc))
            return self.docid

    name = property(__get_name)

    def __get_docid(self):
        return self.__docid

    def __set_docid(self, new_base_docid):
        workdir = os.path.dirname(self.path)
        new_docid = new_base_docid
        new_docpath = os.path.join(workdir, new_docid)
        idx = 0

        while os.path.exists(new_docpath):
            idx += 1
            new_docid = new_base_docid + ("_%02d" % idx)
            new_docpath = os.path.join(workdir, new_docid)

        self.__docid = new_docid
        if self.path != new_docpath:
            logger.info("Changing docid: %s -> %s" % (self.path, new_docpath))
            os.rename(self.path, new_docpath)
            self.path = new_docpath

    docid = property(__get_docid, __set_docid)

    def __get_date(self):
        try:
            split = self.__docid.split("_")[0]
            return (datetime.datetime(
                int(split[0:4]),
                int(split[4:6]),
                int(split[6:8])))
        except (IndexError, ValueError):
            return (datetime.datetime())

    def __set_date(self, new_date):
        new_id = ("%02d%02d%02d_0000_01"
                  % (new_date.year,
                     new_date.month,
                     new_date.day))
        self.docid = new_id

    date = property(__get_date, __set_date)

    def __get_extra_text(self):
        extra_txt_file = os.path.join(self.path, self.EXTRA_TEXT_FILE)
        if not os.access(extra_txt_file, os.R_OK):
            return u""
        with codecs.open(extra_txt_file, 'r', encoding='utf-8') as file_desc:
            text = file_desc.read()
            return text

    def __set_extra_text(self, txt):
        extra_txt_file = os.path.join(self.path, self.EXTRA_TEXT_FILE)

        txt = txt.strip()
        if txt == u"":
            os.unlink(extra_txt_file)
        else:
            with codecs.open(extra_txt_file, 'w',
                             encoding='utf-8') as file_desc:
                file_desc.write(txt)

    extra_text = property(__get_extra_text, __set_extra_text)

    @staticmethod
    def hash_file(path):
        dochash = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        return int(dochash, 16)

########NEW FILE########
__FILENAME__ = page
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

from copy import copy
import PIL.Image
import os.path

import numpy
from scipy import sparse
from scipy.sparse.csr import csr_matrix
from skimage import feature
from sklearn.preprocessing import normalize

from paperwork.backend.util import split_words


class PageExporter(object):
    can_select_format = False
    can_change_quality = True

    def __init__(self, page, img_format='PNG', mime='image/png',
                 valid_exts=['png']):
        self.page = page
        self.img_format = img_format
        self.mime = mime
        self.valid_exts = valid_exts
        self.__quality = 75
        self.__img = None

    def get_mime_type(self):
        return self.mime

    def get_file_extensions(self):
        return self.valid_exts

    def save(self, target_path):
        # the user gives us a quality between 0 and 100
        # but PIL expects a quality between 1 and 75
        quality = int(float(self.__quality) / 100.0 * 74.0) + 1
        # We also adjust the size of the image
        resize_factor = float(self.__quality) / 100.0

        img = self.page.img

        new_size = (int(resize_factor * img.size[0]),
                    int(resize_factor * img.size[1]))
        img = img.resize(new_size, PIL.Image.ANTIALIAS)

        img.save(target_path, self.img_format, quality=quality)
        return target_path

    def refresh(self):
        tmp = "%s.%s" % (os.tempnam(None, "paperwork_export_"),
                         self.valid_exts[0])
        path = self.save(tmp)
        img = PIL.Image.open(path)
        img.load()

        self.__img = (path, img)

    def set_quality(self, quality):
        self.__quality = int(quality)
        self.__img = None

    def estimate_size(self):
        if self.__img is None:
            self.refresh()
        return os.path.getsize(self.__img[0])

    def get_img(self):
        if self.__img is None:
            self.refresh()
        return self.__img[1]

    def __str__(self):
        return self.img_format

    def __copy__(self):
        return PageExporter(self.page, self.img_format, self.mime,
                            self.valid_exts)


class BasicPage(object):

    # The width of the thumbnails is defined arbitrarily
    DEFAULT_THUMB_WIDTH = 150
    # The height of the thumbnails is defined based on the A4 format
    # proportions
    DEFAULT_THUMB_HEIGHT = 212

    EXT_THUMB = "thumb.jpg"
    FILE_PREFIX = "paper."

    boxes = []
    img = None
    size = (0, 0)

    can_edit = False

    def __init__(self, doc, page_nb):
        """
        Don't create directly. Please use ImgDoc.get_page()
        """
        self.doc = doc
        self.page_nb = page_nb

        self.__thumbnail_cache = (None, 0)
        self.__text_cache = None

        assert(self.page_nb >= 0)
        self.__prototype_exporters = {
            'PNG': PageExporter(self, 'PNG', 'image/png', ["png"]),
            'JPEG': PageExporter(self, 'JPEG', 'image/jpeg', ["jpeg", "jpg"]),
        }

    def __get_pageid(self):
        return self.doc.docid + "/" + str(self.page_nb)

    pageid = property(__get_pageid)

    def _get_filepath(self, ext):
        """
        Returns a file path relative to this page
        """
        filename = ("%s%d.%s" % (self.FILE_PREFIX, self.page_nb + 1, ext))
        return os.path.join(self.doc.path, filename)

    def __make_thumbnail(self, width, height):
        """
        Create the page's thumbnail
        """
        img = self.img
        (w, h) = img.size
        factor = max(
            (float(w) / width),
            (float(h) / height)
        )
        w /= factor
        h /= factor
        img = img.resize((int(w), int(h)), PIL.Image.ANTIALIAS)
        return img

    def _get_thumb_path(self):
        return self._get_filepath(self.EXT_THUMB)

    def get_thumbnail(self, width, height):
        """
        thumbnail with a memory cache
        """
        if ((width, height) == self.__thumbnail_cache[1]):
            return self.__thumbnail_cache[0]

        # get from the file
        try:
            if os.path.getmtime(self.get_doc_file_path()) < \
               os.path.getmtime(self._get_thumb_path()):
                thumbnail = PIL.Image.open(self._get_thumb_path())
            else:
                thumbnail = self.__make_thumbnail(width, height)
                thumbnail.save(self._get_thumb_path())
        except:
            thumbnail = self.__make_thumbnail(width, height)
            thumbnail.save(self._get_thumb_path())

        self.__thumbnail_cache = (thumbnail, (width, height))
        return thumbnail

    def drop_cache(self):
        self.__thumbnail_cache = (None, 0)
        self.__text_cache = None

    def __get_text(self):
        if self.__text_cache is not None:
            return self.__text_cache
        self.__text_cache = self._get_text()
        return self.__text_cache

    text = property(__get_text)

    def print_page_cb(self, print_op, print_context):
        raise NotImplementedError()

    def destroy(self):
        raise NotImplementedError()

    def get_export_formats(self):
        return self.__prototype_exporters.keys()

    def build_exporter(self, file_format='PNG'):
        return copy(self.__prototype_exporters[file_format.upper()])

    def __str__(self):
        return "%s p%d" % (str(self.doc), self.page_nb + 1)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if None == other:
            return False
        return self.doc == other.doc and self.page_nb == other.page_nb

    def __contains__(self, sentence):
        words = split_words(sentence)
        words = [word.lower() for word in words]
        txt = self.text
        for line in txt:
            line = line.lower()
            for word in words:
                if word in line:
                    return True
        return False

    def __get_keywords(self):
        """
        Get all the keywords related of this page

        Returns:
            An array of strings
        """
        txt = self.text
        for line in txt:
            for word in split_words(line):
                yield(word)

    keywords = property(__get_keywords)

    def extract_features(self):
        """
        compute image data to present features for the estimators
        """
        image = self.get_thumbnail(BasicPage.DEFAULT_THUMB_WIDTH,
                                   BasicPage.DEFAULT_THUMB_HEIGHT)
        image = image.convert('RGB')

        # use the first two channels of color histogram
        histogram = image.histogram()
        separated_histo = []
        separated_histo.append(histogram[0:256])
        separated_histo.append(histogram[256:256*2])
        # use the grayscale histogram with a weight of 2
        separated_histo.append([i*2 for i in image.convert('L').histogram()])
        separated_flat_histo = []
        for histo in separated_histo:
            # flatten histograms
            window_len = 4
            s = numpy.r_[histo[window_len-1:0:-1],histo,histo[-1:-window_len:-1]]
            w = numpy.ones(window_len,'d')
            separated_flat_histo.append(csr_matrix(numpy.convolve(w/w.sum(),
                                                                  s,
                                                                  mode='valid'))
                                        .astype(numpy.float64))
        flat_histo = normalize(sparse.hstack(separated_flat_histo), norm='l1')

        # hog feature extraction
        # must resize to multiple of 8 because of skimage hog bug
        hog_features = feature.hog(numpy.array(image.resize((144,144))
                                               .convert('L')),
                                   normalise=False)
        hog_features = csr_matrix(hog_features).astype(numpy.float64)
        hog_features = normalize(hog_features, norm='l1')

        # concatenate
        features = sparse.hstack([flat_histo, hog_features * 3])

        return features

class DummyPage(object):
    page_nb = -1
    text = ""
    boxes = []
    keywords = []
    img = None

    def __init__(self, parent_doc):
        self.doc = parent_doc

    def _get_filepath(self, ext):
        raise NotImplementedError()

    def get_thumbnail(self, width):
        raise NotImplementedError()

    def print_page_cb(self, print_op, print_context):
        raise NotImplementedError()

    def destroy(self):
        pass

    def get_boxes(self, sentence):
        return []

    def get_export_formats(self):
        return []

    def build_exporter(self, file_format='PNG'):
        raise NotImplementedError()

    def __str__(self):
        return "Dummy page"

########NEW FILE########
__FILENAME__ = config
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.
"""
Paperwork configuration management code
"""

import ConfigParser
import logging
import os


logger = logging.getLogger(__name__)


def paperwork_cfg_boolean(string):
    if string.lower() == "true":
        return True
    return False


class PaperworkSetting(object):
    def __init__(self, section, token, default_value_func=lambda: None,
                 constructor=str):
        self.section = section
        self.token = token
        self.default_value_func = default_value_func
        self.constructor = constructor
        self.value = None

    def load(self, config):
        try:
            value = config.get(self.section, self.token)
            if value != "None":
                value = self.constructor(value)
            else:
                value = None
            self.value = value
            return
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            pass
        self.value = self.default_value_func()

    def update(self, config):
        config.set(self.section, self.token, str(self.value))


class PaperworkConfig(object):
    """
    Paperwork config. See each accessor to know for what purpose each value is
    used.
    """
    def __init__(self):
        self.settings = {
            'workdir' : PaperworkSetting("Global", "WorkDirectory",
                                         lambda: os.path.expanduser("~/papers"))
        }

        self._configparser = None

        # Possible config files are evaluated in the order they are in the
        # array. The last one of the list is the default one.
        configfiles = [
            "./paperwork.conf",
            os.path.expanduser("~/.paperwork.conf"),
            ("%s/paperwork.conf"
             % (os.getenv("XDG_CONFIG_HOME",
                          os.path.expanduser("~/.config"))))
        ]

        configfile_found = False
        for self.__configfile in configfiles:
            if os.access(self.__configfile, os.R_OK):
                configfile_found = True
                logger.info("Config file found: %s" % self.__configfile)
                break
        if not configfile_found:
            logger.info("Config file not found. Will use '%s'"
                    % self.__configfile)

    def read(self):
        """
        (Re)read the configuration.

        Beware that the current work directory may affect this operation:
        If there is a 'paperwork.conf' in the current directory, it will be
        read instead of '~/.paperwork.conf', see __init__())
        """
        logger.info("Reloading %s ..." % self.__configfile)

        # smash the previous config
        self._configparser = ConfigParser.SafeConfigParser()
        self._configparser.read([self.__configfile])

        sections = set()
        for setting in self.settings.values():
            sections.add(setting.section)
        for section in sections:
            # make sure that all the sections exist
            if not self._configparser.has_section(section):
                self._configparser.add_section(section)

        for setting in self.settings.values():
            setting.load(self._configparser)

    def write(self):
        """
        Rewrite the configuration file. It rewrites the same file than
        PaperworkConfig.read() read.
        """
        logger.info("Updating %s ..." % self.__configfile)

        for setting in self.settings.values():
            setting.update(self._configparser)

        file_path = self.__configfile
        with open(file_path, 'wb') as file_descriptor:
            self._configparser.write(file_descriptor)
        logger.info("Done")

    def __getitem__(self, item):
        return self.settings[item]

########NEW FILE########
__FILENAME__ = docimport
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

"""
Document import (PDF, images, etc)
"""

import gettext
import logging
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Poppler
from PIL import Image

from paperwork.backend.pdf.doc import PdfDoc
from paperwork.backend.img.doc import ImgDoc

_ = gettext.gettext
logger = logging.getLogger(__name__)


class SinglePdfImporter(object):
    """
    Import a single PDF file as a document
    """
    def __init__(self):
        pass

    @staticmethod
    def can_import(file_uri, current_doc=None):
        """
        Check that the specified file looks like a PDF
        """
        return file_uri.lower().endswith(".pdf")

    @staticmethod
    def import_doc(file_uri, config, docsearch, current_doc=None):
        """
        Import the specified PDF file
        """
        doc = PdfDoc(config.settings['workdir'].value)
        logger.info("Importing doc '%s' ..." % file_uri)
        doc.import_pdf(config, file_uri)
        return ([doc], None, True)

    def __str__(self):
        return _("Import PDF")


class MultiplePdfImporter(object):
    """
    Import many PDF files as many documents
    """
    def __init__(self):
        pass

    @staticmethod
    def __get_all_children(parent):
        """
        Find all the children files from parent
        """
        children = parent.enumerate_children(
            Gio.FILE_ATTRIBUTE_STANDARD_NAME,
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
            None)
        for child in children:
            name = child.get_attribute_as_string(
                Gio.FILE_ATTRIBUTE_STANDARD_NAME)
            child = parent.get_child(name)
            try:
                for child in MultiplePdfImporter.__get_all_children(child):
                    yield child
            except GLib.GError:
                yield child

    @staticmethod
    def can_import(file_uri, current_doc=None):
        """
        Check that the specified file looks like a directory containing many pdf
        files
        """
        try:
            parent = Gio.File.parse_name(file_uri)
            for child in MultiplePdfImporter.__get_all_children(parent):
                if child.get_basename().lower().endswith(".pdf"):
                    return True
        except GLib.GError:
            pass
        return False

    @staticmethod
    def import_doc(file_uri, config, docsearch, current_doc=None):
        """
        Import the specified PDF files
        """
        logger.info("Importing PDF from '%s'" % (file_uri))
        parent = Gio.File.parse_name(file_uri)
        doc = None
        docs = []

        idx = 0

        for child in MultiplePdfImporter.__get_all_children(parent):
            if not child.get_basename().lower().endswith(".pdf"):
                continue
            if docsearch.is_hash_in_index(PdfDoc.hash_file(child.get_path())):
                logger.info("Document %s already found in the index. Skipped"
                            % (child.get_path()))
                continue
            try:
                # make sure we can import it
                Poppler.Document.new_from_file(child.get_uri(),
                                               password=None)
            except Exception:
                continue
            doc = PdfDoc(config.settings['workdir'].value)
            doc.import_pdf(config, child.get_uri())
            docs.append(doc)
            idx += 1
        if doc is None:
            return (None, None, False)
        else :
            return (docs, None, True)

    def __str__(self):
        return _("Import each PDF in the folder as a new document")


class SingleImageImporter(object):
    """
    Import a single image file (in a format supported by PIL). It is either
    added to a document (if one is specified) or as a new document (--> with a
    single page)
    """
    def __init__(self):
        pass

    @staticmethod
    def can_import(file_uri, current_doc=None):
        """
        Check that the specified file looks like an image supported by PIL
        """
        for ext in ImgDoc.IMPORT_IMG_EXTENSIONS:
            if file_uri.lower().endswith(ext):
                return True
        return False

    @staticmethod
    def import_doc(file_uri, config, docsearch, current_doc=None):
        """
        Import the specified image
        """
        logger.info("Importing doc '%s'" % (file_uri))
        if current_doc is None:
            current_doc = ImgDoc(config.settings['workdir'].value)
        new = current_doc.is_new
        if file_uri[:7] == "file://":
            # XXX(Jflesch): bad bad bad
            file_uri = file_uri[7:]
        img = Image.open(file_uri)
        page = current_doc.add_page(img, [])
        return ([current_doc], page, new)

    def __str__(self):
        return _("Append the image to the current document")


IMPORTERS = [
    SinglePdfImporter(),
    SingleImageImporter(),
    MultiplePdfImporter(),
]


def get_possible_importers(file_uri, current_doc=None):
    """
    Return all the importer objects that can handle the specified file.

    Possible imports may vary depending on the currently active document
    """
    importers = []
    for importer in IMPORTERS:
        if importer.can_import(file_uri, current_doc):
            importers.append(importer)
    return importers

########NEW FILE########
__FILENAME__ = docsearch
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.
"""
Contains all the code relative to keyword and document list management list.
Also everything related to indexation and searching in the documents (+
suggestions)
"""

import logging
import copy
import datetime
import multiprocessing
import os.path
import time
import threading

from gi.repository import GObject

import numpy
from sklearn.externals import joblib
from sklearn.linear_model.passive_aggressive import PassiveAggressiveClassifier

import whoosh.fields
import whoosh.index
import whoosh.qparser
import whoosh.query
import whoosh.sorting

from paperwork.backend import img
from paperwork.backend.common.doc import BasicDoc
from paperwork.backend.img.doc import ImgDoc
from paperwork.backend.img.doc import is_img_doc
from paperwork.backend.pdf.doc import PdfDoc
from paperwork.backend.pdf.doc import is_pdf_doc
from paperwork.backend.util import dummy_progress_cb
from paperwork.backend.util import MIN_KEYWORD_LEN
from paperwork.backend.util import mkdir_p
from paperwork.backend.util import rm_rf


logger = logging.getLogger(__name__)

DOC_TYPE_LIST = [
    (is_pdf_doc, PdfDoc.doctype, PdfDoc),
    (is_img_doc, ImgDoc.doctype, ImgDoc)
]


class DummyDocSearch(object):
    """
    Dummy doc search object.

    Instantiating a DocSearch object takes time (the time to rereard the index).
    So you can use this object instead during this time as a placeholder
    """
    docs = []
    label_list = []

    def __init__(self):
        pass

    @staticmethod
    def get_doc_examiner():
        """ Do nothing """
        assert()

    @staticmethod
    def get_index_updater():
        """ Do nothing """
        assert()

    @staticmethod
    def find_suggestions(sentence):
        """ Do nothing """
        sentence = sentence  # to make pylint happy
        return []

    @staticmethod
    def find_documents(sentence, limit=None, must_sort=True, search_type='full'):
        """ Do nothing """
        sentence = sentence  # to make pylint happy
        return []

    @staticmethod
    def add_label(label):
        """ Do nothing """
        label = label  # to make pylint happy
        assert()

    @staticmethod
    def update_label(old_label, new_label, cb_progress=None):
        """ Do nothing """
        # to make pylint happy
        old_label = old_label
        new_label = new_label
        cb_progress = cb_progress
        assert()

    @staticmethod
    def destroy_label(label, cb_progress=None):
        """ Do nothing """
        # to make pylint happy
        label = label
        cb_progress = cb_progress
        assert()

    @staticmethod
    def destroy_index():
        """ Do nothing """
        assert()

    @staticmethod
    def is_hash_in_index(filehash=None):
        """ Do nothing """
        assert()

class DocDirExaminer(GObject.GObject):
    """
    Examine a directory containing documents. It looks for new documents,
    modified documents, or deleted documents.
    """
    def __init__(self, docsearch):
        GObject.GObject.__init__(self)
        self.docsearch = docsearch
        # we may be run in an independent thread --> use an independent
        # searcher
        self.__searcher = docsearch.index.searcher()

    def examine_rootdir(self,
                        on_new_doc,
                        on_doc_modified,
                        on_doc_deleted,
                        progress_cb=dummy_progress_cb):
        """
        Examine the rootdir.
        Calls on_new_doc(doc), on_doc_modified(doc), on_doc_deleted(docid)
        every time a new, modified, or deleted document is found
        """
        # getting the doc list from the index
        query = whoosh.query.Every()
        results = self.__searcher.search(query, limit=None)
        old_doc_list = [result['docid'] for result in results]
        old_doc_infos = {}
        for result in results:
            old_doc_infos[result['docid']] = (result['doctype'],
                                              result['last_read'])
        old_doc_list = set(old_doc_list)

        # and compare it to the current directory content
        docdirs = os.listdir(self.docsearch.rootdir)
        progress = 0
        for docdir in docdirs:
            old_infos = old_doc_infos.get(docdir)
            doctype = None
            if old_infos is not None:
                doctype = old_infos[0]
            doc = self.docsearch.get_doc_from_docid(docdir, doctype)
            if doc is None:
                continue
            if docdir in old_doc_list:
                old_doc_list.remove(docdir)
                assert(old_infos is not None)
                last_mod = datetime.datetime.fromtimestamp(doc.last_mod)
                if old_infos[1] != last_mod:
                    on_doc_modified(doc)
            else:
                on_new_doc(doc)
            progress_cb(progress, len(docdirs),
                        DocSearch.INDEX_STEP_CHECKING, doc)
            progress += 1

        # remove all documents from the index that don't exist anymore
        for old_doc in old_doc_list:
            on_doc_deleted(old_doc)

        progress_cb(1, 1, DocSearch.INDEX_STEP_CHECKING)


class DocIndexUpdater(GObject.GObject):
    """
    Update the index content.
    Don't forget to call commit() to apply the changes
    """
    def __init__(self, docsearch, optimize, progress_cb=dummy_progress_cb):
        self.docsearch = docsearch
        self.optimize = optimize
        self.writer = docsearch.index.writer()
        self.progress_cb = progress_cb
        self.__need_reload = False

    def _update_doc_in_index(self, index_writer, doc,
                             fit_label_estimator=True):
        """
        Add/Update a document in the index
        """
        all_labels = set(self.docsearch.label_list)
        doc_labels = set(doc.labels)
        new_labels = doc_labels.difference(all_labels)

        if new_labels != set():
            for label in new_labels:
                self.docsearch.label_list += [label]
            self.docsearch.label_list.sort()
            if fit_label_estimator:
                self.docsearch.fit_label_estimator(labels=new_labels)

        if fit_label_estimator:
            self.docsearch.fit_label_estimator([doc])
        last_mod = datetime.datetime.fromtimestamp(doc.last_mod)
        docid = unicode(doc.docid)

        dochash = doc.get_docfilehash()
        dochash = (u"%X" % dochash)

        index_writer.update_document(
            docid=docid,
            doctype=doc.doctype,
            docfilehash=dochash,
            content=doc.get_index_text(),
            label=doc.get_index_labels(),
            date=doc.date,
            last_read=last_mod
        )
        return True

    @staticmethod
    def _delete_doc_from_index(index_writer, docid):
        """
        Remove a document from the index
        """
        query = whoosh.query.Term("docid", docid)
        index_writer.delete_by_query(query)

    def add_doc(self, doc, fit_label_estimator=True):
        """
        Add a document to the index
        """
        logger.info("Indexing new doc: %s" % doc)
        self._update_doc_in_index(self.writer, doc,
                                  fit_label_estimator=fit_label_estimator)
        self.__need_reload = True

    def upd_doc(self, doc, fit_label_estimator=True):
        """
        Update a document in the index
        """
        logger.info("Updating modified doc: %s" % doc)
        self._update_doc_in_index(self.writer, doc,
                                  fit_label_estimator=fit_label_estimator)

    def del_doc(self, docid, fit_label_estimator=True):
        """
        Delete a document
        argument fit_label_estimator is not used but is needed for the
        same interface as upd_doc and add_doc
        """
        logger.info("Removing doc from the index: %s" % docid)
        self._delete_doc_from_index(self.writer, docid)
        self.__need_reload = True

    def commit(self):
        """
        Apply the changes to the index
        """
        logger.info("Index: Commiting changes and saving estimators")
        self.docsearch.save_label_estimators()
        self.writer.commit(optimize=self.optimize)
        del self.writer
        self.docsearch.reload_searcher()
        if self.__need_reload:
            logger.info("Index: Reloading ...")
            self.docsearch.reload_index(progress_cb=self.progress_cb)

    def cancel(self):
        """
        Forget about the changes
        """
        logger.info("Index: Index update cancelled")
        self.writer.cancel()
        del self.writer


def is_dir_empty(dirpath):
    """
    Check if the specified directory is empty or not
    """
    if not os.path.isdir(dirpath):
        return False
    return (len(os.listdir(dirpath)) <= 0)


class DocSearch(object):
    """
    Index a set of documents. Can provide:
        * documents that match a list of keywords
        * suggestions for user input.
        * instances of documents
    """

    INDEX_STEP_LOADING = "loading"
    INDEX_STEP_CLEANING = "cleaning"
    INDEX_STEP_CHECKING = "checking"
    INDEX_STEP_READING = "checking"
    INDEX_STEP_COMMIT = "commit"
    LABEL_STEP_UPDATING = "label updating"
    LABEL_STEP_DESTROYING = "label deletion"
    WHOOSH_SCHEMA = whoosh.fields.Schema( #static up to date schema
                docid=whoosh.fields.ID(stored=True, unique=True),
                doctype=whoosh.fields.ID(stored=True, unique=False),
                docfilehash=whoosh.fields.ID(stored=True),
                content=whoosh.fields.TEXT(spelling=True),
                label=whoosh.fields.KEYWORD(stored=True, commas=True,
                                            spelling=True, scorable=True),
                date=whoosh.fields.DATETIME(stored=True),
                last_read=whoosh.fields.DATETIME(stored=True),
            )
    LABEL_ESTIMATOR_TEMPLATE = PassiveAggressiveClassifier(n_iter=50)

    """
    Label_estimators is a dict with one estimator per label.
    Each label is predicted with its own estimator (OneVsAll strategy)
    We cannot use directly OneVsAllClassifier sklearn class because
    it doesn't support online learning (partial_fit)
    """
    label_estimators = {}

    def __init__(self, rootdir, callback=dummy_progress_cb):
        """
        Index files in rootdir (see constructor)

        Arguments:
            callback --- called during the indexation (may be called *often*).
                step : DocSearch.INDEX_STEP_READING or
                    DocSearch.INDEX_STEP_SORTING
                progression : how many elements done yet
                total : number of elements to do
                document (only if step == DocSearch.INDEX_STEP_READING): file
                    being read
        """
        self.rootdir = rootdir
        base_indexdir = os.getenv("XDG_DATA_HOME",
                                  os.path.expanduser("~/.local/share"))
        self.indexdir = os.path.join(base_indexdir, "paperwork", "index")
        mkdir_p(self.indexdir)

        self.__docs_by_id = {}  # docid --> doc
        self.label_list = []

        need_index_rewrite = True
        try:
            logger.info("Opening index dir '%s' ..." % self.indexdir)
            self.index = whoosh.index.open_dir(self.indexdir)
            # check that the schema is up-to-date
            # We use the string representation of the schemas, because previous
            # versions of whoosh don't always implement __eq__
            if str(self.index.schema) == str(self.WHOOSH_SCHEMA):
                need_index_rewrite = False
        except whoosh.index.EmptyIndexError, exc:
            logger.warning("Failed to open index '%s'" % self.indexdir)
            logger.warning("Exception was: %s" % str(exc))

        if need_index_rewrite:
            logger.info("Creating a new index")
            self.index = whoosh.index.create_in(self.indexdir,
                                                self.WHOOSH_SCHEMA)
            logger.info("Index '%s' created" % self.indexdir)

        self.__searcher = self.index.searcher()


        class CustomFuzzy(whoosh.qparser.query.FuzzyTerm):
            def __init__(self, fieldname, text, boost=1.0, maxdist=1,
                         prefixlength=0, constantscore=True):
                whoosh.qparser.query.FuzzyTerm.__init__(self, fieldname, text, boost, maxdist,
                                                        prefixlength, constantscore=True)

        facets = [whoosh.sorting.ScoreFacet(), whoosh.sorting.FieldFacet("date", reverse=True)]

        self.search_param_list = {
            'full': [
                {
                    "query_parser" : whoosh.qparser.MultifieldParser(
                        ["label", "content"], schema=self.index.schema,
                        termclass=CustomFuzzy),
                    "sortedby" : facets
                },
                {
                    "query_parser" : whoosh.qparser.MultifieldParser(
                        ["label", "content"], schema=self.index.schema,
                        termclass=whoosh.qparser.query.Prefix),
                    "sortedby" : facets
                },
            ],
            'fast': [
                {
                    "query_parser" : whoosh.qparser.MultifieldParser(
                        ["label", "content"], schema=self.index.schema,
                        termclass=whoosh.query.Term),
                    "sortedby" : facets
                },
            ],
        }

        self.check_workdir()
        self.cleanup_rootdir(callback)
        self.reload_index(callback)

        self.label_estimators_dir = os.path.join(base_indexdir,
                                                  "paperwork",
                                                  "label_estimators")
        self.label_estimators_file = os.path.join(self.label_estimators_dir,
                                                  "label_estimators.jbl")
        try:
            logger.info("Opening label_estimators file '%s' ..." %
                        self.label_estimators_file)
            (l_estimators,ver) = joblib.load(self.label_estimators_file)
            if ver != BasicDoc.FEATURES_VER:
                logger.info("Estimator version is not up to date")
                self.label_estimators = {}
            else:
                self.label_estimators = l_estimators

            # check that the label_estimators are up to date for their class
            for label_name in self.label_estimators:
                params = self.label_estimators[label_name].get_params()
                if params != self.LABEL_ESTIMATOR_TEMPLATE.get_params():
                    raise IndexError('label_estimators params are not up to date')
        except Exception, exc:
            logger.error("Failed to open label_estimator file '%s', or bad label_estimator structure"
                   % self.indexdir)
            logger.error("Exception was: %s" % exc)
            logger.info("Will create new label_estimators")
            self.label_estimators = {}

    def save_label_estimators(self):
        if not os.path.exists(self.label_estimators_dir):
            os.mkdir(self.label_estimators_dir)
        joblib.dump((self.label_estimators, BasicDoc.FEATURES_VER),
                    self.label_estimators_file,
                    compress=0)

    def __must_clean(self, filepath):
        must_clean_cbs = [
            is_dir_empty,
        ]
        for must_clean_cb in must_clean_cbs:
            if must_clean_cb(filepath):
                return True
        return False

    def check_workdir(self):
        """
        Check that the current work dir (see config.PaperworkConfig) exists. If
        not, open the settings dialog.
        """
        mkdir_p(self.rootdir)

    def cleanup_rootdir(self, progress_cb=dummy_progress_cb):
        """
        Remove all the crap from the work dir (temporary files, empty
        directories, etc)
        """
        progress_cb(0, 1, self.INDEX_STEP_CLEANING)
        for filename in os.listdir(self.rootdir):
            filepath = os.path.join(self.rootdir, filename)
            if self.__must_clean(filepath):
                logger.info("Cleanup: Removing '%s'" % filepath)
                rm_rf(filepath)
            elif os.path.isdir(filepath):
                # we only want to go one subdirectory deep, no more
                for subfilename in os.listdir(filepath):
                    subfilepath = os.path.join(filepath, subfilename)
                    if self.__must_clean(subfilepath):
                        logger.info("Cleanup: Removing '%s'" % subfilepath)
                        rm_rf(subfilepath)
        progress_cb(1, 1, self.INDEX_STEP_CLEANING)

    def get_doc_examiner(self):
        """
        Return an object useful to find added/modified/removed documents
        """
        return DocDirExaminer(self)

    def get_index_updater(self, optimize=True):
        """
        Return an object useful to update the content of the index

        Note that this object is only about modifying the index. It is not
        made to modify the documents themselves.
        Some helper methods, with more specific goals, may be available for
        what you want to do.
        """
        return DocIndexUpdater(self, optimize)

    def fit_label_estimator(self, docs=None, removed_label=None, labels=None):
        """
        fit the estimator with the supervised documents

        Arguments:
            docs --- a collection of documents to fit the estimator with
                if none, all the docs are used
            removed_label --- if the fitting is done when a label is removed
                a doc with no label is not used for learning (fitting), unless
                the label has been explicitely removed
            labels --- a collection a labels to operate with. If none, all
                the labels are used
        """
        if docs is None:
            docs = self.docs


        if labels is None:
            labels = set(self.label_list)
            for doc in docs:
                labels.union(set(doc.labels))
        else:
            labels = set(labels)

        label_name_set = set([label.name for label in labels])

        # construct the estimators if not present in the list
        for label_name in label_name_set:
            if label_name not in self.label_estimators:
                self.label_estimators[label_name] = copy.deepcopy(DocSearch.LABEL_ESTIMATOR_TEMPLATE)

        for doc in docs:
            logger.info("Fitting estimator with doc: %s " % doc)
            # fit only with labelled documents
            if doc.labels:
                for label_name in label_name_set:
                    # check for this estimator if the document is labelled or not
                    doc_has_label = 'unlabelled'
                    for label in doc.labels:
                        if label.name == label_name:
                            doc_has_label = 'labelled'
                            break

                    # fit the estimators with the model class (labelled or unlabelled)
                    # don't use True or False for the classes as it raises a casting bug in underlying library
                    l_estimator =  self.label_estimators[label_name]
                    l_estimator.partial_fit(doc.get_features(),
                                            [doc_has_label],
                                            numpy.array(['labelled','unlabelled']))
            elif removed_label:
                l_estimator = self.label_estimators[removed_label.name]
                l_estimator.partial_fit(doc.get_features(),
                                        ['unlabelled'],
                                        numpy.array(['labelled','unlabelled']))

    def predict_label_list(self, doc, progress_cb=dummy_progress_cb):
        """
        return a prediction of label names
        """
        if doc.nb_pages <= 0:
            return []

        # if there is only one label, or not enough document fitted prediction is not possible
        if len(self.label_estimators) < 2:
            return []

        predicted_label_list = []
        label_names = self.label_estimators.keys()

        for label_name_idx in xrange(0, len(label_names)):
            progress_cb(label_name_idx, len(label_names))

            label_name = label_names[label_name_idx]
            features = doc.get_features()
            # check that the estimator will not throw an error because its not fitted
            if self.label_estimators[label_name].coef_ is None:
                logger.warning("Label estimator '%s' not fitted yet"
                               % label_name)
                continue
            prediction = self.label_estimators[label_name].predict(features)
            if prediction == 'labelled':
                predicted_label_list.append(label_name)
            logger.debug("%s %s %s with decision %s "
                         % (doc, prediction, label_name,
                            self.label_estimators[label_name].
                            decision_function(features)))
        return predicted_label_list

    def __inst_doc(self, docid, doc_type_name=None):
        """
        Instantiate a document based on its document id.
        The information are taken from the whoosh index.
        """
        doc = None
        docpath = os.path.join(self.rootdir, docid)
        if not os.path.exists(docpath):
            return None
        if doc_type_name is not None:
            # if we already know the doc type name
            for (is_doc_type, doc_type_name_b, doc_type) in DOC_TYPE_LIST:
                if doc_type_name_b == doc_type_name:
                    doc = doc_type(docpath, docid)
            if not doc:
                logger.warning("Warning: unknown doc type found in the index: %s"
                   % doc_type_name)
        # otherwise we guess the doc type
        if not doc:
            for (is_doc_type, doc_type_name, doc_type) in DOC_TYPE_LIST:
                if is_doc_type(docpath):
                    doc = doc_type(docpath, docid)
                    break
        if not doc:
            logger.warning("Warning: unknown doc type for doc '%s'" % docid)

        return doc

    def get_doc_from_docid(self, docid, doc_type_name=None):
        """
        Try to find a document based on its document id. If it hasn't been
        instantiated yet, it will be.
        """
        assert(docid is not None)
        if docid in self.__docs_by_id:
            return self.__docs_by_id[docid]
        doc = self.__inst_doc(docid, doc_type_name)
        if doc is None:
            return None
        self.__docs_by_id[docid] = doc
        return doc

    def reload_index(self, progress_cb=dummy_progress_cb):
        """
        Read the index, and load the document list from it
        """
        docs_by_id = self.__docs_by_id
        self.__docs_by_id = {}
        for doc in docs_by_id.values():
            doc.drop_cache()
        del docs_by_id

        query = whoosh.query.Every()
        results = self.__searcher.search(query, limit=None)

        nb_results = len(results)
        progress = 0
        labels = set()

        for result in results:
            docid = result['docid']
            doctype = result['doctype']
            doc = self.__inst_doc(docid, doctype)
            if doc is None:
                continue
            progress_cb(progress, nb_results, self.INDEX_STEP_LOADING, doc)
            self.__docs_by_id[docid] = doc
            for label in doc.labels:
                labels.add(label)

            progress += 1
        progress_cb(1, 1, self.INDEX_STEP_LOADING)

        self.label_list = [label for label in labels]
        self.label_list.sort()

    def index_page(self, page):
        """
        Extract all the keywords from the given page

        Arguments:
            page --- from which keywords must be extracted

        Obsolete. To remove. Use get_index_updater() instead
        """
        updater = self.get_index_updater(optimize=False)
        updater.upd_doc(page.doc)
        updater.commit()
        if not page.doc.docid in self.__docs_by_id:
            logger.info("Adding document '%s' to the index" % page.doc.docid)
            assert(page.doc is not None)
            self.__docs_by_id[page.doc.docid] = page.doc

    def __get_all_docs(self):
        """
        Return all the documents. Beware, they are unsorted.
        """
        return self.__docs_by_id.values()

    docs = property(__get_all_docs)

    def get_by_id(self, obj_id):
        """
        Get a document or a page using its ID
        Won't instantiate them if they are not yet available
        """
        if "/" in obj_id:
            (docid, page_nb) = obj_id.split("/")
            page_nb = int(page_nb)
            return self.__docs_by_id[docid].pages[page_nb]
        return self.__docs_by_id[obj_id]

    def find_documents(self, sentence, limit=None, must_sort=True,
                       search_type='full'):
        """
        Returns all the documents matching the given keywords

        Arguments:
            sentence --- a sentenced query
        Returns:
            An array of document (doc objects)
        """
        sentence = sentence.strip()

        if sentence == u"":
            return self.docs

        result_list_list=[]
        total_results = 0

        for query_parser in self.search_param_list[search_type]:
            query = query_parser["query_parser"].parse(sentence)
            if must_sort and "sortedby" in query_parser:
                result_list = self.__searcher.search(
                    query, limit=limit, sortedby=query_parser["sortedby"])
            else:
                result_list = self.__searcher.search(
                    query, limit=limit)

            result_list_list.append(result_list)
            total_results += len(result_list)

            if not must_sort and total_results >= limit:
                break

        # merging results
        results = result_list_list[0]
        for result_intermediate in result_list_list[1:]:
            results.extend(result_intermediate)

        docs = [self.__docs_by_id.get(result['docid']) for result in results]
        try:
            while True:
                docs.remove(None)
        except ValueError:
            pass
        assert (not None in docs)

        if limit is not None:
            docs = docs[:limit]

        return docs

    def find_suggestions(self, sentence):
        """
        Search all possible suggestions. Suggestions returned always have at
        least one document matching.

        Arguments:
            sentence --- keywords (single strings) for which we want
                suggestions
        Return:
            An array of sets of keywords. Each set of keywords (-> one string)
            is a suggestion.
        """
        keywords = sentence.split(" ")
        final_suggestions = []

        corrector = self.__searcher.corrector("content")
        label_corrector = self.__searcher.corrector("label")
        for keyword_idx in range(0, len(keywords)):
            keyword = keywords[keyword_idx]
            if (len(keyword) <= MIN_KEYWORD_LEN):
                continue
            keyword_suggestions = label_corrector.suggest(keyword, limit=2)[:]
            keyword_suggestions += corrector.suggest(keyword, limit=5)[:]
            for keyword_suggestion in keyword_suggestions:
                new_suggestion = keywords[:]
                new_suggestion[keyword_idx] = keyword_suggestion
                new_suggestion = u" ".join(new_suggestion)

                docs = self.find_documents(new_suggestion, limit=1,
                                           must_sort=False, search_type='fast')
                if len(docs) <= 0:
                    continue
                final_suggestions.append(new_suggestion)
        final_suggestions.sort()
        return final_suggestions

    def add_label(self, doc, label, update_index=True):
        """
        Add a label on a document.

        Arguments:
            label --- The new label (see labels.Label)
            doc --- The first document on which this label has been added
        """
        label = copy.copy(label)
        new_label = False
        if not label in self.label_list:
            self.label_list.append(label)
            self.label_list.sort()
            new_label = True
        doc.add_label(label)
        if update_index:
            updater = self.get_index_updater(optimize=False)
            updater.upd_doc(doc)
        if new_label:
            # its a brand new label, there is a new estimator.
            # we need to fit this new estimator.
            self.fit_label_estimator(labels=[label])
        if update_index:
            updater.commit()

    def remove_label(self, doc, label, update_index=True):
        """
        Remove a label from a doc. Takes care of updating the index
        """
        doc.remove_label(label)
        if update_index:
            updater = self.get_index_updater(optimize=False)
            updater.upd_doc(doc)
            self.fit_label_estimator(docs=[doc], removed_label=label)
            updater.commit()

    def update_label(self, old_label, new_label, callback=dummy_progress_cb):
        """
        Replace 'old_label' by 'new_label' on all the documents. Takes care of
        updating the index.
        """
        assert(old_label)
        assert(new_label)
        self.label_list.remove(old_label)
        if old_label.name in self.label_estimators:
            self.label_estimators[new_label.name] = self.label_estimators.pop(old_label.name)
        if new_label not in self.label_list:
            self.label_list.append(new_label)
            self.label_list.sort()
        current = 0
        total = len(self.docs)
        updater = self.get_index_updater(optimize=False)
        for doc in self.docs:
            must_reindex = (old_label in doc.labels)
            callback(current, total, self.LABEL_STEP_UPDATING, doc)
            doc.update_label(old_label, new_label)
            if must_reindex:
                updater.upd_doc(doc)
            current += 1

        updater.commit()

    def destroy_label(self, label, callback=dummy_progress_cb):
        """
        Remove the label 'label' from all the documents. Takes care of updating
        the index.
        """
        assert(label)
        self.label_list.remove(label)
        self.label_estimators.pop(label.name)
        current = 0
        docs = self.docs
        total = len(docs)
        updater = self.get_index_updater(optimize=False)
        for doc in docs:
            must_reindex = (label in doc.labels)
            callback(current, total, self.LABEL_STEP_DESTROYING, doc)
            doc.remove_label(label)
            if must_reindex:
                updater.upd_doc(doc)
            current += 1
        updater.commit()

    def reload_searcher(self):
        """
        When the index has been updated, it's safer to re-instantiate the Whoosh
        Searcher object used to browse it.

        You shouldn't have to call this method yourself.
        """
        searcher = self.__searcher
        self.__searcher = self.index.searcher()
        del(searcher)

    def destroy_index(self):
        """
        Destroy the index. Don't use this DocSearch object anymore after this
        call. Next instantiation of a DocSearch will rebuild the whole index
        """
        logger.info("Destroying the index ...")
        rm_rf(self.indexdir)
        rm_rf(self.label_estimators_dir)
        logger.info("Done")

    def is_hash_in_index(self, filehash):
        """
        Check if there is a document using this file hash
        """
        filehash = (u"%X" % filehash)
        results = self.__searcher.search(
               Term('docfilehash', filehash))
        return results

########NEW FILE########
__FILENAME__ = doc
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#    Copyright (C) 2012  Sebastien Maccagnoni-Munch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.
"""
Code for managing documents (not page individually ! see page.py for that)
"""

import codecs
import datetime
import errno
import os
import os.path
import time
import logging

import cairo
from gi.repository import Gio
import PIL.Image
from gi.repository import Poppler

from paperwork.backend.common.doc import BasicDoc
from paperwork.backend.img.page import ImgPage
from paperwork.backend.util import dummy_progress_cb
from paperwork.backend.util import image2surface
from paperwork.backend.util import surface2image
from paperwork.backend.util import mkdir_p

logger = logging.getLogger(__name__)


class ImgToPdfDocExporter(object):
    can_change_quality = True
    can_select_format = True
    valid_exts = ['pdf']

    def __init__(self, doc):
        self.doc = doc
        self.__quality = 75
        self.__preview = None  # will just contain the first page
        self.__page_format = (0, 0)

    def get_mime_type(self):
        return 'application/pdf'

    def get_file_extensions(self):
        return ['pdf']

    def __save(self, target_path, pages):
        pdf_surface = cairo.PDFSurface(target_path,
                                       self.__page_format[0],
                                       self.__page_format[1])
        pdf_context = cairo.Context(pdf_surface)

        quality = float(self.__quality) / 100.0

        for page in [self.doc.pages[x] for x in range(pages[0], pages[1])]:
            img = page.img
            if (img.size[0] < img.size[1]):
                (x, y) = (min(self.__page_format[0], self.__page_format[1]),
                          max(self.__page_format[0], self.__page_format[1]))
            else:
                (x, y) = (max(self.__page_format[0], self.__page_format[1]),
                          min(self.__page_format[0], self.__page_format[1]))
            pdf_surface.set_size(x, y)
            new_size = (int(quality * img.size[0]),
                        int(quality * img.size[1]))
            img = img.resize(new_size, PIL.Image.ANTIALIAS)

            scale_factor_x = x / img.size[0]
            scale_factor_y = y / img.size[1]
            scale_factor = min(scale_factor_x, scale_factor_y)

            img_surface = image2surface(img)

            pdf_context.identity_matrix()
            pdf_context.scale(scale_factor, scale_factor)
            pdf_context.set_source_surface(img_surface)
            pdf_context.paint()

            pdf_context.show_page()

        return target_path

    def save(self, target_path):
        return self.__save(target_path, (0, self.doc.nb_pages))

    def refresh(self):
        # make the preview

        tmp = "%s.%s" % (os.tempnam(None, "paperwork_export_"),
                         self.valid_exts[0])
        path = self.__save(tmp, pages=(0, 1))

        # reload the preview

        pdfdoc = Poppler.Document.new_from_file(
            ("file://%s" % path), password=None)
        assert(pdfdoc.get_n_pages() > 0)

        pdfpage = pdfdoc.get_page(0)
        pdfpage_size = pdfpage.get_size()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     int(pdfpage_size[0]),
                                     int(pdfpage_size[1]))
        ctx = cairo.Context(surface)
        pdfpage.render(ctx)
        img = surface2image(surface)

        self.__preview = (path, img)

    def set_quality(self, quality):
        self.__quality = quality
        self.__preview = None

    def set_page_format(self, page_format):
        self.__page_format = page_format
        self.__preview = None

    def estimate_size(self):
        if self.__preview is None:
            self.refresh()
        return os.path.getsize(self.__preview[0]) * self.doc.nb_pages

    def get_img(self):
        if self.__preview is None:
            self.refresh()
        return self.__preview[1]

    def __str__(self):
        return 'PDF'


class _ImgPagesIterator(object):
    """
    Iterates on a page list
    """

    def __init__(self, page_list):
        self.idx = 0
        self.page_list = page_list

    def __iter__(self):
        return self

    def next(self):
        """
        Provide the next element of the list.
        """
        if self.idx >= len(self.page_list):
            raise StopIteration()
        page = self.page_list[self.idx]
        self.idx += 1
        return page


class _ImgPages(object):
    """
    Page list. Page are accessed using [] operator.
    """

    def __init__(self, doc):
        self.doc = doc

        nb_pages = self.doc.nb_pages
        self.__pages = [ImgPage(doc, idx) for idx in range(0, nb_pages)]

    def add(self, page):
        self.__pages.append(page)
        self.doc.drop_cache()

    def __getitem__(self, idx):
        return self.__pages[idx]

    def __len__(self):
        return self.doc.nb_pages

    def __contains__(self, page):
        return (page.doc == self.doc and page.page_nb <= self.doc.nb_pages)

    def __eq__(self, other):
        return (self.doc == other.doc)

    def __iter__(self):
        return _ImgPagesIterator(self)


class ImgDoc(BasicDoc):
    """
    Represents a document (aka a set of pages + labels).
    """
    IMPORT_IMG_EXTENSIONS = [
        ".jpg",
        ".jpeg",
        ".png"
    ]
    can_edit = True
    doctype = u"Img"

    def __init__(self, docpath, docid=None):
        """
        Arguments:
            docpath --- For an existing document, the path to its folder. For
                a new one, the rootdir of all documents
            docid --- Document Id (ie folder name). Use None for a new document
        """
        BasicDoc.__init__(self, docpath, docid)
        self.__pages = None

    def __get_last_mod(self):
        last_mod = 0.0
        for page in self.pages:
            if last_mod < page.last_mod:
                last_mod = page.last_mod
        labels_path = os.path.join(self.path, BasicDoc.LABEL_FILE)
        try:
            file_last_mod = os.stat(labels_path).st_mtime
            if file_last_mod > last_mod:
                last_mod = file_last_mod
        except OSError, err:
            pass
        extra_txt_path = os.path.join(self.path, BasicDoc.EXTRA_TEXT_FILE)
        try:
            file_last_mod = os.stat(extra_txt_path).st_mtime
            if file_last_mod > last_mod:
                last_mod = file_last_mod
        except OSError, err:
            pass
        return last_mod

    last_mod = property(__get_last_mod)

    def __get_pages(self):
        if self.__pages is None:
            self.__pages = _ImgPages(self)
        return self.__pages

    pages = property(__get_pages)

    def _get_nb_pages(self):
        """
        Compute the number of pages in the document. It basically counts
        how many JPG files there are in the document.
        """
        try:
            filelist = os.listdir(self.path)
            count = 0
            for filename in filelist:
                if (filename[-4:].lower() != "." + ImgPage.EXT_IMG
                    or (filename[-10:].lower() == "." + ImgPage.EXT_THUMB)
                    or (filename[:len(ImgPage.FILE_PREFIX)].lower() !=
                        ImgPage.FILE_PREFIX)):
                    continue
                count += 1
            return count
        except OSError, exc:
            if exc.errno != errno.ENOENT:
                logging.error("Exception while trying to get the number of pages of "
                       "'%s': %s" % (self.docid, exc))
                raise
            return 0

    def print_page_cb(self, print_op, print_context, page_nb):
        """
        Called for printing operation by Gtk
        """
        page = ImgPage(self, page_nb)
        page.print_page_cb(print_op, print_context)

    @staticmethod
    def get_export_formats():
        return ['PDF']

    def build_exporter(self, file_format='pdf'):
        return ImgToPdfDocExporter(self)

    def steal_page(self, page):
        """
        Steal a page from another document
        """
        if page.doc == self:
            return
        mkdir_p(self.path)
        other_doc = page.doc
        other_doc_nb_pages = page.doc.nb_pages

        new_page = ImgPage(self, self.nb_pages)
        logger.info("%s --> %s" % (str(page), str(new_page)))
        new_page._steal_content(page)
        page.doc.drop_cache()
        self.drop_cache()

    def drop_cache(self):
        BasicDoc.drop_cache(self)
        del(self.__pages)
        self.__pages = None

    def get_docfilehash(self):
        if self._get_nb_pages() == 0:
            print "WARNING: Document %s is empty" % self.docid
            dochash = ''
        else :
            dochash = 0
            for page in self.pages:
                dochash ^= page.get_docfilehash()
        return dochash

    def add_page(self, img, boxes):
        mkdir_p(self.path)
        page = ImgPage(self, self.nb_pages)
        page.img = img
        page.boxes = boxes
        self.drop_cache()
        return self.pages[-1]


def is_img_doc(docpath):
    if not os.path.isdir(docpath):
        return False
    try:
        filelist = os.listdir(docpath)
    except OSError, exc:
        logging.warn("Warning: Failed to list files in %s: %s" % (docpath, str(exc)))
        return False
    for filename in filelist:
        if filename.lower().endswith(ImgPage.EXT_IMG) and not filename.lower().endswith(ImgPage.EXT_THUMB):
            return True
    return False

########NEW FILE########
__FILENAME__ = page
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#    Copyright (C) 2012  Sebastien Maccagnoni-Munch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

"""
Code relative to page handling.
"""

import codecs
from copy import copy
import PIL.Image
import multiprocessing
import os
import os.path
import re
import threading
import time

import logging
from gi.repository import Gtk
import pyocr
import pyocr.builders

from paperwork.backend.common.page import BasicPage
from paperwork.backend.common.page import PageExporter
from paperwork.backend.config import PaperworkConfig
from paperwork.backend.util import check_spelling
from paperwork.backend.util import dummy_progress_cb
from paperwork.backend.util import image2surface


logger = logging.getLogger(__name__)


class ImgPage(BasicPage):
    """
    Represents a page. A page is a sub-element of ImgDoc.
    """
    FILE_PREFIX = "paper."
    EXT_TXT = "txt"
    EXT_BOX = "words"
    EXT_IMG = "jpg"

    KEYWORD_HIGHLIGHT = 3

    can_edit = True

    def __init__(self, doc, page_nb=None):
        if page_nb is None:
            page_nb = doc.nb_pages
        BasicPage.__init__(self, doc, page_nb)

    def __get_box_path(self):
        """
        Returns the file path of the box list corresponding to this page
        """
        return self._get_filepath(self.EXT_BOX)

    __box_path = property(__get_box_path)

    def __get_img_path(self):
        """
        Returns the file path of the image corresponding to this page
        """
        return self._get_filepath(self.EXT_IMG)

    def get_doc_file_path(self):
        """
        Returns the file path of the image corresponding to this page
        """
        return self.__get_img_path()

    __img_path = property(__get_img_path)

    def __get_last_mod(self):
        try:
            return os.stat(self.__get_box_path()).st_mtime
        except OSError, exc:
            return 0.0

    last_mod = property(__get_last_mod)

    def _get_text(self):
        """
        Get the text corresponding to this page
        """
        boxes = self.boxes
        txt = u""
        for box in boxes:
            txt += u" " + str(box).decode('utf-8')
        return [txt]

    def __get_boxes(self):
        """
        Get all the word boxes of this page.
        """
        boxfile = self.__box_path

        try:
            box_builder = pyocr.builders.LineBoxBuilder()
            with codecs.open(boxfile, 'r', encoding='utf-8') as file_desc:
                boxes = box_builder.read_file(file_desc)
            if boxes != []:
                return boxes
            # fallback: old format: word boxes
            # shouldn't be used anymore ...
            logger.warning("WARNING: Doc %s uses old box format" %
                           (str(self.doc)))
            box_builder = pyocr.builders.WordBoxBuilder()
            with codecs.open(boxfile, 'r', encoding='utf-8') as file_desc:
                boxes = box_builder.read_file(file_desc)
            return boxes
        except IOError, exc:
            logger.error("Unable to get boxes for '%s': %s"
                    % (self.doc.docid, exc))
            return []

    def __set_boxes(self, boxes):
        boxfile = self.__box_path
        with codecs.open(boxfile, 'w', encoding='utf-8') as file_desc:
            pyocr.builders.LineBoxBuilder().write_file(file_desc, boxes)
        self.drop_cache()
        self.doc.drop_cache()

    boxes = property(__get_boxes, __set_boxes)

    def __get_img(self):
        """
        Returns an image object corresponding to the page
        """
        return PIL.Image.open(self.__img_path)

    def __set_img(self, img):
        img.save(self.__img_path)
        self.drop_cache()

    img = property(__get_img, __set_img)

    def __get_size(self):
        return self.img.size

    size = property(__get_size)

    def print_page_cb(self, print_op, print_context):
        """
        Called for printing operation by Gtk
        """
        ORIENTATION_PORTRAIT = 0
        ORIENTATION_LANDSCAPE = 1
        SCALING = 2.0

        img = self.img
        (width, height) = img.size

        # take care of rotating the image if required
        if print_context.get_width() <= print_context.get_height():
            print_orientation = ORIENTATION_PORTRAIT
        else:
            print_orientation = ORIENTATION_LANDSCAPE
        if width <= height:
            img_orientation = ORIENTATION_PORTRAIT
        else:
            img_orientation = ORIENTATION_LANDSCAPE
        if print_orientation != img_orientation:
            logger.info("Rotating the page ...")
            img = img.rotate(90)

        # scale the image down
        # XXX(Jflesch): beware that we get floats for the page size ...
        new_w = int(SCALING * (print_context.get_width()))
        new_h = int(SCALING * (print_context.get_height()))

        logger.info("DPI: %fx%f" % (print_context.get_dpi_x(),
                              print_context.get_dpi_y()))
        logger.info("Scaling it down to %fx%f..." % (new_w, new_h))
        img = img.resize((new_w, new_h), PIL.Image.ANTIALIAS)

        surface = image2surface(img)

        # .. and print !
        cairo_context = print_context.get_cairo_context()
        cairo_context.scale(1.0 / SCALING, 1.0 / SCALING)
        cairo_context.set_source_surface(surface, 0, 0)
        cairo_context.paint()

    def __ch_number(self, offset=0, factor=1):
        """
        Move the page number by a given offset. Beware to not let any hole
        in the page numbers when doing this. Make sure also that the wanted
        number is available.
        Will also change the page number of the current object.
        """
        src = {}
        src["box"] = self.__get_box_path()
        src["img"] = self.__get_img_path()
        src["thumb"] = self._get_thumb_path()

        page_nb = self.page_nb

        page_nb += offset
        page_nb *= factor

        logger.info("--> Moving page %d (+%d*%d) to index %d"
               % (self.page_nb, offset, factor, page_nb))

        self.page_nb = page_nb

        dst = {}
        dst["box"] = self.__get_box_path()
        dst["img"] = self.__get_img_path()
        dst["thumb"] = self._get_thumb_path()

        for key in src.keys():
            if os.access(src[key], os.F_OK):
                if os.access(dst[key], os.F_OK):
                    logger.error("Error: file already exists: %s" % dst[key])
                    assert(0)
                os.rename(src[key], dst[key])

    def change_index(self, new_index):
        if (new_index == self.page_nb):
            return

        logger.info("Moving page %d to index %d" % (self.page_nb, new_index))

        # we remove ourselves from the page list by turning our index into a
        # negative number
        page_nb = self.page_nb
        self.__ch_number(offset=1, factor=-1)

        if (page_nb < new_index):
            move = 1
            start = page_nb + 1
            end = new_index + 1
        else:
            move = -1
            start = page_nb - 1
            end = new_index - 1

        logger.info("Moving the other pages: %d, %d, %d" % (start, end, move))
        for page_idx in range(start, end, move):
            page = self.doc.pages[page_idx]
            page.__ch_number(offset=-1*move)

        # restore our index in the positive values,
        # and move it the final index
        diff = new_index - page_nb
        diff *= -1  # our index is temporarily negative
        self.__ch_number(offset=diff+1, factor=-1)

        self.page_nb = new_index

        self.drop_cache()
        self.doc.drop_cache()

    def destroy(self):
        """
        Delete the page. May delete the whole document if it's actually the
        last page.
        """
        logger.info("Destroying page: %s" % self)
        if self.doc.nb_pages <= 1:
            self.doc.destroy()
            return
        doc_pages = self.doc.pages[:]
        current_doc_nb_pages = self.doc.nb_pages
        paths = [
            self.__get_box_path(),
            self.__get_img_path(),
            self._get_thumb_path(),
        ]
        for path in paths:
            if os.access(path, os.F_OK):
                os.unlink(path)
        for page_nb in range(self.page_nb + 1, current_doc_nb_pages):
            page = doc_pages[page_nb]
            page.__ch_number(offset=-1)
        self.drop_cache()
        self.doc.drop_cache()

    def _steal_content(self, other_page):
        """
        Call ImgDoc.steal_page() instead
        """
        other_doc = other_page.doc
        other_doc_pages = other_doc.pages[:]
        other_doc_nb_pages = other_doc.nb_pages
        other_page_nb = other_page.page_nb

        to_move = [
            (other_page.__get_box_path(), self.__get_box_path()),
            (other_page.__get_img_path(), self.__get_img_path()),
            (other_page._get_thumb_path(), self._get_thumb_path())
        ]
        for (src, dst) in to_move:
            # sanity check
            if os.access(dst, os.F_OK):
                logger.error("Error, file already exists: %s" % dst)
                assert(0)
        for (src, dst) in to_move:
            logger.info("%s --> %s" % (src, dst))
            os.rename(src, dst)

        if (other_doc_nb_pages <= 1):
            other_doc.destroy()
        else:
            for page_nb in range(other_page_nb + 1, other_doc_nb_pages):
                page = other_doc_pages[page_nb]
                page.__ch_number(offset=-1)

        self.drop_cache()

    def get_docfilehash(self):
        return self.doc.hash_file(self.__get_img_path())

########NEW FILE########
__FILENAME__ = labels
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

"""
Code to manage document labels
"""

from gi.repository import Gdk


class Label(object):
    """
    Represents a Label (color + string).
    """

    def __init__(self, name=u"", color="#000000000000"):
        """
        Arguments:
            name --- label name
            color --- label color (string representation, see get_color_str())
        """
        if type(name) == unicode:
            self.name = name
        else:
            self.name = unicode(name, encoding='utf-8')
        self.color = Gdk.color_parse(color)

    def __copy__(self):
        return Label(self.name, self.get_color_str())

    def __label_cmp(self, other):
        """
        Comparaison function. Can be used to sort labels alphabetically.
        """
        if other is None:
            return -1
        cmp_r = cmp(self.name, other.name)
        if cmp_r != 0:
            return cmp_r
        return cmp(self.get_color_str(), other.get_color_str())

    def __lt__(self, other):
        return self.__label_cmp(other) < 0

    def __gt__(self, other):
        return self.__label_cmp(other) > 0

    def __eq__(self, other):
        return self.__label_cmp(other) == 0

    def __le__(self, other):
        return self.__label_cmp(other) <= 0

    def __ge__(self, other):
        return self.__label_cmp(other) >= 0

    def __ne__(self, other):
        return self.__label_cmp(other) != 0

    def __hash__(self):
        return hash(self.name)

    def get_html_color(self):
        """
        get a string representing the color, using HTML notation
        """
        return ("#%02X%02X%02X" % (self.color.red >> 8, self.color.green >> 8,
                                   self.color.blue >> 8))

    def get_color_str(self):
        """
        Returns a string representation of the color associated to this label.
        """
        return self.color.to_string()

    def get_html(self):
        """
        Returns a HTML string that represent the label. Can be used with GTK.
        """
        return ("<span bgcolor=\"%s\">    </span> %s"
                % (self.get_html_color(), self.name))

    def get_rgb_fg(self):
        bg_color = self.get_rgb_bg()
        brightness = (((bg_color[0] * 255) * 0.299)
                      + ((bg_color[1] * 255) * 0.587)
                      + ((bg_color[2] * 255) * 0.114))
        if brightness > 186:
            return (0.0, 0.0, 0.0) # black
        else:
            return (1.0, 1.0, 1.0) # white

    def get_rgb_bg(self):
        return (float((self.color.red >> 8) & 0xFF) / 0xFF,
                float((self.color.green >> 8) & 0xFF) / 0xFF,
                float((self.color.blue >> 8) & 0xFF) / 0xFF)

    def __str__(self):
        return ("Color: %s ; Text: %s"
                % (self.get_html_color(), self.name))

########NEW FILE########
__FILENAME__ = doc
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import os
import shutil
import logging

import gi
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Poppler

from paperwork.backend.common.doc import BasicDoc
from paperwork.backend.pdf.page import PdfPage


PDF_FILENAME = "doc.pdf"
logger = logging.getLogger(__name__)


class PdfDocExporter(object):
    can_select_format = False
    can_change_quality = False

    def __init__(self, doc):
        self.doc = doc
        self.pdfpath = ("%s/%s" % (doc.path, PDF_FILENAME))

    def get_mime_type(self):
        return 'application/pdf'

    def get_file_extensions(self):
        return ['pdf']

    def save(self, target_path):
        shutil.copy(self.pdfpath, target_path)
        return target_path

    def estimate_size(self):
        return os.path.getsize(self.pdfpath)

    def get_img(self):
        return self.doc.pages[0].img

    def __str__(self):
        return 'PDF'


class PdfPagesIterator(object):
    def __init__(self, pdfdoc):
        self.pdfdoc = pdfdoc
        self.idx = 0
        self.pages = [pdfdoc.pages[i] for i in range(0, pdfdoc.nb_pages)]

    def __iter__(self):
        return self

    def next(self):
        if self.idx >= self.pdfdoc.nb_pages:
            raise StopIteration()
        page = self.pages[self.idx]
        self.idx += 1
        return page


class PdfPages(object):
    def __init__(self, pdfdoc):
        self.pdfdoc = pdfdoc
        self.page = {}

    def __getitem__(self, idx):
        if idx < 0:
            idx = self.pdfdoc.nb_pages + idx
        if idx not in self.page:
            self.page[idx] = PdfPage(self.pdfdoc, idx)
        return self.page[idx]

    def __len__(self):
        return self.pdfdoc.nb_pages

    def __iter__(self):
        return PdfPagesIterator(self.pdfdoc)


class PdfDoc(BasicDoc):
    can_edit = False
    doctype = u"PDF"

    def __init__(self, docpath, docid=None):
        BasicDoc.__init__(self, docpath, docid)
        self.__pdf = None
        self.__nb_pages = 0
        self.__pages = None

    def __get_last_mod(self):
        pdfpath = os.path.join(self.path, PDF_FILENAME)
        last_mod = os.stat(pdfpath).st_mtime
        for page in self.pages:
            if page.last_mod > last_mod:
                last_mod = page.last_mod
        labels_path = os.path.join(self.path, BasicDoc.LABEL_FILE)
        try:
            file_last_mod = os.stat(labels_path).st_mtime
            if file_last_mod > last_mod:
                last_mod = file_last_mod
        except OSError, err:
            pass
        extra_txt_path = os.path.join(self.path, BasicDoc.EXTRA_TEXT_FILE)
        try:
            file_last_mod = os.stat(extra_txt_path).st_mtime
            if file_last_mod > last_mod:
                last_mod = file_last_mod
        except OSError, err:
            pass

        return last_mod

    last_mod = property(__get_last_mod)

    def get_pdf_file_path(self):
        return  ("%s/%s" % (self.path, PDF_FILENAME))

    def _open_pdf(self):
        self.__pdf = Poppler.Document.new_from_file(
            ("file://%s/%s" % (self.path, PDF_FILENAME)),
            password=None)
        self.__nb_pages = self.pdf.get_n_pages()
        self.__pages = PdfPages(self)

    def __get_pdf(self):
        if self.__pdf is None:
            self._open_pdf()
        return self.__pdf

    pdf = property(__get_pdf)

    def __get_pages(self):
        if self.__pdf is None:
            self._open_pdf()
        return self.__pages

    pages = property(__get_pages)

    def _get_nb_pages(self):
        if self.__pdf is None:
            if self.is_new:
                # happens when a doc was recently deleted
                return 0
            self._open_pdf()
        return self.__nb_pages

    def print_page_cb(self, print_op, print_context, page_nb):
        """
        Called for printing operation by Gtk
        """
        self.pages[page_nb].print_page_cb(print_op, print_context)

    def import_pdf(self, config, file_uri):
        logger.info("PDF: Importing '%s'" % (file_uri))
        try:
            dest = Gio.File.parse_name("file://%s" % self.path)
            dest.make_directory(None)
        except GLib.GError, exc:
            logger.exception("Warning: Error while trying to create '%s': %s"
                    % (self.path, exc))
        f = Gio.File.parse_name(file_uri)
        dest = dest.get_child(PDF_FILENAME)
        f.copy(dest,
               0,  # TODO(Jflesch): Missing flags: don't keep attributes
               None, None, None)
        self._open_pdf()

    @staticmethod
    def get_export_formats():
        return ['PDF']

    def build_exporter(self, file_format='pdf'):
        return PdfDocExporter(self)

    def drop_cache(self):
        BasicDoc.drop_cache(self)
        del(self.__pdf)
        self.__pdf = None
        del(self.__pages)
        self.__pages = None

    def get_docfilehash(self):
        return BasicDoc.hash_file("%s/%s" % (self.path, PDF_FILENAME))


def is_pdf_doc(docpath):
    if not os.path.isdir(docpath):
        return False
    try:
        filelist = os.listdir(docpath)
    except OSError, exc:
        logger.exception("Warning: Failed to list files in %s: %s"
                % (docpath, str(exc)))
        return False
    return PDF_FILENAME in filelist

########NEW FILE########
__FILENAME__ = page
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import codecs
import os
import logging
import pyocr
import pyocr.builders

from paperwork.backend.common.page import BasicPage
from paperwork.backend.util import split_words
from paperwork.backend.util import surface2image


# By default, PDF are too small for a good image rendering
# so we increase their size
PDF_RENDER_FACTOR = 2
logger = logging.getLogger(__name__)


class PdfWordBox(object):
    def __init__(self, content, rectangle, pdf_size):
        self.content = content
        # XXX(Jflesch): Coordinates seem to come from the bottom left of the
        # page instead of the top left !?
        self.position = ((int(rectangle.x1 * PDF_RENDER_FACTOR),
                         int((pdf_size[1] - rectangle.y2)
                             * PDF_RENDER_FACTOR)),
                        (int(rectangle.x2 * PDF_RENDER_FACTOR),
                         int((pdf_size[1] - rectangle.y1)
                             * PDF_RENDER_FACTOR)))


class PdfLineBox(object):
    def __init__(self, word_boxes, rectangle, pdf_size):
        self.word_boxes = word_boxes
        # XXX(Jflesch): Coordinates seem to come from the bottom left of the
        # page instead of the top left !?
        self.position = ((int(rectangle.x1 * PDF_RENDER_FACTOR),
                         int((pdf_size[1] - rectangle.y2)
                             * PDF_RENDER_FACTOR)),
                        (int(rectangle.x2 * PDF_RENDER_FACTOR),
                         int((pdf_size[1] - rectangle.y1)
                             * PDF_RENDER_FACTOR)))


class PdfPage(BasicPage):
    EXT_TXT = "txt"
    EXT_BOX = "words"

    def __init__(self, doc, page_nb):
        BasicPage.__init__(self, doc, page_nb)
        self.pdf_page = doc.pdf.get_page(page_nb)
        assert(self.pdf_page is not None)
        size = self.pdf_page.get_size()
        self._size = (int(size[0]), int(size[1]))
        self.__boxes = None
        self.__img_cache = {}
        doc = doc

    def get_doc_file_path(self):
        """
        Returns the file path of the image corresponding to this page
        """
        return self.doc.get_pdf_file_path()

    def __get_txt_path(self):
        return self._get_filepath(self.EXT_TXT)

    def __get_box_path(self):
        return self._get_filepath(self.EXT_BOX)

    def __get_last_mod(self):
        try:
            return os.stat(self.__get_txt_path()).st_mtime
        except OSError, exc:
            return 0.0

    last_mod = property(__get_last_mod)

    def _get_text(self):
        txtfile = self.__get_txt_path()

        try:
            os.stat(txtfile)

            txt = []
            try:
                with codecs.open(txtfile, 'r', encoding='utf-8') as file_desc:
                    for line in file_desc.readlines():
                        line = line.strip()
                        txt.append(line)
            except IOError, exc:
                logger.error("Unable to read [%s]: %s" % (txtfile, str(exc)))
            return txt

        except OSError, exc:  # os.stat() failed
            txt = self.pdf_page.get_text()
            txt = unicode(txt, encoding='utf-8')
            return txt.split(u"\n")

    def __get_boxes(self):
        """
        Get all the word boxes of this page.
        """
        if self.__boxes is not None:
            return self.__boxes

        # Check first if there is an OCR file available
        boxfile = self.__get_box_path()
        try:
            os.stat(boxfile)

            box_builder = pyocr.builders.LineBoxBuilder()

            try:
                with codecs.open(boxfile, 'r', encoding='utf-8') as file_desc:
                    self.__boxes = box_builder.read_file(file_desc)
                return self.__boxes
            except IOError, exc:
                logger.error("Unable to get boxes for '%s': %s"
                       % (self.doc.docid, exc))
                # will fall back on pdf boxes
        except OSError, exc:  # os.stat() failed
            pass

        # fall back on what libpoppler tells us

        # TODO: Line support !

        txt = self.pdf_page.get_text()
        pdf_size = self.pdf_page.get_size()
        words = set()
        self.__boxes = []
        for line in txt.split("\n"):
            for word in split_words(unicode(line, encoding='utf-8')):
                words.add(word)
        for word in words:
            for rect in self.pdf_page.find_text(word):
                word_box = PdfWordBox(word, rect, pdf_size)
                line_box = PdfLineBox([word_box], rect, pdf_size)
                self.__boxes.append(line_box)
        return self.__boxes

    def __set_boxes(self, boxes):
        boxfile = self.__get_box_path()
        with codecs.open(boxfile, 'w', encoding='utf-8') as file_desc:
            pyocr.builders.LineBoxBuilder().write_file(file_desc, boxes)
        self.drop_cache()
        self.doc.drop_cache()

    boxes = property(__get_boxes, __set_boxes)

    def __render_img(self, factor):
        # TODO(Jflesch): In a perfect world, we shouldn't use ImageSurface.
        # we should draw directly on the GtkImage.window.cairo_create()
        # context. It would be much more efficient.

        if factor not in self.__img_cache:
            logger.debug('Building img from pdf with factor: %s'
                    % factor)
            width = int(factor * self._size[0])
            height = int(factor * self._size[1])

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            ctx = cairo.Context(surface)
            ctx.scale(factor, factor)
            self.pdf_page.render(ctx)
            self.__img_cache[factor] = surface2image(surface)
        return self.__img_cache[factor]

    def __get_img(self):
        return self.__render_img(PDF_RENDER_FACTOR)

    img = property(__get_img)

    def __get_size(self):
        return (self._size[0] * PDF_RENDER_FACTOR,
                self._size[1] * PDF_RENDER_FACTOR)

    size = property(__get_size)

    def print_page_cb(self, print_op, print_context):
        ctx = print_context.get_cairo_context()

        logger.debug("Context: %d x %d" % (print_context.get_width(),
                                    print_context.get_height()))
        logger.debug("Size: %d x %d" % (self._size[0], self._size[1]))

        factor_x = float(print_context.get_width()) / float(self._size[0])
        factor_y = float(print_context.get_height()) / float(self._size[1])
        factor = min(factor_x, factor_y)

        logger.debug("Scale: %f x %f --> %f" % (factor_x, factor_y, factor))

        ctx.scale(factor, factor)

        self.pdf_page.render_for_printing(ctx)
        return None

########NEW FILE########
__FILENAME__ = util
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>

import array
import errno
import logging
import os
import re
import StringIO
import threading
import unicodedata

import enchant
import enchant.tokenize
import Levenshtein
import numpy

logger = logging.getLogger(__name__)
FORCED_SPLIT_KEYWORDS_REGEX = re.compile("[ '()]", re.UNICODE)
WISHED_SPLIT_KEYWORDS_REGEX = re.compile("[^\w!]", re.UNICODE)

MIN_KEYWORD_LEN = 3


def strip_accents(string):
    """
    Strip all the accents from the string
    """
    return ''.join(
        (character for character in unicodedata.normalize('NFD', string)
         if unicodedata.category(character) != 'Mn'))


def __cleanup_word_array(keywords):
    """
    Yield all the keywords long enough to be used
    """
    for word in keywords:
        if len(word) >= MIN_KEYWORD_LEN:
            yield word


def split_words(sentence):
    """
    Extract and yield the keywords from the sentence:
    - Drop keywords that are too short
    - Drop the accents
    - Make everything lower case
    - Try to separate the words as much as possible (using 2 list of
      separators, one being more complete than the others)
    """
    if (sentence == "*"):
        yield sentence
        return

    # TODO: i18n
    sentence = sentence.lower()
    sentence = strip_accents(sentence)

    words = FORCED_SPLIT_KEYWORDS_REGEX.split(sentence)
    for word in __cleanup_word_array(words):
        can_split = True
        can_yield = False
        subwords = WISHED_SPLIT_KEYWORDS_REGEX.split(word)
        for subword in subwords:
            if subword == "":
                continue
            can_yield = True
            if len(subword) < MIN_KEYWORD_LEN:
                can_split = False
                break
        if can_split:
            for subword in subwords:
                if subword == "":
                    continue
                if subword[0] == '"':
                    subword = subword[1:]
                if subword[-1] == '"':
                    subword = subword[:-1]
                yield subword
        elif can_yield:
            if word[0] == '"':
                word = word[1:]
            if word[-1] == '"':
                word = word[:-1]
            yield word



def dummy_progress_cb(progression, total, step=None, doc=None):
    """
    Dummy progression callback. Do nothing.
    """
    pass


_ENCHANT_LOCK = threading.Lock()
_MAX_LEVENSHTEIN_DISTANCE = 1
_MIN_WORD_LEN = 4


def check_spelling(spelling_lang, txt):
    """
    Check the spelling in the text, and compute a score. The score is the
    number of words correctly (or almost correctly) spelled, minus the number
    of mispelled words. Words "almost" correct remains neutral (-> are not
    included in the score)

    Returns:
        A tuple : (fixed text, score)
    """
    _ENCHANT_LOCK.acquire()
    try:
        # Maximum distance from the first suggestion from python-enchant

        words_dict = enchant.request_dict(spelling_lang)
        try:
            tknzr = enchant.tokenize.get_tokenizer(spelling_lang)
        except enchant.tokenize.TokenizerNotFoundError:
            # Fall back to default tokenization if no match for 'lang'
            tknzr = enchant.tokenize.get_tokenizer()

        score = 0
        offset = 0
        for (word, word_pos) in tknzr(txt):
            if len(word) < _MIN_WORD_LEN:
                continue
            if words_dict.check(word):
                # immediately correct words are a really good hint for
                # orientation
                score += 100
                continue
            suggestions = words_dict.suggest(word)
            if (len(suggestions) <= 0):
                # this word is useless. It may even indicates a bad orientation
                score -= 10
                continue
            main_suggestion = suggestions[0]
            lv_dist = Levenshtein.distance(word, main_suggestion)
            if (lv_dist > _MAX_LEVENSHTEIN_DISTANCE):
                # hm, this word looks like it's in a bad shape
                continue

            logging.debug("Spell checking: Replacing: %s -> %s"
                   % (word, main_suggestion))

            # let's replace the word by its suggestion

            pre_txt = txt[:word_pos + offset]
            post_txt = txt[word_pos + len(word) + offset:]
            txt = pre_txt + main_suggestion + post_txt
            offset += (len(main_suggestion) - len(word))

            # fixed words may be a good hint for orientation
            score += 5

        return (txt, score)
    finally:
        _ENCHANT_LOCK.release()


def mkdir_p(path):
    """
    Act as 'mkdir -p' in the shell
    """
    try:
        os.makedirs(path)
    except OSError, exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def rm_rf(path):
    """
    Act as 'rm -rf' in the shell
    """
    if os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for filename in files:
                filepath = os.path.join(root, filename)
                logging.info("Deleting file %s" % filepath)
                os.unlink(filepath)
            for dirname in dirs:
                dirpath = os.path.join(root, dirname)
                logging.info("Deleting dir %s" % dirpath)
                os.rmdir(dirpath)
        os.rmdir(path)


def surface2image(surface):
    """
    Convert a cairo surface into a PIL image
    """
    import cairo
    import PIL.Image
    import PIL.ImageDraw

    if surface is None:
        return None
    dimension = (surface.get_width(), surface.get_height())
    img = PIL.Image.frombuffer("RGBA", dimension,
                           surface.get_data(), "raw", "BGRA", 0, 1)

    background = PIL.Image.new("RGB", img.size, (255, 255, 255))
    background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
    return background


def image2surface(img):
    """
    Convert a PIL image into a Cairo surface
    """
    import cairo

    img.putalpha(256)
    (width, height) = img.size
    imgd = img.tobytes('raw', 'BGRA')
    imga = array.array('B', imgd)
    stride = width * 4
    return cairo.ImageSurface.create_for_data(
        imga, cairo.FORMAT_ARGB32, width, height, stride)

########NEW FILE########
__FILENAME__ = pages
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import threading
import time

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import PangoCairo

from paperwork.backend.util import image2surface
from paperwork.backend.util import split_words
from paperwork.frontend.util.canvas.animations import SpinnerAnimation
from paperwork.frontend.util.canvas.drawers import Drawer
from paperwork.frontend.util.jobs import Job
from paperwork.frontend.util.jobs import JobFactory
from paperwork.frontend.util.jobs import JobScheduler


class JobPageImgLoader(Job):
    can_stop = False
    priority = 500

    __gsignals__ = {
        'page-loading-start': (GObject.SignalFlags.RUN_LAST, None, ()),
        'page-loading-img': (GObject.SignalFlags.RUN_LAST, None,
                             (GObject.TYPE_PYOBJECT,)),
        'page-loading-done': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, factory, job_id, page):
        Job.__init__(self, factory, job_id)
        self.page = page

    def do(self):
        self.emit('page-loading-start')
        try:
            img = self.page.img
            img.load()
            self.emit('page-loading-img', image2surface(img))

        finally:
            self.emit('page-loading-done')


GObject.type_register(JobPageImgLoader)


class JobFactoryPageImgLoader(JobFactory):
    def __init__(self):
        JobFactory.__init__(self, "PageImgLoader")

    def make(self, drawer, page):
        job = JobPageImgLoader(self, next(self.id_generator), page)
        job.connect('page-loading-img',
                    lambda job, img:
                    GLib.idle_add(drawer.on_page_loading_img,
                                  job.page, img))
        return job


class JobPageBoxesLoader(Job):
    can_stop = True
    priority = 100

    __gsignals__ = {
        'page-loading-start': (GObject.SignalFlags.RUN_LAST, None, ()),
        'page-loading-boxes': (GObject.SignalFlags.RUN_LAST, None,
                               (
                                   GObject.TYPE_PYOBJECT,  # all boxes
                               )),
        'page-loading-done': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, factory, job_id, page):
        Job.__init__(self, factory, job_id)
        self.page = page
        self.__cond = threading.Condition()

    def do(self):
        self.can_run = True
        self.emit('page-loading-start')
        try:
            line_boxes = self.page.boxes

            self.__cond.acquire()
            try:
                self.__cond.wait(1.0)
            finally:
                self.__cond.release()
            if not self.can_run:
                self.emit('page-loading-done')

            boxes = []
            highlight = set()

            boxes = []
            for line in line_boxes:
                boxes += line.word_boxes

            self.emit('page-loading-boxes', boxes)
        finally:
            self.emit('page-loading-done')

    def stop(self, will_resume=False):
        self.can_run = False
        self.__cond.acquire()
        try:
            self.__cond.notify_all()
        finally:
            self.__cond.release()


GObject.type_register(JobPageBoxesLoader)


class JobFactoryPageBoxesLoader(JobFactory):
    def __init__(self):
        JobFactory.__init__(self, "PageBoxesLoader")

    def make(self, drawer, page):
        job = JobPageBoxesLoader(self, next(self.id_generator), page)
        job.connect('page-loading-boxes',
                    lambda job, all_boxes:
                    GLib.idle_add(drawer.on_page_loading_boxes,
                                  job.page, all_boxes))
        return job


class PageDrawer(Drawer):
    layer = Drawer.IMG_LAYER

    def __init__(self, position, page,
                 job_factories,
                 job_schedulers,
                 show_all_boxes=False,
                 sentence=u""):
        Drawer.__init__(self)

        self.max_size = page.size
        self.page = page
        self.show_all_boxes = show_all_boxes

        self.surface = None
        self.boxes = {
            'all': [],
            'highlighted': [],
            'mouse_over': None,
        }
        self.sentence = sentence
        self.visible = False
        self.loading = False

        self.factories = job_factories
        self.schedulers = job_schedulers

        self._position = position
        self._size = self.max_size
        self.spinner = SpinnerAnimation((0, 0))
        self.upd_spinner_position()

    def set_canvas(self, canvas):
        Drawer.set_canvas(self, canvas)
        canvas.connect("absolute-motion-notify-event", lambda canvas, event:
                       GLib.idle_add(self._on_mouse_motion, event))

    def on_tick(self):
        Drawer.on_tick(self)
        self.spinner.on_tick()

    def upd_spinner_position(self):
        self.spinner.position = (
            (self._position[0] + (self._size[0] / 2)
             - (SpinnerAnimation.ICON_SIZE / 2)),
            (self._position[1] + (self._size[1] / 2)
             - (SpinnerAnimation.ICON_SIZE / 2)),
        )

    def _get_position(self):
        return self._position

    def _set_position(self, position):
        self._position = position
        self.upd_spinner_position()

    position = property(_get_position, _set_position)

    def _get_size(self):
        return self._size

    def _set_size(self, size):
        self._size = size
        self.upd_spinner_position()

    size = property(_get_size, _set_size)

    def set_size_ratio(self, factor):
        self.size = (int(factor * self.max_size[0]),
                     int(factor * self.max_size[1]))

    def load_content(self):
        if self.loading:
            return
        self.canvas.add_drawer(self.spinner)
        self.loading = True
        job = self.factories['page_img_loader'].make(self, self.page)
        self.schedulers['page_img_loader'].schedule(job)

    def on_page_loading_img(self, page, surface):
        if self.loading:
            self.canvas.remove_drawer(self.spinner)
            self.loading = False
        if not self.visible:
            return
        self.surface = surface
        self.canvas.redraw()
        if len(self.boxes['all']) <= 0:
            job = self.factories['page_boxes_loader'].make(self, self.page)
            self.schedulers['page_boxes_loader'].schedule(job)

    def _get_highlighted_boxes(self, sentence):
        """
        Get all the boxes corresponding the given sentence

        Arguments:
            sentence --- can be string (will be splited), or an array of
                strings
        Returns:
            an array of boxes (see pyocr boxes)
        """
        if isinstance(sentence, unicode):
            keywords = split_words(sentence)
        else:
            assert(isinstance(sentence, list))
            keywords = sentence

        output = set()
        for keyword in keywords:
            for box in self.boxes["all"]:
                if keyword in box.content:
                    output.add(box)
                    continue
                # unfold generator output
                words = [x for x in split_words(box.content)]
                if keyword in words:
                    output.add(box)
                    continue
        return output

    def reload_boxes(self, new_sentence=None):
        if new_sentence:
            self.sentence = new_sentence
        self.boxes["highlighted"] = \
                self._get_highlighted_boxes(self.sentence)
        self.canvas.redraw()

    def on_page_loading_boxes(self, page, all_boxes):
        if not self.visible:
            return
        self.boxes['all'] = all_boxes
        self.reload_boxes()

    def unload_content(self):
        if self.loading:
            self.canvas.remove_drawer(self.spinner)
            self.loading = False
        if self.surface is not None:
            del(self.surface)
            self.surface = None
        self.boxes = {
            'all': [],
            'highlighted': [],
            'mouse_over': None,
        }

    def hide(self):
        self.unload_content()
        self.visible = False

    def draw_tmp_area(self, cairo_context, canvas_offset, canvas_visible_size):
        cairo_context.save()
        try:
            cairo_context.set_source_rgb(0.85, 0.85, 0.85)
            cairo_context.rectangle(self.position[0] - canvas_offset[0],
                                    self.position[1] - canvas_offset[1],
                                    self.size[0], self.size[1])
            cairo_context.clip()
            cairo_context.paint()
        finally:
            cairo_context.restore()

    def _get_factors(self):
        return (
            (float(self._size[0]) / self.max_size[0]),
            (float(self._size[1]) / self.max_size[1]),
        )

    def _get_real_box(self, box, canvas_offset):
        (x_factor, y_factor) = self._get_factors()

        ((a, b), (c, d)) = box.position
        (w, h) = (c - a, d - b)

        a *= x_factor
        b *= y_factor
        w *= x_factor
        h *= y_factor

        a += self.position[0]
        b += self.position[1]
        a -= canvas_offset[0]
        b -= canvas_offset[1]

        return (int(a), int(b), int(w), int(h))

    def draw_boxes(self, cairo_context, canvas_offset, canvas_visible_size,
                   boxes, color):
        for box in boxes:
            (a, b, w, h) = self._get_real_box(box, canvas_offset)
            cairo_context.save()
            try:
                cairo_context.set_source_rgb(color[0], color[1], color[2])
                cairo_context.set_line_width(1.0)
                cairo_context.rectangle(a, b, w, h)
                cairo_context.stroke()
            finally:
                cairo_context.restore()

    def draw_box_txt(self, cairo_context, canvas_offset, canvas_visible_size,
                     box):
        (a, b, w, h) = self._get_real_box(box, canvas_offset)

        cairo_context.save()
        try:
            cairo_context.set_source_rgb(1.0, 1.0, 1.0)
            cairo_context.rectangle(a, b, w, h)
            cairo_context.clip()
            cairo_context.paint()
        finally:
            cairo_context.restore()

        cairo_context.save()
        try:
            cairo_context.translate(a, b)
            cairo_context.set_source_rgb(0.0, 0.0, 0.0)

            layout = PangoCairo.create_layout(cairo_context)
            layout.set_text(box.content, -1)

            txt_size = layout.get_size()
            txt_factor = min(
                float(w) * Pango.SCALE / txt_size[0],
                float(h) * Pango.SCALE / txt_size[1],
            )

            cairo_context.scale(txt_factor, txt_factor)

            PangoCairo.update_layout(cairo_context, layout)
            PangoCairo.show_layout(cairo_context, layout)
        finally:
            cairo_context.restore()

    def draw(self, cairo_context, canvas_offset, canvas_visible_size):
        should_be_visible = self.compute_visibility(
            canvas_offset, canvas_visible_size,
            self.position, self.size)
        if should_be_visible and not self.visible:
            self.load_content()
        elif not should_be_visible and self.visible:
            self.unload_content()
        self.visible = should_be_visible

        if not self.visible:
            return

        if not self.surface:
            self.draw_tmp_area(cairo_context, canvas_offset, canvas_visible_size)
        else:
            self.draw_surface(cairo_context, canvas_offset,
                              canvas_visible_size,
                              self.surface, self.position,
                              self.size)

        if self.show_all_boxes:
            self.draw_boxes(cairo_context, canvas_offset, canvas_visible_size,
                            self.boxes['all'], color=(0.0, 0.0, 0.5))
        if self.boxes["mouse_over"]:
            self.draw_boxes(cairo_context, canvas_offset, canvas_visible_size,
                            [self.boxes['mouse_over']], color=(0.0, 0.0, 1.0))
            self.draw_box_txt(cairo_context, canvas_offset, canvas_visible_size,
                              self.boxes['mouse_over'])
        self.draw_boxes(cairo_context, canvas_offset, canvas_visible_size,
                        self.boxes['highlighted'], color=(0.0, 0.85, 0.0))

    def _get_box_at(self, x, y):
        for box in self.boxes["all"]:
            if (x >= box.position[0][0]
                and x <= box.position[1][0]
                and y >= box.position[0][1]
                and y <= box.position[1][1]):
                return box
        return None

    def _on_mouse_motion(self, event):
        position = self.position
        size = self.size

        if (event.x < position[0]
            or event.x > (position[0] + size[0])
            or event.y < position[1]
            or event.y >= (position[1] + size[1])):
            return

        (x_factor, y_factor) = self._get_factors()
        # position on the whole page image
        (x, y) = (
            (event.x - position[0]) / x_factor,
            (event.y - position[1]) / y_factor,
        )

        box = self._get_box_at(x, y)
        if box != self.boxes["mouse_over"]:
            self.boxes["mouse_over"] = box
            self.canvas.redraw()

########NEW FILE########
__FILENAME__ = scan
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import logging
import multiprocessing
import re
import threading
import time

from gi.repository import GLib
from gi.repository import GObject
import pyocr
import pyocr.builders

from paperwork.backend.util import check_spelling
from paperwork.frontend.util.jobs import Job
from paperwork.frontend.util.jobs import JobFactory
from paperwork.frontend.util.canvas.animations import Animation
from paperwork.frontend.util.canvas.animations import ScanAnimation
from paperwork.frontend.util.canvas.animations import SpinnerAnimation
from paperwork.frontend.util.canvas.animators import LinearSimpleAnimator
from paperwork.frontend.util.canvas.animators import LinearCoordAnimator
from paperwork.frontend.util.canvas.drawers import fit
from paperwork.frontend.util.canvas.drawers import LineDrawer
from paperwork.frontend.util.canvas.drawers import PillowImageDrawer
from paperwork.frontend.util.canvas.drawers import RectangleDrawer
from paperwork.frontend.util.canvas.drawers import TargetAreaDrawer


logger = logging.getLogger(__name__)


class JobScan(Job):
    __gsignals__ = {
        'scan-started': (GObject.SignalFlags.RUN_LAST, None, ()),
        'scan-info': (GObject.SignalFlags.RUN_LAST, None,
                      (
                          # expected width
                          GObject.TYPE_INT,
                          # expected height
                          GObject.TYPE_INT,
                      )),
        'scan-chunk': (GObject.SignalFlags.RUN_LAST, None,
                       # line where to put the image
                       (GObject.TYPE_INT,
                        GObject.TYPE_PYOBJECT,)),  # The PIL image
        'scan-done': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_PYOBJECT,  # Pillow image
                      )),
        'scan-error': (GObject.SignalFlags.RUN_LAST, None,
                       (GObject.TYPE_PYOBJECT,  # Exception
                       )),
        'scan-canceled': (GObject.SignalFlags.RUN_LAST, None,
                          ()),
    }

    can_stop = True
    priority = 10

    def __init__(self, factory, id, scan_session):
        Job.__init__(self, factory, id)
        self.can_run = False
        self.scan_session = scan_session

    def do(self):
        self.can_run = True
        logger.info("Scan started")
        self.emit('scan-started')

        try:
            size = self.scan_session.scan.expected_size
            self.emit('scan-info', size[0], size[1])

            last_line = 0
            try:
                while self.can_run:
                    self.scan_session.scan.read()

                    next_line = self.scan_session.scan.available_lines[1]
                    if (next_line > last_line):
                        chunk = self.scan_session.scan.get_image(last_line, next_line)
                        self.emit('scan-chunk', last_line, chunk)
                        last_line = next_line

                    time.sleep(0)  # Give some CPU time to Gtk
                if not self.can_run:
                    logger.info("Scan canceled")
                    self.emit('scan-canceled')
                    return
            except EOFError:
                pass
        except Exception, exc:
            self.emit('scan-error', exc)
            raise

        img = self.scan_session.images[-1]
        self.emit('scan-done', img)
        logger.info("Scan done")

    def stop(self, will_resume=False):
        self.can_run = False
        self._stop_wait()
        if not will_resume:
            self.scan_session.scan.cancel()


GObject.type_register(JobScan)


class JobFactoryScan(JobFactory):
    def __init__(self, scan_workflow):
        JobFactory.__init__(self, "Scan")
        self.scan_workflow = scan_workflow

    def make(self, scan_session):
        job = JobScan(self, next(self.id_generator), scan_session)
        job.connect("scan-started",
                    lambda job: GLib.idle_add(self.scan_workflow.on_scan_start))
        job.connect("scan-info",
                    lambda job, x, y:
                    GLib.idle_add(self.scan_workflow.on_scan_info, x, y))
        job.connect("scan-chunk",
                    lambda job, line, img_chunk:
                    GLib.idle_add(self.scan_workflow.on_scan_chunk, line,
                                  img_chunk))
        job.connect("scan-done",
                    lambda job, img: GLib.idle_add(self.scan_workflow.on_scan_done,
                                                   img))
        job.connect("scan-error",
                    lambda job, exc:
                    GLib.idle_add(self.scan_workflow.on_scan_error, exc))
        job.connect("scan-canceled", lambda job:
                    GLib.idle_add(self.scan_workflow.on_scan_canceled))
        return job


class _ImgOCRThread(threading.Thread):
    # we don't use jobs here, because we would need 1 scheduler for each job
    # --> too painful and useless

    def __init__(self, name, ocr_tool, langs, angle, img):
        threading.Thread.__init__(self, name="OCR")
        self.name = name
        self.ocr_tool = ocr_tool
        self.langs = langs
        self.angle = angle
        self.img = img
        self.score = -1
        self.boxes = None

    def __compute_ocr_score_with_spell_checking(self, txt):
        return check_spelling(self.langs['spelling'], txt)

    @staticmethod
    def __boxes_to_txt(boxes):
        txt = u""
        for line in boxes:
            txt += line.content + u"\n"
        return txt

    @staticmethod
    def __compute_ocr_score_without_spell_checking(txt):
        """
        Try to evaluate how well the OCR worked.
        Current implementation:
            The score is the number of words only made of 4 or more letters
            ([a-zA-Z])
        """
        # TODO(Jflesch): i18n / l10n
        score = 0
        prog = re.compile(r'^[a-zA-Z]{4,}$')
        for word in txt.split(" "):
            if prog.match(word):
                score += 1
        return (txt, score)

    def run(self):
        SCORE_METHODS = [
            ("spell_checker", self.__compute_ocr_score_with_spell_checking),
            ("lucky_guess", self.__compute_ocr_score_without_spell_checking),
            ("no_score", lambda txt: (txt, 0))
        ]

        logger.info("Running OCR on page orientation %s" % self.name)
        self.boxes = self.ocr_tool.image_to_string(
            self.img, lang=self.langs['ocr'],
            builder=pyocr.builders.LineBoxBuilder())

        txt = self.__boxes_to_txt(self.boxes)

        for score_method in SCORE_METHODS:
            try:
                logger.info("Evaluating score of page orientation (%s)"
                             " using method '%s' ..."
                             % (self.name, score_method[0]))
                (_, self.score) = score_method[1](txt)
                # TODO(Jflesch): For now, we throw away the fixed version of the
                # text:
                # The original version may contain proper nouns, and spell
                # checking could make them disappear
                # However, it would be best if we could keep both versions
                # without increasing too much indexation time
                return
            except Exception, exc:
                logger.error("Scoring method '%s' on orientation %s failed !"
                             % (score_method[0], self.name))
                logger.error("Reason: %s" % exc)


class JobOCR(Job):
    __gsignals__ = {
        'ocr-started': (GObject.SignalFlags.RUN_LAST, None,
                        (GObject.TYPE_PYOBJECT,  # image to ocr
                        )),
        'ocr-angles': (GObject.SignalFlags.RUN_LAST, None,
                       # list of images to ocr: { angle: img }
                       (GObject.TYPE_PYOBJECT,
                       )),
        'ocr-score': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_INT,  # angle
                       GObject.TYPE_FLOAT,  # score
                      )),
        'ocr-done': (GObject.SignalFlags.RUN_LAST, None,
                     (GObject.TYPE_INT,   # angle
                      GObject.TYPE_PYOBJECT,  # image to ocr (rotated)
                      GObject.TYPE_PYOBJECT,  # line + word boxes
                     )),
    }

    can_stop = False
    priority = 5

    OCR_THREADS_POLLING_TIME = 0.1

    def __init__(self, factory, id,
                 ocr_tool, langs, angles, img):
        Job.__init__(self, factory, id)
        self.ocr_tool = ocr_tool
        self.langs = langs
        self.imgs = {angle: img.rotate(angle) for angle in angles}

    def do(self):
        self.emit('ocr-started', self.imgs[0])
        self.emit('ocr-angles', dict(self.imgs))

        max_threads = multiprocessing.cpu_count()
        threads = []
        scores = []

        if len(self.imgs) > 1:
            logger.debug("Will use %d process(es) for OCR" % (max_threads))

        # Run the OCR tools in as many threads as there are processors/core
        # on the computer
        nb = 0
        while (len(self.imgs) > 0 or len(threads) > 0):
            # look for finished threads
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)
                    logger.info("OCR done on angle %d: %f"
                                % (thread.angle, thread.score))
                    scores.append((thread.score, thread.angle,
                                   thread.img, thread.boxes))
                    self.emit('ocr-score', thread.angle, thread.score)
            # start new threads if required
            while (len(threads) < max_threads and len(self.imgs) > 0):
                (angle, img) = self.imgs.popitem()
                logger.info("Starting OCR on angle %d" % angle)
                thread = _ImgOCRThread(str(nb), self.ocr_tool,
                                       self.langs, angle, img)
                thread.start()
                threads.append(thread)
                nb += 1
            time.sleep(self.OCR_THREADS_POLLING_TIME)

        # We want the higher score first
        scores.sort(cmp=lambda x, y: cmp(y[0], x[0]))

        logger.info("Best: %f" % (scores[0][0]))

        self.emit('ocr-done', scores[0][1], scores[0][2], scores[0][3])


GObject.type_register(JobOCR)


class JobFactoryOCR(JobFactory):
    def __init__(self, scan_workflow, config):
        JobFactory.__init__(self, "OCR")
        self.__config = config
        self.scan_workflow = scan_workflow

    def make(self, img, nb_angles):
        angles = range(0, nb_angles * 90, 90)

        ocr_tools = pyocr.get_available_tools()
        if len(ocr_tools) == 0:
            print("No OCR tool found")
            sys.exit(1)
        ocr_tool = ocr_tools[0]
        logger.info("Will use tool '%s'" % (ocr_tool.get_name()))

        job = JobOCR(self, next(self.id_generator), ocr_tool,
                     self.__config['langs'].value, angles, img)
        job.connect("ocr-started", lambda job, img:
                    GLib.idle_add(self.scan_workflow.on_ocr_started, img))
        job.connect("ocr-angles", lambda job, imgs:
                    GLib.idle_add(self.scan_workflow.on_ocr_angles, imgs))
        job.connect("ocr-score", lambda job, angle, score:
                    GLib.idle_add(self.scan_workflow.on_ocr_score, angle, score))
        job.connect("ocr-done", lambda job, angle, img, boxes:
                    GLib.idle_add(self.scan_workflow.on_ocr_done, angle, img,
                                  boxes))
        return job


class BasicScanWorkflowDrawer(Animation):
    GLOBAL_MARGIN = 10
    SCAN_TO_OCR_ANIM_TIME = 1000  # ms
    IMG_MARGIN = 20

    layer = Animation.IMG_LAYER

    def __init__(self, scan_workflow):
        Animation.__init__(self)

        self.scan_drawers = []

        self.ocr_drawers = {}  # angle --> [drawers]

        self.animators = []
        self._position = (0, 0)

        self.scan_workflow = scan_workflow

        self.__used_angles = None  # == any

        # we are used as a page drawer, but our page is being built
        # --> no actual page
        self.page = None
        self.rotation_done = False

        scan_workflow.connect("scan-start",
                              lambda gobj:
                              GLib.idle_add(self.__on_scan_started_cb))
        scan_workflow.connect("scan-info", lambda gobj, img_x, img_y:
                              GLib.idle_add(self.__on_scan_info_cb,
                                            img_x, img_y))
        scan_workflow.connect("scan-chunk", lambda gobj, line, chunk:
                              GLib.idle_add(self.__on_scan_chunk_cb, line, chunk))
        scan_workflow.connect("scan-done", lambda gobj, img:
                              GLib.idle_add(self.__on_scan_done_cb, img))
        scan_workflow.connect("ocr-start", lambda gobj, img:
                              GLib.idle_add(self.__on_ocr_started_cb, img))
        scan_workflow.connect("ocr-angles", lambda gobj, imgs:
                              GLib.idle_add(self.__on_ocr_angles_cb, imgs))
        scan_workflow.connect("ocr-score", lambda gobj, angle, score:
                              GLib.idle_add(self.__on_ocr_score_cb, angle, score))
        scan_workflow.connect("ocr-done", lambda gobj, angle, img, boxes:
                              GLib.idle_add(self.__on_ocr_done_cb, angle, img,
                                            boxes))

    def __get_size(self):
        assert(self.canvas)
        return (
            self.canvas.visible_size[0],
            self.canvas.visible_size[1],
        )

    size = property(__get_size)
    max_size = property(__get_size)

    def __get_position(self):
        return self._position

    def __set_position(self, position):
        self._position = position
        for drawer in self.scan_drawers:
            drawer.position = (
                position[0] + (self.canvas.visible_size[0] / 2)
                - (drawer.size[0] / 2),
                position[1],
            )

    position = property(__get_position, __set_position)

    def set_size_ratio(self, ratio):
        # we are used as a page drawer, but we don't care about the scale/ratio
        return

    def do_draw(self, cairo_ctx, offset, size):
        for drawer in self.scan_drawers:
            drawer.draw(cairo_ctx, offset, size)
        for drawers in self.ocr_drawers.values():
            for drawer in drawers:
                drawer.draw(cairo_ctx, offset, size)

    def on_tick(self):
        for drawer in self.scan_drawers:
            drawer.on_tick()
        for animator in self.animators:
            animator.on_tick()

    def __on_scan_started_cb(self):
        pass

    def __on_scan_info_cb(self, x, y):
        size = fit((x, y), self.canvas.visible_size)
        position = (
            self.position[0] + (self.canvas.visible_size[0] / 2)
            - (size[0] / 2),
            self.position[1],
        )

        scan_drawer = ScanAnimation(position, (x, y),
                                    self.canvas.visible_size)
        scan_drawer.set_canvas(self.canvas)
        ratio = scan_drawer.ratio

        self.scan_drawers = [scan_drawer]

        calibration = self.scan_workflow.calibration
        if calibration:
            calibration_drawer = TargetAreaDrawer(
                position, size,
                (
                    int(position[0] + (ratio * calibration[0][0])),
                    int(position[1] + (ratio * calibration[0][1])),
                ),
                (
                    int(ratio * (calibration[1][0] - calibration[0][0])),
                    int(ratio * (calibration[1][1] - calibration[0][1])),
                ),
            )
            calibration_drawer.set_canvas(self.canvas)

            self.scan_drawers.append(calibration_drawer)

        self.canvas.redraw()

    def __on_scan_chunk_cb(self, line, img_chunk):
        assert(len(self.scan_drawers) > 0)
        self.scan_drawers[0].add_chunk(line, img_chunk)

    def __on_scan_done_cb(self, img):
        if img is None:
            self.__on_scan_canceled()
            return
        pass

    def __on_scan_error_cb(self, error):
        self.scan_drawers = []

    def __on_scan_canceled_cb(self):
        self.scan_drawers = []

    def __on_ocr_started_cb(self, img):
        assert(self.canvas)

        if len(self.scan_drawers) > 0:
            if hasattr(self.scan_drawers[-1], 'target_size'):
                size = self.scan_drawers[-1].target_size
                position = self.scan_drawers[-1].target_position
            else:
                size = self.scan_drawers[-1].size
                position = self.scan_drawers[-1].position
            self.scan_drawers = []
        else:
            size = fit(img.size, self.canvas.visible_size)
            position = self.position

        # animations with big images are too slow
        # --> reduce the image size
        img = img.resize(size)

        target_sizes = self._compute_reduced_sizes(
            self.canvas.visible_size, size)
        target_positions = self._compute_reduced_positions(
            self.canvas.visible_size, size, target_sizes)

        self.ocr_drawers = {}

        for angle in target_positions.keys():
            self.ocr_drawers[angle] = [PillowImageDrawer(position, img)]

        self.animators = []
        for (angle, drawers) in self.ocr_drawers.iteritems():
            drawer = drawers[0]
            drawer.size = size
            logger.info("Animator: Angle %d: %s %s -> %s %s"
                        % (angle,
                           str(drawer.position), str(drawer.size),
                           str(target_positions[angle]),
                           str(target_sizes)))

            # reduce the rotation to its minimum
            anim_angle = angle % 360
            if (anim_angle > 180):
                anim_angle = -1 * (360 - anim_angle)

            new_animators = [
                LinearCoordAnimator(
                    drawer, target_positions[angle],
                    self.SCAN_TO_OCR_ANIM_TIME,
                    attr_name='position', canvas=self.canvas),
                LinearCoordAnimator(
                    drawer, target_sizes,
                    self.SCAN_TO_OCR_ANIM_TIME,
                    attr_name='size', canvas=self.canvas),
                LinearSimpleAnimator(
                    drawer, anim_angle,
                    self.SCAN_TO_OCR_ANIM_TIME,
                    attr_name='angle', canvas=self.canvas),
            ]
            # all the animators last the same length of time
            # so any of them is good enough for this signal
            new_animators[0].connect(
                'animator-end', lambda animator:
                GLib.idle_add(self.__on_ocr_rotation_anim_done_cb))
            self.animators += new_animators

    def _disable_angle(self, angle):
        img_drawer = self.ocr_drawers[angle][0]
        # cross out the image
        line_drawer = LineDrawer(
            (
                img_drawer.position[0],
                img_drawer.position[1] + img_drawer.size[1]
            ),
            (
                img_drawer.position[0] + img_drawer.size[0],
                img_drawer.position[1]
            ),
            width=5.0
        )
        self.ocr_drawers[angle] = [
            img_drawer,
            line_drawer,
        ]

    def __on_ocr_angles_cb(self, imgs):
        # disable all the angles not evaluated
        self.__used_angles = imgs.keys()
        if self.rotation_done:
            for angle in self.ocr_drawers.keys()[:]:
                if angle not in self.__used_angles:
                    self._disable_angle(angle)

    def __on_ocr_rotation_anim_done_cb(self):
        self.rotation_done = True
        for angle in self.ocr_drawers.keys()[:]:
            if self.__used_angles and angle not in self.__used_angles:
                self._disable_angle(angle)
            else:
                img_drawer = self.ocr_drawers[angle][0]
                spinner_bg = RectangleDrawer(
                    img_drawer.position, img_drawer.size,
                    inside_color=(0.0, 0.0, 0.0, 0.1),
                    angle=angle,
                )
                spinner = SpinnerAnimation(
                    (
                        (img_drawer.position[0] + (img_drawer.size[0] / 2))
                        - (SpinnerAnimation.ICON_SIZE / 2),
                        (img_drawer.position[1] + (img_drawer.size[1] / 2))
                        - (SpinnerAnimation.ICON_SIZE / 2)
                    )
                )
                self.ocr_drawers[angle] = [img_drawer, spinner_bg, spinner]
                self.animators.append(spinner)

    def __on_ocr_score_cb(self, angle, score):
        if angle in self.ocr_drawers:
            self.ocr_drawers[angle] = self.ocr_drawers[angle][:1]
        # TODO(Jflesch): show score

    def __on_ocr_done_cb(self, angle, img, boxes):
        self.animators = []

        drawers = self.ocr_drawers[angle]
        drawer = drawers[0]

        # we got out winner. Shoot the others
        self.ocr_drawers = {
            angle: [drawer]
        }

        new_size = fit(drawer.img_size, self.canvas.visible_size)
        new_position = (
            (self.position[0] + (self.canvas.visible_size[0] / 2)
             - (new_size[0] / 2)),
            (self.position[1]),
        )

        self.animators += [
            LinearCoordAnimator(
                drawer, new_position,
                self.SCAN_TO_OCR_ANIM_TIME,
                attr_name='position', canvas=self.canvas),
            LinearCoordAnimator(
                drawer, new_size,
                self.SCAN_TO_OCR_ANIM_TIME,
                attr_name='size', canvas=self.canvas),
        ]
        self.animators[-1].connect('animator-end', lambda animator:
                                   GLib.idle_add(self.scan_workflow.on_ocr_anim_done,
                                                 angle, img, boxes))


class SingleAngleScanWorkflowDrawer(BasicScanWorkflowDrawer):
    def __init__(self, workflow):
        BasicScanWorkflowDrawer.__init__(self, workflow)

    def _compute_reduced_sizes(self, visible_area, img_size):
        ratio = min(
            1.0,
            float(visible_area[0]) / float(img_size[0]),
            float(visible_area[1]) / float(img_size[1]),
            float(visible_area[0]) / float(img_size[1]),
            float(visible_area[1]) / float(img_size[0]),
        )
        return (
            int(ratio * img_size[0]) - (self.IMG_MARGIN),
            int(ratio * img_size[1]) - (self.IMG_MARGIN),
        )

    def _compute_reduced_positions(self, visible_area, img_size,
                                    target_img_sizes):
        target_positions = {
            # center positions
            0: (visible_area[0] / 2,
                self.position[1] + (visible_area[1] / 2)),
        }

        for key in target_positions.keys()[:]:
            # image position
            target_positions[key] = (
                target_positions[key][0] - (target_img_sizes[0] / 2),
                target_positions[key][1] - (target_img_sizes[1] / 2),
            )

        return target_positions


class MultiAnglesScanWorkflowDrawer(BasicScanWorkflowDrawer):
    def __init__(self, workflow):
        BasicScanWorkflowDrawer.__init__(self, workflow)

    def _compute_reduced_sizes(self, visible_area, img_size):
        visible_area = (
            visible_area[0] / 2,
            visible_area[1] / 2,
        )
        ratio = min(
            1.0,
            float(visible_area[0]) / float(img_size[0]),
            float(visible_area[1]) / float(img_size[1]),
            float(visible_area[0]) / float(img_size[1]),
            float(visible_area[1]) / float(img_size[0]),
        )
        return (
            int(ratio * img_size[0]) - (2 * self.IMG_MARGIN),
            int(ratio * img_size[1]) - (2 * self.IMG_MARGIN),
        )

    def _compute_reduced_positions(self, visible_area, img_size,
                                    target_img_sizes):
        target_positions = {
            # center positions
            0: (visible_area[0] / 4,
                self.position[1] + (visible_area[1] / 4)),
            90: (visible_area[0] * 3 / 4,
                 self.position[1] + (visible_area[1] / 4)),
            180: (visible_area[0] / 4,
                  self.position[1] + (visible_area[1] * 3 / 4)),
            270: (visible_area[0] * 3 / 4,
                  self.position[1] + (visible_area[1] * 3 / 4)),
        }

        for key in target_positions.keys()[:]:
            # image position
            target_positions[key] = (
                target_positions[key][0] - (target_img_sizes[0] / 2),
                target_positions[key][1] - (target_img_sizes[1] / 2),
            )

        return target_positions


class ScanWorkflow(GObject.GObject):
    __gsignals__ = {
        'scan-start': (GObject.SignalFlags.RUN_LAST, None, ()),
        'scan-info': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_INT,
                       GObject.TYPE_INT,
                      )),
        'scan-chunk': (GObject.SignalFlags.RUN_LAST, None,
                       (GObject.TYPE_INT,  # line
                        GObject.TYPE_PYOBJECT,  # img chunk
                       )),
        'scan-done': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_PYOBJECT,  # PIL image
                      )),
        'scan-canceled': (GObject.SignalFlags.RUN_LAST, None,
                          ()),
        'scan-error': (GObject.SignalFlags.RUN_LAST, None,
                       (GObject.TYPE_PYOBJECT,  # Exception
                       )),
        'ocr-start': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_PYOBJECT,  # PIL image
                      )),
        'ocr-angles': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_PYOBJECT,  # array of PIL image
                      )),
        'ocr-score': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_INT,  # angle
                       GObject.TYPE_INT,  # score
                      )),
        'ocr-done': (GObject.SignalFlags.RUN_LAST, None,
                     (GObject.TYPE_INT,  # angle
                      GObject.TYPE_PYOBJECT,  # PIL image
                      GObject.TYPE_PYOBJECT,  # line + word boxes
                     )),
        'ocr-canceled': (GObject.SignalFlags.RUN_LAST, None,
                         ()),
        'process-done': (GObject.SignalFlags.RUN_LAST, None,
                         (GObject.TYPE_PYOBJECT,  # PIL image
                          GObject.TYPE_PYOBJECT,  # line + word boxes
                         )),
    }

    STEP_SCAN = 0
    STEP_OCR = 1

    def __init__(self, config, scan_scheduler, ocr_scheduler):
        GObject.GObject.__init__(self)
        self.__config = config
        self.schedulers = {
            'scan': scan_scheduler,
            'ocr': ocr_scheduler,
        }

        self.current_step = -1

        self.factories = {
            'scan': JobFactoryScan(self),
            'ocr': JobFactoryOCR(self, config),
        }
        self.__resolution = -1
        self.calibration = None

    def scan(self, resolution, scan_session):
        """
        Returns immediately
        Listen for the signal scan-done to get the result
        """
        self.__resolution = resolution

        calibration = self.__config['scanner_calibration'].value
        if calibration:
            (calib_resolution, calibration) = calibration

            self.calibration = (
                (calibration[0][0] * resolution / calib_resolution,
                 calibration[0][1] * resolution / calib_resolution),
                (calibration[1][0] * resolution / calib_resolution,
                 calibration[1][1] * resolution / calib_resolution),
            )

        job = self.factories['scan'].make(scan_session)
        self.schedulers['scan'].schedule(job)
        return job

    def on_scan_start(self):
        self.emit('scan-start')

    def on_scan_info(self, img_x, img_y):
        self.emit("scan-info", img_x, img_y)

    def on_scan_chunk(self, line, img_chunk):
        self.emit("scan-chunk", line, img_chunk)

    def on_scan_done(self, img):
        if self.calibration:
            img = img.crop(
                (
                    self.calibration[0][0],
                    self.calibration[0][1],
                    self.calibration[1][0],
                    self.calibration[1][1]
                )
            )

        self.emit('scan-done', img)

    def on_scan_error(self, exc):
        self.emit('scan-error', exc)

    def on_scan_canceled(self):
        self.emit('scan-done', None)

    def ocr(self, img, angles=None):
        """
        Returns immediately.
        Listen for the signal ocr-done to get the result
        """
        if angles is None:
            angles = self.__config['ocr_nb_angles'].value
        img.load()
        job = self.factories['ocr'].make(img, angles)
        self.schedulers['ocr'].schedule(job)
        return job

    def on_ocr_started(self, img):
        self.emit('ocr-start', img)

    def on_ocr_angles(self, imgs):
        self.emit("ocr-angles", imgs)

    def on_ocr_score(self, angle, score):
        self.emit("ocr-score", angle, score)

    def on_ocr_done(self, angle, img, boxes):
        self.emit("ocr-done", angle, img, boxes)

    def on_ocr_anim_done(self, angle, img, boxes):
        self.emit('process-done', img, boxes)

    def scan_and_ocr(self, resolution, scan_session):
        """
        Convenience function.
        Returns immediately.
        """
        class _ScanOcrChainer(object):
            def __init__(self, scan_workflow):
                scan_workflow.connect("scan-done", self.__start_ocr)

            def __start_ocr(self, scan_workflow, img):
                if img is None:
                    return
                scan_workflow.ocr(img)

        _ScanOcrChainer(self)
        self.scan(resolution, scan_session)


GObject.type_register(ScanWorkflow)

########NEW FILE########
__FILENAME__ = scan
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GLib
from gi.repository import GObject

from paperwork.frontend.util.canvas.animations import Animation
from paperwork.frontend.util.canvas.animations import ScanAnimation
from paperwork.frontend.util.canvas.animations import SpinnerAnimation
from paperwork.frontend.util.canvas.drawers import Drawer
from paperwork.frontend.util.canvas.drawers import RectangleDrawer
from paperwork.frontend.util.canvas.drawers import PillowImageDrawer
from paperwork.frontend.util.canvas.drawers import fit

class DocScan(object):
    def __init__(self, doc):
        """
        Arguments:
            doc --- if None, new doc
        """
        self.doc = doc


class PageScan(GObject.GObject):
    __gsignals__ = {
        'scanworkflow-inst': (GObject.SignalFlags.RUN_LAST, None,
                              (GObject.TYPE_PYOBJECT, )),
        'done': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self,
                 main_win, multiscan_win, config,
                 resolution, scan_session,
                 line_idx, doc_scan,
                 page_nb, total_pages):
        GObject.GObject.__init__(self)
        self.__main_win = main_win
        self.__multiscan_win = multiscan_win
        self.__config = config
        self.resolution = resolution
        self.__scan_session = scan_session
        self.line_idx = line_idx
        self.doc_scan = doc_scan
        self.page_nb = page_nb
        self.total_pages = total_pages

    def __on_ocr_done(self, img, line_boxes):
        docid = self.__main_win.remove_scan_workflow(self.scan_workflow)
        self.__main_win.add_page(docid, img, line_boxes)
        self.emit("done")

    def __on_error(self, exc):
        logger.error("Scan failed: %s" % str(exc))
        self.__main_win.remove_scan_workflow(self.scan_workflow)
        self.__main_win.refresh_page_list()
        self.__multiscan_win.on_scan_error_cb(self, exc)

    def __make_scan_workflow(self):
        self.scan_workflow = self.__main_win.make_scan_workflow()
        self.scan_workflow.connect("scan-start", lambda _: GLib.idle_add(
            self.__multiscan_win.on_scan_start_cb, self))
        self.scan_workflow.connect("scan-error", lambda _, exc:
                                   GLib.idle_add(self.__on_error, exc))
        self.scan_workflow.connect("ocr-start", lambda _, a: GLib.idle_add(
            self.__multiscan_win.on_ocr_start_cb, self))
        self.scan_workflow.connect("process-done",
                                   lambda _, a, b: GLib.idle_add(
                                       self.__multiscan_win.on_scan_done_cb,
                                       self))
        self.scan_workflow.connect("process-done",
                                   lambda scan_workflow, img, boxes:
                                   GLib.idle_add(self.__on_ocr_done,
                                                 img, boxes))
        self.emit('scanworkflow-inst', self.scan_workflow)

    def start_scan_workflow(self):
        self.__make_scan_workflow()
        if not self.doc_scan.doc:
            self.doc_scan.doc = self.__main_win.get_new_doc()
        self.__main_win.show_doc(self.doc_scan.doc)
        drawer = self.__main_win.make_scan_workflow_drawer(
            self.scan_workflow, single_angle=False)
        self.__main_win.add_scan_workflow(self.doc_scan.doc, drawer)
        self.scan_workflow.scan_and_ocr(self.resolution, self.__scan_session)

    def connect_next_page_scan(self, next_page_scan):
        self.connect("done", lambda _: GLib.idle_add(
            next_page_scan.start_scan_workflow))


GObject.type_register(PageScan)


class PageScanDrawer(Animation):
    layer = Drawer.IMG_LAYER
    visible = True

    DEFAULT_SIZE = (70, 100)

    def __init__(self, position):
        Animation.__init__(self)
        self.position = position
        self.scan_animation = None
        self.size = self.DEFAULT_SIZE
        self.drawers = [
            RectangleDrawer(self.position, self.size,
                            inside_color=ScanAnimation.BACKGROUND_COLOR),
        ]

    def set_canvas(self, canvas):
        Animation.set_canvas(self, canvas)
        assert(self.canvas)
        for drawer in self.drawers:
            drawer.set_canvas(canvas)

    def set_scan_workflow(self, page_scan, scan_workflow):
        GLib.idle_add(self.__set_scan_workflow, scan_workflow)

    def __set_scan_workflow(self, scan_workflow):
        scan_workflow.connect("scan-info", lambda _, x, y:
                              GLib.idle_add(self.__on_scan_info, (x, y)))
        scan_workflow.connect("scan-chunk", lambda _, line, chunk:
                              GLib.idle_add(self.__on_scan_chunk, line, chunk))
        scan_workflow.connect("scan-done", lambda _, img:
                              GLib.idle_add(self.__on_scan_done, img))
        scan_workflow.connect("process-done", lambda _, img, boxes:
                              GLib.idle_add(self.__on_process_done, img))

    def on_tick(self):
        for drawer in self.drawers:
            drawer.on_tick()

    def do_draw(self, cairo_ctx, offset, visible_size):
        for drawer in self.drawers:
            drawer.draw(cairo_ctx, offset, visible_size)

    def __on_scan_info(self, size):
        self.scan_animation = ScanAnimation(self.position, size, self.size)
        self.drawers = [
            RectangleDrawer(self.position, self.size,
                            inside_color=ScanAnimation.BACKGROUND_COLOR),
            self.scan_animation,
        ]
        assert(self.canvas)
        self.set_canvas(self.canvas)  # reset canvas on all new drawers
        self.canvas.redraw()

    def __on_scan_chunk(self, line, img):
        assert(self.canvas)
        self.scan_animation.add_chunk(line, img)
        self.canvas.redraw()

    def __on_scan_done(self, img):
        size = fit(img.size, self.size)
        img = img.resize(size)
        self.scan_animation = None
        self.drawers = [
            RectangleDrawer(self.position, self.size,
                            inside_color=ScanAnimation.BACKGROUND_COLOR),
            PillowImageDrawer(self.position, img),
            SpinnerAnimation(((self.position[0] + (self.size[0] / 2) -
                               SpinnerAnimation.ICON_SIZE / 2),
                              (self.position[1] + (self.size[1] / 2) -
                               SpinnerAnimation.ICON_SIZE / 2))),
        ]
        self.set_canvas(self.canvas)  # reset canvas on all new drawers
        self.canvas.redraw()

    def __on_process_done(self, img):
        size = fit(img.size, self.size)
        img = img.resize(size)
        self.drawers = [
            RectangleDrawer(self.position, self.size,
                            inside_color=ScanAnimation.BACKGROUND_COLOR),
            PillowImageDrawer(self.position, img)
        ]
        self.set_canvas(self.canvas)  # reset canvas on all new drawers
        self.canvas.redraw()

########NEW FILE########
__FILENAME__ = actions
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import logging

from gi.repository import Gio
from gi.repository import Gtk

logger = logging.getLogger(__name__)


class SimpleAction(object):
    """
    Template for all the actions started by buttons
    """
    def __init__(self, name):
        self.name = name
        self.__signal_handlers = [
            (Gtk.ToolButton, "clicked", self.on_button_clicked_cb, -1),
            (Gtk.Button, "clicked", self.on_button_clicked_cb, -1),
            (Gtk.MenuItem, "activate", self.on_menuitem_activate_cb, -1),
            (Gtk.Editable, "changed", self.on_entry_changed_cb, -1),
            (Gtk.Editable, "activate", self.on_entry_activate_cb, -1),
            (Gtk.Entry, "icon-press", self.on_icon_press_cb, -1),
            (Gtk.TreeView, "cursor-changed",
             self.on_treeview_cursor_changed_cb, -1),
            (Gtk.IconView, "selection-changed",
             self.on_iconview_selection_changed_cb, -1),
            (Gtk.ComboBox, "changed", self.on_combobox_changed_cb, -1),
            (Gtk.CellRenderer, "edited", self.on_cell_edited_cb, -1),
            (Gtk.Range, "value-changed", self.on_value_changed_cb, -1),
            (Gio.Action, "activate", self.on_action_activated_cb, -1),
        ]
        self.enabled = True

    def do(self, **kwargs):
        logger.info("Action: [%s]" % (self.name))

    def __do(self, **kwargs):
        if not self.enabled:
            return
        return self.do(**kwargs)

    def on_button_clicked_cb(self, toolbutton):
        return self.__do()

    def on_menuitem_activate_cb(self, menuitem):
        return self.__do()

    def on_entry_changed_cb(self, entry):
        return self.__do()

    def on_entry_activate_cb(self, entry):
        return self.__do()

    def on_treeview_cursor_changed_cb(self, treeview):
        return self.__do()

    def on_iconview_selection_changed_cb(self, iconview):
        return self.__do()

    def on_combobox_changed_cb(self, combobox):
        return self.__do()

    def on_cell_edited_cb(self, cellrenderer, path, new_text):
        return self.__do(new_text=new_text)

    def on_icon_press_cb(self, entry=None, iconpos=None, event=None):
        return self.__do()

    def on_value_changed_cb(self, widget_range=None):
        return self.__do()

    def on_action_activated_cb(self, action, parameter):
        return self.__do()

    def connect(self, buttons):
        for button in buttons:
            assert(button is not None)
            handled = False
            for handler_idx in range(0, len(self.__signal_handlers)):
                (obj_class, signal, handler, handler_id) = \
                    self.__signal_handlers[handler_idx]
                if isinstance(button, obj_class):
                    handler_id = button.connect(signal, handler)
                    handled = True
                self.__signal_handlers[handler_idx] = \
                    (obj_class, signal, handler, handler_id)
            assert(handled)

########NEW FILE########
__FILENAME__ = animations
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import math

import cairo

from gi.repository import Gdk
from gi.repository import Gtk

from paperwork.backend.util import image2surface
from paperwork.frontend.util.canvas import Canvas
from paperwork.frontend.util.canvas.drawers import Drawer
from paperwork.frontend.util.canvas.drawers import fit


class Animation(Drawer):
    def __init__(self):
        Drawer.__init__(self)
        self.ticks_enabled = False

    def show(self):
        Drawer.show(self)
        if not self.ticks_enabled:
            self.ticks_enabled = True
            self.canvas.start_ticks()

    def hide(self):
        Drawer.hide(self)
        if self.ticks_enabled:
            self.ticks_enabled = False
            self.canvas.stop_ticks()


class ScanAnimation(Animation):
    layer = Drawer.IMG_LAYER

    visible = True

    BACKGROUND_COLOR = (1.0, 1.0, 1.0)

    ANIM_LENGTH = 1000  # mseconds
    ANIM_HEIGHT = 5

    def __init__(self, position, scan_size, visible_size):
        Animation.__init__(self)
        self.ratio = min(
            float(visible_size[0]) / float(scan_size[0]),
            float(visible_size[1]) / float(scan_size[1]),
        )
        self.size = (
            int(self.ratio * scan_size[0]),
            int(self.ratio * scan_size[1]),
        )
        self.position = position
        self.surfaces = []

        self.anim = {
            "position": 0,
            "offset": (float(self.size[1])
                       / (self.ANIM_LENGTH
                          / Canvas.TICK_INTERVAL)),
        }

    def on_tick(self):
        self.anim['position'] += self.anim['offset']
        if self.anim['position'] < 0 or self.anim['position'] >= self.size[0]:
            self.anim['position'] = max(0, self.anim['position'])
            self.anim['position'] = min(self.size[0], self.anim['position'])
            self.anim['offset'] *= -1

    def add_chunk(self, line, img_chunk):
        # big images take more time to draw
        # --> we resize it now
        img_size = fit(img_chunk.size, self.size)
        if (img_size[0] <= 0 or img_size[1] <= 0):
            return
        img_chunk = img_chunk.resize(img_size)

        surface = image2surface(img_chunk)
        self.surfaces.append((line * self.ratio, surface))
        self.canvas.redraw()

    def draw_chunks(self, cairo_ctx, canvas_offset, canvas_size):
        position = (
            self.position[0] - canvas_offset[0],
            self.position[1] - canvas_offset[1],
        )

        cairo_ctx.save()
        try:
            cairo_ctx.set_source_rgb(self.BACKGROUND_COLOR[0],
                                     self.BACKGROUND_COLOR[1],
                                     self.BACKGROUND_COLOR[2])
            cairo_ctx.rectangle(position[0], position[1],
                                self.size[0], self.size[1])
            cairo_ctx.clip()
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()

        for (line, surface) in self.surfaces:
            chunk_size = (surface.get_width(), surface.get_height())
            self.draw_surface(cairo_ctx, canvas_offset, canvas_size,
                              surface, (float(self.position[0]),
                                        float(self.position[1]) + line),
                              chunk_size)

    def draw_animation(self, cairo_ctx, canvas_offset, canvas_size):
        if len(self.surfaces) <= 0:
            return

        position = (
            self.position[0] - canvas_offset[0],
            (
                self.position[1] - canvas_offset[1]
                + (self.surfaces[-1][0])
                + (self.surfaces[-1][1].get_height())
            ),
        )

        cairo_ctx.save()
        try:
            cairo_ctx.set_operator(cairo.OPERATOR_OVER)
            cairo_ctx.set_source_rgb(0.5, 0.0, 0.0)
            cairo_ctx.set_line_width(1.0)
            cairo_ctx.move_to(position[0], position[1])
            cairo_ctx.line_to(position[0] + self.size[0], position[1])
            cairo_ctx.stroke()

            cairo_ctx.set_source_rgb(1.0, 0.0, 0.0)
            cairo_ctx.arc(position[0] + self.anim['position'],
                          position[1],
                          float(self.ANIM_HEIGHT) / 2,
                          0.0, math.pi * 2)
            cairo_ctx.stroke()

        finally:
            cairo_ctx.restore()

    def do_draw(self, *args, **kwargs):
        self.draw_chunks(*args, **kwargs)
        self.draw_animation(*args, **kwargs)


class SpinnerAnimation(Animation):
    ICON_SIZE = 48

    layer = Drawer.PROGRESSION_INDICATOR_LAYER

    def __init__(self, position):
        Animation.__init__(self)
        self.visible = False
        self.position = position
        self.size = (self.ICON_SIZE, self.ICON_SIZE)

        icon_theme = Gtk.IconTheme.get_default()
        icon_info = icon_theme.lookup_icon("process-working", self.ICON_SIZE,
                                           Gtk.IconLookupFlags.NO_SVG)
        self.icon_pixbuf = icon_info.load_icon()
        self.frame = 1
        self.nb_frames = (
            (self.icon_pixbuf.get_width() / self.ICON_SIZE),
            (self.icon_pixbuf.get_height() / self.ICON_SIZE),
        )

    def on_tick(self):
        self.frame += 1
        self.frame %= (self.nb_frames[0] * self.nb_frames[1])
        if self.frame == 0:
            # XXX(Jflesch): skip the first frame:
            # in gnome-spinner.png, the first frame is empty.
            # don't know why.
            self.frame += 1

    def draw(self, cairo_ctx, canvas_offset, canvas_visible_size):
        frame = (
            (self.frame % self.nb_frames[0]),
            (self.frame / self.nb_frames[0]),
        )
        frame = (
            (frame[0] * self.ICON_SIZE),
            (frame[1] * self.ICON_SIZE),
        )

        img_offset = (max(0, canvas_offset[0] - self.position[0]),
                      max(0, canvas_offset[1] - self.position[1]))
        img_offset = (
            img_offset[0] + frame[0],
            img_offset[1] + frame[1],
        )
        target_offset = (max(0, self.position[0] - canvas_offset[0]),
                         max(0, self.position[1] - canvas_offset[1]))

        cairo_ctx.save()
        try:
            Gdk.cairo_set_source_pixbuf(cairo_ctx, self.icon_pixbuf,
                                        (target_offset[0] - img_offset[0]),
                                        (target_offset[1] - img_offset[1]),
                                       )
            cairo_ctx.rectangle(target_offset[0],
                                target_offset[1],
                                self.ICON_SIZE,
                                self.ICON_SIZE)
            cairo_ctx.clip()
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()

########NEW FILE########
__FILENAME__ = animators
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject

from paperwork.frontend.util.canvas import Canvas


class Animator(GObject.GObject):
    __gsignals__ = {
        'animator-start': (GObject.SignalFlags.RUN_LAST, None, ()),
        'animator-end': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self,
                 drawer,
                 attr_name, attr_values,  # one value per canvas tick
                 canvas=None):
        GObject.GObject.__init__(self)
        self.drawer = drawer
        self.attr_name = attr_name
        self.attr_values = attr_values
        self.canvas = canvas
        self.started = False
        self.stopped = False

    def set_canvas(self, canvas):
        self.canvas = canvas

    def on_tick(self):
        if len(self.attr_values) <= 0:
            if not self.stopped:
                self.stopped = True
                self.emit('animator-end')
            return
        if not self.started:
            self.started = True
            self.emit('animator-start')
        setattr(self.drawer, self.attr_name, self.attr_values[0])
        self.attr_values = self.attr_values[1:]


class LinearSimpleAnimator(Animator):
    def __init__(self, drawer,
                 target_value,
                 time_length,  # ms
                 attr_name='angle',
                 canvas=None):
        nb_values = int(time_length / Canvas.TICK_INTERVAL)
        assert(nb_values)
        value_intervals = (
            (target_value - getattr(drawer, attr_name)) / nb_values
        )
        values = [
            getattr(drawer, attr_name) + (i * value_intervals)
            for i in xrange(0, nb_values + 1)
        ]
        Animator.__init__(self, drawer, attr_name, values, canvas)


GObject.type_register(LinearSimpleAnimator)


class LinearCoordAnimator(Animator):
    def __init__(self, drawer,
                 target_coord,
                 time_length,  # ms
                 attr_name='position',
                 canvas=None):
        nb_coords = int(time_length / Canvas.TICK_INTERVAL)
        assert(nb_coords)
        pos_intervals = (
            (target_coord[0] - getattr(drawer, attr_name)[0]) / nb_coords,
            (target_coord[1] - getattr(drawer, attr_name)[1]) / nb_coords,
        )
        coords = [
            (getattr(drawer, attr_name)[0] + (i * pos_intervals[0]),
             getattr(drawer, attr_name)[1] + (i * pos_intervals[1]))
            for i in xrange(0, nb_coords + 1)
        ]
        Animator.__init__(self, drawer, attr_name, coords, canvas)


GObject.type_register(LinearCoordAnimator)

########NEW FILE########
__FILENAME__ = drawers
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import math
import logging

from gi.repository import Gdk
from gi.repository import Gtk

from paperwork.backend.util import image2surface
from paperwork.frontend.util.canvas import Canvas


logger = logging.getLogger(__name__)


class Drawer(object):
    # layer number == priority --> higher is drawn first (lower level)
    BACKGROUND_LAYER = 1000
    IMG_LAYER = 200
    BOX_LAYER = 50
    PROGRESSION_INDICATOR_LAYER = 25
    FADDING_EFFECT_LAYER = 0
    # layer number == priority --> lower is drawn last (higher level)

    layer = -1  # must be set by subclass

    position = (0, 0)  # (x, y)
    size = (0, 0)  # (width, height)

    def __init__(self):
        self.canvas = None

    def set_canvas(self, canvas):
        self.canvas = canvas

    @staticmethod
    def compute_visibility(offset, visible_area_size, position, size):
        should_be_visible = True
        if (position[0] + size[0] < offset[0]):
            should_be_visible = False
        elif (offset[0] + visible_area_size[0] < position[0]):
            should_be_visible = False
        elif (position[1] + size[1] < offset[1]):
            should_be_visible = False
        elif (offset[1] + visible_area_size[1] < position[1]):
            should_be_visible = False
        return should_be_visible

    @staticmethod
    def draw_surface(cairo_ctx, canvas_offset, canvas_size,
                     surface, img_position, img_size, angle=0):
        """
        Draw a surface

        Arguments:
            cairo_ctx --- cairo context to draw on
            canvas_offset --- position of the visible area of the canvas
            canvas_size --- size of the visible area of the canvas
            surface --- surface to draw on the context
            img_position --- target position for the surface once on the canvas
            img_size --- target size for the surface once on the canvas
            angle --- rotation to apply (WARNING: applied after positioning, and
                      rotated at the center of the surface !)
        """
        angle = math.pi * angle / 180
        surface_size = (surface.get_width(), surface.get_height())
        scaling = (
            (float(img_size[0]) / float(surface_size[0])),
            (float(img_size[1]) / float(surface_size[1])),
        )

        # some drawer call draw_surface() many times, so we save the
        # context here
        cairo_ctx.save()
        try:
            cairo_ctx.translate(img_position[0], img_position[1])
            cairo_ctx.translate(-canvas_offset[0], -canvas_offset[1])
            if angle != 0:
                cairo_ctx.translate(img_size[0] / 2, img_size[1] / 2)
                cairo_ctx.rotate(angle)
                cairo_ctx.translate(-img_size[0] / 2, -img_size[1] / 2)
            cairo_ctx.scale(scaling[0], scaling[1])

            cairo_ctx.set_source_surface(
                surface, 0, 0)
            cairo_ctx.rectangle(0, 0,
                                surface_size[0],
                                surface_size[1])
            cairo_ctx.clip()
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()


    def do_draw(self, cairo_ctx, offset, size):
        """
        Arguments:
            offset --- Position of the area in which to draw:
                       (offset_x, offset_y)
            size --- Size of the area in which to draw: (width, height) = size
        """
        assert()

    def on_tick(self):
        """
        Called every 1/27 second
        """
        pass

    def draw(self, cairo_ctx, offset, visible_size):
        # don't bother drawing if it's not visible
        if offset[0] + visible_size[0] < self.position[0]:
            return
        if offset[1] + visible_size[1] < self.position[1]:
            return
        if self.position[0] + self.size[0] < offset[0]:
            return
        if self.position[1] + self.size[1] < offset[1]:
            return
        self.do_draw(cairo_ctx, offset, visible_size)

    def show(self):
        pass

    def hide(self):
        pass


class BackgroundDrawer(Drawer):
    layer = Drawer.BACKGROUND_LAYER

    def __init__(self, rgb):
        Drawer.__init__(self)
        self.rgb = rgb
        self.position = (0, 0)

    def __get_size(self):
        assert(self.canvas is not None)
        return (self.canvas.full_size[0], self.canvas.full_size[1])

    size = property(__get_size)

    def do_draw(self, cairo_ctx, offset, size):
        cairo_ctx.set_source_rgb(self.rgb[0], self.rgb[1], self.rgb[2])
        cairo_ctx.rectangle(0, 0, size[0], size[1])
        cairo_ctx.clip()
        cairo_ctx.paint()


class RectangleDrawer(Drawer):
    layer = Drawer.BOX_LAYER
    visible = True

    def __init__(self,
                 position, size,
                 inside_color=(0.0, 0.0, 1.0, 1.0),
                 angle=0):
        Drawer.__init__(self)
        self.position = position
        self.size = size
        self.inside_color = inside_color
        self.angle = angle

    def do_draw(self, cairo_ctx, canvas_offset, canvas_visible_size):
        cairo_ctx.save()
        try:
            if (len(self.inside_color) > 3):
                cairo_ctx.set_source_rgba(self.inside_color[0], self.inside_color[1],
                                          self.inside_color[2], self.inside_color[3])
            else:
                cairo_ctx.set_source_rgb(self.inside_color[0], self.inside_color[1],
                                         self.inside_color[2])
            cairo_ctx.set_line_width(2.0)

            if self.angle != 0:
                angle = math.pi * self.angle / 180
                cairo_ctx.translate(self.position[0] - canvas_offset[0]
                                    + (self.size[0] / 2),
                                    self.position[1] - canvas_offset[1]
                                    + (self.size[1] / 2))
                cairo_ctx.rotate(angle)
                cairo_ctx.translate(-self.position[0] + canvas_offset[0]
                                    - (self.size[0] / 2),
                                    -self.position[1] + canvas_offset[1]
                                    - (self.size[1] / 2))

            cairo_ctx.rectangle(
                self.position[0] - canvas_offset[0],
                self.position[1] - canvas_offset[1],
                self.size[0], self.size[1]
            )
            cairo_ctx.clip()
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()


class LineDrawer(Drawer):
    layer = Drawer.BOX_LAYER
    visible = True

    def __init__(self,
                 start_point, end_point,
                 width=1.0,
                 color=(0.0, 0.0, 0.0, 1.0)):
        Drawer.__init__(self)

        self.start = start_point
        self.end = end_point
        self.width = width
        self.color = color

    def _get_position(self):
        return (
            min(self.start[0], self.end[0]),
            min(self.start[1], self.end[1]),
        )

    def _set_position(self, new):
        old = self.position
        offset = (
            new[0] - old[0],
            new[1] - old[1],
        )
        self.start = (
            self.start[0] + offset[0],
            self.start[1] + offset[1],
        )
        self.end = (
            self.end[0] + offset[0],
            self.end[1] + offset[1],
        )

    position = property(_get_position, _set_position)

    def _get_size(self):
        return (
            max(self.start[0], self.end[0]) - min(self.start[0], self.end[0]),
            max(self.start[1], self.end[1]) - min(self.start[1], self.end[1]),
        )

    size = property(_get_size)

    def do_draw(self, cairo_ctx, canvas_offset, canvas_visible_size):
        cairo_ctx.save()
        try:
            cairo_ctx.set_source_rgba(self.color[0], self.color[1],
                                      self.color[2], self.color[3])
            cairo_ctx.set_line_width(self.width)
            cairo_ctx.move_to(self.start[0] - canvas_offset[0],
                              self.start[1] - canvas_offset[1])
            cairo_ctx.line_to(self.end[0] - canvas_offset[0],
                              self.end[1] - canvas_offset[1])
            cairo_ctx.stroke()
        finally:
            cairo_ctx.restore()


class PillowImageDrawer(Drawer):
    layer = Drawer.IMG_LAYER
    visible = True

    def __init__(self, position, image):
        Drawer.__init__(self)
        self.size = image.size
        self.img_size = self.size
        self.position = position
        self.angle = 0
        self.surface = image2surface(image)

    def do_draw(self, cairo_ctx, offset, size):
        self.draw_surface(cairo_ctx, offset, size,
                          self.surface, self.position, self.size, self.angle)


class TargetAreaDrawer(Drawer):
    layer = Drawer.BOX_LAYER
    visible = True

    def __init__(self,
                 position, size,
                 target_position, target_size,
                 rect_color=(0.0, 0.0, 1.0, 1.0),
                 out_color=(0.0, 0.0, 1.0, 0.1)):
        Drawer.__init__(self)

        assert(position[0] <= target_position[0])
        assert(position[1] <= target_position[1])
        assert(position[0] + size[0] >= target_position[0] + target_size[0])
        assert(position[1] + size[1] >= target_position[1] + target_size[1])

        self._position = position
        self.size = size
        self.target_position = target_position
        self.target_size = target_size
        self.rect_color = rect_color
        self.out_color = out_color

        logger.info("Drawer: Target area: %s (%s) << %s (%s)"
                    % (str(self._position), str(self.size),
                       str(self.target_position), str(self.target_size)))

    def _get_position(self):
        return self._position

    def _set_position(self, new_position):
        offset = (
            new_position[0] - self._position[0],
            new_position[1] - self._position[1],
        )
        self._position = new_position
        self.target_position = (
            self.target_position[0] + offset[0],
            self.target_position[1] + offset[1],
        )

    position = property(_get_position, _set_position)

    def _draw_rect(self, cairo_ctx, rect):
        cairo_ctx.save()
        try:
            cairo_ctx.set_source_rgba(self.rect_color[0], self.rect_color[1],
                                      self.rect_color[2], self.rect_color[3])
            cairo_ctx.set_line_width(2.0)
            cairo_ctx.rectangle(rect[0][0], rect[0][1],
                                rect[1][0] - rect[0][0],
                                rect[1][1] - rect[0][1])
            cairo_ctx.stroke()
        finally:
            cairo_ctx.restore()

    def _draw_area(self, cairo_ctx, rect):
        cairo_ctx.save()
        try:
            cairo_ctx.set_source_rgba(self.out_color[0], self.out_color[1],
                                      self.out_color[2], self.out_color[3])
            cairo_ctx.rectangle(rect[0][0], rect[0][1],
                                rect[1][0] - rect[0][0],
                                rect[1][1] - rect[0][1])
            cairo_ctx.clip()
            cairo_ctx.paint()
        finally:
            cairo_ctx.restore()

    def do_draw(self, cairo_ctx, canvas_offset, canvas_visible_size):
        # we draw *outside* of the target but inside of the whole
        # area
        rects = [
            (
                # left
                self._draw_area,
                (
                    (self._position[0], self._position[1]),
                    (self.target_position[0], self._position[1] + self.size[1]),
                )
            ),
            (
                # top
                self._draw_area,
                (
                    (self.target_position[0], self._position[1]),
                    (
                        self.target_position[0] + self.target_size[0],
                        self.target_position[1]
                    ),
                )
            ),
            (
                # right
                self._draw_area,
                (
                    (
                        self.target_position[0] + self.target_size[0],
                        self._position[1]),
                    (
                        self._position[0] + self.size[0],
                        self._position[1] + self.size[1]
                    ),
                )
            ),
            (
                # bottom
                self._draw_area,
                (
                    (self.target_position[0],
                     self.target_position[1] + self.target_size[1]),
                    (
                        self.target_position[0] + self.target_size[0],
                        self._position[1] + self.size[1]
                    )
                )
            ),
            (
                # target area
                self._draw_rect,
                (
                    (self.target_position[0], self.target_position[1]),
                    (
                        self.target_position[0] + self.target_size[0],
                        self.target_position[1] + self.target_size[1]
                    ),
                )
            ),
        ]

        rects = [
            (
                func,
                (
                    (
                        rect[0][0] - canvas_offset[0],
                        rect[0][1] - canvas_offset[1],
                    ),
                    (
                        rect[1][0] - canvas_offset[0],
                        rect[1][1] - canvas_offset[1],
                    ),
                )
            )
            for (func, rect) in rects
        ]

        for (func, rect) in rects:
            func(cairo_ctx, rect)


def fit(element_size, area_size):
    """
    Return the size to give to the element so it fits in the area size.
    Keep aspect ratio.
    """
    ratio = min(
        1.0,
        float(area_size[0]) / float(element_size[0]),
        float(area_size[1]) / float(element_size[1]),
    )
    return (
        int(element_size[0] * ratio),
        int(element_size[1] * ratio),
    )

########NEW FILE########
__FILENAME__ = config
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import ConfigParser
import locale
import logging

import pycountry
import pyocr
import pyinsane.abstract_th as pyinsane

from paperwork.backend.config import PaperworkConfig
from paperwork.backend.config import PaperworkSetting
from paperwork.backend.config import paperwork_cfg_boolean
from paperwork.frontend.util.scanner import maximize_scan_area
from paperwork.frontend.util.scanner import set_scanner_opt


logger = logging.getLogger(__name__)
DEFAULT_CALIBRATION_RESOLUTION = 200
DEFAULT_OCR_LANG = "eng"  # if really we can't guess anything
RECOMMENDED_SCAN_RESOLUTION = 300


class _ScanTimes(object):
    """
    Helper to find, load and rewrite the scan times stored in the configuration
    """
    __ITEM_2_CONFIG = {
        'calibration': ('Scanner', 'ScanTimeCalibration'),
        'normal': ('Scanner', 'ScanTime'),
        'ocr': ('OCR', 'OCRTime'),
    }

    def __init__(self):
        self.section = self.__ITEM_2_CONFIG['normal'][0]
        self.values = {}
        self.value = self

    def load(self, config):
        for (k, cfg) in self.__ITEM_2_CONFIG.iteritems():
            try:
                value = float(config.get(cfg[0], cfg[1]))
                self.values[k] = value
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
                if k in self.values:
                    self.values.pop(k)

    def update(self, config):
        for (k, v) in self.values.iteritems():
            if k not in self.__ITEM_2_CONFIG:
                logger.warning("Got timing for '%s' but don't know how to"
                               " store it" % k)
                continue
            cfg = self.__ITEM_2_CONFIG[k]
            config.set(cfg[0], cfg[1], str(v))

    def __getitem__(self, item):
        if item in self.values:
            return self.values[item]
        return 60.0

    def __setitem__(self, item, value):
        self.values[item] = value

    def __get_value(self):
        return self


class _PaperworkScannerCalibration(object):
    def __init__(self, section):
        self.section = section
        self.value = None

    def load(self, config):
        try:
            pt_a_x = int(config.get(
                "Scanner", "Calibration_Pt_A_X"))
            pt_a_y = int(config.get(
                "Scanner", "Calibration_Pt_A_Y"))
            pt_b_x = int(config.get(
                "Scanner", "Calibration_Pt_B_X"))
            pt_b_y = int(config.get(
                "Scanner", "Calibration_Pt_B_Y"))
            if (pt_a_x > pt_b_x):
                (pt_a_x, pt_b_x) = (pt_b_x, pt_a_x)
            if (pt_a_y > pt_b_y):
                (pt_a_y, pt_b_y) = (pt_b_y, pt_a_y)

            resolution = DEFAULT_CALIBRATION_RESOLUTION
            try:
                resolution = int(config.get(
                    "Scanner", "Calibration_Resolution"))
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
                logger.warning("Calibration resolution is not specified in the"
                               " configuration. Will assume the calibration was"
                               " done with a resolution of %ddpi" % resolution)

            self.value = (resolution, ((pt_a_x, pt_a_y), (pt_b_x, pt_b_y)))
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            # no calibration -> no cropping -> we have to keep the whole image
            # each time
            self.value = None

    def update(self, config):
        if self.value is None:
            return
        config.set("Scanner", "Calibration_Resolution",
                   str(self.value[0]))
        config.set("Scanner", "Calibration_Pt_A_X",
                   str(self.value[1][0][0]))
        config.set("Scanner", "Calibration_Pt_A_Y",
                   str(self.value[1][0][1]))
        config.set("Scanner", "Calibration_Pt_B_X",
                   str(self.value[1][1][0]))
        config.set("Scanner", "Calibration_Pt_B_Y",
                   str(self.value[1][1][1]))


class _PaperworkCfgStringList(list):
    def __init__(self, string):
        elements = string.split(",")
        for element in elements:
            self.append(element)

    def __str__(self):
        return ",".join(self)


class _PaperworkLangs(object):
    """
    Convenience setting. Gives all the languages used as one dictionary
    """
    def __init__(self, ocr_lang_setting, spellcheck_lang_setting):
        self.ocr_lang_setting = ocr_lang_setting
        self.spellcheck_lang_setting = spellcheck_lang_setting
        self.section = "OCR"

    def __get_langs(self):
        ocr_lang = self.ocr_lang_setting.value
        if ocr_lang is None:
            return None
        return {
            'ocr': ocr_lang,
            'spelling': self.spellcheck_lang_setting.value
        }

    value = property(__get_langs)

    @staticmethod
    def load(_):
        pass

    @staticmethod
    def update(_):
        pass


class _PaperworkSize(object):
    def __init__(self, section, base_token,
                 default_size=(1024, 768),
                 min_size=(400, 300)):
        self.section = section
        self.base_token = base_token
        self.value = default_size
        self.default_size = default_size
        self.min_size = min_size

    def load(self, config):
        try:
            w = config.get(self.section, self.base_token + "_w")
            w = int(w)
            if w < self.min_size[0]:
                w = self.min_size[0]
            h = config.get(self.section, self.base_token + "_h")
            h = int(h)
            if h < self.min_size[1]:
                h = self.min_size[1]
            self.value = (w, h)
            return
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            self.value = self.default_size

    def update(self, config):
        config.set(self.section, self.base_token + "_w", str(self.value[0]))
        config.set(self.section, self.base_token + "_h", str(self.value[1]))


class _PaperworkFrontendConfigUtil:
    @staticmethod
    def get_default_ocr_lang():
        # Try to guess based on the system locale what would be
        # the best OCR language

        ocr_tools = pyocr.get_available_tools()
        if (len(ocr_tools) < 0):
            return DEFAULT_OCR_LANG
        ocr_langs = ocr_tools[0].get_available_languages()

        default_locale_long = locale.getdefaultlocale()[0]
        # Usually something like "fr_FR" --> we just need the first part
        default_locale = default_locale_long.split("_")[0]
        try:
            lang = pycountry.pycountry.languages.get(alpha2=default_locale)
            for ocr_lang in (lang.terminology, lang.bibliographic):
                if ocr_lang in ocr_langs:
                    return ocr_lang
        except Exception, exc:
            logger.error("Warning: Failed to figure out system language"
                   " (locale is [%s]). Will default to %s"
                   % (default_locale_long, default_locale_long))
            logger.error('Exception was: %s' % exc)
        return DEFAULT_OCR_LANG

    @staticmethod
    def get_default_spellcheck_lang(ocr_lang):
        ocr_lang = ocr_lang.value
        if ocr_lang is None:
            return None

        # Try to guess the lang based on the ocr lang
        try:
            language = pycountry.languages.get(terminology=ocr_lang[:3])
        except KeyError:
            language = pycountry.languages.get(bibliographic=ocr_lang[:3])
        spelling_lang = language.alpha2
        return spelling_lang


def load_config():
    config = PaperworkConfig()

    settings = {
        'main_win_size' : _PaperworkSize("GUI", "main_win_size"),
        'ocr_enabled' : PaperworkSetting("OCR", "Enabled", lambda: True,
                                         paperwork_cfg_boolean),
        'ocr_lang' : PaperworkSetting("OCR", "Lang",
                                      _PaperworkFrontendConfigUtil.get_default_ocr_lang),
        'ocr_nb_angles' : PaperworkSetting("OCR", "Nb_Angles", lambda: 4, int),
        'result_sorting' : PaperworkSetting("GUI", "Sorting", lambda: "scan_date"),
        'scanner_calibration' : _PaperworkScannerCalibration("Scanner"),
        'scanner_devid' : PaperworkSetting("Scanner", "Device"),
        'scanner_resolution' : PaperworkSetting("Scanner", "Resolution",
                                                lambda: RECOMMENDED_SCAN_RESOLUTION,
                                                int),
        'scanner_source' : PaperworkSetting("Scanner", "Source"),
        'scanner_sources' : PaperworkSetting("Scanner", "Sources",
                                             lambda: _PaperworkCfgStringList(""),
                                             _PaperworkCfgStringList),
        'scan_time' : _ScanTimes(),
        'zoom_level' : PaperworkSetting("GUI", "zoom_level", lambda: 0.0, float),
    }
    ocr_lang = _PaperworkFrontendConfigUtil.get_default_spellcheck_lang
    settings['spelling_lang'] = (
        PaperworkSetting("SpellChecking", "Lang",
                         lambda: ocr_lang(settings['ocr_lang']))
    )
    settings['langs'] = (
        _PaperworkLangs(settings['ocr_lang'], settings['spelling_lang'])
    )

    for (k, v) in settings.iteritems():
        config.settings[k] = v

    return config


def get_scanner(config, preferred_sources=None):
    devid = config['scanner_devid'].value
    logger.info("Will scan using %s" % str(devid))
    resolution = config['scanner_resolution'].value
    logger.info("Will scan at a resolution of %d" % resolution)

    dev = pyinsane.Scanner(name=devid)

    if preferred_sources:
        try:
            set_scanner_opt('source', dev.options['source'], preferred_sources)
        except (KeyError, pyinsane.SaneException), exc:
            config_source = config['scanner_source'].value
            logger.error("Warning: Unable to set scanner source to '%s': %s"
                         % (preferred_sources, exc))
            dev.options['source'].value = config_source
    else:
        config_source = config['scanner_source'].value
        dev.options['source'].value = config_source
        logger.info("Will scan using source %s" % str(config_source))

    try:
        dev.options['resolution'].value = resolution
    except pyinsane.SaneException:
        logger.warning("Unable to set scanner resolution to %d: %s"
                       % (resolution, exc))
    if "Color" in dev.options['mode'].constraint:
        dev.options['mode'].value = "Color"
        logger.info("Scanner mode set to 'Color'")
    elif "Gray" in dev.options['mode'].constraint:
        dev.options['mode'].value = "Gray"
        logger.info("Scanner mode set to 'Gray'")
    else:
        logger.warning("Unable to set scanner mode ! May be 'Lineart'")
    maximize_scan_area(dev)
    return (dev, resolution)

########NEW FILE########
__FILENAME__ = dialog
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import logging

import gettext
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import GdkPixbuf


_ = gettext.gettext
logger = logging.getLogger(__name__)


def popup_no_scanner_found(parent):
    """
    Show a popup to the user to tell them no scanner has been found
    """
    # TODO(Jflesch): should be in paperwork.frontend
    # Pyinsane doesn't return any specific exception :(
    logger.info("Showing popup !")
    msg = _("Scanner not found (is your scanner turned on ?)")
    dialog = Gtk.MessageDialog(parent=parent,
                               flags=Gtk.DialogFlags.MODAL,
                               message_type=Gtk.MessageType.WARNING,
                               buttons=Gtk.ButtonsType.OK,
                               message_format=msg)
    dialog.run()
    dialog.destroy()


def ask_confirmation(parent):
    """
    Ask the user "Are you sure ?"

    Returns:
        True --- if they are
        False --- if they aren't
    """
    confirm = Gtk.MessageDialog(parent=parent,
                                flags=Gtk.DialogFlags.MODAL
                                | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                message_type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.YES_NO,
                                message_format=_('Are you sure ?'))
    response = confirm.run()
    confirm.destroy()
    if response != Gtk.ResponseType.YES:
        logging.info("User cancelled")
        return False
    return True


########NEW FILE########
__FILENAME__ = img
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import StringIO

from gi.repository import GdkPixbuf
import PIL.ImageDraw


def add_img_border(img, color="#a6a5a4", width=1):
    """
    Add a border of the specified color and width around a PIL image
    """
    img_draw = PIL.ImageDraw.Draw(img)
    for line in range(0, width):
        img_draw.rectangle([(line, line), (img.size[0]-1-line,
                                           img.size[1]-1-line)],
                           outline=color)
    del img_draw
    return img


def image2pixbuf(img):
    """
    Convert an image object to a gdk pixbuf
    """
    if img is None:
        return None
    file_desc = StringIO.StringIO()
    try:
        img.save(file_desc, "ppm")
        contents = file_desc.getvalue()
    finally:
        file_desc.close()
    loader = GdkPixbuf.PixbufLoader.new_with_type("pnm")
    try:
        loader.write(contents)
        pixbuf = loader.get_pixbuf()
    finally:
        loader.close()
    return pixbuf

########NEW FILE########
__FILENAME__ = imgcutting
#   Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2013-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import PIL.ImageDraw

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from paperwork.frontend.util.canvas.drawers import Drawer
from paperwork.frontend.util.canvas.drawers import PillowImageDrawer
from paperwork.frontend.util.img import image2pixbuf


class ImgGrip(Drawer):
    """
    Represents one of the grip that user can move to cut an image.
    """
    layer = Drawer.BOX_LAYER

    GRIP_SIZE = 40
    DEFAULT_COLOR = (0.0, 0.0, 1.0)
    HOVER_COLOR = (0.0, 1.0, 0.0)
    SELECTED_COLOR = (1.0, 0.0, 0.0)

    def __init__(self, position, max_position):
        self._img_position = position
        self.max_position = max_position
        self.size = (0, 0)
        self.scale = 1.0
        self.selected = False
        self.hover = False
        self.visible = True

    def __get_img_position(self):
        return self._img_position

    def __set_img_position(self, position):
        self._img_position = (
            min(max(0, position[0]), self.max_position[0]),
            min(max(0, position[1]), self.max_position[1]),
        )

    img_position = property(__get_img_position, __set_img_position)

    def __get_on_screen_pos(self):
        x = int(self.scale * self._img_position[0])
        y = int(self.scale * self._img_position[1])
        return (x, y)

    position = property(__get_on_screen_pos)

    def __get_select_area(self):
        (x, y) = self.__get_on_screen_pos()
        x_min = x - (self.GRIP_SIZE / 2)
        y_min = y - (self.GRIP_SIZE / 2)
        x_max = x + (self.GRIP_SIZE / 2)
        y_max = y + (self.GRIP_SIZE / 2)
        return ((x_min, y_min), (x_max, y_max))

    def is_on_grip(self, position):
        """
        Indicates if position is on the grip

        Arguments:
            position --- tuple (int, int)
            scale --- Scale at which the image is represented

        Returns:
            True or False
        """
        ((x_min, y_min), (x_max, y_max)) = self.__get_select_area()
        return (x_min <= position[0] and position[0] <= x_max
                and y_min <= position[1] and position[1] <= y_max)

    def do_draw(self, cairo_ctx, canvas_offset, canvas_size):
        if not self.visible:
            return
        ((a_x, a_y), (b_x, b_y)) = self.__get_select_area()
        a_x -= canvas_offset[0]
        a_y -= canvas_offset[1]
        b_x -= canvas_offset[0]
        b_y -= canvas_offset[1]

        if self.selected:
            color = self.SELECTED_COLOR
        elif self.hover:
            color = self.HOVER_COLOR
        else:
            color = self.DEFAULT_COLOR
        cairo_ctx.set_source_rgb(color[0], color[1], color[2])
        cairo_ctx.set_line_width(1.0)
        cairo_ctx.rectangle(a_x, a_y, b_x - a_x, b_y - a_y)
        cairo_ctx.stroke()


class ImgGripRectangle(Drawer):
    layer = (Drawer.BOX_LAYER + 1)  # draw below/before the grips itself

    COLOR = (0.0, 0.0, 1.0)

    def __init__(self, grips):
        self.grips = grips

    def __get_size(self):
        positions = [grip.position for grip in self.grips]
        return (
            abs(positions[0][0] - positions[1][0]),
            abs(positions[0][1] - positions[1][1]),
        )

    size = property(__get_size)

    def do_draw(self, cairo_ctx, canvas_offset, canvas_size):
        for grip in self.grips:
            if not grip.visible:
                return

        (a_x, a_y) = self.grips[0].position
        (b_x, b_y) = self.grips[1].position
        a_x -= canvas_offset[0]
        a_y -= canvas_offset[1]
        b_x -= canvas_offset[0]
        b_y -= canvas_offset[1]

        cairo_ctx.set_source_rgb(self.COLOR[0], self.COLOR[1], self.COLOR[2])
        cairo_ctx.set_line_width(1.0)
        cairo_ctx.rectangle(a_x, a_y, b_x - a_x, b_y - a_y)
        cairo_ctx.stroke()


class ImgGripHandler(GObject.GObject):
    __gsignals__ = {
        'grip-moved': (GObject.SignalFlags.RUN_LAST, None, ()),
        'zoom-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, img, canvas, zoom_widget):
        GObject.GObject.__init__(self)

        if zoom_widget is None:
            zoom_widget = Gtk.Adjustment(1.0, 0.01, 1.0, 0.01, 0.10)
        self.zoom_widget = zoom_widget

        self.__visible = False

        self.img = img
        self.img_size = self.img.size
        self.canvas = canvas

        self.img_drawer = PillowImageDrawer((0, 0), img)
        self.grips = (
            ImgGrip((0, 0), self.img_size),
            ImgGrip(self.img_size, self.img_size),
        )
        select_rectangle = ImgGripRectangle(self.grips)

        self.selected = None  # the grip being moved

        self.__cursors = {
            'default': Gdk.Cursor.new(Gdk.CursorType.HAND1),
            'visible': Gdk.Cursor.new(Gdk.CursorType.HAND1),
            'on_grip': Gdk.Cursor.new(Gdk.CursorType.TCROSS)
        }

        zoom_widget.connect("value-changed", lambda x:
                            GLib.idle_add(self.__on_zoom_changed))
        canvas.connect("absolute-button-press-event",
                       self.__on_mouse_button_pressed_cb)
        canvas.connect("absolute-motion-notify-event",
                       self.__on_mouse_motion_cb)
        canvas.connect("absolute-button-release-event",
                       self.__on_mouse_button_released_cb)

        self.last_rel_position = (False, 0, 0)
        self.toggle_zoom((0.0, 0.0))

        self.canvas.remove_all_drawers()
        self.canvas.add_drawer(self.img_drawer)
        self.canvas.add_drawer(select_rectangle)
        for grip in self.grips:
            self.canvas.add_drawer(grip)

    def __on_zoom_changed(self):
        self.img_drawer.size = (
            self.img_size[0] * self.scale,
            self.img_size[1] * self.scale,
        )

        for grip in self.grips:
            grip.scale = self.scale

        if self.last_rel_position[0]:
            rel_pos = self.last_rel_position[1:]
            self.last_rel_position = (False, 0, 0)
        else:
            h = self.canvas.get_hadjustment()
            v = self.canvas.get_vadjustment()
            adjs = [h, v]
            rel_pos = []
            for adj in adjs:
                upper = adj.get_upper() - adj.get_page_size()
                lower = adj.get_lower()
                if (upper - lower) <= 0:
                    # XXX(Jflesch): Weird bug ?
                    break
                val = adj.get_value()
                val -= lower
                val /= (upper - lower)
                rel_pos.append(val)
        if len(rel_pos) >= 2:
            GLib.idle_add(self.__replace_scrollbars, rel_pos)

        self.canvas.recompute_size()

        self.emit("zoom-changed")

    def __replace_scrollbars(self, rel_cursor_pos):
        adjustements = [
            (self.canvas.get_hadjustment(), rel_cursor_pos[0]),
            (self.canvas.get_vadjustment(), rel_cursor_pos[1]),
        ]
        for (adjustment, val) in adjustements:
            upper = adjustment.get_upper() - adjustment.get_page_size()
            lower = adjustment.get_lower()
            val = (val * (upper - lower)) + lower
            adjustment.set_value(int(val))

    def __get_scale(self):
        return float(self.zoom_widget.get_value())

    scale = property(__get_scale)

    def toggle_zoom(self, rel_cursor_pos):
        if self.scale != 1.0:
            scale = 1.0
        else:
            scale = min(
                float(self.canvas.visible_size[0]) / self.img_size[0],
                float(self.canvas.visible_size[1]) / self.img_size[1]
            )
        self.last_rel_position = (True, rel_cursor_pos[0], rel_cursor_pos[1])
        self.zoom_widget.set_value(scale)

    def __on_mouse_button_pressed_cb(self, widget, event):
        if not self.visible:
            return
        self.selected = None
        for grip in self.grips:
            if grip.is_on_grip((event.x, event.y)):
                self.selected = grip
                grip.selected = True
                break

    def __move_grip(self, event_pos):
        """
        Move a grip, based on the position
        """
        if not self.selected:
            return None

        new_x = event_pos[0] / self.scale
        new_y = event_pos[1] / self.scale
        self.selected.img_position = (new_x, new_y)

    def __on_mouse_motion_cb(self, widget, event):
        if not self.visible:
            return
        if self.selected:
            self.__move_grip((event.x, event.y))
            is_on_grip = True
            self.canvas.redraw()
        else:
            is_on_grip = False
            for grip in self.grips:
                if grip.is_on_grip((event.x, event.y)):
                    grip.hover = True
                    is_on_grip = True
                else:
                    grip.hover = False
            self.canvas.redraw()

        if is_on_grip:
            cursor = self.__cursors['on_grip']
        else:
            cursor = self.__cursors['visible']
        self.canvas.get_window().set_cursor(cursor)

    def __on_mouse_button_released_cb(self, widget, event):
        if not self.selected:
            # figure out the cursor position on the image
            (img_w, img_h) = self.img_size
            rel_cursor_pos = (
                float(event.x) / (img_w * self.scale),
                float(event.y) / (img_h * self.scale),
            )
            self.toggle_zoom(rel_cursor_pos)
            self.canvas.redraw()
            self.emit('zoom-changed')
            return

        if not self.visible:
            return

        self.selected.selected = False
        self.selected = None
        self.emit('grip-moved')

    def __get_visible(self):
        return self.__visible

    def __set_visible(self, visible):
        self.__visible = visible
        for grip in self.grips:
            grip.visible = visible
        if self.canvas.get_window():
            self.canvas.get_window().set_cursor(self.__cursors['default'])
        self.canvas.redraw()

    visible = property(__get_visible, __set_visible)

    def get_coords(self):
        a_x = min(self.grips[0].img_position[0],
                  self.grips[1].img_position[0])
        a_y = min(self.grips[0].img_position[1],
                  self.grips[1].img_position[1])
        b_x = max(self.grips[0].img_position[0],
                  self.grips[1].img_position[0])
        b_y = max(self.grips[0].img_position[1],
                  self.grips[1].img_position[1])
        return ((int(a_x), int(a_y)), (int(b_x), int(b_y)))


GObject.type_register(ImgGripHandler)

########NEW FILE########
__FILENAME__ = jobs
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import heapq
import logging
import os
import itertools
import sys
import threading
import traceback
import time

from gi.repository import GLib
from gi.repository import GObject

"""
Job scheduling

A major issue in Paperwork are non-thread-safe dependencies (for instance,
libpoppler). This is solved by having only one thread other than the Gtk
main-loop thread. It is the job scheduler. Any long action is run in this
thread to avoid blocking the GUI.
"""

logger = logging.getLogger(__name__)


class JobException(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)


class JobFactory(object):
    def __init__(self, name):
        self.name = name
        self.id_generator = itertools.count()

    def make(self, *args, **kwargs):
        """Child class must override this method"""
        raise NotImplementedError()

    def __eq__(self, other):
        return self is other


class Job(GObject.GObject):  # inherits from GObject so it can send signals
    MAX_TIME_FOR_UNSTOPPABLE_JOB = 0.5  # secs
    MAX_TIME_TO_STOP = 0.5  # secs

    # some jobs can be interrupted. In that case, the job should store in
    # the instance where it stopped, so it can resume its work when do()
    # is called again.
    # If can_stop = False, the job should never last more than
    # MAX_TIME_FOR_UNSTOPPABLE_JOB
    can_stop = False

    priority = 0  # the higher priority is run first

    started_by = None  # set by the scheduler

    already_started_once = False

    def __init__(self, job_factory, job_id):
        GObject.GObject.__init__(self)
        self.factory = job_factory
        self.id = job_id

        self._wait_time = None
        self._wait_cond = threading.Condition()

    def _wait(self, wait_time, force=False):
        """Convenience function to wait while being stoppable"""
        if self._wait_time is None or force:
            self._wait_time = wait_time

        start = time.time()
        self._wait_cond.acquire()
        try:
            self._wait_cond.wait(self._wait_time)
        finally:
            self._wait_cond.release()
            stop = time.time()
            self._wait_time -= (stop - start)

    def _stop_wait(self):
        self._wait_cond.acquire()
        try:
            self._wait_cond.notify_all()
        finally:
            self._wait_cond.release()

    def do(self):
        """Child class must override this method"""
        raise NotImplementedError()

    def stop(self, will_resume=False):
        """
        Only called if can_stop == True.
        Child class must override this method if can_stop == True.
        This function is run from the Gtk thread. It must *not* block
        """
        raise NotImplementedError()

    def __eq__(self, other):
        return self is other

    def __str__(self):
        return ("%s:%d" % (self.factory.name, self.id))


class JobScheduler(object):
    def __init__(self, name):
        self.name = name
        self._thread = None
        self.running = False

        # _job_queue_cond.acquire()/release() protect the job queue
        # _job_queue_cond.notify_all() is called each time the queue is modified
        #  (except on cancel())
        self._job_queue_cond = threading.Condition()
        self._job_queue = []
        self._active_job = None

        self._job_idx_generator = itertools.count()

    def start(self):
        """Starts the scheduler"""
        assert(not self.running)
        assert(self._thread is None)
        logger.info("[Scheduler %s] Starting" % self.name)
        self._thread = threading.Thread(target=self._run)
        self.running = True
        self._thread.start()

    def _run(self):
        logger.info("[Scheduler %s] Started" % self.name)

        while self.running:

            self._job_queue_cond.acquire()
            try:
                while len(self._job_queue) <= 0:
                    self._job_queue_cond.wait()
                    if not self.running:
                        return
                (_, _, self._active_job) = heapq.heappop(self._job_queue)
            finally:
                self._job_queue_cond.release()

            if not self.running:
                return

            # we are the only thread changing self._active_job,
            # so we can safely use it even if we didn't keep the lock
            # on self._job_queue_lock

            assert(self._active_job is not None)

            start = time.time()
            self._active_job.already_started_once = True
            try:
                self._active_job.do()
            except Exception, exc:
                logger.error("===> Job %s raised an exception: %s: %s"
                             % (str(self._active_job),
                                type(exc), str(exc)))
                idx = 0
                for stack_el in traceback.extract_tb(sys.exc_info()[2]):
                    logger.error("%2d: %20s: L%5d: %s"
                                 % (idx, stack_el[0],
                                    stack_el[1], stack_el[2]))
                    idx += 1
                logger.error("---> Job %s was started by:"
                             % (str(self._active_job)))
                idx = 0
                for stack_el in self._active_job.started_by:
                    logger.error("%2d: %20s: L%5d: %s"
                                 % (idx, stack_el[0],
                                    stack_el[1], stack_el[2]))
                    idx += 1
            stop = time.time()

            diff = stop - start
            if (self._active_job.can_stop
                or diff <= Job.MAX_TIME_FOR_UNSTOPPABLE_JOB):
                logger.debug("Job %s took %dms"
                             % (str(self._active_job), diff * 1000))
            else:
                logger.warning("Job %s took %dms and is unstoppable !"
                               " (maximum allowed: %dms)"
                               % (str(self._active_job), diff * 1000,
                                  Job.MAX_TIME_FOR_UNSTOPPABLE_JOB * 1000))

            self._job_queue_cond.acquire()
            try:
                self._active_job = None
                self._job_queue_cond.notify_all()
            finally:
                self._job_queue_cond.release()

            if not self.running:
                return

    def _stop_active_job(self, will_resume=False):
        active_job = self._active_job

        if active_job.can_stop:
            logger.debug("[Scheduler %s] Job %s marked for stopping"
                         % (self.name, str(active_job)))
            active_job.stop(will_resume=will_resume)
        else:
            logger.warning(
                "[Scheduler %s] Tried to stop job %s, but it can't"
                " be stopped"
                % (self.name, str(active_job)))

    def schedule(self, job):
        """
        Schedule a job.

        Job are run by priority (higher first). If the given job
        has a priority higher than the one currently running, the scheduler
        will try to stop the running one, and start the given one instead.

        In case 2 jobs have the same priority, they are run in the order they
        were given.
        """
        logger.debug("[Scheduler %s] Queuing job %s"
                     % (self.name, str(job)))

        job.started_by = traceback.extract_stack()

        self._job_queue_cond.acquire()
        try:
            heapq.heappush(self._job_queue,
                           (-1 * job.priority, next(self._job_idx_generator),
                            job))

            # if a job with a lower priority is running, we try to stop
            # it and take its place
            active = self._active_job
            if (active is not None
                    and active.priority < job.priority):
                if not active.can_stop:
                    logger.debug("Job %s has a higher priority than %s,"
                                 " but %s can't be stopped"
                                 % (str(job), str(active), str(active)))
                else:
                    self._stop_active_job(will_resume=True)
                    # the active job may have already been re-queued
                    # previously. In which case we don't want to requeue
                    # it again
                    if not active in self._job_queue:
                        heapq.heappush(self._job_queue,
                                       (-1 * active.priority,
                                        next(self._job_idx_generator),
                                        active))

            self._job_queue_cond.notify_all()
        finally:
            self._job_queue_cond.release()

    def _cancel_matching_jobs(self, condition):
        self._job_queue_cond.acquire()
        try:
            try:
                to_rm = []
                for job in self._job_queue:
                    if condition(job[2]):
                        to_rm.append(job)
                for job in to_rm:
                    self._job_queue.remove(job)
                    if job[2].already_started_once:
                        job[2].stop(will_resume=False)
                    logger.debug("[Scheduler %s] Job %s cancelled"
                                 % (self.name, str(job[2])))
            except ValueError:
                pass

            heapq.heapify(self._job_queue)
            if (self._active_job is not None and condition(self._active_job)):
                self._stop_active_job(will_resume=False)
        finally:
            self._job_queue_cond.release()

    def cancel(self, target_job):
        logger.debug("[Scheduler %s] Canceling job %s"
                     % (self.name, str(target_job)))
        self._cancel_matching_jobs(
            lambda job: (job == target_job))

    def cancel_all(self, factory):
        logger.debug("[Scheduler %s] Canceling all jobs %s"
                     % (self.name, factory.name))
        self._cancel_matching_jobs(
            lambda job: (job.factory == factory))

    def stop(self):
        assert(self.running)
        assert(self._thread is not None)
        logger.info("[Scheduler %s] Stopping" % self.name)

        self.running = False

        self._job_queue_cond.acquire()
        if self._active_job is not None:
            self._stop_active_job(will_resume=False)
        try:
            self._job_queue_cond.notify_all()
        finally:
            self._job_queue_cond.release()

        self._thread.join()
        self._thread = None

        logger.info("[Scheduler %s] Stopped" % self.name)


class JobProgressUpdater(Job):
    """
    Update a progress bar a predefined timing.
    """

    can_stop = True
    priority = 500
    NB_UPDATES = 50

    def __init__(self, factory, id, progressbar,
                 value_min=0.0, value_max=0.5, total_time=20.0):
        Job.__init__(self, factory, id)
        self.progressbar = progressbar
        self.value_min = float(value_min)
        self.value_max = float(value_max)
        self.total_time = float(total_time)

    def do(self):
        self.can_run = True

        for upd in xrange(0, self.NB_UPDATES):
            if not self.can_run:
                return

            val = self.value_max - self.value_min
            val *= upd
            val /= self.NB_UPDATES
            val += self.value_min

            GLib.idle_add(self.progressbar.set_fraction, val)
            self._wait(self.total_time / self.NB_UPDATES, force=True)

    def stop(self, will_resume=False):
        self.can_run = False
        self._stop_wait()


GObject.type_register(JobProgressUpdater)


class JobFactoryProgressUpdater(JobFactory):
    def __init__(self, progress_bar):
        JobFactory.__init__(self, "ProgressUpdater")
        self.progress_bar = progress_bar

    def make(self, value_min=0.0, value_max=0.5, total_time=20.0):
        job = JobProgressUpdater(self, next(self.id_generator),
                                 self.progress_bar, value_min, value_max,
                                 total_time)
        return job

########NEW FILE########
__FILENAME__ = progressivelist
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import logging

import gettext
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from paperwork.frontend.util.jobs import Job, JobFactory, JobScheduler


_ = gettext.gettext
logger = logging.getLogger(__name__)


class JobProgressiveList(Job):
    can_stop = True
    priority = 500

    def __init__(self, factory, id, progressive_list):
        Job.__init__(self, factory, id)
        self.__progressive_list = progressive_list
        self.can_run = True

    def do(self):
        self._wait(0.5)
        if not self.can_run:
            return
        GLib.idle_add(self.__progressive_list.display_extra)

    def stop(self, will_resume=True):
        self.can_run = False
        self._stop_wait()


GObject.type_register(JobProgressiveList)


class JobFactoryProgressiveList(JobFactory):
    def __init__(self, progressive_list):
        JobFactory.__init__(self, "Progressive List")
        self.progressive_list = progressive_list

    def make(self):
        return JobProgressiveList(self, next(self.id_generator),
                                  self.progressive_list)


class ProgressiveList(GObject.GObject):
    """
    We use GtkIconView to display documents and pages. However this widget
    doesn't like having too many elements to display: it keeps redrawing the
    list when the mouse goes over it --> with 600 documents, this may be
    quite long.

    So instead, we display only X elements. When the user scroll down,
    we add Y elements to the list, etc.
    """

    NB_EL_DISPLAYED_INITIALLY = 100
    NB_EL_DISPLAY_EXTRA_WHEN_LOWER_THAN = 0.85
    NB_EL_DISPLAYED_ADDITIONNAL = int((1.0 - NB_EL_DISPLAY_EXTRA_WHEN_LOWER_THAN)
                                      * NB_EL_DISPLAYED_INITIALLY)

    __gsignals__ = {
        'lines-shown': (GObject.SignalFlags.RUN_LAST, None,
                      (GObject.TYPE_PYOBJECT,) ),  # [(line_idx, obj), ... ]
    }

    def __init__(self, name,
                 scheduler,
                 default_thumbnail,
                 gui, scrollbars, model,
                 model_nb_columns, actions=[]):
        """
        Arguments:
            name --- Name of the progressive list (for verbose only)
            scheduler --- Job scheduler to use to schedule list extension jobs
            default_thumbnail --- default thumbnail to use until the new one is
                                    loaded
            gui --- list widget
            scrollbars --- scrollpane widget
            model -- liststore
            actions --- actions to disabled while updating the list
        """
        GObject.GObject.__init__(self)
        self.name = name
        self.scheduler = scheduler
        self.default_thumbnail = default_thumbnail
        self.actions = actions
        self.widget_gui = gui

        self.widget_scrollbars = scrollbars
        self._vadjustment = scrollbars.get_vadjustment()

        self.model = model
        self.model_content = []
        self.model_nb_columns = model_nb_columns

        self.nb_displayed = 0

        self._vadjustment.connect(
            "value-changed",
            lambda widget: GLib.idle_add(self.__on_scrollbar_moved))

        self.job_factory = JobFactoryProgressiveList(self)

    def set_model(self, model_content):
        self.model_content = model_content

        self.widget_gui.freeze_child_notify()
        self.widget_gui.set_model(None)
        try:
            self.model.clear()
            self.nb_displayed = 0
            self._display_up_to(self.NB_EL_DISPLAYED_INITIALLY)
        finally:
            self.widget_gui.freeze_child_notify()
            self.widget_gui.set_model(self.model)

    def display_extra(self):
        for action in self.actions:
            action.enabled = False
        try:
            selected = self.widget_gui.get_selected_items()
            if len(selected) <= 0:
                selected = -1
            else:
                selected = min([x.get_indices()[0] for x in selected])

            (first_visible, last_visible) = self.widget_gui.get_visible_range()

            self.widget_gui.freeze_child_notify()
            self.widget_gui.set_model(None)
            try:
                self._display_up_to(self.nb_displayed +
                                    self.NB_EL_DISPLAYED_ADDITIONNAL)
            finally:
                self.widget_gui.freeze_child_notify()
                self.widget_gui.set_model(self.model)

            if (selected > 0):
                path = Gtk.TreePath(selected)
                self.widget_gui.select_path(path)
                self.widget_gui.set_cursor(path, None, False)

            GLib.idle_add(self.widget_gui.scroll_to_path, last_visible,
                             False, 0.0, 0.0)
        finally:
            for action in self.actions:
                action.enabled = True

    def _display_up_to(self, nb_elements):
        l_model = len(self.model)
        if l_model > 0:
            doc = self.model[-1][2]
            if doc is None or doc == 0:
                line_iter = self.model.get_iter(l_model-1)
                self.model.remove(line_iter)

        newly_displayed = []
        for line_idx in xrange(self.nb_displayed, nb_elements):
            if (self.nb_displayed >= nb_elements
                    or line_idx >= len(self.model_content)):
                break
            newly_displayed.append((line_idx, self.model_content[line_idx][2]))
            self.model.append(self.model_content[line_idx])
            self.nb_displayed += 1

        self.emit('lines-shown', newly_displayed)

        if nb_elements < len(self.model_content):
            padding = [None] * (self.model_nb_columns - 2)
            model_line = [_("Loading ..."), self.default_thumbnail]
            model_line += padding
            self.model.append(model_line)

        logger.info("List '%s' : %d elements displayed (%d additionnal)"
                    % (self.name, self.nb_displayed, len(newly_displayed)))

    def __on_scrollbar_moved(self):
        if self.nb_displayed >= len(self.model_content):
            return

        lower = self._vadjustment.get_lower()
        upper = self._vadjustment.get_upper()
        val = self._vadjustment.get_value()
        proportion = (val - lower) / (upper - lower)

        if proportion > self.NB_EL_DISPLAY_EXTRA_WHEN_LOWER_THAN:
            self.scheduler.cancel_all(self.job_factory)
            job = self.job_factory.make()
            self.scheduler.schedule(job)

    def set_model_value(self, line_idx, column_idx, value):
        self.model_content[line_idx][column_idx] = value
        if line_idx < self.nb_displayed:
            line_iter = self.model.get_iter(line_idx)
            self.model.set_value(line_iter, column_idx, value)

    def set_model_line(self, line_idx, model_line):
        self.model_content[line_idx] = model_line
        if line_idx < self.nb_displayed:
            self.model[line_idx] = model_line

    def pop(self, idx):
        content = self.model_content.pop(idx)
        itr = self.model.get_iter(idx)
        self.model.remove(itr)
        return content

    def insert(self, idx, line):
        self.model_content.insert(idx, line)
        self.model.insert(idx, line)

    def select_idx(self, idx=-1):
        if idx >= 0:
            # we are going to select the current page in the list
            # except we don't want to be called again because of it
            for action in self.actions:
                action.enabled = False
            try:
                self.widget_gui.unselect_all()

                path = Gtk.TreePath(idx)
                self.widget_gui.select_path(path)
                self.widget_gui.set_cursor(path, None, False)
            finally:
                for action in self.actions:
                    action.enabled = True

            # HACK(Jflesch): The Gtk documentation says that scroll_to_path()
            # should do nothing if the target cell is already visible (which
            # is the desired behavior here). Except we just emptied the
            # document list model and remade it from scratch. For some reason,
            # it seems that  Gtk will then always consider that the cell is
            # not visible and move the scrollbar.
            # --> we use idle_add to move the scrollbar only once everything
            # has been displayed
            GLib.idle_add(self.widget_gui.scroll_to_path,
                             path, False, 0.0, 0.0)
        else:
            self.unselect()

    def unselect(self):
        self.widget_gui.unselect_all()
        path = Gtk.TreePath(0)
        GLib.idle_add(self.widget_gui.scroll_to_path,
                         path, False, 0.0, 0.0)

    def __getitem__(self, item):
        return {
            'gui': self.widget_gui,
            'model': self.model_content,
            'scrollbars': self.widget_scrollbars
        }[item]


GObject.type_register(ProgressiveList)



########NEW FILE########
__FILENAME__ = renderer
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import math
from gi.repository import GObject
from gi.repository import Gtk


class CellRendererLabels(Gtk.CellRenderer):
    LABEL_HEIGHT = 25
    LABEL_SPACING = 3
    LABEL_TEXT_SIZE = 13
    LABEL_CORNER_RADIUS = 10

    labels = GObject.property(type=object, default=None,
                              flags=GObject.PARAM_READWRITE)
    highlight = GObject.property(type=bool, default=False,
                                 flags=GObject.PARAM_READWRITE)

    def __init__(self):
        Gtk.CellRenderer.__init__(self)

    def do_get_size(self, widget, cell_area):
        if self.labels is None or len(self.labels) == 0:
            return (0, 0, 0, 0)
        xpad = self.get_property('xpad')
        ypad = self.get_property('ypad')
        width = 50  # meh, not really used
        height = len(self.labels) * (self.LABEL_HEIGHT + self.LABEL_SPACING)
        return (xpad, ypad, width+(2*ypad), height+(2*ypad))

    @staticmethod
    def _rectangle_rounded(cairo_ctx, area, radius):
        (x, y, w, h) = area
        cairo_ctx.new_sub_path()
        cairo_ctx.arc(x + w - radius, y + radius, radius, -1.0 * math.pi / 2, 0)
        cairo_ctx.arc(x + w - radius, y + h - radius, radius, 0, math.pi / 2)
        cairo_ctx.arc(x + radius, y + h - radius, radius, math.pi / 2, math.pi)
        cairo_ctx.arc(x + radius, y + radius, radius, math.pi,
                      3.0 * math.pi / 2)
        cairo_ctx.close_path()

    def do_render(self, cairo_ctx, widget,
                  bg_area_gdk_rect, cell_area_gdk_rect,
                  flags):
        if self.labels is None or len(self.labels) == 0:
            return

        txt_offset = (self.LABEL_HEIGHT - self.LABEL_TEXT_SIZE) / 2
        cairo_ctx.set_font_size(self.LABEL_TEXT_SIZE)

        if not self.highlight:
            cairo_ctx.select_font_face("", cairo.FONT_SLANT_NORMAL,
                                       cairo.FONT_WEIGHT_NORMAL)
        else:
            cairo_ctx.select_font_face("", cairo.FONT_SLANT_NORMAL,
                                       cairo.FONT_WEIGHT_BOLD)

        xpad = self.get_property('xpad')
        ypad = self.get_property('ypad')
        (x, y, w, h) = (cell_area_gdk_rect.x + xpad,
                        cell_area_gdk_rect.y + ypad,
                        cell_area_gdk_rect.width - (2*xpad),
                        cell_area_gdk_rect.height - (2*ypad))

        for label_idx in xrange(0, len(self.labels)):
            label = self.labels[label_idx]

            (label_x, label_y, label_w, label_h) = \
                    (x,
                     y + (label_idx * (self.LABEL_HEIGHT + self.LABEL_SPACING)),
                     w, self.LABEL_HEIGHT)

            # background rectangle
            bg = label.get_rgb_bg()
            cairo_ctx.set_source_rgb(bg[0], bg[1], bg[2])
            cairo_ctx.set_line_width(1)
            self._rectangle_rounded(cairo_ctx,
                                    (label_x, label_y, label_w, label_h),
                                    self.LABEL_CORNER_RADIUS)
            cairo_ctx.fill()

            # foreground text
            fg = label.get_rgb_fg()
            cairo_ctx.set_source_rgb(fg[0], fg[1], fg[2])
            cairo_ctx.move_to(label_x + self.LABEL_CORNER_RADIUS,
                              label_y + self.LABEL_HEIGHT - txt_offset)
            cairo_ctx.show_text(label.name)


GObject.type_register(CellRendererLabels)



########NEW FILE########
__FILENAME__ = scanner
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re

import pyinsane.abstract_th as pyinsane


logger = logging.getLogger(__name__)


def _set_scanner_opt(scanner_opt_name, scanner_opt, possible_values):
    value = possible_values[0]
    regexs = [re.compile(x, flags=re.IGNORECASE) for x in possible_values]

    if (scanner_opt.constraint_type ==
        pyinsane.SaneConstraintType.STRING_LIST):
        value = None
        for regex in regexs:
            for constraint in scanner_opt.constraint:
                if regex.match(constraint):
                    value = constraint
                    break
            if value is not None:
                break
        if value is None:
            raise pyinsane.SaneException(
                "%s are not a valid values for option %s"
                % (str(possible_values), scanner_opt_name))

    logger.info("Setting scanner option '%s' to '%s'"
                % (scanner_opt_name, str(value)))
    scanner_opt.value = value


def set_scanner_opt(scanner_opt_name, scanner_opt, possible_values):
    """
    Set one of the scanner options

    Arguments:
        scanner_opt_name --- for verbose
        scanner_opt --- the scanner option (its value, its constraints, etc)
        possible_values --- a list of values considered valid (the first one
                            being the preferred one)
    """
    # WORKAROUND(Jflesch): For some reason, my crappy scanner returns
    # I/O errors randomly for fun
    for t in xrange(0, 5):
        try:
            _set_scanner_opt(scanner_opt_name, scanner_opt, possible_values)
            break
        except Exception, exc:
            logger.warning("Warning: Failed to set scanner option"
                           " %s=%s: %s (try %d/5)"
                           % (scanner_opt_name, possible_values, str(exc), t))


def __set_scan_area_pos(options, opt_name, select_value_func, missing_options):
    if not opt_name in options:
        missing_options.append(opt_name)
    constraint = options[opt_name].constraint
    if isinstance(constraint, tuple):
        value = select_value_func(constraint[0], constraint[1])
    else:  # is an array
        value = select_value_func(constraint)
    options[opt_name].value = value


def maximize_scan_area(scanner):
    opts = scanner.options
    missing_opts = []
    __set_scan_area_pos(opts, "tl-x", min, missing_opts)
    __set_scan_area_pos(opts, "tl-y", min, missing_opts)
    __set_scan_area_pos(opts, "br-x", max, missing_opts)
    __set_scan_area_pos(opts, "br-y", max, missing_opts)
    if missing_opts:
        logger.warning("Failed to maximize the scan area. Missing options: %s"
                       % ", ".join(missing_opts))

########NEW FILE########
__FILENAME__ = paperwork
#!/usr/bin/env python
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012-2014  Jerome Flesch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.
"""
Bootstrapping code
"""

import os

import gettext
import logging
from gi.repository import GObject
from gi.repository import Gtk
import locale

import pyinsane.abstract_th  # Just to start the Sane thread

from frontend.mainwindow import ActionRefreshIndex, MainWindow
from frontend.util.config import load_config


logger = logging.getLogger(__name__)

LOCALE_PATHS = [
    # French
    ('locale/fr/LC_MESSAGES/paperwork.mo', 'locale'),
    ('/usr/local/share/locale/fr/LC_MESSAGES/paperwork.mo',
     '/usr/local/share/locale'),
    ('/usr/share/locale/fr/LC_MESSAGES/paperwork.mo', '/usr/share/locale'),

    # German
    ('locale/de/LC_MESSAGES/paperwork.mo', 'locale'),
    ('/usr/local/share/locale/de/LC_MESSAGES/paperwork.mo',
     '/usr/local/share/locale'),
    ('/usr/share/locale/de/LC_MESSAGES/paperwork.mo', '/usr/share/locale'),
]


def set_locale():
    """
    Enable locale support
    """
    locale.setlocale(locale.LC_ALL, '')

    got_locales = False
    locales_path = None
    for (fr_locale_path, locales_path) in LOCALE_PATHS:
        logger.info("Looking for locales in '%s' ..." % (fr_locale_path))
        if os.access(fr_locale_path, os.R_OK):
            logging.info("Will use locales from '%s'" % (locales_path))
            got_locales = True
            break
    if not got_locales:
        logger.warning("WARNING: Locales not found")
    else:
        for module in (gettext, locale):
            module.bindtextdomain('paperwork', locales_path)
            module.textdomain('paperwork')


def init_logging():
    formatter = logging.Formatter(
            '%(levelname)-6s %(name)-30s %(message)s')
    handler = logging.StreamHandler()
    logger = logging.getLogger()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel({
        "DEBUG" : logging.DEBUG,
        "INFO" : logging.INFO,
        "WARNING" : logging.WARNING,
        "ERROR" : logging.ERROR,
    }[os.getenv("PAPERWORK_VERBOSE", "INFO")])


def main():
    """
    Where everything start.
    """
    init_logging()
    set_locale()

    GObject.threads_init()

    try:
        config = load_config()
        config.read()

        main_win = MainWindow(config)
        ActionRefreshIndex(main_win, config).do()
        Gtk.main()
    finally:
        logger.info("Good bye")


if __name__ == "__main__":
    main()

########NEW FILE########
