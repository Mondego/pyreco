__FILENAME__ = 01readlahmanplayerstats
#!/usr/bin/python

# Converts Master.csv into a python shelf object
# input: Master.csv filename from the Lahman data set (http://seanlahman.com/files/database/readme59.txt), python shelf filename for data
# output: (none)

from common import csv_split

import shelve
import sys

def process_master_file(shelf_fn, master_fn):
    lahman_shelf = shelve.open(shelf_fn, flag='n')

    for i, line in enumerate(open(master_fn)):
        line = line.strip()
        if i == 0:
            schema = line.split(",")
        else:
            values = csv_split(line)

            if len(values) != len(schema):
                raise Exception("Line mismatch: expected %d values, got %d.  Schema:\n%s\nLine:\n%s" % (len(schema), len(values), ",".join(schema), line))
            stats = dict( zip(schema, values) )
            lahman_shelf[stats["retroID"]] = stats

    lahman_shelf.close()

def main():
    shelf_fn = sys.argv[1]
    master_fn = sys.argv[2]

    process_master_file(shelf_fn, master_fn)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 02parsegamelogs
#!/usr/bin/python

# input: python shelf filename from Lahman dataset (see 01readlahmanplayerstats.py), filename(s) in EVA/EVN format
# output: training set representing labelled situations

import json
import logging
import re
import shelve
import sys

from common import FeatureSet, GameState, PlayerState, Label, csv_split

def parse_header(header):
    game_state = GameState()
    base_featureset = FeatureSet()

    for line in header.split("\n"):
        line = line.strip()
        if line.startswith("info,"):
            try:
                _, key, value = csv_split(line)
            except Exception:
                logging.error("Choked on line: %s" % line)
                raise

            if key in ["visteam", "hometeam"]:
                setattr(GameState, key, value)

            fs_key = "game_%s" % key
            if fs_key in FeatureSet.__slots__:
                setattr(FeatureSet, fs_key, value)

    return game_state, base_featureset

def add_player_state(line, lahman_shelf, game_state, state_by_id):
    # note, this doesn't keep track of who gets subbed out, just the latest state for each player
    try:
        _, retrosheetid, name, team, batpos, fieldpos = csv_split(line)
    except Exception:
        logging.error("Choked on line: %s" % line)
        raise

    player_state = PlayerState()
    player_state.retrosheetid = retrosheetid
    player_state.name = name
    player_state.visorhome = "visteam" if team == "0" else "hometeam"
    player_state.team = getattr(game_state, player_state.visorhome)
    player_state.batpos = batpos
    player_state.fieldpos = fieldpos

    # update for pitcher changes
    if fieldpos == "1":
        setattr(game_state, "%s_pitcherid" % player_state.visorhome, retrosheetid)

    if retrosheetid in lahman_shelf:
        lahman_stats = lahman_shelf[retrosheetid]
        for lahman_key in PlayerState.lahman_stats:
            setattr(player_state, "lahman_%s" % lahman_key, lahman_stats[lahman_key])

    state_by_id[retrosheetid] = player_state

def parse_players(players, lahman_shelf, game_state):
    state_by_id = {}

    for line in players.split("\n"):
        line = line.strip()
        if line.startswith("start,"):
            add_player_state(line, lahman_shelf, game_state, state_by_id)

    return state_by_id

