package org.example.utility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.Getter;
import lombok.Setter;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.eclipse.jetty.websocket.api.Session;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;
import java.util.Random;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;


@Getter
class ChatTurn {
    private final String role;
    private final String content;

    public ChatTurn(String role, String content) {
        this.role = role;
        this.content = content;
    }

}

public class OutputEventsInteractObserver implements InteractObserver<String> {
    private static final Logger log = LoggerFactory.getLogger(OutputEventsInteractObserver.class);
    private final ObjectMapper objectMapper;
    private final Session session;
    private final List<ChatTurn> localChatHistory;
    private String promptId = "";
    @Setter
    private InteractObserver<String> inputObserver;
    AtomicReference<String> toolUseId = new AtomicReference<>("");
    AtomicReference<String> toolUseContent = new AtomicReference<>("");
    AtomicReference<String> toolName = new AtomicReference<>("");
    AtomicReference<String> role = new AtomicReference<>("");
    AtomicReference<String> generationStage = new AtomicReference<>("");
    private final ToolResultProcessor toolResultProcessor;

    public OutputEventsInteractObserver(Session session) {
        this.session = session;
        this.objectMapper = new ObjectMapper();
        this.localChatHistory = new ArrayList<>();
        this.toolResultProcessor = new ToolResultProcessor();
    }

    @Override
    public void onNext(String msg) {
        try {
            boolean shouldSendMsgToUI = true;
            JsonNode rootNode = objectMapper.readTree(msg);
            JsonNode eventNode = rootNode.get("event");

            if (eventNode != null) {
                if (eventNode.has("completionStart")) {
                    handleCompletionStart(eventNode.get("completionStart"));
                } else if (eventNode.has("contentStart")) {
                    if (eventNode.get("contentStart").get("type") == null) {
                        shouldSendMsgToUI = false;
                    }
                    handleContentStart(eventNode.get("contentStart"));
                } else if (eventNode.has("textOutput")) {
                    if (!generationStage.get().equals("SPECULATIVE")) {
                        localChatHistory.add(new ChatTurn(role.get(), eventNode.get("textOutput").get("content").asText()));
                    }
                    handleTextOutput(eventNode.get("textOutput"));
                } else if (eventNode.has("audioOutput")) {
                    handleAudioOutput(eventNode.get("audioOutput"));
                } else if (eventNode.has("toolUse")) {
                    shouldSendMsgToUI = false;
                    toolUseId.set(eventNode.get("toolUse").get("toolUseId").asText());
                    toolUseContent.set(eventNode.get("toolUse").get("content").asText());
                    toolName.set(eventNode.get("toolUse").get("toolName").asText());
                    log.info("tool use: {}", eventNode);

                } else if (eventNode.has("contentEnd")) {
                    if ("TOOL".equals(eventNode.get("contentEnd").get("type").asText())) {
                        handleToolUse(eventNode);
                        shouldSendMsgToUI = false;
                    }
                    handleContentEnd(eventNode.get("contentEnd"));
                } else if (eventNode.has("completionEnd")) {
                    handleCompletionEnd(eventNode.get("completionEnd"));
                }
                else if (eventNode.has("usageEvent")) {
                    log.info("Parsing usage metrics jsonText={}", eventNode);
                }
            }

            if (shouldSendMsgToUI) {
                sendToUI(msg);
            }

        } catch (Exception e) {
            log.error("Error processing message", e);
            onError(e);
        }
    }

    private void handleCompletionStart(JsonNode node) {
        log.info("Completion started for node: {}", node);
        promptId = node.get("promptName").asText();
        log.info("Completion started with promptId: {}", promptId);
    }

    private void handleContentStart(JsonNode node) {
        log.info("Content started for node: {}", node);
        try {
            if(node.has("additionalModelFields"))
            {
            String additionalModelFieldsStr = node.get("additionalModelFields").asText();
            ObjectMapper mapper = new ObjectMapper();
            JsonNode additionalFields = mapper.readTree(additionalModelFieldsStr);
            // FINAL is the option for USER
            // SPECULATIVE is the option before audio generation for ASSISTANT
            // FINAL is the other option after audio generation for ASSISTANT
            generationStage.set(additionalFields.get("generationStage").asText());
            }
            if(node.has("role")) {// USER, ASSISTANT, or TOOL
                role.set(node.get("role").asText());
            }
        } catch (Exception e) {
        // Handle other errors
        System.err.println("Error processing content event: " + e.getMessage());
        }
        String contentId = node.get("contentId").asText();
        log.info("Content started with contentId: {}", contentId);
    }

