__FILENAME__ = database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relation, backref
import sqlalchemy
try:
    from database_settings import CONNECTION_STRING
except ImportError:
    CONNECTION_STRING = "sqlite:///imdbapi.db"

Base = declarative_base()

class Show(Base):
    __tablename__ = 'shows'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Unicode(200))
    year = sqlalchemy.Column(sqlalchemy.Integer)

    def __init__(self, name, year):
        self.name = name
        self.year = year

    def __repr__(self):
        return "<Show('%s','%s')>" % (self.name, self.year)

sqlalchemy.Index('idx_show_name_year', Show.name, Show.year)

class Episode(Base):
    __tablename__ = 'episodes'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    show_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('shows.id'), index=True)
    name = sqlalchemy.Column(sqlalchemy.Unicode(200), index=True)
    season = sqlalchemy.Column(sqlalchemy.Integer)
    number = sqlalchemy.Column(sqlalchemy.Integer)

    show = relation(Show, backref='episodes', order_by=id)

    def __init__(self, show, name, season, number):
        self.show = show
        self.name = name
        self.season = season
        self.number = number

    def __repr__(self):
        return "<Episode('%s.%s','%s')>" % (self.season, self.number, self.name)

class Stats(Base):
    __tablename__ = 'stats'
    key = sqlalchemy.Column(sqlalchemy.Unicode(200), index=True, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.Integer)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return "<Stats('%s','%s')>" % (self.key, self.value)


def init_db(transactional=False):
    engine = sqlalchemy.create_engine(CONNECTION_STRING)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, transactional=transactional)
    session = Session()
    return session

if __name__ == "__main__":
    init_db()

########NEW FILE########
__FILENAME__ = imdbapi
from database import Show, Episode, Stats, init_db
from bottle import route, run, request, template, response
import simplejson
import sqlalchemy
import urllib

session = init_db()

def get_data(show_name, show_year=None):
    if not show_name or (show_year and not show_year.isdigit()):
        return None

    show = session.query(Show).filter(Show.name.like(show_name))
    if show_year:
        show = show.filter(Show.year==int(show_year))
    try:
        single_show = show.one()
    except sqlalchemy.orm.exc.NoResultFound:
        return None
    except sqlalchemy.orm.exc.MultipleResultsFound:
        shows = show.order_by(Show.name)[:15]
        show_list = [{"name": show.name, "year": show.year} for show in shows]
        return {"shows": show_list}

    episodes = []
    for episode in single_show.episodes:
        episodes.append({"name": episode.name, "number": episode.number, "season": episode.season})
    return {single_show.name: {"year": single_show.year, "episodes": episodes}}

@route('/json/')
def json():
    response.header['Content-Type'] = 'application/json'
    show_name = request.GET.get("name", None)
    show_year = request.GET.get("year", None)
    callback = request.GET.get("callback", None)
    data = simplejson.dumps(get_data(show_name, show_year))
    session.close()
    if callback:
        data = "%s(%s)" % (callback, data)
    return data

@route('/js/')
def js():
    show_name = request.GET.get("name", None)
    show_year = request.GET.get("year", None)
    callback = request.GET.get("callback", None)
    data = simplejson.dumps(get_data(show_name, show_year))
    session.close()
    if callback:
        data = "%s(%s)" % (callback, data)
    return data

@route('/')
def index():
    return template("index")

if __name__ == "__main__":
    run(host='localhost', port=8000)

########NEW FILE########
__FILENAME__ = importer
from __future__ import with_statement
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relation, backref
from database import Show, Episode, init_db

import codecs
import re
import sqlalchemy

session = init_db(transactional=True)

def import_data(filename):
    """Import episode names and ratings from a file."""
    regex = re.compile(""""(?P<show_name>.*?)"\s+\((?P<year>\d+)(?:|/.*?)\)\s+\{(?P<episode_name>.*?)\s?\(\#(?P<season_no>\d+)\.(?P<episode_no>\d+)\)\}""")

    with codecs.open(filename, "r", "latin-1") as ratings:
        # Generate all the lines that matched.
        matches = (match for match in (regex.search(line.strip()) for line in ratings) if match)
        counter = 0
        for match in matches:
            counter += 1
            if not counter % 100:
                print counter
            episode = {}
            for field in ["show_name", "year", "episode_name", "episode_no", "season_no"]:
                episode[field] = match.group(field)

            # If the episode has no name it is given the same name as on imdb.com for consistency.
            if not episode["episode_name"]:
                episode["episode_name"] = "Episode #%s.%s" % (episode["season_no"], episode["episode_no"])

            try:
                show = session.query(Show).filter_by(name=episode["show_name"], year=episode["year"]).one()
            except sqlalchemy.orm.exc.NoResultFound:
                show = Show(episode["show_name"], episode["year"])
                session.add(show)

            try:
                episode = session.query(Episode).filter_by(name=episode["episode_name"], show=show).one()
            except sqlalchemy.orm.exc.NoResultFound:
                episode = Episode(show, episode["episode_name"], episode["season_no"], episode["episode_no"])
                session.add(episode)

    #session.commit()

if __name__ == "__main__":
    import_data("movies.list")


########NEW FILE########
