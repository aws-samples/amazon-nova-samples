# 🎨 Amazon Nova Customization Hub

**Nova Customization Hub へようこそ!** 👋

Amazon Nova モデルを本当に自分仕様にしたいなら、ここが出発点です。ここでは、Nova モデルをあなた固有のユースケースに合わせてファインチューニング、蒸留、カスタマイズするための情報をまとめています。Nova に SQL を話させたい場合も、アート作品を生み出したい場合も、特定ドメイン向けの AI アシスタントを構築したい場合も、必要な材料が揃っています。

---

## 🗺️ ナビゲーション ガイド

ここは Nova カスタマイズの地図です。それぞれのルートが、Nova モデルを目的どおりに動かすための強力な手法につながっています。

### 📋 クイック リファレンス テーブル

#### 🔷 Amazon Bedrock でのカスタマイズ

| 🎯 ユースケース | 💡 内容 | 🔗 移動先 |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **🗄️ Text-to-SQL** | 自然言語を、あなたのデータベーススキーマ向けの SQL クエリに変換 | [`bedrock-finetuning/text-to-sql/`](bedrock-finetuning/text-to-sql/) |
| **🧠 Understanding Fine-tuning** | ドキュメント処理、OCR、ツール利用向けに Nova の理解能力を調整 | [`bedrock-finetuning/understanding/`](bedrock-finetuning/understanding/) |
| **🔄 Model Distillation (S3)** | S3 ベースのプロンプトを使い、大きなモデルの知識を蒸留してより小さく高速なモデルを作成 | [`bedrock-distillation/`](bedrock-distillation/) <br> 📓 [`Distillation-via-S3-input.ipynb`](bedrock-distillation/Distillation-via-S3-input.ipynb) |
| **📝 Model Distillation (Historical)** | 過去の API 呼び出しログを使ってモデルを蒸留 | [`bedrock-distillation/`](bedrock-distillation/) <br> 📓 [`Historical_invocation_distillation.ipynb`](bedrock-distillation/Historical_invocation_distillation.ipynb) |
| **💬 Citations Distillation** | 小型モデルにも大型モデルのような引用生成を学習させる | [`bedrock-distillation/distillation_recipes/01_citations/`](bedrock-distillation/distillation_recipes/01_citations/) |
| **🛠️ Function Calling Distillation** | ツール利用や関数呼び出し能力を小型モデルへ蒸留 | [`bedrock-distillation/distillation_recipes/02_function_calling/`](bedrock-distillation/distillation_recipes/02_function_calling/) |
| **🎨 Canvas Fine-tuning** | あなたのペット、ブランド、作風など、独自スタイルの画像を Nova Canvas に学習させる | [`bedrock-finetuning/canvas/`](bedrock-finetuning/canvas/) |

#### ⚙️ HyperPod セットアップ (Nova 1.0 / 2.0) - 任意

| 🎯 ユースケース | 💡 内容 | 🔗 移動先 |
| ------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **⚙️ HyperPod Cluster Setup** | HyperPod RIG クラスターの一度きりのセットアップ（RFT や分散ワークロードのような HyperPod ベース学習時のみ必要） | [`hyperpod-rig-cluster-setup/`](hyperpod-rig-cluster-setup/) <br> 📓 [`Hyperpod Nova Cluster and Dependencies setup.ipynb`](hyperpod-rig-cluster-setup/Hyperpod%20Nova%20Cluster%20and%20Dependencies%20setup.ipynb) |

#### 🔶 SageMaker Nova 1.0 カスタマイズ

