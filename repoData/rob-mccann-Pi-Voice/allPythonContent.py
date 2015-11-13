__FILENAME__ = db
#!/usr/bin/env python
# coding: utf-8

"""
Main script for dbpedia quepy.
"""

import sys
import time
import random
import datetime

import quepy
from SPARQLWrapper import SPARQLWrapper, JSON
from ex.exception import NoResultsFoundException

sparql = SPARQLWrapper("http://dbpedia.org/sparql")
dbpedia = quepy.install("actions.dbpedia")


class DBPedia:
    def __init__(self, tts):
            self.tts = tts

    def process(self, job):
        if job.get_is_processed():
            return False

        try:
            self.query(job.raw())
            job.is_processed = True
        except NoResultsFoundException:
            print "failed to get reponse from dbpedia"
            return False

    def query(self, phrase):
        print "Creating SparQL query"

        target, query, metadata = dbpedia.get_query(phrase)

        if isinstance(metadata, tuple):
            query_type = metadata[0]
            metadata = metadata[1]
        else:
            query_type = metadata
            metadata = None

        if query is None:
            raise NoResultsFoundException()

        print query

        print_handlers = {
            "define": self.print_define,
            "enum": self.print_enum,
            "time": self.print_time,
            "literal": self.print_literal,
            "age": self.print_age,
        }

        if target.startswith("?"):
            target = target[1:]

        if query:
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()

            if not results["results"]["bindings"]:
                raise NoResultsFoundException()

        return print_handlers[query_type](results, target, metadata)

    def print_define(self, results, target, metadata=None):
        for result in results["results"]["bindings"]:
            if result[target]["xml:lang"] == "en":
                self.say(result[target]["value"])

    def print_enum(self, results, target, metadata=None):
        used_labels = []

        for result in results["results"]["bindings"]:
            if result[target]["type"] == u"literal":
                if result[target]["xml:lang"] == "en":
                    label = result[target]["value"]
                    if label not in used_labels:
                        used_labels.append(label)
                        self.say(label)


    def print_literal(self, results, target, metadata=None):
        for result in results["results"]["bindings"]:
            literal = result[target]["value"]
            if metadata:
                self.say(metadata.format(literal))
            else:
                self.say(literal)


    def print_time(self, results, target, metadata=None):
        gmt = time.mktime(time.gmtime())
        gmt = datetime.datetime.fromtimestamp(gmt)

        for result in results["results"]["bindings"]:
            offset = result[target]["value"].replace(u"−", u"-")

            if "to" in offset:
                from_offset, to_offset = offset.split("to")
                from_offset, to_offset = int(from_offset), int(to_offset)

                if from_offset > to_offset:
                    from_offset, to_offset = to_offset, from_offset

                from_delta = datetime.timedelta(hours=from_offset)
                to_delta = datetime.timedelta(hours=to_offset)

                from_time = gmt + from_delta
                to_time = gmt + to_delta

                location_string = random.choice(["where you are",
                                                 "your location"])

                self.say("Between %s and %s, depending %s" % \
                      (from_time.strftime("%H:%M"),
                       to_time.strftime("%H:%M on %A"),
                       location_string))

            else:
                offset = int(offset)

                delta = datetime.timedelta(hours=offset)
                the_time = gmt + delta

                self.say(the_time.strftime("%H:%M on %A"))


    def print_age(self, results, target, metadata=None):
        assert len(results["results"]["bindings"]) == 1

        birth_date = results["results"]["bindings"][0][target]["value"]
        year, month, days = birth_date.split("-")

        birth_date = datetime.date(int(year), int(month), int(days))

        now = datetime.datetime.utcnow()
        now = now.date()

        age = now - birth_date
        self.say("{} years old".format(age.days / 365))

    def say(self, text):
        return self.tts.say(text)

