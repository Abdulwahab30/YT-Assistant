from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(youtube_url: str) -> str:
    """
    Extracts the video ID from common YouTube URL formats.

    Examples:
    - https://www.youtube.com/watch?v=abc123
    - https://youtu.be/abc123
    - https://www.youtube.com/embed/abc123
    """
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


def get_transcript(youtube_url: str) -> list[dict]:
    """
    Returns transcript segments from a YouTube video.

    Output format expected by our chunking code:
    [
        {
            "text": "...",
            "start": 0.0,
            "duration": 4.2
        }
    ]
    """
    video_id = extract_video_id(youtube_url)

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