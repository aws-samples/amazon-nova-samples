# Evaluating Generative AI Models using Amazon Nova LLM-As-A-Judge on Amazon SageMaker AI

## Overview

This project demonstrates how to evaluate and compare generative AI models using **Amazon Nova LLM-As-A-Judge**, a scalable and automated evaluation framework. We compare two models:

* **Qwen2.5 1.5B Instruct** deployed on **Amazon SageMaker**
* **Claude 3.7 Sonnet** accessed via **Amazon Bedrock**

Although this is an **uneven comparison** due to the substantial size and capability gap between Claude 3.7 and Qwen2.5, the exercise serves to showcase how Amazon Nova can be used to benchmark and contrast any two LLMs under a unified evaluation framework. The focus is on demonstrating Amazon Nova's ability to objectively judge LLM responses.

---

## Goals

* Deploy a lightweight open-source model (Qwen2.5 1.5B) to SageMaker
* Query a powerful commercial model (Claude 3.7) via Bedrock
* Use a small set of natural language questions (e.g., SQuAD subset)
* Record model responses in JSONL format
* Use Amazon Nova LLM-as-a-Judge via a SageMaker Training Job to evaluate the responses
* Visualize results: win rates, confidence intervals, error rates

---

## Architecture

```
Prompt Set ├──> Qwen2.5 via SageMaker
           └──> Claude 3.7 via Bedrock
                      ↓
            Response pairs written to JSONL
                      ↓
     Amazon Nova LLM-as-a-Judge Training Job (SageMaker)
                      ↓
       Evaluation Metrics + Visualization + Win Rates
```

---

## Components

### 1. Model Setup

* **Qwen2.5-1.5B-Instruct**: Deployed to SageMaker using `HuggingFaceModel`.
* **Claude 3.7 Sonnet**: Queried via `boto3` and Amazon Bedrock runtime client.

### 2. Prompting

* Small question set sourced from `squad` dataset
* Each question sent to both models
* Responses stored as: `{ prompt, response_A, response_B }`

### 3. Evaluation

* JSONL file uploaded to S3
* SageMaker Training Job launched with Amazon Nova evaluation image
* Nova outputs preference scores, win rate, confidence intervals, and error metrics

---

## Evaluation Metrics Explained

* **a\_scores**: Count of Qwen2.5-preferred responses
* **b\_scores**: Count of Claude 3.7-preferred responses
* **ties**: Equal quality
* **inference\_error**: Failures in either generation or judging
* **winrate**: Proportion of B wins over valid comparisons
* **95% CI**: Confidence interval on winrate

---

## Sample Result Summary

* **Total Prompts:** 12
* **Claude 3.7 Wins:** 9
* **Qwen2.5 Wins:** 3
* **Ties/Inferences Errors:** 0
* **Win Rate:** 75% (CI: \[0.23, 0.91])

---

## Why This Comparison Is Useful

Despite the disparity between Claude 3.7 and Qwen2.5, we run this evaluation to:

* Showcase Amazon Nova's model-agnostic LLM-as-a-Judge pipeline
* Demonstrate integration of Bedrock and SageMaker models into the same evaluation loop
* Visualize quality gaps clearly using Nova's built-in analytics

---

## Requirements

* AWS Account with access to:

  * Amazon SageMaker
  * Amazon Bedrock
  * S3 for input/output
* IAM Role with permissions for:

  * SageMaker training and deployment
  * S3 access
  * Bedrock model invocation

---

## Conclusion

Amazon Nova LLM-as-a-Judge provides a reliable and scalable way to assess model quality, independent of source or vendor. This project highlights:

* **Easy side-by-side LLM evaluation**
* **Statistical rigor without human annotation**
* **Multicloud-friendly model comparison**

It also demonstrates how to bring together open-source and proprietary models under a unified benchmarking framework using AWS-native tools.
