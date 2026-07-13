# Amazon Nova Sonic Speech-to-Speech モデル サンプル

>**注:** Amazon Nova 2 Sonic は 2025 年 12 月 2 日に発表されました。
➡️ 既存のサンプルは引き続きモデル ID `amazon.nova-2-sonic-v1:0` で動作します
➡️ Amazon Nova 2 Sonic を使った更新版サンプルは [`amazon-nova-2-sonic`](amazon-nova-2-sonic/) ディレクトリにあります。

Amazon Nova Sonic モデルは、双方向音声ストリーミングによるリアルタイムな会話体験を提供します。Amazon Nova Sonic は、話されている最中の音声をリアルタイムで処理して応答するため、自然で人間らしい対話を実現できます。

Amazon Nova Sonic モデルは `InvokeModelWithBidirectionalStream` API を使用します。これにより、リアルタイムの双方向ストリーミング会話が可能になります。これは従来のリクエスト / レスポンス型パターンとは異なり、双方向の連続音声ストリーミングのためにオープンなチャネルを維持します。

このリポジトリでは、サンプルアプリケーションをサブフォルダごとに整理しています。
- `sample-codes` フォルダには Java、Node.js、Python の基本サンプルがあります。使い慣れた言語で Nova Sonic とやり取りする方法を素早く把握したい場合は、ここから始めてください。
- `repeatable-patterns` フォルダには、Amazon Bedrock Knowledge Bases や LangChain を使った Retrieval-Augmented Generation (RAG)、チャット履歴ロギング、カスタマーサービスや会話再開シナリオなど、一般的な統合パターンが含まれています。
- `workshops` フォルダには、AWS 主導およびセルフサービス型ワークショップ向けのサンプルコードがあります。学習用途のために技術的詳細を見せる Python WebSocket サーバーと React Web アプリケーションが含まれます。

