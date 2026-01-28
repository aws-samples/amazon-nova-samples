# 🎨 Amazon Nova Customization Hub

**Welcome,to Nova Customization Hub!** 👋

Ready to make Amazon Nova models truly _yours_? You've come to the right place! This is your one-stop shop for fine-tuning, distilling, and customizing Nova models to match your unique use cases. Whether you're teaching Nova to speak SQL, creating artistic masterpieces, or building domain-specific AI assistants, we've got you covered.

---

## 🗺️ Navigation Guide

Think of this as your treasure map to Nova customization. Each path leads to powerful techniques for making Nova models work exactly the way you need them to.

### 📋 Quick Reference Tables

#### 🔷 Amazon Bedrock Customization

| 🎯 Use Case                            | 💡 What It Does                                                                                      | 🔗 Where To Go                                                                                                                                                       |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **🗄️ Text-to-SQL**                     | Convert natural language into SQL queries for your specific database schema                          | [`bedrock-finetuning/text-to-sql/`](bedrock-finetuning/text-to-sql/)                                                                                                 |
| **🧠 Understanding Fine-tuning**       | Customize Nova's understanding for document processing, OCR, and tool use                            | [`bedrock-finetuning/understanding/`](bedrock-finetuning/understanding/)                                                                                             |
| **🔄 Model Distillation (S3)**         | Create smaller, faster models by distilling knowledge from larger models using S3-based prompts      | [`bedrock-distillation/`](bedrock-distillation/) <br> 📓 [`Distillation-via-S3-input.ipynb`](bedrock-distillation/Distillation-via-S3-input.ipynb)                   |
| **📝 Model Distillation (Historical)** | Distill models using your historical API invocation logs                                             | [`bedrock-distillation/`](bedrock-distillation/) <br> 📓 [`Historical_invocation_distillation.ipynb`](bedrock-distillation/Historical_invocation_distillation.ipynb) |
| **💬 Citations Distillation**          | Teach compact models to provide citations like larger models                                         | [`bedrock-distillation/distillation_recipes/01_citations/`](bedrock-distillation/distillation_recipes/01_citations/)                                                 |
| **🛠️ Function Calling Distillation**   | Distill tool-use and function-calling capabilities into smaller models                               | [`bedrock-distillation/distillation_recipes/02_function_calling/`](bedrock-distillation/distillation_recipes/02_function_calling/)                                   |
| **🎨 Canvas Fine-tuning**              | Teach Nova Canvas to generate images in your unique style (like your pet, brand, or artistic vision) | [`bedrock-finetuning/canvas/`](bedrock-finetuning/canvas/)                                                                                                           |

#### ⚙️ HyperPod Setup (Nova 1.0 & 2.0) - Optional

| 🎯 Use Case                    | 💡 What It Does                                        | 🔗 Where To Go                                                                                                                                             |
| ------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **⚙️ HyperPod Cluster Setup**  | One-time setup for HyperPod RIG cluster (only needed for HyperPod-based training like RFT or distributed workloads) | [`hyperpod-rig-cluster-setup/`](hyperpod-rig-cluster-setup/) <br> 📓 [`Hyperpod Nova Cluster and Dependencies setup.ipynb`](hyperpod-rig-cluster-setup/Hyperpod%20Nova%20Cluster%20and%20Dependencies%20setup.ipynb) |

#### 🔶 SageMaker Nova 1.0 Customization

| 🎯 Use Case                    | 💡 What It Does                                        | 🛠️ Platform         | 🔗 Where To Go                                                                                                                                             |
| ------------------------------ | ------------------------------------------------------ | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **🔧 SFT/FFT/DPO Training**    | Fine-tune Nova 1.0 with full control over training     | Training Jobs       | [`Nova_1.0/SageMakerTrainingJobs/getting_started/`](Nova_1.0/SageMakerTrainingJobs/getting_started/)                                                       |
| **🏛️ LLM-as-a-Judge**          | Use Nova as an evaluator for other models              | Training Jobs       | [`Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-LLM-As-A-Judge/`](Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-LLM-As-A-Judge/)                                 |
| **🗄️ Text-to-SQL (SageMaker)** | Text-to-SQL fine-tuning with SageMaker                 | Training Jobs       | [`Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-Text-to-SQL-Sagemaker-Training/`](Nova_1.0/SageMakerTrainingJobs/Amazon-Nova-Text-to-SQL-Sagemaker-Training/) |
| **⚡ Distributed Training**    | Scale your training with distributed HyperPod clusters | HyperPod            | [`Nova_1.0/SageMakerHyperPod/getting_started/`](Nova_1.0/SageMakerHyperPod/getting_started/)                                                               |
| **🔧 CLI Utilities**           | Command-line tools for training workflows              | Training Jobs & Pod | [`Nova_1.0/SageMakerTrainingJobs/cli_utility/`](Nova_1.0/SageMakerTrainingJobs/cli_utility/)                                                               |