def get_feature_sets(playbyplay, lahman_shelf, game_state, base_featureset, player_state_by_id):
    for line in playbyplay.split("\n"):
        line = line.strip()

        if line.startswith("sub"):
            add_player_state(line, lahman_shelf, game_state, player_state_by_id)

        elif line.startswith("play"):
            try:
                _, inning, visorhome, retrosheetid, count, pitches, play = csv_split(line)
            except Exception:
                logging.error("Choked on line: %s" % line)
                raise

            if any( play.startswith(ignore) for ignore in ["NP"] ):
                continue

            try:
                featureset = base_featureset.copy()

                # player info
                featureset.add_batter_info(player_state_by_id[retrosheetid])

                # make sure to select the OPPOSITE pitcher from the current batter
                game_state_key = "%s_pitcherid" % ("visteam" if visorhome == "1" else "hometeam")
                featureset.add_pitcher_info(player_state_by_id[getattr(game_state, game_state_key)])

                # at-bat stats
                featureset.ab_inning = inning
                try:
                    numballs, numstrikes = count[:2]
                    featureset.ab_numballs = numballs
                    featureset.ab_numstrikes = numstrikes
                except Exception:
                    pass

                # TODO: keep track of outs, runners on?

                # label
                if play.startswith("HR"):
                    featureset.label = Label.HR
                elif play.startswith("K"):
                    featureset.label = Label.K
                else:
                    featureset.label = Label.OTHER

                yield featureset
            except Exception:
                logging.error("Choked on line: %s" % line)
                raise

def get_game_sections(game):
    sections_regex = re.compile(r"(?P<header>^id,.*?)"
                                r"(?P<players>^start,.*?)"
                                r"(?P<playbyplay>^play,.*?)"
                                r"(?P<data>^data,.*)$",
                                re.DOTALL | re.MULTILINE)
    return sections_regex.match(game)

def parse_game(lahman_shelf, game):
    sections = get_game_sections(game)

    game_state, base_featureset = parse_header(sections.group("header"))
    player_state_by_id = parse_players(sections.group("players"), lahman_shelf, game_state)

    for feature_set in get_feature_sets(sections.group("playbyplay"), lahman_shelf, game_state, base_featureset, player_state_by_id):
        print feature_set

def parse_ev(lahman_shelf, ev_fn):
    game_regex = re.compile(r"(\s|^)id,(.*?)(?=((\s|^)id,|$))", re.DOTALL)

    for match in game_regex.finditer(open(ev_fn).read()):
        try:
            parse_game(lahman_shelf, match.group(0).strip())
        except Exception:
            logging.error("Choked on fn: %s" % ev_fn)
            raise

def main():
    lahman_shelf = shelve.open(sys.argv[1], flag='r')
    for fn in sys.argv[2:]:
        parse_ev(lahman_shelf, fn)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 03maketrainingdata
#!/usr/bin/python

# input: parsed game logs filename, training set output filename
# output: parsed and cleaned training set

from common import TrainingDatum
import sys

def main():
    input_fn, output_fn = sys.argv[1:]

    out_f = open(output_fn, 'w')
    for line in open(input_fn):
        td = TrainingDatum.from_featureset_json(line.strip())
        out_f.write("%s\n" % td.to_json())

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 04featuresetsperyear
#!/usr/bin/python

# input: output filename, training set filename
# output: all possible feature / value pairs in that training set

import json
import sys

from common import TrainingDatum

def main():
    output_fn, tdata_fn = sys.argv[1], sys.argv[2]
    all_features = {}
    for line in open(tdata_fn):
        td = json.loads(line.strip())
        for fname, fval in td.iteritems():
            if fname != "label":
                all_features.setdefault(fname, set()).add(fval)

    for k in all_features:
        all_features[k] = sorted(all_features[k])

    json.dump(all_features, open(output_fn, 'w'))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 05featureselection
#!/usr/bin/python

# input: beginning and ending year (e.g. 1996 2011), label to predict, feature type, algorithm
# output: p-independence for all features

import json
import os
import multiprocessing
import sys
import time

import itertools
import numpy
from sklearn.feature_selection import univariate_selection

class Features2Indices(object):
    def __init__(self, featuresets):
        raise NotImplemented

class Features2IndicesByFeature(Features2Indices):
    """ Just uses the feature name itself, not particular values. """
    def __init__(self, featuresets):
        self.features2indices = {}
        self.indices2features = []
        for i, (key, all_values) in enumerate(sorted(featuresets.items())):
            self.features2indices[key] = {"index": i,
                                          "values": dict([ (j, v) for v, j in enumerate(sorted(all_values)) ])}
            self.indices2features.append({"key": key,
                                          "values": sorted(all_values)})

    def get_num_features(self):
        return len(self.features2indices)

    def make_feature_array(self, dct):
        lst = [ -1 ] * self.get_num_features()
        for k, v in dct.iteritems():
            if k == "label":
                continue
            idx = self.features2indices[k]["index"]
            val = self.features2indices[k]["values"][v]
            lst[idx] = val
        return lst

    def get_feature_name(self, idx):
        return self.indices2features[idx]["key"]

