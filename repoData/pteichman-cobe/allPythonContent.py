__FILENAME__ = bot
# Copyright (C) 2014 Peter Teichman

import irc.client
import logging
import re

log = logging.getLogger("cobe.bot")


class Bot(irc.client.SimpleIRCClient):
    def __init__(self, brain, nick, channel, log_channel, ignored_nicks,
                 only_nicks):
        irc.client.SimpleIRCClient.__init__(self)

        self.brain = brain
        self.nick = nick
        self.channel = channel
        self.log_channel = log_channel
        self.ignored_nicks = ignored_nicks
        self.only_nicks = only_nicks

        if log_channel is not None:
            # set up a new logger
            handler = IrcLogHandler(self.connection, log_channel)
            handler.setLevel(logging.DEBUG)

            logging.root.addHandler(handler)

    def _dispatcher(self, c, e):
        log.debug("on_%s %s", e.type, (e.source, e.target, e.arguments))
        irc.client.SimpleIRCClient._dispatcher(self, c, e)

    def _delayed_check(self, delay=120):
        self.connection.execute_delayed(delay, self._check_connection)

    def _check_connection(self):
        conn = self.connection
        if conn.is_connected():
            log.debug("connection: ok")
            self._delayed_check()
            return

        try:
            log.debug("reconnecting to %s:%p", conn.server, conn.port)
            conn.connect(conn.server, conn.port, conn.nickname, conn.password,
                         conn.username, conn.ircname, conn.localaddress,
                         conn.localport)
        except irc.client.ServerConnectionError:
            log.info("failed reconnection, rescheduling", exc_info=True)
            self._delayed_check()

    def on_disconnect(self, conn, event):
        self._check_connection()

    def on_endofmotd(self, conn, event):
        self._delayed_check()
        self.connection.join(self.channel)

        if self.log_channel:
            self.connection.join(self.log_channel)

    def on_pubmsg(self, conn, event):
        user = irc.client.NickMask(event.source).nick

        if event.target == self.log_channel:
            # ignore input in the log channel
            return

        # ignore specified nicks
        if self.ignored_nicks and user in self.ignored_nicks:
            return

        # only respond on channels
        if not irc.client.is_channel(event.target):
            return

        msg = event.arguments[0].strip()

        # strip pasted nicks from messages
        msg = re.sub("<\S+>\s+", "", msg)

        # strip kibot style quotes from messages
        match = re.match("\"(.*)\" --\S+, \d+-\S+\d+.", msg)
        if match:
            msg = match.group(1)

        # look for messages directed to a user
        match = re.match("\s*(\S+)[,:]\s+(.*?)\s*$", msg)

        if match:
            to = match.group(1)
            text = match.group(2)
        else:
            to = None
            text = msg

        if not self.only_nicks or user in self.only_nicks:
            self.brain.learn(text)

        if to == conn.nickname:
            reply = self.brain.reply(text)
            conn.privmsg(event.target, "%s: %s" % (user, reply))


class Runner:
    def run(self, brain, args):
        bot = Bot(brain, args.nick, args.channel, args.log_channel,
                  args.ignored_nicks, args.only_nicks)
        bot.connect(args.server, args.port, args.nick)
        log.info("connected to %s:%s", args.server, args.port)

        bot.start()


class IrcLogHandler(logging.Handler):
    def __init__(self, connection, channel):
        logging.Handler.__init__(self)

        self.connection = connection
        self.channel = channel

    def emit(self, record):
        conn = self.connection

        if conn.is_connected():
            conn.privmsg(self.channel, record.getMessage().encode("utf-8"))

########NEW FILE########
__FILENAME__ = brain
# Copyright (C) 2013 Peter Teichman

import collections
import itertools
import logging
import math
import operator
import os
import random
import re
import sqlite3
import time
import types

from .instatrace import trace, trace_ms, trace_us
from . import scoring
from . import tokenizers

log = logging.getLogger("cobe")


class CobeError(Exception):
    pass


class Brain:
    """The main interface for Cobe."""

    # use an empty string to denote the start/end of a chain
    END_TOKEN = ""

    # use a magic token id for (single) whitespace, so space is never
    # in the tokens table
    SPACE_TOKEN_ID = -1

    def __init__(self, filename):
        """Construct a brain for the specified filename. If that file
        doesn't exist, it will be initialized with the default brain
        settings."""
        if not os.path.exists(filename):
            log.info("File does not exist. Assuming defaults.")
            Brain.init(filename)

        with trace_us("Brain.connect_us"):
            self.graph = graph = Graph(sqlite3.connect(filename))

        version = graph.get_info_text("version")
        if version != "2":
            raise CobeError("cannot read a version %s brain" % version)

        self.order = int(graph.get_info_text("order"))

        self.scorer = scoring.ScorerGroup()
        self.scorer.add_scorer(1.0, scoring.CobeScorer())

        tokenizer_name = graph.get_info_text("tokenizer")
        if tokenizer_name == "MegaHAL":
            self.tokenizer = tokenizers.MegaHALTokenizer()
        else:
            self.tokenizer = tokenizers.CobeTokenizer()

        self.stemmer = None
        stemmer_name = graph.get_info_text("stemmer")

        if stemmer_name is not None:
            try:
                self.stemmer = tokenizers.CobeStemmer(stemmer_name)
                log.debug("Initialized a stemmer: %s" % stemmer_name)
            except Exception, e:
                log.error("Error creating stemmer: %s", str(e))

        self._end_token_id = \
            graph.get_token_by_text(self.END_TOKEN, create=True)

        self._end_context = [self._end_token_id] * self.order
        self._end_context_id = graph.get_node_by_tokens(self._end_context)

        self._learning = False

    def start_batch_learning(self):
        """Begin a series of batch learn operations. Data will not be
        committed to the database until stop_batch_learning is
        called. Learn text using the normal learn(text) method."""
        self._learning = True

        self.graph.cursor().execute("PRAGMA journal_mode=memory")
        self.graph.drop_reply_indexes()

    def stop_batch_learning(self):
        """Finish a series of batch learn operations."""
        self._learning = False

        self.graph.commit()
        self.graph.cursor().execute("PRAGMA journal_mode=truncate")
        self.graph.ensure_indexes()

    def del_stemmer(self):
        self.stemmer = None

        self.graph.delete_token_stems()

        self.graph.set_info_text("stemmer", None)
        self.graph.commit()

    def set_stemmer(self, language):
        self.stemmer = tokenizers.CobeStemmer(language)

        self.graph.delete_token_stems()
        self.graph.update_token_stems(self.stemmer)

        self.graph.set_info_text("stemmer", language)
        self.graph.commit()

    def learn(self, text):
        """Learn a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        trace("Brain.learn_input_token_count", len(tokens))

        self._learn_tokens(tokens)

    def _to_edges(self, tokens):
        """This is an iterator that returns the nodes of our graph:
"This is a test" -> "None This" "This is" "is a" "a test" "test None"

Each is annotated with a boolean that tracks whether whitespace was
found between the two tokens."""
        # prepend self.order Nones
        chain = self._end_context + tokens + self._end_context

        has_space = False

        context = []

        for i in xrange(len(chain)):
            context.append(chain[i])

            if len(context) == self.order:
                if chain[i] == self.SPACE_TOKEN_ID:
                    context.pop()
                    has_space = True
                    continue

                yield tuple(context), has_space

                context.pop(0)
                has_space = False

    def _to_graph(self, contexts):
        """This is an iterator that returns each edge of our graph