Amazon Nova Sonic の詳細は [User Guide](https://docs.aws.amazon.com/nova/latest/userguide/speech.html) を参照してください。

## Browser Compatibility Warning
> **Warning:** このリポジトリ内の UI 付き WebSocket ベース サンプルアプリケーションは Google Chrome 向けに最適化されており、他ブラウザでは正しく動作しない場合があります。これらのアプリケーションでは、WebSocket 経由でマイク音声を適切にストリーミングするためにオーディオサンプルレートを 16kHz に設定できる必要がありますが、Firefox や一部ブラウザではこれがネイティブ対応していません。

## 参考ソリューション
以下のプロジェクトは AWS チームによって開発され、Amazon Nova Sonic と AWS サービスを使ったソリューション構築例を示しています。独自実装の参考や出発点として役立ちます。

- [Amazon Nova Sonic over WebSocket with Amazon Bedrock AgentCore](https://github.com/aws-samples/sample-nova-sonic-websocket-agentcore)

    React で構築された、すぐにデプロイ可能な音声会話 AI サンプルです。Amazon Nova Sonic を AWS Bedrock AgentCore 上で Strands BidiAgent と組み合わせて利用します。Amazon Cognito によるクライアント側認証と SigV4 署名付き WebSocket URL を備え、一時クレデンシャルは Cognito Identity Pool から払い出され、ブラウザには露出しません。ワンコマンドの CDK デプロイ、リアルタイム双方向音声ストリーミング、ライブ文字起こし、barge-in 対応、tool use、AWS インフラなしで高速反復できるローカル開発モードを備えています。

- [Intelligent conversational IVR for hotel reservation system using Amazon Nova Sonic](https://github.com/aws-samples/genai-quickstart-pocs/tree/main/genai-quickstart-pocs-python/amazon-bedrock-nova-sonic-poc)

    この Python アプリは、ホテル予約シナリオで Amazon Nova Sonic モデルによるリアルタイム音声ストリーミングを紹介します。自然な会話を実現し、function calling を使って API 経由で予約の作成、変更、キャンセルを行います。

- [Nova Sonic CDK Package: Call Center Agent Tools](https://github.com/aws-samples/sample-s2s-cdk-agent)

    PoC 構築の柔軟な土台として設計された、CDK でデプロイ可能な Nova Sonic S2S アプリケーションです。WebSocket サービスを Amazon ECS Fargate にデプロイし、フロントエンド Web アプリケーションを Amazon S3 と CloudFront 上の静的サイトとして、Amazon Cognito 認証付きでホストします。

- [Nova Sonic Sample Integration with Telephony Platforms: Vonage and Twilio](https://github.com/aws-samples/sample-sonic-contact-center-with-telephony)

    このソリューションは、カスタマーサポートにおける Amazon Bedrock の Nova 音声対話を監視・最適化するための包括的な分析ダッシュボードを提供します。リアルタイム感情分析、エージェントガイダンス、発話時間比率や応答時間などの主要指標を備え、Nova Lite によって動作します。バックエンドは、より正確な応答のためにナレッジベースを統合し、アダプタ層によって Vonage や Twilio のような電話プラットフォームとの連携も可能です。

- [Nova Sonic CDK Package: Supports Java and Python WebSocket with Load Testing Capability](https://github.com/aws-samples/generative-ai-cdk-constructs-samples/tree/main/samples/speech-to-speech)

    この CDK デプロイ可能な Nova Sonic パッケージには、汎用 WebSocket サーバーと UI が含まれ、PoC の出発点であると同時に本番デプロイのリファレンスアーキテクチャでもあります。Java SDK を使う実装と Python SDK を使う実装の 2 種類のサーバーを提供し、利用者が好みの言語を選べます。さらに、同時接続数の上限評価に使える負荷試験ツールも含まれており、本番容量計画やコスト見積りに役立ちます。

- [Nova Sonic VoIP Gateway](https://github.com/aws-samples/sample-s2s-voip-gateway/tree/main)

    このプロジェクトは、従来の電話システムと Nova Sonic speech-to-speech の間をつなぐ SIP エンドポイントを実装します。ユーザーは電話番号へ発信し、VoIP 経由で Nova Sonic と会話できます。ECS + CDK または単一 EC2 インスタンス向けのデプロイ手段があり、用途に応じて柔軟に使えます。RTP 音声ストリームを Nova Sonic に橋渡しし、標準的な電話インフラ経由で音声 AI 機能を提供します。

- [Serverless Nova Sonic Chat](https://github.com/aws-samples/sample-serverless-nova-sonic-chat)

    このサーバーレス実装は、AWS Lambda と AppSync Events を使って、軽量で容易にデプロイでき、スケーラブルな Nova Sonic インフラを提供します。リアルタイムな音声対話のためのシンプルなアプローチです。サーバーとクライアント間の AppSync Events によるリアルタイム通信、過去会話履歴の参照、tool use 実装、8 分を超える会話向け自動再開機能、Next.js で構築された拡張可能な Web UI を備えています。

- [Sonic Playground for Experimenting](https://github.com/aws-samples/sample-sonic-java-playground)

    このソリューションは、各種モデルパラメータを設定しながら Nova Sonic の機能を試し、ユースケースに最適な設定を見つけるための実験用プレイグラウンドです。新規会話セッション作成、言語選択用の voice ID、TopP、Temperature、応答長制御用 MaxTokens、system prompt をサポートします。Java Spring Boot と React で構築されており、speech-to-speech アプリケーションのリファレンス実装として使えます。

- [WebRTC-based Nova Sonic Solution](https://github.com/aws-samples/sample-nova-sonic-speech2speech-webrtc)

    このソリューションは、WebRTC 統合によりリアルタイム speech-to-speech 機能を提供し、AWS Bedrock Nova Sonic と Amazon Kinesis Video Streams with WebRTC を活用します。Python バックエンドと React フロントエンドを分離したモジュラー構成で、Windows、macOS、Linux を横断して利用できます。主な技術要素には RTC 音声処理、AWS サービス連携（Bedrock、Kinesis Video Streams）、MCP サーバーや Strands エージェント向けツール対応が含まれます。

- [Nova Sonic Live Podcasting POC](https://github.com/aws-samples/genai-quickstart-pocs/tree/main/genai-quickstart-pocs-python/amazon-bedrock-nova-s2s-live-podcasting-poc)

    この Python アプリケーションは、Amazon Nova Sonic の双方向ストリーミングを使い、AI によるライブポッドキャスト会話を生成します。2 人の AI ホストである Matthew と Tiffany が AWS トピックについて複数ターンの音声対話を行い、Flask Web インターフェース上で Server-Sent Events (SSE) を通じてリアルタイムに音声と文字起こしを配信します。このアプリケーションには、トピック検証、PII 出力フィルタリング、system prompt ガードレール、テキスト・音声・混合インタラクション向けのスタンドアロン CLI モードが含まれています。