class Features2IndicesByValue(Features2Indices):
    """ Uses feature name+value as the feature name. """
    @classmethod
    def get_fname(cls, key, value):
        return "%s::%s" % (key, value)

    def __init__(self, featuresets):
        self.features2indices = {}
        self.indices2features = []
        curpos = 0
        for key, all_values in sorted(featuresets.items()):
            for value in sorted(all_values):
                fname = self.get_fname(key, value)
                self.features2indices[fname] = curpos
                self.indices2features.append(fname)
                curpos += 1

    def get_num_features(self):
        return len(self.features2indices)

    def make_feature_array(self, dct):
        lst = [ -1 ] * self.get_num_features()
        for k, v in dct.iteritems():
            if k == "label":
                continue
            fname = self.get_fname(k, v)
            idx = self.features2indices[fname]
            lst[idx] = 1
        return numpy.array(lst)

    def get_feature_name(self, idx):
        return self.indices2features[idx]

def print_significant_features(p_values, feature_mapper, start_year, end_year):
    best_indices = sorted(range(len(p_values)),
                          key=(lambda x: p_values[x]))
    lines = []
    for idx in best_indices:
        lines.append( [feature_mapper.get_feature_name(idx), str(p_values[idx])] )

    max_width_by_col = [ max( len(lines[i][c]) for i in xrange(len(lines)) ) for c in xrange(len(lines[0])) ]
    for fname, val in lines:
        print fname.ljust(max_width_by_col[0]), "\t", val.ljust(max_width_by_col[1])

def _read_file(args):
    fn, params, functions = args[0], args[1], args[2:]
    results = []
    for line in open(fn):
        results.append([ f(line.strip(), **params) for f in functions ])
    return results

def _get_label(line, **kwargs):
    return 1 if json.loads(line)["label"] == kwargs["predicted_label"] else 0

def _make_arr(line, **kwargs):
    return kwargs["feature_mapper"].make_feature_array(json.loads(line))

def _noop(line, **kwargs):
    pass

def get_feature_array(start_year, end_year, feature_mapper, predicted_label):
    pool = multiprocessing.Pool(processes=(multiprocessing.cpu_count()-1))

    try:
        def send_to_pool(args):
            return itertools.chain(*pool.imap(_read_file, args, chunksize=1))

        filenames = [ os.path.join("data", "training", "%d.tdata" % year) for year in range(start_year, end_year + 1) ]
        args = [ (fn, {}, _noop) for fn in filenames ]

        num_lines = sum( 1 for _ in enumerate(send_to_pool(args)) )

        value_array = numpy.zeros( (num_lines, feature_mapper.get_num_features()) )
        labels = numpy.zeros(num_lines)

        kwargs = {"feature_mapper": feature_mapper, "predicted_label": predicted_label}
        args = [ (fn, kwargs, _make_arr, _get_label) for fn in filenames ]

        # rip through all data points again, this time populating the array
        for i, (val_arr, label) in enumerate(send_to_pool(args)):
            for j in xrange(len(val_arr)):
                value_array[i][j] = val_arr[j]
            labels[i] = label

        return value_array, labels
    finally:
        pool.close()

def get_feature_mapper(start_year, end_year, feature_mapper_clss):
    # grabs all possible features for a given start/end year and maps all keys and values to integers for arrays

    featuresets = {}
    for year in range(start_year, end_year + 1):
        fn = os.path.join("data", "featuresets", "%d.json" % year)
        d = json.load(open(fn))
        for k, values in d.iteritems():
            featuresets.setdefault(k, set()).update(set(values))

    return feature_mapper_clss(featuresets)

