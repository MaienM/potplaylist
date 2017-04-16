import curses
import sys

from dl_wrapper import DLWrapper

def main(urls):
    playlists = []
    output = []
    processed = []
    index = 1

    curses.setupterm(fd=sys.stdout.fileno())
    EL = curses.tigetstr('el') or '\r'

    def event_playlist(event):
        if event['number'] == 1:
            print('Scanning playlist', end='')
        print('.', end='')

    def event_video(event):
        nonlocal index

        if event['number'] < event['total']:
            print(EL + 'Getting video info ({}/{})'.format(event['number'] + 1, event['total']), end='')
        else:
            print()
            print('Done with playlist')
            print()

        info = event['data']
        if event['number'] == 1:
            playlists.append(info['playlist'])

        if info['id'] in processed:
            return
        processed.append(info['id'])

        info['index'] = index
        output.append('{index}*title*{title}'.format(**info))
        output.append('{index}*thumbnail*{thumbnail}'.format(**info))
        output.append('{index}*duration2*{duration}123'.format(**info))
        output.append('{index}*file*{url}'.format(**info))
        index += 1

    dl = DLWrapper()
    dl.add_playlist_callback(event_playlist)
    dl.add_video_callback(event_video)

    for url in urls:
        print('Processing {}'.format(url))
        dl.process(url)

    output = [
        'DAUMPLAYLIST',
        'playname={}'.format(' + '.join(playlists)),
    ] + output + ['']
    print('Writing playlist.dpl')
    with open('playlist.dpl', 'w') as f:
        f.write('\n'.join(output))

if __name__ == '__main__':
    main(sys.argv[1:])
