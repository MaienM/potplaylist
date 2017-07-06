import collections
import json
import os
import re
import subprocess
import sys
import tempfile
import time

class DLWrapper(object):
    """
    Wrapper around youtube_dl that captures it's output and processes it into progress events.
    """

    # All events supported by this class
    EVENTS = [
        'playlist.start', 'playlist.progress', 'playlist.end',
        'video.start', 'video.progress', 'video.end',
    ]

    # Extractor for which potplayer has native support, meaning the original URL can be used, allowing potplayer the chance to get more metadata
    NATIVE_EXTRACTORS = ['youtube']

    def __init__(self):
        self.event_handlers = collections.defaultdict(lambda *a: [])

    def on(self, event, callback):
        """
        Subscribe to an event.

        ## playlist.start

        Fires when the playlist index scan is started. There is no way of
        telling the amount of steps this is going to take up-front.

        >>> {
        >>>     'title': 'Cool playlist!',
        >>> }

        ## playlist.progress

        Fires when the playlist index scan is making progress.

        >>> {
        >>>     'title': 'Cool playlist!',
        >>>     'number': 1,
        >>> }

        ## playlist.end

        Fires when the playlist index scan is finished.

        >>> {
        >>>     'id': 'SoM3Pl4yL1St',
        >>>     'title': 'Cool playlist!',
        >>>     'total': 2,
        >>> }

        ## video.start

        Fires when the video scanning phase is started.

        >>> {
        >>>     'total': 2,
        >>> }

        ## video.progress

        Fires when a video is scanned.

        >>> {
        >>>     'id': 'SoM3ViDe0ID',
        >>>     'title': 'Cool video!',
        >>>     'duration': 1234,
        >>>     'url': 'http://video.url/here.mpv',
        >>>     'thumbnail': 'http://thumbnail.url/here.png',
        >>>     'number': 1,
        >>>     'total': 2,
        >>> }

        ## video.end

        Fires when the video scanning phase is completed.

        >>> {
        >>>     'total': 2,
        >>> }
        """
        if event not in self.EVENTS:
            raise ArgumentError('Unknown event {}'.format(event))
        self.event_handlers[event].append(callback)

    def off(self, event, callback=None):
        """
        Ubsubscribe from an event.

        If no callback is passed, all callbacks for the given event will be removed.
        """
        if event not in self.EVENTS:
            raise ArgumentError('Unknown event {}'.format(event))
        if callback:
            self.event_handlers[event].remove(callback)
        else:
            self.event_handlers[event] = []

    def trigger(self, event, *args):
        """
        Trigger an event.
        """
        if event not in self.EVENTS:
            raise ArgumentError('Unknown event {}'.format(event))
        for callback in self.event_handlers[event]:
            callback(*args)

    PATTERN_PLAYLIST_START = re.compile(r'^\[download\] Downloading playlist: (?P<title>.*)$')
    PATTERN_PLAYLIST_PROGRESS = re.compile(r'^.*Downloading.*page( #(?P<num>\d+))?$')
    PATTERN_VIDEO_START = re.compile(r'^\[download\] Downloading video (?P<num>\d+) of (?P<total>\d+)$')
    PATTERN_VIDEO_END = re.compile(r'^\[info\].*JSON.*to: (?P<file>.*\.info\.json)$')

    def process(self, url, *args):
        """
        Processes a playlist.
        """

        # Run the youtube-dl command
        outdir = tempfile.mkdtemp()
        cmd = ['youtube-dl', '--skip-download', '--write-info-json', '--id'] + list(args) + [url]
        print('Executing', *cmd)
        proc = subprocess.Popen(
            cmd,
            cwd=outdir,
            env=os.environ.copy().update({
                'PYTHONUNBUFFERED': 'x',
            }),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
        )

        state = 'start'
        last_event = {}
        count_event = collections.defaultdict(lambda *a: 0)
        def trigger(event, data, merge_with=None):
            nonlocal state
            state = event
            last_event[event] = data
            count_event[event] += 1
            self.trigger(event, data)

        # Process the output
        last_match = {}
        count_match = collections.defaultdict(lambda *a: 0)
        patterns = [getattr(self, k) for k in dir(self) if k.startswith('PATTERN_')]
        for line in proc.stdout:
            # Parse line
            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    break
            else:
                continue
            last_match[match.re] = match
            count_match[match.re] += 1

            if state == 'start' and match.re == self.PATTERN_PLAYLIST_START:
                trigger('playlist.start', {
                    'title': match.group('title'),
                })
                trigger('playlist.progress', {
                    **last_event['playlist.start'],
                    'number': 1,
                })
            if (state == 'playlist.start' or state == 'playlist.progress') and match.re == self.PATTERN_PLAYLIST_PROGRESS:
                trigger('playlist.progress', {
                    **last_event['playlist.start'],
                    'number': int(match.group('num')) + 1,
                })
            if state == 'playlist.progress' and match.re == self.PATTERN_VIDEO_START:
                trigger('playlist.end', {
                    **last_event['playlist.start'],
                    'total': count_event['playlist.progress'],
                })
                trigger('video.start', {
                    'total': int(match.group('total')),
                })
            if (state == 'video.start' or state == 'video.progress') and match.re == self.PATTERN_VIDEO_END:
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

                trigger('video.progress', {
                    **last_event['video.start'],
                    'playlist': raw_data['playlist'],
                    'id': raw_data['id'],
                    'title': raw_data['title'],
                    'duration': raw_data['duration'],
                    'url': raw_data['extractor'].lower() in self.NATIVE_EXTRACTORS and raw_data['webpage_url'] or raw_data['url'],
                    'thumbnail': raw_data['thumbnails'][0]['url'],
                    'number': int(last_match[self.PATTERN_VIDEO_START].group('num')),
                }, 'video.start')

        # If the process exited unsuccessfully, output the stderr to stderr
        if proc.returncode != 0:
            print()
            print('youtube-dl failed', file=sys.stderr)
            print(file=sys.stderr)
            print(proc.stderr.read(), file=sys.stderr)

        trigger('video.end', {}, 'video.start')