with its two nodes"""
        prev = None

        for context in contexts:
            if prev is None:
                prev = context
                continue

            yield prev[0], context[1], context[0]
            prev = context

    def _learn_tokens(self, tokens):
        token_count = len([token for token in tokens if token != " "])
        if token_count < 3:
            return

        # create each of the non-whitespace tokens
        token_ids = []
        for text in tokens:
            if text == " ":
                token_ids.append(self.SPACE_TOKEN_ID)
                continue

            token_id = self.graph.get_token_by_text(text, create=True,
                                                    stemmer=self.stemmer)
            token_ids.append(token_id)

        edges = list(self._to_edges(token_ids))

        prev_id = None
        for prev, has_space, next in self._to_graph(edges):
            if prev_id is None:
                prev_id = self.graph.get_node_by_tokens(prev)
            next_id = self.graph.get_node_by_tokens(next)

            self.graph.add_edge(prev_id, next_id, has_space)
            prev_id = next_id

        if not self._learning:
            self.graph.commit()

    def reply(self, text, loop_ms=500, max_len=None):
        """Reply to a string of text. If the input is not already
        Unicode, it will be decoded as utf-8."""
        if type(text) != types.UnicodeType:
            # Assume that non-Unicode text is encoded as utf-8, which
            # should be somewhat safe in the modern world.
            text = text.decode("utf-8", "ignore")

        tokens = self.tokenizer.split(text)
        input_ids = map(self.graph.get_token_by_text, tokens)

        # filter out unknown words and non-words from the potential pivots
        pivot_set = self._filter_pivots(input_ids)

        # Conflate the known ids with the stems of their words
        if self.stemmer is not None:
            self._conflate_stems(pivot_set, tokens)

        # If we didn't recognize any word tokens in the input, pick
        # something random from the database and babble.
        if len(pivot_set) == 0:
            pivot_set = self._babble()

        score_cache = {}

        best_score = -1.0
        best_reply = None

        # Loop for approximately loop_ms milliseconds. This can either
        # take more (if the first reply takes a long time to generate)
        # or less (if the _generate_replies search ends early) time,
        # but it should stay roughly accurate.
        start = time.time()
        end = start + loop_ms * 0.001
        count = 0

        all_replies = []

        _start = time.time()
        for edges, pivot_node in self._generate_replies(pivot_set):
            reply = Reply(self.graph, tokens, input_ids, pivot_node, edges)

            if max_len and self._too_long(max_len, reply):
                continue

            key = reply.edge_ids
            if key not in score_cache:
                with trace_us("Brain.evaluate_reply_us"):
                    score = self.scorer.score(reply)
                    score_cache[key] = score
            else:
                # skip scoring, we've already seen this reply
                score = -1

            if score > best_score:
                best_reply = reply
                best_score = score

            # dump all replies to the console if debugging is enabled
            if log.isEnabledFor(logging.DEBUG):
                all_replies.append((score, reply))

            count += 1
            if time.time() > end:
                break

        if best_reply is None:
            # we couldn't find any pivot words in _babble(), so we're
            # working with an essentially empty brain. Use the classic
            # MegaHAL reply:
            return "I don't know enough to answer you yet!"

        _time = time.time() - _start

        if best_reply is None:
            # we couldn't find any pivot words in _babble(), so we're
            # working with an essentially empty brain. Use the classic
            # MegaHAL reply:
            return "I don't know enough to answer you yet!"

        self.scorer.end(best_reply)

        if log.isEnabledFor(logging.DEBUG):
            replies = [(score, reply.to_text())
                       for score, reply in all_replies]
            replies.sort()

            for score, text in replies:
                log.debug("%f %s", score, text)

        trace("Brain.reply_input_token_count", len(tokens))
        trace("Brain.known_word_token_count", len(pivot_set))

        trace("Brain.reply_us", _time)
        trace("Brain.reply_count", count, _time)
        trace("Brain.best_reply_score", int(best_score * 1000))
        trace("Brain.best_reply_length", len(best_reply.edge_ids))

        log.debug("made %d replies (%d unique) in %f seconds"
                  % (count, len(score_cache), _time))

        if len(text) > 60:
            msg = text[0:60] + "..."
        else:
            msg = text

        log.info("[%s] %d %f", msg, count, best_score)

        # look up the words for these tokens
        with trace_us("Brain.reply_words_lookup_us"):
            text = best_reply.to_text()

        return text

    def _too_long(self, max_len, reply):
        text = reply.to_text()
        if len(text) > max_len:
            log.debug("over max_len [%d]: %s", len(text), text)
            return True

    def _conflate_stems(self, pivot_set, tokens):
        for token in tokens:
            stem_ids = self.graph.get_token_stem_id(self.stemmer.stem(token))
            if not stem_ids:
                continue

            # add the tuple of stems to the pivot set, and then
            # remove the individual token_ids
            pivot_set.add(tuple(stem_ids))
            pivot_set.difference_update(stem_ids)

    def _babble(self):
        token_ids = []
        for i in xrange(5):
            # Generate a few random tokens that can be used as pivots
            token_id = self.graph.get_random_token()

            if token_id is not None:
                token_ids.append(token_id)

        return set(token_ids)

    def _filter_pivots(self, pivots):
        # remove pivots that might not give good results
        tokens = set(filter(None, pivots))

        filtered = self.graph.get_word_tokens(tokens)
        if not filtered:
            filtered = self.graph.get_tokens(tokens) or []

        return set(filtered)

    def _pick_pivot(self, pivot_ids):
        pivot = random.choice(tuple(pivot_ids))

        if type(pivot) is types.TupleType:
            # the input word was stemmed to several things
            pivot = random.choice(pivot)

        return pivot

    def _generate_replies(self, pivot_ids):
        if not pivot_ids:
            return

        end = self._end_context_id
        graph = self.graph
        search = graph.search_random_walk

        # Cache all the trailing and beginning sentences we find from
        # each random node we search. Since the node is a full n-tuple
        # context, we can combine any pair of next_cache[node] and
        # prev_cache[node] and get a new reply.
        next_cache = collections.defaultdict(set)
        prev_cache = collections.defaultdict(set)

        while pivot_ids:
            # generate a reply containing one of token_ids
            pivot_id = self._pick_pivot(pivot_ids)
            node = graph.get_random_node_with_token(pivot_id)

            parts = itertools.izip_longest(search(node, end, 1),
                                           search(node, end, 0),
                                           fillvalue=None)

            for next, prev in parts:
                if next:
                    next_cache[node].add(next)
                    for p in prev_cache[node]:
                        yield p + next, node

                if prev:
                    prev = tuple(reversed(prev))
                    prev_cache[node].add(prev)
                    for n in next_cache[node]:
                        yield prev + n, node

    @staticmethod
    def init(filename, order=3, tokenizer=None):
        """Initialize a brain. This brain's file must not already exist.