def main():
    start_year, end_year, predicted_label, feature_type, selection_type = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]

    feature_mapper_clss = {"name": Features2IndicesByFeature, "nameval": Features2IndicesByValue}[feature_type]
    selection_fn = {"chi2": univariate_selection.chi2, "anova": univariate_selection.f_classif}[selection_type]

    feature_mapper = get_feature_mapper(start_year, end_year, feature_mapper_clss)
    value_array, labels = get_feature_array(start_year, end_year, feature_mapper, predicted_label)

    _, p_values = selection_fn(value_array, labels)
    print_significant_features(p_values, feature_mapper, start_year, end_year)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 06buildhistogram
#!/usr/bin/python

# input: beginning and ending year (e.g. 1996 2011), output filename
# output: per feature, per value, per value histogram

import json
import os
import sys

from common import Label

def main():
    start_year, end_year, out_fn = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]

    counts = {}
    for fn in ( os.path.join("data", "training", "%d.tdata" % year) for year in range(start_year, end_year + 1) ):
        print fn
        for line in open(fn):
            td = json.loads(line.strip())
            label = td.pop("label")
            for fname, fval in td.iteritems():
                counts.setdefault(fname, {}).setdefault(fval, dict([ (k, 0) for k in Label.get_all() ]))[label] += 1

    json.dump(counts, open(out_fn, "w"))

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 07trainbayesclassifier
#!/usr/bin/python

# input: beginning and ending year (e.g. 1996 2011), output filename
# output: per feature, per value, per value histogram

import json
import os
import sys

import nltk

from common import dump_bayes_to_file

def tset_gen(start_year, end_year):
    for fn in ( os.path.join("data", "training", "%d.tdata" % year) for year in range(start_year, end_year + 1) ):
        print fn
        for line in open(fn):
            td = json.loads(line.strip())
            label = td.pop("label")
            yield (td, label)

def main():
    start_year, end_year, out_fn = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]

    dump_bayes_to_file(nltk.NaiveBayesClassifier.train(tset_gen(start_year, end_year)),
                       out_fn)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = 08buildcharts
#!/usr/bin/python

# input: histogram fn and an output directory
# output: per-feature significance charts for home runs and strikeouts

import csv
import json
import os.path
import re
import sys

from common import UNK

def build_chart(feature_name, data, category_names, output_dir):
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.textlabels import Label
    from reportlab.lib import colors
    from reportlab.lib.validators import Auto

    # build chart and save it
    d = Drawing(800, 600)
    d.add(String(200,180,feature_name), name='title')

    chart = VerticalBarChart()
    chart.width = d.width-100
    chart.height = d.height-75
    chart.x = 40
    chart.y = 40

    chart.data = data
    chart.categoryAxis.categoryNames = category_names
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 2

    chart.bars[0].fillColor = colors.red
    chart.bars[1].fillColor = colors.blue

    d.add(chart)

    d.title.x = d.width/2
    d.title.y = d.height - 30
    d.title.textAnchor ='middle'
    d.title.fontSize = 24

    d.add(Legend(),name='Legend')
    d.Legend.colorNamePairs  = [(chart.bars[i].fillColor, name) for i, name in enumerate(["Home Run", "Strikeout"])]
    d.Legend.fontName = 'Times-Roman'
    d.Legend.fontSize = 16
    d.Legend.x = d.width-80
    d.Legend.y = d.height-25
    d.Legend.dxTextSpace = 5
    d.Legend.dy = 5
    d.Legend.dx = 5
    d.Legend.deltay = 5
    d.Legend.alignment ='right'

    d.add(Label(),name='XLabel')
    d.XLabel.fontName = 'Times-Roman'
    d.XLabel.fontSize = 12
    d.XLabel.x = chart.x + chart.width/2
    d.XLabel.y = 15
    d.XLabel.textAnchor ='middle'
    d.XLabel._text = "Value"

    d.add(Label(),name='YLabel')
    d.YLabel.fontName = 'Times-Roman'
    d.YLabel.fontSize = 12
    d.YLabel.x = 10
    d.YLabel.y = chart.y + chart.height/2
    d.YLabel.angle = 90
    d.YLabel.textAnchor ='middle'
    d.YLabel._text = "Likelihood Index"

    d.save(fnRoot=os.path.join(output_dir, feature_name), formats=['png'])

