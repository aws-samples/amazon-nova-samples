# Amazon Nova Canvas モデルのファインチューニング

### 概要

このリポジトリでは、Amazon Bedrock を使って Amazon Nova Canvas Model をファインチューニングするためのリソースとノートブックを提供します。Amazon Nova Canvas は高品質な画像を生成でき、クリエイティブな要件に合わせて出力の見た目を柔軟に調整できます。インペインティング、アウトペインティング、画像条件付けなどの高度な画像編集タスクも実行できます。一方で、既存学習済みではない独自データセットの特性へモデルを適応させたいケースがあります。

| Ron the dog| Smila the cat|
|---------|---------|
| <img src="data/ron_01.jpg" alt="Image 1" width="300"/> | <img src="data/smila_29.jpg" alt="Image 2" width="300"/> |

### ノートブック
**1. モデルをカスタマイズする**

ノートブック **1-CanvasFT-customization-job** では、Amazon Nova Canvas モデルをカスタマイズする手順を段階的に説明しています。学習データセットの準備方法と、ファインチューニングジョブの開始方法を学べます。

**2. カスタマイズ済みモデルをプロビジョニングしてテストする**

ノートブック **2-CanvasFT-provisioned-throughput-inference** では、ファインチューニング済みモデルをプロビジョニングする流れを説明しています。ベースモデルの結果とカスタマイズ済みモデルの結果も比較します。