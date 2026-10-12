# AIM313 - Improving multimedia analytics with customized Amazon Nova models

This workshop walks you end-to-end through fine-tuning **Amazon Nova-Lite** for a
document visual question-answering (Document VQA) task using **Amazon SageMaker
Training Jobs**, importing the fine-tuned model into **Amazon Bedrock**, and
evaluating it against the pre-trained baseline.

It was delivered as the AWS re:Invent 2025 builder session
*"AIM313 - Improving multimedia analytics with customized Amazon Nova models."*

You can run this workshop in a guided **AWS Workshop Studio** environment:
[AIM313 Workshop Studio catalog](https://catalog.us-east-1.prod.workshops.aws/workshops/4765b5c2-88c6-41aa-9fae-0adb0c8fd1d9/en-US).

## What you'll build

Starting from raw [DocumentVQA](https://huggingface.co/datasets/HuggingFaceM4/DocumentVQA)
data, you convert it to the Bedrock conversation format, fine-tune Nova-Lite on
SageMaker, deploy the custom model to Bedrock for on-demand inference, and measure
the quality gains using the ANLS* metric. In the reference run, fine-tuning lifted
the ANLS* score from **0.21** (pre-trained) to **0.86** (fine-tuned) on a 20-sample
test split — roughly a 3x improvement.

## Prerequisites

- An AWS account with access to [Amazon Bedrock](https://aws.amazon.com/bedrock/)
  and Amazon SageMaker AI (SageMaker Studio recommended).
- A SageMaker execution role with permissions for SageMaker training jobs, S3, and
  Bedrock (`bedrock:*`). See the [repo root README](../../../../README.md) for an
  example IAM policy.
- Access to a GPU training instance such as `ml.g5.12xlarge` (falls back to
  `ml.g5.2xlarge`). Check your service quotas before running Lab 2.
- Run the notebooks in order — each lab stores variables that later labs reuse.

## Workshop labs

Run the notebooks sequentially. Estimated total time is about 40 minutes of hands-on
work, plus training time in Lab 2 (which can run for a while in the background).

| Lab | Notebook | Focus | Est. time |
|-----|----------|-------|-----------|
| 1 | `Lab1_data_prep.ipynb` | Prepare and convert DocumentVQA data to the Bedrock conversation format and upload to S3 | 10 min |
| 2 | `Lab2_train.ipynb` | Fine-tune Nova-Lite with a SageMaker Training Job and inspect train/validation loss | 10 min* |
| 3 | `Lab3_import_deploy.ipynb` | Import the fine-tuned model into Bedrock and deploy for on-demand inference | 5 min |
| 4 | `Lab4_inference_testing.ipynb` | Run inference and qualitatively compare fine-tuned vs pre-trained responses | 10 min |
| 5 | `Lab5_quantitative_evals.ipynb` | Score both models with ANLS* and summarize the improvement | 5 min |

\* Lab 2 hands-on setup is ~10 minutes; the training job itself takes longer to
complete (environment setup alone is ~15-20 minutes).

### Lab 1 — Data preparation
Explore the DocumentVQA dataset, learn Nova's data-format requirements, split the
data into train/validation/test (60/20/20), convert each sample into the Bedrock
`bedrock-conversation-2024` schema with S3 image references, and upload everything
to S3.

### Lab 2 — Fine-tuning Nova-Lite
Configure a SageMaker PyTorch Estimator using a Nova-Lite training recipe from the
SageMaker HyperPod recipes repo, adjust hyperparameters (e.g. `max_epochs`), launch
the training job, and monitor training/validation loss. Fine-tuned model artifacts
are stored in an AWS-managed escrow S3 bucket; training metadata and loss curves
land in your account's output S3 location.

### Lab 3 — Import and deploy to Bedrock
Use the Bedrock `create_custom_model` API to import the model artifacts from the
escrow bucket, then deploy for on-demand inference. The deployment ARN is stored for
later labs.

### Lab 4 — Inference and qualitative testing
Call the Bedrock runtime API against the deployed custom model with real document
images and questions, and compare the fine-tuned model's answers against the
pre-trained baseline.

### Lab 5 — Quantitative evaluation
Run batch inference over the test split for both the fine-tuned and pre-trained
models, compute ANLS* scores, and review the side-by-side performance summary.

## Repository contents

```
amazon-nova-document-vqa-fine-tuning/
├── Lab1_data_prep.ipynb            # Data preparation
├── Lab2_train.ipynb                # SageMaker fine-tuning
├── Lab3_import_deploy.ipynb        # Import & deploy to Bedrock
├── Lab4_inference_testing.ipynb    # Qualitative inference testing
├── Lab5_quantitative_evals.ipynb   # ANLS* evaluation
├── HuggingFace_DocVQA/             # Sample dataset (100 images + metadata.jsonl)
│   ├── images/                     # 100 document .jpg images
│   └── metadata.jsonl              # file_name / prompt / completion records
└── utils/
    ├── anls_calculation.py         # ANLS* scoring helpers
    └── batch_inference.py          # Batch inference helpers for Bedrock
```

## Dataset

The `HuggingFace_DocVQA/` folder contains a pre-downloaded 100-sample subset of the
[HuggingFaceM4/DocumentVQA](https://huggingface.co/datasets/HuggingFaceM4/DocumentVQA)
dataset so you can run the workshop without downloading the full dataset. Each record
in `metadata.jsonl` has a `file_name`, a `prompt` (question), and a `completion`
(answer). Lab 1 converts these into the Bedrock conversation format.

## References

- [Amazon Nova fine-tuning – prepare data](https://docs.aws.amazon.com/nova/latest/userguide/fine-tune-prepare-data-understanding.html)
- [Amazon Nova fine-tuning (PEFT)](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-fine-tune.html#nova-fine-tune-peft)
- [SageMaker Python SDK](https://sagemaker.readthedocs.io/)
- [Overfitting vs. underfitting](https://aws.amazon.com/what-is/overfitting/)

## Workshop Contributors

This workshop was created by:

- **Ajit Kumar KP** — Sr. Specialist SA, GenAI, AWS
- **Arabinda Pani** — Pr. Partner SA, GenAI, AWS
- **Rajesh Gomatam** — Pr. Partner SA, Mfg., AWS
- **Shiva Mahalingam** — Sr. Solutions Architect, AGS, AWS
- **Vijay Karthick Baskar** — Sr. Partner SA, Mfg., AWS

## License

This sample is licensed under the MIT-0 License. See the [LICENSE](../../../../LICENSE)
file at the repository root.