| 🎯 ユースケース | 💡 内容 | 🛠️ プラットフォーム | 🔗 移動先 |
| ------------------------------ | ------------------------------------------------------ | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **🔧 SFT/FFT/DPO Training** | 学習を細かく制御しながら Nova 1.0 をファインチューニング | Training Jobs | [`Nova_1.0/SageMakerTrainingJobs/getting_started/`](Nova_1.0/SageMakerTrainingJobs/getting_started/) |
| **🏛️ LLM-as-a-Judge** | 他モデルの評価者として Nova を利用 | Training Jobs | [`Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-LLM-As-A-Judge/`](Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-LLM-As-A-Judge/) |
| **🗄️ Text-to-SQL (SageMaker)** | SageMaker を使った Text-to-SQL ファインチューニング | Training Jobs | [`Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-Text-to-SQL-Sagemaker-Training/`](Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-Text-to-SQL-Sagemaker-Training/) |
| **⚡ Distributed Training** | HyperPod クラスターを使って分散学習をスケール | HyperPod | [`Nova_1.0/SageMakerHyperPod/getting_started/`](Nova_1.0/SageMakerHyperPod/getting_started/) |
| **🔧 CLI Utilities** | 学習ワークフロー向けのコマンドラインツール | Training Jobs & Pod | [`Nova_1.0/SageMakerTrainingJobs/cli_utility/`](Nova_1.0/SageMakerTrainingJobs/cli_utility/) |

#### 🔵 SageMaker Nova 2.0 カスタマイズ

| 🎯 ユースケース | 💡 内容 | 🔗 移動先 |
| ----------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **📊 Data Prep for Training** | Nova 2.0 のファインチューニング向けにデータセットを準備・整形 | [`Nova_2.0/01_data_prep/`](Nova_2.0/01_data_prep/) <br> 📓 [`data_prep_sft_peft_fr.ipynb`](Nova_2.0/01_data_prep/data_prep_sft_peft_fr.ipynb) |
| **🎓 Supervised Fine-Tuning (SFT)** | ラベル付き例を使い、LoRA/PEFT で Nova 2.0 を学習 | [`Nova_2.0/02_sft/`](Nova_2.0/02_sft/) <br> 📓 [`sft_peft_fr.ipynb`](Nova_2.0/02_sft/sft_peft_fr.ipynb) |
| **🎯 Reinforcement Fine-Tuning (RFT)** | HyperPod 上で単一ターンの RFT 学習を行い、モデル品質を改善（HyperPod セットアップが必要） | [`Nova_2.0/03_rft/`](Nova_2.0/03_rft/) <br> 📓 [`Hyperpod Nova RFT One-Stop Notebook (Single turn).ipynb`](Nova_2.0/03_rft/Hyperpod%20Nova%20RFT%20One-Stop%20Notebook%20(Single%20turn).ipynb) |
| **✅ Model Evaluation** | カスタム指標でファインチューニング済み Nova モデルを評価 | [`Nova_2.0/04_eval/`](Nova_2.0/04_eval/) <br> 📓 [`eval.ipynb`](Nova_2.0/04_eval/eval.ipynb) |
| **🚀 Model Deployment** | カスタム Nova モデルを本番環境へデプロイ | [`Nova_2.0/05_deployment/`](Nova_2.0/05_deployment/) <br> 📓 [`deployment_custom_model.ipynb`](Nova_2.0/05_deployment/deployment_custom_model.ipynb) |
| **🎪 End-to-End Workshop** | データ準備からデプロイまで、SFT の一連の流れを体験 | [`Nova_2.0/workshop/EndToEnd_SFT_Workshop/`](Nova_2.0/workshop/EndToEnd_SFT_Workshop/) |

#### 🛠️ ユーティリティとツール

| ツール | 内容 | リンク |
| ------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| **Dataset Validator** | 学習ジョブ送信前にトレーニングデータ形式を検証 | [Bedrock Distillation Validator](bedrock-distillation/dataset-validation/) |
| **FT-to-Eval Converter** | ファインチューニング用データセットを評価形式へ変換 | [Data Converter](SageMakerUilts/01-ft-to-eval-data-convertor/) |
| **Job Monitor** | 学習ジョブの状態をメール通知で取得 | [Job Monitoring](SageMakerUilts/SageMakerJobsMonitoring/) |

---

## 🎯 どのルートを選ぶべきか

### 🆕 **Nova カスタマイズが初めての方へ**

まずはここから始めてください。

