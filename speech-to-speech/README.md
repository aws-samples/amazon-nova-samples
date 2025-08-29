# Amazon Nova Sonic Speech-to-Speech Model Samples 

The Amazon Nova Sonic model provides real-time, conversational interactions through bidirectional audio streaming. Amazon Nova Sonic processes and responds to real-time speech as it occurs, enabling natural, human-like conversational experiences.

The Amazon Nova Sonic model uses the `InvokeModelWithBidirectionalStream` API, which enables real-time bidirectional streaming conversations. This differs from traditional request-response patterns by maintaining an open channel for continuous audio streaming in both directions.

This repository provides sample applications, organized into subfolders:
- The `sample-codes` folder contains basic examples in Java, Node.js, and Python. If you're looking for a quick start to understand how to interact with Nova Sonic in your preferred programming language, this is the place to begin.
- The `repeatable-patterns` folder includes common integration patterns, such as Retrieval-Augmented Generation (RAG) using Amazon Bedrock Knowledge Bases or Langchain, chat history logging, and business-oriented sample apps like customer service and resume conversation scenarios.
- The `workshops` folder contains sample code for both AWS-led and self-service workshops. It includes a Python WebSocket server and a React web application designed to expose technical details for training purposes.

To learn more about Amazon Nova Sonic, refer to the [User Guide](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)


## Browser Compatibility Warning
> **Warning:** The WebSocket-based sample applications with UIs in this repository are optimized for Google Chrome and may not function properly in other browsers. These applications require the ability to set the audio sample rate to 16kHz for proper microphone streaming over WebSockets, which Firefox and some other browsers do not support natively.

## Reference Solutions
The following projects were developed by AWS teams and showcase examples of how to build solutions using Amazon Nova Sonic and AWS services, serve as helpful inspiration or starting points for your own implementations.

- [Intelligent conversational IVR for hotel reservation system using Amazon Nova Sonic](https://github.com/aws-samples/genai-quickstart-pocs/tree/main/genai-quickstart-pocs-python/amazon-bedrock-nova-sonic-poc)

    This Python app showcases real-time audio streaming with Amazon Nova Sonic model in a hotel reservation scenario. It enables natural conversations and uses function calling to create, modify, or cancel reservations via API.

- [Nova Sonic CDK Package: Call Center Agent Tools](https://github.com/aws-samples/sample-s2s-cdk-agent)

    A CDK-deployable Nova Sonic S2S application designed as a flexible foundation for building PoCs. The CDK package deploys the WebSocket service to Amazon ECS Fargate and hosts the frontend web application on Amazon S3 and CloudFront as a static site with Amazon Cognito authentication.

- [Nova Sonic Sample Integration with Telephony Platforms: Vonage and Twilio](https://github.com/aws-samples/sample-sonic-contact-center-with-telephony)

    This solution delivers a comprehensive analytics dashboard for monitoring and optimizing Amazon Bedrock's Nova speech-to-speech interactions in customer support. It features real-time sentiment analysis, agent guidance, and key metrics like talk time ratios and response times—powered by Nova Lite. The backend integrates a knowledge base for more accurate responses, and an adapter layer enables integration with telephony platforms like Vonage and Twilio.

- [Nova Sonic CDK Package: Supports Java and Python WebSocket with Load Testing Capability](https://github.com/aws-samples/generative-ai-cdk-constructs-samples/tree/main/samples/speech-to-speech)

    The CDK-deployable Nova Sonic package includes a generic WebSocket server and UI, serving as both a PoC starting point and a reference architecture for production deployments. It offers two server implementations—one using the Java SDK and the other using the Python SDK—allowing users to choose their preferred programming language. The package also includes a load testing tool to evaluate concurrency limits, helping with production capacity planning and cost estimation.

- [Nova Sonic VoIP Gateway](https://github.com/aws-samples/sample-s2s-voip-gateway/tree/main)

    This project implements a SIP endpoint that acts as a gateway between traditional phone systems and Nova Sonic speech-to-speech. It allows users to call a phone number and have a conversation with Nova Sonic over VoIP. The solution includes deployment options for ECS with CDK or a single EC2 instance, making it versatile for different use cases. It bridges RTP audio streams with Nova Sonic, enabling voice AI capabilities through standard telephony infrastructure.

- [Serverless Nova Sonic Chat](https://github.com/aws-samples/sample-serverless-nova-sonic-chat)

    This serverless implementation provides a lightweight, easily deployable, and scalable Nova Sonic infrastructure using AWS Lambda and AppSync Events, offering a streamlined approach to real-time speech-to-speech communication. It features serverless real-time communication between server and client using AppSync Events, reference to past conversation history, tool use implementation, automatic resume for conversations exceeding 8 minutes, and an extensible web UI built with Next.js.

  
- [Sonic Playground for Experimenting](https://github.com/aws-samples/sample-sonic-java-playground)

    This solution serves as an experimental playground for developers to test and optimize Nova Sonic capabilities by configuring various model parameters and finding the optimal settings for their specific use cases. The application supports creating new conversation sessions with voice IDs for language selection, TopP, Temperature, MaxTokens for response length control, and system prompts. Built with Java Spring Boot and React, it provides a reference implementation for speech-to-speech applications.
