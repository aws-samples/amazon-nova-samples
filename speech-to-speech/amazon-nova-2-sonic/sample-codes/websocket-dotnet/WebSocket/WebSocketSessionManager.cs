using System;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using Microsoft.Extensions.Logging;

namespace NovaSonicWebSocket
{
    public class WebSocketSessionManager
    {
        private readonly ConcurrentDictionary<string, WebSocketSession> _sessions = new();
        private readonly ILogger _logger;
        
        public WebSocketSessionManager(ILogger logger)
        {
            _logger = logger;
        }
        
        public WebSocketSession CreateSession(WebSocket webSocket)
        {
            var session = new WebSocketSession(webSocket, _logger);
            _sessions.TryAdd(session.SessionId, session);
            _logger.LogInformation("Web Socket Session created: {SessionId}", session.SessionId);
            return session;
        }
        
        public bool TryGetSession(string sessionId, out WebSocketSession? session)
        {
            return _sessions.TryGetValue(sessionId, out session);
        }
        
        public void RemoveSession(string sessionId)
        {
            if (_sessions.TryRemove(sessionId, out var session))
            {
                _logger.LogInformation("Web Socket Session removed: {SessionId}", sessionId);
            }
        }
        
        public int ActiveSessionCount => _sessions.Count;
    }
}
