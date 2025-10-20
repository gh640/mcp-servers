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
        "YouTube 動画の文字起こしと言語リストを返すツールです。"
        "動画 URL または動画 ID を指定し、必要なら言語コードも渡してください。"
    ),
)
_transcript_api = YouTubeTranscriptApi()


def main():
    mcp.run(transport="stdio")


class TranscriptSegment(BaseModel):
    start: float = Field(description="セグメント開始時刻（秒）")
    duration: float = Field(description="セグメント継続時間（秒）")
    text: str = Field(description="字幕テキスト")


class TranscriptResult(BaseModel):
    video_id: str = Field(description="解析した動画ID")
    language: str = Field(description="取得した言語コード")
    segments: list[TranscriptSegment] = Field(description="字幕セグメント一覧")


class TranscriptLanguage(BaseModel):
    language_code: str = Field(description="言語コード（例: en, ja）")
    language: str = Field(description="表示名")
    is_generated: bool = Field(description="自動生成字幕かどうか")
    is_translatable: bool = Field(description="他言語への翻訳が可能か")


class AvailableLanguagesResult(BaseModel):
    video_id: str = Field(description="解析した動画ID")
    languages: list[TranscriptLanguage] = Field(
        description="利用可能な字幕言語一覧（言語コード昇順）"
    )


TranscriptResult.model_rebuild()
AvailableLanguagesResult.model_rebuild()


class TranscriptFetchError(Exception):
    """カスタム例外"""


def _extract_video_id(video_reference: str) -> str:
    video_reference = video_reference.strip()

    if not video_reference:
        raise TranscriptFetchError("動画を識別する文字列が空です")

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
        "YouTube の動画の URL または ID を認識できませんでした。"
        " https://youtu.be/<id> や https://www.youtube.com/watch?v=<id> の形式を指定してください。"
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
                f"言語コード {language} の字幕が見つかりませんでした"
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
    """指定された YouTube 動画に利用可能な字幕言語を一覧取得する"""
    video_id = _extract_video_id(video)
    languages = [*_yield_languages(video_id)]

    return AvailableLanguagesResult(video_id=video_id, languages=languages)


@mcp.tool()
def get_transcript(video: str, language: str) -> TranscriptResult:
    """指定された YouTube 動画の字幕を取得する"""
    if not language.strip():
        raise ValueError("language には言語コードを指定してください（例: en, ja ）")

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
