package org.example.utility;

import static com.google.common.base.Preconditions.checkNotNull;

import org.reactivestreams.Subscriber;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.model.BidiInputPayloadPart;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelWithBidiStreamInput;

public class InputEventsInteractObserver implements InteractObserver<String> {
    private static final Logger log = LoggerFactory.getLogger(InputEventsInteractObserver.class);
    private static final String SESSION_END = """
                {
                    "event": {
                        "sessionEnd": {}
                    }
                }""";
    private final Subscriber<InvokeModelWithBidiStreamInput> subscriber;

    public InputEventsInteractObserver(Subscriber<InvokeModelWithBidiStreamInput> publisher) {
        this.subscriber = checkNotNull(publisher, "subscriber cannot be null");
    }

    @Override
    public void onNext(String msg) {
        log.info("publishing message {}", msg);
        this.subscriber.onNext(inputBuilder(msg));
    }

    @Override
    public void onComplete() {
        this.subscriber.onNext(inputBuilder(SESSION_END));
        this.subscriber.onComplete();
    }

    @Override
    public void onError(Exception error) {
       new RuntimeException(error.getMessage());
    }

    private BidiInputPayloadPart inputBuilder (String input) {
        return InvokeModelWithBidiStreamInput.chunkBuilder()
                .bytes(SdkBytes.fromUtf8String(input))
                .build();
    }
}