1. 📖 [Model Distillation basics](bedrock-distillation/) を読む - 最も始めやすい手法
2. 🎨 [Canvas fine-tuning](bedrock-finetuning/canvas/) を試す - 視覚的で取り組みやすいです
3. 📊 より深いカスタマイズに進む準備ができたら [Data Prep](Nova_2.0/01_data_prep/) へ

### 🏃 **Bedrock で素早く成果を出したい方へ**

- 🔄 **Model Distillation**: ラベル付けデータなしで効率的なモデルを作成
  - [`Distillation-via-S3-input.ipynb`](bedrock-distillation/Distillation-via-S3-input.ipynb) から始めてください
- 🎨 **Canvas Fine-tuning**: 画像生成をカスタマイズ
  - [`bedrock-finetuning/canvas/`](bedrock-finetuning/canvas/) へ進んでください
- 🗄️ **Text-to-SQL**: 自然言語によるデータベース操作インターフェースを構築
  - [`bedrock-finetuning/text-to-sql/`](bedrock-finetuning/text-to-sql/) を確認してください

### 🔬 **SageMaker でより高度な制御が必要な方へ**

次の用途に適しています。

- カスタム学習レシピ
- フルパラメータのファインチューニング
- 大規模分散学習
- 高度な DPO と RLHF

**Nova 2.0 ルート**（多くのユーザー向け推奨）:

1. [`Nova_2.0/01_data_prep/`](Nova_2.0/01_data_prep/) → データ準備
2. [`Nova_2.0/02_sft/`](Nova_2.0/02_sft/) → SFT/PEFT で学習（SageMaker Training Jobs または Bedrock）
3. [`Nova_2.0/03_rft/`](Nova_2.0/03_rft/) → HyperPod 上で高度な RFT 学習（任意、[HyperPod setup](hyperpod-rig-cluster-setup/) が必要）
4. [`Nova_2.0/04_eval/`](Nova_2.0/04_eval/) → 結果を評価
5. [`Nova_2.0/05_deployment/`](Nova_2.0/05_deployment/) → 本番環境へデプロイ

**Nova 1.0 ルート**（特定パターン向け）:

- [`Nova_1.0/SageMakerTrainingJobs/`](Nova_1.0/SageMakerTrainingJobs/) - 高度な学習手法向け
- [`Nova_1.0/SageMakerHyperPod/`](Nova_1.0/SageMakerHyperPod/) - 大規模分散学習向け

---

## 🧰 カスタマイズ手法の説明

### 🔄 Model Distillation

**要点**: モデルを賢いまま、より小さく高速にする

**向いているケース:**

- 推論コストの削減（最大 10 倍安くなることもあります）
- レイテンシ改善（応答を高速化）
- リソース制約のある環境へのデプロイ

**主な利点:**

- ✨ 手作業のラベル付けが不要
- 💰 運用コストを削減
- ⚡ 推論が高速
- 🎯 タスク特化の精度を維持

**現実的なユースケース:**

- RAG アプリケーション
- ドキュメント要約
- チャットボット配備
- テキスト分類

### 🎓 Fine-Tuning (SFT/PEFT)

**要点**: Nova に、あなた独自のスタイル・形式・ドメインを教える

**向いているケース:**

- カスタム応答フォーマット
- ドメイン固有の言語
- 振る舞いの調整
- 一貫したトーンやスタイル

**主な利点:**

- 🎨 振る舞いのカスタマイズ
- 📝 形式の制御
- 🎯 タスク特化
- 💪 タスク性能の向上

**使うべきタイミング:**

- 明確な入出力例がある
- 一貫した形式やトーンが必要
- 特定の判断パターンを学習させたい
- 高品質な例が数千件ある

### 🏋️ Full Fine-Tuning (FFT)

**要点**: すべてのモデルパラメータを更新し、最大限適応させる

**向いているケース:**

- 大きなドメインシフト
- 大規模で高品質なデータセット
- 最大限の性能が必要な場合

**主な利点:**

- 🚀 可能な限り高い性能
- 🔧 完全なモデル適応
- 📊 複雑なドメイン知識にも対応

**トレードオフ:**

- 💰 計算コストが高い
- ⏱️ 学習時間が長い
- 🎯 より多くのデータが必要

