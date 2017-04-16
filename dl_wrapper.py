import json
import os
import re
import subprocess
import tempfile
import time

class DLWrapper(object):
    """
    Wrapper around youtube_dl that captures it's output and processes it into progress events.
    """

    def __init__(self):
        self.playlist_callbacks = []
        self.video_callbacks = []

    def add_playlist_callback(self, callback):
        """
        Playlist callbacks will fire whenever any progress is made on scanning
        the playlist index.

        The callback will be passed a dictionary in the following format:

        >>> {
        >>>     'number': 1,
        >>> }
        """
        self.playlist_callbacks.append(callback)

    def add_video_callback(self, callback):
        """
        Video callbacks will fire whenever the info of a video is scanned.

        The callback will be passed a dictionary in the following format:

        >>> {
        >>>     'number': 1,
        >>>     'total': 2,
        >>>     'data': {
        >>>         'playlist': 'Cool playlist!',
        >>>         'id': 'SoM3ViDe0ID',
        >>>         'title': 'Cool video!',
        >>>         'duration': 1234, # seconds
        >>>         'url': 'http://video.url/here.mpv',
        >>>         'thumbnail': 'http://thumbnail.url/here.png',
        >>>     },
        >>> }
        """
        self.video_callbacks.append(callback)

    PATTERN_PLAYLIST = re.compile(r'^\[.*:playlist\].*page( #(?P<num>\d+))?$')
    PATTERN_VIDEO_START = re.compile(r'^\[download\] Downloading video (?P<num>\d+) of (?P<total>\d+)$')
    PATTERN_VIDEO_END = re.compile(r'^\[info\].*JSON.*to: (?P<file>.*\.info\.json)$')

    def process(self, url):
        """
        Processes a playlist.
        """

        # Run the youtube-dl command
        outdir = tempfile.mkdtemp()
        proc = subprocess.Popen(
            ['youtube-dl', '--skip-download', '--write-info-json', '--id', url],
            cwd=outdir,
            env=os.environ.copy().update({
                'PYTHONUNBUFFERED': 'x',
            }),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )

        # Process the output
        for line in proc.stdout:
            # Playlist progress
            match = self.PATTERN_PLAYLIST.match(line)
            if match:
                event = {
                    'number': int(match.group('num') or 1),
                }
                for callback in self.playlist_callbacks:
                    callback(event)

            # Start of video info
            match = self.PATTERN_VIDEO_START.match(line)
            if match:
                match_video_start = match

            # End of video info
            match = self.PATTERN_VIDEO_END.match(line)
            if match:
                # Wait for the file to finish writing
                path = os.path.join(outdir, match.group('file'))
                attempts = 0
                while attempts < 10 and not os.path.exists(path):
                    attempts += 1
                    time.sleep(0.1 * attempts)
                    # If after 10 attempts the file still doesn't exist, we let
                    # it fall through, and the open will raise an appropriate
                    # error for us

                with open(path, 'r') as f:
                    raw_data = json.load(f)
                    raw_data['thumbnails'].append({ 'url': None })
                event = {
                    'number': int(match_video_start.group('num')),
                    'total': int(match_video_start.group('total')),
                    'data': {
                        'playlist': raw_data['playlist'],
                        'id': raw_data['id'],
                        'title': raw_data['title'],
                        'duration': raw_data['duration'],
                        'url': raw_data['url'],
                        'thumbnail': raw_data['thumbnails'][0]['url'],
                    },
                }
                for callback in self.video_callbacks:
                    callback(event)
