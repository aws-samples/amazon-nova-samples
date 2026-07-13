# Getting Started Module

Amazon Nova モデルをこれから試し始める場合、最初の数回の API 呼び出しを行う最もよい方法は [Getting Started Module](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/getting-started) を確認することです。

# Self Paced Workshop

数回 API を呼び出したら、次のステップは Amazon Nova モデルの機能に慣れるためのセルフペース ワークショップを完了することです。このワークショップは [self paced workshop here](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/workshop) から参照できます。

# Repeatable Patterns Module

Amazon Nova モデルの使い方を学び、ワークショップを終えたら、毎回ゼロから作るのではなく、作業を加速できる再利用可能なコードブロックを活用するのが有益です。[repeatable patterns available here](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns) を確認することを推奨します。現在利用できる各種パターンもあわせて確認してください。

## :bulb: 各種再利用パターンの内訳

## Core Text Understanding Repeatable Patterns

| UseCase | UseCase Description | Repeatable Pattern Github Link |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Textual Key Information Extraction (Text-to-SQL) | Amazon Nova モデルを使ってテキストから重要情報を抽出し、SQL データベースへ問い合わせるためのガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/02-key-info-extraction-to-sql) |
| Batch Inference with Text | Amazon Nova モデルで Batch Inference を使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/14-batch-inference/text) |
| Long Context Intelligent Document Understanding with Premier | Premier の長いコンテキスト（1m）を活用して長文ドキュメントを理解する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/14-document-longcontext-idp) |
| Deeper Chain of Thought with Premier | Premier でより深い chain of thought を活用する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/blob/main/multimodal-understanding/repeatable-patterns/17-chain-of-thought/text/chain-of-thought.ipynb) |
| Citations with Amazon Nova | Amazon Nova で引用機能を活用する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/26-nova-citations) |
| Lite as SubAgent to Pro | Teacher モデルをエージェントとして使い、小さな Lite モデルをサブエージェントとして使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/08-lite-as-subagent-to-pro) |
| Feedback based Prompt Optimization | Teacher モデルで小型モデルからのフィードバックをレビューし、プロンプトを改善する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/18-feedback-based-prompt-optimization) |

## Multimodal Understanding Repeatable Patterns

| UseCase | UseCase Description | Repeatable Pattern Github Link |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Vision Understanding(Image and Video) | Amazon Nova モデルの視覚理解機能を使ってチャートやプロセスを理解する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/01-charts-and-process-understanding) |
| MultiModal RAG with Langchain | Amazon Nova の視覚理解モデルで Multimodal RAG を LangChain と組み合わせて構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/10-multimodal-rag-with-langchain) |
| Image Grounding with Bounding Box Detection | Amazon Nova のマルチモーダル理解モデルを使って画像を理解し、バウンディングボックス座標を検出する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/13-image-grounding) |
| Multimodal Agentic Workflow | Amazon のマルチモーダル理解モデルを使ってマルチモーダルなエージェント ワークフローを構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/16-multimodal-agentic-workflow) |
| Batch Inference with Multimodal Inputs | 画像や動画などのマルチモーダル コンテンツで Bedrock Batch Inference を使う方法のガイド | Image: [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/14-batch-inference/image); Video: [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/14-batch-inference/video) |
| Intelligent Multimodal Document Understanding with PDF Support | PDF 対応の Intelligent Document Processing に Amazon Nova のマルチモーダル理解モデルを使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/14-document-understanding-idp) |
| Video Temporal Understanding with Amazon Nova Premier | Amazon Nova Premier の時間的理解を活用する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/25-temporal-reasoning-premier) |
| Helpful Library for Multimodal | Amazon Nova モデルのマルチモーダル理解機能を使う際に役立つ各種ユーティリティのガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/sample-apps/01-multimodal-with-helper-libraries) |
| Notebook LM with Amazon Nova models | Amazon Nova と Polly を使った Notebook LLM アプリの例 | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/sample-apps/02-bedrock-notebook-lm) |

### Bedrock Fine Tuning and Distillation Repeatable Patterns

| UseCase | UseCase Description | Repeatable Pattern Github Link |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Distillation: Synthetic Data Generation using a Teacher Model | Amazon Nova Pro/Premier を teacher model として使い、合成データを生成し、その後 Lite をファインチューニングする方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/03-synthetic-data-knowledge-distillation) |
| Fine Tuning: Amazon Nova model Customization using Bedrock | Tool use を使い、Bedrock Fine Tuning でモデルをファインチューニングする方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/15-finetuning-with-bedrock) |

### Agents/RAG Repeatable Patterns

| UseCase | UseCase Description | Repeatable Pattern Github Link |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Text RAG with Langchain | Amazon Nova 理解モデルを使ってテキスト RAG を LangChain で構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/04-text-rag-with-langchain) |
| Text Agents with Langchain | Amazon Nova 理解モデルを使ってテキスト エージェント システムを LangChain で構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/05-agents-with-langchain) |
| Text RAG with LLamaIndex | Amazon Nova 理解モデルを使ってテキスト RAG を LlamaIndex で構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/06-text-rag-with-llama-index) |
| Contextual Retrieval using LLamaIndex | LlamaIndex を使って contextual retrieval を構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/09-contextual-retrieval-with-llama-index) |
| Function Calling with Structured Output | Function(tool) calling を使って構造化出力を適用する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/07-function-call-with-structured-json) |
| Function Calling with ConverseAPI | Converse API で function calling を使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/10-tool-calling-with-converse) |
| Function Calling with Pydantic Schema | Pydantic Schema で function calling を使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/11-pydantic-tool-calling) |
| Smolagents and Litellm with Nova models | Nova で Smolagents と Litellm を使う方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/12-smolagents-and-litellm) |
| ReAct Agent with Langgraph using Nova Premier | Premier を使って LangGraph ベースの ReAct エージェントを構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/19-react-agent-with-langgraph-and-premier) |
| ReAct Agent with OpenAI SDK with Nova Premier | Premier を使って OpenAI SDK ベースの ReAct エージェントを構築する方法のガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/20-react-agent-with-openapi-agent-sdk-and-premier) |
| MultiAgent Orchestration using CrewAI and Noav Premier | CrewAI と Nova Premier を使ったマルチエージェント オーケストレーションのガイド | [Link](https://github.com/aws-samples/amazon-nova-samples/tree/main/multimodal-understanding/repeatable-patterns/21-multi-agent-with-crewai-and-premier) |