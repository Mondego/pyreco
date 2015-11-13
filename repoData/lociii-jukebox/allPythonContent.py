__FILENAME__ = admin
# -*- coding: UTF-8 -*-

from models import Artist, Genre, Album, Song, Queue, History, Favourite
from django.contrib import admin


class ArtistAdmin(admin.ModelAdmin):
    list_display = ('Name', )
    search_fields = ['Name']


class GenreAdmin(admin.ModelAdmin):
    list_display = ('Name', )


class AlbumAdmin(admin.ModelAdmin):
    list_display = ('Title', )
    search_fields = ['Title']


class SongAdmin(admin.ModelAdmin):
    list_display = ('Title', 'Artist', 'Year', 'Genre', )
    search_fields = ['Title']


class QueueAdmin(admin.ModelAdmin):
    list_display = ('Song', 'Created', )


class HistoryAdmin(admin.ModelAdmin):
    list_display = ('Song', 'Created', )


class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('Song', 'User', 'Created', )
    search_fields = ['User__username']


admin.site.register(Artist, ArtistAdmin)
admin.site.register(Genre, GenreAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(Queue, QueueAdmin)
admin.site.register(History, HistoryAdmin)
admin.site.register(Favourite, FavouriteAdmin)

########NEW FILE########
__FILENAME__ = api
# -*- coding: UTF-8 -*-
from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, Min, Q
from django.contrib.sessions.models import Session
from django.utils import formats
import os, re, time
from datetime import datetime
from signal import SIGABRT
from django.contrib.auth.models import User
from models import Song, Artist, Album, Genre, Queue, Favourite, History, Player


class api_base:
    count = 30
    user_id = None
    search_term = None
    search_title = None
    search_artist_name = None
    search_album_title = None
    filter_year = None
    filter_genre = None
    filter_album_id = None
    filter_artist_id = None
    order_by_field = None
    order_by_direction = None
    order_by_fields = []
    order_by_directions = ["asc", "desc"]
    order_by_default = None

    def set_count(self, count):
        if count > 100:
            self.count = 100
        elif count > 0:
            self.count = count

    def set_user_id(self, user_id):
        self.user_id = user_id

    def set_search_term(self, term):
        options = self.parseSearchString(
            (
                "title",
                "artist",
                "album",
                "genre",
                "year",
            ),
            term
        )
        for key, value in options.items():
            if key == "title":
                self.set_search_title(value)
            elif key == "artist":
                self.set_search_artist_name(value)
            elif key == "album":
                self.set_search_album_title(value)
            elif key == "genre":
                try:
                    genre = Genre.objects.all().filter(Name__iexact=value)[0:1].get()
                    self.set_filter_genre(genre.id)
                except ObjectDoesNotExist:
                    pass
            elif key == "year":
                self.set_filter_year(value)

        self.search_term = options["term"]

    def parseSearchString(self, keywords, term):
        values = {}
        for i in range(len(keywords)):
            do_continue = False
            keyword = keywords[i]
            value = None
            pos = term.find(keyword + ":")
            if pos != -1:
                value_start = pos + len(keyword) + 1
                # no brackets, search for next whitespace
                if term[value_start:value_start + 1] != "(":
                    value_end = term.find(" ", value_start)
                    if value_end == -1:
                        value_end = len(term)
                        do_continue = True
                    value = term[value_start:value_end]
                # search for next closing bracket but count opened ones
                else:
                    i = value_start + 1
                    bracket_count = 1
                    while i < len(term):
                        char = term[i:i+1]
                        if char == "(":
                            bracket_count+= 1
                        elif char == ")":
                            bracket_count-= 1
                            if not bracket_count:
                                value = term[value_start:i+1]
                                continue
                        i+= 1

                    if not value:
                        value = term[value_start:len(term)]
                        do_continue = True

            if value is not None:
                values[keyword] = value
            if do_continue:
                continue

        for key, value in values.items():
            term = term.replace(key + ":" + value, "").strip()
            if value.startswith("("):
                values[key] = value[1:len(value)-1]

        values["term"] = re.sub("\s+", " ", term)
        return values

    def set_search_title(self, term):
        self.search_title = term

    def set_search_artist_name(self, term):
        self.search_artist_name = term

    def set_search_album_title(self, term):
        self.search_album_title = term

    def set_filter_year(self, term):
        self.filter_year = term

    def set_filter_genre(self, term):
        self.filter_genre = term

    def set_filter_album_id(self, term):
        self.filter_album_id = term

    def set_filter_artist_id(self, term):
        self.filter_artist_id = term

    def set_order_by(self, field, direction="asc"):
        if (not field in self.order_by_fields or
            not direction in self.order_by_directions):
            return

        self.order_by_field = field
        self.order_by_direction = direction

    def get_default_result(self, result_type, page):
        search = {}
        if self.search_title is not None:
            value = self.search_title
            if value.find(" ") != -1:
                value = "(" + value + ")"
            search["title"] = value
        if self.search_artist_name is not None:
            value = self.search_artist_name
            if value.find(" ") != -1:
                value = "(" + value + ")"
            search["artist"] = value
        if self.search_album_title is not None:
            value = self.search_album_title
            if value.find(" ") != -1:
                value = "(" + value + ")"
            search["album"] = value
        if self.filter_genre is not None:
            genre = Genre.objects.all().filter(id=self.filter_genre)[0:1].get()
            value = genre.Name
            if value.find(" ") != -1:
                value = "(" + value + ")"
            search["genre"] = value
            search["genre_id"] = genre.id
        if self.filter_year is not None:
            search["year"] = str(self.filter_year)
        if self.search_term is not None:
            search["term"] = self.search_term

        return {
            "type": result_type,
            "page": page,
            "hasNextPage": False,
            "itemList": [],
            "order": [],
            "search": search,
        }

    def result_add_queue_and_favourite(self, song, dataset):
        if not self.user_id is None:
            try:
                queue = Queue.objects.get(Song=song)
                for user in queue.User.all():
                    if user.id == self.user_id:
                        dataset["queued"] = True
                        break
            except ObjectDoesNotExist:
                pass
            try:
                user = User.objects.get(id=self.user_id)
                Favourite.objects.get(Song=song, User=user)
                dataset["favourite"] = True
            except ObjectDoesNotExist:
                pass

        return dataset

    def source_set_order(self, object_list):
        if not self.order_by_field is None:
            field_name = self.order_by_fields.get(self.order_by_field)
            if self.order_by_direction == "desc":
                field_name = "-" + field_name

            return object_list.order_by(field_name)
        elif not self.order_by_default is None:
            order = []
            for key, value in self.order_by_default.items():
                order.append(value)

            object_list = object_list.order_by(*order)

        return object_list

    def result_set_order(self, result):
        result["order"] = []

        if not self.order_by_field is None:
            result["order"].append({
                "field": self.order_by_field,
                "direction": self.order_by_direction,
            })
        elif not self.order_by_default is None:
            for field, order in self.order_by_default.items():
                result["order"].append({
                    "field": field,
                    "direction": "desc" if order.startswith("-") else "asc",
                })

        return result

class songs(api_base):
    order_by_fields = {
        "title": "Title",
        "artist": "Artist__Name",
        "album": "Album__Title",
        "year": "Year",
        "genre": "Genre__Name",
        "length": "Length",
    }
    order_by_default = {
        "title": "Title",
    }

    def index(self, page=1):
        object_list = Song.objects.all()

        # searches
        if not self.search_term is None:
            object_list = object_list.filter(
                Q(Title__contains=self.search_term)
                |
                Q(Artist__Name__contains=self.search_term)
                |
                Q(Album__Title__contains=self.search_term)
            )
        if not self.search_title is None:
            object_list = object_list.filter(
                 Title__contains=self.search_title
             )
        if not self.search_artist_name is None:
            object_list = object_list.filter(
                 Artist__Name__contains=self.search_artist_name
             )
        if not self.search_album_title is None:
            object_list = object_list.filter(
                 Album__Title__contains=self.search_album_title
             )

        # filters
        if not self.filter_year is None:
            object_list = object_list.filter(
                 Year__exact=self.filter_year
             )
        if not self.filter_genre is None:
            object_list = object_list.filter(
                 Genre__exact=self.filter_genre
             )
        if not self.filter_album_id is None:
            object_list = object_list.filter(
                 Album__exact=self.filter_album_id
             )
        if not self.filter_artist_id is None:
            object_list = object_list.filter(
                 Artist__exact=self.filter_artist_id
             )

        # order
        object_list = self.source_set_order(object_list)

        # prepare result
        result = self.get_default_result("songs", page)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "id": item.id,
                "title": None,
                "artist": {
                    "id": None,
                    "name": None,
                },
                "album": {
                    "id": None,
                    "title": None,
                },
                "year": None,
                "genre": {
                    "id": None,
                    "name": None,
                },
                "length": None,
                "queued": False,
                "favourite": False,
            }
            if not item.Title is None:
                dataset["title"] = item.Title
            if not item.Artist is None:
                dataset["artist"]["id"] = item.Artist.id
                dataset["artist"]["name"] = item.Artist.Name
            if not item.Album is None:
                dataset["album"]["id"] = item.Album.id
                dataset["album"]["title"] = item.Album.Title
            if not item.Year is None:
                dataset["year"] = item.Year
            if not item.Genre is None:
                dataset["genre"]["id"] = item.Genre.id
                dataset["genre"]["name"] = item.Genre.Name
            if not item.Length is None:
                dataset["length"] = item.Length

            dataset = self.result_add_queue_and_favourite(item, dataset)
            result["itemList"].append(dataset)

        return result

    def getNextSong(self):
        # commit transaction to force fresh queryset result
        try:
            transaction.enter_transaction_management()
            transaction.commit()
        except BaseException:
            pass

        try:
            data = Queue.objects.all()
            data = data.annotate(VoteCount=Count("User"))
            data = data.annotate(MinCreated=Min("Created"))
            data = data.order_by("-VoteCount", "MinCreated")[0:1].get()
            self.addToHistory(data.Song, data.User)
            song_instance = data.Song
            data.delete()
        except ObjectDoesNotExist:
            try:
                song_instance = self.getRandomSongByPreferences()
                self.addToHistory(song_instance, None)
            except ObjectDoesNotExist:
                song_instance = Song.objects.order_by('?')[0:1].get()
                self.addToHistory(song_instance, None)

        # remove missing files
        if not os.path.exists(song_instance.Filename.encode('utf8')):
            Song.objects.all().filter(id=song_instance.id).delete()
            return self.getNextSong()

        return song_instance

    def getRandomSongByPreferences(self):
        artists = {}

        # get logged in users
        sessions = Session.objects.exclude(
            expire_date__lt=datetime.today()
        )
        for session in sessions.all():
            data = session.get_decoded()
            if not "_auth_user_id" in data:
                continue
            user_id = data["_auth_user_id"]

            # get newest favourites
            favourites = Favourite.objects.filter(User__id=user_id)[0:30]
            for favourite in favourites:
                if not favourite.Song.Artist.id in artists:
                    artists[favourite.Song.Artist.id] = 0
                artists[favourite.Song.Artist.id]+= 1

            # get last voted songs
            votes = History.objects.filter(User__id=user_id)[0:30]
            for vote in votes:
                if not vote.Song.Artist.id in artists:
                    artists[vote.Song.Artist.id] = 0
                artists[vote.Song.Artist.id]+= 1

        # nothing played and no favourites
        if not len(artists):
            raise ObjectDoesNotExist

        # calculate top artists
        from operator import itemgetter
        sorted_artists = sorted(
            artists.iteritems(),
            key=itemgetter(1),
            reverse=True
        )[0:30]
        artists = []
        for key in range(len(sorted_artists)):
            artists.append(sorted_artists[key][0])

        # get the 50 last played songs
        history = History.objects.all()[0:50]
        last_played = []
        for item in history:
            last_played.append(item.Song.id)

        # find a song not played recently
        song_instance = Song.objects.exclude(
            id__in=last_played
        ).filter(
            Artist__id__in=artists
        ).order_by('?')[0:1].get()
        return song_instance

    def addToHistory(self, song_instance, user_list):
        history_instance = History(
            Song=song_instance
        )
        history_instance.save()

        if user_list is not None and user_list.count() > 0:
            for user_instance in user_list.all():
                history_instance.User.add(user_instance)

    def skipCurrentSong(self):
        players = Player.objects.all()
        for player in players:
            try:
                os.kill(player.Pid, SIGABRT)
            except OSError:
                player.delete()

