using System.Net.WebSockets;
using System.Text;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace NovaSonicWebSocket.Utility;

public class ChatTurn
{
    public string Role { get; }
    public string Content { get; }

    public ChatTurn(string role, string content)
    {
        Role = role;
        Content = content;
    }
}

public class OutputEventsInteractObserver : IInteractObserver<string>
{
    private readonly WebSocket _webSocket;
    private readonly ILogger _logger;
    private readonly List<ChatTurn> _localChatHistory = new();
    private readonly AtomicReference<string> _promptId;
    private readonly AtomicReference<string> _toolUseId = new(string.Empty);
    private readonly AtomicReference<string> _toolUseContent = new(string.Empty);
    private readonly AtomicReference<string> _toolName = new(string.Empty);
    private readonly AtomicReference<string> _role = new(string.Empty);
    private readonly AtomicReference<string> _generationStage = new(string.Empty);
    private readonly ToolResultProcessor _toolResultProcessor;
    private IInteractObserver<string>? _inputObserver;

    public OutputEventsInteractObserver(WebSocket webSocket, ILogger logger, AtomicReference<string> promptId)
    {
        _webSocket = webSocket;
        _logger = logger;
        _promptId = promptId;
        _toolResultProcessor = new ToolResultProcessor(logger);
    }

    public void SetInputObserver(IInteractObserver<string>? inputObserver)
    {
        _inputObserver = inputObserver;
    }

