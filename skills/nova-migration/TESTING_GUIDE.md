# Testing the nova-migration Skill (Complete Guide)

This guide shows how to test the **nova-migration skill** without Claude Code. Choose your path based on time available.

---

## ⚡ Quick Start (2 minutes)

```bash
cd amazon-nova-samples/skills/nova-migration

# Verify AWS is ready
aws sts get-caller-identity

# Run the test
python3 test_skill.py --live
```

**Expected output:**
```
==== 100 passed, 0 failed ====
ALL GREEN ✅
```

That's it! Skip to [✅ Success](#-success) section below.

---

## 📋 Prerequisites (2 minutes)

### Check AWS Credentials
```bash
aws sts get-caller-identity
```

Should output JSON with your account info. If not:
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

### Check Python & boto3
```bash
python3 --version          # Should be 3.9+
python3 -c "import boto3; print('✓')"
```

If boto3 is missing:
```bash
pip install boto3
```

---

## 🧪 Testing Methods

Choose based on what you want to test:

### Method 1: Offline Tests (10 seconds) ⚡
**No AWS calls, instant verification**

```bash
python3 test_skill.py
```

**What it validates:**
- ✅ All SKILL.md files have proper frontmatter
- ✅ References point to real files
- ✅ Router correctly detects Claude vs Gemini
- ✅ All Nova code examples are valid Python
- ✅ Nova invariants enforced (typed blocks, nested inferenceConfig)

**Result:** 95 tests pass

---

### Method 2: Live Bedrock Test (30 seconds) ✅ RECOMMENDED
**Tests real migration with Nova on Bedrock**

```bash
python3 test_skill.py --live
```

**What it does:**
1. Loads skill content from `references/nova-target.md` and `gemini/SKILL.md`
2. Sends a sample Gemini code snippet to Nova on Bedrock
3. Validates that Nova's output:
   - ✅ Uses `boto3 converse`
   - ✅ Targets `nova-2-lite` model ID
   - ✅ Nests inference config correctly
   - ✅ Removes source SDK imports
   - ✅ Follows Nova invariants

**Result:** 100 tests pass (95 offline + 5 live)

**Output example:**
```
----- model output -----
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "Be concise"}],
    messages=[{"role": "user", "content": [{"text": "Summarize cloud computing."}]}],
    inferenceConfig={"temperature": 0.2}
)
------------------------
  [ok] output calls boto3 converse
  [ok] output targets nova-2-lite
  [ok] output nests inferenceConfig
  [ok] output drops google genai SDK
```

---

### Method 3: Test Your Own Code (5 minutes) 📝

**Migrate your actual Claude or Gemini code**

#### Option A: Quick inline script

```bash
python3 << 'EOF'
import boto3
from botocore.config import Config

# Load skill documentation
with open("references/nova-target.md") as f:
    nova_target = f.read()
with open("claude/SKILL.md") as f:
    claude_skill = f.read()

# Your source code
source_code = """
from anthropic import Anthropic
client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-5-haiku",
    max_tokens=1024,
    system="You are helpful",
    messages=[{"role": "user", "content": "Hello"}]
)
"""

# Send to Nova
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{
            "text": f"Migrate to Nova:\n\n{nova_target}\n\n{claude_skill}\n\n```python\n{source_code}\n```\n\nOutput ONLY the migrated code."
        }]
    }],
    inferenceConfig={"maxTokens": 2048, "temperature": 0}
)

print(response["output"]["message"]["content"][0]["text"])
EOF
```

#### Option B: Create a migration script

```python
# migrate.py
import boto3
import re
from botocore.config import Config

with open("references/nova-target.md") as f:
    nova_target = f.read()
with open("claude/SKILL.md") as f:
    claude_skill = f.read()
with open("my_code.py") as f:
    source_code = f.read()

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{
            "text": f"Migrate this code to Nova 2 Lite on Bedrock.\n\n"
                   f"Nova target spec:\n{nova_target}\n\n"
                   f"Claude migration guide:\n{claude_skill}\n\n"
                   f"Code to migrate:\n```python\n{source_code}\n```\n\n"
                   f"Output ONLY the migrated Python code in a ```python block."
        }]
    }],
    inferenceConfig={"maxTokens": 2048, "temperature": 0}
)