class history(api_base):
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
    }
    order_by_default = {
        "created": "-Created",
    }

    def index(self, page=1):
        object_list = History.objects.all()
        object_list = self.source_set_order(object_list)
        result = self.build_result(object_list, page)
        result = self.result_set_order(result)
        return result

    def build_result(self, object_list, page):
        # prepare result
        result = self.get_default_result("history", page)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "id": item.Song.id,
                "title": None,
                "artist": {
                    "id": None,
                    "name": None,
                },
                "album": {
                    "id": None,
                    "title": None,
                },
                "year": None,
                "genre": {
                    "id": None,
                    "name": None,
                },
                "queued": False,
                "favourite": False,
                "created": formats.date_format(
                    item.Created, "DATETIME_FORMAT"
                ),
                "votes": item.User.count(),
                "users": [],
            }
            if not item.Song.Title is None:
                dataset["title"] = item.Song.Title
            if not item.Song.Artist is None:
                dataset["artist"]["id"] = item.Song.Artist.id
                dataset["artist"]["name"] = item.Song.Artist.Name
            if not item.Song.Album is None:
                dataset["album"]["id"] = item.Song.Album.id
                dataset["album"]["title"] = item.Song.Album.Title
            if not item.Song.Year is None:
                dataset["year"] = item.Song.Year
            if not item.Song.Genre is None:
                dataset["genre"]["id"] = item.Song.Genre.id
                dataset["genre"]["name"] = item.Song.Genre.Name

            if not item.User.count() == 0:
                for user in item.User.all():
                    dataset["users"].append({
                        "id": user.id,
                        "name": user.get_full_name()
                    })

            dataset = self.result_add_queue_and_favourite(item.Song, dataset)
            result["itemList"].append(dataset)

        return result

    def getCurrent(self):
        item = History.objects.all()[0:1].get()
        createdTimestamp = time.mktime(item.Created.timetuple())
        dataset = {
            "id": item.Song.id,
            "title": None,
            "artist": {
                "id": None,
                "name": None,
            },
            "album": {
                "id": None,
                "title": None,
            },
            "year": None,
            "genre": {
                "id": None,
                "name": None,
            },
            "queued": False,
            "favourite": False,
            "created": formats.date_format(
                item.Created, "DATETIME_FORMAT"
            ),
            "votes": item.User.count(),
            "users": [],
            "remaining": createdTimestamp + item.Song.Length - int(time.time())
        }
        if not item.Song.Title is None:
            dataset["title"] = item.Song.Title
        if not item.Song.Artist is None:
            dataset["artist"]["id"] = item.Song.Artist.id
            dataset["artist"]["name"] = item.Song.Artist.Name
        if not item.Song.Album is None:
            dataset["album"]["id"] = item.Song.Album.id
            dataset["album"]["title"] = item.Song.Album.Title
        if not item.Song.Year is None:
            dataset["year"] = item.Song.Year
        if not item.Song.Genre is None:
            dataset["genre"]["id"] = item.Song.Genre.id
            dataset["genre"]["name"] = item.Song.Genre.Name

        return dataset

class history_my(history):
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
    }
    order_by_default = {
        "created": "-Created",
    }

    def index(self, page=1):
        object_list = History.objects.all().filter(User__id=self.user_id)
        object_list = self.source_set_order(object_list)
        result = self.build_result(object_list, page)

        result = self.result_set_order(result)
        result["type"] = "history/my"
        return result


class queue(api_base):
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
        "votes": "VoteCount",
    }
    order_by_default = {
        "votes": "-VoteCount",
        "created": "MinCreated",
    }

    def index(self, page=1):
        object_list = Queue.objects.all()
        object_list = object_list.annotate(VoteCount=Count("User"))
        object_list = object_list.annotate(MinCreated=Min("Created"))
        object_list = self.source_set_order(object_list)

        # prepare result
        result = self.get_default_result("queue", page)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            result["itemList"].append(self.get(item.Song.id))

        return result

    def get(self, song_id):
        song = Song.objects.get(id=song_id)
        item = Queue.objects.get(Song=song)

        result = {
            "id": item.Song.id,
            "title": None,
            "artist": {
                "id": None,
                "name": None,
            },
            "album": {
                "id": None,
                "title": None,
            },
            "year": None,
            "genre": {
                "id": None,
                "name": None,
            },
            "queued": False,
            "favourite": False,
            "created": formats.date_format(item.Created, "DATETIME_FORMAT"),
            "votes": item.User.count(),
            "users": [],
        }

        if not item.Song.Title is None:
            result["title"] = item.Song.Title
        if not item.Song.Artist is None:
            result["artist"]["id"] = item.Song.Artist.id
            result["artist"]["name"] = item.Song.Artist.Name
        if not item.Song.Album is None:
            result["album"]["id"] = item.Song.Album.id
            result["album"]["title"] = item.Song.Album.Title
        if not item.Song.Year is None:
            result["year"] = item.Song.Year
        if not item.Song.Genre is None:
            result["genre"]["id"] = item.Song.Genre.id
            result["genre"]["name"] = item.Song.Genre.Name

        if not item.User.count() == 0:
            for user in item.User.all():
                result["users"].append({"id": user.id, "name": user.get_full_name()})

        result = self.result_add_queue_and_favourite(item.Song, result)

        return result

    def add(self, song_id):
        song = Song.objects.get(id=song_id)
        user = User.objects.get(id=self.user_id)

        try:
            queue = Queue.objects.get(Song=song)
        except ObjectDoesNotExist:
            queue = Queue(
                Song=song
            )
            queue.save()
        queue.User.add(user)

        return song_id

    def remove(self, song_id):
        song = Song.objects.get(id=song_id)
        user = User.objects.get(id=self.user_id)

        queue = Queue.objects.get(Song=song)
        queue.User.remove(user)
        vote_count = queue.User.count()
        if not queue.User.count():
            queue.delete()

        return {
            "id": song_id,
            "count": vote_count,
        }