#### 🔵 SageMaker Nova 2.0 Customization

| 🎯 Use Case                         | 💡 What It Does                                           | 🔗 Where To Go                                                                                                                                       |
| ----------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **📊 Data Prep for Training**       | Prepare and format datasets for Nova 2.0 fine-tuning      | [`Nova_2.0/01_data_prep/`](Nova_2.0/01_data_prep/) <br> 📓 [`data_prep_sft_peft_fr.ipynb`](Nova_2.0/01_data_prep/data_prep_sft_peft_fr.ipynb)        |
| **🎓 Supervised Fine-Tuning (SFT)** | Train Nova 2.0 with your labeled examples using LoRA/PEFT | [`Nova_2.0/02_sft/`](Nova_2.0/02_sft/) <br> 📓 [`sft_peft_fr.ipynb`](Nova_2.0/02_sft/sft_peft_fr.ipynb)                                              |
| **🎯 Reinforcement Fine-Tuning (RFT)**  | Single-turn RFT training on HyperPod for improved model quality (requires HyperPod setup) | [`Nova_2.0/03_rft/`](Nova_2.0/03_rft/) <br> 📓 [`Hyperpod Nova RFT One-Stop Notebook (Single turn).ipynb`](Nova_2.0/03_rft/Hyperpod%20Nova%20RFT%20One-Stop%20Notebook%20(Single%20turn).ipynb) |
| **✅ Model Evaluation**             | Evaluate your fine-tuned Nova models with custom metrics  | [`Nova_2.0/04_eval/`](Nova_2.0/04_eval/) <br> 📓 [`eval.ipynb`](Nova_2.0/04_eval/eval.ipynb)                                                         |
| **🚀 Model Deployment**             | Deploy your custom Nova models to production              | [`Nova_2.0/05_deployment/`](Nova_2.0/05_deployment/) <br> 📓 [`deployment_custom_model.ipynb`](Nova_2.0/05_deployment/deployment_custom_model.ipynb) |
| **🎪 End-to-End Workshop**          | Complete SFT workflow from data prep to deployment        | [`Nova_2.0/workshop/EndToEnd_SFT_Workshop/`](Nova_2.0/workshop/EndToEnd_SFT_Workshop/)                                                               |

#### 🛠️ Utilities & Tools

| Tool                     | What It Does                                         | Link                                                                       |
| ------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| **Dataset Validator**    | Validate your training data format before submission | [Bedrock Distillation Validator](bedrock-distillation/dataset-validation/) |
| **FT-to-Eval Converter** | Convert fine-tuning datasets to evaluation format    | [Data Converter](SageMakerUilts/01-ft-to-eval-data-convertor/)             |
| **Job Monitor**          | Get email notifications for training job status      | [Job Monitoring](SageMakerUilts/SageMakerJobsMonitoring/)                  |

---

## 🎯 Which Path Should You Take?

### 🆕 **New to Nova Customization?**

Start here:

1. 📖 Read about [Model Distillation basics](bedrock-distillation/) - easiest way to get started
2. 🎨 Try [Canvas fine-tuning](bedrock-finetuning/canvas/) - fun and visual!
3. 📊 Move to [Data Prep](Nova_2.0/01_data_prep/) when ready for deeper customization

### 🏃 **Want Quick Wins with Bedrock?**

- 🔄 **Model Distillation**: Create efficient models without labeling data
  - Start with [`Distillation-via-S3-input.ipynb`](bedrock-distillation/Distillation-via-S3-input.ipynb)
- 🎨 **Canvas Fine-tuning**: Customize image generation
  - Jump to [`bedrock-finetuning/canvas/`](bedrock-finetuning/canvas/)
- 🗄️ **Text-to-SQL**: Build natural language database interfaces
  - Check out [`bedrock-finetuning/text-to-sql/`](bedrock-finetuning/text-to-sql/)

### 🔬 **Need Advanced Control with SageMaker?**

Perfect for:

- Custom training recipes
- Full parameter fine-tuning
- Large-scale distributed training
- Advanced DPO and RLHF

**Nova 2.0 Path** (Recommended for most users):

1. [`Nova_2.0/01_data_prep/`](Nova_2.0/01_data_prep/) → Prepare data
2. [`Nova_2.0/02_sft/`](Nova_2.0/02_sft/) → Train with SFT/PEFT (SageMaker Training Jobs or Bedrock)
3. [`Nova_2.0/03_rft/`](Nova_2.0/03_rft/) → Advanced RFT training on HyperPod (optional, requires [HyperPod setup](hyperpod-rig-cluster-setup/))
4. [`Nova_2.0/04_eval/`](Nova_2.0/04_eval/) → Evaluate results
5. [`Nova_2.0/05_deployment/`](Nova_2.0/05_deployment/) → Deploy to production