### 🎯 Reinforcement Fine-Tuning (RFT)

**要点**: 正解ラベルではなく、報酬信号に基づくフィードバックでモデル性能を改善する

Reinforcement Fine-Tuning は、モデル応答を報酬関数で評価し、その報酬が最大化されるように反復的に最適化します。入力と出力の正解ペアから学ぶ従来の教師ありファインチューニングとは異なり、RFT では応答品質を示す測定可能なスコアを使って学習を誘導します。

**向いているケース:**

- 厳密な正解出力を定義しにくいが、応答品質は測定できるタスク
- クリエイティブライティング、コード最適化、複雑な推論タスク
- 微妙な意思決定や特定の品質基準への準拠が求められるアプリケーション
- 精度、効率、スタイルなど複数の目的を両立したい場合

**主な利点:**

- 📈 試行とフィードバックから複雑な振る舞いを学習
- 🎯 厳密な正解出力なしで、測定可能な成功基準を最適化
- 🔄 主観的または多面的な品質要件に対応
- ⚡ 複雑な問題解決向けの reasoning mode を活用可能

**使うべきタイミング:**

- 測定可能な成功基準は定義できるが、厳密な正解出力の提示が難しい
- 品質が主観的、または複数の妥当解がある多面的な課題である
- 反復改善、パーソナライズ、複雑な業務ルール準拠が必要
- 単一ターンの対話で出力品質を客観的に測定できる

**RFT が特に得意なこと:**

- スタイル制約付きの創造的コンテンツ生成
- 性能最適化を伴うコード生成
- 段階的な問題解決が必要な複雑推論タスク
- 有用性、安全性、エンゲージメントを両立する対話システム

**対応モデル:**

- Amazon Nova Lite 2.0 (amazon.nova-2-lite-v1:0:256k)

**要件:**

- HyperPod RIG クラスター（初回のみ [cluster setup guide](hyperpod-rig-cluster-setup/) を参照）
- 報酬信号を含む学習データ、または応答を採点できる評価器
- SageMaker Studio JupyterLab 環境

**注**: 現時点で RFT には HyperPod が必要です。他の学習方法（SFT、DPO）では、HyperPod セットアップなしで Bedrock または SageMaker Training Jobs を利用できます。

**詳細**: [AWS Documentation on RFT](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-hp-rft.html)

---

## 🎓 学習パス

### 🌟 **初級パス** (1-2 時間)

Nova のカスタマイズを始めたばかりの方向け:

1. **開始**: [Nova Lite Fine-tuning](bedrock-finetuning/understanding/)
2. **学習**: [Model Distillation Basics](bedrock-distillation/)
3. **実践**: [Text-to-SQL Tutorial](bedrock-finetuning/text-to-sql/)

### 🔥 **中級パス** (1 日)

すでに機械学習を少し触っていて、さらに踏み込みたい方向け:

1. **Data Prep**: [Nova 2.0 Data Preparation](Nova_2.0/01_data_prep/)
2. **Training**: [Supervised Fine-Tuning with PEFT](Nova_2.0/02_sft/)
3. **Advanced Training**: [Reinforcement Fine-Tuning (RFT)](Nova_2.0/03_rft/)
4. **Evaluation**: [Model Evaluation Techniques](Nova_2.0/04_eval/)
5. **Deploy**: [Production Deployment](Nova_2.0/05_deployment/)

### 🚀 **上級パス** (2-3 日)

完全なエンドツーエンド ワークショップ:

1. **SFT End to End Workshop**: [End To End SFT from Data prep to Deployment](Nova_2.0/workshop/EndToEnd_SFT_Workshop/)
2. **SFT, RFT End to End Workshop**: [End To End SFT from Data prep to Deployment](Nova_2.0/workshop/EndToEnd_SFT_RFT_Workshop/)

---

## 🛠️ ツールとユーティリティ

カスタマイズを簡単にする便利なツールも見逃さないでください。