Keyword arguments:
order -- Order of the forward/reverse Markov chains (integer)
tokenizer -- One of Cobe, MegaHAL (default Cobe). See documentation
             for cobe.tokenizers for details. (string)"""
        log.info("Initializing a cobe brain: %s" % filename)

        if tokenizer is None:
            tokenizer = "Cobe"

        if tokenizer not in ("Cobe", "MegaHAL"):
            log.info("Unknown tokenizer: %s. Using CobeTokenizer", tokenizer)
            tokenizer = "Cobe"

        graph = Graph(sqlite3.connect(filename))

        with trace_us("Brain.init_time_us"):
            graph.init(order, tokenizer)


class Reply:
    """Provide useful support for scoring functions"""
    def __init__(self, graph, tokens, token_ids, pivot_node, edge_ids):
        self.graph = graph
        self.tokens = tokens
        self.token_ids = token_ids
        self.pivot_node = pivot_node
        self.edge_ids = edge_ids
        self.text = None

    def to_text(self):
        if self.text is None:
            parts = []
            for word, has_space in map(self.graph.get_text_by_edge,
                                       self.edge_ids):
                parts.append(word)
                if has_space:
                    parts.append(" ")

            self.text = "".join(parts)

        return self.text


class Graph:
    """A special-purpose graph class, stored in a sqlite3 database"""
    def __init__(self, conn, run_migrations=True):
        self._conn = conn
        conn.row_factory = sqlite3.Row

        if self.is_initted():
            if run_migrations:
                self._run_migrations()

            self.order = int(self.get_info_text("order"))

            self._all_tokens = ",".join(["token%d_id" % i
                                         for i in xrange(self.order)])
            self._all_tokens_args = " AND ".join(
                ["token%d_id = ?" % i for i in xrange(self.order)])
            self._all_tokens_q = ",".join(["?" for i in xrange(self.order)])
            self._last_token = "token%d_id" % (self.order - 1)

            # Disable the SQLite cache. Its pages tend to get swapped
            # out, even if the database file is in buffer cache.
            c = self.cursor()
            c.execute("PRAGMA cache_size=0")
            c.execute("PRAGMA page_size=4096")

            # Each of these speed-for-reliability tradeoffs is useful for
            # bulk learning.
            c.execute("PRAGMA journal_mode=truncate")
            c.execute("PRAGMA temp_store=memory")
            c.execute("PRAGMA synchronous=OFF")

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        with trace_us("Brain.db_commit_us"):
            self._conn.commit()

    def close(self):
        return self._conn.close()

    def is_initted(self):
        try:
            self.get_info_text("order")
            return True
        except sqlite3.OperationalError:
            return False

    def set_info_text(self, attribute, text):
        c = self.cursor()

        if text is None:
            q = "DELETE FROM info WHERE attribute = ?"
            c.execute(q, (attribute,))
        else:
            q = "UPDATE info SET text = ? WHERE attribute = ?"
            c.execute(q, (text, attribute))

            if c.rowcount == 0:
                q = "INSERT INTO info (attribute, text) VALUES (?, ?)"
                c.execute(q, (attribute, text))

    def get_info_text(self, attribute, default=None, text_factory=None):
        c = self.cursor()

        if text_factory is not None:
            old_text_factory = self._conn.text_factory
            self._conn.text_factory = text_factory

        q = "SELECT text FROM info WHERE attribute = ?"
        row = c.execute(q, (attribute,)).fetchone()

        if text_factory is not None:
            self._conn.text_factory = old_text_factory

        if row:
            return row[0]

        return default

    def get_seq_expr(self, seq):
        # Format the sequence seq as (item1, item2, item2) as appropriate
        # for an IN () clause in SQL
        if len(seq) == 1:
            # Grab the first item from seq. Use an iterator so this works
            # with sets as well as lists.
            return "(%s)" % iter(seq).next()

        return str(tuple(seq))

    def get_token_by_text(self, text, create=False, stemmer=None):
        c = self.cursor()

        q = "SELECT id FROM tokens WHERE text = ?"

        row = c.execute(q, (text,)).fetchone()
        if row:
            return row[0]
        elif create:
            q = "INSERT INTO tokens (text, is_word) VALUES (?, ?)"

            is_word = bool(re.search("\w", text, re.UNICODE))
            c.execute(q, (text, is_word))

            token_id = c.lastrowid
            if stemmer is not None:
                stem = stemmer.stem(text)
                if stem is not None:
                    self.insert_stem(token_id, stem)

            return token_id

    def insert_stem(self, token_id, stem):
        q = "INSERT INTO token_stems (token_id, stem) VALUES (?, ?)"
        self._conn.execute(q, (token_id, stem))

    def get_token_stem_id(self, stem):
        q = "SELECT token_id FROM token_stems WHERE token_stems.stem = ?"
        rows = self._conn.execute(q, (stem,))
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_word_tokens(self, token_ids):
        q = "SELECT id FROM tokens WHERE id IN %s AND is_word = 1" % \
            self.get_seq_expr(token_ids)

        rows = self._conn.execute(q)
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_tokens(self, token_ids):
        q = "SELECT id FROM tokens WHERE id IN %s" % \
            self.get_seq_expr(token_ids)

        rows = self._conn.execute(q)
        if rows:
            return map(operator.itemgetter(0), rows)

    def get_node_by_tokens(self, tokens):
        c = self.cursor()

        q = "SELECT id FROM nodes WHERE %s" % self._all_tokens_args

        row = c.execute(q, tokens).fetchone()
        if row:
            return int(row[0])

        # if not found, create the node
        q = "INSERT INTO nodes (count, %s) " \
            "VALUES (0, %s)" % (self._all_tokens, self._all_tokens_q)
        c.execute(q, tokens)
        return c.lastrowid

    def get_text_by_edge(self, edge_id):
        q = "SELECT tokens.text, edges.has_space FROM nodes, edges, tokens " \
            "WHERE edges.id = ? AND edges.prev_node = nodes.id " \
            "AND nodes.%s = tokens.id" % self._last_token

        return self._conn.execute(q, (edge_id,)).fetchone()

    def get_random_token(self):
        # token 1 is the end_token_id, so we want to generate a random token
        # id from 2..max(id) inclusive.
        q = "SELECT (abs(random()) % (MAX(id)-1)) + 2 FROM tokens"
        row = self._conn.execute(q).fetchone()
        if row:
            return row[0]

    def get_random_node_with_token(self, token_id):
        c = self.cursor()

        q = "SELECT id FROM nodes WHERE token0_id = ? " \
            "LIMIT 1 OFFSET abs(random())%(SELECT count(*) FROM nodes " \
            "                              WHERE token0_id = ?)"

        row = c.execute(q, (token_id, token_id)).fetchone()
        if row:
            return int(row[0])

    def get_edge_logprob(self, edge_id):
        # Each edge goes from an n-gram node (word1, word2, word3) to
        # another (word2, word3, word4). Calculate the probability:
        # P(word4|word1,word2,word3) = count(edge_id) / count(prev_node_id)

        c = self.cursor()
        q = "SELECT edges.count, nodes.count FROM edges, nodes " \
            "WHERE edges.id = ? AND edges.prev_node = nodes.id"

        edge_count, node_count = c.execute(q, (edge_id,)).fetchone()
        return math.log(edge_count, 2) - math.log(node_count, 2)

    def has_space(self, edge_id):
        c = self.cursor()

        q = "SELECT has_space FROM edges WHERE id = ?"

        row = c.execute(q, (edge_id,)).fetchone()
        if row:
            return bool(row[0])

    def add_edge(self, prev_node, next_node, has_space):
        c = self.cursor()

        assert type(has_space) == types.BooleanType

        update_q = "UPDATE edges SET count = count + 1 " \
            "WHERE prev_node = ? AND next_node = ? AND has_space = ?"

        q = "INSERT INTO edges (prev_node, next_node, has_space, count) " \
            "VALUES (?, ?, ?, 1)"

        args = (prev_node, next_node, has_space)

        c.execute(update_q, args)
        if c.rowcount == 0:
            c.execute(q, args)

        # The count on the next_node in the nodes table must be
        # incremented here, to register that the node has been seen an
        # additional time. This is now handled by database triggers.

    def search_bfs(self, start_id, end_id, direction):
        if direction:
            q = "SELECT id, next_node FROM edges WHERE prev_node = ?"
        else:
            q = "SELECT id, prev_node FROM edges WHERE next_node = ?"

        c = self.cursor()

        left = collections.deque([(start_id, tuple())])
        while left:
            cur, path = left.popleft()
            rows = c.execute(q, (cur,))

            for rowid, next in rows:
                newpath = path + (rowid,)

                if next == end_id:
                    yield newpath
                else:
                    left.append((next, newpath))

    def search_random_walk(self, start_id, end_id, direction):
        """Walk once randomly from start_id to end_id."""
        if direction:
            q = "SELECT id, next_node " \
                "FROM edges WHERE prev_node = :last " \
                "LIMIT 1 OFFSET abs(random())%(SELECT count(*) from edges " \
                "                              WHERE prev_node = :last)"
        else:
            q = "SELECT id, prev_node " \
                "FROM edges WHERE next_node = :last " \
                "LIMIT 1 OFFSET abs(random())%(SELECT count(*) from edges " \
                "                              WHERE next_node = :last)"

        c = self.cursor()

        left = collections.deque([(start_id, tuple())])
        while left:
            cur, path = left.popleft()
            rows = c.execute(q, dict(last=cur))

            # Note: the LIMIT 1 above means this list only contains
            # one row. Using a list here so this matches the bfs()
            # code, so the two functions can be more easily combined
            # later.
            for rowid, next in rows:
                newpath = path + (rowid,)

                if next == end_id:
                    yield newpath
                else:
                    left.append((next, newpath))

    def init(self, order, tokenizer, run_migrations=True):
        c = self.cursor()

        log.debug("Creating table: info")
        c.execute("""
