# YouTube Transcript MCP

このプロジェクトは Model Context Protocol (MCP) サーバーとして YouTube の字幕情報を提供します。動画の URL または ID を指定するだけで、利用可能な字幕言語の一覧取得や、特定言語での字幕本文取得が可能です。

## 前提

- Python 3.13 以上
- [uv](https://github.com/astral-sh/uv) がインストール済み

初回のみ依存関係を解決するために以下を実行してください。

```bash
uv sync
```

## 利用パッケージ

- [`mcp[cli]`](https://github.com/modelcontextprotocol/python-sdk)
- [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api)

## サーバーの起動

MCP サーバーは次のコマンドで起動できます。

```bash
uv run src/youtube_transcript_mcp/server.py
```

## 提供ツール

### `list_transcript_languages`

指定した動画で利用できる字幕言語の一覧を返します。

引数:

- `video` 動画 URL または動画 ID

### `get_transcript`

指定言語の字幕を取得し、開始時刻・継続時間付きで返します。翻訳可能な字幕が存在する場合は自動翻訳も試行します。

引数:

- `video`: 動画 URL または ID
- `language`: 取得したい言語コード (例: `en`, `ja`)

## 動作確認のヒント

サーバー起動後、MCP クライアント（例: [MCP Inspector](https://github.com/modelcontextprotocol/inspector)）や対応する LLM クライアントに接続して、上記ツールを呼び出してください。
