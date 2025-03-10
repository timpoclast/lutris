import json
import os
import random
import time

from lutris import settings
from lutris.database.services import ServiceGameCollection
from lutris.gui.widgets.utils import get_pixbuf
from lutris.util import system
from lutris.util.http import HTTPError, download_file
from lutris.util.log import logger

PGA_DB = settings.PGA_DB


class ServiceMedia:
    """Information about the service's media format"""

    service = NotImplemented
    size = NotImplemented
    source = "remote"  # set to local if the files don't need to be downloaded
    visible = True  # This media should be displayed as an option in the UI
    small_size = None
    dest_path = None
    file_pattern = NotImplemented
    file_format = NotImplemented
    api_field = NotImplemented
    url_pattern = "%s"

    def __init__(self):
        if self.dest_path and not system.path_exists(self.dest_path):
            os.makedirs(self.dest_path)

    def get_filename(self, slug):
        return self.file_pattern % slug

    def get_media_path(self, slug):
        """Return the absolute path of a local media file"""
        return os.path.join(self.dest_path, self.get_filename(slug))

    def exists(self, slug):
        """Whether the icon for the specified slug exists locally"""
        return system.path_exists(self.get_media_path(slug))

    def get_pixbuf_for_game(self, slug, size=None):
        image_abspath = self.get_media_path(slug)
        return get_pixbuf(image_abspath, size or self.size)

    def get_media_url(self, details):
        if self.api_field not in details:
            logger.warning("No field '%s' in API game %s", self.api_field, details)
            return
        if not details[self.api_field]:
            return
        return self.url_pattern % details[self.api_field]

    def get_media_urls(self):
        """Return URLs for icons and logos from a service"""
        if self.source == "local":
            return {}
        service_games = ServiceGameCollection.get_for_service(self.service)
        medias = {}
        for game in service_games:
            if not game["details"]:
                continue
            details = json.loads(game["details"])
            media_url = self.get_media_url(details)
            if not media_url:
                continue
            medias[game["slug"]] = media_url
        return medias

    def download(self, slug, url):
        """Downloads the banner if not present"""
        if not url:
            return
        cache_path = os.path.join(self.dest_path, self.get_filename(slug))
        if system.path_exists(cache_path, exclude_empty=True):
            return
        if system.path_exists(cache_path):
            cache_stats = os.stat(cache_path)
            # Empty files have a life time between 1 and 2 weeks, retry them after
            if time.time() - cache_stats.st_mtime < 3600 * 24 * random.choice(range(7, 15)):
                return cache_path
            os.unlink(cache_path)
        try:
            return download_file(url, cache_path, raise_errors=True)
        except HTTPError as ex:
            logger.error("Failed to download %s: %s", url, ex)

    @property
    def custom_media_storage_size(self):
        """The size this media is stored in when customized; we accept
        whatever we get when we download the media, however."""
        return self.size

    @property
    def config_ui_size(self):
        """The size this media should be shown at when in the configuration UI."""
        return self.size

    def update_desktop(self):
        """Update the desktop, if this media type appears there. Most don't."""

    def render(self):
        """Used if the media requires extra processing"""
