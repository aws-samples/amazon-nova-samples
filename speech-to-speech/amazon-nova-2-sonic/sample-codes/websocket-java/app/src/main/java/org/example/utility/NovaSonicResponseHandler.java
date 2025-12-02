package org.example.utility;

import static com.google.common.base.Preconditions.checkNotNull;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.async.SdkPublisher;
import software.amazon.awssdk.services.bedrockruntime.model.BidirectionalOutputPayloadPart;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamOutput;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamResponse;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidirectionalStreamResponseHandler;

import java.nio.charset.StandardCharsets;

public class NovaSonicResponseHandler implements InvokeModelWithBidirectionalStreamResponseHandler {
    private static final Logger log = LoggerFactory.getLogger(NovaSonicResponseHandler.class);
    private final InteractObserver<String> delegate;

    public NovaSonicResponseHandler( InteractObserver<String> delegate) {
        this.delegate = checkNotNull(delegate, "delegate cannot be null");
    }

    @Override
    public void responseReceived(InvokeModelWithBidirectionalStreamResponse response) {
        log.info("Amazon Nova Sonic request id: {}", response.responseMetadata().requestId());
    }

    @Override
    public void onEventStream(SdkPublisher<InvokeModelWithBidirectionalStreamOutput> sdkPublisher) {
        log.info("Amazon Nova Sonic event stream received");
        var completableFuture = sdkPublisher.subscribe((output) -> output.accept(new Visitor() {
            @Override
            public void visitChunk(BidirectionalOutputPayloadPart event) {
                log.info("Nova Sonic chunk received, converting to payload");
                String payloadString =
                        StandardCharsets.UTF_8.decode((event.bytes().asByteBuffer().rewind().duplicate())).toString();
                log.info("Nova Sonic payload: {}", payloadString);
                    delegate.onNext(payloadString);
            }
        }));

        // if any of the chunks fail to parse or be handled ensure to send an error or they will get lost
        completableFuture.exceptionally(t -> {
            delegate.onError(new Exception(t));
            return null;
        });
    }

    @Override
    public void exceptionOccurred(Throwable t) {
        delegate.onError(new Exception(t));
    }

    @Override
    public void complete() {
        delegate.onComplete();
    }
}