class favourites(api_base):
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
    }
    order_by_default = {
        "created": "-Created",
    }

    def index(self, page=1):
        object_list = Favourite.objects.all().filter(User__id=self.user_id)
        object_list = self.source_set_order(object_list)

        # prepare result
        result = self.get_default_result("favourites", page)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            result["itemList"].append(self.get(item.Song.id))

        return result

    def get(self, song_id):
        song = Song.objects.get(id=song_id)
        item = Favourite.objects.get(Song=song,User__id=self.user_id)

        result = {
            "id": item.Song.id,
            "title": None,
            "artist": {
                "id": None,
                "name": None,
            },
            "album": {
                "id": None,
                "title": None,
            },
            "year": None,
            "genre": {
                "id": None,
                "name": None,
            },
            "queued": False,
            "favourite": False,
            "created": formats.date_format(item.Created, "DATETIME_FORMAT"),
        }

        if not item.Song.Title is None:
            result["title"] = item.Song.Title
        if not item.Song.Artist is None:
            result["artist"]["id"] = item.Song.Artist.id
            result["artist"]["name"] = item.Song.Artist.Name
        if not item.Song.Album is None:
            result["album"]["id"] = item.Song.Album.id
            result["album"]["title"] = item.Song.Album.Title
        if not item.Song.Year is None:
            result["year"] = item.Song.Year
        if not item.Song.Genre is None:
            result["genre"]["id"] = item.Song.Genre.id
            result["genre"]["name"] = item.Song.Genre.Name

        result = self.result_add_queue_and_favourite(item.Song, result)

        return result

    def add(self, song_id):
        song = Song.objects.get(id=song_id)
        user = User.objects.get(id=self.user_id)

        favourite = Favourite(
            Song=song,
            User=user
        )
        favourite.save()

        return song_id

    def remove(self, song_id):
        song = Song.objects.get(id=song_id)
        user = User.objects.get(id=self.user_id)

        Favourite.objects.get(
            Song=song,
            User=user
        ).delete()

        return {
            "id": song_id,
        }


class artists(api_base):
    order_by_fields = {
        "artist": "Name",
    }
    order_by_default = {
        "artist": "Name",
    }

    def index(self, page=1):
        # prepare result
        result = self.get_default_result("artists", page)

        object_list = Artist.objects.all()
        object_list = self.source_set_order(object_list)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "id": item.id,
                "artist": item.Name,
            }

            result["itemList"].append(dataset)

        return result


class albums(api_base):
    order_by_fields = {
        "album": "Title",
    }
    order_by_default = {
        "album": "Title",
    }

    def index(self, page=1):
        # prepare result
        result = self.get_default_result("albums", page)

        object_list = Album.objects.all()
        object_list = self.source_set_order(object_list)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "id": item.id,
                "album": item.Title,
            }

            result["itemList"].append(dataset)

        return result


class genres(api_base):
    order_by_fields = {
        "genre": "Name",
    }
    order_by_default = {
        "genre": "Name",
    }

    def index(self, page=1):
        # prepare result
        result = self.get_default_result("genres", page)

        object_list = Genre.objects.all()
        object_list = self.source_set_order(object_list)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "id": item.id,
                "genre": item.Name,
            }

            result["itemList"].append(dataset)

        return result


class years(api_base):
    order_by_fields = {
        "year": "Year",
    }
    order_by_default = {
        "year": "Year"
    }

    def index(self, page=1):
        # prepare result
        result = self.get_default_result("years", page)

        object_list = Song.objects.values("Year").distinct()
        object_list = object_list.exclude(Year=None).exclude(Year=0)
        object_list = self.source_set_order(object_list)

        # get data
        paginator = Paginator(object_list, self.count)
        try:
            page_obj = paginator.page(page)
        except InvalidPage:
            return result

        result = self.result_set_order(result)
        result["hasNextPage"] = page_obj.has_next()
        for item in page_obj.object_list:
            dataset = {
                "year": item["Year"],
            }

            result["itemList"].append(dataset)

        return result


class players(api_base):
    def add(self, pid):
        player = Player(
            Pid=pid
        )
        player.save()

        return player.id

    def remove(self, pid):
        Player.objects.get(Pid=pid).delete()

        return {
            "pid": pid,
        }

########NEW FILE########
__FILENAME__ = forms
# -*- coding: UTF-8 -*-

from django import forms


class IdForm(forms.Form):
    id = forms.IntegerField(
        required=True
    )


class SongsForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    search_term = forms.CharField(
        required=False
    )
    search_title = forms.CharField(
        required=False
    )
    search_artist = forms.CharField(
        required=False
    )
    search_album = forms.CharField(
        required=False
    )

    filter_year = forms.IntegerField(
        required=False
    )
    filter_genre = forms.IntegerField(
        required=False
    )
    filter_album_id = forms.IntegerField(
        required=False
    )
    filter_artist_id = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=6,
        help_text="'title', 'artist', 'album', 'year', 'genre'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class ArtistsForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=6,
        help_text="'artist'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class AlbumsForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=6,
        help_text="'album', 'artist'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class GenresForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=5,
        help_text="'genre'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class YearsForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=4,
        help_text="'year'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class HistoryForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=7,
        help_text="'title', 'artist', 'album', 'year', 'genre', 'created'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class FavouritesForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=7,
        help_text="'title', 'artist', 'album', 'year', 'genre', 'created'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )


class QueueForm(forms.Form):
    count = forms.IntegerField(
        required=False
    )
    page = forms.IntegerField(
        required=False
    )

    order_by = forms.CharField(
        max_length=7,
        help_text="'title', 'artist', 'album', 'year', \
            'genre', 'created', 'votes'",
        required=False
    )
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False
    )

