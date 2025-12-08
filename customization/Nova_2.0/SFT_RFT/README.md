# Securities Law Synthetic Data for Amazon Nova Fine-Tuning

## Non-determinsitc raw data and samples generation
Please note that each download of raw data sources is non-deterministic. So is the fine-tuning samples generation by virtue of using LLM.


## License
The license for the datasets crawled and distributed in this example is CC-BY-4. Find attached file at data/CC-BY-4.0.txt

## 🎯 Overview

The training data demonstrates:
- **Query Type Classification**: Categorizing legal questions into 8 predefined types
- **Tool Selection**: Choosing appropriate tools from 4 available legal research tools
- **Reasoning**: Providing clear justification for each tool selection decision
- **Sequential Analysis**: Determining optimal tool sequences for complex queries
- **Cross-Document Analysis**: Connecting SEC regulations, EDGAR filings, and case law

## 🏗️ Architecture

```
📁 Data Sources → 🔄 Processing → 🤖 Generation → ✅ Validation → 🚀 Training
     ↓              ↓             ↓              ↓              ↓
┌─────────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐
│ EDGAR       │ │ Parsing  │ │ Synthetic   │ │ Post     │ │ Nova        │
│ SEC Regs    │ │ Cleaning │ │ Data Kit    │ │ Process  │ │ Fine-tuning │
│ Case Law    │ │ Indexing │ │ Data Gen    │ │ Fixed/LLM│ │ Evaluation  │
└─────────────┘ └──────────┘ └─────────────┘ └──────────┘ └─────────────┘
```

## 📊 Data Sources

The training data is built from three interconnected information sources that together provide comprehensive coverage of securities law:

### 1. EDGAR Filings (Securities Agreements)
Contains actual agreement language and compliance clauses from SEC filings. These documents demonstrate how regulations are implemented in practice through material contracts, exhibits, and disclosure documents.

### 2. SEC Regulations (Authoritative Rules)
Provides the official regulatory text and requirements from the Code of Federal Regulations. These define the legal standards and obligations that agreements must comply with, covering areas such as private placements, restricted securities resales, and anti-fraud provisions.

### 3. Case Law (Judicial Interpretations)
Judicial interpretations - how regulations are applied in real-world scenarios. These cases provide context for understanding regulatory requirements and compliance validation.

### Interconnections
The three sources form a data source for tool-assisted securities law analysis across private stock sales, public offerings, restricted securities resales, and compliance validation:
- **Regulations** establish the rules and definitions
- **EDGAR filings** show practical implementation of those rules
- **Case law** provides judicial interpretation and application guidance

This inter-connected corpus enables the model to perform cross-document analysis, connecting regulatory requirements with actual contract language and court precedents.

## 🛠️ Available Tools

Models learn to select from 4 specialized legal research tools:

| Tool | Purpose | Parameters |
|------|---------|------------|
| `statute_retrieval` | Fetch SEC regulation text | `{"regulation": "str"}` |
| `case_law_search` | Search judicial precedents | `{"query": "str"}` |
| `compliance_checker` | Validate agreement clauses | `{"query": "str", "edgar_check": "str", "regulation": "str", "case_interpretation_check": "str"}` |
| `citation_validator` | Validate legal citations | `{"query": "str"}` |

## 🎯 Query Types

Models learn to classify queries into 8 predefined categories:

| Type | Tools Used | Description |
|------|------------|-------------|
| `regulatory_definition` | statute_retrieval | Single regulatory lookup |
| `judicial_interpretation` | case_law_search | Court precedent research |
| `compliance_validation` | compliance_checker | Agreement clause validation |
| `citation_verification` | citation_validator | Legal citation checking |
| `regulatory_compliance_analysis` | statute_retrieval → compliance_checker | Multi-step regulatory analysis |
| `judicial_compliance_assessment` | case_law_search → compliance_checker | Court precedent + validation |
| `cross_document_analysis` | statute_retrieval → case_law_search → compliance_checker | Full 3-source analysis |
| `regulatory_interpretation_research` | statute_retrieval → case_law_search | Regulation + precedent research |

## Generate Raw Data
The notebook `TBA.ipynb` contains the data generation workflow:

```python
# Download EDGAR agreements
download_edgar_agreements(num_filings=500, output_path="data/raw/edgar")

# Download SEC regulations  
download_sec_regulations(output_path="data/raw/regulations")

# Download case law
download_courtlistener_cases(max_cases=5000, output_path="data/raw/cases")
```

### 3. Generate Synthetic Training Data

