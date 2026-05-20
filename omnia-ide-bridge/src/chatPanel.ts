import * as vscode from 'vscode';
import * as http from 'http';
import * as path from 'path';

// ============================================================
// Types
// ============================================================

interface IdeContext {
    file: string | null;
    language: string | null;
    line: number | null;
    column: number | null;
    selectedText: string;
    timestamp: number;
    fullContent?: string;
}

// ============================================================
// Chat Panel — Agent Mode (v1.0.0)
// ============================================================

export class OmniaChatPanel {
    public static currentPanel: OmniaChatPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _chatHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [];
    private _currentContext: IdeContext | null = null;
    private _isProcessing = false;

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._panel.webview.html = this._getHtmlContent();
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.command) {
                    case 'sendMessage':
                        await this._handleUserMessage(message.text);
                        break;
                    case 'clearHistory':
                        this._chatHistory = [];
                        this._panel.webview.postMessage({ command: 'clearMessages' });
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.ViewColumn.Two;

        if (OmniaChatPanel.currentPanel) {
            OmniaChatPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'omniaChat',
            'Omnia AI 助手',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri],
            }
        );

        OmniaChatPanel.currentPanel = new OmniaChatPanel(panel, extensionUri);
    }

    public updateContext(context: IdeContext) {
        this._currentContext = context;
    }

    public dispose() {
        OmniaChatPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const d = this._disposables.pop();
            if (d) d.dispose();
        }
    }

    private _resetWebviewState() {
        try {
            this._panel.webview.postMessage({
                command: 'endAssistant',
                fullContent: '',
                toolCalls: 0,
                rounds: 0,
            });
        } catch {
            // webview may have been disposed
        }
    }

    private _buildIdeContextPrefix(): string {
        // Build a rich context prefix that tells Omnia about the VSCode environment
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const projectName = workspaceFolder ? path.basename(workspaceFolder.uri.fsPath) : '未知项目';
        const workspacePath = workspaceFolder?.uri.fsPath || '未知路径';
        const editor = vscode.window.activeTextEditor;
        
        let prefix = '---\n';
        prefix += '[系统提示] 以下消息来自 VSCode IDE 扩展 (Omnia IDE Bridge)\n';
        prefix += `当前项目: ${projectName}\n`;
        prefix += `项目路径: ${workspacePath}\n`;
        prefix += `操作系统: ${process.platform}\n`;
        
        if (editor) {
            const doc = editor.document;
            const pos = editor.selection.active;
            const selected = editor.selection.isEmpty ? '' : doc.getText(editor.selection);
            
            prefix += `当前文件: ${path.basename(doc.fileName)}\n`;
            prefix += `文件路径: ${doc.fileName}\n`;
            prefix += `语言: ${doc.languageId}\n`;
            prefix += `光标位置: 第${pos.line + 1}行, 第${pos.character + 1}列\n`;
            
            if (selected) {
                const maxLen = 500;
                const truncated = selected.length > maxLen ? selected.slice(0, maxLen) + '...' : selected;
                prefix += `\n用户选中的代码:\n\`\`\`${doc.languageId}\n${truncated}\n\`\`\`\n`;
            }
        }
        
        // Also include IDE context from extension.ts if available
        if (this._currentContext) {
            const ctx = this._currentContext;
            if (ctx.file) {
                prefix += `IDE上下文文件: ${path.basename(ctx.file)}\n`;
            }
            if (ctx.fullContent && ctx.fullContent.length > 0) {
                const maxLen = 3000;
                const content = ctx.fullContent.length > maxLen ? ctx.fullContent.slice(0, maxLen) + '\n... (已截断)' : ctx.fullContent;
                prefix += `\n当前文件完整内容:\n\`\`\`${ctx.language || ''}\n${content}\n\`\`\`\n`;
            }
        }
        
        prefix += '---\n\n';
        return prefix;
    }

    private async _handleUserMessage(text: string) {
        if (this._isProcessing) {
            return;
        }
        this._isProcessing = true;

        this._chatHistory.push({ role: 'user', content: text });
        this._panel.webview.postMessage({ command: 'addMessage', role: 'user', content: text });
        this._panel.webview.postMessage({ command: 'startAssistant' });

        // Build the full prompt with IDE context
        const ideContextPrefix = this._buildIdeContextPrefix();
        const fullPrompt = ideContextPrefix + text;

        let fullResponse = '';
        let toolCallsCount = 0;
        let roundsCount = 0;

        const timeoutId = setTimeout(() => {
            if (this._isProcessing) {
                this._isProcessing = false;
                this._resetWebviewState();
            }
        }, 90000);

        try {
            const streamSupported = await this._checkStreamSupport();

            if (streamSupported) {
                await this._callOmniaAgentStream(fullPrompt, {
                    onToken: (chunk) => {
                        fullResponse += chunk;
                        this._panel.webview.postMessage({ command: 'streamToken', content: chunk });
                    },
                    onStatus: (msg) => {
                        this._panel.webview.postMessage({ command: 'agentStatus', message: msg });
                    },
                    onToolCall: (name, args) => {
                        toolCallsCount++;
                        this._panel.webview.postMessage({
                            command: 'toolCall',
                            name,
                            args: JSON.stringify(args),
                        });
                    },
                    onToolResult: (name, result) => {
                        this._panel.webview.postMessage({
                            command: 'toolResult',
                            name,
                            content: result,
                            success: true,
                        });
                    },
                    onToolError: (name, error) => {
                        this._panel.webview.postMessage({
                            command: 'toolResult',
                            name,
                            content: error,
                            success: false,
                        });
                    },
                    onDone: (content, stats) => {
                        if (content) {
                            fullResponse = content;
                        }
                        roundsCount = stats?.rounds_executed || 0;
                    },
                });
            } else {
                fullResponse = await this._callOmniaChatNormal(fullPrompt);
            }
        } catch (err: any) {
            fullResponse = '❌ 错误: ' + (err.message || String(err));
        } finally {
            clearTimeout(timeoutId);
            this._isProcessing = false;
        }

        this._panel.webview.postMessage({
            command: 'endAssistant',
            fullContent: fullResponse,
            toolCalls: toolCallsCount,
            rounds: roundsCount,
        });

        this._chatHistory.push({ role: 'assistant', content: fullResponse });

        if (this._chatHistory.length > 40) {
            this._chatHistory = this._chatHistory.slice(-40);
        }
    }

    private async _checkStreamSupport(): Promise<boolean> {
        const config = vscode.workspace.getConfiguration('omnia.ideBridge');
        const endpoint = config.get<string>('endpoint', 'http://127.0.0.1:8765');

        return new Promise((resolve) => {
            try {
                const url = new URL('/api/chat/stream', endpoint);
                const options = {
                    hostname: url.hostname,
                    port: parseInt(url.port || '8765'),
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    timeout: 3000,
                };

                const req = http.request(options, (res) => {
                    resolve(res.statusCode === 200);
                });

                req.on('error', () => resolve(false));
                req.on('timeout', () => {
                    req.destroy();
                    resolve(false);
                });

                req.write(JSON.stringify({ message: 'test' }));
                req.end();
            } catch {
                resolve(false);
            }
        });
    }

    private async _callOmniaChatNormal(prompt: string): Promise<string> {
        const config = vscode.workspace.getConfiguration('omnia.ideBridge');
        const endpoint = config.get<string>('endpoint', 'http://127.0.0.1:8765');

        return new Promise((resolve, reject) => {
            try {
                const url = new URL('/api/chat', endpoint);

                const postData = JSON.stringify({
                    message: prompt,
                    history: this._chatHistory,
                });

                const options = {
                    hostname: url.hostname,
                    port: parseInt(url.port || '8765'),
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData),
                    },
                    timeout: 60000,
                };

                const req = http.request(options, (res) => {
                    let data = '';

                    res.on('data', (chunk: Buffer) => {
                        data += chunk.toString();
                    });

                    res.on('end', () => {
                        try {
                            const json = JSON.parse(data);
                            resolve(json.response || json.message || data);
                        } catch {
                            resolve(data);
                        }
                    });
                });

                req.on('error', (err) => reject(err));
                req.on('timeout', () => {
                    req.destroy();
                    reject(new Error('请求超时'));
                });

                req.write(postData);
                req.end();
            } catch (err: any) {
                reject(err);
            }
        });
    }

    private async _callOmniaAgentStream(
        prompt: string,
        callbacks: {
            onToken: (chunk: string) => void;
            onStatus: (msg: string) => void;
            onToolCall: (name: string, args: any) => void;
            onToolResult: (name: string, result: string) => void;
            onToolError: (name: string, error: string) => void;
            onDone: (content: string, stats?: any) => void;
        }
    ): Promise<void> {
        const config = vscode.workspace.getConfiguration('omnia.ideBridge');
        const endpoint = config.get<string>('endpoint', 'http://127.0.0.1:8765');

        return new Promise((resolve, reject) => {
            try {
                const url = new URL('/api/chat/stream', endpoint);

                const postData = JSON.stringify({
                    message: prompt,
                    history: this._chatHistory,
                });

                const options = {
                    hostname: url.hostname,
                    port: parseInt(url.port || '8765'),
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData),
                    },
                    timeout: 60000,
                };

                let resolved = false;
                const safeResolve = () => {
                    if (!resolved) {
                        resolved = true;
                        resolve();
                    }
                };
                const safeReject = (err: Error) => {
                    if (!resolved) {
                        resolved = true;
                        reject(err);
                    }
                };

                const req = http.request(options, (res) => {
                    let buffer = '';

                    res.on('data', (chunk: Buffer) => {
                        buffer += chunk.toString();
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (!line.startsWith('data: ')) continue;
                            const data = line.slice(6).trim();
                            if (data === '[DONE]') {
                                safeResolve();
                                return;
                            }
                            try {
                                const event = JSON.parse(data);
                                this._handleAgentEvent(event, callbacks);
                            } catch {
                                // ignore parse errors
                            }
                        }
                    });

                    res.on('end', () => safeResolve());
                    res.on('error', (err) => safeReject(err));
                });

                req.on('error', (err) => safeReject(err));
                req.on('timeout', () => {
                    req.destroy();
                    safeReject(new Error('流式请求超时'));
                });

                req.write(postData);
                req.end();
            } catch (err: any) {
                reject(err);
            }
        });
    }

    private _handleAgentEvent(
        event: any,
        callbacks: {
            onToken: (chunk: string) => void;
            onStatus: (msg: string) => void;
            onToolCall: (name: string, args: any) => void;
            onToolResult: (name: string, result: string) => void;
            onToolError: (name: string, error: string) => void;
            onDone: (content: string, stats?: any) => void;
        }
    ) {
        const type = event.type;

        switch (type) {
            case 'token':
                if (event.content) {
                    callbacks.onToken(event.content);
                }
                break;

            case 'status':
                if (event.message) {
                    callbacks.onStatus(event.message);
                }
                break;

            case 'tool_call':
                callbacks.onToolCall(
                    event.name || '',
                    event.arguments || {}
                );
                break;

            case 'tool_result':
                callbacks.onToolResult(
                    event.name || '',
                    event.content || ''
                );
                break;

            case 'tool_error':
                callbacks.onToolError(
                    event.name || '',
                    event.content || ''
                );
                break;

            case 'safety_warning':
                callbacks.onStatus(
                    '⚠️ 安全警告 [' + event.name + ']: ' + event.reason
                );
                break;

            case 'validation_failed':
                callbacks.onStatus(
                    '⚠️ 验证失败: ' + event.reason
                );
                break;

            case 'preroll':
                if (event.content) {
                    callbacks.onStatus('📋 ' + event.content);
                }
                break;

            case 'done':
                callbacks.onDone(
                    event.full_content || '',
                    event.stats || {}
                );
                break;

            case 'error':
                callbacks.onStatus('❌ ' + (event.message || '未知错误'));
                break;

            case 'thinking':
                break;

            default:
                break;
        }
    }

    // ============================================================
    // HTML Content — Agent UI
    // Build the HTML by generating the JS code as a string
    // to avoid template literal escaping issues
    // ============================================================

    private _getHtmlContent(): string {
        // Build the JavaScript code as a separate string to avoid
        // backtick escaping issues inside template literals
        const jsCode = this._buildWebviewScript();

        return '<!DOCTYPE html>\n' +
            '<html lang="zh-CN">\n' +
            '<head>\n' +
            '    <meta charset="UTF-8">\n' +
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n' +
            '    <title>Omnia AI</title>\n' +
            '    <style>\n' +
            this._getStyles() +
            '    </style>\n' +
            '</head>\n' +
            '<body>\n' +
            '    <div class="header">\n' +
            '        <h2>🤖 Omnia AI Agent</h2>\n' +
            '        <div class="header-actions">\n' +
            '            <button id="clearBtn">清空</button>\n' +
            '        </div>\n' +
            '    </div>\n' +
            '\n' +
            '    <div class="context-info" id="contextInfo"></div>\n' +
            '\n' +
            '    <div class="messages" id="messages">\n' +
            '        <div class="welcome">\n' +
            '            <h3>👋 你好！我是 Omnia AI</h3>\n' +
            '            <p>我可以帮你写代码、修改文件、执行命令、管理 Git。</p>\n' +
            '\n' +
            '            <div class="features">\n' +
            '                <div class="feature-title">🧠 Agent 模式 — 我能直接操作你的项目</div>\n' +
            '                <div class="feature-item"><span class="icon">📂</span> 读取和修改文件</div>\n' +
            '                <div class="feature-item"><span class="icon">⚡</span> 执行终端命令</div>\n' +
            '                <div class="feature-item"><span class="icon">🔍</span> 搜索代码和文件</div>\n' +
            '                <div class="feature-item"><span class="icon">🔀</span> Git 操作</div>\n' +
            '            </div>\n' +
            '\n' +
            '            <div class="shortcuts">\n' +
            '                <div class="shortcut-item">\n' +
            '                    <kbd>Enter</kbd>\n' +
            '                    <span>发送消息</span>\n' +
            '                </div>\n' +
            '                <div class="shortcut-item">\n' +
            '                    <kbd>Shift+Enter</kbd>\n' +
            '                    <span>换行</span>\n' +
            '                </div>\n' +
            '            </div>\n' +
            '        </div>\n' +
            '    </div>\n' +
            '\n' +
            '    <div class="input-area">\n' +
            '        <textarea id="input" placeholder="告诉我你想做什么..." rows="1"></textarea>\n' +
            '        <button id="sendBtn">发送</button>\n' +
            '    </div>\n' +
            '\n' +
            '    <script>\n' +
            jsCode + '\n' +
            '    </script>\n' +
            '</body>\n' +
            '</html>';
    }

    private _getStyles(): string {
        return `
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif);
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            padding: 12px 16px;
            background: var(--vscode-sideBar-background);
            border-bottom: 1px solid var(--vscode-panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h2 {
            font-size: 14px;
            font-weight: 600;
            color: var(--vscode-foreground);
        }

        .header .header-actions {
            display: flex;
            gap: 6px;
        }

        .header button {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }

        .header button:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .message {
            margin-bottom: 16px;
            max-width: 95%;
            line-height: 1.6;
            font-size: 13px;
        }

        .message.user {
            margin-left: auto;
            background: var(--vscode-inputValidation-infoBorder);
            color: var(--vscode-editor-background);
            padding: 10px 14px;
            border-radius: 12px 12px 2px 12px;
            max-width: 80%;
        }

        .message.assistant {
            background: transparent;
            color: var(--vscode-foreground);
        }

        .message.assistant .msg-content {
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
            padding: 14px 16px;
            border-radius: 2px 12px 12px 12px;
        }

        .agent-activity {
            margin-bottom: 12px;
        }

        .agent-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--vscode-textBlockQuote-background);
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 12px;
            color: var(--vscode-descriptionLabel-foreground);
            border-left: 3px solid var(--vscode-textLink-foreground);
        }

        .agent-status .spinner {
            width: 12px;
            height: 12px;
            border: 2px solid var(--vscode-panel-border);
            border-top: 2px solid var(--vscode-textLink-foreground);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .agent-status.done {
            border-left-color: var(--vscode-terminal-ansiGreen);
        }

        .agent-status.done .spinner {
            display: none;
        }

        .tool-card {
            background: var(--vscode-textBlockQuote-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 8px;
            margin-bottom: 8px;
            overflow: hidden;
            font-size: 12px;
        }

        .tool-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: var(--vscode-panel-border);
            cursor: pointer;
            user-select: none;
        }

        .tool-card-header:hover {
            background: var(--vscode-input-border);
        }

        .tool-card-header .tool-name {
            font-weight: 600;
            color: var(--vscode-textLink-foreground);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .tool-card-header .tool-icon {
            font-size: 14px;
        }

        .tool-card-header .tool-status {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 3px;
        }

        .tool-card-header .tool-status.running {
            background: var(--vscode-inputValidation-warningBackground);
            color: var(--vscode-inputValidation-warningForeground);
        }

        .tool-card-header .tool-status.success {
            background: var(--vscode-inputValidation-infoBackground);
            color: var(--vscode-inputValidation-infoForeground);
        }

        .tool-card-header .tool-status.error {
            background: var(--vscode-inputValidation-errorBackground);
            color: var(--vscode-inputValidation-errorForeground);
        }

        .tool-card-body {
            padding: 10px 12px;
            display: none;
            max-height: 300px;
            overflow-y: auto;
        }

        .tool-card-body.expanded {
            display: block;
        }

        .tool-card-body pre {
            background: var(--vscode-editor-background);
            padding: 8px 10px;
            border-radius: 4px;
            font-family: var(--vscode-editor-font-family, monospace);
            font-size: 12px;
            line-height: 1.4;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .tool-args-label, .tool-result-label {
            font-size: 11px;
            color: var(--vscode-descriptionLabel-foreground);
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .tool-args-label {
            margin-top: 0;
        }

        .tool-result-label {
            margin-top: 10px;
        }

        .agent-summary {
            display: flex;
            gap: 12px;
            padding: 8px 12px;
            background: var(--vscode-inputValidation-infoBackground);
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 12px;
            color: var(--vscode-descriptionLabel-foreground);
        }

        .agent-summary .stat {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .agent-summary .stat-value {
            font-weight: 600;
            color: var(--vscode-textLink-foreground);
        }

        .msg-content h1 {
            font-size: 18px;
            font-weight: 600;
            margin: 16px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--vscode-panel-border);
            color: var(--vscode-foreground);
        }

        .msg-content h1:first-child {
            margin-top: 0;
        }

        .msg-content h2 {
            font-size: 16px;
            font-weight: 600;
            margin: 14px 0 10px 0;
            color: var(--vscode-foreground);
        }

        .msg-content h3 {
            font-size: 14px;
            font-weight: 600;
            margin: 12px 0 8px 0;
            color: var(--vscode-foreground);
        }

        .msg-content p {
            margin: 8px 0;
        }

        .msg-content strong {
            font-weight: 600;
            color: var(--vscode-foreground);
        }

        .msg-content em {
            font-style: italic;
            color: var(--vscode-descriptionLabel-foreground);
        }

        .msg-content pre {
            background: var(--vscode-textBlockQuote-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            margin: 12px 0;
            position: relative;
            overflow: hidden;
        }

        .msg-content pre .code-header {
            background: var(--vscode-panel-border);
            padding: 6px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--vscode-descriptionLabel-foreground);
        }

        .msg-content pre .copy-btn {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            padding: 3px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
            transition: background 0.2s;
        }

        .msg-content pre .copy-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }

        .msg-content pre .copy-btn.copied {
            background: var(--vscode-terminal-ansiGreen);
            color: white;
        }

        .msg-content pre code {
            display: block;
            padding: 14px 16px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family, 'Consolas', 'Monaco', 'Courier New', monospace);
            font-size: 13px;
            line-height: 1.5;
            tab-size: 4;
        }

        .msg-content code:not(pre code) {
            background: var(--vscode-textBlockQuote-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: var(--vscode-editor-font-family, 'Consolas', 'Monaco', 'Courier New', monospace);
            font-size: 12px;
            color: var(--vscode-textLink-foreground);
        }

        .msg-content ul, .msg-content ol {
            margin: 8px 0;
            padding-left: 24px;
        }

        .msg-content li {
            margin: 4px 0;
        }

        .msg-content li::marker {
            color: var(--vscode-textLink-foreground);
        }

        .msg-content table {
            border-collapse: collapse;
            margin: 12px 0;
            width: 100%;
            font-size: 12px;
        }

        .msg-content th {
            background: var(--vscode-panel-border);
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            border: 1px solid var(--vscode-input-border);
        }

        .msg-content td {
            padding: 8px 12px;
            border: 1px solid var(--vscode-input-border);
        }

        .msg-content tr:nth-child(even) {
            background: var(--vscode-textBlockQuote-background);
        }

        .msg-content blockquote {
            border-left: 3px solid var(--vscode-textLink-foreground);
            padding: 8px 12px;
            margin: 8px 0;
            background: var(--vscode-textBlockQuote-background);
            color: var(--vscode-descriptionLabel-foreground);
        }

        .msg-content hr {
            border: none;
            border-top: 1px solid var(--vscode-panel-border);
            margin: 16px 0;
        }

        .msg-content a {
            color: var(--vscode-textLink-foreground);
            text-decoration: none;
        }

        .msg-content a:hover {
            text-decoration: underline;
        }

        .streaming-cursor {
            display: inline;
            animation: blink 1s step-end infinite;
            color: var(--vscode-textLink-foreground);
            font-weight: bold;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        .welcome {
            text-align: center;
            padding: 40px 20px;
            color: var(--vscode-descriptionLabel-foreground);
        }

        .welcome h3 {
            font-size: 18px;
            margin-bottom: 12px;
            color: var(--vscode-foreground);
        }

        .welcome p {
            font-size: 13px;
            line-height: 1.6;
        }

        .welcome .features {
            margin-top: 20px;
            text-align: left;
            display: inline-block;
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
            border-radius: 8px;
            padding: 16px 20px;
            min-width: 320px;
        }

        .welcome .feature-title {
            font-weight: 600;
            color: var(--vscode-textLink-foreground);
            margin-bottom: 10px;
            font-size: 13px;
        }

        .welcome .feature-item {
            display: flex;
            align-items: center;
            margin: 6px 0;
            font-size: 12px;
            color: var(--vscode-descriptionLabel-foreground);
        }

        .welcome .feature-item .icon {
            margin-right: 8px;
            font-size: 14px;
        }

        .welcome .shortcuts {
            margin-top: 16px;
            text-align: left;
        }

        .welcome .shortcut-item {
            display: flex;
            align-items: center;
            margin: 6px 0;
        }

        .welcome kbd {
            background: var(--vscode-textBlockQuote-background);
            border: 1px solid var(--vscode-panel-border);
            padding: 3px 8px;
            border-radius: 4px;
            font-family: var(--vscode-font-family);
            font-size: 12px;
            margin-right: 10px;
            min-width: 100px;
            text-align: center;
        }

        .input-area {
            padding: 12px 16px;
            background: var(--vscode-sideBar-background);
            border-top: 1px solid var(--vscode-panel-border);
            display: flex;
            gap: 8px;
        }

        .input-area textarea {
            flex: 1;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 13px;
            font-family: var(--vscode-font-family);
            resize: none;
            outline: none;
            min-height: 40px;
            max-height: 150px;
        }

        .input-area textarea:focus {
            border-color: var(--vscode-focusBorder);
        }

        .input-area button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 8px;
            padding: 0 16px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
        }

        .input-area button:hover {
            background: var(--vscode-button-hoverBackground);
        }

        .input-area button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .context-info {
            padding: 8px 16px;
            background: var(--vscode-inputValidation-infoBackground);
            border-bottom: 1px solid var(--vscode-panel-border);
            font-size: 12px;
            color: var(--vscode-descriptionLabel-foreground);
            display: none;
        }

        .context-info.show {
            display: block;
        }
        `;
    }

    private _buildWebviewScript(): string {
        // Build the JS as plain string to avoid template literal escaping issues
        // Use String.fromCharCode(96) for backtick in regex patterns
        const BACKTICK = String.fromCharCode(96);

        return `
        (function() {
            'use strict';

            var vscode = acquireVsCodeApi();
            var messagesContainer = document.getElementById('messages');
            var input = document.getElementById('input');
            var sendBtn = document.getElementById('sendBtn');
            var contextInfo = document.getElementById('contextInfo');
            var clearBtn = document.getElementById('clearBtn');

            var welcomeShown = true;
            var currentAssistantBlock = null;
            var currentActivityBlock = null;
            var streamingContent = '';
            var isStreaming = false;

            console.log('[Omnia] Webview script loaded');

            // Auto-resize textarea
            input.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 150) + 'px';
            });

            // Enter to send, Shift+Enter for newline
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    doSendMessage();
                    return false;
                }
            });

            // Send button click
            sendBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                doSendMessage();
            });

            // Clear button
            clearBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                vscode.postMessage({ command: 'clearHistory' });
            });

            // Tool card toggle
            messagesContainer.addEventListener('click', function(e) {
                var header = e.target.closest('.tool-card-header');
                if (header) {
                    var body = header.nextElementSibling;
                    if (body) body.classList.toggle('expanded');
                    return;
                }
                var copyBtn = e.target.closest('.copy-btn');
                if (copyBtn) {
                    doCopyCode(copyBtn);
                    return;
                }
            });

            function doSendMessage() {
                console.log('[Omnia] doSendMessage called, isStreaming:', isStreaming);
                if (isStreaming) return;

                var text = input.value;
                if (typeof text === 'string') text = text.trim();
                if (!text) return;

                if (welcomeShown) {
                    var welcome = messagesContainer.querySelector('.welcome');
                    if (welcome) welcome.remove();
                    welcomeShown = false;
                }

                console.log('[Omnia] Sending message:', text.substring(0, 50));
                vscode.postMessage({ command: 'sendMessage', text: text });
                input.value = '';
                input.style.height = 'auto';
                isStreaming = true;
                sendBtn.disabled = true;
            }

            function doAddMessage(role, content) {
                var div = document.createElement('div');
                div.className = 'message ' + role;
                if (role === 'user') {
                    div.textContent = content;
                } else {
                    var inner = document.createElement('div');
                    inner.className = 'msg-content';
                    inner.innerHTML = doRenderMarkdown(content);
                    div.appendChild(inner);
                }
                messagesContainer.appendChild(div);
                doScrollToBottom();
            }

            function doStartAssistantMessage() {
                streamingContent = '';
                currentActivityBlock = document.createElement('div');
                currentActivityBlock.className = 'agent-activity';
                messagesContainer.appendChild(currentActivityBlock);
                currentAssistantBlock = document.createElement('div');
                currentAssistantBlock.className = 'message assistant';
                var inner = document.createElement('div');
                inner.className = 'msg-content';
                inner.innerHTML = '<span class="streaming-cursor">&#9608;</span>';
                currentAssistantBlock.appendChild(inner);
                messagesContainer.appendChild(currentAssistantBlock);
            }

            function doAppendStreamToken(text) {
                if (!currentAssistantBlock) return;
                streamingContent += text;
                var inner = currentAssistantBlock.querySelector('.msg-content');
                if (streamingContent.trim()) {
                    inner.innerHTML = doRenderMarkdown(streamingContent) + '<span class="streaming-cursor">&#9608;</span>';
                }
                doScrollToBottom();
            }

            function doAddAgentStatus(message) {
                if (!currentActivityBlock) return;
                var statusDiv = document.createElement('div');
                statusDiv.className = 'agent-status';
                statusDiv.innerHTML = '<div class="spinner"></div><span>' + doEscapeHtml(message) + '</span>';
                currentActivityBlock.appendChild(statusDiv);
                doScrollToBottom();
            }

            function doAddToolCallCard(name, args) {
                if (!currentActivityBlock) return;
                var card = document.createElement('div');
                card.className = 'tool-card';
                card.id = 'tool-' + name + '-' + Date.now();
                var toolIcon = doGetToolIcon(name);
                card.innerHTML =
                    '<div class="tool-card-header">' +
                        '<span class="tool-name"><span class="tool-icon">' + toolIcon + '</span>' + doEscapeHtml(name) + '</span>' +
                        '<span class="tool-status running">⏳ 执行中</span>' +
                    '</div>' +
                    '<div class="tool-card-body">' +
                        '<div class="tool-args-label">参数</div>' +
                        '<pre>' + doEscapeHtml(doFormatJson(args)) + '</pre>' +
                    '</div>';
                currentActivityBlock.appendChild(card);
                doScrollToBottom();
            }

            function doUpdateToolResult(name, content, success) {
                if (!currentActivityBlock) return;
                var cards = currentActivityBlock.querySelectorAll('.tool-card');
                var targetCard = null;
                for (var i = cards.length - 1; i >= 0; i--) {
                    var header = cards[i].querySelector('.tool-name');
                    if (header && header.textContent.trim() === name) {
                        targetCard = cards[i];
                        break;
                    }
                }
                if (!targetCard) return;
                var statusEl = targetCard.querySelector('.tool-status');
                if (statusEl) {
                    statusEl.className = 'tool-status ' + (success ? 'success' : 'error');
                    statusEl.textContent = success ? '✅ 完成' : '❌ 失败';
                }
                var body = targetCard.querySelector('.tool-card-body');
                if (body) {
                    var resultHtml =
                        '<div class="tool-result-label">' + (success ? '结果' : '错误') + '</div>' +
                        '<pre>' + doEscapeHtml(doTruncateText(content, 2000)) + '</pre>';
                    body.innerHTML += resultHtml;
                }
            }

            function doShowAgentSummary(toolCalls, rounds) {
                if (!currentActivityBlock) return;
                if (toolCalls === 0 && rounds <= 1) return;
                var summary = document.createElement('div');
                summary.className = 'agent-summary';
                summary.innerHTML =
                    '<span class="stat">🔄 轮次: <span class="stat-value">' + rounds + '</span></span>' +
                    '<span class="stat">🔧 工具调用: <span class="stat-value">' + toolCalls + '</span></span>';
                currentActivityBlock.insertBefore(summary, currentActivityBlock.firstChild);
            }

            function doEndAssistantMessage(fullContent) {
                if (currentAssistantBlock) {
                    var inner = currentAssistantBlock.querySelector('.msg-content');
                    if (fullContent && fullContent.trim()) {
                        inner.innerHTML = doRenderMarkdown(fullContent);
                    } else if (streamingContent.trim()) {
                        inner.innerHTML = doRenderMarkdown(streamingContent);
                    } else {
                        inner.innerHTML = '<em style="color: var(--vscode-descriptionLabel-foreground);">（无文字回复）</em>';
                    }
                }
                if (currentActivityBlock) {
                    var spinners = currentActivityBlock.querySelectorAll('.agent-status .spinner');
                    for (var i = 0; i < spinners.length; i++) {
                        spinners[i].parentElement.classList.add('done');
                    }
                }
                currentAssistantBlock = null;
                currentActivityBlock = null;
                streamingContent = '';
                isStreaming = false;
                sendBtn.disabled = false;
                input.focus();
                doScrollToBottom();
            }

            // Utilities
            function doEscapeHtml(text) {
                var div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            function doFormatJson(str) {
                try {
                    if (typeof str === 'string') return JSON.stringify(JSON.parse(str), null, 2);
                    return JSON.stringify(str, null, 2);
                } catch (e) { return str; }
            }

            function doTruncateText(text, maxLen) {
                if (text.length <= maxLen) return text;
                return text.slice(0, maxLen) + '...\\n[已截断，共 ' + text.length + ' 字符]';
            }

            function doScrollToBottom() {
                requestAnimationFrame(function() {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                });
            }

            function doGetToolIcon(name) {
                var icons = {
                    'read_file': '📖', 'write_file': '✏️', 'execute_shell': '⚡',
                    'list_directory': '📂', 'web_search': '🔍', 'query_memory': '🧠',
                    'save_memory': '💾', 'memory_stats': '📊'
                };
                return icons[name] || '🔧';
            }

            function doCopyCode(btn) {
                var codeBlock = btn.closest('pre').querySelector('code');
                var text = codeBlock.textContent;
                navigator.clipboard.writeText(text).then(function() {
                    btn.textContent = '已复制!';
                    btn.classList.add('copied');
                    setTimeout(function() {
                        btn.textContent = '复制';
                        btn.classList.remove('copied');
                    }, 2000);
                });
            }

            // ===== Markdown Renderer =====
            // Using String.fromCharCode(96) for backtick to avoid escaping issues
            var BK = String.fromCharCode(96);

            function doRenderMarkdown(text) {
                if (!text) return '';

                var result = text;

                // Save code blocks (using BK for backtick)
                var codeBlocks = [];
                var tripleBkRe = new RegExp(BK + BK + BK + '(\\\\w*)\\\\n([\\\\s\\\\S]*?)' + BK + BK + BK, 'g');
                result = result.replace(tripleBkRe, function(match, lang, code) {
                    var index = codeBlocks.length;
                    codeBlocks.push({ lang: lang || 'plaintext', code: code });
                    return '%%CODEBLOCK_' + index + '%%';
                });

                // Save inline code
                var inlineCodes = [];
                var inlineBkRe = new RegExp(BK + '([^' + BK + ']+)' + BK, 'g');
                result = result.replace(inlineBkRe, function(match, code) {
                    var index = inlineCodes.length;
                    inlineCodes.push(code);
                    return '%%INLINE_' + index + '%%';
                });

                // Headers
                result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>');
                result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>');
                result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>');

                // Bold & italic
                result = result.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
                result = result.replace(/\\*(.+?)\\*/g, '<em>$1</em>');

                // Blockquote
                result = result.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

                // HR
                result = result.replace(/^---$/gm, '<hr>');

                // Table rows
                result = result.replace(/^\\|(.+)\\|$/gm, function(match, content) {
                    return '%%TABLE_ROW%%' + content + '%%/TABLE_ROW%%';
                });

                // Unordered list
                result = result.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
                result = result.replace(/(<li>.*<\\/li>\\n?)+/g, '<ul>$&</ul>');

                // Ordered list
                result = result.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');

                // Checkbox
                result = result.replace(/\\[ \\]/g, '<span class="checkbox"></span>');
                result = result.replace(/\\[x\\]/g, '<span class="checkbox checked">✓</span>');

                // Links
                result = result.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank">$1</a>');

                // Paragraphs
                result = result.replace(/\\n\\n/g, '</p><p>');
                result = '<p>' + result + '</p>';
                result = result.replace(/<p><\\/p>/g, '');
                result = result.replace(/<p>(<h[1-3]>)/g, '$1');
                result = result.replace(/(<\\/h[1-3]>)<\\/p>/g, '$1');
                result = result.replace(/<p>(<ul>)/g, '$1');
                result = result.replace(/(<\\/ul>)<\\/p>/g, '$1');
                result = result.replace(/<p>(<blockquote>)/g, '$1');
                result = result.replace(/(<\\/blockquote>)<\\/p>/g, '$1');
                result = result.replace(/<p>(<hr>)<\\/p>/g, '$1');

                // Restore tables
                result = result.replace(/(<p>)?%%TABLE_ROW%%(.+)%%\\/TABLE_ROW%%(<\\/p>)?/gm, function(match, p1, content, p2) {
                    var cells = content.split('|').map(function(c) { return c.trim(); });
                    var isHeader = cells.every(function(c) { return /^[-:]+$/.test(c); });
                    if (isHeader) return '';
                    return '<tr>' + cells.map(function(c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
                });

                // Restore code blocks
                for (var idx = 0; idx < codeBlocks.length; idx++) {
                    var langLabel = codeBlocks[idx].lang || 'code';
                    var escapedCode = doEscapeHtml(codeBlocks[idx].code.trim());
                    var codeBlockHtml = '<pre><div class="code-header"><span>' + langLabel + '</span><button class="copy-btn">复制</button></div><code>' + escapedCode + '</code></pre>';
                    result = result.replace('%%CODEBLOCK_' + idx + '%%', codeBlockHtml);
                }

                // Restore inline code
                for (var idx2 = 0; idx2 < inlineCodes.length; idx2++) {
                    result = result.replace('%%INLINE_' + idx2 + '%%', '<code>' + doEscapeHtml(inlineCodes[idx2]) + '</code>');
                }

                // Clean empty p
                result = result.replace(/<p>\\s*<\\/p>/g, '');

                return result;
            }

            // ===== Message handler =====
            window.addEventListener('message', function(event) {
                var msg = event.data;
                console.log('[Omnia] Received message:', msg.command);
                switch (msg.command) {
                    case 'addMessage':
                        doAddMessage(msg.role, msg.content);
                        break;
                    case 'startAssistant':
                        doStartAssistantMessage();
                        break;
                    case 'streamToken':
                        doAppendStreamToken(msg.content);
                        break;
                    case 'agentStatus':
                        doAddAgentStatus(msg.message);
                        break;
                    case 'toolCall':
                        doAddToolCallCard(msg.name, msg.args);
                        break;
                    case 'toolResult':
                        doUpdateToolResult(msg.name, msg.content, msg.success);
                        break;
                    case 'endAssistant':
                        doShowAgentSummary(msg.toolCalls || 0, msg.rounds || 0);
                        doEndAssistantMessage(msg.fullContent);
                        break;
                    case 'clearMessages':
                        messagesContainer.innerHTML = '';
                        welcomeShown = false;
                        break;
                    case 'updateContext':
                        if (msg.context) {
                            contextInfo.textContent = '📄 ' + msg.context.file + ' (第' + msg.context.line + '行)';
                            contextInfo.classList.add('show');
                        } else {
                            contextInfo.classList.remove('show');
                        }
                        break;
                }
            });

            console.log('[Omnia] Script initialization complete');
            input.focus();
        })();
        `;
    }
}