########NEW FILE########
__FILENAME__ = jukebox_index
# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand
from optparse import make_option
import os
from jukebox.jukebox_core.utils import FileIndexer


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--path", action="store", dest="path",
                    help="Music library path to scan"),
    )

    def handle(self, *args, **options):
        if options["path"] is None:
            print "Required arguments: path"
            return

        if not os.path.exists(options["path"]):
            print "Path does not exist"
            return

        print "Indexing music in " + options["path"]
        print "This may take a while"
        self.index(options["path"], int(options["verbosity"]))

    def index(self, path, verbosity):
        if not path.endswith("/"):
            path += "/"

        indexer = FileIndexer()

        listing = os.listdir(path)
        for filename in listing:
            filename = path + filename
            if os.path.isdir(filename):
                self.index(filename + "/", verbosity)
            elif filename.endswith(".mp3"):
                if verbosity >= 2:
                    print "Indexing file " + filename
                indexer.index(filename)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Artist'
        db.create_table('jukebox_core_artist', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('jukebox_core', ['Artist'])

        # Adding model 'Genre'
        db.create_table('jukebox_core_genre', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('jukebox_core', ['Genre'])

        # Adding model 'Album'
        db.create_table('jukebox_core_album', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('Artist', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Artist'])),
        ))
        db.send_create_signal('jukebox_core', ['Album'])

        # Adding model 'Song'
        db.create_table('jukebox_core_song', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Artist', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Artist'])),
            ('Album', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Album'], null=True)),
            ('Genre', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Genre'], null=True)),
            ('Title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('Year', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('Length', self.gf('django.db.models.fields.IntegerField')()),
            ('Filename', self.gf('django.db.models.fields.CharField')(max_length=1000)),
        ))
        db.send_create_signal('jukebox_core', ['Song'])

        # Adding model 'Queue'
        db.create_table('jukebox_core_queue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Song', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Song'], unique=True)),
            ('Created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('jukebox_core', ['Queue'])

        # Adding M2M table for field User on 'Queue'
        db.create_table('jukebox_core_queue_User', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queue', models.ForeignKey(orm['jukebox_core.queue'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('jukebox_core_queue_User', ['queue_id', 'user_id'])

        # Adding model 'Favourite'
        db.create_table('jukebox_core_favourite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Song', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Song'])),
            ('User', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('Created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('jukebox_core', ['Favourite'])

        # Adding unique constraint on 'Favourite', fields ['Song', 'User']
        db.create_unique('jukebox_core_favourite', ['Song_id', 'User_id'])

        # Adding model 'History'
        db.create_table('jukebox_core_history', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Song', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['jukebox_core.Song'])),
            ('Created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('jukebox_core', ['History'])

        # Adding M2M table for field User on 'History'
        db.create_table('jukebox_core_history_User', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('history', models.ForeignKey(orm['jukebox_core.history'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('jukebox_core_history_User', ['history_id', 'user_id'])

        # Adding model 'Player'
        db.create_table('jukebox_core_player', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('Pid', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('jukebox_core', ['Player'])


    def backwards(self, orm):
        # Removing unique constraint on 'Favourite', fields ['Song', 'User']
        db.delete_unique('jukebox_core_favourite', ['Song_id', 'User_id'])

        # Deleting model 'Artist'
        db.delete_table('jukebox_core_artist')

        # Deleting model 'Genre'
        db.delete_table('jukebox_core_genre')

        # Deleting model 'Album'
        db.delete_table('jukebox_core_album')

        # Deleting model 'Song'
        db.delete_table('jukebox_core_song')

        # Deleting model 'Queue'
        db.delete_table('jukebox_core_queue')

        # Removing M2M table for field User on 'Queue'
        db.delete_table('jukebox_core_queue_User')

        # Deleting model 'Favourite'
        db.delete_table('jukebox_core_favourite')

        # Deleting model 'History'
        db.delete_table('jukebox_core_history')

        # Removing M2M table for field User on 'History'
        db.delete_table('jukebox_core_history_User')

        # Deleting model 'Player'
        db.delete_table('jukebox_core_player')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'jukebox_core.album': {
            'Artist': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Artist']"}),
            'Meta': {'ordering': "['Title']", 'object_name': 'Album'},
            'Title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.artist': {
            'Meta': {'ordering': "['Name']", 'object_name': 'Artist'},
            'Name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.favourite': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'ordering': "['-Created']", 'unique_together': "(('Song', 'User'),)", 'object_name': 'Favourite'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']"}),
            'User': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.genre': {
            'Meta': {'ordering': "['Name']", 'object_name': 'Genre'},
            'Name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.history': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'ordering': "['-Created']", 'object_name': 'History'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']"}),
            'User': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'null': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.player': {
            'Meta': {'object_name': 'Player'},
            'Pid': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.queue': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'object_name': 'Queue'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']", 'unique': 'True'}),
            'User': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.song': {
            'Album': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Album']", 'null': 'True'}),
            'Artist': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Artist']"}),
            'Filename': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'Genre': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Genre']", 'null': 'True'}),
            'Length': ('django.db.models.fields.IntegerField', [], {}),
            'Meta': {'ordering': "['Title', 'Artist', 'Album']", 'object_name': 'Song'},
            'Title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'Year': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['jukebox_core']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_album_Artist
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Album.Artist'
        db.delete_column('jukebox_core_album', 'Artist_id')


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Album.Artist'
        raise RuntimeError("Cannot reverse this migration. 'Album.Artist' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'jukebox_core.album': {
            'Meta': {'ordering': "['Title']", 'object_name': 'Album'},
            'Title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.artist': {
            'Meta': {'ordering': "['Name']", 'object_name': 'Artist'},
            'Name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.favourite': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'ordering': "['-Created']", 'unique_together': "(('Song', 'User'),)", 'object_name': 'Favourite'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']"}),
            'User': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.genre': {
            'Meta': {'ordering': "['Name']", 'object_name': 'Genre'},
            'Name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.history': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'ordering': "['-Created']", 'object_name': 'History'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']"}),
            'User': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'null': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.player': {
            'Meta': {'object_name': 'Player'},
            'Pid': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.queue': {
            'Created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'Meta': {'object_name': 'Queue'},
            'Song': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Song']", 'unique': 'True'}),
            'User': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'jukebox_core.song': {
            'Album': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Album']", 'null': 'True'}),
            'Artist': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Artist']"}),
            'Filename': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'Genre': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['jukebox_core.Genre']", 'null': 'True'}),
            'Length': ('django.db.models.fields.IntegerField', [], {}),
            'Meta': {'ordering': "['Title', 'Artist', 'Album']", 'object_name': 'Song'},
            'Title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'Year': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['jukebox_core']
########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-

from django.db import models
from django.contrib.auth.models import User
from django.contrib.syndication.views import Feed
import time

class Artist(models.Model):
    class Meta:
        ordering = ['Name']

    def __unicode__(self):
        return "%s" % self.Name

    Name = models.CharField(max_length=200)


class Genre(models.Model):
    class Meta:
        ordering = ['Name']

    def __unicode__(self):
        return "%s" % self.Name

    Name = models.CharField(max_length=200)


class Album(models.Model):
    class Meta:
        ordering = ['Title']

    def __unicode__(self):
        return "%s" % self.Title

    Title = models.CharField(max_length=200)


class Song(models.Model):
    class Meta:
        ordering = ['Title', 'Artist', 'Album']

    def __unicode__(self):
        return "%s - %s" % (self.Artist.Name, self.Title)

    Artist = models.ForeignKey(Artist)
    Album = models.ForeignKey(Album, null=True)
    Genre = models.ForeignKey(Genre, null=True)
    Title = models.CharField(max_length=200)
    Year = models.IntegerField(null=True)
    Length = models.IntegerField()
    Filename = models.CharField(max_length=1000)


class Queue(models.Model):
    Song = models.ForeignKey(Song, unique=True)
    User = models.ManyToManyField(User)
    Created = models.DateTimeField(auto_now_add=True)


class Favourite(models.Model):
    class Meta:
        unique_together = ("Song", "User")
        ordering = ['-Created']

    Song = models.ForeignKey(Song)
    User = models.ForeignKey(User)
    Created = models.DateTimeField(auto_now_add=True)


class History(models.Model):
    class Meta:
        ordering = ['-Created']

    Song = models.ForeignKey(Song)
    User = models.ManyToManyField(User, null=True)
    Created = models.DateTimeField(auto_now_add=True)


class Player(models.Model):
    Pid = models.IntegerField()


class QueueFeed(Feed):
    title = "Jukebox Queue Feed"
    link = "/queue/"
    description = "Top song in the queue"

    def items(self):
        return Queue.objects.all()[:1]

    def item_title(self, item):
        return item.Song.Title


    def item_description(self, item):
        return unicode(item.Song.Title) + " by " + \
                unicode(item.Song.Artist) + " from " + \
                unicode(item.Song.Album)


    def item_link(self, item):
        # Not sure what to do with url as there isn't any unque url for song
        return "/queue/#" + unicode(int(round(time.time() * 1000)))


########NEW FILE########
__FILENAME__ = api
# -*- coding: UTF-8 -*-

from django.test import TestCase, Client
from django.db import transaction
import base64
from jukebox.jukebox_core.models import Artist, Album, Genre, Song
from django.contrib.auth.models import User


class ApiTestBase(TestCase):
    user = None
    username = "TestUser"
    email = "test@domain.org"
    password = "TestPassword"
    passwords = {}

    def setUp(self):
        transaction.rollback()

        # register test user and setup auth
        self.user = self.addUser(self.username, self.email, self.password)

    def httpGet(self, url, params={}, user=None):
        c = Client()
        return c.get(url, params, HTTP_AUTHORIZATION=self.getAuth(user))

    def httpPost(self, url, params={}, user=None):
        c = Client()
        return c.post(url, params, HTTP_AUTHORIZATION=self.getAuth(user))

    def httpDelete(self, url, params={}, user=None):
        c = Client()
        return c.delete(url, params, HTTP_AUTHORIZATION=self.getAuth(user))

    def getAuth(self, user=None):
        if user is None:
            user = self.user
        username = user.username
        password = self.passwords[user.id]

        return "Basic %s" % base64.encodestring(
            '%s:%s' % (username, password)
        ).strip()


    def addArtist(self, name="TestArist"):
        artist = Artist(
            Name=name
        )
        artist.save()
        return artist

    def addAlbum(self, title="TestTitle"):
        album = Album(
            Title=title
        )
        album.save()
        return album

    def addGenre(self, name="TestGenre"):
        genre = Genre(
            Name=name
        )
        genre.save()
        return genre

    def addSong(
        self,
        artist,
        album = None,
        genre = None,
        title="TestTitle",
        year=2000,
        length=100,
        filename="/path/to/test.mp3"
    ):
        # save a song
        song = Song(
            Artist=artist,
            Album=album,
            Genre=genre,
            Title=title,
            Year=year,
            Length=length,
            Filename=filename
        )
        song.save()
        return song

    def addUser(self, username, email, password):
        user = User.objects.create_user(username, email, password)
        self.passwords[user.id] = password
        return user

########NEW FILE########
__FILENAME__ = api_albums
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase


class ApiAlbumsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 0)

    def testIndex(self):
        album = self.addAlbum()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], album.id)

    def testIndexOrderByAlbum(self):
        album_a = self.addAlbum(title="A Title")
        album_b = self.addAlbum(title="B Title")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?order_by=album"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], album_a.id)
        self.assertEquals(result["itemList"][1]["id"], album_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?order_by=album&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], album_b.id)
        self.assertEquals(result["itemList"][1]["id"], album_a.id)

    def testCount(self):
        album_a = self.addAlbum("AAA")
        album_b = self.addAlbum("BBB")
        album_c = self.addAlbum("CCC")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], album_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], album_a.id)
        self.assertEquals(result["itemList"][1]["id"], album_b.id)
        self.assertEquals(result["itemList"][2]["id"], album_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        album_a = self.addAlbum("AAA")
        album_b = self.addAlbum("BBB")
        album_c = self.addAlbum("CCC")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], album_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], album_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/albums?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], album_c.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_artists
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase


class ApiArtistsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 0)

    def testIndex(self):
        artist = self.addArtist()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], artist.id)

    def testIndexOrderBy(self):
        artist_a = self.addArtist(name="A Name")
        artist_b = self.addArtist(name="B Name")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?order_by=artist"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], artist_a.id)
        self.assertEquals(result["itemList"][1]["id"], artist_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?order_by=artist&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], artist_b.id)
        self.assertEquals(result["itemList"][1]["id"], artist_a.id)

    def testCount(self):
        artist_a = self.addArtist()
        artist_b = self.addArtist()
        artist_c = self.addArtist()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], artist_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], artist_a.id)
        self.assertEquals(result["itemList"][1]["id"], artist_b.id)
        self.assertEquals(result["itemList"][2]["id"], artist_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        artist_a = self.addArtist()
        artist_b = self.addArtist()
        artist_c = self.addArtist()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], artist_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], artist_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/artists?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], artist_c.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_favourites
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase

# ATTENTION: order tests
# favourites are ordered by insertion date DESC per default
class ApiFavouritesTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

    def testAddAndIndex(self):
        # register second user
        user = self.addUser("TestUser2", "test2@domain.org", "TestPassword2")

        song = self.addSong(artist=self.addArtist())

        # check that song is not a favourite
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)
        self.assertFalse(result["itemList"][0]["favourite"])

        # add to favourites
        response = self.httpPost(
            "/api/v1/favourites",
            {"id": song.id}
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(content["id"], song.id)

        # check favourites list
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

        # check that song is marked as favourite
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)
        self.assertTrue(result["itemList"][0]["favourite"])

        # check favourites list of second user
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites",
                {},
                user
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

        # check that song is not marked as favourite for second user
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs",
                {},
                user
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)
        self.assertFalse(result["itemList"][0]["favourite"])

    def testDeleteAndIndex(self):
        song = self.addSong(artist=self.addArtist())

        # add to favourites
        response = self.httpPost(
            "/api/v1/favourites",
            {"id": song.id}
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(content["id"], song.id)

        # check favourites list
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

        # remove from favourites
        response = self.httpDelete(
            "/api/v1/favourites/" + str(song.id),
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["id"], str(song.id))

        # check favourites list
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

    def addFavourite(self, song):
        return self.httpPost(
            "/api/v1/favourites",
            {"id": song.id}
        )

    def testIndexOrderByTitle(self):
        song_a = self.addSong(artist=self.addArtist(), title="A Title")
        song_b = self.addSong(artist=self.addArtist(), title="B Title")
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=title"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=title&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByArtist(self):
        song_a = self.addSong(artist=self.addArtist(name="A Name"))
        song_b = self.addSong(artist=self.addArtist(name="B Name"))
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=artist"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=artist&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByAlbum(self):
        album_a = self.addAlbum("A Title")
        album_b = self.addAlbum("B Title")
        song_a = self.addSong(artist=self.addArtist(), album=album_a)
        song_b = self.addSong(artist=self.addArtist(), album=album_b)
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=album"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=album&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByYear(self):
        song_a = self.addSong(artist=self.addArtist(), year=2000)
        song_b = self.addSong(artist=self.addArtist(), year=2001)
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=year"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=year&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByGenre(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="A Genre")
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="B Genre")
        )
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=genre"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=genre&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByCreated(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        self.addFavourite(song_a)
        self.addFavourite(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=created"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?order_by=created&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testCount(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())
        self.addFavourite(song_a)
        self.addFavourite(song_b)
        self.addFavourite(song_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)
        self.assertEquals(result["itemList"][2]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())
        self.addFavourite(song_a)
        self.addFavourite(song_b)
        self.addFavourite(song_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/favourites?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_genres
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase


class ApiGenresTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 0)

    def testIndex(self):
        genre = self.addGenre()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], genre.id)

    def testIndexOrderBy(self):
        genre_a = self.addGenre(name="A Name")
        genre_b = self.addGenre(name="B Name")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?order_by=genre"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], genre_a.id)
        self.assertEquals(result["itemList"][1]["id"], genre_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?order_by=genre&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], genre_b.id)
        self.assertEquals(result["itemList"][1]["id"], genre_a.id)

    def testCount(self):
        genre_a = self.addGenre()
        genre_b = self.addGenre()
        genre_c = self.addGenre()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], genre_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], genre_a.id)
        self.assertEquals(result["itemList"][1]["id"], genre_b.id)
        self.assertEquals(result["itemList"][2]["id"], genre_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        genre_a = self.addGenre()
        genre_b = self.addGenre()
        genre_c = self.addGenre()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], genre_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], genre_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/genres?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], genre_c.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_history
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core import api
from jukebox.jukebox_core.tests.api import ApiTestBase

