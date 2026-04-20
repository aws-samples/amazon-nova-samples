"""
BEFORE: LangChain text-based banking agent.

This is the original text agent that we want to migrate to voice.
It uses LangChain's create_react_agent with Bedrock Nova, inline tools,
and a text-oriented system prompt.
"""

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


SYSTEM_PROMPT = (
    "You are a customer service assistant for AnyBank. "
    "Help users with account balance inquiries, recent transactions, "
    "and fund transfers. Always authenticate the user first. "
    "Respond with structured data when available. "
    "Format currency as USD with two decimal places. "
    "If an error occurs, return the error code and description."
)


@tool
def get_account_balance(account_id: str) -> str:
    """Get the balance for a customer account."""
    return '{"status":"success","account_id":"' + account_id + '","balance":4231.56,"currency":"USD"}'


@tool
def get_recent_transactions(account_id: str, count: int = 5) -> str:
    """Get recent transactions for a customer account."""
    return (
        '{"transactions":['
        '{"desc":"Coffee Shop","amount":-4.50},'
        '{"desc":"Grocery Store","amount":-62.30},'
        '{"desc":"Direct Deposit","amount":3200.00}]}'
    )


@tool
def transfer_funds(from_account: str, to_account: str, amount: float) -> str:
    """Transfer funds between two accounts."""
    return f'{{"status":"success","from":"{from_account}","to":"{to_account}","amount":{amount}}}'


def build_text_agent(region: str = "us-east-1"):
    llm = ChatBedrockConverse(
        model_id="us.amazon.nova-2-lite-v1:0",
        region_name=region,
    )
    agent = create_react_agent(
        model=llm,
        tools=[get_account_balance, get_recent_transactions, transfer_funds],
        prompt=SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )
    return agent
