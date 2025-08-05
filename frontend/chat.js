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
            option.title = workspace.description || '';
            this.workspaceSelect.appendChild(option);
        });
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
            const workspaceName = this.workspaceSelect.options[this.workspaceSelect.selectedIndex].text;
            this.currentWorkspaceSpan.textContent = workspaceName;
        } else {
            this.currentWorkspaceSpan.textContent = 'None selected';
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
            this.updateRecentSources(data.relevant_docs);

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
        this.scrollToBottom();
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
            this.recentSourcesDiv.innerHTML = '<p class="no-sources">No sources found</p>';
            return;
        }

        this.recentSourcesDiv.innerHTML = '';
        sources.forEach(source => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'source-item';
            sourceDiv.innerHTML = `
                <div class="source-title">${source.s3_key}</div>
                <div class="source-score">Relevance: ${(source.score * 100).toFixed(1)}%</div>
            `;
            this.recentSourcesDiv.appendChild(sourceDiv);
        });
    }

    updateMessageCount() {
        const userMessages = this.conversation.filter(msg => msg.role === 'user').length;
        this.messageCountSpan.textContent = userMessages;
    }

    clearConversation() {
        if (confirm('Are you sure you want to clear the conversation?')) {
            this.conversation = [];
            this.chatMessages.innerHTML = '';
            this.recentSourcesDiv.innerHTML = '<p class="no-sources">No sources yet</p>';
            this.updateMessageCount();
            
            if (this.currentWorkspace) {
                this.showSystemMessage('Conversation cleared. You can start a new conversation.');
            }
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize the chat interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
}); 