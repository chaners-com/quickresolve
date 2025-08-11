class ChatInterface {
    constructor() {
        this.currentWorkspace = null;
        this.conversation = [];
        this.aiAgentUrl = '/api/ai-agent';
        
        this.initializeElements();
        this.bindEvents();
        this.loadWorkspaces();
        this.updateCurrentTime();
        
        // Update time every minute
        setInterval(() => this.updateCurrentTime(), 60000);
    }

    initializeElements() {
        this.workspaceSelect = document.getElementById('workspaceSelect');
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearChatButton = document.getElementById('clearChat');
        this.currentWorkspaceSpan = document.getElementById('currentWorkspace');
        this.messageCountSpan = document.getElementById('messageCount');
        this.recentSourcesDiv = document.getElementById('recentSources');
        
        // Additional workspace info elements
        this.workspaceDescriptionSpan = document.getElementById('workspaceDescription');
        
        // Document viewer elements
        this.documentModal = document.getElementById('documentModal');
        this.closeDocumentModal = document.getElementById('closeDocumentModal');
        this.documentTitle = document.getElementById('documentTitle');
        this.documentSource = document.getElementById('documentSource');
        this.documentRelevance = document.getElementById('documentRelevance');
        this.documentWorkspace = document.getElementById('documentWorkspace');
        this.documentText = document.getElementById('documentText');
        this.viewAllSourcesBtn = document.getElementById('viewAllSources');
    }

    bindEvents() {
        this.workspaceSelect.addEventListener('change', (e) => this.onWorkspaceChange(e));
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.messageInput.addEventListener('input', () => this.adjustTextareaHeight());
        this.clearChatButton.addEventListener('click', () => this.clearConversation());
        
        // Document viewer events
        this.closeDocumentModal.addEventListener('click', () => this.hideDocumentModal());
        this.viewAllSourcesBtn.addEventListener('click', () => this.showAllSources());
        
        // Close document modal when clicking outside
        this.documentModal.addEventListener('click', (e) => {
            if (e.target === this.documentModal) {
                this.hideDocumentModal();
            }
        });
    }

    async loadWorkspaces() {
        try {
            const response = await fetch(`${this.aiAgentUrl}/workspaces`);
            if (!response.ok) throw new Error('Failed to load workspaces');
            
            const workspaces = await response.json();
            this.populateWorkspaceSelect(workspaces);
        } catch (error) {
            console.error('Error loading workspaces:', error);
            this.showSystemMessage('Error loading workspaces. Please refresh the page.');
        }
    }

    populateWorkspaceSelect(workspaces) {
        this.workspaceSelect.innerHTML = '<option value="">Choose a workspace...</option>';
        
        workspaces.forEach(workspace => {
            const option = document.createElement('option');
            option.value = workspace.workspace_id;
            option.textContent = workspace.name;
            option.title = workspace.description || `Workspace: ${workspace.name}`;
            this.workspaceSelect.appendChild(option);
        });
        
        // If there are workspaces, show a helpful message
        if (workspaces.length > 0) {
            this.showSystemMessage(`Loaded ${workspaces.length} workspace(s). Select one to start chatting!`);
        } else {
            this.showSystemMessage('No workspaces available. Please contact your administrator to create workspaces or upload documents to existing workspaces.');
        }
    }

    onWorkspaceChange(event) {
        const workspaceId = parseInt(event.target.value);
        if (workspaceId) {
            this.currentWorkspace = workspaceId;
            this.enableChat();
            this.updateWorkspaceInfo();
            this.showSystemMessage(`Switched to workspace: ${event.target.options[event.target.selectedIndex].text}`);
        } else {
            this.currentWorkspace = null;
            this.disableChat();
            this.updateWorkspaceInfo();
        }
    }

    enableChat() {
        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        this.messageInput.placeholder = 'Type your message here...';
    }

    disableChat() {
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        this.messageInput.placeholder = 'Please select a workspace first...';
    }

    updateWorkspaceInfo() {
        if (this.currentWorkspace) {
            const selectedOption = this.workspaceSelect.options[this.workspaceSelect.selectedIndex];
            const workspaceName = selectedOption.text;
            const workspaceDescription = selectedOption.title;
            
            this.currentWorkspaceSpan.textContent = workspaceName;
            this.workspaceDescriptionSpan.textContent = workspaceDescription;
        } else {
            this.currentWorkspaceSpan.textContent = 'None selected';
            this.workspaceDescriptionSpan.textContent = '-';
        }
    }

    updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        document.getElementById('currentTime').textContent = timeString;
    }

    adjustTextareaHeight() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.currentWorkspace) return;

        // Add user message to chat
        this.addMessage('user', message);
        this.conversation.push({ role: 'user', content: message });

        // Clear input
        this.messageInput.value = '';
        this.adjustTextareaHeight();

        // Show typing indicator
        const typingIndicator = this.showTypingIndicator();

        try {
            // Send to AI agent
            const response = await fetch(`${this.aiAgentUrl}/conversation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: this.conversation,
                    workspace_id: this.currentWorkspace
                })
            });

            if (!response.ok) throw new Error('Failed to get response from AI agent');

            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();

            // Add AI response
            this.addMessage('assistant', data.response);
            this.conversation.push({ role: 'assistant', content: data.response });

            // Update sources
            if (data.relevant_docs && data.relevant_docs.length > 0) {
                this.updateRecentSources(data.relevant_docs);
                this.showSystemMessage(`Retrieved ${data.relevant_docs.length} relevant document(s) for your question.`);
            } else {
                this.updateRecentSources([]);
                this.showSystemMessage('No specific documents were retrieved for this question.');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            typingIndicator.remove();
            this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        }

        this.updateMessageCount();
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);

        this.chatMessages.appendChild(messageDiv);
        // Use microtask to ensure layout is updated before scrolling
        Promise.resolve().then(() => this.scrollToBottom());
    }

    showSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;

        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
        return typingDiv;
    }

    updateRecentSources(sources) {
        if (!sources || sources.length === 0) {
            this.recentSourcesDiv.innerHTML = '<p class="no-sources">No documents retrieved</p>';
            this.viewAllSourcesBtn.disabled = true;
            this.updateSourcesCount(0);
            return;
        }

        this.recentSourcesDiv.innerHTML = '';
        this.updateSourcesCount(sources.length);
        this.viewAllSourcesBtn.disabled = false;
        
        sources.forEach((source, index) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'source-item';
            sourceDiv.dataset.sourceIndex = index;
            
            // Create a preview of the content (first 100 characters)
            const preview = source.content ? 
                source.content.substring(0, 100) + (source.content.length > 100 ? '...' : '') :
                'No content preview available';
            
            sourceDiv.innerHTML = `
                <div class="source-title">${this.formatSourceName(source.s3_key || 'Unknown source')}</div>
                <div class="source-score">Relevance: ${(source.score * 100).toFixed(1)}%</div>
                <div class="source-preview">${preview}</div>
            `;
            
            // Make the source item clickable to view full content
            sourceDiv.addEventListener('click', () => this.showDocumentContent(source, index));
            
            this.recentSourcesDiv.appendChild(sourceDiv);
        });
    }

    updateSourcesCount(count) {
        const sourcesCountElement = document.querySelector('.sources-count');
        if (sourcesCountElement) {
            sourcesCountElement.textContent = `${count} document${count !== 1 ? 's' : ''}`;
        }
    }

    updateMessageCount() {
        const userMessages = this.conversation.filter(msg => msg.role === 'user').length;
        this.messageCountSpan.textContent = userMessages;
    }

    formatSourceName(s3Key) {
        const parts = s3Key.split('/');
        return parts[parts.length - 1];
    }

    showDocumentContent(source, index) {
        this.documentTitle.textContent = this.formatSourceName(source.s3_key);
        this.documentSource.textContent = `Source: ${this.formatSourceName(source.s3_key)}`;
        this.documentRelevance.textContent = `Relevance: ${(source.score * 100).toFixed(1)}%`;
        this.documentWorkspace.textContent = `Workspace: ${source.workspace_name}`;
        this.documentText.textContent = source.content || 'No content available for this document.';
        this.documentModal.style.display = 'block';
        this.scrollToBottom();
    }

    hideDocumentModal() {
        this.documentModal.style.display = 'none';
    }

    showAllSources() {
        // Show a summary of all retrieved documents
        const sources = this.recentSourcesDiv.querySelectorAll('.source-item');
        if (sources.length === 0) {
            this.showSystemMessage('No documents have been retrieved yet.');
            return;
        }
        
        let summary = `Retrieved ${sources.length} document(s):\n\n`;
        sources.forEach((source, index) => {
            const title = source.querySelector('.source-title').textContent;
            const score = source.querySelector('.source-score').textContent;
            summary += `${index + 1}. ${title} (${score})\n`;
        });
        
        // Show the summary in the modal
        this.documentTitle.textContent = 'Retrieved Documents Summary';
        this.documentSource.textContent = `Total: ${sources.length} document(s)`;
        this.documentRelevance.textContent = `Current conversation`;
        this.documentWorkspace.textContent = `Workspace: ${this.currentWorkspace ? this.workspaceSelect.options[this.workspaceSelect.selectedIndex].text : 'Unknown'}`;
        this.documentText.textContent = summary;
        this.documentModal.style.display = 'block';
    }

    clearConversation() {
        if (confirm('Are you sure you want to clear the conversation?')) {
            this.conversation = [];
            this.chatMessages.innerHTML = '';
            this.recentSourcesDiv.innerHTML = '<p class="no-sources">No documents retrieved yet</p>';
            this.updateSourcesCount(0);
            this.viewAllSourcesBtn.disabled = true;
            this.updateMessageCount();
            
            if (this.currentWorkspace) {
                this.showSystemMessage('Conversation cleared. You can start a new conversation.');
            }
        }
    }

    scrollToBottom() {
        const last = this.chatMessages.lastElementChild;
        if (last && last.scrollIntoView) {
            last.scrollIntoView({ behavior: 'smooth', block: 'end' });
        } else {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
}

// Initialize the chat interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
}); 