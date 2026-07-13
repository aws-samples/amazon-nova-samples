# Strands BidiAgent を使った Text Agent から Nova Sonic Voice Agent への移行スキル

[Agent Skill](https://agentskills.io/specification) 形式のガイドで、任意のテキストベース エージェントを [Strands BidiAgent](https://github.com/strands-agents/sdk-python) と [Amazon Nova 2 Sonic](https://aws.amazon.com/ai/generative-ai/nova/sonic/) を用いたリアルタイム音声エージェントへ移行する方法を説明します。Strands BidiAgent は双方向音声ストリーミングを提供し、既存の system prompt と `@tool` 関数をそのまま使って、WebSocket 上で動く live speech-to-speech agent として実行できます。

## このスキルで扱う内容

このスキルは 2 つのパートで構成されています。

| Part | 内容 |
|------|------|
| **Frontend** | Web Audio API でマイク入力を扱うブラウザ WebSocket クライアント（16kHz PCM）、音声再生、テキスト入力フォールバック、system prompt を含む config event |
| **Orchestrator** | FastAPI + Strands BidiAgent + BidiNovaSonicModel サーバー、音声向け prompt 最適化ルール（簡潔さ、数字の読み上げ、確認フロー、構造化出力を避ける）、`@tool` デコレータまたは MCP Gateway によるツール統合 |

追加で含まれる内容:
- システム依存関係の注意点（`aws_sdk_bedrock_runtime`、`pyaudio`、`portaudio`）
- 完全な before / after 例付きの音声向け prompt 書き換えガイド
- 3 種類の移行例（LangChain、OpenAI function-calling、独自 Bedrock Converse）

## スキル構成

```
skills/text-agent-to-strands-voice-agent/
├── SKILL.md                              # メインスキル - 2 パート構成の移行ガイド
├── README.md                             # このファイルの英語版
├── references/
│   ├── voice-prompt-guide.md             # prompt 書き換えの詳細リファレンス
│   ├── server-reference.md               # 本番向けサーバー詳細（分割、可観測性）
│   └── client-reference.md               # 音声取得 / 再生、Python CLI、イベント処理
└── examples/
    ├── langchain-migration/              # LangChain create_react_agent → BidiAgent
    │   ├── text_agent.py                 # 移行前
    │   ├── voice_agent.py                # 移行後
    │   └── README.md
    ├── openai-migration/                 # OpenAI function-calling → BidiAgent
    │   ├── text_agent.py
    │   ├── voice_agent.py
    │   └── README.md
    └── custom-migration/                 # Bedrock Converse toolSpec → BidiAgent
        ├── text_agent.py
        ├── voice_agent.py
        └── README.md
```

## 使い方

### Kiro で使う場合

このスキルは Kiro の steering file として登録できます。セットアップ手順は次の通りです。

**1. steering file を登録する（1 コマンド）:**

```bash
mkdir -p .kiro/steering && cat > .kiro/steering/text-to-voice-migration.md << 'EOF'
---
inclusion: manual
---

# Text Agent to Nova Sonic Voice Agent Migration

When the user asks to migrate a text agent to voice, convert a chatbot to a Nova Sonic voice agent, follow the skill instructions in `#[[file:skills/text-agent-to-strands-voice-agent/SKILL.md]]`.

The skill is structured in two parts:

1. **Frontend** — Browser WebSocket client with mic capture and audio playback
2. **Orchestrator** — FastAPI + Strands BidiAgent + Nova Sonic server

## Reference Files

Load these on demand when deeper detail is needed:

- Voice prompt rewriting: `#[[file:skills/text-agent-to-strands-voice-agent/references/voice-prompt-guide.md]]`
- Server implementation details: `#[[file:skills/text-agent-to-strands-voice-agent/references/server-reference.md]]`
- Client implementation details: `#[[file:skills/text-agent-to-strands-voice-agent/references/client-reference.md]]`

## Examples

Use these as reference implementations when migrating from specific frameworks:

- LangChain migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/langchain-migration/README.md]]`
- OpenAI migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/openai-migration/README.md]]`
- Custom/Bedrock migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/custom-migration/README.md]]`

## Production Reference

The working production implementation is in the same repo:

- Server: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/websocket/agent.py]]` and `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/websocket/server.py]]`
- Client: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/client/client.py]]` and `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/client/strands-client.html]]`
- MCP tools: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/mcp/banking_mcp.py]]`
EOF
```

このコマンドでディレクトリとファイルを一度に作成できます。ポイントは次の通りです。
- `inclusion: manual` は明示的に有効化する設定です。Kiro のチャットで `#` を入力し、`text-to-voice-migration` を選択して有効化します
- `#[[file:...]]` 構文は、steering を有効化した際に Kiro が参照ファイル内容を取り込むための記法です
- 常時読み込みしたい場合は `manual` を `auto` に変更してください

**2. Kiro チャットで使う:**

1. Kiro のチャット入力で `#` を打ち、`text-to-voice-migration` を選択する
2. 自分のテキストエージェントを説明し、移行を依頼する。例:
   - "I have a text agent with this system prompt and these tools. Migrate it to a Nova Sonic voice agent."
   - "Help me convert my LangChain chatbot to voice."
3. Kiro が SKILL.md を読み込み、必要に応じて参照ファイルを取り込みながら、2 パート構成で移行を進める

**3. サンプルプロンプト:**

```
#text-to-voice-migration generate a voice agent under a voice-agent folder using
this text agent: https://github.com/strands-agents/samples/blob/main/python/04-industry-use-cases/finance/personal-finance-assistant/lab3-multi-agent-orchestration.ipynb
```

この指示により、Kiro は移行スキルを有効化し、対象テキストエージェントのソースを取得して system prompt と tools を抽出し、音声向けに prompt を書き換え、`voice-agent/` 配下に voice agent 一式（server、agent、tools、client、README）を生成します。

### Claude Code で使う場合

```bash
# スキルを登録
claude skill add skills/text-agent-to-strands-voice-agent

# その後、Claude に依頼
# "Migrate my text agent to a Nova Sonic voice agent"
```

### 人間向けの開発ガイドとして使う場合

ファイルを直接読み進めてください。

1. まず `SKILL.md` を読み、移行全体の流れを把握する
2. 自分のフレームワークに最も近い `examples/` の例を選ぶ
3. `references/voice-prompt-guide.md` を使って system prompt を音声向けに書き換える
4. `references/server-reference.md` と `references/client-reference.md` で本番向け実装詳細を確認する

## 検証

このスキルは [Agent Skills specification](https://agentskills.io/specification) に従っています。

- `name`: 小文字とハイフンのみ、64 文字未満
- `description`: 1024 文字未満で、TRIGGER / SKIP キーワードを含む
- `SKILL.md`: YAML frontmatter を含み 500 行未満
- すべてのファイル参照が既存ファイルへ解決される
- 補助コンテンツが `references/` と `examples/` に仕様どおり配置されている