using System.Text;
using Amazon.BedrockRuntime.Model;
using Microsoft.Extensions.Logging;

namespace NovaSonicWebSocket.Utility;

public class NovaSonicResponseHandler
{
    private readonly IInteractObserver<string> _delegate;
    private readonly ILogger _logger;

    public NovaSonicResponseHandler(IInteractObserver<string> @delegate, ILogger logger)
    {
        _delegate = @delegate ?? throw new ArgumentNullException(nameof(@delegate));
        _logger = logger;
    }

    public void HandleChunk(BidirectionalOutputPayloadPart chunk)
    {
        try
        {
            _logger.LogDebug("Nova Sonic chunk received, converting to payload");
            
            using var memoryStream = chunk.Bytes;
            if (memoryStream == null)
            {
                _logger.LogWarning("Received null bytes in chunk");
                return;
            }
            
            memoryStream.Position = 0;
            using var reader = new StreamReader(memoryStream, Encoding.UTF8);
            var payloadString = reader.ReadToEnd();
            
            _logger.LogDebug("Nova Sonic payload: {Payload}", payloadString);
            _delegate.OnNext(payloadString);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling chunk");
            _delegate.OnError(ex);
        }
    }

    public void HandleException(Exception exception)
    {
        _logger.LogError(exception, "Exception in Nova Sonic response");
        _delegate.OnError(exception);
    }

    public void Complete()
    {
        _logger.LogInformation("Nova Sonic stream completed");
        _delegate.OnComplete();
    }
}
