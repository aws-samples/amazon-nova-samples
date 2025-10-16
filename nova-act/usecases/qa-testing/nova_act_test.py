from nova_act import NovaAct
import os

# Browser args enables browser debugging on port 9222.
#os.environ["NOVA_ACT_BROWSER_ARGS"] = "--remote-debugging-port=9222"
# Get your API key from https://nova.amazon.com/act
# Set API Key using Set API Key command (CMD/Ctrl+Shift+P) or set it below.
# os.environ["NOVA_ACT_API_KEY"] = "<YOUR_API_KEY>"
BOOL_SCHEMA = {"type": "boolean"}
STRING_SCHEMA = {"type": "string"}

class NovaActQA:
    def __init__(self, nova_instance):
        self.nova = nova_instance

    def AssertTrue(self, prompt):
        result = self.nova.act(prompt, schema=BOOL_SCHEMA)
        actual = result.parsed_response if result.matches_schema else False
        print(f"[{'PASS' if actual else 'FAIL'}] {prompt[:40]}...: {actual}")
        return actual

    def AssertStringMatch(self, prompt, expected_string):
        result = self.nova.act(prompt, schema=STRING_SCHEMA)
        actual = result.parsed_response if result.matches_schema else ""
        match = actual.lower() == expected_string.lower()
        print(f"[{'PASS' if match else 'FAIL'}] Expected '{expected_string}', Got '{actual}'")
        return match


# Initialize Nova Act with your starting page.
nova = NovaAct(
    starting_page="https://d2f7zionz83pjp.cloudfront.net",
    headless=False,
    nova_act_api_key = "..."
)

# Running nova.start will launch a new browser instance.
# Only one nova.start() call is needed per Nova Act session.
nova.start()

qa = NovaActQA(nova)
search_works = qa.AssertTrue("type laptop in search bar and search. Return true if the page shows results for laptop")
title_match = qa.AssertStringMatch("what is the text on the left top corner in dark blue color ", "QA Test App")