**Nova 1.0 Path** (For specific patterns):

- [`Nova_1.0/SageMakerTrainingJobs/`](Nova_1.0/SageMakerTrainingJobs/) - For advanced training techniques
- [`Nova_1.0/SageMakerHyperPod/`](Nova_1.0/SageMakerHyperPod/) - For distributed training at scale

---

## 🧰 Customization Techniques Explained

### 🔄 Model Distillation

**TL;DR**: Make your model smaller and faster while keeping it smart

**Perfect for:**

- Reducing inference costs (up to 10x cheaper!)
- Improving latency (faster responses)
- Deploying to resource-constrained environments

**Key Benefits:**

- ✨ No manual labeling required
- 💰 Lower operational costs
- ⚡ Faster inference
- 🎯 Maintains task-specific accuracy

**Real-world use cases:**

- RAG applications
- Document summarization
- Chatbot deployments
- Text classification

### 🎓 Fine-Tuning (SFT/PEFT)

**TL;DR**: Teach Nova your specific style, format, or domain

**Perfect for:**

- Custom response formats
- Domain-specific language
- Behavioral adjustments
- Consistent tone and style

**Key Benefits:**

- 🎨 Behavior customization
- 📝 Format control
- 🎯 Task specialization
- 💪 Improved on-task performance

**When to use:**

- You have clear input-output examples
- Need consistent formatting or tone
- Want to teach specific decision patterns
- Have thousands of quality examples

### 🏋️ Full Fine-Tuning (FFT)

**TL;DR**: Update all model parameters for maximum adaptation

**Perfect for:**

- Significant domain shifts
- Large, high-quality datasets
- Maximum performance requirements

**Key Benefits:**

- 🚀 Best possible performance
- 🔧 Complete model adaptation
- 📊 Handles complex domain knowledge

**Trade-offs:**

- 💰 Higher computational cost
- ⏱️ Longer training time
- 🎯 Requires more data

### 🎯 Reinforcement Fine-Tuning (RFT)

**TL;DR**: Improve model performance through feedback signals (rewards) rather than exact correct answers

Reinforcement Fine-Tuning uses reward functions to evaluate model responses and iteratively optimizes the model to maximize these rewards. Unlike traditional supervised fine-tuning that learns from input-output pairs, RFT uses measurable scores indicating response quality to guide learning.

**Perfect for:**

- Tasks where defining exact correct outputs is challenging, but you can measure response quality
- Creative writing, code optimization, or complex reasoning tasks
- Applications requiring nuanced decision-making or adherence to specific quality criteria
- Balancing multiple competing objectives (accuracy, efficiency, style)

**Key Benefits:**

- 📈 Learns complex behaviors through trial and feedback
- 🎯 Optimizes for measurable success criteria without needing exact outputs
- 🔄 Handles subjective or multifaceted quality requirements
- ⚡ Supports reasoning mode for complex problem-solving tasks

**When to use:**

- You can define clear, measurable success criteria but struggle to provide exact correct outputs
- Quality is subjective or multifaceted with multiple valid solutions
- Need iterative improvement, personalization, or adherence to complex business rules
- Working with single-turn interactions where output quality can be objectively measured

**What RFT excels at:**

- Creative content generation with style constraints
- Code generation with performance optimization
- Complex reasoning tasks requiring step-by-step problem solving
- Dialogue systems balancing helpfulness, safety, and engagement

**Supported Models:**

- Amazon Nova Lite 2.0 (amazon.nova-2-lite-v1:0:256k)

**Requirements:**

- HyperPod RIG cluster (see [cluster setup guide](hyperpod-rig-cluster-setup/) for one-time setup)
- Training data with reward signals or evaluator to score responses
- SageMaker Studio JupyterLab environment

**Note**: RFT currently requires HyperPod. For other training methods (SFT, DPO), you can use Bedrock or SageMaker Training Jobs without HyperPod setup.

**Learn more**: [AWS Documentation on RFT](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-hp-rft.html)

---

## 🎓 Learning Paths

### 🌟 **Beginner Path** (1-2 hours)

Perfect if you're just starting with Nova customization:

1. **Start**: [Nova Lite Fine-tuning](bedrock-finetuning/understanding/)
2. **Learn**: [Model Distillation Basics](bedrock-distillation/)
3. **Practice**: [Text-to-SQL Tutorial](bedrock-finetuning/text-to-sql/)

### 🔥 **Intermediate Path** (1 day)

