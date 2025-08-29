from strands import Agent, tool
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel
import re, argparse

app = BedrockAgentCoreApp()

@tool
def get_mortgage(account_id) -> str:
    """Retrieve current mortgage information and available refinance options and repayment options based on the account ID.x`x``

    Args:
        account_id: Bank account Id
    """

    # In this sample, we use a mock response. 
    # The actual implementation will retrieve information from a database, API or other backend services.
    result = {
        "mortgage_id": "MORT-987654321",
        "current_mortgage": {
            "principal_balance": 245000.00,
            "interest_rate": 4.85,
            "monthly_payment": 1620.45,
            "remaining_term_months": 240
        },
        "refinance_options": [
            {
              "option_id": "REFI-30YR-001",
              "term_months": 360,
              "interest_rate": 3.95,
              "monthly_payment": 1163.21,
              "estimated_closing_costs": 3500.00,
              "apr": 4.02
            },
            {
              "option_id": "REFI-15YR-002",
              "term_months": 180,
              "interest_rate": 3.25,
              "monthly_payment": 1724.56,
              "estimated_closing_costs": 2800.00,
              "apr": 3.40
            }
        ],
        "repayment_options": [
            {
              "option_type": "Standard",
              "description": "Fixed monthly payments until the end of the loan term.",
              "monthly_payment": 1620.45,
              "remaining_term_months": 240,
              "total_interest_paid": 144902.00
            },
            {
              "option_type": "Bi-Weekly",
              "description": "Half of the monthly payment every two weeks, resulting in 26 payments per year.",
              "biweekly_payment": 810.23,
              "remaining_term_months": 216,
              "total_interest_paid": 129876.00
            },
            {
              "option_type": "Accelerated",
              "description": "Pay an additional 10% each month to reduce the principal faster.",
              "monthly_payment": 1782.50,
              "remaining_term_months": 204,
              "total_interest_paid": 121543.00
            },
            {
              "option_type": "Lump-Sum Prepayment",
              "description": "Apply a one-time lump-sum payment of $10,000 to reduce principal.",
              "adjusted_principal_balance": 235000.00,
              "remaining_term_months": 228,
              "total_interest_paid": 133452.00
            }
          ],
      "last_updated": "2025-08-24T15:00:00Z"
    }

    return {"result": result}

@tool
def get_instruction(account_id: str) -> str:
    """About general mortage process
    Args:
        account_id: Bank account Id
    """
    # In this sample, we use a mock response. 
    # The actual implementation will retrieve information from a database API or another backend service.
    result = '''
        ## Requirements
        - Full Name, Date of Birth, Account ID  
        - Employment Status, Annual Income  
        - Desired Mortgage Amount, Property Address
        
        ## Process
        1. Collect applicant info.  
        2. Evaluate mock credit score (simulate 650–800).  
        3. Select mortgage type: Fixed, ARM, or Refinance.  
        4. Calculate mock monthly payment and repayment options (Standard, Bi-Weekly, Accelerated).  
        5. Submit application and return JSON with:
           - Application ID  
           - Eligibility Status  
           - Recommended Product  
           - Monthly Payment  
           - Repayment Options
    '''
    return {"result": result}

# Specify Bedrock LLM for the Agent
bedrock_model = BedrockModel(
    model_id="amazon.nova-lite-v1:0",
)
# System prompt
system_prompt = '''
You are a mortgage agent. You will receive requests that include:  
- `account_id`  
- `query` (the inquiry type, such as **current mortgage** or **refinance option**, **repayment options** plus any additional details).  

## Instructions
1. Use the provided `account_id` and `query` to call the tools.  
2. The tool will return a JSON response.  
3. Summarize the result in 2–3 sentences.  
 - For refinance: give the refianace options and current mortageg balance
 - For repayment options: give the options summary including term duration, rate and monthly payments.
4. Do not return raw JSON. Always respond in natural language.  
5. Include the result in a <response></response> tag
'''

agent = Agent(
    tools=[get_mortgage, get_instruction], 
    model=bedrock_model,
    system_prompt=system_prompt
)

@app.entrypoint
def mortgage_agent(payload):
    #input = json.loads(payload)
    response = agent(json.dumps(payload))
    output = response.message['content'][0]['text']
    if "<response>" in output and "</response>" in output:
        match = re.search(r"<response>(.*?)</response>", output, re.DOTALL)
        if match:
            output = match.group(1)
    return output
    
if __name__ == "__main__":
    app.run()