# ATTENTION: order tests
# favourites are ordered by insertion date DESC per default
class ApiHistoryTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

    def addSongToQueue(self, song, user=None):
        if user is None:
            user = self.user

        return self.httpPost(
            "/api/v1/queue",
            {"id": song.id},
            user
        )

    def getNextSong(self):
        songs_api = api.songs()
        return songs_api.getNextSong()

    def testAddAndIndex(self):
        song = self.addSong(artist=self.addArtist(), filename= __file__)

        # check that song is not in history
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

        # add to queue and play the song
        self.addSongToQueue(song)
        self.getNextSong()

        # check history
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testAddAndIndexMy(self):
        # register second user
        user = self.addUser("TestUser2", "test2@domain.org", "TestPassword2")

        song_a = self.addSong(artist=self.addArtist(), filename=__file__)
        song_b = self.addSong(artist=self.addArtist(), filename=__file__)

        # check that song is not in history
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

        # add to queue and play the song
        self.addSongToQueue(song_a, user)
        self.addSongToQueue(song_b)
        self.getNextSong()

        # overall history contains the song
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)

        # my history should still be empty
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

        # play my song
        self.getNextSong()

        # overall history contains both songs
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        # check my history
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)

    def testIndexOrderByTitle(self):
        song_a = self.addSong(
            artist=self.addArtist(), title="A Title", filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(), title="B Title", filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=title"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=title"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=title&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=title&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByArtist(self):
        song_a = self.addSong(
            artist=self.addArtist("A Name"), filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist("B Name"), filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=artist"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=artist"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=artist&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=artist&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByAlbum(self):
        artist = self.addArtist()
        song_a = self.addSong(
            artist=artist,
            album=self.addAlbum(title="A Title"),
            filename=__file__
        )
        song_b = self.addSong(
            artist=artist,
            album=self.addAlbum(title="B Title"),
            filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=album"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=album"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=album&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=album&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByYear(self):
        song_a = self.addSong(
            artist=self.addArtist(), filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(), year=2010, filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=year"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=year"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=year&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=year&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByGenre(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="A Name"),
            filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="B Name"),
            filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=genre"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=genre"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=genre&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=genre&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByCreated(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=created"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=created"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?order_by=created&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?order_by=created&order_direction=desc"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testCount(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        song_c = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.addSongToQueue(song_c)
        self.getNextSong()
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)
        self.assertEquals(result["itemList"][2]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)
        self.assertEquals(result["itemList"][2]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        song_c = self.addSong(
            artist=self.addArtist(),
            filename=__file__
        )
        self.addSongToQueue(song_a)
        self.addSongToQueue(song_b)
        self.addSongToQueue(song_c)
        self.getNextSong()
        self.getNextSong()
        self.getNextSong()

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/history/my?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_queue
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase

class ApiQueueTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

    def testAddAndIndex(self):
        song = self.addSong(artist=self.addArtist())

        # check that song is not in queue
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)
        self.assertFalse(result["itemList"][0]["queued"])

        # add to queue
        response = self.httpPost(
            "/api/v1/queue",
            {"id": song.id}
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(content["id"], song.id)

        # check queue
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

        # check that song is marked as queued
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)
        self.assertTrue(result["itemList"][0]["queued"])

    def testDeleteAndIndex(self):
        song = self.addSong(artist=self.addArtist())

        # add to queue
        response = self.httpPost(
            "/api/v1/queue",
            {"id": song.id}
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(content["id"], song.id)

        # check queue
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

        # remove from queue
        response = self.httpDelete(
            "/api/v1/queue/" + str(song.id),
        )
        content = simplejson.loads(
            response.content
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content["id"], str(song.id))

        # check queue
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 0)

    def addToQueue(self, song):
        return self.httpPost(
            "/api/v1/queue",
            {"id": song.id}
        )

    def testIndexOrderByTitle(self):
        song_a = self.addSong(artist=self.addArtist(), title="A Title")
        song_b = self.addSong(artist=self.addArtist(), title="B Title")
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=title"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=title&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByArtist(self):
        song_a = self.addSong(artist=self.addArtist(name="A Name"))
        song_b = self.addSong(artist=self.addArtist(name="B Name"))
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=artist"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=artist&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByAlbum(self):
        album_a = self.addAlbum(title="A Title")
        album_b = self.addAlbum(title="B Title")
        song_a = self.addSong(artist=self.addArtist(), album=album_a)
        song_b = self.addSong(artist=self.addArtist(), album=album_b)
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=album"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=album&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByYear(self):
        song_a = self.addSong(artist=self.addArtist(), year=2000)
        song_b = self.addSong(artist=self.addArtist(), year=2001)
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=year"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=year&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByGenre(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="A Genre")
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="B Genre")
        )
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=genre"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=genre&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByCreated(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        self.addToQueue(song_a)
        self.addToQueue(song_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=created"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?order_by=created&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testCount(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())
        self.addToQueue(song_a)
        self.addToQueue(song_b)
        self.addToQueue(song_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)
        self.assertEquals(result["itemList"][2]["id"], song_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())
        self.addToQueue(song_a)
        self.addToQueue(song_b)
        self.addToQueue(song_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/queue?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = api_songs
# -*- coding: UTF-8 -*-

import random, simplejson
from jukebox.jukebox_core import api
from jukebox.jukebox_core.tests.api import ApiTestBase


class ApiSongsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 0)

    def testIndex(self):
        song = self.addSong(artist=self.addArtist())

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchTermInTitle(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        song = self.addSong(artist=self.addArtist(), title=fixture)
        self.addSong(artist=self.addArtist(), title="AAAAAAAAAAAAAA")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_term=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchTermInArtistName(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        song = self.addSong(artist=self.addArtist(name=fixture))
        self.addSong(artist=self.addArtist(name="AAAAAAAAAAAAAA"))

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_term=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchTermInAlbumTitle(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        artist = self.addArtist()
        album = self.addAlbum(title=fixture)
        song = self.addSong(artist=artist, album=album)
        self.addSong(
            artist=artist,
            album=self.addAlbum(title="AAAAAAAAAAAAAA")
        )

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_term=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchTitle(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        song = self.addSong(artist=self.addArtist(), title=fixture)
        self.addSong(artist=self.addArtist(), title="AAAAAAAAAAAAAA")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_title=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchArtistName(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        song = self.addSong(artist=self.addArtist(name=fixture))
        self.addSong(artist=self.addArtist(name="AAAAAAAAAAAAAA"))

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_artist=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithSearchAlbumTitle(self):
        fixture = "thisIsATestFixtureString"
        fixturePart = fixture[0:random.randint(5, len(fixture))]

        artist = self.addArtist()
        album = self.addAlbum(title=fixture)
        song = self.addSong(artist=artist, album=album)
        self.addSong(
            artist=artist,
            album=self.addAlbum(title="AAAAAAAAAAAAAA")
        )

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?search_album=" + fixturePart
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithFilterYear(self):
        fixture = 2010
        song = self.addSong(artist=self.addArtist(), year=fixture)
        self.addSong(artist=self.addArtist(), year=2001)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?filter_year=" + str(fixture)
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithFilterGenre(self):
        genre = self.addGenre()
        song = self.addSong(artist=self.addArtist(), genre=genre)
        self.addSong(artist=self.addArtist(), genre=self.addGenre())

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?filter_genre=" + str(genre.id)
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithFilterAlbumId(self):
        artist = self.addArtist()
        album = self.addAlbum(title="Foo")
        song = self.addSong(artist=artist, album=album)
        self.addSong(artist=artist, album=self.addAlbum(title="Bar"))

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?filter_album_id=" + str(album.id)
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexWithFilterArtistId(self):
        artist = self.addArtist()
        song = self.addSong(artist=artist)
        self.addSong(artist=self.addArtist())

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?filter_artist_id=" + str(artist.id)
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song.id)

    def testIndexOrderByTitle(self):
        song_a = self.addSong(artist=self.addArtist(), title="A Title")
        song_b = self.addSong(artist=self.addArtist(), title="B Title")

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=title"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=title&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByArtist(self):
        song_a = self.addSong(artist=self.addArtist(name="A Name"))
        song_b = self.addSong(artist=self.addArtist(name="B Name"))

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=artist"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=artist&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByAlbum(self):
        artist = self.addArtist()
        album_a = self.addAlbum(title="A Title")
        album_b = self.addAlbum(title="B Title")
        song_a = self.addSong(artist=artist, album=album_a)
        song_b = self.addSong(artist=artist, album=album_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=album"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=album&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByYear(self):
        song_a = self.addSong(artist=self.addArtist(), year=2000)
        song_b = self.addSong(artist=self.addArtist(), year=2001)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=year"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=year&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByGenre(self):
        song_a = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="A Name")
        )
        song_b = self.addSong(
            artist=self.addArtist(),
            genre=self.addGenre(name="B Name")
        )

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=genre"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=genre&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testIndexOrderByLength(self):
        song_a = self.addSong(artist=self.addArtist(), length=100)
        song_b = self.addSong(artist=self.addArtist(), length=200)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=length"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?order_by=length&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertEquals(result["itemList"][1]["id"], song_a.id)

    def testCount(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertEquals(result["itemList"][1]["id"], song_b.id)
        self.assertEquals(result["itemList"][2]["id"], song_c.id)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        song_a = self.addSong(artist=self.addArtist())
        song_b = self.addSong(artist=self.addArtist())
        song_c = self.addSong(artist=self.addArtist())

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_a.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_b.id)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/songs?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["id"], song_c.id)
        self.assertFalse(result["hasNextPage"])

    def testGetNextSongRandom(self):
        song = self.addSong(artist=self.addArtist(), filename=__file__)

        songs_api = api.songs()
        result = songs_api.getNextSong()

        self.assertEquals(result, song)

        # check if song has been added to history
        history_api = api.history()
        result = history_api.index()

        self.assertEqual(result["itemList"][0]["id"], song.id)

    def testGetNextSongFromQueue(self):
        song = self.addSong(artist=self.addArtist(), filename=__file__)

        # add to queue
        queue_api = api.queue()
        queue_api.set_user_id(self.user.id)
        queue_api.add(song.id)

        # get next song
        songs_api = api.songs()
        result = songs_api.getNextSong()
        self.assertEquals(result, song)

        # check if song has been added to history
        history_api = api.history()
        result = history_api.index()
        self.assertEqual(result["itemList"][0]["id"], song.id)

        # check if song has been removed from queue
        result = queue_api.index()
        self.assertEqual(len(result["itemList"]), 0)

########NEW FILE########
__FILENAME__ = api_years
# -*- coding: UTF-8 -*-

import simplejson
from jukebox.jukebox_core.tests.api import ApiTestBase


class ApiYearsTest(ApiTestBase):
    def testIndexEmpty(self):
        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 0)

    def testIndex(self):
        year = 2000
        self.addSong(artist=self.addArtist(), year=year)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["year"], year)

    def testIndexOrderBy(self):
        year_a = 2000
        year_b = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?order_by=year"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["year"], year_a)
        self.assertEquals(result["itemList"][1]["year"], year_b)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?order_by=year&order_direction=desc"
            ).content
        )

        self.assertEquals(len(result["itemList"]), 2)
        self.assertEquals(result["itemList"][0]["year"], year_b)
        self.assertEquals(result["itemList"][1]["year"], year_a)

    def testCount(self):
        year_a = 2000
        year_b = 2005
        year_c = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)
        self.addSong(artist=self.addArtist(), year=year_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?count=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["year"], year_a)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?count=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 3)
        self.assertEquals(result["itemList"][0]["year"], year_a)
        self.assertEquals(result["itemList"][1]["year"], year_b)
        self.assertEquals(result["itemList"][2]["year"], year_c)
        self.assertFalse(result["hasNextPage"])

    def testCountAndPage(self):
        year_a = 2000
        year_b = 2005
        year_c = 2010
        self.addSong(artist=self.addArtist(), year=year_a)
        self.addSong(artist=self.addArtist(), year=year_b)
        self.addSong(artist=self.addArtist(), year=year_c)

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?count=1&page=1"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["year"], year_a)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?count=1&page=2"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["year"], year_b)
        self.assertTrue(result["hasNextPage"])

        result = simplejson.loads(
            self.httpGet(
                "/api/v1/years?count=1&page=3"
            ).content
        )
        self.assertEquals(len(result["itemList"]), 1)
        self.assertEquals(result["itemList"][0]["year"], year_c)
        self.assertFalse(result["hasNextPage"])

