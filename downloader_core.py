import os
import re
from urllib.parse import parse_qs, urlparse

import yt_dlp


def sanitize_filename(name):
    cleaned = str(name or 'album').strip()
    cleaned = re.sub(r'[\\/:*?"<>|]', '-', cleaned)
    cleaned = cleaned.replace('\n', ' ').replace('\r', '')
    return cleaned.strip() or 'album'


def get_album_name(info):
    if not isinstance(info, dict):
        return 'album'

    for key in ('playlist_title', 'album', 'title'):
        value = info.get(key)
        if value:
            return sanitize_filename(value)

    entries = info.get('entries')
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get('title'):
                return sanitize_filename(entry.get('title'))

    return 'album'


def is_single_track_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if 'list' in query or parsed.path.startswith('/playlist') or '/playlist' in parsed.path:
        return False

    if parsed.path.startswith('/watch') or parsed.path.startswith('/shorts/') or parsed.path.startswith('/live/'):
        return True

    if parsed.path.startswith('/album'):
        return False

    return True


def download_album(album_url, output_dir=None, audio_format='flac', ffmpeg_location=None):
    """Download a YouTube Music album or track."""
    try:
        base_dir = os.path.expanduser("~/Downloads") if output_dir is None else output_dir
        os.makedirs(base_dir, exist_ok=True)
        is_single = is_single_track_url(album_url)

        info_probe = yt_dlp.YoutubeDL({
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }).extract_info(album_url, download=False)

        album_name = get_album_name(info_probe)
        target_dir = os.path.join(base_dir, album_name)
        os.makedirs(target_dir, exist_ok=True)

        outtmpl = os.path.join(target_dir, '%(title)s.%(ext)s')
        if not is_single:
            outtmpl = os.path.join(target_dir, '%(playlist_index)02d - %(title)s.%(ext)s')

        ydl_opts = {
            'format': (
                'bestaudio[ext=m4a]/bestaudio/best'
                if audio_format == 'm4a-original'
                else 'bestaudio/best'
            ),
            'outtmpl': outtmpl,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'noplaylist': False,
        }
        if audio_format not in ('best', 'm4a-original'):
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '0',
            }]
        if ffmpeg_location:
            ydl_opts['ffmpeg_location'] = ffmpeg_location

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading {'track' if is_single else 'album'} from: {album_url}")
            info = ydl.extract_info(album_url, download=True)
            entries = info.get('entries') if isinstance(info, dict) else None
            if isinstance(entries, list):
                song_count = len([entry for entry in entries if entry is not None])
            else:
                song_count = (
                    info.get('playlist_count') or info.get('count') or 1
                    if isinstance(info, dict)
                    else 1
                )
            if is_single:
                print("\nSuccessfully downloaded 1 track!")
            else:
                print(f"\nSuccessfully downloaded {song_count} songs!")
            print(f"Saved to: {os.path.abspath(target_dir)}")
            return True
    except Exception as error:
        print(f"Error downloading album: {error}")
        return False


def parse_urls(raw_input):
    if not raw_input:
        return []

    parts = re.split(r'[\s,]+', raw_input)
    return [
        part.strip()
        for part in parts
        if part.strip().startswith(('http://', 'https://'))
    ]