CREATE TABLE info (
    attribute TEXT NOT NULL PRIMARY KEY,
    text TEXT NOT NULL)""")

        log.debug("Creating table: tokens")
        c.execute("""
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT UNIQUE NOT NULL,
    is_word INTEGER NOT NULL)""")

        tokens = []
        for i in xrange(order):
            tokens.append("token%d_id INTEGER REFERENCES token(id)" % i)

        log.debug("Creating table: token_stems")
        c.execute("""
CREATE TABLE token_stems (
    token_id INTEGER,
    stem TEXT NOT NULL)""")

        log.debug("Creating table: nodes")
        c.execute("""
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    count INTEGER NOT NULL,
    %s)""" % ',\n    '.join(tokens))

        log.debug("Creating table: edges")
        c.execute("""
CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_node INTEGER NOT NULL REFERENCES nodes(id),
    next_node INTEGER NOT NULL REFERENCES nodes(id),
    count INTEGER NOT NULL,
    has_space INTEGER NOT NULL)""")

        if run_migrations:
            self._run_migrations()

        # save the order of this brain
        self.set_info_text("order", str(order))
        self.order = order

        # save the tokenizer
        self.set_info_text("tokenizer", tokenizer)

        # save the brain/schema version
        self.set_info_text("version", "2")

        self.commit()
        self.ensure_indexes()

        self.close()

    def drop_reply_indexes(self):
        self._conn.execute("DROP INDEX IF EXISTS edges_all_next")
        self._conn.execute("DROP INDEX IF EXISTS edges_all_prev")

        self._conn.execute("""
CREATE INDEX IF NOT EXISTS learn_index ON edges
    (prev_node, next_node)""")

    def ensure_indexes(self):
        c = self.cursor()

        # remove the temporary learning index if it exists
        c.execute("DROP INDEX IF EXISTS learn_index")

        token_ids = ",".join(["token%d_id" % i for i in xrange(self.order)])
        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS nodes_token_ids on nodes
    (%s)""" % token_ids)

        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS edges_all_next ON edges
    (next_node, prev_node, has_space, count)""")

        c.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS edges_all_prev ON edges
    (prev_node, next_node, has_space, count)""")

    def delete_token_stems(self):
        c = self.cursor()

        # drop the two stem indexes
        c.execute("DROP INDEX IF EXISTS token_stems_stem")
        c.execute("DROP INDEX IF EXISTS token_stems_id")

        # delete all the existing stems from the table
        c.execute("DELETE FROM token_stems")

        self.commit()

    def update_token_stems(self, stemmer):
        # stemmer is a CobeStemmer
        with trace_ms("Db.update_token_stems_ms"):
            c = self.cursor()

            insert_c = self.cursor()
            insert_q = "INSERT INTO token_stems (token_id, stem) VALUES (?, ?)"

            q = c.execute("""
SELECT id, text FROM tokens""")

            for row in q:
                stem = stemmer.stem(row[1])
                if stem is not None:
                    insert_c.execute(insert_q, (row[0], stem))

            self.commit()

        with trace_ms("Db.index_token_stems_ms"):
            c.execute("""
CREATE INDEX token_stems_id on token_stems (token_id)""")
            c.execute("""
CREATE INDEX token_stems_stem on token_stems (stem)""")

    def _run_migrations(self):
        with trace_us("Db.run_migrations_us"):
            self._maybe_drop_tokens_text_index()
            self._maybe_create_node_count_triggers()

    def _maybe_drop_tokens_text_index(self):
        # tokens_text was an index on tokens.text, deemed redundant since
        # tokens.text is declared UNIQUE, and sqlite automatically creates
        # indexes for UNIQUE columns
        self._conn.execute("DROP INDEX IF EXISTS tokens_text")

    def _maybe_create_node_count_triggers(self):
        # Create triggers on the edges table to update nodes counts.
        # In previous versions, the node counts were updated with a
        # separate query. Moving them into triggers improves
        # performance.
        c = self.cursor()

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_insert_trigger AFTER INSERT ON edges
    BEGIN UPDATE nodes SET count = count + NEW.count
        WHERE nodes.id = NEW.next_node; END;""")

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_update_trigger AFTER UPDATE ON edges
    BEGIN UPDATE nodes SET count = count + (NEW.count - OLD.count)
        WHERE nodes.id = NEW.next_node; END;""")

        c.execute("""
CREATE TRIGGER IF NOT EXISTS edges_delete_trigger AFTER DELETE ON edges
    BEGIN UPDATE nodes SET count = count - old.count
        WHERE nodes.id = OLD.next_node; END;""")

########NEW FILE########
__FILENAME__ = commands
# Copyright (C) 2014 Peter Teichman