Data is generate using [Synthetic Data Generation Kit](https://github.com/meta-llama/synthetic-data-kit) from Meta to create training examples.

- **Model Routing**: A local Flask server (`aws_proxy.py`) routes API requests from the kit to AWS services (SageMaker endpoints and Bedrock models), bypassing the kit's API key requirement and authenticating via [AWS SigV4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) using a signature created by using access keys (access key ID, secret access key.
- **Prompt Engineering**: Custom prompts can be provided in the kit's or user-provided configuration file (`aws-config.yaml`). Follow model-specific best practices for prompting to ensure high-quality generation
- **Flexible Configuration**: `aws_proxy.py` supports multiple AWS options - Bedrock models via model ID or inference profile ID, and SageMaker real-time endpoints via deployed model name

```bash
# Bedrock with model ID
python aws_proxy.py --platform br --model-id <model-id>

# Bedrock with inference profile ID
python aws_proxy.py --platform br --model-id <inference-profile-id>

# SageMaker real-time endpoint
python aws_proxy.py --platform sm --endpoint <endpoint-name>
```

## 🎯 Training Data Examples

### Single-Tool Query (regulatory_definition)
```json
{
  "messages": [
    {
      "role": "system",
      "content": [{"text": "You are a securities law tool selection specialist..."}]
    },
    {
      "role": "user", 
      "content": [{"text": "What is the SEC definition of an accredited investor?"}]
    },
    {
      "role": "assistant",
      "content": [{
        "text": "{\"Query analysis\": {\"Type\": \"regulatory_definition\", \"Information needed\": \"Official SEC definition of accredited investor\", \"Tools\": [{\"Tool\": \"statute_retrieval\", \"Parameters\": {\"regulation\": \"Rule 501\"}, \"Reasoning\": \"Definition questions require authoritative regulatory text from Rule 501 of Regulation D\"}]}}"
      }]
    }
  ]
}
```

### Multi-Tool Query (cross_document_analysis)
```json
{
  "Query analysis": {
    "Type": "cross_document_analysis",
    "Information needed": "Rule 144 requirements + judicial interpretation + EDGAR clause validation", 
    "Tools": [
      {
        "Tool": "statute_retrieval",
        "Parameters": {"regulation": "Rule 144"},
        "Reasoning": "Must first establish regulatory foundation before interpretation or validation"
      },
      {
        "Tool": "case_law_search",
        "Parameters": {"query": "Rule 144 holding period judicial interpretation"}, 
        "Reasoning": "Need court precedent on how holding periods are calculated in practice"
      },
      {
        "Tool": "compliance_checker",
        "Parameters": {
          "query": "6-month lockup compliance",
          "edgar_check": "EDGAR transfer restriction clause",
          "regulation": "Rule 144", 
          "case_interpretation_check": "Court precedent on lockup periods"
        },
        "Reasoning": "Final validation requires regulation + case law + specific EDGAR clause analysis"
      }
    ]
  }
}
```

## ✅ Quality Assurance
### Validation Checks
- ✅ **JSON Format**: Valid JSONL structure
- ✅ **Message Structure**: System, user, assistant message format
- ✅ **System Prompt**: Exact prompt matching
- ✅ **Tool Names**: Valid tool selection from available set
- ✅ **Parameters**: Correct parameter names and types
- ✅ **Query Types**: Classification into predefined categories
- ✅ **Reasoning**: Non-empty reasoning strings

### Error Categories Detected
| Error Type | Description | Auto-Fix |
|------------|-------------|----------|
| `json_parse_error` | Invalid JSON syntax | ✅ Remove line |
| `missing_tool_parameters` | Required parameters missing | ✅ Remove line |
| `invalid_tool_name` | Tool not in available set | ✅ Remove line |
| `invalid_predefined_type` | Query type not in predefined list | ✅ Remove line |
| `system_prompt_mismatch` | System prompt doesn't match exactly | ✅ Remove line |


## 📈 Data Goals for Fine-Tuning

Based on evaluation results, the fine-tuned model achieves:
- **Tool Selection Accuracy**: %+ on securities law queries
- **Reasoning Quality**: High coherence and legal accuracy
- **Multi-Tool Sequencing**: Correct tool ordering for complex queries
- **Cross-Document Analysis**: Effective integration of regulatory, case law, and EDGAR sources

## 📚 References

- [SEC EDGAR Database](https://www.sec.gov/edgar)
- [Cornell Law CFR](https://www.law.cornell.edu/cfr/)
- [CourtListener](https://www.courtlistener.com/)
- [Amazon Nova Documentation](https://docs.aws.amazon.com/nova/)
- [SageMaker Training Documentation](https://docs.aws.amazon.com/sagemaker/)