########NEW FILE########
__FILENAME__ = country
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Coutry related regex
"""

from refo import Plus, Question
from quepy.semantics import HasKeyword
from quepy.regex import Lemma, Pos, RegexTemplate, Token, Particle
from semantics import IsCountry, IncumbentOf, CapitalOf, LabelOf, \
                      LanguageOf, PopulationOf, PresidentOf


class Country(Particle):
    regex = Plus(Pos("DT") | Pos("NN") | Pos("NNS") | Pos("NNP") | Pos("NNPS"))

    def semantics(self, match):
        name = match.words.tokens.title()
        return IsCountry() + HasKeyword(name)


class PresidentOfRegex(RegexTemplate):
    """
    Regex for questions about the president of a country.
    Ex: "Who is the president of Argentina?"
    """

    regex = Pos("WP") + Token("is") + Question(Pos("DT")) + \
        Lemma("president") + Pos("IN") + Country() + Question(Pos("."))

    def semantics(self, match):
        president = PresidentOf(match.country)
        incumbent = IncumbentOf(president)
        label = LabelOf(incumbent)

        return label, "enum"


class CapitalOfRegex(RegexTemplate):
    """
    Regex for questions about the capital of a country.
    Ex: "What is the capital of Bolivia?"
    """

    opening = Lemma("what") + Token("is")
    regex = opening + Pos("DT") + Lemma("capital") + Pos("IN") + \
        Question(Pos("DT")) + Country() + Question(Pos("."))

    def semantics(self, match):
        capital = CapitalOf(match.country)
        label = LabelOf(capital)
        return label, "enum"


# FIXME: the generated query needs FILTER isLiteral() to the head
# because dbpedia sometimes returns different things
class LanguageOfRegex(RegexTemplate):
    """
    Regex for questions about the language spoken in a country.
    Ex: "What is the language of Argentina?"
        "what language is spoken in Argentina?"
    """

    openings = (Lemma("what") + Token("is") + Pos("DT") +
                Question(Lemma("official")) + Lemma("language")) | \
               (Lemma("what") + Lemma("language") + Token("is") +
                Lemma("speak"))

    regex = openings + Pos("IN") + Question(Pos("DT")) + Country() + \
        Question(Pos("."))

    def semantics(self, match):
        language = LanguageOf(match.country)
        return language, "enum"


class PopulationOfRegex(RegexTemplate):
    """
    Regex for questions about the population of a country.
    Ex: "What is the population of China?"
        "How many people live in China?"
    """

    openings = (Pos("WP") + Token("is") + Pos("DT") +
                Lemma("population") + Pos("IN")) | \
               (Pos("WRB") + Lemma("many") + Lemma("people") +
                Token("live") + Pos("IN"))
    regex = openings + Question(Pos("DT")) + Country() + Question(Pos("."))

    def semantics(self, match):
        population = PopulationOf(match.country)
        return population, "literal"

########NEW FILE########
__FILENAME__ = movies
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Movie related regex.
"""

from refo import Plus, Question
from quepy.semantics import HasKeyword
from quepy.regex import Lemma, Lemmas, Pos, RegexTemplate, Particle
from semantics import IsMovie, NameOf, IsPerson, DirectedBy, LabelOf, \
                      DurationOf, HasActor, HasName, ReleaseDateOf, \
                      DirectorOf, StarsIn, DefinitionOf

nouns = Plus(Pos("NN") | Pos("NNS") | Pos("NNP") | Pos("NNPS"))


class Movie(Particle):
    regex = Question(Pos("DT")) + nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsMovie() + HasName(name)


class Actor(Particle):
    regex = nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsPerson() + HasKeyword(name)


class Director(Particle):
    regex = nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsPerson() + HasKeyword(name)


class ListMoviesRegex(RegexTemplate):
    """
    Ex: "list movies"
    """

    regex = Lemma("list") + (Lemma("movie") | Lemma("film"))

    def semantics(self, match):
        movie = IsMovie()
        name = NameOf(movie)
        return name, "enum"


class MoviesByDirectorRegex(RegexTemplate):
    """
    Ex: "List movies directed by Quentin Tarantino.
        "movies directed by Martin Scorsese"
        "which movies did Mel Gibson directed"
    """

    regex = (Question(Lemma("list") | (Lemma('show'))) + (Lemma("movie") | Lemma("film")) +
             Question(Lemma("direct")) + Lemma("by") + Director()) | \
            (Lemma("which") + (Lemma("movie") | Lemma("film")) + Lemma("do") +
             Director() + Lemma("direct") + Question(Pos(".")))

    def semantics(self, match):
        movie = IsMovie() + DirectedBy(match.director)
        movie_name = LabelOf(movie)

        return movie_name, "enum"


class MovieDurationRegex(RegexTemplate):
    """
    Ex: "How long is Pulp Fiction"
        "What is the duration of The Thin Red Line?"
    """

    regex = ((Lemmas("how long be") + Movie()) |
            (Lemmas("what be") + Pos("DT") + Lemma("duration") +
             Pos("IN") + Movie())) + \
            Question(Pos("."))

    def semantics(self, match):
        duration = DurationOf(match.movie)
        return duration, ("literal", "{} minutes long")


class ActedOnRegex(RegexTemplate):
    """
    Ex: "List movies with Hugh Laurie"
        "Movies with Matt LeBlanc"
        "In what movies did Jennifer Aniston appear?"
        "Which movies did Mel Gibson starred?"
        "Movies starring Winona Ryder"
    """

    acted_on = (Lemma("appear") | Lemma("act") | Lemma("star"))
    movie = (Lemma("movie") | Lemma("movies") | Lemma("film"))
    regex = (Question(Lemma("list")) + movie + Lemma("with") + Actor()) | \
            (Question(Pos("IN")) + (Lemma("what") | Lemma("which")) +
             movie + Lemma("do") + Actor() + acted_on + Question(Pos("."))) | \
            (Question(Pos("IN")) + Lemma("which") + movie + Lemma("do") +
             Actor() + acted_on) | \
            (Question(Lemma("list")) + movie + Lemma("star") + Actor())

    def semantics(self, match):
        movie = IsMovie() + HasActor(match.actor)
        movie_name = NameOf(movie)
        return movie_name, "enum"