import atexit
import logging
import os
import re
import readline
import Stemmer
import sys
import time

from .bot import Runner
from .brain import Brain

log = logging.getLogger("cobe")


class InitCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("init", help="Initialize a new brain")

        subparser.add_argument("--force", action="store_true")
        subparser.add_argument("--order", type=int, default=3)
        subparser.add_argument("--megahal", action="store_true",
                               help="Use MegaHAL-compatible tokenizer")
        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        filename = args.brain

        if os.path.exists(filename):
            if args.force:
                os.remove(filename)
            else:
                log.error("%s already exists!", filename)
                return

        tokenizer = None
        if args.megahal:
            tokenizer = "MegaHAL"

        Brain.init(filename, order=args.order, tokenizer=tokenizer)


def progress_generator(filename):
    s = os.stat(filename)
    size_left = s.st_size

    fd = open(filename)
    for line in fd.xreadlines():
        size_left = size_left - len(line)
        progress = 100 * (1. - (float(size_left) / float(s.st_size)))

        yield line, progress

    fd.close()


class LearnCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("learn", help="Learn a file of text")
        subparser.add_argument("file", nargs="+")
        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        b = Brain(args.brain)
        b.start_batch_learning()

        for filename in args.file:
            now = time.time()
            print filename

            count = 0
            for line, progress in progress_generator(filename):
                show_progress = ((count % 1000) == 0)

                if show_progress:
                    elapsed = time.time() - now
                    sys.stdout.write("\r%.0f%% (%d/s)" % (progress,
                                                          count / elapsed))
                    sys.stdout.flush()

                b.learn(line.strip())
                count = count + 1

                if (count % 10000) == 0:
                    b.graph.commit()

            elapsed = time.time() - now
            print "\r100%% (%d/s)" % (count / elapsed)

        b.stop_batch_learning()


class LearnIrcLogCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("learn-irc-log",
                                      help="Learn a file of IRC log text")
        subparser.add_argument("-i", "--ignore-nick", action="append",
                               dest="ignored_nicks",
                               help="Ignore an IRC nick")
        subparser.add_argument("-o", "--only-nick", action="append",
                               dest="only_nicks",
                               help="Only learn from specified nicks")
        subparser.add_argument("-r", "--reply-to", action="append",
                               help="Reply (invisibly) to things said "
                               "to specified nick")
        subparser.add_argument("file", nargs="+")
        subparser.set_defaults(run=cls.run)

    @classmethod
    def run(cls, args):
        b = Brain(args.brain)
        b.start_batch_learning()

        for filename in args.file:
            now = time.time()
            print filename

            count = 0
            for line, progress in progress_generator(filename):
                show_progress = ((count % 100) == 0)

                if show_progress:
                    elapsed = time.time() - now
                    sys.stdout.write("\r%.0f%% (%d/s)" % (progress,
                                                          count / elapsed))
                    sys.stdout.flush()

                count = count + 1

                if (count % 1000) == 0:
                    b.graph.commit()

                parsed = cls._parse_irc_message(line.strip(),
                                                args.ignored_nicks,
                                                args.only_nicks)
                if parsed is None:
                    continue

                to, msg = parsed
                b.learn(msg)

                if args.reply_to is not None and to in args.reply_to:
                    b.reply(msg)

            elapsed = time.time() - now
            print "\r100%% (%d/s)" % (count / elapsed)

        b.stop_batch_learning()

    @staticmethod
    def _parse_irc_message(msg, ignored_nicks=None, only_nicks=None):
        # only match lines of the form "HH:MM <nick> message"
        match = re.match("\d+:\d+\s+<(.+?)>\s+(.*)", msg)
        if not match:
            return None

        nick = match.group(1)
        msg = match.group(2)

        if ignored_nicks is not None and nick in ignored_nicks:
            return None

        if only_nicks is not None and nick not in only_nicks:
            return None

        to = None

        # strip "username: " at the beginning of messages
        match = re.search("^(\S+)[,:]\s+(\S.*)", msg)
        if match:
            to = match.group(1)
            msg = match.group(2)

        # strip kibot style '"asdf" --user, 06-oct-09' quotes
        msg = re.sub("\"(.*)\" --\S+,\s+\d+-\S+-\d+",
                     lambda m: m.group(1), msg)

        return to, msg


class ConsoleCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("console", help="Interactive console")
        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        b = Brain(args.brain)

        history = os.path.expanduser("~/.cobe_history")
        try:
            readline.read_history_file(history)
        except IOError:
            pass
        atexit.register(readline.write_history_file, history)

        while True:
            try:
                cmd = raw_input("> ")
            except EOFError:
                print
                sys.exit(0)

            b.learn(cmd)
            print b.reply(cmd).encode("utf-8")


class IrcClientCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("irc-client",
                                      help="IRC client [requires twisted]")
        subparser.add_argument("-s", "--server", required=True,
                               help="IRC server hostname")
        subparser.add_argument("-p", "--port", type=int, default=6667,
                               help="IRC server port")
        subparser.add_argument("-n", "--nick", default="cobe",
                               help="IRC nick")
        subparser.add_argument("-c", "--channel", required=True,
                               help="IRC channel")
        subparser.add_argument("-l", "--log-channel",
                               help="IRC channel for logging")
        subparser.add_argument("-i", "--ignore-nick", action="append",
                               dest="ignored_nicks",
                               help="Ignore an IRC nick")
        subparser.add_argument("-o", "--only-nick", action="append",
                               dest="only_nicks",
                               help="Only learn from a specific IRC nick")

        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        b = Brain(args.brain)

        Runner().run(b, args)


class SetStemmerCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("set-stemmer",
                                      help="Configure a stemmer")

        subparser.set_defaults(run=cls.run)

        subparser.add_argument("language", choices=Stemmer.algorithms(),
                               help="Stemmer language")

    @staticmethod
    def run(args):
        b = Brain(args.brain)

        b.set_stemmer(args.language)


class DelStemmerCommand:
    @classmethod
    def add_subparser(cls, parser):
        subparser = parser.add_parser("del-stemmer", help="Delete the stemmer")
        subparser.set_defaults(run=cls.run)

    @staticmethod
    def run(args):
        b = Brain(args.brain)

        b.del_stemmer()

########NEW FILE########
__FILENAME__ = control
import argparse
import codecs
import logging
import sys

from . import commands
from . import instatrace

parser = argparse.ArgumentParser(description="Cobe control")
parser.add_argument("-b", "--brain", default="cobe.brain")
parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
parser.add_argument("--instatrace", metavar="FILE",
                    help="log performance statistics to FILE")

subparsers = parser.add_subparsers(title="Commands")
commands.ConsoleCommand.add_subparser(subparsers)
commands.InitCommand.add_subparser(subparsers)
commands.IrcClientCommand.add_subparser(subparsers)
commands.LearnCommand.add_subparser(subparsers)
commands.LearnIrcLogCommand.add_subparser(subparsers)
commands.SetStemmerCommand.add_subparser(subparsers)
commands.DelStemmerCommand.add_subparser(subparsers)


def main():
    args = parser.parse_args()

    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console = logging.StreamHandler(codecs.getwriter('utf8')(sys.stderr))
    console.setFormatter(formatter)
    logging.root.addHandler(console)

    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    if args.instatrace:
        instatrace.init_trace(args.instatrace)

    try:
        args.run(args)
    except KeyboardInterrupt:
        print
        sys.exit(1)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = instatrace
