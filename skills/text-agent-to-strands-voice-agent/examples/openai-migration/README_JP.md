# OpenAI Function-Calling から Voice への移行例

OpenAI の `chat.completions` ベース text agent を、function calling 付きのまま Strands BidiAgent ベースの voice agent へ移行する例です。

## ファイル構成

| File | 役割 |
|------|------|
| `text_agent.py` | **移行前** - `tools=[{"type":"function",...}]` を使う OpenAI text agent |
| `voice_agent.py` | **移行後** - 音声向けに最適化された prompt を持つ voice session handler |
| `voice_tools_mcp.py` | **移行後** - OpenAI の function schema を MCP Tool 定義へ変換したもの |

## 何が変わるか

1. **System prompt**: markdown や code block 前提の指示を削除し、話し言葉のフローと再起動前の確認を追加
2. **Tools**: OpenAI の `parameters` schema は MCP の `inputSchema` にほぼそのまま対応するため、ラッパーだけ変えればよい
3. **Agent**: `client.chat.completions.create()` のループを `BidiAgent.run()` に置き換え、双方向ストリーミングへ変更
4. **Transport**: HTTP の request / response から、WebSocket による双方向音声通信へ移行