########NEW FILE########
__FILENAME__ = urls
# -*- coding: UTF-8 -*-

from django.conf.urls import patterns, url
import views

urlpatterns = patterns("",
    url(
        r"^api/v1/songs$",
        views.songs.as_view(),
        name="jukebox_api_songs"
    ),
    url(
        r"^api/v1/songs/skip$",
        views.songs_skip.as_view(),
        name="jukebox_api_songs_skip"
    ),
    url(
        r"^api/v1/songs/current",
        views.songs_current.as_view(),
        name="jukebox_api_songs_current"
    ),
    url(
        r"^api/v1/artists$",
        views.artists.as_view(),
        name="jukebox_api_artists"
    ),
    url(
        r"^api/v1/albums$",
        views.albums.as_view(),
        name="jukebox_api_albums"
    ),
    url(
        r"^api/v1/genres$",
        views.genres.as_view(),
        name="jukebox_api_genres"
    ),
    url(
        r"^api/v1/years$",
        views.years.as_view(),
        name="jukebox_api_years"
    ),
    url(
        r"^api/v1/history$",
        views.history.as_view(),
        name="jukebox_api_history"
    ),
    url(
        r"^api/v1/history/my$",
        views.history_my.as_view(),
        name="jukebox_api_history_my"
    ),
    url(
        r"^api/v1/favourites$",
        views.favourites.as_view(),
        name="jukebox_api_favourites"
    ),
    url(
        r"^api/v1/favourites/(?P<song_id>[0-9]+)$",
        views.favourites_item.as_view(),
        name="jukebox_api_favourites_item"
    ),

    url(
        r"^api/v1/queue$",
        views.queue.as_view(),
        name="jukebox_api_queue"
    ),
    url(
        r"^api/v1/queue/(?P<song_id>[0-9]+)$",
        views.queue_item.as_view(),
        name="jukebox_api_queue_item"
    ),
    url(
        r"^api/v1/ping$",
        views.ping.as_view(),
        name="jukebox_api_ping"
    ),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: UTF-8 -*-
from jukebox.jukebox_core.models import Artist, Album, Song, Genre
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3NoHeaderError


class FileIndexer:
    def index(self, filename):
        # skip already indexed
        if self.is_indexed(filename):
            return

        try:
            id3 = EasyID3(filename)
            tags = {
                "artist": None,
                "title": None,
                "album": None,
                "genre": None,
                "date": None,
                "length": None,
            }

            for k, v in id3.items():
                tags[k] = v[0].lower()

            if tags["artist"] is None or tags["title"] is None:
                print "Artist or title not set in " + \
                    filename + " - skipping file"
                return

            if tags["artist"] is not None:
                tags["artist"], created = Artist.objects.get_or_create(
                    Name=tags["artist"]
                )
            if tags["album"] is not None and tags["artist"] is not None:
                tags["album"], created = Album.objects.get_or_create(
                    Title=tags["album"]
                )
            if tags["genre"] is not None:
                tags["genre"], created = Genre.objects.get_or_create(
                    Name=tags["genre"]
                )
            if tags["date"] is not None:
                try:
                    tags["date"] = int(tags["date"])
                except ValueError:
                    tags["date"] = None

            audio = MP3(filename)
            tags["length"] = int(audio.info.length)

            song = Song(
                Artist=tags["artist"],
                Album=tags["album"],
                Genre=tags["genre"],
                Title=tags["title"],
                Year=tags["date"],
                Length=tags["length"],
                Filename=filename
            )
            song.save()
        except HeaderNotFoundError:
            print "File contains invalid header data: " + filename
        except ID3NoHeaderError:
            print "File does not contain an id3 header: " + filename

    def delete(self, filename):
        # single file
        Song.objects.filter(Filename__exact=filename).delete()
        # directory
        Song.objects.filter(Filename__startswith=filename).delete()

    def is_indexed(self, filename):
        data = Song.objects.filter(Filename__exact=filename)
        if not data:
            return False
        return True

########NEW FILE########
__FILENAME__ = views
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import api, base64
import forms


class JukeboxAPIView(APIView):
    def api_set_user_id(self, request, api):
        if request.user.is_authenticated():
            api.set_user_id(request.user.id)
        return api


class songs(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        songs_api = api.songs()
        songs_api = self.api_set_user_id(request, songs_api)

        form = forms.SongsForm(request.GET)
        if form.is_valid():
            if not form.cleaned_data["search_term"] == "":
                songs_api.set_search_term(
                    form.cleaned_data["search_term"]
                )
            if not form.cleaned_data["search_title"] == "":
                songs_api.set_search_title(
                    form.cleaned_data["search_title"]
                )
            if not form.cleaned_data["search_artist"] == "":
                songs_api.set_search_artist_name(
                    form.cleaned_data["search_artist"]
                )
            if not form.cleaned_data["search_album"] == "":
                songs_api.set_search_album_title(
                    form.cleaned_data["search_album"]
                )

            if not form.cleaned_data["filter_artist_id"] is None:
                songs_api.set_filter_artist_id(
                    form.cleaned_data["filter_artist_id"]
                )
            if not form.cleaned_data["filter_album_id"] is None:
                songs_api.set_filter_album_id(
                    form.cleaned_data["filter_album_id"]
                )
            if not form.cleaned_data["filter_genre"] is None:
                songs_api.set_filter_genre(
                    form.cleaned_data["filter_genre"]
                )
            if not form.cleaned_data["filter_year"] is None:
                songs_api.set_filter_year(
                    form.cleaned_data["filter_year"]
                )

            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                songs_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                songs_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                songs_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        result = songs_api.index(page)
        result["form"] = form.cleaned_data
        return Response(
            data=result
        )


class songs_current(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        history = api.history()
        current = {}
        try:
            current = history.getCurrent()
        except:
            pass

        return Response(
            data=current
        )


class songs_skip(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        songs_api = api.songs()
        songs_api.skipCurrentSong()
        return Response("")

class artists(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        artists_api = api.artists()

        form = forms.ArtistsForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                artists_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                artists_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                artists_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=artists_api.index(page)
        )


class albums(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        albums_api = api.albums()

        form = forms.AlbumsForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                albums_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                albums_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                albums_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=albums_api.index(page)
        )


class genres(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        genres_api = api.genres()

        form = forms.GenresForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                genres_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                genres_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                genres_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=genres_api.index(page)
        )


class years(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        years_api = api.years()

        form = forms.YearsForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                years_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                years_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                years_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=years_api.index(page)
        )


class history(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        history_api = api.history()
        history_api = self.api_set_user_id(request, history_api)

        form = forms.HistoryForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                history_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                history_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                history_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=history_api.index(page)
        )


class history_my(JukeboxAPIView):
    permissions = (IsAuthenticated, )

    def get(self, request):
        request.session.modified = True

        page = 1
        history_api = api.history_my()
        history_api = self.api_set_user_id(request, history_api)

        form = forms.HistoryForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                history_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                history_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                history_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        return Response(
            data=history_api.index(page)
        )


class queue(JukeboxAPIView):
    permissions = (IsAuthenticated, )
    form = forms.IdForm

    def get(self, request):
        request.session.modified = True

        page = 1
        queue_api = api.queue()
        queue_api = self.api_set_user_id(request, queue_api)

        form = forms.QueueForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                queue_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                queue_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                queue_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        result = queue_api.index(page)
        for k, v in enumerate(result["itemList"]):
            result["itemList"][k]["url"] = reverse(
                "jukebox_api_queue_item",
                kwargs={"song_id": v["id"]}
            )
        return Response(
            data=result
        )

    def post(self, request):
        request.session.modified = True

        queue_api = api.queue()
        queue_api = self.api_set_user_id(request, queue_api)

        try:
            song_id = queue_api.add(self.request.POST["id"])
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    'id': int(self.request.POST['id'])
                },
                headers={"Location": reverse(
                    "jukebox_api_queue_item",
                    kwargs={"song_id": song_id}
                )}
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            print e
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class queue_item(JukeboxAPIView):
    permissions = (IsAuthenticated, )
    form = forms.IdForm

    def get(self, request, song_id):
        request.session.modified = True

        queue_api = api.queue()
        queue_api = self.api_set_user_id(request, queue_api)

        try:
            item = queue_api.get(song_id)
            item["url"] = reverse(
                "jukebox_api_queue_item",
                kwargs={"song_id": item["id"]}
            )
            return Response(
                data=item
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            print e
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, song_id):
        request.session.modified = True

        queue_api = api.queue()
        queue_api = self.api_set_user_id(request, queue_api)

        try:
            return Response(
                data=queue_api.remove(song_id)
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class favourites(JukeboxAPIView):
    permissions = (IsAuthenticated, )
    form = forms.IdForm

    def get(self, request):
        request.session.modified = True

        page = 1
        favourites_api = api.favourites()
        favourites_api = self.api_set_user_id(request, favourites_api)

        form = forms.FavouritesForm(request.GET)
        if form.is_valid():
            if (not form.cleaned_data["order_by"] == "" and
                not form.cleaned_data["order_direction"] == ""):
                favourites_api.set_order_by(
                    form.cleaned_data["order_by"],
                    form.cleaned_data["order_direction"]
                )
            elif not form.cleaned_data["order_by"] == "":
                favourites_api.set_order_by(form.cleaned_data["order_by"])

            if not form.cleaned_data["count"] is None:
                favourites_api.set_count(form.cleaned_data["count"])
            if not form.cleaned_data["page"] is None:
                page = form.cleaned_data["page"]

        result = favourites_api.index(page)
        for k, v in enumerate(result["itemList"]):
            result["itemList"][k]["url"] = reverse(
                "jukebox_api_favourites_item",
                kwargs={"song_id": v["id"]}
            )
        return Response(
            data=result
        )

    def post(self, request):
        request.session.modified = True

        favourites_api = api.favourites()
        favourites_api = self.api_set_user_id(request, favourites_api)

        try:
            song_id = favourites_api.add(self.request.POST["id"])
            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    'id': int(self.request.POST['id']),
                },
                headers={"Location": reverse(
                    "jukebox_api_favourites_item",
                    kwargs={"song_id": song_id}
                )}
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            print e
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class favourites_item(JukeboxAPIView):
    permissions = (IsAuthenticated, )
    form = forms.IdForm

    def get(self, request, song_id):
        request.session.modified = True

        favourites_api = api.favourites()
        favourites_api = self.api_set_user_id(request, favourites_api)

        try:
            item = favourites_api.get(song_id)
            item["url"] = reverse(
                "jukebox_api_favourites_item",
                kwargs={"song_id": item["id"]}
            )
            return Response(
                data=item
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            print e
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, song_id):
        request.session.modified = True

        favourites_api = api.favourites()
        favourites_api = self.api_set_user_id(request, favourites_api)

        try:
            return Response(
                data=favourites_api.remove(song_id)
            )
        except ObjectDoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception, e:
            print e
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ping(JukeboxAPIView):
    def get(self, request):
        request.session.modified = True
        return Response(
            data= {
                "ping": True
            }
        )

########NEW FILE########
__FILENAME__ = urls
# -*- coding: UTF-8 -*-

from django.conf.urls import patterns, url
from jukebox.jukebox_core.models import QueueFeed
import views

js_info_dict = {
    'packages': (
        'jukebox_web',
    ),
}

urlpatterns = patterns("",
    url(r"^$", views.index, name="jukebox_web_index"),
    url(r"^login$", views.login, name="jukebox_web_login"),
    url(r"^login/error$", views.login_error, name="jukebox_web_login_error"),
    url(
        r"^language/set/(?P<language>[-a-z]{5}|[a-z]{2})",
        views.language,
        name="jukebox_web_language"
    ),
    url(r"^logout$", views.logout, name="jukebox_web_logout"),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),

     # RSS feed url
    (r'^feed/$', QueueFeed()),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: UTF-8 -*-

from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect
from django.contrib.auth import logout as auth_logout
from django.template import RequestContext
from django.contrib.messages.api import get_messages
from django.conf import settings
from jukebox.jukebox_core.models import Song, Genre

def index(request):
    if request.user.is_authenticated():
        request.session.set_expiry(settings.SESSION_TTL)

        genres = Genre.objects.all()
        years = Song.objects.values("Year").distinct()
        years = years.exclude(Year=None).exclude(Year=0).order_by("Year")

        context = {
            "username": request.user.get_full_name(),
            "genres": genres,
            "years": years
        }
        context.update(csrf(request))
        return render_to_response('index.html', context)
    else:
        return HttpResponseRedirect('login')

def login(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('index')
    else:
        return render_to_response(
            'login.html',
            {
                "backends": settings.SOCIAL_AUTH_ENABLED_BACKENDS,
            },
            RequestContext(request)
        )

def login_error(request):
    messages = get_messages(request)
    return render_to_response(
        'login.html',
        {"error": messages},
        RequestContext(request)
    )

def logout(request):
    auth_logout(request)
    return HttpResponseRedirect('/')

def language(request, language):
    from django.utils.translation import check_for_language
    from django.utils import translation

    response = HttpResponseRedirect("/")
    if language and check_for_language(language):
        if hasattr(request, "session"):
            request.session["django_language"] = language
        else:
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        translation.activate(language)

    return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os
import pkgutil
import sys

BASE_DIR = os.path.normpath(os.path.dirname(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

JUKEBOX_STORAGE_PATH = os.path.join(
    os.path.expanduser('~'),
    '.jukebox',
)
if not os.path.exists(JUKEBOX_STORAGE_PATH):
    try:
        os.makedirs(JUKEBOX_STORAGE_PATH, 0750)
    except os.error:
        JUKEBOX_STORAGE_PATH = BASE_DIR

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(
            JUKEBOX_STORAGE_PATH,
            'db.sqlite'
        ),
    }
}

SITE_ID = 1

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'
LANGUAGES = (
    ('de', 'Deutsch'),
    ('en', 'English'),
    ('pt-br', 'Brazilian Portuguese'),
)
USE_I18N = True
USE_L10N = True

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'jukebox_web/templates'),
)

ADMIN_MEDIA_PREFIX = '/static/admin/'

ROOT_URLCONF = 'jukebox.urls'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'jukebox_web/locale'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'rest_framework',
    'social_auth',
    'south',
    'jukebox_core',
    'jukebox_web',
)

# automatically add jukebox plugins
for item in pkgutil.iter_modules():
    if str(item[1]).startswith('jukebox_'):
        INSTALLED_APPS += (str(item[1]), )

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'social_auth.context_processors.social_auth_by_type_backends',
)

LOGIN_URL          = '/login'
LOGIN_ERROR_URL    = '/login/error'
LOGIN_REDIRECT_URL = '/'

SESSION_TTL = 300

sys.path.append(JUKEBOX_STORAGE_PATH)
try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings_local.example
ADMINS = (
    ("[admin_user]", "[admin_email]"),
)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = "yourSecretKey"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    [auth_backends]
)

SOCIAL_AUTH_ENABLED_BACKENDS = ([auth_backends_enabled])

[auth_data]

########NEW FILE########
__FILENAME__ = urls
# -*- coding: UTF-8 -*-

from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns("",
    url(r"^admin/", include(admin.site.urls)),
    url(r"^admin/doc/", include("django.contrib.admindocs.urls")),

    url(r'', include('jukebox.jukebox_web.urls')),
    url(r'', include('jukebox.jukebox_core.urls')),
    url(r'', include('social_auth.urls')),
)

########NEW FILE########
