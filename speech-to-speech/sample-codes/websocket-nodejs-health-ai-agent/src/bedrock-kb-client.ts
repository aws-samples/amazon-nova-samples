import {
    BedrockAgentRuntimeClient,
    RetrieveCommand,
    RetrieveCommandInput,
    RetrieveCommandOutput,
} from "@aws-sdk/client-bedrock-agent-runtime";
import { fromNodeProviderChain } from "@aws-sdk/credential-providers";


// Define interfaces for type safety
interface RetrieveOptions {
    knowledgeBaseId: string;
    query: string;
    numberOfResults?: number;
    retrievalFilter?: Record<string, any>;
}

interface RetrievalResult {
    content: string;
    metadata: {
        source: string;
        location?: string;
        title?: string;
        excerpt?: string;
    };
    score: number;
}

class BedrockKnowledgeBaseClient {
    private client: BedrockAgentRuntimeClient;
    
    constructor(region: string = 'us-east-1') {
        // Use the default credential provider chain
        // This will automatically use (in order):
        // 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        // 2. Shared credentials file (~/.aws/credentials) - respects AWS_PROFILE env var
        // 3. ECS credentials provider
        // 4. EC2 Instance Metadata Service (for IAM roles)
        this.client = new BedrockAgentRuntimeClient({
            region,
            credentials: fromNodeProviderChain()
        });
    }


    // Retrieves information from the Amazon Bedrock Knowledge Bases
    async retrieveFromKnowledgeBase(options: RetrieveOptions): Promise<Object> {
        const { knowledgeBaseId, query, numberOfResults = 5, retrievalFilter } = options;

        try {
            // Build the command input
            const input: RetrieveCommandInput = {
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
            const command = new RetrieveCommand(input);

            // Use type assertion if you need to add filter parameters
            if (retrievalFilter) {
                (command.input as any).filter = retrievalFilter;
            }

            const response: RetrieveCommandOutput = await this.client.send(command);

            // Process and format the results
            if (!response.retrievalResults || response.retrievalResults.length === 0) {
                return [];
            }

            // Safely map the results with correct type handling
            const results: RetrievalResult[] = [];

            for (const result of response.retrievalResults) {
                // Extract content - ensure it's a string
                const content = result.content?.text || "";

                // Extract source with proper null checking
                let source = "Unknown source";
                let location: string | undefined = undefined;

                if (result.location?.s3Location) {
                    source = result.location.s3Location.uri?.split('/').pop() || "Unknown S3 file";
                    location = result.location.s3Location.uri;
                } else if (result.location?.confluenceLocation) {
                    source = result.location.confluenceLocation.url || "Unknown Confluence page";
                    location = result.location.confluenceLocation.url;
                } else if (result.location?.webLocation) {
                    source = "Web source";
                    // Access URL property safely
                    const webLocation: any = result.location.webLocation;
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

                console.log(metadata)

                // Get relevance score
                const score = result.score || 0;

                results.push({
                    content,
                    metadata,
                    score
                });
            }
            return results;
        } catch (error) {
            console.error("Error retrieving from Amazon Bedrock Knowledge Bases:", error);
            throw error;
        }
    }
}

export { BedrockKnowledgeBaseClient, RetrieveOptions, RetrievalResult };
