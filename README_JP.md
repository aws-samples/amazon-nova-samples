# Amazon Nova モデル クックブック

## はじめに

コード例を利用するには、まず [Amazon Bedrock](https://aws.amazon.com/bedrock/) へのアクセス権があることを確認してください。次にこのリポジトリをクローンし、上記のいずれかのフォルダに移動してください。詳細な手順は各フォルダの README に記載されています。

### Bedrock のための AWS IAM 権限を有効にする

現在の環境から利用している AWS アイデンティティ（SageMaker の [*Studio/notebook Execution Role*](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html)、またはセルフマネージドなノートブックやその他の用途で使用しているロールもしくは IAM ユーザー）は、Amazon Bedrock サービスを呼び出すために十分な [AWS IAM 権限](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html) を持っている必要があります。

Bedrock へのアクセス権をそのアイデンティティに付与するには、次の手順を実施してください。

- [AWS IAM コンソール](https://us-east-1.console.aws.amazon.com/iam/home?#) を開く
- [Role](https://us-east-1.console.aws.amazon.com/iamv2/home?#/roles)（SageMaker を使っている、または IAM ロールを引き受けている場合）または [User](https://us-east-1.console.aws.amazon.com/iamv2/home?#/users) を見つける
- *Add Permissions > Create Inline Policy* を選択して新しいインライン権限を追加し、*JSON* エディタを開いて以下のポリシー例を貼り付ける

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockFullAccess",
            "Effect": "Allow",
            "Action": ["bedrock:*"],
            "Resource": "*"
        }
    ]
}
```

> ⚠️ **注 1:** Amazon SageMaker では、通常ノートブック実行ロールは、AWS コンソールにログインする際のユーザーまたはロールとは *別* です。Amazon Bedrock 用に AWS コンソールを操作したい場合は、コンソールで使用するユーザーまたはロールにも権限を付与する必要があります。

> ⚠️ **注 2:** 最上位フォルダに対する変更については、GitHub のメンテナーへ連絡してください。

Bedrock におけるより詳細なアクション権限およびリソース権限については、[Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api.html) を参照してください。

## コントリビュート

コミュニティからのコントリビューションを歓迎します。ガイドラインについては [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## セキュリティ

詳細は [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) を参照してください。

## ライセンス

このライブラリは MIT-0 ライセンスのもとで提供されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 👏 コントリビューター

素晴らしいコントリビューターの皆さんに感謝します。

<a href="https://github.com/aws-samples/amazon-nova-samples/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=aws-samples/amazon-nova-samples" />
</a>