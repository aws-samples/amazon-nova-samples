# Supervised Fine-Tuning (SFT) for Model Customization

## 1. Introduction

Supervised Fine-Tuning (SFT) is the classic approach of training an LLM on a dataset of human-labeled input-output pairs for a specific task. You provide examples of prompts (questions, instructions, etc.) along with the correct or desired responses, and continue training the model on these pairs. The model's weights are adjusted to minimize a supervised loss, typically cross-entropy between its predictions and the target output tokens.

**Crucially, SFT changes behavior, not knowledge.** It doesn't make the model learn new facts or jargon it never saw in pre-training. It teaches the model how to answer, not what to know. If you need new domain knowledge (e.g., internal terminology), consider retrieval-augmented generation (RAG) to provide that context at inference time.

### How It Works

The LLM is optimized by minimizing the standard next-token loss on the response tokens while masking the prompt, so the model internalizes your target style, structure, and decision rules. The model learns to generate the correct completion for each prompt by training on high-quality prompt-response pairs until it outputs the right response with high probability.

SFT can be done with as few as a few thousand examples and can scale up to a few hundred thousand. SFT samples are expected to be very high quality and directly aligned with the desirable behavior of the model.

### Parameter-Efficient Fine-Tuning (PEFT)

PEFT methods like LoRA (Low-Rank Adaptation) allow you to perform SFT by training only a small subset of parameters rather than the entire model. Instead of updating all model weights, PEFT adds small trainable modules or adapters while keeping the base model frozen. This approach:

- **Reduces computational costs** by training only 1-10% of the original parameters
- **Enables faster training** with lower memory requirements
- **Allows multiple task-specific adapters** to be stored and swapped for the same base model
- **Maintains model stability** by preserving the pre-trained weights

PEFT is particularly valuable for SFT when you want cost-efficient customization without the overhead of full model fine-tuning.

## 2. When to Use

SFT is best when you have a well-defined task with clear desired outputs. If you can explicitly say "Given X input, the correct/desired output is Y" and you can gather examples of such X-Y mappings, then supervised fine-tuning is a great choice.

### Ideal Scenarios for SFT:

- **Structured or complex classification tasks**: Classifying internal documents or contracts into many custom categories where the model can learn specific categories far better than prompting alone
- **Question-answering or transformation tasks with known answers**: Fine-tuning a model to answer questions from a company's knowledge base, or to convert data between formats where each input has a correct response
- **Formatting and style consistency**: When you need the model to always respond in a certain format or tone, training on examples of the correct format/tone to demonstrate particular brand voice or style

### Use SFT When:

- You can assemble high-quality prompt and response pairs that closely mirror the behavior you want
- Tasks have clear targets or deterministic formats such as schemas, function or tool calls, and structured answers
- You want behavior shaping: getting the model to treat prompts as tasks, follow instructions, adopt tone and refusal policies, and produce consistent formatting
- You need a straightforward, cost-efficient update (favor parameter-efficient methods like LoRA)

### When NOT to Use SFT:

- **Knowledge gaps rather than behavior gaps**: SFT will not make the model learn new facts, jargon, or recent events. Use retrieval-augmented generation instead
- **When you can measure quality but cannot label a single right answer**: Use reinforcement fine-tuning with verifiable rewards or LLM-as-a-judge
- **Frequently changing needs or content**: Rely on retrieval and tool use rather than retraining the model

## 3. Prerequisites

- High-quality dataset of prompt-response pairs (thousands to hundreds of thousands of demonstrations)
- Clear understanding of the desired behavior or output format
- Data quality, consistency, and deduplication processes
- Access to fine-tuning infrastructure and compute resources
- Evaluation metrics to measure model performance on your specific task

## 4. Execution

### 4.1 SageMaker Training Job

```
# Create Estimator
estimator = PyTorch(
    output_path=output_path,
    base_job_name=sm_training_job_name,
    role=role,
    disable_profiler=True,
    debugger_hook_config=False,
    instance_count=instance_count,
    instance_type=instance_type,
    training_recipe=training_recipe,
    recipe_overrides=recipe_overrides,
    max_run=432000,
    sagemaker_session=sagemaker_session,
    image_uri=image_uri,
    tags=[
        {'Key': 'model_name_or_path', 'Value': model_name_or_path},
    ]
)


# Define Input Channels
train_input = TrainingInput(
    s3_data=train_dataset_s3_path,
    distribution="FullyReplicated",
    s3_data_type="Converse",
)

val_input = TrainingInput(
    s3_data=val_dataset_s3_path,
    distribution="FullyReplicated",
    s3_data_type="Converse",
)

# Fit the model
estimator.fit(inputs={"train": train_input, "validation": val_input}, wait=False)
```

### 4.2 SageMaker Hyperpod

### 4.3 Bedrock UI
[Add screen shots here]

### 4.4 Bedrock CLI
*[This section will be completed separately]*