# Copyright (C) 2010 Peter Teichman

import datetime
import os
import time

from contextlib import contextmanager

_instatrace = None


def init_trace(filename):
    global _instatrace
    if _instatrace is not None:
        _instatrace.close()

    _instatrace = Instatrace(filename)


class Instatrace:
    def __init__(self, filename):
        # rotate logs if present
        if os.path.exists(filename):
            now = datetime.datetime.now()
            stamp = now.strftime("%Y-%m-%d.%H%M%S")
            os.rename(filename, "%s.%s" % (filename, stamp))

        self._fd = open(filename, "w")

    def now(self):
        """Microsecond resolution, integer now"""
        return int(time.time() * 100000)

    def now_ms(self):
        """Millisecond resolution, integer now"""
        return int(time.time() * 1000)

    def trace(self, stat, value, data=None):
        extra = ""
        if data is not None:
            extra = " " + repr(data)

        self._fd.write("%s %d%s\n" % (stat, value, extra))


def trace(stat, value, user_data=None):
    if _instatrace is not None:
        _instatrace.trace(stat, value, user_data)


@contextmanager
def trace_us(statName):
    if _instatrace is None:
        yield
        return

    # Microsecond resolution, integer now
    now = _instatrace.now()
    yield
    _instatrace.trace(statName, _instatrace.now() - now)


@contextmanager
def trace_ms(statName):
    if _instatrace is None:
        yield
        return

    # Millisecond resolution, integer now
    now = _instatrace.now_ms()
    yield
    _instatrace.trace(statName, _instatrace.now_ms() - now)

########NEW FILE########
__FILENAME__ = scoring
# Copyright (C) 2012 Peter Teichman

import math


class Scorer:
    def __init__(self):
        self.cache = {}

    def end(self, reply):
        self.cache = {}

    def normalize(self, score):
        # map high-valued scores into 0..1
        if score < 0:
            return score

        return 1.0 - 1.0 / (1.0 + score)

    def score(self, reply):
        return NotImplementedError


class ScorerGroup:
    def __init__(self):
        self.scorers = []

    def add_scorer(self, weight, scorer):
        # add a scorer with a negative weight if you want to reverse
        # its impact
        self.scorers.append((weight, scorer))

        total = 0.
        for weight, scorers in self.scorers:
            total += abs(weight)
        self.total_weight = total

    def end(self, reply):
        for scorer in self.scorers:
            scorer[1].end(reply)

    def score(self, reply):
        # normalize to 0..1
        score = 0.
        for weight, scorer in self.scorers:
            s = scorer.score(reply)

            # make sure score is in our accepted range
            assert 0.0 <= score <= 1.0

            if weight < 0.0:
                s = 1.0 - s

            score += abs(weight) * s

        return score / self.total_weight


class CobeScorer(Scorer):
    """Classic Cobe scorer"""
    def score(self, reply):
        edge_ids = reply.edge_ids
        info = 0.

        logprob_cache = self.cache.setdefault("logprob", {})
        space_cache = self.cache.setdefault("has_space", {})

        get_edge_logprob = reply.graph.get_edge_logprob
        has_space = reply.graph.has_space

        # Calculate the information content of the edges in this reply.
        for edge_id in edge_ids:
            if edge_id not in logprob_cache:
                logprob_cache[edge_id] = get_edge_logprob(edge_id)

            info -= logprob_cache[edge_id]

        # Approximate the number of cobe 1.2 contexts in this reply, so the
        # scorer will have similar results.

        # First, we have (graph.order - 1) extra edges on either end of the
        # reply, since cobe 2.0 learns from (_END_TOKEN, _END_TOKEN, ...).
        n_words = len(edge_ids) - (reply.graph.order - 1) * 2

        # Add back one word for each space between edges, since cobe 1.2
        # treated those as separate parts of a context.
        for edge_id in edge_ids:
            if edge_id not in space_cache:
                space_cache[edge_id] = has_space(edge_id)

            if space_cache[edge_id]:
                n_words += 1

        # Double the score, since Cobe 1.x scored both forward and backward
        info *= 2.0

        # Comparing to Cobe 1.x scoring:
        # At this point we have an extra count for every space token
        # that adjoins punctuation. I'm tweaking the two checks below
        # for replies longer than 16 and 32 tokens (rather than our
        # original 8 and 16) as an adjustment. Scoring is an ongoing
        # project.

        if n_words > 16:
            info /= math.sqrt(n_words - 1)
        elif n_words >= 32:
            info /= n_words

        return self.normalize(info)


class InformationScorer(Scorer):
    """Score based on the information of each edge in the graph"""
    def score(self, reply):
        edge_ids = reply.edge_ids
        info = 0.

        logprob_cache = self.cache.setdefault("logprob", {})

        get_edge_logprob = reply.graph.get_edge_logprob

        # Calculate the information content of the edges in this reply.
        for edge_id in edge_ids:
            if edge_id not in logprob_cache:
                logprob_cache[edge_id] = get_edge_logprob(edge_id)

            info -= logprob_cache[edge_id]

        return self.normalize(info)


class LengthScorer(Scorer):
    def score(self, reply):
        return self.normalize(len(reply.edge_ids))

########NEW FILE########
__FILENAME__ = tokenizers
# Copyright (C) 2010 Peter Teichman

import re
import Stemmer
import types


class MegaHALTokenizer:
    """A traditional MegaHAL style tokenizer. This considers any of these
to be a token:
  * one or more consecutive alpha characters (plus apostrophe)
  * one or more consecutive numeric characters
  * one or more consecutive punctuation/space characters (not apostrophe)

This tokenizer ignores differences in capitalization."""
    def split(self, phrase):
        if type(phrase) != types.UnicodeType:
            raise TypeError("Input must be Unicode")

        if len(phrase) == 0:
            return []

        # add ending punctuation if it is missing
        if phrase[-1] not in ".!?":
            phrase = phrase + "."

        words = re.findall("([A-Z']+|[0-9]+|[^A-Z'0-9]+)", phrase.upper(),
                           re.UNICODE)
        return words

    def join(self, words):
        """Capitalize the first alpha character in the reply and the
        first alpha character that follows one of [.?!] and a
        space."""
        chars = list(u"".join(words))
        start = True

        for i in xrange(len(chars)):
            char = chars[i]
            if char.isalpha():
                if start:
                    chars[i] = char.upper()
                else:
                    chars[i] = char.lower()

                start = False
            else:
                if i > 2 and chars[i - 1] in ".?!" and char.isspace():
                    start = True

        return u"".join(chars)


