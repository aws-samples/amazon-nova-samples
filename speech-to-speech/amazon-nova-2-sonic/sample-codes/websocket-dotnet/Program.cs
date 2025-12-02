using Microsoft.Extensions.Logging;
using NovaSonicWebSocket;

// Configure logging
using var loggerFactory = LoggerFactory.Create(builder =>
{
    builder
        .SetMinimumLevel(LogLevel.Debug)  // Changed from Information to Debug for more detailed logs
        .AddSimpleConsole(options =>
        {
            options.IncludeScopes = true;
            options.TimestampFormat = "yyyy-MM-dd HH:mm:ss ";
            options.SingleLine = false;
        });
});

var logger = loggerFactory.CreateLogger<Program>();
logger.LogInformation("=== Application Starting ===");
logger.LogInformation("Log level set to: {LogLevel}", LogLevel.Debug);

// Create and start the WebSocket server
var server = new WebSocketServer(8081, loggerFactory);

// Add shutdown hook
AppDomain.CurrentDomain.ProcessExit += (sender, e) =>
{
    logger.LogInformation("Shutting down server...");
    try
    {
        server.Stop();
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Error shutting down server");
    }
};

try
{
    await server.Start();
}
catch (Exception ex)
{
    logger.LogError(ex, "Error starting server");
}

public partial class Program { }
