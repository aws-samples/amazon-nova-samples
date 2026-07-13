# Amazon Nova 2 Sonic Python ストリーミング実装

このディレクトリには、Amazon Nova 2 Sonic モデルと連携するリアルタイム音声ストリーミング アプリケーションを実装した Python スクリプトが含まれています。これらの実装により、コマンドライン インターフェースを通じて自然な会話を実現しつつ、Amazon の強力な Nova 2 Sonic モデルで音声処理と応答生成を行えます。

## 利用可能な実装

このリポジトリには、Nova 2 Sonic モデルの 3 つの実装が含まれています。

1. **nova_sonic_simple.py**: 双方向ストリーミング API でイベントがどのように構成されるかを示す基本実装です。このバージョンは barge-in 機能（アシスタントの発話中にユーザーが割り込むこと）をサポートせず、真の双方向通信も実装していません。

2. **nova_sonic.py**: 真の双方向通信と barge-in を備えたフル機能実装です。ユーザーがアシスタントの発話中に割り込めるため、人間同士の会話に近い自然な対話が可能です。

3. **nova_sonic_tool_use.py**: tool use の例を加えて双方向通信機能を拡張した高度な実装です。Nova 2 Sonic が外部ツールや API と連携して機能を拡張する方法を示します。

## 機能

- マイクから AWS Bedrock へのリアルタイム音声ストリーミング
- Nova 2 Sonic モデルとの双方向通信
- Nova 2 Sonic の応答音声の再生
- 文字起こしを表示するシンプルなコンソール インターフェース
- 詳細ログを出せるデバッグモード対応
- barge-in 機能（`nova_sonic.py` と `nova_sonic_tool_use.py`）
- tool use 統合例（`nova_sonic_tool_use.py`）

## 前提条件

- Python 3.12
- Bedrock にアクセスできる AWS アカウント
- 適切な認証情報で設定された AWS CLI
- 利用可能なマイクとスピーカー

## インストール

1. 仮想環境を作成して有効化します。

まず、プロジェクトのルートフォルダへ移動して仮想環境を作成します。

```bash
# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
```

2. 依存関係をすべてインストールします。

仮想環境を有効化した状態で、必要なパッケージをインストールします。

```bash
python -m pip install -r requirements.txt --force-reinstall
```

3. AWS 認証情報を設定します。

このアプリケーションは AWS 認証に環境変数を使用します。実行前に以下を設定してください。

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

## 使い方

任意のスクリプトを通常モードで実行します。

```bash
# 基本実装（barge-in なし、イベント構造の理解に最適）
python nova_sonic_simple.py

# 双方向通信と barge-in を備えたフル実装
python nova_sonic.py

# tool use の例を含む高度な実装
python nova_sonic_tool_use.py
```

あるいは、詳細ログを表示するデバッグモードで実行します。

```bash
python nova_sonic.py --debug
```

### 動作の流れ

1. スクリプトを実行すると、次の処理が行われます。
   - AWS Bedrock へ接続する
   - ストリーミング セッションを初期化する
   - マイクからの音声取得を開始する
   - 音声を Nova 2 Sonic モデルへストリーミングする
   - スピーカーから応答音声を再生する
   - コンソールに文字起こしを表示する

2. 会話中は次のように動作します。
   - あなたの発話は文字起こしされ、`User: [transcript]` として表示されます
   - Nova 2 Sonic の応答は `Assistant: [response]` として表示されます
   - 音声応答はスピーカーから再生されます

3. 会話を終了するには次の操作を行います。
   - いつでも Enter キーを押す
   - スクリプトが接続を適切にクローズして終了する

## 実装詳細

### nova_sonic_simple.py
この実装は、双方向ストリーミング API とやり取りする基本例を提供します。内容は次の通りです。
- Nova 2 Sonic で使われるイベント構造を示す
- シンプルな片方向通信フローを提供する
- barge-in（割り込み）をサポートしない
- 真の双方向通信を実装しない
- API の基礎を理解するのに役立つ

### nova_sonic.py
このフル機能実装では次を提供します。
- 真の双方向通信をサポートする
- ユーザーがアシスタントに割り込める barge-in 機能を実装する
- より自然な会話体験を提供する
- 双方向の音声ストリーミングを同時に処理する
- 改善されたエラーハンドリングとセッション管理を含む

### nova_sonic_tool_use.py
この高度な実装では、双方向機能をさらに拡張し、次を含みます。
- Nova 2 Sonic が外部ツールと連携する方法を示す tool use の例
- tool use リクエストの構造化方法と応答処理方法の実演
- Nova 2 Sonic に追加機能を与える統合パターンの紹介
- 実践的なツール統合例を含む

## カスタマイズ

スクリプト内の次のパラメータを変更できます。

- `SAMPLE_RATE`: 音声サンプルレート（既定: 入力 16000 Hz、出力 24000 Hz）
- `CHANNELS`: 音声チャンネル数（既定: 1）
- `CHUNK_SIZE`: 音声バッファサイズ（実装により異なる）

また、`initialize_stream` メソッド内の `default_system_prompt` 変数を変更することで system prompt もカスタマイズできます。

## トラブルシューティング

1. **音声入力の問題**
   - マイクが正しく接続され、既定の入力デバイスとして選択されていることを確認してください
   - 音が途切れる場合は chunk size を大きくしてみてください
   - PyAudio のインストールで問題が出る場合は次を試してください

      **macOS:**
      ```bash
      brew install portaudio
      ```

      **Ubuntu/Debian:**

      ```bash
      sudo apt-get install portaudio19-dev
      ```

      **Windows:**

      ```bash
      # pip を使って PyAudio バイナリを直接インストール
      pip install pipwin
      pipwin install pyaudio
      ```

      あるいは、Windows ユーザーは事前ビルド済みの PyAudio wheel を以下から取得できます。
      https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
      ```bash
      # Python 3.12, 64-bit Windows の例
      pip install PyAudio‑0.2.11‑cp312‑cp312‑win_amd64.whl
      ```

2. **音声出力の問題**
   - スピーカーが動作していてミュートされていないことを確認してください
   - 音声出力デバイスが正しく選択されていることを確認してください

3. **AWS 接続の問題**
   - AWS 認証情報が環境変数として正しく設定されていることを確認してください
   - AWS Bedrock サービスへアクセスできることを確認してください
   - インターネット接続を確認してください

4. **デバッグモード**
   - 詳細ログを見るには `--debug` フラグ付きで実行してください
   - 接続や音声処理の問題を特定するのに役立ちます

## データフロー

```
User Speech → PyAudio → Amazon Nova 2 Sonic Model → Audio Output
     ↑                                                      ↓
     └──────────────────────────────────────────────────────┘
                          Conversation
```

tool use 実装では、フローは次のように拡張されます。

```
User Speech → PyAudio → Amazon Nova 2 Sonic Model → Tool Execution → Audio Output
```