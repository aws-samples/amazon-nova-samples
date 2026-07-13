## モデル蒸留向けデータセット検証

Amazon Bedrock コンソールでモデル蒸留ジョブを作成する前に、まず提供されているスクリプトでデータセットを検証してください。これにより、フォーマットエラーがある場合に早く特定でき、コスト削減にもつながります。
プロンプトおよび呼び出しログで受け付けられる形式の詳細は次を参照してください: https://docs.aws.amazon.com/bedrock/latest/userguide/prequisites-model-distillation.html

### プロンプト形式

以下は、モデル蒸留向けの有効なプロンプト例 2 件です。

```
{
    "schemaVersion": "bedrock-conversation-2024",
    "system": [
        {
            "text": "A chat between a curious User and an artificial intelligence Bot. The Bot gives helpful, detailed, and polite answers to the User's questions."
        }
    ],    
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "why is the sky blue"
                }
            ]
        },
        {
            "role": "assistant"
            "content": [
               {
                   "text": "The sky is blue because molecules in the air scatter blue light from the Sun more than other colors."
               }
            ]
        }
    ]
}
```

`System` は任意です。また、`messages` 内の `assistant` コンテンツも任意です。これらを含まない有効なプロンプト例を以下に示します。

```
{
    "schemaVersion": "bedrock-conversation-2024",    
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "text": "why is the sky blue"
                }
            ]
        }
    ]
}

```

### データセット制約

- データセットサイズは 1 GB 未満である必要があります
- データセットには少なくとも 100 件の有効なプロンプトが必要です。形式に準拠しない無効なプロンプトは破棄されます

### 呼び出しログ形式

```
{
  "schemaType": "ModelInvocationLog",
  "schemaVersion": "1.0",
  "timestamp": "<timestamp>",
  "accountId": "<accountId>",
  "identity": {
    "arn": "<arn>"
  },
  "region": "<region>",
  "requestId": "<requestId>",
  "operation": "InvokeModel",
  "modelId": "<modelId>",
  "input": {
    "inputContentType": "application/json",
    "inputBodyJson": {
      "prompt": "<|begin_of_text|><|start_header_id|>user<|end_header_id|>What is the capital of Sudan?<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
      "temperature": 0.1,
      "max_gen_len": 2048,
      "top_p": 0.9
    },
    "inputTokenCount": 15
  },
  "output": {
    "outputContentType": "application/json",
    "outputBodyJson": {
      "generation": "\n\nThe capital of Sudan is Khartoum.",
      "prompt_token_count": 15,
      "generation_token_count": 12,
      "stop_reason": "stop"
    },
    "outputTokenCount": 12
  },
  "requestMetadata": {
    "<key>": "<value>",
    "<key>": "<value>"
    ...
  }
}
```

### 呼び出しログ制約

- フィルターが指定されており、呼び出しログがその条件に一致しない場合、そのレコードは破棄されます
- 指定フィルターに一致する呼び出しログが最低 100 件必要です

### 使い方

まだ導入していない場合は、[ここ](https://www.python.org/downloads/) から最新の Python をインストールしてください。

`dataset-validation` フォルダをダウンロードし、ルートディレクトリに `cd` してから、データセット検証スクリプトを実行します。

```
pip install -r requirements.txt -U
python3 dataset_validator.py -p <path>

# 詳細な検証ログの出力先ファイルを指定する場合
python3 dataset_validator.py -p <path> -o <log file>

# 指定パスが呼び出しログであることを明示する場合
python3 dataset_validator.py -p <path> -i
```

- パスの指定方法
    - file: /path/to/file.jsonl または /path/to/file.gz（呼び出しログフラグ付き）
    - folder: /path/to/folder
    - S3: s3://bucket/key

### 機能

1. 指定パス内のプロンプトが `bedrock-conversation-2024` 形式を満たしているか検証します
2. 出力ファイルが指定されている場合、各プロンプトの検証エラーをそのファイルへ記録します
3. 呼び出しログフラグがある場合、validator は呼び出しログ向けのユースケースとして検証を行います

### 制限事項

このスクリプトは現在、次の機能をサポートしていません。

- フィルター付きの呼び出しログ検証
- プロンプトに無効なタグが含まれていないことの検証