class CobeTokenizer:
    """A tokenizer that is somewhat improved from MegaHAL. These are
considered tokens:
  * one or more consecutive Unicode word characters (plus apostrophe and dash)
  * one or more consecutive Unicode non-word characters, possibly with
    internal whitespace
  * the whitespace between word or non-word tokens
  * an HTTP url, [word]: followed by any run of non-space characters.

This tokenizer collapses multiple spaces in a whitespace token into a
single space character.

It preserves differences in case. foo, Foo, and FOO are different
tokens."""
    def __init__(self):
        # Add hyphen to the list of possible word characters, so hyphenated
        # words become one token (e.g. hy-phen). But don't remove it from
        # the list of non-word characters, so if it's found entirely within
        # punctuation it's a normal non-word (e.g. :-( )

        self.regex = re.compile("(\w+:\S+"  # urls
                                "|[\w'-]+"  # words
                                "|[^\w\s][^\w]*[^\w\s]"  # multiple punctuation
                                "|[^\w\s]"  # a single punctuation character
                                "|\s+)",    # whitespace
                                re.UNICODE)

    def split(self, phrase):
        if type(phrase) != types.UnicodeType:
            raise TypeError("Input must be Unicode")

        # Strip leading and trailing whitespace. This might not be the
        # correct choice long-term, but in the brain it prevents edges
        # from the root node that have has_space set.
        phrase = phrase.strip()

        if len(phrase) == 0:
            return []

        tokens = self.regex.findall(phrase)

        # collapse runs of whitespace into a single space
        space = u" "
        for i, token in enumerate(tokens):
            if token[0] == " " and len(token) > 1:
                tokens[i] = space

        return tokens

    def join(self, words):
        return u"".join(words)


class CobeStemmer:
    def __init__(self, name):
        # use the PyStemmer Snowball stemmer bindings
        self.stemmer = Stemmer.Stemmer(name)

    def stem(self, token):
        if not re.search("\w", token, re.UNICODE):
            return self.stem_nonword(token)

        # Don't preserve case when stemming, i.e. create lowercase stems.
        # This will allow us to create replies that switch the case of
        # input words, but still generate the reply in context with the
        # generated case.

        stem = self.stemmer.stemWord(token.lower())

        return stem

    def stem_nonword(self, token):
        # Stem common smile and frown emoticons down to :) and :(
        if re.search(":-?[ \)]*\)", token):
            return ":)"

        if re.search(":-?[' \(]*\(", token):
            return ":("

########NEW FILE########
__FILENAME__ = test_brain
from cobe.brain import Brain, CobeError
from cobe.tokenizers import MegaHALTokenizer
import cPickle as pickle
import os
import unittest

TEST_BRAIN_FILE = "test_cobe.brain"

