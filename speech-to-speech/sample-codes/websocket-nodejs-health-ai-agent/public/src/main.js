// main.js
// Main application entry point

import audioHandler from './audio-handler.js';
import { initializeChatUI } from './chat-ui.js';
import { initializeActionPanel } from './action-panel.js';
import { initializeSocketEvents } from './socket-events.js';
import { UIManager } from './ui-manager.js'; // New centralized UI manager
import { ChatHistoryManager } from "./lib/util/ChatHistoryManager.js";

// Connect to the server
const socket = io();

// DOM elements
const DOM = {
  startButton: document.getElementById('start'),
  stopButton: document.getElementById('stop'),
  statusElement: document.getElementById('status'),
  chatContainer: document.getElementById('chat-container'),
  agentActions: document.getElementById('agent-actions'),
  agentStatus: document.getElementById('agent-status'),
  filterButtons: document.querySelectorAll('.filter-btn')
};

/**
 * Initialize the application
 */
function initializeApp() {
  // Initialize chat UI
  initializeChatUI(DOM.chatContainer);
  
  // Initialize action panel
  initializeActionPanel({
    agentActions: DOM.agentActions,
    agentStatus: DOM.agentStatus
  });
  
  // Initialize socket events
  initializeSocketEvents(socket, {
    statusElement: DOM.statusElement,
    startButton: DOM.startButton,
    stopButton: DOM.stopButton
  });
  
  // Initialize audio handler
  audioHandler.initialize({
    socket,
    statusElement: DOM.statusElement,
    startButton: DOM.startButton,
    stopButton: DOM.stopButton
  });

  // Initialize UI event handlers
  UIManager.initialize(DOM);
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', initializeApp);

// Export the ChatHistoryManager for use in other modules
export { ChatHistoryManager };