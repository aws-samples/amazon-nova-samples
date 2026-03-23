# Amazon Nova Act - Agentic Workflows

Amazon Nova Act is an early research preview of a Python SDK and model specifically designed for building agents that can reliably take actions in web browsers. This repository contains practical implementations and use cases demonstrating how Nova Act can be leveraged for real-world agentic workflows.

## What is Nova Act?

Nova Act enables developers to build intelligent agents that can interact with web applications autonomously. Unlike traditional automation that relies on brittle, script-based approaches, Nova Act agents can:

- **Observe and adapt** to UI changes dynamically
- **Make intelligent decisions** based on context and user intent
- **Execute complex workflows** by breaking them into reliable commands
- **Integrate seamlessly** with Python code for testing, assertions, and debugging

The SDK works in conjunction with **Amazon Bedrock AgentCore Browser**, a secure, cloud-based browser environment that provides:

- Session isolation and security
- Built-in observability (live viewing, CloudTrail logging, session replay)
- Containerized ephemeral environments
- Concurrent browser session support for parallel execution

## Learn More

- **Official Repository**: [aws/nova-act](https://github.com/aws/nova-act)
- **Research Blog**: [Amazon Science - Nova Act](https://labs.amazon.science/blog/nova-act)
- **Documentation**: [Amazon Bedrock AgentCore Browser](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-browser.html)

## Use Cases

This repository demonstrates practical implementations of Nova Act for enterprise workflows:

### 🧪 [Agentic QA Testing](./usecases/qa-testing/)

Automate quality assurance testing for web applications using Nova Act and AgentCore Browser. This use case showcases:

- **Intelligent test execution** that adapts to UI changes without brittle selectors
- **Parallel test execution** across multiple browser sessions for faster feedback
- **JSON-driven test definitions** that enable non-technical team members to create tests
- **Real-time observability** with live browser viewing and session replay
- **Integration with pytest** for comprehensive test reporting and CI/CD pipelines

**Key Benefits:**

- Reduce test maintenance overhead by 40-60%
- Execute comprehensive test suites in minutes instead of hours
- Eliminate false negatives from UI changes
- Scale testing across browsers, devices, and environments effortlessly

**What's Included:**

- Sample retail web application for testing
- 15 ready-to-use JSON test cases
- Pytest framework with parallel execution support
- CloudFormation templates for AWS deployment
- Complete setup and deployment instructions

[→ Explore the QA Testing Use Case](./usecases/qa-testing/)

### 💰 [Price Comparison](./usecases/price_comparison/)

Automate product price comparison across multiple retailers using Nova Act. This use case showcases:

- **Intelligent product search** that navigates retail websites and finds matching products
- **Concurrent execution** across multiple retailers for faster price discovery
- **Structured data extraction** using Pydantic schemas for reliable pricing information
- **Captcha handling** with user prompts for manual intervention when needed
- **CSV export** for easy analysis and comparison of results

**Key Benefits:**

- Compare prices across Amazon, Best Buy, Costco, Target, and more in minutes
- Reduce manual price checking effort by automating browser navigation
- Get structured output with product names, prices, and promotion details
- Easily customize product searches and retailer sources via CLI arguments

**What's Included:**

- Ready-to-run price comparison script
- Support for custom product SKUs and retailer sources
- Pydantic-based data validation for extracted pricing
- ThreadPoolExecutor for parallel retailer searches
- Complete setup and usage instructions

[→ Explore the Price Comparison Use Case](./usecases/price_comparison/)

## Why Agentic Workflows?

Traditional automation approaches face significant challenges:

- **High maintenance overhead**: Scripts break with UI changes, requiring constant updates
- **Limited scalability**: Manual testing is time-intensive and incomplete
- **Technical barriers**: Creating automation requires specialized programming knowledge
- **Brittleness**: Automation relies on specific selectors that fail when components change

Agentic AI with Nova Act addresses these challenges by:

- **Adapting dynamically** to interface changes without manual updates
- **Mimicking human interaction** patterns for realistic testing
- **Enabling non-technical users** to create tests through simple JSON definitions
- **Providing comprehensive coverage** without rigid, scripted pathways

## Contributing

We welcome contributions! Please see the main repository's [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## Security

See [CONTRIBUTING](../CONTRIBUTING.md#security-issue-notifications) for more information on reporting security issues.

## License

This project is licensed under the MIT-0 License. See the [LICENSE](../LICENSE) file for details.

## Support

For questions, issues, or feature requests:

- Open an issue in this repository
- Refer to the [official Nova Act documentation](https://github.com/aws/nova-act)
- Contact AWS Support for enterprise assistance

---

**Note**: Nova Act is currently in early research preview. Features and APIs may change as the project evolves.
