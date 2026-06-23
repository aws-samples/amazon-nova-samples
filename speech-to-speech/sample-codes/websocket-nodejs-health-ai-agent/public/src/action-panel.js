// src/action-panel.js
// Manages the agent actions panel functionality

import { ChatHistoryManager } from "./lib/util/ChatHistoryManager.js";

// Constants for action types and their corresponding Font Awesome class names
const ACTION_CONFIG = {
  system: { iconClass: 'fas fa-cog', label: 'System' },
  user: { iconClass: 'fas fa-user', label: 'User' },
  search: { iconClass: 'fas fa-search', label: 'Search' },
  result: { iconClass: 'fas fa-file-alt', label: 'Result' },
  error: { iconClass: 'fas fa-exclamation-triangle', label: 'Error' },
  emergency: { iconClass: 'fas fa-ambulance', label: 'Emergency' },
  'off-topic': { iconClass: 'fas fa-ban', label: 'Off-Topic' }
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
 * Update the agent status UI safely (no innerHTML)
 */
export function updateAgentStatusUI(status, text) {
  if (!agentStatus) return;

  agentStatus.className = `agent-status ${status}`;
  if (['thinking', 'processing', 'searching'].includes(status)) {
    agentStatus.classList.add('thinking-status');
  }

  let statusTextEl = agentStatus.querySelector('.status-text');
  if (!statusTextEl) {
    const dot = document.createElement('span');
    dot.className = 'status-dot';
    const textEl = document.createElement('span');
    textEl.className = 'status-text';
    textEl.textContent = text;
    agentStatus.appendChild(dot);
    agentStatus.appendChild(textEl);
  } else {
    statusTextEl.textContent = text;
  }
}

/**
 * Add an action to the agent panel
 */
export function addAgentAction(type, title, content, data = {}) {
  if (!agentActions) {
    console.error('Agent actions container not found');
    return null;
  }
  const placeholder = agentActions.querySelector('.action-placeholder');
  if (placeholder) placeholder.remove();
  const actionItem = createActionItem(type, title, content, data);
  if (type === 'result' && data.results?.length) addSearchResults(actionItem, data.results);
  agentActions.appendChild(actionItem);
  agentActions.scrollTop = agentActions.scrollHeight;
  addToChatHistory(type, title, content, data);
  return actionItem;
}

function createActionItem(type, title, content, data) {
  const actionItem = document.createElement('div');
  actionItem.className = `action-item ${type}-action`;
  actionItem.id = `action-${Date.now()}-${Math.floor(Math.random()*1000)}`;
  if (data.toolUseId) actionItem.dataset.toolUseId = data.toolUseId;

  const cfg = ACTION_CONFIG[type] ?? ACTION_CONFIG.system;
  const header = document.createElement('div');
  header.className = 'action-header';

  const iconSpan = document.createElement('span');
  iconSpan.className = 'action-icon';
  const iconEl = document.createElement('i');
  iconEl.className = cfg.iconClass; // constant, safe
  iconSpan.appendChild(iconEl);

  const titleSpan = document.createElement('span');
  titleSpan.className = 'action-title';
  titleSpan.textContent = title;

  header.appendChild(iconSpan);
  header.appendChild(titleSpan);
  actionItem.appendChild(header);

  const contentDiv = document.createElement('div');
  contentDiv.className = 'action-content';
  contentDiv.textContent = content;
  actionItem.appendChild(contentDiv);

  const timeDiv = document.createElement('div');
  timeDiv.className = 'action-time';
  timeDiv.textContent = new Date().toLocaleTimeString();
  actionItem.appendChild(timeDiv);

  return actionItem;
}

function addSearchResults(actionItem, results) {
  const resultsContainer = document.createElement('div');
  resultsContainer.className = 'search-results';

  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'toggle-results';
  toggleBtn.textContent = '▼ Hide Results';
  toggleBtn.addEventListener('click', () => window.toggleSearchResults(actionItem.id));
  resultsContainer.appendChild(toggleBtn);

  const counter = document.createElement('div');
  counter.className = 'results-counter';
  counter.textContent = `${results.length} result${results.length!==1?'s':''}`;
  resultsContainer.appendChild(counter);

  results.forEach((res, idx)=>{
    if(!res) return;
    const resEl=document.createElement('div');
    resEl.className='search-result';
    resEl.id=`result-${actionItem.id}-${idx}`;

    const header=document.createElement('div');
    header.className='result-header';
    const title=document.createElement('div');
    title.className='result-title';
    title.textContent=res.metadata?.title||`Result ${idx+1}`;
    const copy=document.createElement('button');
    copy.className='copy-btn';
    copy.textContent='Copy';
    copy.addEventListener('click',()=>window.copyResultContent(resEl.id));
    header.appendChild(title);
    header.appendChild(copy);
    resEl.appendChild(header);

    const content=document.createElement('div');
    content.className='result-content';
    content.textContent=truncateText(res.content,150);
    resEl.appendChild(content);

    const meta=document.createElement('div');
    meta.className='result-meta';
    const srcSpan=document.createElement('span');
    srcSpan.textContent=`Source: ${res.metadata?.source||'Unknown'}`;
    const relSpan=document.createElement('span');
    relSpan.textContent=`Relevance: ${(res.score*100).toFixed(1)}%`;
    meta.appendChild(srcSpan);
    meta.appendChild(relSpan);
    resEl.appendChild(meta);

    resultsContainer.appendChild(resEl);
  });

  actionItem.appendChild(resultsContainer);
}

function addToChatHistory(type,title,content,data){
  const mgr=ChatHistoryManager.getInstance();
  mgr?.addAction?.({type,title,content,hasResults:type==='result'&&data.results?.length>0,resultCount:data.results?.length||0});
}

function truncateText(text,max){
  if(!text) return 'No content available';
  return text.length<=max?text:text.substring(0,max)+'...';
}

export function updateInsights(){
  [
    ['turn-counter',analytics.conversationTurns],
    ['search-counter',analytics.searchCount],
    ['off-topic-counter',analytics.offTopicCount],
    ['emergency-counter',analytics.emergencyCount],
    ['medical-advice-counter',analytics.medicalAdviceCount]
  ].forEach(([id,val])=>{const el=document.getElementById(id);if(el) el.textContent=val;});
}

export function incrementConversationTurns(){analytics.conversationTurns++;updateInsights();}
export function incrementSearchCount(){analytics.searchCount++;updateInsights();}
export function incrementOffTopicCount(){analytics.offTopicCount++;updateInsights();}
export function incrementEmergencyCount(){analytics.emergencyCount++;updateInsights();}
export function incrementMedicalAdviceCount(){analytics.medicalAdviceCount++;updateInsights();}

export function getConversationTurns(){return analytics.conversationTurns;}
export function getSearchCount(){return analytics.searchCount;}