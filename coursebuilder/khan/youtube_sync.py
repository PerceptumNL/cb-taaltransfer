import cgi
import datetime
import logging
import re
from urlparse import urlparse

import third_party.gdata.youtube
import third_party.gdata.youtube.service
import third_party.gdata.alt.appengine

from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext import db

from models2 import Setting, Video, Playlist, VideoPlaylist
import request_handler
import user_util


def youtube_get_video_data(video):
    data_dict = youtube_get_video_data_dict(video.youtube_id)

    if data_dict is None:
        return None

    for prop, value in data_dict.iteritems():
        setattr(video, prop, value)

    return video




def youtube_get_video_data_dict(youtube_id):
    yt_service = third_party.gdata.youtube.service.YouTubeService()

    # Now that we run these queries from the App Engine servers, we need to
    # explicitly specify our developer_key to avoid being lumped together w/ rest of GAE and
    # throttled by YouTube's "Too many request" quota
    yt_service.developer_key = "AI39si5NKByjOThtM6t1gnmg4N9HkzGPHHkVvRUybKuPG53277wY0Bs4zcvi-G4JiFioRs0738gaE01k1rX-_6-mIHp9jg1twQ"
    yt_service.client_id = "n/a"

    logging.info("trying to get info for youtube_id: %s" % youtube_id)
    try:
        video = yt_service.GetYouTubeVideoEntry(video_id=youtube_id)
    except:
        video = None
    if video:
        video_data = {"youtube_id" : youtube_id,
                      "title" : video.media.title.text.decode('utf-8'),
                      "url" : video.media.player.url.decode('utf-8'),
                      "duration" : int(video.media.duration.seconds)}

        if video.statistics:
            video_data["views"] = int(video.statistics.view_count)

        video_data["description"] = (video.media.description.text or '').decode('utf-8')
        video_data["keywords"] = (video.media.keywords.text or '').decode('utf-8')

        potential_id = re.sub('[^a-z0-9]', '-', video_data["title"].lower());
        potential_id = re.sub('-+$', '', potential_id)  # remove any trailing dashes (see issue 1140)
        potential_id = re.sub('^-+', '', potential_id)  # remove any leading dashes (see issue 1526)

        number_to_add = 0
        current_id = potential_id
        while True:
            query = Video.all()
            query.filter('readable_id=', current_id)
            if (query.get() is None): #id is unique so use it and break out
                video_data["readable_id"] = current_id
                break
            else: # id is not unique so will have to go through loop again
                number_to_add+=1
                current_id = potential_id+'-'+number_to_add

        return video_data

    return None


class YouTubeSyncStep:
    START = 0
    UPDATE_VIDEO_AND_PLAYLIST_DATA = 1 # Sets all VideoPlaylist.last_live_association_generation = Setting.last_youtube_sync_generation_start
    UPDATE_VIDEO_AND_PLAYLIST_READABLE_NAMES = 2
    COMMIT_LIVE_ASSOCIATIONS = 3 # Put entire set of video_playlists in bulk according to last_live_association_generation
    INDEX_VIDEO_DATA = 4
    INDEX_PLAYLIST_DATA = 5
    REGENERATE_LIBRARY_CONTENT = 6

class YouTubeSyncStepLog(db.Model):
    step = db.IntegerProperty()
    generation = db.IntegerProperty()
    dt = db.DateTimeProperty(auto_now_add = True)

from models.courses import Course
from controllers import sites
def get_all_videos(self):
    sites.set_path_info("/")
    self.app_context = sites.get_course_for_current_request()
    self.course = Course(self)
    units = self.course.get_units()
    all_lessons = []
    for unit in units:
        lessons = self.course.get_lessons(unit.unit_id)
        for lesson in lessons:
            all_lessons.append(lesson)

    videos = []
    for lesson in all_lessons:
        if lesson.video:
            videos.append(lesson.video)
    return videos
            
class ListTest(request_handler.RequestHandler):
    @user_util.open_access
    def get(self, path):
        self.response.out.write(get_all_videos(self))
        