class MovieReleaseDateRegex(RegexTemplate):
    """
    Ex: "When was The Red Thin Line released?"
        "Release date of The Empire Strikes Back"
    """

    regex = ((Lemmas("when be") + Movie() + Lemma("release")) |
            (Lemma("release") + Question(Lemma("date")) +
             Pos("IN") + Movie())) + \
            Question(Pos("."))

    def semantics(self, match):
        release_date = ReleaseDateOf(match.movie)
        return release_date, "literal"


class DirectorOfRegex(RegexTemplate):
    """
    Ex: "Who is the director of Big Fish?"
        "who directed Pocahontas?"
    """

    regex = ((Lemmas("who be") + Pos("DT") + Lemma("director") +
             Pos("IN") + Movie()) |
             (Lemma("who") + Lemma("direct") + Movie())) + \
            Question(Pos("."))

    def semantics(self, match):
        director = IsPerson() + DirectorOf(match.movie)
        director_name = NameOf(director)
        return director_name, "literal"


class ActorsOfRegex(RegexTemplate):
    """
    Ex: "who are the actors of Titanic?"
        "who acted in Alien?"
        "who starred in Depredator?"
        "Actors of Fight Club"
    """

    regex = (Lemma("who") + Question(Lemma("be") + Pos("DT")) +
             (Lemma("act") | Lemma("actor") | Lemma("star")) +
             Pos("IN") + Movie() + Question(Pos("."))) | \
            ((Lemma("actors") | Lemma("actor")) + Pos("IN") + Movie())

    def semantics(self, match):
        actor = NameOf(IsPerson() + StarsIn(match.movie))
        return actor, "enum"


class PlotOfRegex(RegexTemplate):
    """
    Ex: "what is Shame about?"
        "plot of Titanic"
    """

    regex = ((Lemmas("what be") + Movie() + Lemma("about")) | \
             (Question(Lemmas("what be the")) + Lemma("plot") +
              Pos("IN") + Movie()) +
            Question(Pos(".")))

    def semantics(self, match):
        definition = DefinitionOf(match.movie)
        return definition, "define"

########NEW FILE########
__FILENAME__ = music
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Music related regex
"""

from refo import Plus, Question
from quepy.semantics import HasKeyword
from quepy.regex import Lemma, Lemmas, Pos, RegexTemplate, Particle
from semantics import IsBand, LabelOf, IsMemberOf, ActiveYears, \
                      MusicGenereOf, NameOf, IsAlbum, ProducedBy


class Band(Particle):
    regex = Question(Pos("DT")) + Plus(Pos("NN") | Pos("NNP"))

    def semantics(self, match):
        name = match.words.tokens.title()
        return IsBand() + HasKeyword(name)


class BandMembersRegex(RegexTemplate):
    """
    Regex for questions about band member.
    Ex: "Radiohead members"
        "What are the members of Metallica?"
    """

    regex1 = Band() + Lemma("member")
    regex2 = Lemma("member") + Pos("IN") + Band()
    regex3 = Pos("WP") + Lemma("be") + Pos("DT") + Lemma("member") + \
        Pos("IN") + Band()

    regex = (regex1 | regex2 | regex3) + Question(Pos("."))

    def semantics(self, match):
        member = IsMemberOf(match.band)
        label = LabelOf(member)
        return label, "enum"


class FoundationRegex(RegexTemplate):
    """
    Regex for questions about the creation of a band.
    Ex: "When was Pink Floyd founded?"
        "When was Korn formed?"
    """

    regex = Pos("WRB") + Lemma("be") + Band() + \
        (Lemma("form") | Lemma("found")) + Question(Pos("."))

    def semantics(self, match):
        active_years = ActiveYears(match.band)
        return active_years, "literal"


class GenreRegex(RegexTemplate):
    """
    Regex for questions about the genre of a band.
    Ex: "What is the music genre of Gorillaz?"
        "Music genre of Radiohead"
    """

    optional_opening = Question(Pos("WP") + Lemma("be") + Pos("DT"))
    regex = optional_opening + Question(Lemma("music")) + Lemma("genre") + \
        Pos("IN") + Band() + Question(Pos("."))

    def semantics(self, match):
        genere = MusicGenereOf(match.band)
        label = LabelOf(genere)
        return label, "enum"


class AlbumsOfRegex(RegexTemplate):
    """
    Ex: "List albums of Pink Floyd"
        "What albums did Pearl Jam record?"
        "Albums by Metallica"
    """

    regex = (Question(Lemma("list")) + (Lemma("album") | Lemma("albums")) + \
             Pos("IN") + Band()) | \
            (Lemmas("what album do") + Band() +
             (Lemma("record") | Lemma("make")) + Question(Pos("."))) | \
            (Lemma("list") + Band() + Lemma("album"))

    def semantics(self, match):
        album = IsAlbum() + ProducedBy(match.band)
        name = NameOf(album)
        return name, "enum"

########NEW FILE########
__FILENAME__ = people
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
People related regex
"""