    public void OnNext(string msg)
    {
        try
        {
            var shouldSendMsgToUI = true;
            var jsonObject = JObject.Parse(msg);
            var eventNode = jsonObject["event"];

            if (eventNode != null)
            {
                if (eventNode["completionStart"] != null)
                {
                    HandleCompletionStart(eventNode["completionStart"]);
                }
                else if (eventNode["contentStart"] != null)
                {
                    if (eventNode["contentStart"]?["type"] == null)
                    {
                        shouldSendMsgToUI = false;
                    }
                    HandleContentStart(eventNode["contentStart"]);
                }
                else if (eventNode["textOutput"] != null)
                {
                    if (_generationStage.Value != "SPECULATIVE")
                    {
                        var content = eventNode["textOutput"]?["content"]?.ToString() ?? string.Empty;
                        _localChatHistory.Add(new ChatTurn(_role.Value, content));
                    }
                    HandleTextOutput(eventNode["textOutput"]);
                }
                else if (eventNode["audioOutput"] != null)
                {
                    HandleAudioOutput(eventNode["audioOutput"]);
                }
                else if (eventNode["toolUse"] != null)
                {
                    shouldSendMsgToUI = false;
                    _toolUseId.Value = eventNode["toolUse"]?["toolUseId"]?.ToString() ?? string.Empty;
                    _toolUseContent.Value = eventNode["toolUse"]?["content"]?.ToString() ?? string.Empty;
                    _toolName.Value = eventNode["toolUse"]?["toolName"]?.ToString() ?? string.Empty;
                    _logger.LogInformation("tool use: {ToolUse}", eventNode["toolUse"]);
                }
                else if (eventNode["contentEnd"] != null)
                {
                    if (eventNode["contentEnd"]?["type"]?.ToString() == "TOOL")
                    {
                        HandleToolUse(eventNode);
                        shouldSendMsgToUI = false;
                    }
                    HandleContentEnd(eventNode["contentEnd"]);
                }
                else if (eventNode["completionEnd"] != null)
                {
                    HandleCompletionEnd(eventNode["completionEnd"]);
                }
                else if (eventNode["sessionEnd"] != null)
                {
                    HandleSessionEnd();
                }
                else if (eventNode["usageEvent"] != null)
                {
                    _logger.LogDebug("Parsing usage metrics jsonText={UsageEvent}", eventNode);
                }
            }

            if (shouldSendMsgToUI)
            {
                // Fire and forget - don't block the observer thread
                _ = SendMessageAsync(msg);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing message");
            OnError(ex);
        }
    }

    public void OnComplete()
    {
        _logger.LogInformation("Stream completed");
        _inputObserver?.OnComplete();
    }

    public void OnError(Exception error)
    {
        _logger.LogError(error, "Error in output observer");

        try
        {
            var errorMessage = new
            {
                error = new
                {
                    message = error.Message,
                    type = error.GetType().Name
                }
            };
            _logger.LogError("Sending error message to client: {ErrorMessage}", JsonConvert.SerializeObject(errorMessage));
            // Fire and forget - don't block on error handling
            _ = SendMessageAsync(JsonConvert.SerializeObject(errorMessage));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending error message to client");
        }
    }

    private void HandleCompletionStart(JToken? node)
    {
        if (node != null)
        {
            _promptId.Value = node["promptName"]?.ToString() ?? string.Empty;
            _logger.LogInformation("Completion started with promptId: {PromptId}", _promptId.Value);
            _logger.LogInformation("Nova Sonic session: {SessionId}", node["sessionId"]?.ToString() ?? string.Empty);
        }
    }

    private void HandleContentStart(JToken? node)
    {
        if (node != null)
        {
            _logger.LogInformation("Content started for node: {Node}", node);
            try
            {
                if (node["additionalModelFields"] != null)
                {
                    var additionalModelFieldsStr = node["additionalModelFields"]?.ToString() ?? string.Empty;
                    var additionalFields = JObject.Parse(additionalModelFieldsStr);
                    // FINAL is the option for USER
                    // SPECULATIVE is the option before audio generation for ASSISTANT
                    // FINAL is the other option after audio generation for ASSISTANT
                    _generationStage.Value = additionalFields["generationStage"]?.ToString() ?? string.Empty;
                }
                if (node["role"] != null)
                {
                    // USER, ASSISTANT, or TOOL
                    _role.Value = node["role"]?.ToString() ?? string.Empty;
                }
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error processing content event");
            }

            var contentId = node["contentId"]?.ToString() ?? string.Empty;
            _logger.LogInformation("Content started with contentId: {ContentId}", contentId);
        }
    }

    private void HandleTextOutput(JToken? node)
    {
        if (node != null)
        {
            var content = node["content"]?.ToString() ?? string.Empty;
            _logger.LogInformation("Received text output: {Content} from {Role}", content, _role.Value);
        }
    }

    private void HandleAudioOutput(JToken? node)
    {
        if (node != null)
        {
            var content = node["content"]?.ToString() ?? string.Empty;
            _logger.LogDebug("Received audio output {Content} from {Role}", content, _role.Value);
        }
    }

    private void HandleToolUse(JToken? node)
    {
        if (node == null)
        {
            _logger.LogWarning("Received null node in handleToolUse");
            return;
        }

        try
        {
            ValidateToolUseParameters();
            ProcessToolUseAsync();
        }
        catch (InvalidOperationException e)
        {
            _logger.LogError(e, "Tool use processing failed: {Message}", e.Message);
        }
    }

    private void ValidateToolUseParameters()
    {
        if (string.IsNullOrEmpty(_toolName.Value) || 
            string.IsNullOrEmpty(_toolUseId.Value) || 
            string.IsNullOrEmpty(_promptId.Value))
        {
            throw new InvalidOperationException("Missing required tool use parameters");
        }
    }

    private void ProcessToolUseAsync()
    {
        _logger.LogDebug("Processing tool use asynchronously");
        var localChatHistory = CreateChatHistoryFromLocal();
        LogChatHistories(localChatHistory);

        // Process the tool use asynchronously
        var task = _toolResultProcessor.ProcessToolUseAsync(
            _promptId.Value, 
            _toolUseId.Value, 
            _toolName.Value, 
            _toolUseContent.Value);

        task.ContinueWith(t =>
        {
            if (t.IsCompletedSuccessfully && t.Result != null)
            {
                var response = t.Result;
                SendStart(response.ContentId, response.ToolUseId);
                SendToolResult(response);
                SendEnd(response.ContentId);
            }
            else if (t.IsFaulted)
            {
                _logger.LogError(t.Exception, "Error processing tool result");
                // Send error response to the model
                var errorContentId = Guid.NewGuid().ToString();
                SendStart(errorContentId, _toolUseId.Value);
                SendErrorToolResult(errorContentId, t.Exception);
                SendEnd(errorContentId);
            }
        });
    }

    private void SendToolResult(ToolResultProcessor.ToolResultResponse response)
    {
        if (_inputObserver != null)
        {
            try
            {
                // Create the "toolResult" object
                var toolResultNode = new JObject
                {
                    ["promptName"] = response.PromptId,
                    ["contentName"] = response.ContentId,
                    ["content"] = response.Content // Content is already properly formatted JSON string
                };

                // Create the final JSON structure
                var eventNode = new JObject
                {
                    ["toolResult"] = toolResultNode
                };

                var rootNode = new JObject
                {
                    ["event"] = eventNode
                };

                var jsonPayload = rootNode.ToString(Formatting.None);
                _logger.LogDebug("Tool Result - Tool Result payload: {Payload}", jsonPayload);
                _inputObserver.OnNext(jsonPayload);
            }
            catch (Exception e)
            {
                throw new Exception("Error creating JSON payload for toolResult", e);
            }
        }
    }

    private void SendErrorToolResult(string contentId, Exception? ex)
    {
        if (_inputObserver != null)
        {
            try
            {
                var errorContent = new JObject
                {
                    ["error"] = $"Tool execution failed: {ex?.Message}"
                };

                var toolResultNode = new JObject
                {
                    ["promptName"] = _promptId.Value,
                    ["contentName"] = contentId,
                    ["content"] = errorContent.ToString(Formatting.None)
                };

                // Create the final JSON structure
                var eventNode = new JObject
                {
                    ["toolResult"] = toolResultNode
                };

                var rootNode = new JObject
                {
                    ["event"] = eventNode
                };

                var jsonPayload = rootNode.ToString(Formatting.None);
                _logger.LogDebug("Sending error tool result: {Payload}", jsonPayload);
                _inputObserver.OnNext(jsonPayload);
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Failed to send error tool result");
            }
        }
    }

    private void SendStart(string contentId, string toolUseId)
    {
        if (_inputObserver != null)
        {
            try
            {
                var textInputConfigNode = new JObject
                {
                    ["mediaType"] = "text/plain"
                };

                var toolResultInputConfigNode = new JObject
                {
                    ["toolUseId"] = toolUseId,
                    ["type"] = "TEXT",
                    ["textInputConfiguration"] = textInputConfigNode
                };

                var contentStartNode = new JObject
                {
                    ["promptName"] = _promptId.Value,
                    ["contentName"] = contentId,
                    ["interactive"] = false,
                    ["type"] = "TOOL",
                    ["role"] = "TOOL",
                    ["toolResultInputConfiguration"] = toolResultInputConfigNode
                };

                var eventNode = new JObject
                {
                    ["contentStart"] = contentStartNode
                };

                var rootNode = new JObject
                {
                    ["event"] = eventNode
                };

                var contentStart = rootNode.ToString(Formatting.None);
                _logger.LogDebug("Tool Result - Content Start payload: {Payload}", contentStart);
                _inputObserver.OnNext(contentStart);
            }
            catch (Exception e)
            {
                throw new Exception("Error creating JSON payload for Tool Result contentStart", e);
            }
        }
    }

    private void SendEnd(string contentId)
    {
        if (_inputObserver != null)
        {
            try
            {
                var contentEndNode = new JObject
                {
                    ["promptName"] = _promptId.Value,
                    ["contentName"] = contentId
                };

                var eventNode = new JObject
                {
                    ["contentEnd"] = contentEndNode
                };

                var rootNode = new JObject
                {
                    ["event"] = eventNode
                };

                var contentEnd = rootNode.ToString(Formatting.None);
                _logger.LogDebug("Tool Result - Content End payload: {Payload}", contentEnd);
                _inputObserver.OnNext(contentEnd);
            }
            catch (Exception e)
            {
                throw new Exception("Error creating JSON payload for Tool Result contentEnd", e);
            }
        }
    }

    private void LogChatHistories(string localChatHistory)
    {
        _logger.LogDebug("Actual chat History: {ActualHistory}", _toolUseContent.Value);
        _logger.LogDebug("Local Chat History: {LocalHistory}", localChatHistory);
    }

    private void HandleContentEnd(JToken? node)
    {
        if (node != null)
        {
            var contentId = node["contentId"]?.ToString() ?? string.Empty;
            var stopReason = node["stopReason"]?.ToString() ?? string.Empty;
            _logger.LogInformation("Content ended: {ContentId} with reason: {StopReason}", contentId, stopReason);
        }
    }

    private void HandleCompletionEnd(JToken? node)
    {
        if (node != null)
        {
            var stopReason = node["stopReason"]?.ToString() ?? string.Empty;
            _logger.LogInformation("Completion ended with reason: {StopReason}", stopReason);
        }
    }

    private void HandleSessionEnd()
    {
        _logger.LogInformation("Session ended");
        _inputObserver?.OnComplete();
    }

    private string CreateChatHistoryFromLocal()
    {
        var messageJsonArray = new JArray();
        foreach (var cc in _localChatHistory)
        {
            var messageObj = new JObject
            {
                ["role"] = cc.Role,
                ["content"] = cc.Content
            };
            messageJsonArray.Add(messageObj);
        }

        var chatHistoryObj = new JObject
        {
            ["chatHistory"] = messageJsonArray
        };

        return chatHistoryObj.ToString(Formatting.None);
    }

    private async Task SendMessageAsync(string message)
    {
        if (_webSocket.State == WebSocketState.Open)
        {
            var buffer = Encoding.UTF8.GetBytes(message);
            await _webSocket.SendAsync(
                new ArraySegment<byte>(buffer),
                WebSocketMessageType.Text,
                true,
                CancellationToken.None).ConfigureAwait(false);
        }
    }
}
