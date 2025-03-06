package org.example.utility;

import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithResponseStreamResponseHandler.Visitor;
import software.amazon.awssdk.services.bedrockruntime.model.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;
import java.util.regex.Pattern;

public class NovaReasoningModel {
    private static final Logger log = LoggerFactory.getLogger(NovaReasoningModel.class);

    public static final String LITE_MODEL_ID = "amazon.nova-lite-v1:0";
    public static final String PRO_MODEL_ID = "amazon.nova-pro-v1:0";
    public static final String MICRO_MODEL_ID = "amazon.nova-micro-v1:0";
    private static final Pattern REMOVE_END_OF_LINE_SPACE = Pattern.compile(" $");

    public static final String DEFAULT_SYSTEM_PROMPT =
            "You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time " +
                    "conversation. The turn taking events are a context from a previous conversation where they start from the user, and " +
                    "continue in an interleaved fashion user, agent, user, agent, user, agent, and so on. The responses from the agent are " +
                    "your responses. You are expected to provide only the next transcript response of what you should say next. You must " +
                    "be human-like and highly emotional, playful, smart, witty, empathetic, engaging and helpful. Be spontaneous and brief " +
                    "in your responses. Use simple vocabulary and short sentences. Use at most two or three sentences per response " +
                    "typically. You may start each of your sentences with emotions in square brackets such as [amused], [neutral], " +
                    "[joyful], [sarcastic] or any other stage command such as [eye roll]. Only use a single pair of square brackets for " +
                    "indicating a stage command. You also should output your turn in spoken format, namely expanding formatted dates and " +
                    "numbers to their spoken representations (for example, 3:45 to three forty-five). Do not output emojis in any form. " +
                    "Do not output any type of markup text. Keep in mind that, aside from stage commands, the output will be sent to a " +
                    "text-to-speech system. Do not output any emojis.";

    private final BedrockRuntimeAsyncClient bedrockClient;
    private final String modelId;
    private final String systemPrompt;
    private final Map<String, Object> inferenceConfiguration;
    private final boolean isStreamingResponse;
    private volatile InteractObserver<String> inputObserver;

    public NovaReasoningModel(BedrockRuntimeAsyncClient bedrockClient,
                                String modelId,
                                boolean isStreamingResponse) {
        this(bedrockClient, modelId, DEFAULT_SYSTEM_PROMPT, isStreamingResponse, null);
    }

    public NovaReasoningModel(BedrockRuntimeAsyncClient bedrockClient,
                                String modelId,
                                String systemPrompt,
                                boolean isStreamingResponse,
                                Map<String, Object> inferenceConfiguration) {
        this.bedrockClient = bedrockClient;
        this.modelId = modelId;
        this.systemPrompt = systemPrompt;
        this.isStreamingResponse = isStreamingResponse;
        this.inferenceConfiguration = inferenceConfiguration != null ?
                inferenceConfiguration : getDefaultInferenceConfiguration();
    }

    private Map<String, Object> getDefaultInferenceConfiguration() {
        Map<String, Object> config = new HashMap<>();
        config.put("temperature", 0.7);
        config.put("topP", 0.95);
        config.put("maxTokens", 1024);
        return config;
    }

    public void setInputObserver(InteractObserver<String> observer) {
        this.inputObserver = observer;
    }

    public CompletableFuture<Void> processRequest(Map<String, String> context, String payload) {
        log.info("Processing request with context={} and payload={}", context, payload);

        InvokeModelWithResponseStreamRequest.Builder reqBuilder = InvokeModelWithResponseStreamRequest.builder()
                .modelId(modelId)
                .accept("application/json")
                .contentType("application/json");

        JSONArray messagesJSONArray = chatHistoryToNovaHistory(payload);
        JSONObject bodyJson = new JSONObject();
        JSONObject inferenceConfig = new JSONObject();

        inferenceConfig.put("max_new_tokens", inferenceConfiguration.get("maxTokens"));
        inferenceConfig.put("top_p", inferenceConfiguration.get("topP"));
        inferenceConfig.put("temperature", inferenceConfiguration.get("temperature"));

        bodyJson.put("inferenceConfig", inferenceConfig);
        bodyJson.put("system", new JSONArray().put(new JSONObject().put("text", systemPrompt)));
        bodyJson.put("messages", messagesJSONArray);

        reqBuilder.body(SdkBytes.fromUtf8String(bodyJson.toString()));
        InvokeModelWithResponseStreamRequest request = reqBuilder.build();

        Consumer<PayloadPart> onChunkConsumer = chunk -> {
            String chunkStr = chunk.bytes().asUtf8String();
            JSONObject response = new JSONObject(chunkStr);

            try {
                if (response.has("messageStart")) {
                    sendStart(context);
                } else if (response.has("contentBlockDelta")) {
                    JSONObject delta = response.getJSONObject("contentBlockDelta")
                            .getJSONObject("delta");
                    if (delta.has("text")) {
                        sendData(context, delta.getString("text"));
                    }
                } else if (response.has("messageStop")) {
                    sendEnd(context);
                }
            } catch (Exception e) {
                log.error("Error processing chunk", e);
                onError(context, e);
            }
        };

        InvokeModelWithResponseStreamResponseHandler responseStreamHandler =
                InvokeModelWithResponseStreamResponseHandler.builder()
                        .subscriber(Visitor.builder()
                                .onChunk(onChunkConsumer)
                                .build())
                        .onComplete(() -> log.info("Request completed"))
                        .onError(t -> onError(context, t))
                        .build();

        return bedrockClient.invokeModelWithResponseStream(request, responseStreamHandler);
    }

