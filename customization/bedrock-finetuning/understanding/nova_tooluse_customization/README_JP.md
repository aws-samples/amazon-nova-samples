# Amazon Bedrock を使った Amazon Nova Tool Use のファインチューニング

## 説明
このリポジトリでは、Amazon Bedrock を使って Amazon Nova モデルの tool usage 向けファインチューニングを行う方法を示します。

## 内容

Amazon Bedrock API を使った tool calling を、ファインチューニングあり / なしの両方でたどれる 4 つのノートブックがあります。

- [01_toolcall_nova_bedrock_invokeAPI_and_converseAPI.ipynb](./tooluse_finetuner_main/notebooks/01\_toolcall_nova_bedrock_invokeAPI_and_converseAPI.ipynb) - このノートブックでは、事前定義されたツール群に対して Amazon Bedrock の invoke API と converse API を使った tool use を扱います。tool config、prompt、messages API を Bedrock converse API および Bedrock invoke API にどう合わせるべきかを示します。異なる入力質問を使って挙動を確認できます。

- [02_prepare_toolcall_dataset_for_bedrock_nova_ft.ipynb](./tooluse_finetuner_main/notebooks/02\_prepare_toolcall_dataset_for_bedrock_nova_ft.ipynb) - このノートブックでは、データセットを Amazon Bedrock invoke API または Amazon Bedrock コンソール経由で Amazon Nova をファインチューニングするために必要な形式へ変換します。

- [03_toolcall_fullfinetune_nova_bedrock.ipynb](./tooluse_finetuner_main/notebooks/03\_toolcall_fullfinetune_nova_bedrock.ipynb) - このノートブックでは、整形済みの train / test tooluse データセットを格納した S3 バケットと IAM ロールを設定します。その後、Bedrock API を使って Amazon Nova の新しいファインチューニングジョブを作成・開始します。なお、ファインチューニングは Amazon Bedrock コンソールから直接実行することも可能です。

- [04_toolcall_test_inference_finetuned_nova_bedrock.ipynb](./tooluse_finetuner_main/notebooks/04\_toolcall_test_inference_finetuned_nova_bedrock.ipynb) - このノートブックでは、Provisioned Throughput を使ってファインチューニング済みモデルをデプロイし、推論を実行する方法を示します。あわせて、tool usage と args calling の両方について validation set 上で精度指標も計算します。

このデータセットで利用するツールに対応する Python ファイルが 8 個含まれています。
tooluse 用データセットは [./tooluse_finetuner_main/assets/](./tooluse_finetuner_main/assets/) にあります。

## Contributing

コミュニティからのコントリビューションを歓迎します。サンプルは AWS の [best practices](https://aws.amazon.com/architecture/well-architected/) に沿うようにしてください。また、この README の **Contents** セクションへ、サンプルへのリンクと説明を追加してください。