| ツール | 内容 | リンク |
| ------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| **Dataset Validator** | 学習ジョブ送信前にトレーニングデータ形式を検証 | [Bedrock Distillation Validator](bedrock-distillation/dataset-validation/) |
| **FT-to-Eval Converter** | ファインチューニング用データセットを評価形式へ変換 | [Data Converter](SageMakerUilts/01-ft-to-eval-data-convertor/) |
| **Job Monitor** | 学習ジョブの状態をメール通知で取得 | [Job Monitoring](SageMakerUilts/SageMakerJobsMonitoring/) |
| **CLI Utilities** | よくあるワークフロー向けのコマンドラインツール | [SageMaker CLI](Nova_1.0/SageMakerTrainingJobs/cli_utility/) |

---

## 💡 実践的なヒント

### 🎯 データ品質 > データ量

- **小さく始める**: 平均的な 10,000 件より、高品質な 100 件の方が価値があります
- **一貫性を保つ**: フォーマットやスタイルは内容と同じくらい重要です
- **早めに検証する**: 学習ジョブを投げる前にバリデーターを使ってください

### 💰 コスト最適化

- **まず蒸留を試す**: ファインチューニングより安価かつ高速なことが多いです
- **PEFT を使う**: LoRA 学習はフルファインチューニングより約 10 倍安価です
- **Micro から始める**: スケール前に小さいモデルで検証してください

### ⚡ 速度最適化

- **並列実験**: 複数の小規模実験を同時に実行
- **プロビジョンドスループットを利用**: 本番ワークロード向け
- **頻出処理をキャッシュ**: 繰り返しパターンにキャッシュを活用

### 🔧 HyperPod セットアップ

- **必要なとき**: 分散学習や RFT で HyperPod を使う場合のみ必要です（Bedrock や SageMaker Training Jobs には不要）
- **一度きりのセットアップ**: 環境ごとに [cluster setup](hyperpod-rig-cluster-setup/) を一度完了してください（Nova 1.0 / 2.0 の両方で利用可能）
- **再利用可能**: 設定後は同じクラスターを複数の学習ジョブで使えます
- **前提条件**: 十分なストレージ（50GB 以上）を持つ SageMaker Studio JupyterLab を用意してください
- **主な用途**: RFT 学習および大規模分散学習ワークロード

### 🔍 デバッグのヒント

- **指標を監視**: 学習中の loss curve を確認してください
- **段階的にテスト**: 次へ進む前に各ステップを検証してください
- **ベースライン比較**: 必ずベースモデル性能と比較してください

---

## 🎪 完全なワークフロー

### End-to-End Bedrock Workflow

```
📊 Prepare Data → 🔄 Distill/Fine-tune → ✅ Evaluate → 🚀 Deploy → 📈 Monitor
```

向いているケース: 迅速な試行、マネージドインフラ

### End-to-End SageMaker Workflow

```
📊 Prep Data → 🎓 Train (SFT/DPO on Training Jobs or RFT on HyperPod) → ✅ Evaluate → 🚀 Deploy → 📈 Monitor → 🔄 Iterate
```

向いているケース: カスタム要件、最大限の制御、高度な学習手法

**注**: HyperPod セットアップが必要なのは Hyperpod Cluster 上で開発する場合のみです。

---

## 🤝 サポートが必要な場合

- 📚 **ドキュメント**: 各フォルダに詳細な README があります
- 💬 **サンプル**: すべての手法に動作するノートブックがあります
- 🐛 **Issues**: バグや質問には GitHub Issues を利用してください
- 🎓 **Workshops**: ガイド付き学習用の完全なワークショップもあります

---

## 🎉 次にやること

準備ができたら、次の流れで進めてください。

1. 上の表から **ユースケースを選ぶ**
2. 経験に合う **学習パスを選ぶ**
3. **ノートブックを順に実行する**
4. **試して改善する** - カスタマイズは反復です

どんなエキスパートも最初は初心者です。小さく始めて、速く反復し、Nova での開発を楽しんでください。🚀

---

**Happy Customizing!** 🎨✨

_補足: このページは Nova カスタマイズ全体のハブなので、すぐ戻れるようにしておくと便利です。_