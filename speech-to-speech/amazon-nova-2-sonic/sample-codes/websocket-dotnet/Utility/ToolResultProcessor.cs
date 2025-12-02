using System.Text.Json;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;

namespace NovaSonicWebSocket.Utility;

public class ToolResultProcessor
{
    private readonly ILogger _logger;

    public ToolResultProcessor(ILogger logger)
    {
        _logger = logger;
    }

    public async Task<ToolResultResponse> ProcessToolUseAsync(string promptId, string toolUseId, string toolName, string toolUseContent)
    {
        return await Task.Run(() =>
        {
            try
            {
                _logger.LogInformation("Processing tool use asynchronously: {ToolName}", toolName);
                var contentId = Guid.NewGuid().ToString();

                // Create the content based on the tool type
                var contentNode = new JObject();

                switch (toolName)
                {
                    case "getDateAndTimeTool":
                        {
                            var pstZone = TimeZoneInfo.FindSystemTimeZoneById("Pacific Standard Time");
                            var pstTime = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, pstZone);
                            
                            contentNode["date"] = pstTime.ToString("yyyy-MM-dd");
                            contentNode["year"] = pstTime.Year;
                            contentNode["month"] = pstTime.Month;
                            contentNode["day"] = pstTime.Day;
                            contentNode["dayOfWeek"] = pstTime.DayOfWeek.ToString();
                            contentNode["timezone"] = "PST";
                            contentNode["formattedTime"] = pstTime.ToString("HH:mm");
                            break;
                        }
                    case "getWeatherTool":
                        {
                            try
                            {
                                // Parse the tool content to get city name
                                var toolContentJson = JObject.Parse(toolUseContent);
                                var city = toolContentJson["city"]?.Value<string>();

                                if (string.IsNullOrEmpty(city))
                                {
                                    contentNode["error"] = "City name is required";
                                    break;
                                }

                                _logger.LogInformation("Getting weather for city: {City}", city);

                                // Geocode the city to get latitude and longitude
                                var (latitude, longitude) = GeocodeCity(city).Result;

                                if (latitude == 0 && longitude == 0)
                                {
                                    contentNode["error"] = $"Could not find location for city: {city}";
                                    break;
                                }

                                // Call the weather API
                                var weatherData = FetchWeatherDataAsync(latitude, longitude).Result;

                                // Add city name to the response
                                weatherData["city"] = city;

                                // Add weather data to content
                                contentNode = weatherData;
                            }
                            catch (Exception e)
                            {
                                _logger.LogError(e, "Error processing weather tool request");
                                contentNode["error"] = $"Failed to fetch weather data: {e.Message}";
                            }
                            break;
                        }
                    default:
                        {
                            _logger.LogWarning("Unhandled tool: {ToolName}", toolName);
                            contentNode["error"] = $"Unsupported tool: {toolName}";
                            break;
                        }
                }

                return new ToolResultResponse(promptId, contentId, toolUseId, contentNode.ToString(Newtonsoft.Json.Formatting.None));
            }
            catch (Exception e)
            {
                _logger.LogError(e, "Error processing tool use");
                throw new Exception("Error processing tool use", e);
            }
        });
    }

    private async Task<(double latitude, double longitude)> GeocodeCity(string city)
    {
        // URL encode the city name
        var encodedCity = Uri.EscapeDataString(city);
        var url = $"https://geocoding-api.open-meteo.com/v1/search?name={encodedCity}&count=1&language=en&format=json";

        try
        {
            _logger.LogInformation("Geocoding city: {City}", city);
            using var httpClient = new HttpClient();
            httpClient.Timeout = TimeSpan.FromSeconds(5);
            httpClient.DefaultRequestHeaders.Add("User-Agent", "MyApp/1.0");
            httpClient.DefaultRequestHeaders.Add("Accept", "application/json");

            var response = await httpClient.GetAsync(url).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
            var geocodeData = JObject.Parse(responseBody);

            _logger.LogDebug("Geocode response: {Response}", responseBody);

            // Check if we got results
            var results = geocodeData["results"] as JArray;
            if (results == null || results.Count == 0)
            {
                _logger.LogWarning("No geocoding results found for city: {City}", city);
                return (0, 0);
            }

            var firstResult = results[0] as JObject;
            var latitude = firstResult?["latitude"]?.Value<double>() ?? 0;
            var longitude = firstResult?["longitude"]?.Value<double>() ?? 0;

            _logger.LogInformation("Geocoded {City} to coordinates: {Latitude}, {Longitude}", city, latitude, longitude);

            return (latitude, longitude);
        }
        catch (Exception error)
        {
            _logger.LogError(error, "Error geocoding city: {City}", city);
            return (0, 0);
        }
    }

    private async Task<JObject> FetchWeatherDataAsync(double latitude, double longitude)
    {
        var url = $"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true";

        try
        {
            _logger.LogInformation("Fetching weather data from: {Url}", url);
            // Simulate real-world tool latency
            Thread.Sleep(1000);
            using var httpClient = new HttpClient();
            httpClient.Timeout = TimeSpan.FromSeconds(5);
            httpClient.DefaultRequestHeaders.Add("User-Agent", "MyApp/1.0");
            httpClient.DefaultRequestHeaders.Add("Accept", "application/json");

            var response = await httpClient.GetAsync(url).ConfigureAwait(false);
            response.EnsureSuccessStatusCode();

            var responseBody = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
            var weatherData = JObject.Parse(responseBody);

            _logger.LogInformation("Weather data received: {WeatherData}", weatherData);

            var result = new JObject
            {
                ["weather_data"] = weatherData
            };

            return result;
        }
        catch (Exception error)
        {
            _logger.LogError(error, "Error fetching weather data");
            throw new Exception("Error fetching weather data", error);
        }
    }

    public class ToolResultResponse
    {
        public string PromptId { get; }
        public string ContentId { get; }
        public string ToolUseId { get; }
        public string Content { get; }

        public ToolResultResponse(string promptId, string contentId, string toolUseId, string content)
        {
            PromptId = promptId;
            ContentId = contentId;
            ToolUseId = toolUseId;
            Content = content;
        }
    }
}
