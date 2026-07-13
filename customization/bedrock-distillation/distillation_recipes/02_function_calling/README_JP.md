# Function Calling モデル蒸留パイプライン

function calling 機能向けに、大規模言語モデルの知識をより小型で特化したモデルへ蒸留する 3 段階パイプラインの包括的な実装です。

## 概要

この実装は、高品質な function calling 機能を維持したまま、小型で効率的なモデルを作成するための体系的アプローチを提供します。パイプラインは次の 3 段階で構成されます。
1. データ準備
2. モデル蒸留
3. 評価

## ノートブック

### 1. Data Preparation (`01_prepare_data.ipynb`)

Berkeley Function Calling Leaderboard (BFCL) V3 Live データセットを使って、function calling モデル蒸留向け学習データを準備します。

- **データセット特性**: 多様なシナリオを含む 2,251 件の question-function-answer ペア:
  - 258 件の単純呼び出し
  - 1,053 件の複数パラメータ呼び出し
  - 16 件の並列 function calling
  - 24 件の並列複数パラメータ呼び出し
  - 882 件の無関連性検出ケース
  - 18 件の関連性検出ケース
- **データ処理**:
  - function calls 向けの構造化 JSON 出力形式を実装
  - 多様な関数シグネチャとパラメータ型に対応（平均 4 パラメータ、最大 28）
  - 学習 / 評価分割を作成（50% / 50%）
  - ground truth answers を含む mix-in data（学習データの 10%）を生成
  - Bedrock distillation service 向けに JSONL 形式へ整形

### 2. Model Distillation (`02_distill.ipynb`)

Amazon Bedrock の distillation APIs を使った知識移転を実装します。

- **Teacher Model**: Nova Premier (us.amazon.nova-premier-v1:0)
- **Student Model**: Nova Lite (amazon.nova-lite-v1:0:300k)
- **主な機能**:
  - 推論のための custom model deployment が必要
  - 蒸留ジョブ向け IAM ロールと S3 バケットを設定
  - prompt-only と tool configuration の両アプローチを実装
  - function calling 向けに最適化された system prompts
  - 本番運用向けの監視とリソース管理

### 3. Evaluation (`03_evaluate.ipynb`)

Berkeley Function Calling Leaderboard フレームワークを使った包括的評価:

- **評価カテゴリ**:
  - 複数のテストシナリオにわたる function calling 精度
  - 無関連性検出（関連する関数が存在しないことの識別）
  - ライブ関連性検出（関連する関数が存在することの識別）
  - 単純および複数パラメータの function calling
- **性能分析**:
  - モデル別性能比較
  - 異なるテストカテゴリごとの精度指標
  - ベースライン Nova モデルとの比較分析
  - BFCL evaluation framework を使った自動スコアリング

## 技術要件

### AWS インフラ

- 対応リージョンで Bedrock へアクセス可能な有効 AWS アカウント（us-east-1 推奨）
- 次の権限を持つ IAM ロール:
  - S3 バケット作成およびアクセス
  - Bedrock モデルカスタマイズジョブ
  - モデルデプロイと推論
  - STS assume role capabilities

### ストレージ要件

- 蒸留データおよび出力用 S3 バケット
- BFCL データセットおよび加工済み学習ファイル向けローカルストレージ

### デプロイ要件

- 蒸留済みモデル向け custom model deployment endpoint
- 依存関係を含む Python 環境:
  ```
  boto3
  pandas
  numpy
  bfcl-eval
  PyYAML
  jupyter
  ```