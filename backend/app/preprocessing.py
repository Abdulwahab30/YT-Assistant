import re


def clean_transcript_text(text: str) -> str:
    """
    Cleans raw transcript text before chunking.

    Goals:
    - normalize whitespace
    - remove duplicated spaces
    - clean common transcript artifacts
    - keep the meaning unchanged
    """

    # Remove newlines/tabs and repeated spaces
    text = re.sub(r"\s+", " ", text)

    # Remove spaces before punctuation
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)

    # Normalize repeated punctuation lightly
    text = re.sub(r"\.{3,}", "...", text)

    return text.strip()


def preprocess_transcript_segments(transcript: list[dict]) -> list[dict]:
    """
    Converts raw transcript segments into cleaned timestamped segments.

    Input:
    [
        {"text": "...", "start": 0.0, "duration": 4.2}
    ]

    Output:
    [
        {"text": "...", "start": 0.0, "end": 4.2}
    ]
    """

    cleaned_segments = []

    for item in transcript:
        text = clean_transcript_text(item.get("text", ""))

        if not text:
            continue

        start = float(item["start"])
        end = start + float(item["duration"])

        cleaned_segments.append({
            "text": text,
            "start": start,
            "end": end
        })

    return cleaned_segments


def combine_segments_for_splitting(segments: list[dict]) -> str:
    """
    Combines transcript segments into one text block.

    We insert sentence-like spaces so recursive splitting has cleaner text.
    """

    return " ".join(segment["text"] for segment in segments)