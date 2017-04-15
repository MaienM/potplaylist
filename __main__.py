import sys
from youtube_dl import YoutubeDL
from IPython import embed

print('Converting to DAUM PotPlayer playlist'.format(url))

# Get the playlist info
print('Fetching playlist...')
yt = YoutubeDL({ 'quiet': True })
playlists = [yt.extract_info(url, download=False) for url in sys.argv[1:]]
videos = [v for pl in playlists for v in playlist['entries']]

# Write the potplayer playlist
print('Writing playlist.dpl')
with open('playlist.dpl', 'w') as f:
    print('DAUMPLAYLIST', file=f)
    print('playname={}'.format(' + '.join([pl['name'] for pl in playlists])), file=f)
    for i, video in enumerate(videos):
        video['index'] = i + 1
        print('{index}*file*{url}'.format(**video), file=f)
        print('{index}*title*{title}'.format(**video), file=f)
        print('{index}*duration2*{duration}123'.format(**video), file=f)
        print('{index}*thumbnail*{thumbnails[0][url]}'.format(**video), file=f)

print('Done!')