def build_csv(feature_name, data, category_names, output_dir):
    out_csv = csv.writer(open(os.path.join(output_dir, feature_name + ".csv"), "w"))

    out_csv.writerow([""] + category_names)
    out_csv.writerow(["HR"] + data[0])
    out_csv.writerow(["K"] + data[1])

def dump_feature(feature_name, value_dict, output_dir):
    # drop insignificant features
    value_dict.pop(UNK, None)
    # HACK: apparently game_temp = 0 is the same as <UNK>
    if feature_name == "game_temp":
        value_dict.pop("[0-5)", None)

    # first pass, sum up the labels
    label_counts = {}
    for fval, counts_by_label in value_dict.iteritems():
        for label, count in counts_by_label.iteritems():
            label_counts[label] = label_counts.get(label, 0) + count

    num_samples = sum(label_counts.itervalues())

    predictor_labels = ["HR", "K"]
    data = [ [] for l in predictor_labels ]
    category_names = []

    baseline_likelihood = dict( (k, float(label_counts[k])/num_samples) for k in predictor_labels )

    def keyfn(x):
        # gah, pesky numeric values
        try:
            return int(x)
        except Exception:
            pass
        if x.startswith("[") and x.endswith(")"): return int(re.match("\[(-?\d+)-\d+\)", x).group(1))
        if x.endswith("+"): return int(x[:-1])
        return x

    # (HR-index, K-index) for each significant value
    for fval in sorted(value_dict.keys(), key=keyfn):
        counts_by_label = value_dict[fval]

        # "significant" features have > 0.05% of the total number of samples
        if sum(counts_by_label.values()) > 0.0005 * num_samples:
            category_names.append(fval)
            for i, label in enumerate(predictor_labels):
                likelihood = float(counts_by_label[label])/sum(counts_by_label.values())
                data[i].append(likelihood / baseline_likelihood[label])

    build_chart(feature_name, data, category_names, output_dir)
    build_csv(feature_name, data, category_names, output_dir)

def main():
    histogram_fn, output_dir = sys.argv[1:]

    histogram = json.load(open(histogram_fn))
    for feature, value_dict in histogram.iteritems():
        dump_feature(feature, value_dict, output_dir)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = common
import datetime
import json
import logging
import pickle
import re

import nltk

UNK = "<UNK>"

class Label(object):
    HR = "HR"
    K = "K"
    OTHER = "OTHER"

    @classmethod
    def get_all(cls):
        return [ k for k in dir(cls) if not k.startswith("_") and k != "get_all" ]

class GameState(object):
    __slots__ = [
        "visteam",
        "hometeam",
        "visteam_pitcherid",
        "hometeam_pitcherid"
        ]

    def __str__(self):
        return "<GameState: %s>" % ", ".join([ "%s=%s" % (slot, getattr(self, slot, None)) for slot in sorted(self.__slots__) ])

class PlayerState(object):
    lahman_stats = ["birthYear",
                    "birthMonth",
                    "birthDay",
                    "birthCountry",
                    "birthState",
                    "birthCity",
                    "weight",
                    "height",
                    "bats",
                    "throws",
                    "debut",
                    "finalGame",
                    "college"]

    player_stats = ["retrosheetid",
                    "visorhome",
                    "team",
                    "name",
                    "fieldpos",
                    "batpos"]
    __slots__ = player_stats \
        + [ "lahman_%s" % stat for stat in lahman_stats ]

    def __str__(self):
        return "<PlayerState: %s>" % ", ".join([ "%s=%s" % (slot, getattr(self, slot, None)) for slot in sorted(self.__slots__) ])

    def __repr__(self):
        return self.__str__()

