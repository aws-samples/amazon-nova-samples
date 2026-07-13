# Citation-Aware モデル蒸留パイプライン

引用付き質問応答向けに、大規模言語モデルの知識をより小型で特化したモデルへ蒸留する 4 段階パイプラインの包括的な実装です。

## 概要

この実装は、高品質な引用機能を維持したまま、小型で効率的なモデルを作成するための体系的アプローチを提供します。パイプラインは次の 4 段階で構成されます。
1. データ準備
2. モデル蒸留
3. バッチ推論
4. 評価

## パイプライン構成要素

### 1. Data Preparation (`01_prepare_data.ipynb`)

- 引用対応学習のために SQuAD v2.0 データセットを利用
- 一貫した回答生成のために構造化 XML 出力形式を実装
- 回答可能な質問と「impossible」な質問の両方を処理
- 効果的な蒸留のため、10% の ground truth answers を含む最適化済み学習セットを作成

### 2. Model Distillation (`02_distill.ipynb`)

- **Teacher Model**: Nova Premier (us.amazon.nova-premier-v1:0)
- **Student Model**: Nova Lite (amazon.nova-lite-v1:0:300k)
- 機能:
  - provisioned throughput deployment をサポート
  - 引用生成向けの高度な system prompts を実装
  - 最適化された知識移転プロセス

### 3. Batch Inference (`03_batch_inference.ipynb`, `batch_inference_simulator.py`)

- 効率的なバッチ処理実装:
  - 堅牢なリトライ機構
  - 分散処理アーキテクチャ
  - 包括的なエラーハンドリングと監視
  - 複数モデルバリアント比較をサポート

### 4. Evaluation (`04_evaluate.ipynb`, `eval_jsonl_parser.py`)

引用品質評価のために、次の包括的な指標を実装しています。
- Citation Coverage
- Correctness
- Completeness
- Faithfulness
- Helpfulness
- Logical Coherence

追加機能:
- 引用の XML 解析とバリデーション
- Bedrock の RAG evaluation capabilities を使った自動評価

## 技術要件

### AWS インフラ

- Bedrock アクセス可能な有効な AWS アカウント
- 次の権限を持つ IAM ロール:
  - S3 アクセス（データ保存）
  - Bedrock モデルアクセス
  - 評価ジョブ実行

### ストレージ要件

次の用途向けに S3 バケットを設定します。
- 学習データ保存
- モデル出力保存
- 評価結果保存

### デプロイ要件

- 蒸留済みモデル向け Provisioned Throughput エンドポイント
- 依存関係を含む Python 環境:
  ```
  boto3
  pandas
  numpy
  tqdm
  ```