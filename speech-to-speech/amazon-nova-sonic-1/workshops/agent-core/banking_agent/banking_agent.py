from strands import Agent, tool
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel
import re, argparse

app = BedrockAgentCoreApp()

@tool
def get_account_balance(account_id) -> str:
    """Get account balance for given account Id

    Args:
        account_id: Bank account Id
    """

    # In this sample, we use a mock response. 
    # The actual implementation will retrieve information from a database API or another backend service.
    result = {
      "account_id": "1234567890",
      "account_type": "Checking",
      "currency": "USD",
      "balance": {
        "available": 1543.75,
        "current": 1600.00,
        "pending": 56.25
      },
      "last_updated": "2025-08-24T14:30:00Z"
    }
    return {"result": result}

@tool
def get_statement(account_id: str, year_and_month: str) -> str:
    """Get account statement for a given year and month
    Args:
        account_id: Bank account Id
        year_and_month: Year and month of the bank statement. For example: 2025_08 or August 2025
    """
    # In this sample, we use a mock response. 
    # The actual implementation will retrieve information from a database API or another backend service.
    result = {
          "account_id": "1234567890",
          "account_type": "Checking",
          "currency": "USD",
          "statement_period": {
            "start_date": "2025-07-24",
            "end_date": "2025-08-24"
          },
          "opening_balance": 2450.00,
          "closing_balance": 1543.75,
          "transactions": [
            {
              "date": "2025-07-26",
              "description": "Payroll Deposit",
              "type": "credit",
              "amount": 3200.00,
              "balance_after": 5650.00
            },
            {
              "date": "2025-07-28",
              "description": "Rent Payment",
              "type": "debit",
              "amount": 2000.00,
              "balance_after": 3650.00
            },
            {
              "date": "2025-08-05",
              "description": "Grocery Store",
              "type": "debit",
              "amount": 125.50,
              "balance_after": 3524.50
            },
            {
              "date": "2025-08-10",
              "description": "Utility Bill",
              "type": "debit",
              "amount": 210.30,
              "balance_after": 3314.20
            },
            {
              "date": "2025-08-15",
              "description": "Dining Out",
              "type": "debit",
              "amount": 85.75,
              "balance_after": 3228.45
            },
            {
              "date": "2025-08-20",
              "description": "Online Shopping",
              "type": "debit",
              "amount": 1684.70,
              "balance_after": 1543.75
            }
          ]
        }
    return {"result": result}


# Specify Bedrock LLM for the Agent
bedrock_model = BedrockModel(
    model_id="amazon.nova-lite-v1:0",
)
# System prompt
system_prompt = '''
You are a banking agent. You will receive requests that include:  
- `account_id`  
- `query` (the inquiry type, such as **balance** or **statement**, plus any additional details like month).  

## Instructions
1. Use the provided `account_id` and `query` to call the tools.  
2. The tool will return a JSON response.  
3. Summarize the result in 2–3 sentences.  
   - For a **balance inquiry**, give the account balance with currency and date.  
   - For a **statement inquiry**, provide opening balance, closing balance, and number of transactions.  
4. Do not return raw JSON. Always respond in natural language.  
5. Include the result in a <response></response> tag
'''

agent = Agent(
    tools=[get_account_balance, get_statement], 
    model=bedrock_model,
    system_prompt=system_prompt
)


@app.entrypoint
def banking_agent(payload):
    response = agent(json.dumps(payload))
    output = response.message['content'][0]['text']
    if "<response>" in output and "</response>" in output:
        match = re.search(r"<response>(.*?)</response>", output, re.DOTALL)
        if match:
            output = match.group(1)
    return output
    
if __name__ == "__main__":
    app.run()