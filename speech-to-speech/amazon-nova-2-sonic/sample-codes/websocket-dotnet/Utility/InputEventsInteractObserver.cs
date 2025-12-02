using System.Collections.Concurrent;
using System.Text;
using Amazon.BedrockRuntime.Model;
using Microsoft.Extensions.Logging;

namespace NovaSonicWebSocket.Utility;

public class InputEventsInteractObserver : IInteractObserver<string>
{
    private static readonly string SESSION_END = """
        {
            "event": {
                "sessionEnd": {}
            }
        }
        """;

    private readonly BlockingCollection<IInvokeModelWithBidirectionalStreamInputEvent> _messageQueue;
    private readonly ILogger _logger;

    public InputEventsInteractObserver(BlockingCollection<IInvokeModelWithBidirectionalStreamInputEvent> messageQueue, ILogger logger)
    {
        _messageQueue = messageQueue ?? throw new ArgumentNullException(nameof(messageQueue));
        _logger = logger;
    }

    public void OnNext(string msg)
    {
        //_logger.LogInformation("Publishing message {Message}", msg);
        _messageQueue.Add(CreateInputEvent(msg));
    }

    public void OnComplete()
    {
        _messageQueue.Add(CreateInputEvent(SESSION_END));
        _messageQueue.CompleteAdding();

    }

    public void OnError(Exception error)
    {
        _messageQueue.CompleteAdding();
    }

    private BidirectionalInputPayloadPart CreateInputEvent(string input)
    {
        return new BidirectionalInputPayloadPart
        {
            Bytes = new MemoryStream(Encoding.UTF8.GetBytes(input))
        };
    }
}
