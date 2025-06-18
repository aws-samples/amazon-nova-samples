# Multi-Agent Orchestration with Strands 

## Overview

This example will guide you through building a system of coordinated AI agents using Strands. We'll break this down into two main parts:

1- Creating and testing individual agents: We'll start by developing standalone agents and verifying their functionality.

2- Implementing Agent Graphs: We'll then explore how to connect these agents together using Strands' Agent Graph functionality, demonstrating a practical use case of agent coordination.

This step-by-step approach will help you understand both the individual components and how they work together in a coordinated system.

## Agents:

* **get_stock_prices_agent**: Specialized agent to get the latest stock prices. Fetches current and historical stock price data for a given ticker using yahoo finance lib.
* **fin_web_searcher_agent**: Financial researcher agent, focus on search and curated financial information. It uses Tivily API to search relevant data on the web.
* **image_generator_agent**: Agent that can generate images using Nova and save them to files.
* **Report Writing**: Report writer agent using Nova to create reports from the gather information.

Note: you need Tavily API Key for fin_web_searcher_agent

