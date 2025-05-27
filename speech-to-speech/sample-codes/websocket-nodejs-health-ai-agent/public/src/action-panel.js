// action-panel.js
// Manages the agent actions panel functionality

import { ChatHistoryManager } from "./lib/util/ChatHistoryManager.js";

// Constants for action types and their corresponding icons
const ACTION_CONFIG = {
  system: { icon: '<i class="fas fa-cog"></i>', label: 'System' },
  user: { icon: '<i class="fas fa-user"></i>', label: 'User' },
  search: { icon: '<i class="fas fa-search"></i>', label: 'Search' },
  result: { icon: '<i class="fas fa-file-alt"></i>', label: 'Result' },
  error: { icon: '<i class="fas fa-exclamation-triangle"></i>', label: 'Error' },
  emergency: { icon: '<i class="fas fa-ambulance"></i>', label: 'Emergency' },
  'off-topic': { icon: '<i class="fas fa-ban"></i>', label: 'Off-Topic' }
};

// DOM elements
let agentActions = null;
let agentStatus = null;

// Analytics counters
const analytics = {
  conversationTurns: 0,
  searchCount: 0,
  offTopicCount: 0,
  emergencyCount: 0,
  medicalAdviceCount: 0
};

/**
 * Initialize the action panel
 * @param {Object} config Configuration object with DOM elements
 */
export function initializeActionPanel(config) {
  agentActions = config.agentActions;
  agentStatus = config.agentStatus;
}

/**
 * Update the agent status UI
 * @param {string} status The agent status
 * @param {string} text The text to display
 */
export function updateAgentStatusUI(status, text) {
  if (!agentStatus) return;
  
  // Reset classes and add new status
  agentStatus.className = `agent-status ${status}`;
  
  // Add thinking animation for specific statuses
  if (['thinking', 'processing', 'searching'].includes(status)) {
    agentStatus.classList.add('thinking-status');
  }
  
  // Update or create status text
  let statusTextEl = agentStatus.querySelector('.status-text');
  if (!statusTextEl) {
    agentStatus.innerHTML = `<span class="status-dot"></span><span class="status-text">${text}</span>`;
  } else {
    statusTextEl.textContent = text;
  }
}

/**
 * Add an action to the agent actions panel
 * @param {string} type The action type
 * @param {string} title The action title
 * @param {string} content The action content
 * @param {Object} data Additional data for the action
 * @returns {HTMLElement} The created action item
 */
export function addAgentAction(type, title, content, data = {}) {
  if (!agentActions) {
    console.error("Agent actions container not found");
    return null;
  }
  
  // Remove placeholder if present
  const placeholder = agentActions.querySelector('.action-placeholder');
  if (placeholder) {
    placeholder.remove();
  }
  
  const actionItem = createActionItem(type, title, content, data);
  
  // Add search results if applicable
  if (type === 'result' && data.results?.length > 0) {
    addSearchResults(actionItem, data.results);
  }
  
  // Add to the actions panel
  agentActions.appendChild(actionItem);
  agentActions.scrollTop = agentActions.scrollHeight;
  
  // Add to chat history for persistence
  addToChatHistory(type, title, content, data);
  
  return actionItem;
}

/**
 * Create an action item element
 * @param {string} type Action type
 * @param {string} title Action title
 * @param {string} content Action content
 * @param {Object} data Additional data
 * @returns {HTMLElement} The action item element
 */
function createActionItem(type, title, content, data) {
  const actionId = `action-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
  const actionItem = document.createElement('div');
  
  actionItem.className = `action-item ${type}-action`;
  actionItem.id = actionId;
  
  if (data.toolUseId) {
    actionItem.dataset.toolUseId = data.toolUseId;
  }
  
  const config = ACTION_CONFIG[type] || ACTION_CONFIG.system;
  const timeString = new Date().toLocaleTimeString();
  
  actionItem.innerHTML = `
    <div class="action-header">
      <span class="action-icon">${config.icon}</span>
      <span class="action-title">${title}</span>
    </div>
    <div class="action-content">${content}</div>
    <div class="action-time">${timeString}</div>
  `;
  
  return actionItem;
}

/**
 * Add search results to an action item
 * @param {HTMLElement} actionItem The action item element
 * @param {Array} results Array of search results
 */
function addSearchResults(actionItem, results) {
  const resultsContainer = document.createElement('div');
  resultsContainer.className = 'search-results';
  
  // Add toggle button
  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'toggle-results';
  toggleBtn.textContent = '▼ Hide Results';
  toggleBtn.onclick = () => window.toggleSearchResults(actionItem.id);
  
  // Add results counter
  const resultsCounter = document.createElement('div');
  resultsCounter.className = 'results-counter';
  resultsCounter.textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;
  
  actionItem.appendChild(toggleBtn);
  actionItem.appendChild(resultsCounter);
  
  // Add individual results
  results.forEach((result, index) => {
    if (!result) return;
    
    const resultId = `result-${actionItem.id}-${index}`;
    const resultEl = document.createElement('div');
    resultEl.className = 'search-result';
    resultEl.id = resultId;
    
    resultEl.innerHTML = `
      <div class="result-header">
        <div class="result-title">${result.metadata?.title || `Result ${index + 1}`}</div>
        <button class="copy-btn" onclick="window.copyResultContent('${resultId}')">Copy</button>
      </div>
      <div class="result-content">${truncateText(result.content, 150)}</div>
      <div class="result-meta">
        <span>Source: ${result.metadata?.source || 'Unknown'}</span>
        <span>Relevance: ${(result.score * 100).toFixed(1)}%</span>
      </div>
    `;
    
    resultsContainer.appendChild(resultEl);
  });
  
  actionItem.appendChild(resultsContainer);
}

/**
 * Add action to chat history
 * @param {string} type Action type
 * @param {string} title Action title
 * @param {string} content Action content
 * @param {Object} data Additional data
 */
function addToChatHistory(type, title, content, data) {
  const chatHistoryManager = ChatHistoryManager.getInstance();
  if (chatHistoryManager?.addAction) {
    chatHistoryManager.addAction({
      type,
      title,
      content,
      hasResults: type === 'result' && data.results?.length > 0,
      resultCount: data.results?.length || 0
    });
  }
}

/**
 * Truncate text to a specified length
 * @param {string} text The text to truncate
 * @param {number} maxLength The maximum length
 * @returns {string} The truncated text
 */
function truncateText(text, maxLength) {
  if (!text) return "No content available";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Update the insights panel with current statistics
 */
export function updateInsights() {
  const updates = [
    { id: 'turn-counter', value: analytics.conversationTurns },
    { id: 'search-counter', value: analytics.searchCount },
    { id: 'off-topic-counter', value: analytics.offTopicCount },
    { id: 'emergency-counter', value: analytics.emergencyCount },
    { id: 'medical-advice-counter', value: analytics.medicalAdviceCount }
  ];
  
  updates.forEach(({ id, value }) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

// Analytics increment functions
export function incrementConversationTurns() {
  analytics.conversationTurns++;
  updateInsights();
}

export function incrementSearchCount() {
  analytics.searchCount++;
  updateInsights();
}

export function incrementOffTopicCount() {
  analytics.offTopicCount++;
  updateInsights();
}

export function incrementEmergencyCount() {
  analytics.emergencyCount++;
  updateInsights();
}

export function incrementMedicalAdviceCount() {
  analytics.medicalAdviceCount++;
  updateInsights();
}

// Getters for analytics
export function getConversationTurns() {
  return analytics.conversationTurns;
}

export function getSearchCount() {
  return analytics.searchCount;
}