# Amazon Nova Sonic Speech-to-Speech Model Samples 

The Amazon Nova Sonic model provides real-time, conversational interactions through bidirectional audio streaming. Amazon Nova Sonic processes and responds to real-time speech as it occurs, enabling natural, human-like conversational experiences.

The Amazon Nova Sonic model uses the `InvokeModelWithBidirectionalStream` API, which enables real-time bidirectional streaming conversations. This differs from traditional request-response patterns by maintaining an open channel for continuous audio streaming in both directions.

This repository provides sample applications, organized into subfolders:
- The `sample-codes` folder contains basic examples in Java, Node.js, and Python. If you're looking for a quick start to understand how to interact with Nova Sonic in your preferred programming language, this is the place to begin.
- The `repeatable-patterns` folder includes common integration patterns, such as Retrieval-Augmented Generation (RAG) using Amazon Bedrock Knowledge Bases or Langchain, chat history logging, and business-oriented sample apps like customer service and resume conversation scenarios.

To learn more about Amazon Nova Sonic, refer to the [User Guide](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)