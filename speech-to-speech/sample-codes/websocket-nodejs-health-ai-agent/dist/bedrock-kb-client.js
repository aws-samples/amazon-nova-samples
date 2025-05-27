"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BedrockKnowledgeBaseClient = void 0;
const client_bedrock_agent_runtime_1 = require("@aws-sdk/client-bedrock-agent-runtime");
const credential_providers_1 = require("@aws-sdk/credential-providers");
const AWS_PROFILE_NAME = process.env.AWS_PROFILE || 'bedrock-test';
class BedrockKnowledgeBaseClient {
    constructor(region = 'us-east-1') {
        this.client = new client_bedrock_agent_runtime_1.BedrockAgentRuntimeClient({
            region,
            credentials: (0, credential_providers_1.fromIni)({ profile: AWS_PROFILE_NAME })
        });
    }
    // Retrieves information from the Bedrock Knowledge Base
    async retrieveFromKnowledgeBase(options) {
        const { knowledgeBaseId, query, numberOfResults = 5, retrievalFilter } = options;
        try {
            // Build the command input
            const input = {
                knowledgeBaseId,
                retrievalQuery: {
                    text: query
                },
                retrievalConfiguration: {
                    vectorSearchConfiguration: {
                        numberOfResults
                    }
                }
            };
            // Execute the retrieval command
            const command = new client_bedrock_agent_runtime_1.RetrieveCommand(input);
            // Use type assertion if you need to add filter parameters
            if (retrievalFilter) {
                command.input.filter = retrievalFilter;
            }
            const response = await this.client.send(command);
            // Process and format the results
            if (!response.retrievalResults || response.retrievalResults.length === 0) {
                return [];
            }
            // Safely map the results with correct type handling
            const results = [];
            for (const result of response.retrievalResults) {
                // Extract content - ensure it's a string
                const content = result.content?.text || "";
                // Extract source with proper null checking
                let source = "Unknown source";
                let location = undefined;
                if (result.location?.s3Location) {
                    source = result.location.s3Location.uri?.split('/').pop() || "Unknown S3 file";
                    location = result.location.s3Location.uri;
                }
                else if (result.location?.confluenceLocation) {
                    source = result.location.confluenceLocation.url || "Unknown Confluence page";
                    location = result.location.confluenceLocation.url;
                }
                else if (result.location?.webLocation) {
                    source = "Web source";
                    // Access URL property safely
                    const webLocation = result.location.webLocation;
                    if (webLocation && (webLocation.url || webLocation.uri)) {
                        location = webLocation.url || webLocation.uri;
                    }
                }
                // Safely extract metadata
                const title = result.metadata?.title;
                const excerpt = result.metadata?.excerpt;
                const metadata = {
                    source,
                    location,
                    title: typeof title === 'string' ? title : "",
                    excerpt: typeof excerpt === 'string' ? excerpt : ""
                };
                console.log(metadata);
                // Get relevance score
                const score = result.score || 0;
                results.push({
                    content,
                    metadata,
                    score
                });
            }
            return results;
        }
        catch (error) {
            console.error("Error retrieving from Bedrock Knowledge Base:", error);
            throw error;
        }
    }
}
exports.BedrockKnowledgeBaseClient = BedrockKnowledgeBaseClient;