class FeatureSet(object):
    __slots__ = [
        # general, per-game
        "game_daynight",
        "game_date",
        "game_number", # 0 is the first game of the day, 1 is the second of a doubleheader
        "game_site", # ballpark
        "game_temp",
        "game_winddir",

        # at-bat
        "ab_inning",
        "ab_numballs",
        "ab_numstrikes",

        # label
        "label" ] \
        + [ "batter_%s" % stat for stat in (PlayerState.player_stats + PlayerState.lahman_stats) ] \
        + [ "pitcher_%s" % stat for stat in (PlayerState.player_stats + PlayerState.lahman_stats) ]

    def __str__(self):
        return self.to_json()

    def to_json(self):
        d = {}
        for slot in self.__slots__:
            # all values are strings!
            d[slot] = getattr(self, slot, "").strip() or UNK
        return json.dumps(d)

    @classmethod
    def get_parse_map(cls):
        if not hasattr(cls, "parse_map"):
            player_ints = ["birthYear",
                           "birthMonth",
                           "birthDay",
                           "weight",
                           "height",
                           "batpos",
                           "fieldpos"]
            int_fields = ["game_number",
                          "game_temp",
                          "ab_inning",
                          "ab_numballs",
                          "ab_numstrikes",
                          "birthYear"] + \
                          [ "batter_%s" % k for k in player_ints ] + \
                          [ "pitcher_%s" % k for k in player_ints ]
            parse_map = {"game_date": (lambda x: datetime.datetime.strptime(x, "%Y/%m/%d")),
                         "batter_debut": (lambda x: datetime.datetime.strptime(x, "%m/%d/%Y")),
                         "pitcher_debut": (lambda x: datetime.datetime.strptime(x, "%m/%d/%Y"))}

            for field in int_fields:
                parse_map[field] = int
            cls.parse_map = parse_map
        return cls.parse_map

    def copy(self):
        # this is very puzzling; why does a new object created in the context of a given object have all the fields of the object in which the new object is created...?
        new_obj = FeatureSet()
        assert(new_obj.to_json() == self.to_json())
        return new_obj

    def add_batter_info(self, batter_state):
        self.add_player_info(batter_state, "batter")

    def add_pitcher_info(self, pitcher_state):
        self.add_player_info(pitcher_state, "pitcher")

    def add_player_info(self, player_state, prefix):
        for field in ["fieldpos", "batpos", "team", "visorhome", "name", "retrosheetid"]:
            setattr(self, "%s_%s" % (prefix, field), getattr(player_state, field))

        for lahman_field in ["birthYear",
                             "birthMonth",
                             "birthDay",
                             "birthCountry",
                             "birthState",
                             "birthCity",
                             "weight",
                             "height",
                             "bats",
                             "throws",
                             "debut",
                             "college"]:
            if hasattr(player_state, "lahman_%s" % lahman_field):
                setattr(self, "%s_%s" % (prefix, lahman_field), getattr(player_state, "lahman_%s" % lahman_field))

