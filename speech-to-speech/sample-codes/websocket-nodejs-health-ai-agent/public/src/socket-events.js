// socket-events.js
// Handles all socket.io events

import audioHandler from './audio-handler.js';
import {
  handleTextOutput,
  showUserThinkingIndicator,
  showAssistantThinkingIndicator,
  hideUserThinkingIndicator,
  hideAssistantThinkingIndicator,
  setTranscriptionReceived
} from './chat-ui.js';
import {
  addAgentAction,
  updateAgentStatusUI,
  incrementConversationTurns,
  incrementSearchCount,
  incrementOffTopicCount,
  incrementEmergencyCount,
  incrementMedicalAdviceCount,
  updateInsights
} from './action-panel.js';
import { ChatHistoryManager } from "./lib/util/ChatHistoryManager.js";

// Socket connection
let socket = null;

// Tracking variables
let responseStartTime = 0;
let lastResponseTime = 0;
let role;
let displayAssistantText = false;
let currentToolUseId = null;

/**
 * Initialize socket event handlers
 * @param {Object} io Socket.io instance
 * @param {Object} config Configuration object
 */
export function initializeSocketEvents(io, config) {
  socket = io;
  const statusElement = config.statusElement;
  
  // Handle connection status updates
  socket.on('connect', () => {
    statusElement.textContent = "Connected to server";
    statusElement.className = "connected";
    updateAgentStatusUI('idle', 'Connected');
  });

  socket.on('disconnect', () => {
    statusElement.textContent = "Disconnected from server";
    statusElement.className = "disconnected";
    config.startButton.disabled = true;
    config.stopButton.disabled = true;
    hideUserThinkingIndicator();
    hideAssistantThinkingIndicator();
    updateAgentStatusUI('error', 'Disconnected');
    addAgentAction('error', 'Connection Lost', 'Disconnected from server');
  });

  // Handle errors
  socket.on('error', (error) => {
    console.error("Server error:", error);
    statusElement.textContent = "Error: " + (error.message || JSON.stringify(error).substring(0, 100));
    statusElement.className = "error";
    hideUserThinkingIndicator();
    hideAssistantThinkingIndicator();
    updateAgentStatusUI('error', 'Error');
    addAgentAction('error', 'Server Error', error.message || 'Unknown error occurred');
  });

  // Handle content start from the server
  socket.on('contentStart', (data) => {
    console.log('Content start received:', data);

    if (data.type === 'TEXT') {
      role = data.role;
      if (data.role === 'USER') {
        hideUserThinkingIndicator();
      }
      else if (data.role === 'ASSISTANT') {
        hideAssistantThinkingIndicator();
        // Start tracking response time
        responseStartTime = Date.now();
        
        let isSpeculative = false;
        try {
          if (data.additionalModelFields) {
            const additionalFields = JSON.parse(data.additionalModelFields);
            isSpeculative = additionalFields.generationStage === "SPECULATIVE";
            if (isSpeculative) {
              console.log("Received speculative content");
              displayAssistantText = true;
            }
            else {
              displayAssistantText = false;
            }
          }
        } catch (e) {
          console.error("Error parsing additionalModelFields:", e);
        }
      }
    }
    else if (data.type === 'AUDIO') {
      if (audioHandler.isStreaming) {
        showUserThinkingIndicator();
      }
    }
  });

  // Handle text output from the server
  socket.on('textOutput', (data) => {
    console.log('Received text output:', data);

    if (role === 'USER') {
      // When user text is received, show thinking indicator for assistant response
      setTranscriptionReceived(true);

      // Add user message to chat
      handleTextOutput({
        role: data.role,
        content: data.content
      });
      
      // Add transcription action
      addAgentAction('user', 'User Speech Transcribed', `"${data.content}"`);

      // Show assistant thinking indicator after user text appears
      showAssistantThinkingIndicator();
      updateAgentStatusUI('thinking', 'Thinking');
    }
    else if (role === 'ASSISTANT') {
      if (displayAssistantText) {
        handleTextOutput({
          role: data.role,
          content: data.content
        });
      }
    }
  });

  // Handle tool use events
  socket.on('toolUse', (data) => {
    console.log('Tool use detected:', data);
    
    try {
      // Parse the tool content
      let toolContent;
      try {
        toolContent = JSON.parse(data.content);
      } catch (e) {
        console.warn('Could not parse tool content as JSON:', data.content);
        toolContent = { query: "Unknown query" };
      }
      
      currentToolUseId = data.toolUseId;
      
      // Handle different tool types based on their actual names
      const toolName = data.toolName.toLowerCase();
      
      switch(toolName) {
        case "retrieve_health_info":
          incrementSearchCount();
          
          // Add to agent actions
          addAgentAction('search', 'Searching Knowledge Base', 
            `Query: "${toolContent.query || 'health information'}"`, 
            { toolUseId: data.toolUseId }
          );
          
          updateAgentStatusUI('searching', 'Searching Knowledge Base');
          break;
          
        case "greeting":
          // Add greeting action
          addAgentAction('system', 'Greeting User', 
            `Type: ${toolContent.greeting_type || "standard"}${toolContent.user_name ? ', User: ' + toolContent.user_name : ''}`, 
            { toolUseId: data.toolUseId }
          );
          
          updateAgentStatusUI('responding', 'Greeting');
          break;
          
        case "safety_response":
          // Add safety response action
          addAgentAction('error', 'Safety Response Triggered', 
            `Topic: "${toolContent.topic || 'Unknown topic'}", Type: ${toolContent.request_type || 'Unknown type'}`, 
            { toolUseId: data.toolUseId }
          );
          
          updateAgentStatusUI('responding', 'Safety Response');
          break;
          
        default:
          // Log the exact tool name for debugging
          console.warn(`Unknown tool name: "${data.toolName}"`);
          
          // Generic handling for unknown tools
          addAgentAction('system', `Tool: ${data.toolName}`, 
            `Processing request...`, 
            { toolUseId: data.toolUseId }
          );
          
          updateAgentStatusUI('processing', 'Processing');
      }
      
      updateInsights();
      
    } catch (error) {
      console.error('Error parsing tool use data:', error);
      addAgentAction('error', 'Tool Use Error', 'Failed to parse tool data');
    }
  });

  // Handle tool results
  socket.on('toolResult', (data) => {
    console.log('Tool result received:', data);
    
    try {
      // Find the action that this result belongs to
      const action = document.querySelector(`.action-item[data-tool-use-id="${data.toolUseId}"]`);
      if (!action) return;
      
      if (action.classList.contains('error-action')) {
        // This is a safety response
        if (data.result && data.result.response) {
          // Update the title to be more specific about the type of off-topic request
          if (data.result.request_details) {
            let requestType = data.result.request_details.type || "";
            let category = data.result.request_details.category || "";
            
            // Create a more descriptive title
            let titleEl = action.querySelector('.action-title');
            if (titleEl) {
              if (requestType === "off_topic" || requestType === "non_health") {
                titleEl.textContent = `Off-Topic Request: ${category}`;
                // Change the icon for off-topic
                let iconEl = action.querySelector('.action-icon');
                if (iconEl) iconEl.textContent = '🚫';
                incrementOffTopicCount();
              } else if (requestType === "emergency") {
                titleEl.textContent = `Emergency Guidance Required`;
                // Change icon for emergency
                let iconEl = action.querySelector('.action-icon');
                if (iconEl) iconEl.textContent = '🚨';
                incrementEmergencyCount();
              } else if (requestType === "medical_advice" || requestType === "diagnosis" || requestType === "treatment") {
                titleEl.textContent = `Medical Advice Boundary`;
                // Change icon for medical advice
                let iconEl = action.querySelector('.action-icon');
                if (iconEl) iconEl.textContent = '⚕️';
                incrementMedicalAdviceCount();
              }
            }
          }
          
          const alternatives = document.createElement('div');
          alternatives.className = 'alternative-suggestions';
          alternatives.innerHTML = `<div class="alternative-title">Alternative:</div><p>${data.result.alternative_suggestion || ''}</p>`;
          
          // Append to the action
          action.appendChild(alternatives);
          
          // Add appropriate topics if available
          if (data.result.appropriate_topics && Array.isArray(data.result.appropriate_topics)) {
            const topicsDiv = document.createElement('div');
            topicsDiv.className = 'appropriate-topics';
            topicsDiv.innerHTML = '<div class="topics-title">I can help with:</div>';
            
            const list = document.createElement('ul');
            data.result.appropriate_topics.forEach(topic => {
              const item = document.createElement('li');
              item.textContent = topic;
              list.appendChild(item);
            });
            topicsDiv.appendChild(list);
            action.appendChild(topicsDiv);
          }
          
          // Add special styling for off-topic requests
          if (data.result.request_details && 
            (data.result.request_details.type === "off_topic" || 
              data.result.request_details.type === "non_health")) {
            action.classList.add('off-topic-action');
          }
          // Add special styling for emergency requests
          else if (data.result.request_details && data.result.request_details.type === "emergency") {
            action.classList.add('emergency-action');
          }
        }
      }
      
      updateAgentStatusUI('thinking', 'Formulating Response');
      
    } catch (error) {
      console.error('Error handling tool result:', error);
      addAgentAction('error', 'Result Processing Error', error.message || 'Unknown error');
    }
  });

  // Handle audio output
  socket.on('audioOutput', (data) => {
    if (data.content) {
      audioHandler.playAudio(data.content);
    }
  });

  // Handle content end events
  socket.on('contentEnd', (data) => {
    console.log('Content end received:', data);

    if (data.type === 'TEXT') {
      if (role === 'USER') {
        hideUserThinkingIndicator();
        showAssistantThinkingIndicator();
      }
      else if (role === 'ASSISTANT') {
        // When assistant's text content ends, calculate response time
        if (responseStartTime > 0) {
          lastResponseTime = (Date.now() - responseStartTime) / 1000;
          responseStartTime = 0;
          
          // Increment conversation turn counter
          incrementConversationTurns();
        }
        
        hideAssistantThinkingIndicator();
        addAgentAction('system', 'Response Complete', 'Assistant finished responding');
      }

      // Handle stop reasons
      if (data.stopReason && data.stopReason.toUpperCase() === 'END_TURN') {
        ChatHistoryManager.getInstance().endTurn();
      } else if (data.stopReason && data.stopReason.toUpperCase() === 'INTERRUPTED') {
        console.log("Interrupted by user");
        audioHandler.audioPlayer.bargeIn();
      }
    }
    else if (data.type === 'AUDIO') {
      if (audioHandler.isStreaming) {
        showUserThinkingIndicator();
      }
    } else if (data.type === 'TOOL') {
      addAgentAction('system', 'Knowledge Base Search Complete', 'Processing search results');
    }
  });

  // Stream completion event
  socket.on('streamComplete', () => {
    if (audioHandler.isStreaming) {
      audioHandler.stopStreaming();
    }
    statusElement.textContent = "Ready";
    statusElement.className = "ready";
    updateAgentStatusUI('idle', 'Idle');
    addAgentAction('system', 'Conversation Turn Complete', 'Ready for next input');
  });

  return socket;
}

/**
 * Get the socket instance
 * @returns {Object} Socket.io instance
 */
export function getSocket() {
  return socket;
}