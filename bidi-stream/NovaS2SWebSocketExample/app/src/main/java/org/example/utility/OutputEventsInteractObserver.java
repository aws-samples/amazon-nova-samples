package org.example.utility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.eclipse.jetty.websocket.api.Session;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;


class ChatTurn {
    private final String role;
    private final String content;

    public ChatTurn(String role, String content) {
        this.role = role;
        this.content = content;
    }

    public String getRole() {
        return role;
    }

    public String getContent() {
        return content;
    }
}

public class OutputEventsInteractObserver implements InteractObserver<String> {
    private static final Logger log = LoggerFactory.getLogger(OutputEventsInteractObserver.class);
    private final ObjectMapper objectMapper;
    private final Session session;
    private final List<ChatTurn> localChatHistory;
    private String promptId = "";
    private NovaReasoningModel novaReasoningModel;
    AtomicReference<String> toolUseId = new AtomicReference<>("");
    AtomicReference<String> toolUseContent = new AtomicReference<>("");

    public OutputEventsInteractObserver(Session session, NovaReasoningModel novaReasoningModel) {
        this.session = session;
        this.objectMapper = new ObjectMapper();
        this.localChatHistory = new ArrayList<>();
        this.novaReasoningModel = novaReasoningModel;
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
                    if (!eventNode.get("textOutput").get("content").asText().startsWith("Speculative")) {
                        localChatHistory.add(new ChatTurn(eventNode.get("textOutput").get("role").asText(), eventNode.get("textOutput").get("content").asText()));
                    }
                    handleTextOutput(eventNode.get("textOutput"));
                } else if (eventNode.has("audioOutput")) {
                    handleAudioOutput(eventNode.get("audioOutput"));
                } else if (eventNode.has("toolUse")) {
                    shouldSendMsgToUI = false;
                    toolUseId.set(eventNode.get("toolUse").get("toolUseId").asText());
                    toolUseContent.set(eventNode.get("toolUse").get("content").asText());

                } else if (eventNode.has("contentEnd")) {
                    if ("TOOL".equals(eventNode.get("contentEnd").get("type").asText())) {
                        handleToolUse(eventNode);
                        shouldSendMsgToUI = false;
                    }
                    handleContentEnd(eventNode.get("contentEnd"));
                } else if (eventNode.has("completionEnd")) {
                    handleCompletionEnd(eventNode.get("completionEnd"));
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
        String contentId = node.get("contentId").asText();
        log.info("Content started with contentId: {}", contentId);
    }

    private void handleTextOutput(JsonNode node) {
        log.info("Text output for node: {}", node);
        String content = node.get("content").asText();
        String role = node.get("role").asText();
        log.info("Received text output: {} from {}", content, role);
    }

    private void handleAudioOutput(JsonNode node) {
        log.info("Audio output for node: {}", node);
        String content = node.get("content").asText();
        String role = node.get("role").asText();
        log.info("Received audio output {} from {}", content, role);
    }

    private void handleToolUse(JsonNode node) {
        log.info("ToolUse for node: {}", node);
        String localChatHistory = createChatHistoryFromLocal();
        log.info("Actual chat History: {}", toolUseContent.get());
        log.info("Local Chat History: {}", localChatHistory);

        novaReasoningModel.processRequest(NovaReasoningModel.createContext(promptId, toolUseId.get()), toolUseContent.get());
        log.info("Tool use: {} with content: {}", toolUseId.get(), toolUseContent.get());
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