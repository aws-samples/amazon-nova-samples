# Amazon Bedrock モデル蒸留サンプル

このリポジトリには、Amazon Bedrock Model Distillation の使い方を示すコードサンプルとノートブックが含まれています。サンプルでは、蒸留ジョブを作成するための 2 つの主要な方法を扱っています。1 つは S3 を使ってプロンプトを含む JSONL ファイルをアップロードする方法、もう 1 つは過去の呼び出しログを利用する方法です。

## 目次

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Notebooks](#notebooks)
4. [Usage](#usage)
5. [Key Benefits](#key-benefits)
6. [Use Cases](#use-cases)
7. [Contributing](#contributing)

## Introduction

Amazon Bedrock Model Distillation を使うと、より大規模で高性能なモデルに近いユースケース特化精度を保ちながら、より小さく、高速で、コスト効率の高いモデルを作成できます。このリポジトリでは、Amazon Bedrock を使ってモデル蒸留を実装するための実践例を提供します。

## Prerequisites

これらのサンプルを利用する前に、次を満たしていることを確認してください。

- 有効な AWS アカウント
- Amazon Bedrock で teacher model と student model が有効化されていること
- モデルの利用可能リージョンとクォータを確認済みであること
- 必要な権限を持つ IAM ロールを作成済みであること
- 蒸留ジョブの出力メトリクス保存用の Amazon S3 バケットを設定済みであること
- 呼び出しログを使う場合は invocation logging を有効化していること
- 推論時に provisioned throughput を実行するための十分なクォータがあること

## Notebooks

このリポジトリには、主に次の 2 つのノートブックがあります。

1. `Distillation-via-S3-input.ipynb`: プロンプトを含む JSONL ファイルを S3 にアップロードし、モデル蒸留に利用する方法を示します。
2. `Historical_invocation_distillation.ipynb`: 過去の呼び出しログを使って蒸留ジョブを作成する方法を示します。ConverseAPI を使った invocation logs と metadata の生成も含みます。

## Usage

これらのノートブックを利用するには、次の手順に従ってください。

1. このリポジトリをクローンする
2. Jupyter 環境で目的のノートブックを開く
3. 各ノートブック内の手順を順番に実行する

必要な AWS 権限があり、前提条件に従って環境設定が完了していることを確認してください。

## Key Benefits

- Efficiency: 蒸留済みモデルは、最も高性能なモデルに匹敵するユースケース特化精度を持ちながら、最小クラスのモデルに近い速度を実現できます。
- Cost Optimization: 蒸留済みモデルの推論コストは、大規模な高性能モデルと比べて低くなります。
- Advanced Customization: Bedrock Model Distillation により、ファインチューニング用のラベル付きデータセット作成が不要になります。
- Ease of Use: Bedrock Model Distillation は、teacher の応答生成、データ合成の追加、最適化されたハイパーパラメータチューニングによる student モデルのファインチューニングを自動化する単一ワークフローを提供します。

## Use Cases

- Retrieval-Augmented Generation (RAG)
- ドキュメント要約
- チャットボット配備
- テキスト分類

## Contributing

これらのサンプル改善へのコントリビューションを歓迎します。変更案がある場合は、Pull Request を送るか、Issue を作成して議論してください。