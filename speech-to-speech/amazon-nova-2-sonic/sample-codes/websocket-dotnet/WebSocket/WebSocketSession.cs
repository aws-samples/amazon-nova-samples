using System;
using System.Net.WebSockets;
using Microsoft.Extensions.Logging;
using NovaSonicWebSocket.Utility;

namespace NovaSonicWebSocket
{
    public class WebSocketSession
    {
        public string SessionId { get; }
        public WebSocket WebSocket { get; }
        public DateTime ConnectedAt { get; }
        public AtomicReference<string> PromptId { get; }
        public OutputEventsInteractObserver OutputObserver { get; }
        public IInteractObserver<string>? InputObserver { get; private set; }
        
        public WebSocketSession(WebSocket webSocket, ILogger logger)
        {
            SessionId = Guid.NewGuid().ToString();
            WebSocket = webSocket;
            ConnectedAt = DateTime.UtcNow;
            PromptId = new AtomicReference<string>(string.Empty);
            
            // Create output observer for this specific session
            OutputObserver = new OutputEventsInteractObserver(webSocket, logger, PromptId);
        }
        
        public void SetInputObserver(IInteractObserver<string> inputObserver)
        {
            InputObserver = inputObserver;
            OutputObserver.SetInputObserver(inputObserver);
        }
    }
}
