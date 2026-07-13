# Amazon Nova 2 Sonic Speech-to-Speech モデル サンプル

> **注:** 2025 年 12 月 2 日に発表された新しいモデル ID `amazon.nova-2-sonic-v1:0` へ、まだ更新されていないリファレンスソリューションがあります。  
> その場合でも、モデル ID を最新の `amazon.nova-2-sonic-v1:0` に手動で置き換えることで引き続き利用できます。

Amazon Nova 2 Sonic モデルは、双方向音声ストリーミングによってリアルタイムで会話できる体験を提供します。Amazon Nova 2 Sonic は、話されている最中の音声をリアルタイムに処理し応答するため、自然で人間らしい対話を実現できます。

Amazon Nova 2 Sonic モデルは `InvokeModelWithBidirectionalStream` API を使用します。これにより、双方向のリアルタイム ストリーミング会話が可能になります。従来のリクエスト / レスポンス型パターンとは異なり、音声を双方向に継続的に送受信するためのオープンなチャネルを維持します。

このリポジトリでは、サンプルアプリケーションをサブフォルダごとに整理しています。
- `sample-codes` フォルダには Java、Node.js、Python の基本サンプルがあります。好みの言語で Nova 2 Sonic とどうやり取りするかを手早く把握したい場合は、ここから始めるのが最適です。
- `repeatable-patterns` フォルダには、Amazon Bedrock Knowledge Bases や LangChain を利用した RAG、チャット履歴ロギング、カスタマーサービスや会話再開など、よくある統合パターンが含まれます。
- `workshops` フォルダには、AWS 主導およびセルフサービス形式のワークショップ向けサンプルコードが含まれます。トレーニング用途のために技術的な詳細を見せる Python WebSocket サーバーと React Web アプリケーションが用意されています。

Amazon Nova 2 Sonic の詳細は [User Guide](https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-conversational-speech.html) を参照してください。

## ブラウザ互換性に関する注意
> **Warning:** このリポジトリ内の UI 付き WebSocket ベース サンプルアプリケーションは Google Chrome 向けに最適化されており、他のブラウザでは正しく動作しない場合があります。これらのアプリケーションでは、マイク音声を WebSocket 経由で正しくストリーミングするために、音声サンプルレートを 16kHz に設定できる必要がありますが、Firefox や一部のブラウザではこれをネイティブにサポートしていません。

## 参考ソリューション
以下のプロジェクトは AWS チームによって開発され、Amazon Nova 2 Sonic と AWS サービスを使ったソリューション構築例を示しています。独自実装の参考や出発点として役立ちます。

