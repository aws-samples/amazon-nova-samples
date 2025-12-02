package org.example.utility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.http.client.config.RequestConfig;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ToolResultProcessor {
    private static final Logger log = LoggerFactory.getLogger(ToolResultProcessor.class);
    private final ObjectMapper objectMapper;
    private final ExecutorService executorService;

    public ToolResultProcessor() {
        this.objectMapper = new ObjectMapper();
        this.executorService = Executors.newCachedThreadPool();
    }

    public CompletableFuture<ToolResultResponse> processToolUseAsync(String promptId, String toolUseId, String toolName, String toolUseContent) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                log.info("Processing tool use asynchronously: {}", toolName);
                String contentId = UUID.randomUUID().toString();
                
                // Create the content based on the tool type
                ObjectNode contentNode = objectMapper.createObjectNode();
                
                switch (toolName) {
                    case "getDateAndTimeTool": {
                        LocalDate currentDate = LocalDate.now(ZoneId.of("America/Los_Angeles"));
                        ZonedDateTime pstTime = ZonedDateTime.now(ZoneId.of("America/Los_Angeles"));
                        contentNode.put("date", currentDate.format(DateTimeFormatter.ISO_DATE));
                        contentNode.put("year", currentDate.getYear());
                        contentNode.put("month", currentDate.getMonthValue());
                        contentNode.put("day", currentDate.getDayOfMonth());
                        contentNode.put("dayOfWeek", currentDate.getDayOfWeek().toString());
                        contentNode.put("timezone", "PST");
                        contentNode.put("formattedTime", pstTime.format(DateTimeFormatter.ofPattern("HH:mm")));
                        break;
                    }
                    case "getWeatherTool": {
                        try {
                            // Parse the tool content to get latitude and longitude
                            JsonNode toolContentJson = objectMapper.readTree(toolUseContent);
                            double latitude = toolContentJson.get("latitude").asDouble();
                            double longitude = toolContentJson.get("longitude").asDouble();
                            
                            // Call the weather API
                            Map<String, Object> weatherData = fetchWeatherData(latitude, longitude);
                            
                            // Convert map to JsonNode and add it to content
                            contentNode = objectMapper.valueToTree(weatherData);
                            
                        } catch (Exception e) {
                            log.error("Error processing weather tool request", e);
                            contentNode.put("error", "Failed to fetch weather data: " + e.getMessage());
                        }
                       
                        break;
                    }
                    default: {
                        log.warn("Unhandled tool: {}", toolName);
                        contentNode.put("error", "Unsupported tool: " + toolName);
                    }
                }
                
                return new ToolResultResponse(promptId, contentId, toolUseId, objectMapper.writeValueAsString(contentNode));
                
            } catch (Exception e) {
                log.error("Error processing tool use", e);
                throw new RuntimeException("Error processing tool use", e);
            }
        }, executorService);
    }

    private Map<String, Object> fetchWeatherData(double latitude, double longitude) throws IOException {
        String url = "https://api.open-meteo.com/v1/forecast?latitude=" + latitude + 
                     "&longitude=" + longitude + "&current_weather=true";

        try {
            log.info("Fetching weather data from: {}", url);
            
            RequestConfig config = RequestConfig.custom()
                .setConnectTimeout(5000)
                .setSocketTimeout(5000)
                .build();

            CloseableHttpClient httpClient = HttpClients.custom()
                .setDefaultRequestConfig(config)
                .build();

            HttpGet request = new HttpGet(url);
            request.addHeader("User-Agent", "MyApp/1.0");
            request.addHeader("Accept", "application/json");

            CloseableHttpResponse response = httpClient.execute(request);
            String responseBody = EntityUtils.toString(response.getEntity());
            
            ObjectMapper mapper = new ObjectMapper();
            Map<String, Object> weatherData = mapper.readValue(responseBody, Map.class);
            
            log.info("Weather data received: {}", weatherData);
            
            Map<String, Object> result = new HashMap<>();
            result.put("weather_data", weatherData);
            return result;            
        } catch (IOException error) {
            log.error("Error fetching weather data: {}", error.getMessage());
            throw new IOException("Error fetching weather data", error);
        }
    }

    public void shutdown() {
        executorService.shutdown();
    }

    public static class ToolResultResponse {
        private final String promptId;
        private final String contentId;
        private final String toolUseId;
        private final String content;
        
        public ToolResultResponse(String promptId, String contentId, String toolUseId, String content) {
            this.promptId = promptId;
            this.contentId = contentId;
            this.toolUseId = toolUseId;
            this.content = content;
        }
        
        public String getPromptId() {
            return promptId;
        }
        
        public String getContentId() {
            return contentId;
        }
        
        public String getToolUseId() {
            return toolUseId;
        }
        
        public String getContent() {
            return content;
        }
    }
}