from refo import Plus, Question
from quepy.regex import Lemma, Lemmas, Pos, RegexTemplate, Particle
from quepy.semantics import HasKeyword
from semantics import IsPerson, LabelOf, DefinitionOf, \
                      BirthDateOf, BirthPlaceOf


class Person(Particle):
    regex = Plus(Pos("NN") | Pos("NNS") | Pos("NNP") | Pos("NNPS"))

    def semantics(self, match):
        name = match.words.tokens
        return IsPerson() + HasKeyword(name)


class WhoIs(RegexTemplate):
    """
    Ex: "Who is Tom Cruise?"
    """

    regex = Lemma("who") + Lemma("be") + Person() + \
        Question(Pos("."))

    def semantics(self, match):
        definition = DefinitionOf(match.person)
        return definition, "define"


class HowOldIsRegex(RegexTemplate):
    """
    Ex: "How old is Bob Dylan".
    """

    regex = Pos("WRB") + Lemma("old") + Lemma("be") + Person() + \
        Question(Pos("."))

    def semantics(self, match):
        birth_date = BirthDateOf(match.person)
        return birth_date, "age"


class WhereIsFromRegex(RegexTemplate):
    """
    Ex: "Where is Bill Gates from?"
    """

    regex = Lemmas("where be") + Person() + Lemma("from") + \
        Question(Pos("."))

    def semantics(self, match):
        birth_place = BirthPlaceOf(match.person)
        label = LabelOf(birth_place)

        return label, "enum"

########NEW FILE########
__FILENAME__ = regex
#!/usr/bin/env python

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>
# coding: utf-8

"""
Regex for DBpedia quepy.
"""

from refo import Group, Plus, Question
from quepy.semantics import HasKeyword, IsRelatedTo, HasType
from quepy.regex import Lemma, Pos, RegexTemplate, Token
from semantics import DefinitionOf, LabelOf, IsPlace, UTCof, LocationOf


# Import all the specific type related regex
from music import *
from movies import *
from people import *
from country import *
from tvshows import *
from writers import *


# Openings
LISTOPEN = Lemma("list") | Lemma("name")


class Thing(Particle):
    regex = Question(Pos("JJ")) + (Pos("NN") | Pos("NNP") | Pos("NNS")) |\
            Pos("VBN")

    def semantics(self, match):
        return HasKeyword(match.words.tokens)


class WhatIs(RegexTemplate):
    """
    Regex for questions like "What is a blowtorch
    Ex: "What is a car"
        "What is Seinfield?"
    """

    regex = Lemma("what") + Lemma("be") + Question(Pos("DT")) + \
        Thing() + Question(Pos("."))

    def semantics(self, match):
        label = DefinitionOf(match.thing)

        return label, "define"


class ListEntity(RegexTemplate):
    """
    Regex for questions like "List Microsoft software"
    """

    entity = Group(Pos("NNP"), "entity")
    target = Group(Pos("NN") | Pos("NNS"), "target")
    regex = LISTOPEN + entity + target

    def semantics(self, match):
        entity = HasKeyword(match.entity.tokens)
        target_type = HasKeyword(match.target.lemmas)
        target = HasType(target_type) + IsRelatedTo(entity)
        label = LabelOf(target)

        return label, "enum"


class WhatTimeIs(RegexTemplate):
    """
    Regex for questions about the time
    Ex: "What time is it in Cordoba"
    """

    nouns = Plus(Pos("NN") | Pos("NNS") | Pos("NNP") | Pos("NNPS"))
    place = Group(nouns, "place")
    openings = (Lemma("what") +
        ((Token("is") + Token("the") + Question(Lemma("current")) +
        Question(Lemma("local")) + Lemma("time")) |
        (Lemma("time") + Token("is") + Token("it")))) | \
               Lemma("time")
    regex = openings + Pos("IN") + place + Question(Pos("."))

    def semantics(self, match):
        place = HasKeyword(match.place.lemmas.title()) + IsPlace()
        utc_offset = UTCof(place)

        return utc_offset, "time"


class WhereIsRegex(RegexTemplate):
    """
    Ex: "where in the world is the Eiffel Tower"
    """

    thing = Group(Plus(Pos("IN") | Pos("NP") | Pos("NNP") | Pos("NNPS")),
                  "thing")
    regex = Lemma("where") + Question(Lemmas("in the world")) + Lemma("be") + \
        Question(Pos("DT")) + thing + Question(Pos("."))

    def semantics(self, match):
        thing = HasKeyword(match.thing.tokens)
        location = LocationOf(thing)
        location_name = LabelOf(location)

        return location_name, "enum"

