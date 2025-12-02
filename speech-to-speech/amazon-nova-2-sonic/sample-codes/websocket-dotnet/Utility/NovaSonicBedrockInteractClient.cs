using Amazon.BedrockRuntime;
using Amazon.BedrockRuntime.Model;
using Amazon.Runtime.EventStreams;
using System;
using System.Collections.Concurrent;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace NovaSonicWebSocket.Utility;
public class NovaSonicBedrockInteractClient
{
    private readonly ILogger<NovaSonicBedrockInteractClient> _logger;
    private readonly AmazonBedrockRuntimeClient _bedrockClient;

    public NovaSonicBedrockInteractClient(AmazonBedrockRuntimeClient bedrockClient, ILoggerFactory loggerFactory)
    {
        _bedrockClient = bedrockClient;
        _logger = loggerFactory.CreateLogger<NovaSonicBedrockInteractClient>();
    }

    public InputEventsInteractObserver InteractMultimodal(
        string initialRequest,
        IInteractObserver<string> outputEventsInteractObserver)
    {
        _logger.LogInformation("initialRequest={InitialRequest}", initialRequest);

        var request = new InvokeModelWithBidirectionalStreamRequest
        {
            ModelId = "amazon.nova-2-sonic-v1:0"
        };

        // Create a publisher-like mechanism
        var messageQueue = new BlockingCollection<IInvokeModelWithBidirectionalStreamInputEvent>();

        // Add the initial request
        messageQueue.Add(new BidirectionalInputPayloadPart
        {
            Bytes = ConvertStringToMemoryStream(initialRequest)
        });

        request.BodyPublisher = () =>
        {
            // Reduced timeout from 60000ms to 5000ms to prevent long blocking
            if (messageQueue.TryTake(out var message, 5000))
            {
                return Task.FromResult<IInvokeModelWithBidirectionalStreamInputEvent?>(message);
            }
            return Task.FromResult<IInvokeModelWithBidirectionalStreamInputEvent?>(null);
        };

        var responseHandler = new NovaSonicResponseHandler(outputEventsInteractObserver, _logger);
        var cancellationTokenSource = new CancellationTokenSource();

        var task = Task.Run(async () =>
        {
            try
            {
                using var response = await _bedrockClient.InvokeModelWithBidirectionalStreamAsync(request, cancellationTokenSource.Token).ConfigureAwait(false);

                response.Body.ChunkReceived += (sender, args) =>
                {
                    responseHandler.HandleChunk(args.EventStreamEvent);
                };

                response.Body.ExceptionReceived += (sender, args) =>
                {
                    _logger.LogError("Error received: {Message}", args.EventStreamException.Message);
                    cancellationTokenSource.Cancel();
                    outputEventsInteractObserver.OnError(args.EventStreamException);
                };

                await response.Body.StartProcessingAsync().ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in bidirectional stream");
                outputEventsInteractObserver.OnError(ex);
            }
            finally
            {
                messageQueue.CompleteAdding();
                outputEventsInteractObserver.OnComplete();
            }
        });

        return new InputEventsInteractObserver(messageQueue, _logger);
    }

    private MemoryStream ConvertStringToMemoryStream(string str)
    {
        var bytes = Encoding.UTF8.GetBytes(str);
        return new MemoryStream(bytes);
    }
}