    private void handleTextOutput(JsonNode node) {
        log.info("Text output for node: {}", node);
        String content = node.get("content").asText();
        log.info("Received text output: {} from {}", content, role.get());
    }

    private void handleAudioOutput(JsonNode node) {
        log.info("Audio output for node: {}", node);
        String content = node.get("content").asText();
        log.info("Received audio output {} from {}", content, role.get());
    }

    private void handleToolUse(JsonNode node) {
        if (node == null) {
            log.warn("Received null node in handleToolUse");
            return;
        }

        try {
            validateToolUseParameters();
            processToolUseAsync();
        } catch (IllegalStateException e) {
            log.error("Tool use processing failed: {}", e.getMessage());
        }
    }

    private void validateToolUseParameters() {
        if (toolName.get() == null || toolUseId.get() == null || promptId == null) {
            throw new IllegalStateException("Missing required tool use parameters");
        }
    }

    private void processToolUseAsync() {
        log.debug("Processing tool use asynchronously");
        String localChatHistory = createChatHistoryFromLocal();
        logChatHistories(localChatHistory);
        
        // Process the tool use asynchronously
        CompletableFuture<ToolResultProcessor.ToolResultResponse> future = 
            toolResultProcessor.processToolUseAsync(promptId, toolUseId.get(), toolName.get(), toolUseContent.get());
        
        // When the future completes, send the tool result
        future.thenAccept(response -> {
            String contentId = response.getContentId();
            sendStart(contentId, response.getToolUseId());
            sendToolResult(response);
            sendEnd(contentId);
        }).exceptionally(ex -> {
            log.error("Error processing tool result", ex);
            // Send error response to the model
            String errorContentId = UUID.randomUUID().toString();
            sendStart(errorContentId, toolUseId.get());
            sendErrorToolResult(errorContentId, ex);
            sendEnd(errorContentId);
            return null;
        });
    }


    private void sendToolResult(ToolResultProcessor.ToolResultResponse response) {
        if (inputObserver != null) {
            try {
                // Create the "toolResult" object
                ObjectNode toolResultNode = objectMapper.createObjectNode();
                toolResultNode.put("promptName", response.getPromptId());
                toolResultNode.put("contentName", response.getContentId());
                toolResultNode.put("content", response.getContent()); // Content is already properly formatted JSON string

                // Create the final JSON structure
                ObjectNode eventNode = objectMapper.createObjectNode();
                eventNode.set("toolResult", toolResultNode);

                ObjectNode rootNode = objectMapper.createObjectNode();
                rootNode.set("event", eventNode);
                
                String jsonPayload = objectMapper.writeValueAsString(rootNode);
                log.debug("Tool Result - Tool Result payload: {}", jsonPayload);
                inputObserver.onNext(jsonPayload);

            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for toolResult", e);
            }
        }
    }

    private void sendErrorToolResult(String contentId, Throwable ex) {
        if (inputObserver != null) {
            try {
                ObjectNode toolResultNode = objectMapper.createObjectNode();
                toolResultNode.put("promptName", promptId);
                toolResultNode.put("contentName", contentId);
                
                ObjectNode errorContent = objectMapper.createObjectNode();
                errorContent.put("error", "Tool execution failed: " + ex.getMessage());
                
                toolResultNode.put("content", objectMapper.writeValueAsString(errorContent));
                
                // Create the final JSON structure
                ObjectNode eventNode = objectMapper.createObjectNode();
                eventNode.set("toolResult", toolResultNode);

                ObjectNode rootNode = objectMapper.createObjectNode();
                rootNode.set("event", eventNode);
                
                String jsonPayload = objectMapper.writeValueAsString(rootNode);
                log.debug("Sending error tool result: {}", jsonPayload);
                inputObserver.onNext(jsonPayload);
            } catch (Exception e) {
                log.error("Failed to send error tool result", e);
            }
        }
    }