You've done some ML before and want to dive deeper:

1. **Data Prep**: [Nova 2.0 Data Preparation](Nova_2.0/01_data_prep/)
2. **Training**: [Supervised Fine-Tuning with PEFT](Nova_2.0/02_sft/)
3. **Advanced Training**: [Reinforcement Fine-Tuning (RFT)](Nova_2.0/03_rft/)
4. **Evaluation**: [Model Evaluation Techniques](Nova_2.0/04_eval/)
5. **Deploy**: [Production Deployment](Nova_2.0/05_deployment/)

### 🚀 **Advanced Path** (2-3 days)

Complete End To End Workshop

1. **SFT End to End Workshop**:[End To End SFT from Data prep to Deployment](Nova_2.0/workshop/EndToEnd_SFT_Workshop/)
2. **SFT, RFT End to End Workshop**:[End To End SFT from Data prep to Deployment](Nova_2.0/workshop/EndToEnd_SFT_RFT_Workshop/)

---

## 🛠️ Tools & Utilities

Don't miss these helpful tools that make customization easier:

| Tool                     | What It Does                                         | Link                                                                       |
| ------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| **Dataset Validator**    | Validate your training data format before submission | [Bedrock Distillation Validator](bedrock-distillation/dataset-validation/) |
| **FT-to-Eval Converter** | Convert fine-tuning datasets to evaluation format    | [Data Converter](SageMakerUilts/01-ft-to-eval-data-convertor/)             |
| **Job Monitor**          | Get email notifications for training job status      | [Job Monitoring](SageMakerUilts/SageMakerJobsMonitoring/)                  |
| **CLI Utilities**        | Command-line tools for common workflows              | [SageMaker CLI](Nova_1.0/SageMakerTrainingJobs/cli_utility/)               |

---

## 💡 Pro Tips

### 🎯 Data Quality > Data Quantity

- **Start small**: 100 high-quality examples > 10,000 mediocre ones
- **Be consistent**: Format and style matter as much as content
- **Validate early**: Use validators before submitting training jobs

### 💰 Cost Optimization

- **Try distillation first**: Often cheaper and faster than fine-tuning
- **Use PEFT**: LoRA training is 10x cheaper than full fine-tuning
- **Start with Micro**: Test on smaller models before scaling up

### ⚡ Speed Optimization

- **Parallel experiments**: Run multiple small experiments simultaneously
- **Use provisioned throughput**: For production workloads
- **Cache frequently**: Leverage caching for repeated patterns

### 🔧 HyperPod Setup

- **When needed**: Only required if you're using HyperPod for distributed training or RFT (not needed for Bedrock or SageMaker Training Jobs)
- **One-time setup**: Complete the [cluster setup](hyperpod-rig-cluster-setup/) once per environment (works for both Nova 1.0 and 2.0)
- **Reusable**: Once configured, use the same cluster for multiple training jobs
- **Prerequisites**: Ensure you have SageMaker Studio JupyterLab with sufficient storage (50GB+)
- **Use cases**: RFT training and large-scale distributed training workloads

### 🔍 Debugging Tips

- **Monitor metrics**: Check loss curves during training
- **Test incrementally**: Validate each step before moving forward
- **Compare baselines**: Always test against base model performance

---

## 🎪 Complete Workflows

### End-to-End Bedrock Workflow

```
📊 Prepare Data → 🔄 Distill/Fine-tune → ✅ Evaluate → 🚀 Deploy → 📈 Monitor
```

Perfect for: Quick iteration, managed infrastructure

### End-to-End SageMaker Workflow

```
📊 Prep Data → 🎓 Train (SFT/DPO on Training Jobs or RFT on HyperPod) → ✅ Evaluate → 🚀 Deploy → 📈 Monitor → 🔄 Iterate
```

Perfect for: Custom requirements, maximum control, advanced training techniques

**Note**: HyperPod setup only needed when developing on Hyperpod Cluster

---

## 🤝 Need Help?

- 📚 **Documentation**: Each folder has detailed READMEs
- 💬 **Examples**: Every technique includes working notebooks
- 🐛 **Issues**: Use GitHub issues for bugs or questions
- 🎓 **Workshops**: Check out complete workshops for guided learning

---

## 🎉 What's Next?

Ready to customize? Here's your action plan:

1. **Pick a use case** from the table above
2. **Follow the learning path** that matches your experience
3. **Run the notebooks** step-by-step
4. **Experiment and iterate** - customization is a journey!

Remember: Every expert started as a beginner. Start small, iterate fast, and have fun building with Nova! 🚀

---

**Happy Customizing!** 🎨✨

_Pro tip: Bookmark this page - it's your navigation hub for all things Nova customization!_
