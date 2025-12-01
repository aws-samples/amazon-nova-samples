package org.example.utility;

import io.reactivex.rxjava3.processors.ReplayProcessor;
import io.reactivex.rxjava3.schedulers.Schedulers;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamInput;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamRequest;

import java.util.concurrent.TimeUnit;

public class NovaSonicBedrockInteractClient {
    private static final Logger log = LoggerFactory.getLogger(NovaSonicBedrockInteractClient.class);
    private final BedrockRuntimeAsyncClient bedrockClient;

    public NovaSonicBedrockInteractClient(BedrockRuntimeAsyncClient bedrockClient) {
        this.bedrockClient = bedrockClient;
    }

    public InteractObserver<String> interactMultimodal(
            String initialRequest,
            InteractObserver<String> outputEventsInteractObserver
    ) {
        log.info("initialRequest={}", initialRequest);
        InvokeModelWithBidirectionalStreamRequest request = InvokeModelWithBidirectionalStreamRequest.builder()
                .modelId("amazon.nova-2-sonic-v1:0")
                .build();
        // we expire the messages after one minute to save memory after connection as this is aligned with the timeout
        ReplayProcessor<InvokeModelWithBidirectionalStreamInput> publisher = ReplayProcessor.createWithTime(
                1, TimeUnit.MINUTES, Schedulers.io()
        );

        var responseHandler = new NovaSonicResponseHandler(outputEventsInteractObserver);

        var completableFuture = bedrockClient.invokeModelWithBidirectionalStream(request, publisher, responseHandler);

        // if the request fails make sure to tell the publisher to close down properly
        completableFuture.exceptionally(throwable -> {
            publisher.onError(throwable);
            return null;
        });

        // if the request finishes make sure to close the publisher properly
        completableFuture.thenApply(result -> {
            publisher.onComplete();
            return result;
        });

        // send the session start
        publisher.onNext(
                InvokeModelWithBidirectionalStreamInput.chunkBuilder()
                        .bytes(SdkBytes.fromUtf8String(initialRequest))
                        .build()
        );

        return new InputEventsInteractObserver(publisher);
    }
}