class YouTubeSync(request_handler.RequestHandler):

    #@user_util.manual_access_checking  # superuser-only via app.yaml (/admin)
    @user_util.open_access
    def get(self):
        if self.request_bool("start", default = False):
            self.task_step(0)
            self.response.out.write("Sync started")
        else:
            latest_logs_query = YouTubeSyncStepLog.all()
            latest_logs_query.order("-dt")
            latest_logs = latest_logs_query.fetch(10)

            self.response.out.write("Latest sync logs:<br/><br/>")
            for sync_log in latest_logs:
                self.response.out.write("Step: %s, Generation: %s, Date: %s<br/>" % (sync_log.step, sync_log.generation, sync_log.dt))
            self.response.out.write("<br/><a href='/admin/youtubesync?start=1'>Start New Sync</a>")

    @user_util.manual_access_checking  # superuser-only via app.yaml (/admin)
    def post(self):
        # Protected for admins only by app.yaml so taskqueue can hit this URL
        step = self.request_int("step", default = 0)

        if step == YouTubeSyncStep.START:
            self.startYouTubeSync()
        elif step == YouTubeSyncStep.UPDATE_VIDEO_AND_PLAYLIST_DATA:
            self.updateVideoAndPlaylistData2()
        elif step == YouTubeSyncStep.UPDATE_VIDEO_AND_PLAYLIST_READABLE_NAMES:
            self.updateVideoAndPlaylistReadableNames()
        elif step == YouTubeSyncStep.COMMIT_LIVE_ASSOCIATIONS:
            self.commitLiveAssociations()
        elif step == YouTubeSyncStep.INDEX_VIDEO_DATA:
            self.indexVideoData()
        elif step == YouTubeSyncStep.INDEX_PLAYLIST_DATA:
            self.indexPlaylistData()
        elif step == YouTubeSyncStep.REGENERATE_LIBRARY_CONTENT:
            self.regenerateLibraryContent()

        log = YouTubeSyncStepLog()
        log.step = step
        log.generation = int(Setting.last_youtube_sync_generation_start())
        log.put()

        if step < YouTubeSyncStep.REGENERATE_LIBRARY_CONTENT:
            self.task_step(step + 1)

    def task_step(self, step):
        taskqueue.add(url='/admin/youtubesync/%s' % step, queue_name='youtube-sync-queue', params={'step': step})

    def startYouTubeSync(self):
        Setting.last_youtube_sync_generation_start(int(Setting.last_youtube_sync_generation_start()) + 1)

    def updateVideoAndPlaylistData2(self):
        self.response.out.write('<html>')

        yt_service = third_party.gdata.youtube.service.YouTubeService()

        # Now that we run these queries from the App Engine servers, we need to
        # explicitly specify our developer_key to avoid being lumped together w/ rest of GAE and
        # throttled by YouTube's "Too many request" quota
        yt_service.developer_key = "AI39si6ctKTnSR_Vx7o7GpkpeSZAKa6xjbZz6WySzTvKVYRDAO7NHBVwofphk82oP-OSUwIZd0pOJyNuWK8bbOlqzJc9OFozrQ"
        yt_service.client_id = "n/a"

        video_youtube_id_dict = Video.get_dict(Video.all(), lambda video: video.youtube_id)
        video_playlist_key_dict = VideoPlaylist.get_key_dict(VideoPlaylist.all())

        association_generation = int(Setting.last_youtube_sync_generation_start())

        playlist_start_index = 1

        #start_index = i * 50 + 1
        #video_feed = yt_service.GetYouTubePlaylistVideoFeed(uri=playlist_uri + '?start-index=' + str(start_index) + '&max-results=50')
        video_data_list = []

        #if len(video_feed.entry) <= 0:
        #    # No more videos in playlist
        #    break
        videos = get_all_videos(self)

        for video in videos:
            video = yt_service.GetYouTubeVideoEntry(video_id=video)
            self.response.out.write('video')
            

            if (video.media.player == None):
                continue
            video_id = cgi.parse_qs(urlparse(video.media.player.url).query)['v'][0].decode('utf-8')

            video_data = None
            if video_youtube_id_dict.has_key(video_id):
                video_data = video_youtube_id_dict[video_id]

            if not video_data:
                video_data = Video(youtube_id=video_id)
                self.response.out.write('<p><strong>Creating Video: ' + video.media.title.text.decode('utf-8') + '</strong>')
                video_data.playlists = []

            video_data.title = video.media.title.text.decode('utf-8')
            video_data.url = video.media.player.url.decode('utf-8')
            video_data.duration = int(video.media.duration.seconds)

            if video.statistics:
                video_data.views = int(video.statistics.view_count)

            if video.media.description.text is not None:
                video_data.description = video.media.description.text.decode('utf-8')
            else:
                video_data.decription = ' '

            if video.media.keywords.text:
                video_data.keywords = video.media.keywords.text.decode('utf-8')
            else:
                video_data.keywords = ''

            #video_data.position = video.position
            video_data_list.append(video_data)

        db.put(video_data_list)


    def updateVideoAndPlaylistReadableNames(self):
        # Makes sure every video and playlist has a unique "name" that can be used in URLs
        query = Video.all()
        all_videos = query.fetch(100000)
        for video in all_videos:
            potential_id = re.sub('[^a-z0-9]', '-', video.title.lower());
            potential_id = re.sub('-+$', '', potential_id)  # remove any trailing dashes (see issue 1140)
            potential_id = re.sub('^-+', '', potential_id)  # remove any leading dashes (see issue 1526)
            if video.readable_id == potential_id: # id is unchanged
                continue
            number_to_add = 0
            current_id = potential_id
            while True:
                query = Video.all()
                query.filter('readable_id=', current_id)
                if (query.get() is None): #id is unique so use it and break out
                    video.readable_id = current_id
                    video.put()
                    break
                else: # id is not unique so will have to go through loop again
                    number_to_add+=1
                    current_id = potential_id+'-'+number_to_add

    def commitLiveAssociations(self):
        pass

    def indexVideoData(self):
        videos = Video.all().fetch(10000)
        for video in videos:
            video.index()
            video.indexed_title_changed()

    def indexPlaylistData(self):
        playlists = Playlist.all().fetch(10000)
        for playlist in playlists:
            playlist.index()
            playlist.indexed_title_changed()

    def regenerateLibraryContent(self):
        taskqueue.add(url='/library_content', queue_name='youtube-sync-queue')