output = response["output"]["message"]["content"][0]["text"]
migrated = re.search(r"```python\n(.*?)\n```", output, re.S)

if migrated:
    print(migrated.group(1))
else:
    print(output)
```

Run it:
```bash
python3 migrate.py
```

---

### Method 4: Manual Step-by-Step Transformation (15 minutes) 📚

**Understand the transformation without calling Bedrock**

#### Claude → Nova transformation rules:

**1. SDK swap**
```python
# Before
from anthropic import Anthropic
client = Anthropic(api_key="...")

# After
import boto3
from botocore.config import Config
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
```

**2. Method call**
```python
# Before
response = client.messages.create(
    model="claude-3-5-haiku",

# After
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
```

**3. System prompt**
```python
# Before
system="You are helpful"

# After
system=[{"text": "You are helpful"}]
```

**4. Message content**
```python
# Before
messages=[{"role": "user", "content": "Hello"}]

# After
messages=[{"role": "user", "content": [{"text": "Hello"}]}]
```

**5. Inference parameters**
```python
# Before
max_tokens=1024
temperature=0.7

# After
inferenceConfig={"maxTokens": 1024, "temperature": 0.7}
```

**6. Complete example**
```python
# BEFORE (Claude)
from anthropic import Anthropic
client = Anthropic(api_key="sk-...")
response = client.messages.create(
    model="claude-3-5-haiku",
    max_tokens=1024,
    temperature=0.7,
    system="You are a helpful assistant.",
    messages=[
        {"role": "user", "content": "Explain cloud computing"}
    ]
)
print(response.content[0].text)

# AFTER (Nova)
import boto3
from botocore.config import Config
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[
        {"role": "user", "content": [{"text": "Explain cloud computing"}]}
    ],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7}
)
print(response["output"]["message"]["content"][0]["text"])
```

---

### Method 5: Batch Processing Multiple Samples (10 minutes) 🔄

**Test many code samples at once**

```python
# batch_migrate.py
import boto3
import re
from botocore.config import Config

# Load skills once
with open("references/nova-target.md") as f:
    nova_target = f.read()
with open("claude/SKILL.md") as f:
    claude_skill = f.read()

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))

samples = {
    "basic_text": """
from anthropic import Anthropic
client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-5-haiku",
    max_tokens=512,
    messages=[{"role": "user", "content": "Hello"}]
)
""",
    "with_system_prompt": """
from anthropic import Anthropic
client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-5-haiku",
    system="Be concise",
    messages=[{"role": "user", "content": "Explain AI"}]
)
""",
}

for name, source in samples.items():
    print(f"\n{'='*60}")
    print(f"Migrating: {name}")
    print(f"{'='*60}")
    
    response = client.converse(
        modelId="us.amazon.nova-2-lite-v1:0",
        messages=[{
            "role": "user",
            "content": [{
                "text": f"Migrate to Nova:\n{nova_target}\n{claude_skill}\n```python\n{source}\n```\nOutput ONLY code."
            }]
        }],
        inferenceConfig={"maxTokens": 2048, "temperature": 0}
    )
    
    migrated = response["output"]["message"]["content"][0]["text"]
    print(migrated)
```

Run it:
```bash
python3 batch_migrate.py
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: boto3` | `pip install boto3` |
| `NoCredentialsError` | `aws configure` |
| `UnknownServiceError: bedrock-runtime` | `export AWS_DEFAULT_REGION=us-east-1` |
| `EOF while scanning triple-quoted string` | Your code sample has syntax errors (not the skill) |
| Tests timeout (>60s) | Normal Bedrock latency; check internet; try again |
| `ConnectionError` | Check AWS credentials and network |

---

## ✅ Success

All tests pass when you see:

```
==== 100 passed, 0 failed ====
ALL GREEN ✅
```

This means:
- ✅ Skill structure is correct
- ✅ Router logic works
- ✅ Code examples are valid
- ✅ **Real migrations work on Bedrock**

---

## 📊 Test Coverage

```
Offline Tests (no AWS calls):
  ✅ Structure & lint         (14 checks)
  ✅ Router logic              (7 checks)
  ✅ Code examples            (74 checks)
  ────────────────────────────
  Subtotal:                   (95 checks)

