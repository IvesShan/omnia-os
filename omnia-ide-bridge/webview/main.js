// @ts-nocheck
// Omnia AI Chat Panel - VSCode Webview Script

(function () {
    'use strict';

    // ============================================================
    // VSCode API
    // ============================================================
    const vscode = acquireVsCodeApi();

    // ============================================================
    // DOM Elements
    // ============================================================
    const messagesContainer = document.getElementById('messages');
    const input = document.getElementById('input');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');
    const contextBtn = document.getElementById('contextBtn');
    const contextBar = document.getElementById('contextBar');
    const contextInfo = document.getElementById('contextInfo');

    // ============================================================
    // State
    // ============================================================
    let messages = [];
    let isStreaming = false;
    let currentResponse = '';
    let includeContext = true;

    // ============================================================
    // Initialize
    // ============================================================
    function init() {
        showWelcome();
        setupEventListeners();
        vscode.postMessage({ command: 'ready' });
    }

    function showWelcome() {
        messagesContainer.innerHTML = `
            <div class="welcome">
                <h2>🧠 Omnia AI Assistant</h2>
                <p>I can help you with coding, debugging, refactoring, and more.</p>
                <div class="shortcuts">
                    <div class="shortcut">
                        <span class="key">/explain</span>
                        <span class="desc">Explain selected code</span>
                    </div>
                    <div class="shortcut">
                        <span class="key">/fix</span>
                        <span class="desc">Find and fix issues</span>
                    </div>
                    <div class="shortcut">
                        <span class="key">/commit</span>
                        <span class="desc">Generate commit message</span>
                    </div>
                    <div class="shortcut">
                        <span class="key">/test</span>
                        <span class="desc">Generate unit tests</span>
                    </div>
                </div>
                <p style="margin-top: 16px;">Select code in editor → Right-click → Ask Omnia</p>
            </div>
        `;
    }

    // ============================================================
    // Event Listeners
    // ============================================================
    function setupEventListeners() {
        // Send button
        sendBtn.addEventListener('click', handleSend);

        // Enter to send (Shift+Enter for new line)
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });

        // Clear button
        clearBtn.addEventListener('click', () => {
            messages = [];
            showWelcome();
            vscode.postMessage({ command: 'clearChat' });
        });

        // Context toggle
        contextBtn.addEventListener('click', () => {
            includeContext = !includeContext;
            contextBtn.style.opacity = includeContext ? '1' : '0.5';
            vscode.postMessage({ command: 'toggleContext', enabled: includeContext });
        });

        // Hint clicks
        document.querySelectorAll('.hint').forEach(hint => {
            hint.addEventListener('click', () => {
                input.value = hint.textContent + ' ';
                input.focus();
            });
        });

        // Listen for messages from extension
        window.addEventListener('message', handleExtensionMessage);
    }

    // ============================================================
    // Message Handling
    // ============================================================
    function handleExtensionMessage(event) {
        const message = event.data;

        switch (message.command) {
            case 'startResponse':
                startStreamingResponse();
                break;
            case 'appendResponse':
                appendResponse(message.text);
                break;
            case 'endResponse':
                endStreamingResponse();
                break;
            case 'error':
                showError(message.text);
                break;
            case 'updateContext':
                updateContext(message.info, message.hasSelection);
                break;
            case 'autoSend':
                autoSend(message.text);
                break;
            case 'insertText':
                insertText(message.text);
                break;
        }
    }

    function handleSend() {
        const text = input.value.trim();
        if (!text || isStreaming) return;

        // Clear welcome if first message
        if (messages.length === 0) {
            messagesContainer.innerHTML = '';
        }

        // Add user message
        addMessage('user', text);

        // Clear input
        input.value = '';
        input.style.height = 'auto';

        // Send to extension
        vscode.postMessage({
            command: 'sendMessage',
            text: text,
            includeContext: includeContext
        });
    }

    function autoSend(text) {
        if (messages.length === 0) {
            messagesContainer.innerHTML = '';
        }

        addMessage('user', text);

        vscode.postMessage({
            command: 'sendMessage',
            text: text,
            includeContext: true
        });
    }

    function insertText(text) {
        input.value += text;
        input.focus();
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    // ============================================================
    // Message Display
    // ============================================================
    function addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        headerDiv.textContent = role === 'user' ? 'You' : 'Omnia AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = formatContent(content);

        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Add code copy buttons
        addCopyButtons(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        messages.push({ role, content });
    }

    function formatContent(text) {
        // Simple markdown-like formatting
        let html = escapeHtml(text);

        // Code blocks
        html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<div class="code-block">
                <div class="code-header">
                    <span>${lang || 'code'}</span>
                    <button class="copy-btn" data-code="${escapeHtml(code.trim())}">📋 Copy</button>
                </div>
                <pre class="code-content"><code>${code.trim()}</code></pre>
            </div>`;
        });

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color: var(--accent);">$1</a>');

        return html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function addCopyButtons(container) {
        container.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const code = btn.getAttribute('data-code');
                navigator.clipboard.writeText(code).then(() => {
                    btn.textContent = '✅ Copied!';
                    setTimeout(() => {
                        btn.textContent = '📋 Copy';
                    }, 2000);
                });
            });
        });
    }

    // ============================================================
    // Streaming Response
    // ============================================================
    function startStreamingResponse() {
        isStreaming = true;
        currentResponse = '';

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.id = 'streaming-message';

        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        headerDiv.textContent = 'Omnia AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';

        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        sendBtn.disabled = true;
        sendBtn.style.opacity = '0.5';
    }

    function appendResponse(text) {
        const messageDiv = document.getElementById('streaming-message');
        if (!messageDiv) return;

        currentResponse += text;

        const contentDiv = messageDiv.querySelector('.message-content');
        contentDiv.innerHTML = formatContent(currentResponse);
        addCopyButtons(contentDiv);

        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function endStreamingResponse() {
        const messageDiv = document.getElementById('streaming-message');
        if (messageDiv) {
            messageDiv.removeAttribute('id');
        }

        messages.push({ role: 'assistant', content: currentResponse });

        isStreaming = false;
        currentResponse = '';

        sendBtn.disabled = false;
        sendBtn.style.opacity = '1';
    }

    function showError(text) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = text;
        messagesContainer.appendChild(errorDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        isStreaming = false;
        sendBtn.disabled = false;
        sendBtn.style.opacity = '1';
    }

    // ============================================================
    // Context
    // ============================================================
    function updateContext(info, hasSelection) {
        contextInfo.textContent = info;
        if (hasSelection) {
            contextInfo.textContent += ' (with selection)';
        }
    }

    // ============================================================
    // Start
    // ============================================================
    init();
})();
