from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

from .cache import load_cached_transcript, save_cached_transcript
from .retry_utils import retry_external_call


def extract_video_id(youtube_url: str) -> str:
    parsed_url = urlparse(youtube_url)

    if parsed_url.hostname in ["www.youtube.com", "youtube.com", "m.youtube.com"]:
        if parsed_url.path == "/watch":
            query_params = parse_qs(parsed_url.query)
            return query_params["v"][0]

        if parsed_url.path.startswith("/embed/"):
            return parsed_url.path.split("/")[2]

        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/")[2]

    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")

    raise ValueError("Invalid YouTube URL")


def get_youtube_title(video_id: str) -> str:
    import urllib.request
    import re
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            match = re.search(r'<title>(.*?)</title>', html)
            if match:
                title = match.group(1)
                return title.replace(" - YouTube", "")
    except Exception:
        pass
    return "YouTube Video"


@retry_external_call()
def fetch_transcript_from_youtube(video_id: str) -> list[dict]:
    """
    Fetch transcript from YouTube with retry.
    """
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)

    transcript = []

    for snippet in fetched_transcript:
        transcript.append({
            "text": snippet.text,
            "start": snippet.start,
            "duration": snippet.duration
        })

    return transcript


def get_transcript(youtube_url: str) -> list[dict]:
    """
    Gets transcript from cache first.
    If not cached, fetches from YouTube and caches it.
    """
    video_id = extract_video_id(youtube_url)

    cached = load_cached_transcript(video_id)

    if cached is not None:
        return cached

    transcript = fetch_transcript_from_youtube(video_id)

    save_cached_transcript(video_id, transcript)

    return transcript