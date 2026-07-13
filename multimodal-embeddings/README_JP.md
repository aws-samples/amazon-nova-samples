# 🚀 Amazon Nova マルチモーダル埋め込みサンプル

Amazon Nova のマルチモーダル埋め込みモデル向けの包括的なサンプルコードとチュートリアルです。テキスト、画像、動画、ドキュメントから埋め込みを生成し、実運用のアプリケーションで活用する方法を示します。

## 🌟 概要

Amazon Nova は、複数種類のコンテンツを同時に処理・理解できる最先端のマルチモーダル埋め込みを提供します。このリポジトリには、実践的な例、チュートリアル、本番利用を意識した再利用可能パターンが含まれています。

## 📚 はじめ方チュートリアル

| Tutorial | Content Type | Description |
|----------|-------------|-------------|
| 🔧 [`00_setup.ipynb`](getting-started/00_setup.ipynb) | セットアップ | 環境設定と依存関係 |
| 📝 [`01_basics_text_embeddings.ipynb`](getting-started/01_basics_text_embeddings.ipynb) | テキスト | 基本的なテキスト処理と埋め込み生成 |
| 🖼️ [`02_basics_image_embeddings.ipynb`](getting-started/02_basics_image_embeddings.ipynb) | 画像 | 画像特徴抽出と類似度マッチング |
| 🎬 [`03_basics_video_embeddings.ipynb`](getting-started/03_basics_video_embeddings.ipynb) | 動画 | 動画コンテンツ解析と時間的埋め込み |
| 🎵 [`04_basics_audio_embeddings.ipynb`](getting-started/04_basics_audio_embeddings.ipynb) | 音声 | 音声コンテンツ処理と特徴抽出 |
| 📄 [`05_example_document_embedding_retrieval.ipynb`](getting-started/05_example_document_embedding_retrieval.ipynb) | ドキュメント | 複数ページ文書の処理とチャンク分割 |
| 🔍 [`06_example_text_query_embeddings.ipynb`](getting-started/06_example_text_query_embeddings.ipynb) | クエリ | 検索向けに最適化された埋め込みの作成 |
| ⚡ [`07_batch_inference_sample.ipynb`](getting-started/07_batch_inference_sample.ipynb) | バッチ | 複数埋め込みのバッチ処理 |

## 🏗️ 再利用可能パターン

| Pattern | Technologies | Use Case | Description |
|---------|-------------|----------|-------------|
| 🎬 [**Video Embedding S3 Vector**](repeatable-patterns/video-embedding-s3-vector/) | Amazon Bedrock, S3 Vectors, Nova Embeddings | 動画検索 | S3 Vectors をベクターデータベースとして使い、動画埋め込みを保存・検索 |
| 🌍 [**Multilingual Text Clustering**](repeatable-patterns/multilingual-text-clustering/) | Nova Embeddings, Clustering, Visualization | ニュース分析 | 複数言語（ドイツ語、スペイン語、英語）のニュース記事をクラスタリング |
| 📚 [**Multimodal Doc Search Framework**](repeatable-patterns/multimodal-doc-search-opensource-framework/) | LangChain, LlamaIndex, FAISS | RAG システム | オープンソースフレームワークと連携した文書処理 |
| 🛍️ [**Visual Product Search**](repeatable-patterns/visual-product-search-with-image-text-embeddings/) | OpenSearch Serverless, Berkeley Objects | EC サイト | テキスト説明と画像の両方で商品検索 |
| 🔍 [**Multilingual Search**](repeatable-patterns/multilingual-search/) | Nova Embeddings, S3 Vectors | 検索システム | ベクトル類似度を使い、複数言語を横断して動作するセマンティック検索を構築 |
| 🎯 [**Multilingual Intent Classification**](repeatable-patterns/multilingual-intent-classification/) | Nova Embeddings, S3 Vectors| カスタマーサービス | セマンティック埋め込みを使い、複数言語でユーザー意図を分類 |

## 🛠️ 技術スタック

| Category | Technologies |
|----------|-------------|
| **AI/ML** | Amazon Bedrock, Nova Multimodal Embeddings |
| **Vector Databases** | Amazon S3 Vectors, OpenSearch Serverless, FAISS |
| **Frameworks** | LangChain, LlamaIndex |
| **Languages** | Python, Jupyter Notebooks |
| **AWS Services** | Bedrock, S3, OpenSearch |

## 🎯 エンドツーエンド デモ

Amazon Nova のマルチモーダル埋め込みを実際に動かす完全なデモとして、次も参照してください。

🔗 [**Sample Demo of Nova MME**](https://github.com/aws-samples/sample-demo-of-nova-mme) - マルチモーダルな agentic RAG を示す完全なエンドツーエンド実装

## 🚀 クイックスタート

1. 環境設定のために `getting-started/00_setup.ipynb` から始める
2. 基本を学ぶために `getting-started/` の番号付きチュートリアルを順に進める
3. 実運用ユースケースとして `repeatable-patterns/` を確認する
4. パターンを自分のアプリケーション向けテンプレートとして活用する