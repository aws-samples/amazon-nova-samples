package org.example;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.example.websocket.WebSocketServer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.MockedConstruction;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
public class BedrockInitiateClientTest {

    @Test
    void testMainMethodStartsServer() throws Exception {
        // Instead of mocking the constructor directly, use MockedConstruction
        try (MockedConstruction<WebSocketServer> mockedConstruction = mockConstruction(WebSocketServer.class);
             MockedStatic<Runtime> mockedRuntime = mockStatic(Runtime.class)) {

            Runtime mockRuntime = mock(Runtime.class);
            mockedRuntime.when(Runtime::getRuntime).thenReturn(mockRuntime);

            // Call the main method
            BedrockInitiateClient.main(new String[]{});

            // Verify the server was constructed (mockConstruction creates a list of constructed instances)
            assertEquals(1, mockedConstruction.constructed().size(), "One WebSocketServer should be created");

            // Get the constructed instance
            WebSocketServer mockServer = mockedConstruction.constructed().get(0);

            // Verify the server was started
            verify(mockServer).start();
            // Verify a shutdown hook was added
            verify(mockRuntime).addShutdownHook(any(Thread.class));
        }
    }

    @Test
    void testShutdownHook() throws Exception {
        // Capture the shutdown hook
        Thread[] shutdownHook = new Thread[1];

        try (MockedConstruction<WebSocketServer> mockedConstruction = mockConstruction(WebSocketServer.class);
             MockedStatic<Runtime> mockedRuntime = mockStatic(Runtime.class)) {

            Runtime mockRuntime = mock(Runtime.class);
            doAnswer(invocation -> {
                shutdownHook[0] = invocation.getArgument(0);
                return null;
            }).when(mockRuntime).addShutdownHook(any(Thread.class));

            mockedRuntime.when(Runtime::getRuntime).thenReturn(mockRuntime);

            // Call the main method
            BedrockInitiateClient.main(new String[]{});

            // Get the constructed server instance
            assertEquals(1, mockedConstruction.constructed().size(), "One WebSocketServer should be created");
            WebSocketServer mockServer = mockedConstruction.constructed().get(0);

            // Execute the shutdown hook
            assertNotNull(shutdownHook[0], "Shutdown hook should have been captured");
            shutdownHook[0].run();

            // Verify server.stop() was called
            verify(mockServer).stop();
        }
    }
}