class TrainingDatum(object):
    player_stats = ["age", # bucketized by 3
                    "weight", # bucketized by 10
                    "height", # bucketized by 3
                    "team",
                    "experience", # game date - debut, bucketized by 3
                    "birthCountry",
                    "throws"]

    batter_stats = ["fieldpos",
                    "batpos", # bucketized 1-2,3-5,6-7,8-9,10,11 (10 is DH, 11 is PH)
                    "bats",
                    "visorhome" ]

    __slots__ = ["game_daynight",
                 "game_month", # bucketized by 2
                 "game_year", # bucketized by 5
                 "game_number", # 0 or 1+
                 "game_site",
                 "game_temp", # bucketized by 5
                 "game_winddir", # in or out

                 "ab_inning", # bucketized: 1-3, 4-6, 7-9, 9+
                 "ab_numballs",
                 "ab_numstrikes",
                 "ab_lrmatchup", # "same" for L vs. R, "opposite" for R vs. R

                 "label"] \
                 + [ "batter_%s" % stat for stat in (player_stats + batter_stats) ] \
                 + [ "pitcher_%s" % stat for stat in player_stats ]

    @classmethod
    def bucketized(cls, val, buckets=None, granularity=None):
        if granularity:
            lower = (val / granularity) * granularity
            upper = ((val / granularity) + 1) * granularity
            return "[%d-%d)" % (lower, upper)
        if buckets:
            for i in reversed(xrange(len(buckets))):
                bkt = buckets[i]
                if val >= bkt:
                    if i == (len(buckets) - 1):
                        # this is the last bucket
                        return "%d+" % bkt
                    else:
                        return "[%d-%d)" % (bkt, buckets[i+1])
            raise Exception, "Bucket value %s doesn't fit into buckets: %s" % (val, buckets)

    @classmethod
    def get_winddir(cls, d):
        if d["game_winddir"].startswith("from"):
            return "in"
        elif d["game_winddir"].startswith("to"):
            return "out"
        return UNK

    @classmethod
    def get_lrmatchup(cls, d):
        if d["batter_bats"] is UNK:
            return UNK

        if d["batter_bats"] in "B":
            return "same"

        if d["pitcher_throws"] is UNK:
            return None

        return "same" if d["batter_bats"] == d["pitcher_throws"] else "opposite"

    @classmethod
    def from_featureset_json(cls, json_str):
        d = json.loads(json_str)
        parse_map = FeatureSet.get_parse_map()

        for k in d:
            # all keys are strings in the .features format
            if d[k] != UNK and k in parse_map:
                try:
                    d[k] = parse_map[k](d[k])
                except ValueError:
                    d[k] = UNK

        obj = cls()

        def unk_check(obj_key, keys=None):
            """ If all specified keys are known, return True.  Otherwise,
            set UNK on the specified object key. """
            if keys is None:
                keys = [ obj_key ]

            if all( (d[k] != UNK) for k in keys):
                # proceed with calculation
                return True
            else:
                setattr(obj, obj_key, UNK)
                return False

        obj.game_daynight = d["game_daynight"]
        if unk_check("game_date"):
            obj.game_month = cls.bucketized(d["game_date"].month, granularity=2)

        if unk_check("game_date"):
            obj.game_year = cls.bucketized(d["game_date"].year, granularity=5)

        if unk_check("game_number"):
            obj.game_number = cls.bucketized(d["game_number"], buckets=[0,1])

        if unk_check("game_temp"):
            obj.game_temp = cls.bucketized(d["game_temp"], granularity=5)

        obj.game_site = d["game_site"]

        obj.game_winddir = cls.get_winddir(d)

        if unk_check("ab_inning"):
            obj.ab_inning = cls.bucketized(d["ab_inning"], buckets=[1,4,7,10])

        obj.ab_numballs = d["ab_numballs"]
        obj.ab_numstrikes = d["ab_numstrikes"]

        obj.ab_lrmatchup = cls.get_lrmatchup(d)

        obj.batter_bats = d["batter_bats"]
        obj.batter_fieldpos = d["batter_fieldpos"]
        obj.batter_visorhome = d["batter_visorhome"]

        if unk_check("batter_batpos"):
            obj.batter_batpos = cls.bucketized(d["batter_batpos"], buckets=[1,3,5,8,10,11,12])

        obj.label = d["label"]

        for prefix in ["batter_", "pitcher_"]:
            def key(k):
                return prefix + k

            def year_from_td(td):
                return td.days / 365

            if unk_check(key("age"), keys=[key("birthYear"), key("birthMonth"), key("birthDay"), "game_date"]):
                birthday = datetime.datetime(d[key("birthYear")], d[key("birthMonth")], d[key("birthDay")])
                setattr(obj, key("age"), cls.bucketized(year_from_td(d["game_date"] - birthday), granularity=3))

            if unk_check(key("weight")):
                setattr(obj, key("weight"), cls.bucketized(d[key("weight")], granularity=10))
            if unk_check(key("height")):
                setattr(obj, key("height"), cls.bucketized(d[key("height")], granularity=3))

            setattr(obj, key("team"), d[key("team")])
            setattr(obj, key("throws"), d[key("throws")])
            setattr(obj, key("birthCountry"), d[key("birthCountry")])

            if unk_check(key("experience"), keys=[key("debut"), "game_date"]):
                setattr(obj, key("experience"), cls.bucketized(year_from_td(d["game_date"] - d[key("debut")]), granularity=3))

        return obj

    def __str__(self):
        return "<TrainingDatum: %s>" % ", ".join([ "%s=%s" % (k, getattr(self, k)) for k in sorted(self.__slots__) if hasattr(self, k)])

    def to_json(self):
        return json.dumps(dict([ (slot, getattr(self,slot)) for slot in self.__slots__ ]))