Live Tests (Bedrock):
  ✅ Real migration           (5 checks)
  ────────────────────────────
  Total:                     (100 checks)
```

---

## ⏱️ Time & Cost Summary

| Method | Time | Cost | What |
|--------|------|------|------|
| Method 1 | 10 sec | $0 | Offline structure test |
| Method 2 | 30 sec | $0.001 | Real migration test |
| Method 3 | 5 min | $0.001 | Your own code |
| Method 4 | 15 min | $0 | Manual transformation |
| Method 5 | 10 min | $0.01+ | Batch processing |

---

## 🎯 Validation Checklist

After migrating code, verify:

- [ ] Uses `boto3` (not `anthropic` or `google`)
- [ ] Uses `converse()` (not `messages.create()`)
- [ ] Model ID is `us.amazon.nova-2-lite-v1:0`
- [ ] System prompt is `[{"text": "..."}]` (list of objects)
- [ ] Message content is `[{"text": "..."}]` (typed blocks)
- [ ] Inference params in `inferenceConfig` (camelCase)
- [ ] No top-level `max_tokens` or `temperature`
- [ ] Code parses as valid Python
- [ ] Code runs without errors

---

## 💡 Understanding the Skill

The **nova-migration skill** converts Python LLM code:
- **From:** Claude (Anthropic) or Gemini (Google)
- **To:** Nova 2 Lite on Bedrock

**Key transformations:**
1. SDK change (anthropic/google → boto3)
2. Auth change (API key → AWS IAM)
3. Method change (messages.create/generate_content → converse)
4. Parameter nesting (top-level → inferenceConfig)
5. Data structure changes (strings → typed blocks)
6. Prompt format (XML tags → ##Section## delimiters)

---

## 📖 Detailed Documentation

For more info, see:
- `SKILL.md` — Main skill definition
- `claude/SKILL.md` — Claude-specific migrations
- `gemini/SKILL.md` — Gemini-specific migrations
- `references/nova-target.md` — Nova target specification
- `references/code-examples.md` — Before/after examples
- `references/feature-mapping.md` — Complete feature map

---

## 🚀 Next Steps

1. **Test offline:** `python3 test_skill.py`
2. **Test live:** `python3 test_skill.py --live`
3. **Migrate your code:** Use Method 3 above
4. **Validate output:** Check against validation checklist
5. **Deploy:** Use migrated code with confidence

---

## ✨ Pro Tips

✅ Use `temperature=0` for deterministic migrations  
✅ Use `maxTokens=2048` for complex code  
✅ Always validate output before deploying  
✅ Read `references/code-examples.md` for real examples  
✅ Keep AWS credentials in `~/.aws/credentials` (never in code)  

---

## ❓ FAQ

**Q: Do I need Claude Code?**  
A: No. This guide works without it.

**Q: Can I test offline?**  
A: Yes, use Method 1 (`python3 test_skill.py`).

**Q: How much does testing cost?**  
A: ~$0.001 per live test (minimal Bedrock usage).

**Q: Is the skill production-ready?**  
A: Yes! 100 tests pass, all invariants verified.

**Q: What if migration is wrong?**  
A: Check the validation checklist. File an issue if there's a bug.

---

## 📞 Support

- **Tests won't run:** Check Troubleshooting section above
- **Migration output wrong:** Validate against checklist
- **Found a bug:** File an issue with example code
- **Want more details:** Read the SKILL.md files in claude/ and gemini/ directories

---

**Status:** ✅ **READY TO USE**  
**Test Coverage:** 100 tests passing  
**Last Validated:** 2026-06-08