class testInit(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def testInit(self):
        Brain.init(TEST_BRAIN_FILE)
        self.failUnless(os.path.exists(TEST_BRAIN_FILE),
                        "missing brain file after init")

        brain = Brain(TEST_BRAIN_FILE)
        self.failUnless(brain.order, "missing brain order after init")
        self.failUnless(brain._end_token_id,
                        "missing brain _end_token_id after init")

    def testInitWithOrder(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual(order, brain.order)

    def testVersion(self):
        Brain.init(TEST_BRAIN_FILE)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertEqual("2", brain.graph.get_info_text("version"))

    def testEmptyReply(self):
        Brain.init(TEST_BRAIN_FILE)

        brain = Brain(TEST_BRAIN_FILE)
        self.assert_(brain.reply("") is not "")

    def testWrongVersion(self):
        Brain.init(TEST_BRAIN_FILE)

        # manually change the brain version to 1
        brain = Brain(TEST_BRAIN_FILE)
        brain.graph.set_info_text("version", "1")
        brain.graph.commit()
        brain.graph.close()

        try:
            Brain(TEST_BRAIN_FILE)
        except CobeError, e:
            self.assert_("cannot read a version" in str(e))
        else:
            self.fail("opened a wrong version brain file")

    def testInitWithTokenizer(self):
        tokenizer = "MegaHAL"
        Brain.init(TEST_BRAIN_FILE, order=2, tokenizer=tokenizer)

        brain = Brain(TEST_BRAIN_FILE)
        self.assertTrue(isinstance(brain.tokenizer, MegaHALTokenizer))

    def testInfoText(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)

        db = brain.graph
        key = "test_text"

        self.assertEqual(None, db.get_info_text(key))

        db.set_info_text(key, "test_value")
        self.assertEqual("test_value", db.get_info_text(key))

        db.set_info_text(key, "test_value2")
        self.assertEqual("test_value2", db.get_info_text(key))

        db.set_info_text(key, None)
        self.assertEqual(None, db.get_info_text(key))

    def testInfoPickle(self):
        order = 2
        Brain.init(TEST_BRAIN_FILE, order=order)

        brain = Brain(TEST_BRAIN_FILE)

        db = brain.graph
        key = "pickle_test"
        obj = {"dummy": "object", "to": "pickle"}

        db.set_info_text(key, pickle.dumps(obj))

        # pickle cannot load from a unicode object
        get_info_text = lambda: pickle.loads(db.get_info_text(key))
        self.assertRaises(TypeError, get_info_text)

        get_info_text = lambda: pickle.loads(
            db.get_info_text(key, text_factory=str))

class testLearn(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

    def testExpandContexts(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        tokens = ["this", Brain.SPACE_TOKEN_ID, "is", Brain.SPACE_TOKEN_ID,
                  "a", Brain.SPACE_TOKEN_ID, "test"]
        self.assertEquals(list(brain._to_edges(tokens)),
                          [((1, 1), False),
                           ((1, "this"), False),
                           (("this", "is"), True),
                           (("is", "a"), True),
                           (("a", "test"), True),
                           (("test", 1), False),
                           ((1, 1), False)])

        tokens = ["this", "is", "a", "test"]
        self.assertEquals(list(brain._to_edges(tokens)),
                          [((1, 1), False),
                           ((1, "this"), False),
                           (("this", "is"), False),
                           (("is", "a"), False),
                           (("a", "test"), False),
                           (("test", 1), False),
                           ((1, 1), False)])

    def testExpandGraph(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        tokens = ["this", Brain.SPACE_TOKEN_ID, "is", Brain.SPACE_TOKEN_ID,
                  "a", Brain.SPACE_TOKEN_ID, "test"]

        self.assertEquals(list(brain._to_graph(brain._to_edges(tokens))),
                          [((1, 1), False, (1, "this")),
                           ((1, "this"), True, ("this", "is")),
                           (("this", "is"), True, ("is", "a")),
                           (("is", "a"), True, ("a", "test")),
                           (("a", "test"), False, ("test", 1)),
                           (("test", 1), False, (1, 1))])

    def testLearn(self):
        Brain.init(TEST_BRAIN_FILE, order=2)
        brain = Brain(TEST_BRAIN_FILE)

        brain.learn("this is a test")
        brain.learn("this is also a test")

    def testLearnStems(self):
        Brain.init(TEST_BRAIN_FILE, order=2)

        brain = Brain(TEST_BRAIN_FILE)
        brain.set_stemmer("english")
        stem = brain.stemmer.stem

        brain.learn("this is testing")

        c = brain.graph.cursor()
        stem_count = c.execute("SELECT count(*) FROM token_stems").fetchone()

        self.assertEquals(3, stem_count[0])
        self.assertEquals(brain.graph.get_token_stem_id(stem("test")),
                          brain.graph.get_token_stem_id(stem("testing")))


class testReply(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_BRAIN_FILE):
            os.remove(TEST_BRAIN_FILE)

        Brain.init(TEST_BRAIN_FILE, order=2)
        self._brain = Brain(TEST_BRAIN_FILE)

    def testReply(self):
        brain = self._brain

        brain.learn("this is a test")
        brain.reply("this is a test")

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_commands
import unittest

from cobe.commands import LearnIrcLogCommand

class testIrcLogParsing(unittest.TestCase):
    def setUp(self):
        self.command = LearnIrcLogCommand()

    def testNonPubmsg(self):
        msg = "this is some non-pubmsg text found in a log"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg))

    def testNormalPubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testPubmsgToCobe(self):
        msg = "12:00 <foo> cobe: bar baz"
        cmd = self.command

        self.assertEqual(("cobe", "bar baz"), cmd._parse_irc_message(msg))

    def testNormalPubmsgWithSpaces(self):
        msg = "12:00 < foo> bar baz"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testKibotQuotePubmsg(self):
        msg = "12:00 <foo> \"bar baz\" --user, 01-oct-09"
        cmd = self.command

        self.assertEqual("bar baz", cmd._parse_irc_message(msg)[1])

    def testIgnoredNickPubmsg(self):
        msg = "12:00 <foo> bar baz"
        cmd = self.command

        self.assertEqual(None, cmd._parse_irc_message(msg, ["foo"]))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tokenizers
import unittest

from cobe.tokenizers import CobeStemmer, CobeTokenizer, MegaHALTokenizer

class testMegaHALTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = MegaHALTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["HI", "."])

    def testSplitComma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["HI", ", ", "COBE", "."])

    def testSplitImplicitStop(self):
        words = self.tokenizer.split(u"hi")
        self.assertEquals(words, ["HI", "."])

    def testSplitUrl(self):
        words = self.tokenizer.split(u"http://www.google.com/")
        self.assertEquals(words, ["HTTP", "://", "WWW", ".", "GOOGLE", ".", "COM", "/."])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testSplitApostrophe(self):
        words = self.tokenizer.split(u"hal's brain")
        self.assertEquals(words, ["HAL'S", " ", "BRAIN", "."])

        words = self.tokenizer.split(u"',','")
        self.assertEquals(words, ["'", ",", "'", ",", "'", "."])

    def testSplitAlphaAndNumeric(self):
        words = self.tokenizer.split(u"hal9000, test blah 12312")
        self.assertEquals(words, ["HAL", "9000", ", ", "TEST", " ", "BLAH", " ", "12312", "."])

        words = self.tokenizer.split(u"hal9000's test")
        self.assertEquals(words, ["HAL", "9000", "'S", " ", "TEST", "."])

    def testCapitalize(self):
        words = self.tokenizer.split(u"this is a test")
        self.assertEquals(u"This is a test.", self.tokenizer.join(words))

        words = self.tokenizer.split(u"A.B. Hal test test. will test")
        self.assertEquals(u"A.b. Hal test test. Will test.",
                          self.tokenizer.join(words))

        words = self.tokenizer.split(u"2nd place test")
        self.assertEquals(u"2Nd place test.", self.tokenizer.join(words))

class testCobeTokenizer(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CobeTokenizer()

    def testSplitEmpty(self):
        self.assertEquals(len(self.tokenizer.split(u"")), 0)

    def testSplitSentence(self):
        words = self.tokenizer.split(u"hi.")
        self.assertEquals(words, ["hi", "."])

    def testSplitComma(self):
        words = self.tokenizer.split(u"hi, cobe")
        self.assertEquals(words, ["hi", ",", " ", "cobe"])

    def testSplitDash(self):
        words = self.tokenizer.split(u"hi - cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitMultipleSpacesWithDash(self):
        words = self.tokenizer.split(u"hi  -  cobe")
        self.assertEquals(words, ["hi", " ", "-", " ", "cobe"])

    def testSplitLeadingDash(self):
        words = self.tokenizer.split(u"-foo")
        self.assertEquals(words, ["-foo"])

    def testSplitLeadingSpace(self):
        words = self.tokenizer.split(u" foo")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"  foo")
        self.assertEquals(words, ["foo"])

    def testSplitTrailingSpace(self):
        words = self.tokenizer.split(u"foo ")
        self.assertEquals(words, ["foo"])

        words = self.tokenizer.split(u"foo  ")
        self.assertEquals(words, ["foo"])

    def testSplitSmiles(self):
        words = self.tokenizer.split(u":)")
        self.assertEquals(words, [":)"])

        words = self.tokenizer.split(u";)")
        self.assertEquals(words, [";)"])

        # not smiles
        words = self.tokenizer.split(u":(")
        self.assertEquals(words, [":("])

        words = self.tokenizer.split(u";(")
        self.assertEquals(words, [";("])

    def testSplitUrl(self):
        words = self.tokenizer.split(u"http://www.google.com/")
        self.assertEquals(words, ["http://www.google.com/"])

        words = self.tokenizer.split(u"https://www.google.com/")
        self.assertEquals(words, ["https://www.google.com/"])

        # odd protocols
        words = self.tokenizer.split(u"cobe://www.google.com/")
        self.assertEquals(words, ["cobe://www.google.com/"])

        words = self.tokenizer.split(u"cobe:www.google.com/")
        self.assertEquals(words, ["cobe:www.google.com/"])

        words = self.tokenizer.split(u":foo")
        self.assertEquals(words, [":", "foo"])

    def testSplitMultipleSpaces(self):
        words = self.tokenizer.split(u"this is  a test")
        self.assertEquals(words, ["this", " ", "is", " ", "a", " ", "test"])

    def testSplitVerySadFrown(self):
        words = self.tokenizer.split(u"testing :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (")
        self.assertEquals(words, ["testing", " ", ":    ("])

        words = self.tokenizer.split(u"testing          :    (  foo")
        self.assertEquals(words, ["testing", " ", ":    (", " ", "foo"])

    def testSplitHyphenatedWord(self):
        words = self.tokenizer.split(u"test-ing")
        self.assertEquals(words, ["test-ing"])

        words = self.tokenizer.split(u":-)")
        self.assertEquals(words, [":-)"])

        words = self.tokenizer.split(u"test-ing :-) 1-2-3")
        self.assertEquals(words, ["test-ing", " ", ":-)", " ", "1-2-3"])

    def testSplitApostrophes(self):
        words = self.tokenizer.split(u"don't :'(")
        self.assertEquals(words, ["don't", " ", ":'("])

    def testSplitNonUnicode(self):
        self.assertRaises(TypeError, self.tokenizer.split, "foo")

    def testJoin(self):
        self.assertEquals("foo bar baz",
                          self.tokenizer.join(["foo", " ", "bar", " ", "baz"]))


class testCobeStemmer(unittest.TestCase):
    def setUp(self):
        self.stemmer = CobeStemmer("english")

    def testStemmer(self):
        self.assertEquals("foo", self.stemmer.stem("foo"))
        self.assertEquals("jump", self.stemmer.stem("jumping"))
        self.assertEquals("run", self.stemmer.stem("running"))

    def testStemmerCase(self):
        self.assertEquals("foo", self.stemmer.stem("Foo"))
        self.assertEquals("foo", self.stemmer.stem("FOO"))

        self.assertEquals("foo", self.stemmer.stem("FOO'S"))
        self.assertEquals("foo", self.stemmer.stem("FOOING"))
        self.assertEquals("foo", self.stemmer.stem("Fooing"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