- [Amazon Nova 2 Sonic over WebSocket with Amazon Bedrock AgentCore](https://github.com/aws-samples/sample-nova-sonic-websocket-agentcore)

    React で構築された、すぐにデプロイ可能な音声会話 AI サンプルです。Strands BidiAgent を用いて AWS Bedrock AgentCore 上の Amazon Nova 2 Sonic を利用します。Amazon Cognito によるクライアント側認証と SigV4 署名付き WebSocket URL を備え、一時クレデンシャルは Cognito Identity Pool から払い出されるためブラウザへ露出しません。ワンコマンド CDK デプロイ、リアルタイム双方向音声ストリーミング、ライブ文字起こし、barge-in 対応、tool use、AWS インフラなしで高速反復できるローカル開発モードを含みます。

- [Intelligent conversational IVR for hotel reservation system using Amazon Nova 2 Sonic](https://github.com/aws-samples/genai-quickstart-pocs/tree/main/genai-quickstart-pocs-python/amazon-bedrock-nova-sonic-poc)

    この Python アプリは、ホテル予約シナリオにおいて Amazon Nova 2 Sonic モデルのリアルタイム音声ストリーミングを紹介します。自然な会話を実現し、function calling を使って API 経由で予約の作成、変更、キャンセルを行います。

- [Nova 2 Sonic CDK Package: Call Center Agent Tools](https://github.com/aws-samples/sample-s2s-cdk-agent)

    PoC 構築の柔軟な土台として設計された、CDK デプロイ可能な Nova 2 Sonic S2S アプリケーションです。WebSocket サービスを Amazon ECS Fargate へデプロイし、フロントエンド Web アプリケーションを Amazon S3 と CloudFront 上の静的サイトとして Amazon Cognito 認証付きでホストします。

- [Nova 2 Sonic Sample Integration with Telephony Platforms: Vonage and Twilio](https://github.com/aws-samples/sample-sonic-contact-center-with-telephony)

    このソリューションは、カスタマーサポートにおける Amazon Bedrock の Nova speech-to-speech 対話を監視・最適化する包括的な分析ダッシュボードを提供します。リアルタイム感情分析、エージェントガイダンス、発話時間比率や応答時間などの主要指標を備え、Nova Lite によって動作します。バックエンドは精度向上のためにナレッジベースを統合し、アダプタ層によって Vonage や Twilio のような電話プラットフォームとも連携できます。

- [Nova 2 Sonic CDK Package: Supports Java and Python WebSocket with Load Testing Capability](https://github.com/aws-samples/generative-ai-cdk-constructs-samples/tree/main/samples/speech-to-speech)

    この CDK デプロイ可能な Nova 2 Sonic パッケージには、汎用 WebSocket サーバーと UI が含まれており、PoC の出発点であると同時に本番デプロイ向けのリファレンスアーキテクチャでもあります。Java SDK 実装と Python SDK 実装の 2 種類のサーバーを提供し、好みの言語を選択できます。さらに、同時接続数の上限を評価するための負荷試験ツールも含まれ、本番容量計画やコスト見積りに役立ちます。

- [Nova 2 Sonic VoIP Gateway](https://github.com/aws-samples/sample-s2s-voip-gateway/tree/main)

    このプロジェクトは、従来の電話システムと Nova 2 Sonic speech-to-speech の間をつなぐ SIP エンドポイントを実装します。ユーザーは電話番号へ発信し、VoIP 経由で Nova 2 Sonic と会話できます。ECS + CDK または単一 EC2 インスタンス向けのデプロイ手段があり、用途に応じて柔軟に使えます。RTP 音声ストリームを Nova 2 Sonic に橋渡しし、標準的な電話インフラ経由で音声 AI 機能を提供します。

- [Serverless Nova 2 Sonic Chat](https://github.com/aws-samples/sample-serverless-nova-sonic-chat)

    このサーバーレス実装は、AWS Lambda と AppSync Events を使って、軽量で容易にデプロイでき、スケーラブルな Nova 2 Sonic インフラを提供します。リアルタイム speech-to-speech 通信のためのシンプルな構成で、AppSync Events によるサーバー・クライアント間リアルタイム通信、過去会話履歴の参照、tool use 実装、8 分を超える会話向け自動再開機能、Next.js 製の拡張可能な Web UI を備えています。

- [Sonic Playground for Experimenting](https://github.com/aws-samples/sample-sonic-java-playground)

    このソリューションは、各種モデルパラメータを調整しながら Nova 2 Sonic の機能を試し、ユースケースに最適な設定を見つけるための実験用プレイグラウンドです。新規会話セッション作成、言語選択用 voice ID、TopP、Temperature、応答長制御用 MaxTokens、system prompt をサポートします。Java Spring Boot と React で構築されており、speech-to-speech アプリケーションのリファレンス実装として利用できます。

- [WebRTC-based Nova 2 Sonic Solution](https://github.com/aws-samples/sample-nova-sonic-speech2speech-webrtc)

    このソリューションは、WebRTC 統合によりリアルタイム Speech-to-Speech 機能を提供し、AWS Bedrock Nova 2 Sonic と Amazon Kinesis Video Streams with WebRTC を活用します。Python バックエンドと React フロントエンドを分離したモジュラー構成で、Windows、macOS、Linux を横断して利用できます。主な技術要素には RTC 音声処理、AWS サービス連携、MCP サーバーや Strands エージェント向けツール対応が含まれます。

- [Nova Sonic Live Podcasting POC](https://github.com/aws-samples/genai-quickstart-pocs/tree/main/genai-quickstart-pocs-python/amazon-bedrock-nova-s2s-live-podcasting-poc)

    この Python アプリケーションは、Amazon Nova Sonic の双方向ストリーミングを使って AI によるライブポッドキャスト会話を生成します。2 人の AI ホスト Matthew と Tiffany が AWS トピックについて複数ターンの音声対話を行い、Flask Web インターフェース上で Server-Sent Events によりリアルタイムに音声と文字起こしを配信します。トピック検証、PII 出力フィルタリング、system prompt ガードレール、テキスト・音声・混合インタラクション向けのスタンドアロン CLI モードも含まれます。