########NEW FILE########
__FILENAME__ = semantics
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Semantics for DBpedia quepy.
"""

from quepy.semantics import FixedType, HasKeyword, FixedRelation, \
                            FixedDataRelation

# Setup the Keywords for this application
HasKeyword.relation = "rdfs:label"
HasKeyword.language = "en"


class IsPerson(FixedType):
    fixedtype = "foaf:Person"


class IsPlace(FixedType):
    fixedtype = "dbpedia:Place"


class IsCountry(FixedType):
    fixedtype = "dbpedia-owl:Country"


class IsBand(FixedType):
    fixedtype = "dbpedia-owl:Band"


class IsAlbum(FixedType):
    fixedtype = "dbpedia-owl:Album"


class IsTvShow(FixedType):
    fixedtype = "dbpedia-owl:TelevisionShow"


class IsMovie(FixedType):
    fixedtype = "dbpedia-owl:Film"


class HasShowName(FixedDataRelation):
    relation = "dbpprop:showName"
    language = "en"


class HasName(FixedDataRelation):
    relation = "dbpprop:name"
    language = "en"


class DefinitionOf(FixedRelation):
    relation = "rdfs:comment"
    reverse = True


class LabelOf(FixedRelation):
    relation = "rdfs:label"
    reverse = True


class UTCof(FixedRelation):
    relation = "dbpprop:utcOffset"
    reverse = True


class PresidentOf(FixedRelation):
    relation = "dbpprop:leaderTitle"
    reverse = True


class IncumbentOf(FixedRelation):
    relation = "dbpprop:incumbent"
    reverse = True


class CapitalOf(FixedRelation):
    relation = "dbpedia-owl:capital"
    reverse = True


class LanguageOf(FixedRelation):
    relation = "dbpprop:officialLanguages"
    reverse = True


class PopulationOf(FixedRelation):
    relation = "dbpprop:populationCensus"
    reverse = True


class IsMemberOf(FixedRelation):
    relation = "dbpedia-owl:bandMember"
    reverse = True


class ActiveYears(FixedRelation):
    relation = "dbpprop:yearsActive"
    reverse = True


class MusicGenereOf(FixedRelation):
    relation = "dbpedia-owl:genre"
    reverse = True


class ProducedBy(FixedRelation):
    relation = "dbpedia-owl:producer"


class BirthDateOf(FixedRelation):
    relation = "dbpprop:birthDate"
    reverse = True


class BirthPlaceOf(FixedRelation):
    relation = "dbpedia-owl:birthPlace"
    reverse = True


class ReleaseDateOf(FixedRelation):
    relation = "dbpedia-owl:releaseDate"
    reverse = True


class StarsIn(FixedRelation):
    relation = "dbpprop:starring"
    reverse = True


class NumberOfEpisodesIn(FixedRelation):
    relation = "dbpedia-owl:numberOfEpisodes"
    reverse = True


class ShowNameOf(FixedRelation):
    relation = "dbpprop:showName"
    reverse = True


class HasActor(FixedRelation):
    relation = "dbpprop:starring"


class CreatorOf(FixedRelation):
    relation = "dbpprop:creator"
    reverse = True


class NameOf(FixedRelation):
    relation = "foaf:name"
    # relation = "dbpprop:name"
    reverse = True


class DirectedBy(FixedRelation):
    relation = "dbpedia-owl:director"


class DirectorOf(FixedRelation):
    relation = "dbpedia-owl:director"
    reverse = True


class DurationOf(FixedRelation):
    # DBpedia throws an error if the relation it's
    # dbpedia-owl:Work/runtime so we expand the prefix
    # by giving the whole URL.
    relation = "<http://dbpedia.org/ontology/Work/runtime>"
    reverse = True


class HasAuthor(FixedRelation):
    relation = "dbpedia-owl:author"


class AuthorOf(FixedRelation):
    relation = "dbpedia-owl:author"
    reverse = True


class IsBook(FixedType):
    fixedtype = "dbpedia-owl:Book"


class LocationOf(FixedRelation):
    relation = "dbpedia-owl:location"
    reverse = True

########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Settings.
"""

# Freeling config
USE_FREELING = False
FREELING_CMD = ""  # Only set if USE_FREELING it's True

# NLTK config
NLTK_DATA_PATH = []  # List of paths with NLTK data

# Encoding config
DEFAULT_ENCODING = "utf-8"

