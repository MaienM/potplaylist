import os
import sys

from dl_wrapper import DLWrapper
from unbuffered import Unbuffered

def main(args):
    output = []
    processed_playlist_titles = []
    processed_video_ids = []
    index = 1

    def on_playlist_start(event):
        title = event['title']
        processed_playlist_titles.append(title)
        print('Scanning playlist "{}"'.format(title), end='')

    def on_playlist_progress(event):
        print('.', end='', flush=True)

    def on_playlist_end(event):
        print()

    def on_video_progress(event):
        nonlocal index

        # Progress indicator
        print('Got video info ({number}/{total}) - {title}'.format(**event))

        # Prevent duplicate videos
        if event['id'] in processed_video_ids:
            return
        processed_video_ids.append(event['id'])

        # Store info in the output cache
        event['index'] = index
        output.append('{index}*title*{title}'.format(**event))
        output.append('{index}*thumbnail*{thumbnail}'.format(**event))
        output.append('{index}*duration2*{duration}123'.format(**event))
        output.append('{index}*file*{url}'.format(**event))
        index += 1

    def on_video_end(event):
        print('Done with playlist')
        print()

    dl = DLWrapper()
    dl.on('playlist.start', on_playlist_start)
    dl.on('playlist.progress', on_playlist_progress)
    dl.on('playlist.end', on_playlist_end)
    dl.on('video.progress', on_video_progress)
    dl.on('video.end', on_video_end)

    for arg in args:
        if ' ' in arg:
            url_args = arg.split(' ')
            url, url_args = url_args[0], url_args[1:]
        else:
            url = arg
            url_args = []

        print('Processing {}'.format(arg))
        print('Url: {}'.format(url))
        print('Args: {}'.format(url_args))

        dl.process(url, *url_args)

    # Write playlist with header
    output = [
        'DAUMPLAYLIST',
        'playname={}'.format(' + '.join(processed_playlist_titles)),
    ] + output + ['']
    print('Writing {} video(s) to playlist.dpl'.format(len(processed_video_ids)))
    with open('playlist.dpl', 'w') as f:
        f.write('\n'.join(output).encode(f.encoding, errors='replace').decode(f.encoding))

if __name__ == '__main__':
    # Unbuffered output
    sys.stdout = Unbuffered(sys.stdout)
    main(sys.argv[1:])
