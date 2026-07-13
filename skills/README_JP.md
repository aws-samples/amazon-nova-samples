# Amazon Nova Skills

Amazon Nova モデル向けの再利用可能な [Agent Skills](https://agentskills.io/specification) です。各スキルは、AI コーディングアシスタント（Kiro、Claude Code など）が従って開発を支援できるよう、段階的なガイダンスを提供します。

## 利用可能なスキル

| Skill | Description |
|-------|-------------|
| [text-agent-to-strands-voice-agent](./text-agent-to-strands-voice-agent/) | Strands BidiAgent と Amazon Nova Sonic を使い、テキストベースのエージェントをリアルタイム音声エージェントへ移行 |
| [nova-prompter](./nova-prompter/) | Amazon Nova 1 と Nova 2 Lite 向けにプロンプトを作成・最適化。Claude Code プラグイン（`/nova1-prompt`, `/nova2-prompt`）と対応する Kiro powers を提供し、Nova 2 のマルチモーダル対応も含む |
| [titan-nova-mme-migration](./titan-nova-mme-migration/) | Amazon Bedrock の埋め込みコードを Titan Text V2 / Titan Multimodal G1 から Amazon Nova Multimodal Embeddings へ移行。リクエストスキーマ、次元マッピング、`embeddingPurpose`、クライアント側のテキスト+画像融合を扱う |
| [gemini-to-nova-migration](./gemini-to-nova-migration/) | Google Gemini 2.0/2.5/3.x の Python コードとプロンプトを Amazon Nova 2 Lite へ移行。SDK 呼び出し（`google-genai` / `google-generativeai` → `boto3` Bedrock `converse`）の変換、`##Section##` 形式へのプロンプト書き換え、マルチモーダル、tool calling、structured output、streaming、reasoning mode に対応 |