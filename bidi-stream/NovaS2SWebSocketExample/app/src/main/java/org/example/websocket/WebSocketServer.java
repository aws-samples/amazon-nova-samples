package org.example.websocket;

import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.server.ServerConnector;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.websocket.server.config.JettyWebSocketServletContainerInitializer;
import org.example.utility.NovaReasoningModel;
import org.example.utility.NovaS2SBedrockInteractClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider;
import software.amazon.awssdk.http.Protocol;
import software.amazon.awssdk.http.ProtocolNegotiation;
import software.amazon.awssdk.http.nio.netty.NettyNioAsyncHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;

import java.time.Duration;
import java.time.temporal.ChronoUnit;

public class WebSocketServer {
    private static final Logger log = LoggerFactory.getLogger(WebSocketServer.class);

    private final Server server;
    private final int port;

    public WebSocketServer(int port) {
        this.port = port;
        this.server = new Server();
    }

    public void start() throws Exception {
        ServerConnector connector = new ServerConnector(server);
        connector.setPort(port);
        server.addConnector(connector);

        // Create WebSocket handler
        ServletContextHandler context = new ServletContextHandler(ServletContextHandler.SESSIONS);
        context.setContextPath("/");

        // Configure WebSocket
        JettyWebSocketServletContainerInitializer.configure(context, (servletContext, wsContainer) -> {
            wsContainer.setIdleTimeout(Duration.ofMinutes(5));
            wsContainer.setMaxTextMessageSize(128 * 1024);

            BedrockRuntimeAsyncClient client = BedrockRuntimeAsyncClient.builder()
                    .region(Region.US_EAST_1)
                    .credentialsProvider(ProfileCredentialsProvider.create("bedrock-test"))
                    .httpClient(NettyNioAsyncHttpClient.builder()
                            .readTimeout(Duration.of(180, ChronoUnit.SECONDS))
                            .maxConcurrency(200)
                            .protocolNegotiation(ProtocolNegotiation.ALPN)
                            .protocol(Protocol.HTTP2)
                            .build())
                    .build();

            BedrockRuntimeAsyncClient novaClient = BedrockRuntimeAsyncClient.builder()
                    .credentialsProvider(ProfileCredentialsProvider.create("bedrock-test"))
                    .region(Region.US_EAST_1)
                    .build();


            NovaS2SBedrockInteractClient interactClient = new NovaS2SBedrockInteractClient(client);
            NovaReasoningModel handler = new NovaReasoningModel(novaClient, NovaReasoningModel.LITE_MODEL_ID, false);
            wsContainer.addMapping("/interact-s2s", (req, resp) -> {
                return new InteractWebSocket(interactClient, handler);
            });
        });

        server.setHandler(context);

        server.start();
        log.info("WebSocket Server started on port {}", port);
        server.join();
    }

    public void stop() throws Exception {
        server.stop();
    }
}