    private void sendStart(String contentId, String toolUseId) {
        if (inputObserver != null) {
            try {
                ObjectNode rootNode = objectMapper.createObjectNode();
                ObjectNode eventNode = rootNode.putObject("event");
                ObjectNode contentStartNode = eventNode.putObject("contentStart");

                contentStartNode.put("promptName", promptId);
                contentStartNode.put("contentName", contentId);
                contentStartNode.put("interactive", false);
                contentStartNode.put("type", "TOOL");
                contentStartNode.put("role", "TOOL");
                ObjectNode toolResultInputConfigNode = contentStartNode.putObject("toolResultInputConfiguration");
                toolResultInputConfigNode.put("toolUseId", toolUseId);
                toolResultInputConfigNode.put("type", "TEXT");

                ObjectNode textInputConfigNode = toolResultInputConfigNode.putObject("textInputConfiguration");
                textInputConfigNode.put("mediaType", "text/plain");

                String contentStart = objectMapper.writeValueAsString(rootNode);
                log.debug("Tool Result - Content Start payload: {}", contentStart);
                inputObserver.onNext(contentStart);
            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for Tool Result contentStart", e);
            }
        }
    }

    private void sendEnd(String contentId) {
        if (inputObserver != null) {
            try {
                ObjectNode rootNode = objectMapper.createObjectNode();
                ObjectNode eventNode = rootNode.putObject("event");
                ObjectNode contentEndNode = eventNode.putObject("contentEnd");

                contentEndNode.put("promptName", promptId);
                contentEndNode.put("contentName", contentId);

                String contentEnd = objectMapper.writeValueAsString(rootNode);
                log.debug("Tool Result - Content End payload: {}", contentEnd);
                inputObserver.onNext(contentEnd);
            } catch (Exception e) {
                throw new RuntimeException("Error creating JSON payload for Tool Result contentEnd", e);
            }
        }
    }

    private void logChatHistories(String localChatHistory) {
        log.debug("Actual chat History: {}", toolUseContent.get());
        log.debug("Local Chat History: {}", localChatHistory);
    }

    private void handleContentEnd(JsonNode node) {
        log.info("Content end for node: {}", node);
        String contentId = node.get("contentId").asText();
        String stopReason = node.has("stopReason") ? node.get("stopReason").asText() : "";
        log.info("Content ended: {} with reason: {}", contentId, stopReason);
    }

    private void handleCompletionEnd(JsonNode node) {
        log.info("Completion end for node: {}", node);
        String stopReason = node.has("stopReason") ? node.get("stopReason").asText() : "";
        log.info("Completion ended with reason: {}", stopReason);
    }

    private void sendToUI(String msg) {
        try {
            if (session.isOpen()) {
                session.getRemote().sendString(msg);
            } else {
                log.debug("Ignoring as session is already closed");
            }
        } catch (Exception e) {
            log.error("Error sending message to UI", e);
        }
    }

    private String createChatHistoryFromLocal() {
        JSONArray messageJsonArray = new JSONArray();
        for (ChatTurn cc : localChatHistory) {
            JSONObject messageObj = new JSONObject();
            messageObj.put("role", cc.getRole());
            messageObj.put("content", cc.getContent());
            messageJsonArray.put(messageObj);
        }
        JSONObject chatHistoryObj = new JSONObject();
        chatHistoryObj.put("chatHistory", messageJsonArray);
        return chatHistoryObj.toString();
    }

    @Override
    public void onComplete() {
        log.info("Output complete");
        try {
            toolResultProcessor.shutdown();
            session.close(1000, "Output complete");
        } catch (Exception e) {
            log.error("Error closing session", e);
        }
    }

    @Override
    public void onError(Exception error) {
        log.error("Error occurred", error);
        try {
            session.close(1011, "Error occurred: " + error.getMessage());
        } catch (Exception e) {
            log.error("Error closing session", e);
        }
    }
}