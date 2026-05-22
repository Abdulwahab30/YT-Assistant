from .preprocessing import preprocess_transcript_segments, clean_transcript_text


def recursive_split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None
) -> list[str]:
    """
    Recursively splits text into chunks.

    It tries larger semantic separators first, then smaller ones.

    Separator priority:
    1. paragraph break
    2. sentence boundary
    3. comma
    4. space
    5. character fallback
    """

    if separators is None:
        separators = ["\n\n", ". ", "? ", "! ", ", ", " ", ""]

    text = clean_transcript_text(text)

    if len(text) <= chunk_size:
        return [text] if text else []

    final_chunks = []

    def split_recursive(current_text: str, separator_index: int) -> list[str]:
        if len(current_text) <= chunk_size:
            return [current_text]

        if separator_index >= len(separators):
            return [
                current_text[i:i + chunk_size]
                for i in range(0, len(current_text), chunk_size)
            ]

        separator = separators[separator_index]

        if separator == "":
            splits = list(current_text)
        else:
            splits = current_text.split(separator)

        # If separator does not split the text, try the next separator
        if len(splits) == 1:
            return split_recursive(current_text, separator_index + 1)

        chunks = []
        current_chunk = ""

        for piece in splits:
            if not piece:
                continue

            if separator:
                piece_with_sep = piece + separator
            else:
                piece_with_sep = piece

            if len(current_chunk) + len(piece_with_sep) <= chunk_size:
                current_chunk += piece_with_sep
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                if len(piece_with_sep) > chunk_size:
                    chunks.extend(split_recursive(piece_with_sep, separator_index + 1))
                    current_chunk = ""
                else:
                    current_chunk = piece_with_sep

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    base_chunks = split_recursive(text, 0)

    # Add overlap between chunks
    for i, chunk in enumerate(base_chunks):
        if i == 0:
            final_chunks.append(chunk)
        else:
            previous_chunk = final_chunks[-1]
            overlap_text = get_word_safe_overlap(previous_chunk, chunk_overlap)
            merged_chunk = clean_transcript_text(overlap_text + " " + chunk)

            if len(merged_chunk) > chunk_size + chunk_overlap:
                merged_chunk = merged_chunk[:chunk_size + chunk_overlap]

            final_chunks.append(merged_chunk)

    return final_chunks

def get_word_safe_overlap(text: str, overlap_size: int) -> str:
    """
    Returns the last overlap_size characters without starting in the middle of a word.
    """

    if len(text) <= overlap_size:
        return text

    overlap = text[-overlap_size:]

    # Move to the first space so we do not start inside a word
    first_space_index = overlap.find(" ")

    if first_space_index != -1:
        overlap = overlap[first_space_index + 1:]

    return overlap.strip()


def find_chunk_timestamps(chunk_text: str, segments: list[dict]) -> tuple[float, float]:
    """
    Finds approximate start/end timestamps for a chunk.

    Since recursive splitting works on combined text, we map the chunk back
    to transcript segments by checking which segment text appears inside it.
    """

    matching_segments = []

    normalized_chunk = clean_transcript_text(chunk_text).lower()

    for segment in segments:
        segment_text = clean_transcript_text(segment["text"]).lower()

        if segment_text and segment_text in normalized_chunk:
            matching_segments.append(segment)

    if matching_segments:
        return matching_segments[0]["start"], matching_segments[-1]["end"]

    # Fallback if exact matching fails
    return segments[0]["start"], segments[-1]["end"]


def chunk_transcript(
    transcript: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[dict]:
    """
    Full chunking pipeline:
    raw transcript
    → preprocessing
    → combined text
    → recursive splitting
    → timestamp mapping
    """

    segments = preprocess_transcript_segments(transcript)

    if not segments:
        return []

    full_text = " ".join(segment["text"] for segment in segments)

    text_chunks = recursive_split_text(
        text=full_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = []

    for index, chunk_text in enumerate(text_chunks):
        start_time, end_time = find_chunk_timestamps(chunk_text, segments)

        chunks.append({
            "text": chunk_text,
            "start_time": start_time,
            "end_time": end_time,
            "chunk_index": index
        })

    return chunks