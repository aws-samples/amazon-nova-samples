## Nova Understanding モデルのファインチューニング向けデータセット検証

Amazon Bedrock コンソールまたは API でファインチューニングジョブを作成する前に、まず提供されているスクリプトでデータセットを検証してください。これにより、フォーマットエラーがある場合に早く特定でき、コスト削減にもつながります。

### 使い方

まだ導入していない場合は、[ここ](https://www.python.org/downloads/) から最新の Python をインストールしてください。

`dataset_validation` フォルダをダウンロードし、ルートディレクトリに `cd` してから、データセット検証スクリプトを実行します。

```
python3 nova_ft_dataset_validator.py -i <file path> -m <model name> -t <task type> [-p <platform>]
```

- タスクタイプの選択肢:

  - sft: Supervised Fine-Tuning（全モデルでサポート）
  - dpo: Direct Preference Optimization（Nova 1.0 のみ - lite-2.0 では未サポート）
  - rft: 参照回答付き Reinforcement Fine-Tuning（Nova 2.0 Lite のみ - lite-2.0）

- モデル名の選択肢

  - **Nova 1.0（後方互換あり）:**

    - micro / micro-1.0: Nova Micro Model
    - lite / lite-1.0: Nova Lite Model
    - pro / pro-1.0: Nova Pro Model

  - **Nova 2.0:**
    - lite-2.0: Nova Lite 2.0 Model（reasoning、tool use、documents をサポート）

- プラットフォームの選択肢（任意、既定値は bedrock）
  - bedrock: Amazon Bedrock platform
  - sagemaker: Amazon SageMaker platform

### タスクタイプ サポートマトリクス

| Task Type | Nova 1.0 Models | Nova 2.0 Lite (lite-2.0) |
|-----------|----------------|--------------------------|
| SFT       | ✅ Supported    | ✅ Supported             |
| DPO       | ✅ Supported    | ❌ Not Supported         |
| RFT       | ❌ Not Supported| ✅ Supported             |
| CPT       | ✅ Supported    | ✅ Supported             |

## CLI 引数

```
python3 nova_dataset_validator.py \
    -i / --input_file       PATH    (required) Training JSONL file
    --validation            PATH    (optional) Validation JSONL file
    -m / --model_name       NAME    (required) Model short name (see table above)
    -t / --task_type        TYPE    (optional) sft | cpt | dpo | rft (default: sft)
    -p / --platform         PLAT    (optional) bedrock | sagemaker (default: bedrock)
    --skip-bad-samples              (optional) Continue past errors to report all issues
```

## 終了コード

| Code | Meaning |
|------|---------|
| `0`  | PASS — dataset is valid for Nova fine-tuning |
| `1`  | FAIL — one or more validation errors found   |

## サンプル出力

```
Validating training file: train.jsonl

============================================================
  Dataset Validation Report: train.jsonl
============================================================
  Total samples:   1000
  Valid samples:   985
  Failed samples:  15
  Pass rate:       98.5%

  Error breakdown:
    role_ordering_error: 7
    empty_content_error: 5
    invalid_token_error: 3

  First errors (up to 20):
    Line 12: [role_ordering_error] Location ('messages', 0, ...): Invalid messages, expected user role but found assistant (type=value_error)
    Line 45: [empty_content_error] Location ('messages', 1, 'content'): Invalid content, empty text content (type=value_error)
    ...
============================================================

Result: FAIL — please fix the issues above and re-validate.
```

### Nova 2.0 の機能

**Nova 2.0 Lite (lite-2.0) がサポートするもの:**

- ✅ Reasoning content - assistant messages 内の任意の reasoning blocks
- ✅ Tool use - 入出力検証付きの完全な tool calling
- ✅ Documents - PDF ドキュメント処理
- ✅ 制限付きメディア形式:
  - 画像: PNG, JPEG, GIF（webp は未サポート）
  - 動画: MOV, MKV, MP4（webm は未サポート）

## 検証ルール要約

### 全レシピ共通
- ファイル拡張子は `.jsonl` である必要があります
- 各行は有効な JSON である必要があります
- サンプル数はモデル上限内である必要があります（Bedrock platform のみ）

### SFT / DPO
- メッセージは `user → assistant → user → assistant → ...` の順に交互である必要があります
- 最後のメッセージは assistant（SFT）または candidates を持つ必要があります（DPO）
- 少なくとも 2 メッセージ必要です（user 1 件、assistant 1 件）
- テキストコンテンツに無効トークン（`System:`、`User:`、`Bot:`、`[EOS]`、`<image>` など）を含めてはいけません
- 画像 / 動画 / ドキュメントは user messages のみ
- 1 メッセージあたり画像は最大 10 件、1 サンプルあたり動画は最大 1 件、1 user turn あたりドキュメントは最大 1 件
- video と image/document は同じ content list に共存できません
- S3 URI は `s3://` で始まる必要があります
- Micro models では image/video/document content は非対応です
- Nova 2.0 Lite は画像形式（png、jpeg、gif）と動画形式（mov、mkv、mp4）に制限があります
- `reasoningContent` は assistant messages のみ、かつ `lite-2.0` のみ
- Tool use: `toolUse` は assistant messages のみ、`toolResult` は user messages のみ、ID は一致する必要があります

### DPO 固有
- 最後のメッセージは少なくとも 2 項目の `candidates` を持つ必要があります
- Candidates は異なる `preferenceLabel` 値（`preferred` / `non-preferred`）を持つ必要があります
- Candidate content に image/video/document は含められません
- candidate 以外の messages に video は含められません
- `lite-2.0` では未サポートです

### CPT
- 各サンプルは空でない `text` 文字列フィールドを持つ必要があります

### RFT
- `lite-2.0` のみ対応
- `messages`（空でなく、少なくとも 1 つの user message）と `tools`（空でない）が必要です
- `tools` は任意ですが、指定する場合は空でないリストで、重複する tool 名があってはいけません
- Tool type は `"function"` で、妥当な name、description、parameters を持つ必要があります
- `id` と `reference_answer` は任意です
- System message がある場合、先頭である必要があります

### データセット単位（Bedrock のみ）
- Nova 2.0 Lite は validation dataset をサポートしません
- モデルごとのサンプル数範囲（既定 8–20,000、lite-2.0 SFT: 200–20,000、lite-2.0 RFT: 100–20,000）

### RFT (Reinforcement Fine-Tuning)

**RFT は、参照回答を使ってより良いモデル整合を実現する新しい学習パラダイムです。**

**注: RFT は Nova 2.0 Lite (lite-2.0) モデルでのみサポートされます。**

RFT 形式では次が必要です。

- `id`: 各サンプルの一意識別子
- `messages`: 会話メッセージのリスト（system、user、assistant）
- `reference_answer`: 期待される / 望ましい出力を含む辞書（構造は任意）
- `tools`: （任意）ツールベースタスク向け関数定義のリスト

**RFT の例:**

Basic RFT:

```json
{
  "id": "chem-01",
  "messages": [
    { "role": "system", "content": "You are a helpful chemistry assistant" },
    {
      "role": "user",
      "content": "Calculate the molecular weight of caffeine (C8H10N4O2)"
    }
  ],
  "reference_answer": {
    "molecular_weight": 194.19,
    "unit": "g/mol",
    "calculation": "8(12.01) + 10(1.008) + 4(14.01) + 2(16.00) = 194.19"
  }
}
```

RFT with Tools:

```json
{
  "id": "tool-001",
  "messages": [
    { "role": "system", "content": "You are a helpful game master assistant" },
    {
      "role": "user",
      "content": "Generate a strength stat for a warrior character. Apply a +2 racial bonus modifier."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "StatRollAPI",
        "description": "Generates character stats",
        "parameters": {
          "type": "object",
          "properties": {
            "modifier": {
              "description": "Modifier to apply",
              "type": "integer"
            }
          },
          "required": ["modifier"]
        }
      }
    }
  ],
  "reference_answer": {
    "tool_called": "StatRollAPI",
    "tool_parameters": { "modifier": 2 },
    "expected_behavior": "Call StatRollAPI with modifier=2"
  }
}
```

### テスト例

以下のテストファイルは、さまざまな機能を示すために用意されています。

**SFT/DPO (Nova 1.0 & 2.0):**

- `test_simple.jsonl` - 基本的なテキスト会話（8 例、全モデルで動作）
- `test_reasoning.jsonl` - reasoning content を含むテキスト会話（8 例、Nova 2.0 のみ）
- `test_image_video_reasoning.jsonl` - 画像 / 動画と reasoning を含むマルチモーダル例（8 例、Nova 2.0 のみ）
- `test_tool_use.jsonl` - reasoning を含む tool calling 例（8 例、Nova 2.0 のみ）
- `test_documents.jsonl` - reasoning を含む PDF ドキュメント処理（6 例、Nova 2.0 のみ）

**RFT (Nova 2.0 Lite only):**

- `test_rft_valid.jsonl` - 参照回答を含む有効な RFT 例（6 例）
- `test_rft_tools.jsonl` - tool 定義を含む RFT 例（6 例）
- `test_rft_invalid.jsonl` - エラー検出テスト用の無効な RFT 例（8 例）

**テストコマンド:**

```bash
# 基本 SFT のテスト（全モデルで動作）
python3 nova_ft_dataset_validator.py -i test_simple.jsonl -m lite-2.0 -t sft

# reasoning content のテスト（SFT、Nova 2.0 のみ）
python3 nova_ft_dataset_validator.py -i test_reasoning.jsonl -m lite-2.0 -t sft

# 画像 / 動画 + reasoning のテスト（SFT、Nova 2.0 のみ）
python3 nova_ft_dataset_validator.py -i test_image_video_reasoning.jsonl -m lite-2.0 -t sft

# tool use のテスト（SFT、Nova 2.0 のみ）
python3 nova_ft_dataset_validator.py -i test_tool_use.jsonl -m lite-2.0 -t sft

# documents のテスト（SFT、Nova 2.0 のみ）
python3 nova_ft_dataset_validator.py -i test_documents.jsonl -m lite-2.0 -t sft

# 有効な RFT サンプルのテスト（RFT は lite-2.0 のみ対応）
python3 nova_ft_dataset_validator.py -i test_rft_valid.jsonl -m lite-2.0 -t rft

# tools 付き RFT のテスト（RFT は lite-2.0 のみ対応）
python3 nova_ft_dataset_validator.py -i test_rft_tools.jsonl -m lite-2.0 -t rft

# 無効な RFT サンプルのテスト（検証エラーが表示される想定）
python3 nova_ft_dataset_validator.py -i test_rft_invalid.jsonl -m lite-2.0 -t rft

# DPO のテスト（Nova 1.0 のみ - lite-2.0 では失敗）
python3 nova_ft_dataset_validator.py -i test_dpo.jsonl -m lite -t dpo

# 後方互換テスト（Nova 1.0）
python3 nova_ft_dataset_validator.py -i test_simple.jsonl -m lite -t sft
```

### 制限事項

このスクリプトは、Nova モデルカスタマイズ固有のロジックであるため、次の検証は実行できません。

- 画像サイズの検証
- 動画長さの検証
- サービスが S3 パスへアクセス可能かどうかの確認

ただし、これらの詳細は Nova モデルカスタマイズのドキュメントに記載されています: https://docs.aws.amazon.com/nova/latest/userguide/customize-fine-tune-prepare.html