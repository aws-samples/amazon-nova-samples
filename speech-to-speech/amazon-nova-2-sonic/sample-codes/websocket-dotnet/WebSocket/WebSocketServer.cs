using System.Net;
using System.Net.WebSockets;
using Amazon;
using Amazon.BedrockRuntime;
using Amazon.Runtime;
using Microsoft.Extensions.Logging;
using NovaSonicWebSocket.Utility;

namespace NovaSonicWebSocket;

public class WebSocketServer
{
    private readonly ILogger<WebSocketServer> _logger;
    private readonly ILoggerFactory _loggerFactory;
    private readonly HttpListener _listener;
    private readonly int _port;
    private bool _isRunning;
    private CancellationTokenSource? _cancellationTokenSource;
    private readonly WebSocketSessionManager _sessionManager;

    public WebSocketServer(int port, ILoggerFactory loggerFactory)
    {
        _port = port;
        _loggerFactory = loggerFactory;
        _logger = loggerFactory.CreateLogger<WebSocketServer>();
        _listener = new HttpListener();
        _listener.Prefixes.Add($"http://+:{port}/");
        _sessionManager = new WebSocketSessionManager(_logger);
    }

    public async Task Start()
    {
        _cancellationTokenSource = new CancellationTokenSource();
        _listener.Start();
        _isRunning = true;
        _logger.LogInformation("WebSocket Server started on port {Port}", _port);

        try
        {
            var config = new AmazonBedrockRuntimeConfig
            {
                RegionEndpoint = RegionEndpoint.EUNorth1,
                Timeout = TimeSpan.FromSeconds(180)
            };
            
            var awsProfile = Environment.GetEnvironmentVariable("AWS_PROFILE");
            if (!string.IsNullOrEmpty(awsProfile))
            {
                AWSConfigs.AWSProfileName = awsProfile;
            }
            
            var client = new AmazonBedrockRuntimeClient(config);
            var interactClient = new NovaSonicBedrockInteractClient(client, _loggerFactory);

            while (_isRunning)
            {
                var context = await _listener.GetContextAsync();
                if (context.Request.IsWebSocketRequest)
                {
                    // Fire and forget - handle each connection independently
                    _ = ProcessWebSocketRequestAsync(context, interactClient);
                }
                else
                {
                    context.Response.StatusCode = 400;
                    context.Response.Close();
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in WebSocket server");
            throw;
        }
    }

    private async Task ProcessWebSocketRequestAsync(HttpListenerContext context, NovaSonicBedrockInteractClient interactClient)
    {
        try
        {
            var webSocketContext = await context.AcceptWebSocketAsync(subProtocol: null).ConfigureAwait(false);
            var webSocket = webSocketContext.WebSocket;

            // Create a new session for this connection
            var session = _sessionManager.CreateSession(webSocket);
            _logger.LogInformation("WebSocket connection established - Session ID: {SessionId}", session.SessionId);

            // Handle the WebSocket connection
            var handler = new InteractWebSocket(session, interactClient, _loggerFactory);
            await handler.ProcessWebSocketConnection(_cancellationTokenSource?.Token ?? CancellationToken.None).ConfigureAwait(false);
            
            // Clean up the session when the connection ends
            _sessionManager.RemoveSession(session.SessionId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing WebSocket request");
            context.Response.StatusCode = 500;
            context.Response.Close();
        }
    }

    public void Stop()
    {
        _isRunning = false;
        _cancellationTokenSource?.Cancel();
        _listener.Stop();
        _logger.LogInformation("WebSocket Server stopped - Active sessions: {ActiveSessions}", _sessionManager.ActiveSessionCount);
    }
}
