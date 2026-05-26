from .preprocessing import preprocess_transcript_segments

def chunk_transcript(
    transcript: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[dict]:
    """
    Chunks a video transcript into overlapping segments.
    
    Instead of concatenating all text and splitting blindly (which breaks 
    timestamp mapping), this groups the native transcript segments directly.
    This guarantees 100% accurate start/end timestamps for each chunk.
    """

    segments = preprocess_transcript_segments(transcript)

    if not segments:
        return []

    chunks = []
    current_chunk_segments = []
    current_length = 0
    
    i = 0
    while i < len(segments):
        segment = segments[i]
        seg_text = segment["text"]
        seg_len = len(seg_text)
        
        # Check if adding this segment would exceed the chunk size
        # (and ensure we have at least one segment in the current chunk)
        if current_length + seg_len + (1 if current_length > 0 else 0) > chunk_size and current_chunk_segments:
            # Finalize current chunk
            chunk_text = " ".join(s["text"] for s in current_chunk_segments)
            chunks.append({
                "text": chunk_text,
                "start_time": current_chunk_segments[0]["start"],
                "end_time": current_chunk_segments[-1]["end"],
                "chunk_index": len(chunks)
            })
            
            # Start new chunk with overlap
            overlap_length = 0
            overlap_segments = []
            
            # Iterate backwards to gather overlap segments
            # We skip the first segment (current_chunk_segments[1:]) to guarantee 
            # the chunk shrinks and we avoid infinite loops.
            for s in reversed(current_chunk_segments[1:]):
                s_len = len(s["text"])
                if overlap_length + s_len <= chunk_overlap:
                    overlap_segments.insert(0, s)
                    overlap_length += s_len + 1 # +1 for space
                else:
                    # If we haven't gathered anything and this single segment is larger than overlap,
                    # we still take it to ensure some overlap
                    if not overlap_segments:
                        overlap_segments.insert(0, s)
                    break
            
            current_chunk_segments = overlap_segments
            current_length = sum(len(s["text"]) for s in current_chunk_segments) + max(0, len(current_chunk_segments) - 1)
            
            # Do NOT increment i, so the current segment that caused the overflow is processed again
        else:
            current_chunk_segments.append(segment)
            current_length += seg_len + (1 if current_length > 0 else 0)
            i += 1

    # Add the last chunk
    if current_chunk_segments:
        chunk_text = " ".join(s["text"] for s in current_chunk_segments)
        chunks.append({
            "text": chunk_text,
            "start_time": current_chunk_segments[0]["start"],
            "end_time": current_chunk_segments[-1]["end"],
            "chunk_index": len(chunks)
        })

    return chunks