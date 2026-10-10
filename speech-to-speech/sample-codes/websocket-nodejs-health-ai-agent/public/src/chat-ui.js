// src/chat-ui.js
// Manages the chat interface and UI components

import { ChatHistoryManager } from "./lib/util/ChatHistoryManager.js";

// Chat state
let chat = { history: [], actions: [] };
const chatRef = { current: chat };

// DOM elements
let chatContainer = null;

// Thinking indicators
let waitingForUserTranscription = false;
let waitingForAssistantResponse = false;
let userThinkingIndicator = null;
let assistantThinkingIndicator = null;
let transcriptionReceived = false;

/**
 * Initialize the Chat UI
 * @param {HTMLElement} container The chat container element
 */
export function initializeChatUI(container) {
  chatContainer = container;
  
  // Initialize chat history manager
  return ChatHistoryManager.getInstance(
    chatRef,
    (newChat) => {
      chat = { ...newChat };
      chatRef.current = chat;
      updateChatUI();
    }
  );
}

/**
 * Update the chat UI with the current chat history
 */
export function updateChatUI() {
  if (!chatContainer) {
    console.error("Chat container not found");
    return;
  }

  // Clear existing chat messages
  chatContainer.innerHTML = '';

  // Add all messages from history
  chat.history.forEach(item => {
    if (item.endOfConversation) {
      const endDiv = document.createElement('div');
      endDiv.className = 'message system';
      endDiv.textContent = "Conversation ended";
      chatContainer.appendChild(endDiv);
      return;
    }

    if (item.role) {
      const messageDiv = document.createElement('div');
      const roleLowerCase = item.role.toLowerCase();
      messageDiv.className = `message ${roleLowerCase}`;

      const roleLabel = document.createElement('div');
      roleLabel.className = 'role-label';
      roleLabel.textContent = item.role;
      messageDiv.appendChild(roleLabel);

      const content = document.createElement('div');
      content.textContent = item.message || "No content";
      messageDiv.appendChild(content);

      chatContainer.appendChild(messageDiv);
    }
  });

  // Re-add thinking indicators if we're still waiting
  if (waitingForUserTranscription) {
    showUserThinkingIndicator();
  }

  if (waitingForAssistantResponse) {
    showAssistantThinkingIndicator();
  }

  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Process message data and add to chat history
 * @param {Object} data The message data
 */
export function handleTextOutput(data) {
  if (data.content) {
    const messageData = {
      role: data.role,
      message: data.content
    };
    ChatHistoryManager.getInstance().addTextMessage(messageData);
  }
}

/**
 * Show the "Listening" indicator for user
 */
export function showUserThinkingIndicator() {
  hideUserThinkingIndicator();

  waitingForUserTranscription = true;
  userThinkingIndicator = document.createElement('div');
  userThinkingIndicator.className = 'message user thinking';

  const roleLabel = document.createElement('div');
  roleLabel.className = 'role-label';
  roleLabel.textContent = 'USER';
  userThinkingIndicator.appendChild(roleLabel);

  const listeningText = document.createElement('div');
  listeningText.className = 'thinking-text';
  listeningText.textContent = 'Listening';
  userThinkingIndicator.appendChild(listeningText);

  const dotContainer = document.createElement('div');
  dotContainer.className = 'thinking-dots';

  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.className = 'dot';
    dotContainer.appendChild(dot);
  }

  userThinkingIndicator.appendChild(dotContainer);
  chatContainer.appendChild(userThinkingIndicator);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Show the "Thinking" indicator for assistant
 */
export function showAssistantThinkingIndicator() {
  hideAssistantThinkingIndicator();

  waitingForAssistantResponse = true;
  assistantThinkingIndicator = document.createElement('div');
  assistantThinkingIndicator.className = 'message assistant thinking';

  const roleLabel = document.createElement('div');
  roleLabel.className = 'role-label';
  roleLabel.textContent = 'ASSISTANT';
  assistantThinkingIndicator.appendChild(roleLabel);

  const thinkingText = document.createElement('div');
  thinkingText.className = 'thinking-text';
  thinkingText.textContent = 'Thinking';
  assistantThinkingIndicator.appendChild(thinkingText);

  const dotContainer = document.createElement('div');
  dotContainer.className = 'thinking-dots';

  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.className = 'dot';
    dotContainer.appendChild(dot);
  }

  assistantThinkingIndicator.appendChild(dotContainer);
  chatContainer.appendChild(assistantThinkingIndicator);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Hide the user thinking indicator
 */
export function hideUserThinkingIndicator() {
  waitingForUserTranscription = false;
  if (userThinkingIndicator && userThinkingIndicator.parentNode) {
    userThinkingIndicator.parentNode.removeChild(userThinkingIndicator);
  }
  userThinkingIndicator = null;
}

/**
 * Hide the assistant thinking indicator
 */
export function hideAssistantThinkingIndicator() {
  waitingForAssistantResponse = false;
  if (assistantThinkingIndicator && assistantThinkingIndicator.parentNode) {
    assistantThinkingIndicator.parentNode.removeChild(assistantThinkingIndicator);
  }
  assistantThinkingIndicator = null;
}

/**
 * Get the current chat history
 * @returns {Object} Current chat history
 */
export function getChatHistory() {
  return chat;
}

/**
 * Check if we're waiting for a user transcription
 * @returns {boolean} True if waiting for user transcription
 */
export function isWaitingForUserTranscription() {
  return waitingForUserTranscription;
}

/**
 * Check if we're waiting for an assistant response
 * @returns {boolean} True if waiting for assistant response
 */
export function isWaitingForAssistantResponse() {
  return waitingForAssistantResponse;
}

/**
 * Set the transcription received flag
 * @param {boolean} value True if transcription received
 */
export function setTranscriptionReceived(value) {
  transcriptionReceived = value;
}

/**
 * Check if transcription has been received
 * @returns {boolean} True if transcription received
 */
export function isTranscriptionReceived() {
  return transcriptionReceived;
}