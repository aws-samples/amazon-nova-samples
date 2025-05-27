// ui-manager.js
// Centralized UI management and event handling

export class UIManager {
  static DOM = null;

  /**
   * Initialize UI event handlers
   * @param {Object} domElements - Object containing DOM element references
   */
  static initialize(domElements) {
    this.DOM = domElements;
    this.setupEventListeners();
    this.setupPanelToggle();
  }

  /**
   * Setup all UI event listeners
   */
  static setupEventListeners() {
    // Filter button event listeners
    this.DOM.filterButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.filterAgentActions(e.target.dataset.filter);
      });
    });

    // Make functions globally accessible for dynamically created elements
    window.toggleSearchResults = this.toggleSearchResults.bind(this);
    window.copyResultContent = this.copyResultContent.bind(this);
    window.toggleAgentPanel = this.toggleAgentPanel.bind(this);
  }

  /**
   * Setup panel toggle functionality
   */
  static setupPanelToggle() {
    const toggleBtn = document.getElementById('toggle-panel-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', this.toggleAgentPanel.bind(this));
    }
  }

  /**
   * Toggle agent panel visibility
   */
  static toggleAgentPanel() {
    const contentContainer = document.getElementById('content-container');
    const toggleBtn = document.getElementById('toggle-panel-btn');
    
    if (!contentContainer || !toggleBtn) return;

    contentContainer.classList.toggle('agent-panel-hidden');
    const isHidden = contentContainer.classList.contains('agent-panel-hidden');
    const span = toggleBtn.querySelector('span');
    
    if (span) {
      span.textContent = isHidden ? '👁️' : '✕';
    }
  }

  /**
   * Toggle search results visibility
   * @param {string} actionItemId - ID of the action item
   */
  static toggleSearchResults(actionItemId) {
    const actionItem = document.getElementById(actionItemId);
    if (!actionItem) return;
    
    const resultsContainer = actionItem.querySelector('.search-results');
    const toggleBtn = actionItem.querySelector('.toggle-results');
    
    if (!resultsContainer || !toggleBtn) return;
    
    const isHidden = resultsContainer.style.display === 'none';
    resultsContainer.style.display = isHidden ? 'block' : 'none';
    toggleBtn.textContent = isHidden ? '▼ Hide Results' : '▶ Show Results';
  }

  /**
   * Copy result content to clipboard
   * @param {string} resultId - ID of the result item
   */
  static async copyResultContent(resultId) {
    const resultItem = document.getElementById(resultId);
    if (!resultItem) return;
    
    const contentElement = resultItem.querySelector('.result-content');
    if (!contentElement) return;

    const content = contentElement.textContent;
    const copyBtn = resultItem.querySelector('.copy-btn');
    
    try {
      await navigator.clipboard.writeText(content);
      
      if (copyBtn) {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
          copyBtn.textContent = originalText;
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to copy text:', err);
      // Fallback for older browsers
      this.fallbackCopyToClipboard(content);
    }
  }

  /**
   * Fallback copy method for older browsers
   * @param {string} text - Text to copy
   */
  static fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      console.log('Text copied using fallback method');
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }
    
    document.body.removeChild(textArea);
  }

  /**
   * Filter agent actions by type
   * @param {string} type - Filter type ('all', 'search', 'result', 'system', etc.)
   */
  static filterAgentActions(type) {
    const actionItems = document.querySelectorAll('.action-item');
    
    actionItems.forEach(item => {
      const shouldShow = type === 'all' || item.classList.contains(`${type}-action`);
      item.style.display = shouldShow ? 'block' : 'none';
    });
    
    // Update active filter button
    this.DOM.filterButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === type);
    });
  }
}