line_regex = re.compile(r'((?:".*?")|.*?)(?:,|$)')
def csv_split(line):
    # there's gotta be a better way to do this
    values = line_regex.findall(line)
    if not line.endswith(","):
        return values[:-1]
    return values

def dump_bayes_to_file(bayes_classifier, filename):
    pickle.dump({"_label_probdist": bayes_classifier._label_probdist,
                 "_feature_probdist": bayes_classifier._feature_probdist},
                open(filename, "w"))

def load_bayes_from_file(filename):
    d = pickle.load(open(filename))
    return nltk.NaiveBayesClassifier(d["_label_probdist"], d["_feature_probdist"])

########NEW FILE########
__FILENAME__ = wsgi

from cgi import FieldStorage, parse_qs
import json
import re

from common import load_bayes_from_file, UNK

PREDICTOR_LABELS = ["HR", "K", "OTHER"]
HISTOGRAM_FN = "output/histogram_1980-2011.json"
ALL_FEATURES = None
def get_all_features(args, post_data):
    global ALL_FEATURES

    if ALL_FEATURES is None:
        # pedantic note: I could do this in one line, but that would be wrong.
        ALL_FEATURES = []
        for fname, valdict in json.load(open(HISTOGRAM_FN)).iteritems():

            if fname != "label":
                def keyfn(x):
                    try:
                        return int(x)
                    except Exception:
                        pass
                    # gah, pesky numeric values
                    if x.startswith("[") and x.endswith(")"): return int(re.match("\[(-?\d+)-\d+\)", x).group(1))
                    if x.endswith("+"): return int(x[:-1])
                    return x

                tpl = (fname,
                       sorted([ k for k in valdict.keys() if k != UNK ],
                              key=keyfn))
                ALL_FEATURES.append(tpl)

        ALL_FEATURES.sort()

    return {"features": ALL_FEATURES}

def predict_bundle(args, post_data):
    # this is a silly hack because qs args are coming through to the post data and I'm too lazy to figure out why
    d = dict( (k, post_data[k].value) for k in post_data if k != "type" )

    for k in d.keys():
        try:
            # gah, this is so gross; stupid post args not being ints and I'm running out of time.  PyCon is Friday!
            d[k] = int(d[k])
        except ValueError:
            pass

    response = {"bundle": {},
                "baseline": {}}
    probdist = CLASSIFIER.prob_classify(d)
    baseline_probdist = CLASSIFIER.prob_classify({})
    for label in PREDICTOR_LABELS:
        response["bundle"][label] = probdist.prob(label)
        response["baseline"][label] = baseline_probdist.prob(label)

    return response

BAYES_FN = "output/bayes_1980-2011.json"
CLASSIFIER = load_bayes_from_file(BAYES_FN)
def get_response(args, post_data):
    response_map = {"features": get_all_features,
                    "predict": predict_bundle}
    unspecified = (lambda x,y: {"error": "specify 'type'"})

    fn = response_map.get(args.pop("type", None), unspecified)
    return fn(args, post_data)

# WSGI funtimes
def get_args(environ):
    # just use the first argument for each key provided
    return dict(( (k, v[0]) for k,v in parse_qs(environ["QUERY_STRING"]).iteritems() ))

def get_post_data(environ):
    post_data = environ.copy()
    return FieldStorage(
        fp=environ['wsgi.input'],
        environ=post_data,
        keep_blank_values=True)

def application(environ, start_response):
    args = get_args(environ)
    post_data = get_post_data(environ)
    response = json.dumps(get_response(args, post_data))

    headers = [ ("Content-Type", "application/json"),
                ("Content-Length", len(response)) ]

    start_response("200 OK", headers)
    return iter([response])

########NEW FILE########
