using System.Net.WebSockets;
using System.Text;
using Microsoft.Extensions.Logging;
using NovaSonicWebSocket.Utility;

namespace NovaSonicWebSocket;

public class InteractWebSocket
{
    private readonly WebSocket _webSocket;
    private readonly NovaSonicBedrockInteractClient _interactClient;
    private readonly ILogger<InteractWebSocket> _logger;
    private readonly WebSocketSession _session;
    private bool _isInitialRequest = true;
    private readonly object _lockObject = new();

    public InteractWebSocket(WebSocketSession session, NovaSonicBedrockInteractClient interactClient, ILoggerFactory loggerFactory)
    {
        _session = session;
        _webSocket = session.WebSocket;
        _interactClient = interactClient;
        _logger = loggerFactory.CreateLogger<InteractWebSocket>();
    }

    public async Task ProcessWebSocketConnection(CancellationToken cancellationToken)
    {
        var buffer = new byte[16384]; // Increased from 4096 to 16384 for better throughput

        try
        {
            while (_webSocket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
            {
                var result = await _webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationToken).ConfigureAwait(false);

                if (result.MessageType == WebSocketMessageType.Text)
                {
                    var jsonText = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    await HandleWebSocketMessage(jsonText).ConfigureAwait(false);
                }
                else if (result.MessageType == WebSocketMessageType.Close)
                {
                    await _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", cancellationToken).ConfigureAwait(false);
                    _session.InputObserver?.OnComplete();
                    break;
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "WebSocket error");
            if (_webSocket.State == WebSocketState.Open)
            {
                await _webSocket.CloseAsync(WebSocketCloseStatus.InternalServerError, "Error", cancellationToken).ConfigureAwait(false);
            }
            _session.InputObserver?.OnError(ex);
        }
    }

    private async Task HandleWebSocketMessage(string jsonText)
    {
        bool isInitial = false;

        lock (_lockObject)
        {
            if (_isInitialRequest)
            {
                _isInitialRequest = false;
                isInitial = true;
            }
        }

        if (isInitial)
        {
            await HandleInitialRequest(jsonText);
        }
        else
        {
            await HandleRemainingRequests(jsonText);
        }
    }

    private Task HandleInitialRequest(string jsonInitialRequestText)
    {
        try
        {
            _logger.LogInformation("Handling initial request for websocket session {SessionId}", _session.SessionId);
            var inputObserver = _interactClient.InteractMultimodal(jsonInitialRequestText, _session.OutputObserver);
            _session.SetInputObserver(inputObserver);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling initial request");
            _session.InputObserver?.OnError(ex);
        }
        return Task.CompletedTask;
    }

    private Task HandleRemainingRequests(string jsonMsg)
    {
        try
        {
            if (_session.InputObserver == null)
            {
                _logger.LogError("Input observer is null for session {SessionId}", _session.SessionId);
                return Task.CompletedTask;
            }
            _session.InputObserver.OnNext(jsonMsg);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling remaining requests");
            _session.InputObserver?.OnError(ex);
        }
        return Task.CompletedTask;
    }
}