# Sparql config
SPARQL_PREAMBLE = u"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX quepy: <http://www.machinalis.com/quepy#>
PREFIX dbpedia: <http://dbpedia.org/ontology/>
PREFIX dbpprop: <http://dbpedia.org/property/>
PREFIX dbpedia-owl: <http://dbpedia.org/ontology/>
"""

########NEW FILE########
__FILENAME__ = tvshows
#!/usr/bin/env python
# coding: utf-8

"""
Tv Shows related regex.
"""

from refo import Plus, Question
from quepy.semantics import HasKeyword
from quepy.regex import Lemma, Lemmas, Pos, RegexTemplate, Particle
from semantics import IsTvShow, ReleaseDateOf, IsPerson, StarsIn, LabelOf, \
                      HasShowName, NumberOfEpisodesIn, HasActor, ShowNameOf, \
                      CreatorOf

nouns = Plus(Pos("NN") | Pos("NNS") | Pos("NNP") | Pos("NNPS"))


class TvShow(Particle):
    regex = Plus(Question(Pos("DT")) + nouns)

    def semantics(self, match):
        name = match.words.tokens
        return IsTvShow() + HasShowName(name)


class Actor(Particle):
    regex = nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsPerson() + HasKeyword(name)


# FIXME: clash with movies release regex
class ReleaseDateRegex(RegexTemplate):
    """
    Ex: when was Friends release?
    """

    regex = Lemmas("when be") + TvShow() + Lemma("release") + \
        Question(Pos("."))

    def semantics(self, match):
        release_date = ReleaseDateOf(match.tvshow)
        return release_date, "literal"


class CastOfRegex(RegexTemplate):
    """
    Ex: "What is the cast of Friends?"
        "Who works in Breaking Bad?"
        "List actors of Seinfeld"
    """

    regex = (Question(Lemmas("what be") + Pos("DT")) +
             Lemma("cast") + Pos("IN") + TvShow() + Question(Pos("."))) | \
            (Lemmas("who works") + Pos("IN") + TvShow() +
             Question(Pos("."))) | \
            (Lemmas("list actor") + Pos("IN") + TvShow())

    def semantics(self, match):
        actor = IsPerson() + StarsIn(match.tvshow)
        name = LabelOf(actor)
        return name, "enum"


class ListTvShows(RegexTemplate):
    """
    Ex: "List TV shows"
    """

    regex = Lemmas("list tv show")

    def semantics(self, match):
        show = IsTvShow()
        label = LabelOf(show)
        return label, "enum"


class EpisodeCountRegex(RegexTemplate):
    """
    Ex: "How many episodes does Seinfeld have?"
        "Number of episodes of Seinfeld"
    """

    regex = ((Lemmas("how many episode do") + TvShow() + Lemma("have")) |
             (Lemma("number") + Pos("IN") + Lemma("episode") +
              Pos("IN") + TvShow())) + \
            Question(Pos("."))

    def semantics(self, match):
        number_of_episodes = NumberOfEpisodesIn(match.tvshow)
        return number_of_episodes, "literal"


class ShowsWithRegex(RegexTemplate):
    """
    Ex: "List shows with Hugh Laurie"
        "In what shows does Jennifer Aniston appears?"
        "Shows with Matt LeBlanc"
    """

    regex = (Lemmas("list show") + Pos("IN") + Actor()) | \
            (Pos("IN") + (Lemma("what") | Lemma("which")) + Lemmas("show do") +
             Actor() + (Lemma("appear") | Lemma("work")) +
             Question(Pos("."))) | \
            ((Lemma("show") | Lemma("shows")) + Pos("IN") + Actor())

    def semantics(self, match):
        show = IsTvShow() + HasActor(match.actor)
        show_name = ShowNameOf(show)
        return show_name, "enum"


class CreatorOfRegex(RegexTemplate):
    """
    Ex: "Who is the creator of Breaking Bad?"
    """

    regex = Question(Lemmas("who be") + Pos("DT")) + \
        Lemma("creator") + Pos("IN") + TvShow() + Question(Pos("."))

    def semantics(self, match):
        creator = CreatorOf(match.tvshow)
        label = LabelOf(creator)
        return label, "enum"

########NEW FILE########
__FILENAME__ = writers
#!/usr/bin/env python
# coding: utf-8

# Copyright (c) 2012, Machinalis S.R.L.
# This file is part of quepy and is distributed under the Modified BSD License.
# You should have received a copy of license in the LICENSE file.
#
# Authors: Rafael Carrascosa <rcarrascosa@machinalis.com>
#          Gonzalo Garcia Berrotaran <ggarcia@machinalis.com>

"""
Writers related regex.
"""


from refo import Plus, Question
from quepy.semantics import HasKeyword
from quepy.regex import Lemma, Lemmas, Pos, RegexTemplate, Particle
from semantics import IsBook, HasAuthor, AuthorOf, IsPerson, NameOf


nouns = Plus(Pos("DT") | Pos("IN") | Pos("NN") | Pos("NNS") |
             Pos("NNP") | Pos("NNPS"))


class Book(Particle):
    regex = nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsBook() + HasKeyword(name)


class Author(Particle):
    regex = nouns

    def semantics(self, match):
        name = match.words.tokens
        return IsPerson() + HasKeyword(name)


class WhoWroteRegex(RegexTemplate):
    """
    Ex: "who wrote The Little Prince?"
        "who is the author of A Game Of Thrones?"
    """

    regex = ((Lemmas("who write") + Book()) |
             (Question(Lemmas("who be") + Pos("DT")) +
              Lemma("author") + Pos("IN") + Book())) + \
            Question(Pos("."))

    def semantics(self, match):
        author = NameOf(IsPerson() + AuthorOf(match.book))
        return author, "literal"


class BooksByAuthorRegex(RegexTemplate):
    """
    Ex: "list books by George Orwell"
        "which books did Suzanne Collins wrote?"
    """

    regex = (Question(Lemma("list")) + Lemmas("book by") + Author()) | \
            ((Lemma("which") | Lemma("what")) + Lemmas("book do") +
             Author() + Lemma("write") + Question(Pos(".")))

    def semantics(self, match):
        book = IsBook() + HasAuthor(match.author)
        book_name = NameOf(book)
        return book_name, "enum"

########NEW FILE########
__FILENAME__ = search

########NEW FILE########
__FILENAME__ = wolfram
#!/usr/bin/python
# -*- coding: utf-8 -*-

import wolframalpha


class Wolfram:
    def __init__(self, tts, key):
            self.tts = tts
            self.key = key

    def process(self, job):
        if job.get_is_processed():
            return False
            
        print "Checking for API key..."

        if not self.key:
            self.tts.say("I can't contact the knowledge base without an API key. Set one in an environment variable.")
            return False

        self.say(self.query(job.raw(), self.key))
        job.is_processed = True

    def query(self, phrase, key):
        print "Querying Wolfram"
        client = wolframalpha.Client(key)
        res = client.query(phrase)

        print "Parsing response"
        try:
            if len(res.pods) == 0:
                # a bit messy but will do for now
                raise StopIteration()

            for pod in res.results:
                if hasattr(pod.text, "encode"):
                    # festival tts didn't recognise the utf8 degrees sign so we convert it to words
                    # there's probably more we need to add here
                    # convert to ascii too to prevent moans
                    return pod.text.replace(u"°", ' degrees ').encode('ascii', 'ignore')
                else:
                    break

            # TODO offer to display the result instead of a display is detected
            return "I found a result but could not read it out to you. It could be a map, image or table."

        except StopIteration:
            return "Sorry, I couldn't find any results for the query, '" + phrase + "'"

    def say(self, text):
        return self.tts.say(text)

########NEW FILE########
__FILENAME__ = exception
class NotUnderstoodException(Exception):
    pass

class NoResultsFoundException(Exception):
    pass

########NEW FILE########
__FILENAME__ = microphone

from array import array
from struct import pack

import tempfile
import pyaudio
import sys
import wave
import os


class Microphone:

    def listen(self):
        print "Recording..."

        recording_rate = self.rate()

        # execute recording
        (_, recording_wav_filename) = tempfile.mkstemp('.wav')
        self.do_wav_recording(recording_wav_filename, recording_rate)

        self.recordedWavFilename = recording_wav_filename

        return self.recordedWavFilename

    def filename(self):
        return self.recordedWavFilename

    def rate(self):
        return 44100

    def housekeeping(self):
        os.remove(self.recordedWavFilename)

    def is_silent(self, sound_data, threshold):
        return max(sound_data) < threshold

    def add_silence(self, sound_data, seconds, recording_rate):
        r = array('h', [0 for i in xrange(int(seconds*recording_rate))])
        r.extend(sound_data)
        r.extend([0 for i in xrange(int(seconds*recording_rate))])
        return r

    def do_wav_recording(self, recording_filename, recording_rate):
        THRESHOLD = 2000            # Set threshold of volume to consider as silence
        NUM_SILENT = 40             # Set amt of silence to accept before ending recording
        CHUNK = 1024    
        FORMAT = pyaudio.paInt16
        CHANNELS = 2

        if sys.platform == 'darwin':
            CHANNELS = 1

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=recording_rate,
                        input=True,
                        frames_per_buffer=CHUNK)

        num_silent = 0              
        speech_started = False       
        r = array('h')

        print("* recording")

        while 1:
            sound_data = array('h', stream.read(CHUNK))
            if sys.byteorder == 'big':
                sound_data.byteswap()
            r.extend(sound_data)

            silent = self.is_silent(sound_data, THRESHOLD)

            if silent and speech_started:
                num_silent += 1
            elif not silent and not speech_started:
                speech_started = True

            if speech_started and num_silent > NUM_SILENT:
                break

        print("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()

        data = self.add_silence(r, 0.5, recording_rate)
        data = pack('<' + ('h'*len(data)), *data)

        wf = wave.open(recording_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(recording_rate)
        wf.writeframes(b''.join(data))
        wf.close()

########NEW FILE########
__FILENAME__ = listen
#!/usr/bin/python
# -*- coding: utf-8 -*-

from inputs.microphone import Microphone
from actions.wolfram import Wolfram
from actions.db import DBPedia
from ex.exception import NotUnderstoodException

import sys
import os
import tts
import stt


class Job:
    def __init__(self, raw):
            self.raw_text = raw
            self.is_processed = False

    def get_is_processed(self):
        return self.is_processed

    def raw(self):
        return self.raw_text

    def naturalLanguage(self):
        # parse the raw text into semantic using nltk
        return self.raw


def main():
    if sys.platform == 'darwin':
        speaker = tts.OSX()
    else:
        # n.b. at the time of writing, this doesnt work on OSX
        speaker = tts.Google()

    try:
        audioInput = Microphone()

        audioInput.listen()

        speaker.say("Searching...")

        speech_to_text = stt.Google(audioInput)

        # speech_to_text = stt.Dummy('who was winston churchill?')

        job = Job(speech_to_text.get_text())

        plugins = {
            "db": DBPedia(speaker),
            "Wolfram": Wolfram(speaker, os.environ.get('WOLFRAM_API_KEY'))
        }

        for plugin in plugins:
            plugins[plugin].process(job)

        if not job.get_is_processed():
            speaker.say("Sorry, I couldn't find any results for the query, '" + job.raw() + "'.")

    except NotUnderstoodException:
        speaker.say("Sorry, I couldn't understand what you said.")


if __name__ == "__main__":
    main()



########NEW FILE########
__FILENAME__ = dummy
from exceptions import *


class Dummy:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        if not self.text is None:
            return self.text

########NEW FILE########
__FILENAME__ = google
import tempfile
import audiotools
import requests
import json
import os

from ex.exception import NotUnderstoodException


class Google:
    def __init__(self, audio, rate=44100):
            self.audio = audio
            self.recordingRate = audio.rate() if audio.rate() else rate
            self.text = None

    def get_text(self):
        if not self.text is None:
            return self.text

        print "Converting to FLAC"
        (_, recording_flac_filename) = tempfile.mkstemp('.flac')
        recording_wav = audiotools.open(self.audio.filename())
        recording_wav.convert(recording_flac_filename,
                              audiotools.FlacAudio,)
                              #compression=audiotools.FlacAudio.COMPRESSION_MODES[8],
                              #progress=False)

        # turn the audio into useful text
        print "Sending to Google"
        google_speech_url = "http://www.google.com/speech-api/v1/recognize?lang=en"
        headers = {'Content-Type': 'audio/x-flac; rate= %d;' % self.recordingRate}
        recording_flac_data = open(recording_flac_filename, 'rb').read()
        r = requests.post(google_speech_url, data=recording_flac_data, headers=headers)

        # housekeeping
        os.remove(recording_flac_filename)
        self.audio.housekeeping()

        # grab the response
        response = r.text

        if not 'hypotheses' in response:
            raise NotUnderstoodException()

        # we are only interested in the most likely utterance
        phrase = json.loads(response)['hypotheses'][0]['utterance']
        print "Heard: " + phrase
        return str(phrase)

########NEW FILE########
__FILENAME__ = festival
import os


class Festival:

    def say(self, text):
        print "Saying: " + text
        os.system('echo "%s" | festival --tts' % text)

########NEW FILE########
__FILENAME__ = google
import urllib
import tempfile
import audiotools
import requests
import os
import pyaudio
import wave


class Google:

    def say(self, text):
        print "Google Speaking: " + text

        urlencoded_words = urllib.quote_plus(text)
        (_, tts_mp3_filename) = tempfile.mkstemp('.mp3')
        request_url = "http://translate.google.com/translate_tts?ie=utf-8&tl=en&q=%s" % urlencoded_words
        r = requests.get(request_url, headers={'User-agent': 'Mozilla'})
        f = open(tts_mp3_filename, 'wb')
        f.write(r.content)
        f.close()

        print "Got wav"

        print "converting to WAV"

        (_, tts_wav_filename) = tempfile.mkstemp('.wav')
        recording_wav = audiotools.open(tts_mp3_filename)
        recording_wav.convert(tts_wav_filename, audiotools.WaveAudio,)
        self.play_wav(tts_wav_filename)
        os.remove(tts_mp3_filename)

    def play_wav(self, filename):
        CHUNK = 1024
        wf = wave.open(filename, 'rb')

        # instantiate PyAudio (1)
        p = pyaudio.PyAudio()

        # open stream (2)
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # read data
        data = wf.readframes(CHUNK)

        # play stream (3)
        while data != '':
            stream.write(data)
            data = wf.readframes(CHUNK)

        # stop stream (4)
        stream.stop_stream()
        stream.close()

        # close PyAudio (5)
        p.terminate()

########NEW FILE########
__FILENAME__ = osx
import os


class OSX:

    def say(self, text):
        print "Saying: " + text
        os.system('say "%s"' % text)

########NEW FILE########
