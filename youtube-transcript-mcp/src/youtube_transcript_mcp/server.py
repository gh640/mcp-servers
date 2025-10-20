import re
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)


mcp = FastMCP(
    "YouTube Transcript MCP",
    instructions=(
        "This tool returns YouTube video transcripts and available language lists."
        " Provide a video URL or video ID, and include a language code if necessary."
    ),
)
_transcript_api = YouTubeTranscriptApi()


def main():
    mcp.run(transport="stdio")


class TranscriptSegment(BaseModel):
    start: float = Field(description="Segment start time in seconds")
    duration: float = Field(description="Segment duration in seconds")
    text: str = Field(description="Caption text")


class TranscriptResult(BaseModel):
    video_id: str = Field(description="Analyzed video ID")
    language: str = Field(description="Retrieved language code")
    segments: list[TranscriptSegment] = Field(description="List of caption segments")


class TranscriptLanguage(BaseModel):
    language_code: str = Field(description="Language code (e.g., en, ja)")
    language: str = Field(description="Display name")
    is_generated: bool = Field(description="Whether the captions are auto-generated")
    is_translatable: bool = Field(
        description="Whether translation into other languages is available"
    )


class AvailableLanguagesResult(BaseModel):
    video_id: str = Field(description="Analyzed video ID")
    languages: list[TranscriptLanguage] = Field(
        description="List of available caption languages"
    )


TranscriptResult.model_rebuild()
AvailableLanguagesResult.model_rebuild()


class TranscriptFetchError(Exception):
    """Custom exception"""


def _extract_video_id(video_reference: str) -> str:
    video_reference = video_reference.strip()

    if not video_reference:
        raise TranscriptFetchError("The video identifier string is empty")

    if _looks_like_video_id(video_reference):
        return video_reference

    parsed = urlparse(video_reference)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            video_ids = query.get("v")
            if video_ids:
                candidate = video_ids[0]
                if _looks_like_video_id(candidate):
                    return candidate
        if parsed.path.startswith("/live/") or parsed.path.startswith("/shorts/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and _looks_like_video_id(parts[1]):
                return parts[1]
    if "youtu.be" in host:
        candidate = parsed.path.lstrip("/")
        if _looks_like_video_id(candidate):
            return candidate

    raise TranscriptFetchError(
        "Could not recognize the URL or ID for a YouTube video."
        " Please provide it in the form https://youtu.be/<id> or https://www.youtube.com/watch?v=<id>."
    )


def _looks_like_video_id(candidate: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate))


def _fetch_transcript(video_id: str, language: str) -> list[dict]:
    try:
        fetched = _transcript_api.fetch(video_id, languages=[language])
        return fetched.to_raw_data()
    except NoTranscriptFound:
        transcripts = _transcript_api.list(video_id)
        try:
            transcript = transcripts.find_transcript([language])
            return transcript.fetch().to_raw_data()
        except NoTranscriptFound as original_error:
            for t in transcripts:
                if t.is_translatable:
                    try:
                        translated = t.translate(language)
                        return translated.fetch().to_raw_data()
                    except NoTranscriptFound:
                        continue
            raise TranscriptFetchError(
                f"Captions with language code {language} were not found"
            ) from original_error
    except (VideoUnavailable, TranscriptsDisabled, CouldNotRetrieveTranscript) as error:
        raise TranscriptFetchError(str(error)) from error


def _yield_languages(video_id: str) -> Iterator[TranscriptLanguage]:
    try:
        transcripts = _transcript_api.list(video_id)
    except (VideoUnavailable, TranscriptsDisabled, CouldNotRetrieveTranscript) as error:
        raise TranscriptFetchError(str(error)) from error

    seen_codes: set[str] = set()

    for t in sorted(transcripts, key=lambda x: x.language_code):
        code = t.language_code
        if code in seen_codes:
            continue
        seen_codes.add(code)
        yield TranscriptLanguage(
            language_code=code,
            language=t.language,
            is_generated=t.is_generated,
            is_translatable=t.is_translatable,
        )


@mcp.tool()
def list_transcript_languages(video: str) -> AvailableLanguagesResult:
    """Retrieve the list of available caption languages for the specified YouTube video"""
    video_id = _extract_video_id(video)
    languages = [*_yield_languages(video_id)]

    return AvailableLanguagesResult(video_id=video_id, languages=languages)


@mcp.tool()
def get_transcript(video: str, language: str) -> TranscriptResult:
    """Retrieve captions for the specified YouTube video"""
    if not language.strip():
        raise ValueError(
            "Provide a language code for the language parameter (e.g., en, ja)"
        )

    video_id = _extract_video_id(video)
    raw_segments = _fetch_transcript(video_id, language.strip())

    segments = [
        TranscriptSegment(
            start=s["start"],
            duration=s["duration"],
            text=s["text"],
        )
        for s in raw_segments
    ]

    return TranscriptResult(
        video_id=video_id,
        language=language.strip(),
        segments=segments,
    )


if __name__ == "__main__":
    main()