    private void sendStart(Map<String, String> context) {
        if (inputObserver != null) {
            String contentStart = String.format("""
                        {
                            "event": {
                                "contentStart": {
                                    "promptName": "%s",
                                    "contentName": "%s",
                                    "interactive": false,
                                    "type": "TOOL",
                                    "toolResultInputConfiguration": {
                                        "toolUseId": "%s",
                                        "type": "TEXT",
                                        "textInputConfiguration": {
                                            "mediaType": "text/plain"
                                        }
                                    }
                                }
                            }
                        }""", context.get("promptId"), context.get("contentId"), context.get("toolInvocationId"));

            inputObserver.onNext(contentStart);
        }
    }

    private void sendData(Map<String, String> context, String content) {
        if (inputObserver != null) {
            String toolResultJson = String.format("""
                    {
                        "event": {
                            "toolResult": {
                                "promptName": "%s",
                                "contentName": "%s",
                                "role": "TOOL",
                                "content": "%s"
                            }
                        }
                    }""", context.get("promptId"), context.get("contentId"), content);
            inputObserver.onNext(toolResultJson);
        }
    }

    private void sendEnd(Map<String, String> context) {
        if (inputObserver != null) {
            String contentEndJson = String.format("""
                    {
                        "event": {
                            "contentEnd": {
                                "promptName": "%s",
                                "contentName": "%s"
                            }
                        }
                    }""", context.get("promptId"), context.get("contentId"));

            inputObserver.onNext(contentEndJson);
        }
    }

    private void onError(Map<String, String> context, Throwable t) {
        log.error("Error occurred during processing", t);
        if (inputObserver != null) {
            inputObserver.onError(new Exception("Processing error: " + t.getMessage(), t));
        }
    }

    private static JSONArray chatHistoryToNovaHistory(String payloadStr) {
        JSONObject payload = new JSONObject(payloadStr);
        JSONArray chatHistory = payload.optJSONArray("chatHistory");
        if (chatHistory == null) {
            return new JSONArray();
        }

        JSONArray messagesJSONArray = new JSONArray();
        String activeRole = null;
        StringBuilder activeContentBuilder = new StringBuilder();

        for (int i = 0; i < chatHistory.length(); i++) {
            JSONObject entry = chatHistory.getJSONObject(i);
            String currentRole = entry.getString("role").toLowerCase();
            String currentContent = entry.getString("content");

            if (!currentRole.equals(activeRole)) {
                if (activeRole != null) {
                    messagesJSONArray.put(addContent(new JSONObject(),
                            activeRole, activeContentBuilder.toString()));
                }
                activeRole = currentRole;
                activeContentBuilder = new StringBuilder();
            }
            activeContentBuilder.append(currentContent).append(" ");
        }

        if (activeRole != null) {
            messagesJSONArray.put(addContent(new JSONObject(),
                    activeRole, activeContentBuilder.toString()));
        }

        return messagesJSONArray;
    }

    private static JSONObject addContent(JSONObject jobj, String role, String content) {
        JSONArray contentArray = new JSONArray();
        contentArray.put(new JSONObject().put("text",
                REMOVE_END_OF_LINE_SPACE.matcher(content).replaceAll("")));

        jobj.put("role", role)
                .put("content", contentArray);

        return jobj;
    }

    public static Map<String, String> createContext(String promptName, String toolUseId) {
        Map<String, String> context = new HashMap<>();
        context.put("promptId", promptName);
        context.put("contentId", UUID.randomUUID().toString());
        context.put("toolInvocationId", toolUseId);
        return context;
    }
}
