"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const http = require("http");
const fs = require("fs");
const path = require("path");
// ============================================================
// Global State
// ============================================================
let currentContext = null;
let chatPanel;
let omniaChannel;
function getEndpoint() {
    return vscode.workspace.getConfiguration('omnia.ideBridge').get('endpoint', 'http://127.0.0.1:8765');
}
function log(msg) {
    const ts = new Date().toISOString();
    omniaChannel.appendLine(`[${ts}] ${msg}`);
}
// ============================================================
// Context Building
// ============================================================
function buildContext(editor) {
    if (!editor) {
        return { file: null, language: null, line: null, column: null, selectedText: '', timestamp: Date.now() };
    }
    const doc = editor.document;
    const pos = editor.selection.active;
    const selected = editor.selection.isEmpty ? '' : doc.getText(editor.selection);
    const maxLen = vscode.workspace.getConfiguration('omnia.ai').get('maxContextLength', 4000);
    let fullContent = '';
    if (doc.fileName) {
        try {
            fullContent = doc.getText();
            if (fullContent.length > maxLen) {
                fullContent = fullContent.slice(0, maxLen) + '\n... (truncated)';
            }
        }
        catch { }
    }
    return {
        file: doc.fileName,
        language: doc.languageId,
        line: pos.line + 1,
        column: pos.character + 1,
        selectedText: selected.length > 500 ? selected.slice(0, 500) + '...' : selected,
        timestamp: Date.now(),
        fullContent,
    };
}
function formatContextForPrompt(ctx) {
    if (!ctx || !ctx.file)
        return '';
    let prompt = `\n[Current Context]\n`;
    prompt += `File: ${path.basename(ctx.file)}\n`;
    prompt += `Language: ${ctx.language}\n`;
    prompt += `Position: Line ${ctx.line}, Col ${ctx.column}\n`;
    if (ctx.selectedText) {
        prompt += `\nSelected Code:\n\`\`\`${ctx.language}\n${ctx.selectedText}\n\`\`\`\n`;
    }
    if (ctx.fullContent && ctx.fullContent.length > 0) {
        prompt += `\nFull File Content:\n\`\`\`${ctx.language}\n${ctx.fullContent}\n\`\`\`\n`;
    }
    return prompt;
}
// ============================================================
// Push context to backend
// ============================================================
let debounceTimer;
function pushContext(ctx) {
    const cfg = vscode.workspace.getConfiguration('omnia.ideBridge');
    if (!cfg.get('enabled', true))
        return;
    const endpoint = cfg.get('endpoint', 'http://127.0.0.1:8765');
    const url = new URL(endpoint);
    const payload = JSON.stringify(ctx);
    const options = {
        hostname: url.hostname,
        port: parseInt(url.port || '8765'),
        path: '/ide-context',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
    };
    const req = http.request(options, (res) => {
        log(`Context pushed: ${res.statusCode}`);
    });
    req.on('error', (err) => log(`Context push error: ${err.message}`));
    req.write(payload);
    req.end();
}
function sendContext(editor, immediate = false) {
    const debounceMs = vscode.workspace.getConfiguration('omnia.ideBridge').get('debounceMs', 300);
    currentContext = buildContext(editor);
    if (immediate) {
        pushContext(currentContext);
        return;
    }
    if (debounceTimer)
        clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => pushContext(currentContext), debounceMs);
}
// ============================================================
// Omnia API Helper
// ============================================================
async function callOmniaChat(prompt) {
    const endpoint = getEndpoint();
    const url = new URL('/api/chat', endpoint);
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({ message: prompt, history: [] });
        const options = {
            hostname: url.hostname,
            port: parseInt(url.port || '8765'),
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
        };
        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk.toString(); });
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    resolve(parsed.response || parsed.content || data);
                }
                catch {
                    resolve(data);
                }
            });
        });
        req.on('error', (err) => reject(err));
        req.write(postData);
        req.end();
    });
}
async function callOmniaChatStream(prompt, onChunk) {
    const endpoint = getEndpoint();
    const url = new URL('/api/chat/stream', endpoint);
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({ message: prompt, history: [] });
        const options = {
            hostname: url.hostname,
            port: parseInt(url.port || '8765'),
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
        };
        const req = http.request(options, (res) => {
            let buffer = '';
            res.on('data', (chunk) => {
                buffer += chunk.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            resolve();
                            return;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                onChunk(parsed.content);
                            }
                        }
                        catch { }
                    }
                }
            });
            res.on('end', () => resolve());
        });
        req.on('error', (err) => reject(err));
        req.write(postData);
        req.end();
    });
}
// ============================================================
// Diff Preview Provider
// ============================================================
class DiffContentProvider {
    constructor() {
        this._onDidChange = new vscode.EventEmitter();
        this.contents = new Map();
        this.onDidChange = this._onDidChange.event;
    }
    setContent(uri, content) {
        this.contents.set(uri, content);
    }
    provideTextDocumentContent(uri) {
        return this.contents.get(uri.toString()) || '';
    }
}
const diffProvider = new DiffContentProvider();
// ============================================================
// Inline Edit with Diff Preview
// ============================================================
async function performInlineEdit(editor, instruction) {
    const selected = editor.document.getText(editor.selection);
    if (!selected)
        return;
    const language = editor.document.languageId;
    // Show progress
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Omnia AI: Generating edit...',
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: 'Thinking...' });
        const prompt = `你是一个代码编辑助手。请根据以下指令修改代码。

**重要规则：**
1. 只输出修改后的完整代码，不要包含任何解释
2. 不要添加 markdown 代码块标记
3. 保持原有的代码风格和缩进

指令: ${instruction}

原始代码:
\`\`\`${language}
${selected}
\`\`\`

请直接输出修改后的代码:`;
        try {
            let modified = '';
            await callOmniaChatStream(prompt, (chunk) => {
                modified += chunk;
            });
            // Clean up the response - remove markdown code blocks if present
            modified = cleanCodeResponse(modified, language);
            // Show diff preview
            await showDiffPreview(editor, selected, modified, instruction);
        }
        catch (err) {
            vscode.window.showErrorMessage(`Omnia AI Error: ${err.message}`);
        }
    });
}
function cleanCodeResponse(code, language) {
    // Remove markdown code blocks
    let cleaned = code.trim();
    const patterns = [
        new RegExp(`^\`\`\`${language}\\n?`, 'i'),
        /^```\w*\n?/,
        /\n?```$/,
    ];
    for (const pattern of patterns) {
        cleaned = cleaned.replace(pattern, '');
    }
    return cleaned.trim();
}
async function showDiffPreview(editor, original, modified, instruction) {
    // Create temporary files for diff
    const originalUri = vscode.Uri.parse(`omnia-diff:original_${Date.now()}.txt`);
    const modifiedUri = vscode.Uri.parse(`omnia-diff:modified_${Date.now()}.txt`);
    diffProvider.setContent(originalUri.toString(), original);
    diffProvider.setContent(modifiedUri.toString(), modified);
    // Show diff
    const diffTitle = `Omnia Edit: ${instruction.slice(0, 50)}`;
    await vscode.commands.executeCommand('vscode.diff', originalUri, modifiedUri, diffTitle);
    // Show accept/reject dialog
    const action = await vscode.window.showInformationMessage('Apply this edit?', { modal: true }, '✅ Apply', '❌ Reject', '📋 Copy');
    if (action === '✅ Apply') {
        await editor.edit((editBuilder) => {
            editBuilder.replace(editor.selection, modified);
        });
        vscode.window.showInformationMessage('✅ Edit applied!');
    }
    else if (action === '📋 Copy') {
        await vscode.env.clipboard.writeText(modified);
        vscode.window.showInformationMessage('📋 Copied to clipboard!');
    }
}
// ============================================================
// CodeLens Provider
// ============================================================
class OmniaCodeLensProvider {
    constructor() {
        this._onDidChangeCodeLenses = new vscode.EventEmitter();
        this.onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
    }
    provideCodeLenses(document) {
        const lenses = [];
        // Add CodeLens at the top of the file
        const topRange = new vscode.Range(0, 0, 0, 0);
        lenses.push(new vscode.CodeLens(topRange, {
            title: '✨ Ask Omnia',
            command: 'omnia.openChat',
            tooltip: 'Open Omnia AI Chat'
        }));
        // Find functions and classes
        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const text = line.text.trim();
            // Function definitions
            if (text.match(/^(function|def|async function|const \w+ = |class |public |private |protected )/)) {
                const range = new vscode.Range(i, 0, i, 0);
                lenses.push(new vscode.CodeLens(range, {
                    title: '📝 Explain',
                    command: 'omnia.explainCode',
                    arguments: [document, range],
                    tooltip: 'Ask Omnia to explain this'
                }));
            }
        }
        return lenses;
    }
}
// ============================================================
// Completion Provider
// ============================================================
class OmniaCompletionProvider {
    constructor() {
        this.lastRequest = 0;
        this.cache = new Map();
    }
    async provideInlineCompletionItems(document, position, context, token) {
        // Only trigger on explicit request or specific triggers
        if (context.triggerKind === vscode.InlineCompletionTriggerKind.Automatic) {
            return [];
        }
        const line = document.lineAt(position);
        const textBefore = document.getText(new vscode.Range(Math.max(0, position.line - 10), 0, position.line, position.character));
        // Don't trigger on empty lines
        if (line.text.trim().length === 0) {
            return [];
        }
        // Debounce
        const now = Date.now();
        if (now - this.lastRequest < 500) {
            return [];
        }
        this.lastRequest = now;
        const prompt = `Continue this code (only output the continuation, no explanations):
\`\`\`${document.languageId}
${textBefore}
\`\`\`

Continue from where it left off:`;
        try {
            let completion = '';
            await callOmniaChatStream(prompt, (chunk) => {
                completion += chunk;
            });
            completion = cleanCodeResponse(completion, document.languageId);
            if (completion && completion.length > 0) {
                return [new vscode.InlineCompletionItem(completion)];
            }
        }
        catch (err) {
            log(`Completion error: ${err}`);
        }
        return [];
    }
}
// ============================================================
// @file Reference Provider
// ============================================================
async function resolveFileReference(ref) {
    // Remove @ prefix
    const fileName = ref.slice(1);
    // Search workspace for matching files
    const files = await vscode.workspace.findFiles(`**/${fileName}*`, null, 5);
    if (files.length === 0) {
        return null;
    }
    // Read the first matching file
    try {
        const content = fs.readFileSync(files[0].fsPath, 'utf-8');
        const maxLen = 2000;
        return content.length > maxLen ? content.slice(0, maxLen) + '\n... (truncated)' : content;
    }
    catch {
        return null;
    }
}
async function processAtReferences(text) {
    const fileRefs = text.match(/@[\w\-\.]+/g);
    if (!fileRefs)
        return text;
    let processed = text;
    for (const ref of fileRefs) {
        const content = await resolveFileReference(ref);
        if (content) {
            processed = processed.replace(ref, `\n[File: ${ref.slice(1)}]\n\`\`\`\n${content}\n\`\`\`\n`);
        }
    }
    return processed;
}
// ============================================================
// Webview Chat Panel
// ============================================================
function getWebviewContent(webview, extensionUri) {
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'webview', 'style.css'));
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'webview', 'main.js'));
    const nonce = getNonce();
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <link href="${styleUri}" rel="stylesheet">
    <title>Omnia AI</title>
</head>
<body>
    <div id="app">
        <header class="header">
            <div class="logo">
                <span class="logo-icon">🧠</span>
                <span class="logo-text">Omnia AI</span>
            </div>
            <div class="actions">
                <button id="clearBtn" class="icon-btn" title="Clear chat">🗑️</button>
                <button id="contextBtn" class="icon-btn" title="Toggle context">📎</button>
            </div>
        </header>
        
        <div id="contextBar" class="context-bar hidden">
            <span id="contextInfo">No file context</span>
        </div>
        
        <div id="messages" class="messages"></div>
        
        <div class="input-area">
            <div class="input-wrapper">
                <textarea id="input" placeholder="Ask Omnia anything... (@file to reference files)" rows="1"></textarea>
                <button id="sendBtn" class="send-btn">
                    <span>▶</span>
                </button>
            </div>
            <div class="input-hints">
                <span class="hint">/explain</span>
                <span class="hint">/fix</span>
                <span class="hint">/commit</span>
                <span class="hint">/test</span>
                <span class="hint">@file</span>
            </div>
        </div>
    </div>
    <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
}
function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
function createChatPanel(context) {
    if (chatPanel) {
        chatPanel.reveal(vscode.ViewColumn.Two);
        return;
    }
    chatPanel = vscode.window.createWebviewPanel('omniaChat', 'Omnia AI Chat', { viewColumn: vscode.ViewColumn.Two, preserveFocus: true }, {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'webview')],
    });
    chatPanel.webview.html = getWebviewContent(chatPanel.webview, context.extensionUri);
    // Handle messages from webview
    chatPanel.webview.onDidReceiveMessage(async (message) => {
        switch (message.command) {
            case 'sendMessage':
                await handleChatMessage(message.text, message.includeContext);
                break;
            case 'clearChat':
                // TODO: clear backend history
                break;
            case 'ready':
                updateContextBar();
                break;
        }
    });
    chatPanel.onDidDispose(() => {
        chatPanel = undefined;
    });
}
function updateContextBar() {
    if (!chatPanel)
        return;
    const ctx = currentContext;
    const info = ctx?.file ? `${path.basename(ctx.file)}:${ctx.line}` : 'No file context';
    chatPanel.webview.postMessage({ command: 'updateContext', info, hasSelection: !!ctx?.selectedText });
}
async function handleChatMessage(text, includeContext) {
    if (!chatPanel)
        return;
    // Process @file references
    let prompt = await processAtReferences(text);
    if (includeContext && currentContext) {
        prompt += formatContextForPrompt(currentContext);
    }
    // Handle slash commands
    if (text.startsWith('/')) {
        prompt = handleSlashCommand(text);
        if (includeContext && currentContext) {
            prompt += formatContextForPrompt(currentContext);
        }
    }
    // Send to Omnia backend via streaming
    chatPanel.webview.postMessage({ command: 'startResponse' });
    try {
        await callOmniaChatStream(prompt, (chunk) => {
            chatPanel?.webview.postMessage({ command: 'appendResponse', text: chunk });
        });
        chatPanel?.webview.postMessage({ command: 'endResponse' });
    }
    catch (err) {
        log(`Chat error: ${err.message}`);
        chatPanel?.webview.postMessage({ command: 'error', text: `Error: ${err.message}` });
    }
}
function handleSlashCommand(text) {
    const cmd = text.split(' ')[0].toLowerCase();
    const args = text.slice(cmd.length).trim();
    switch (cmd) {
        case '/explain':
            return `请解释以下代码的功能和逻辑:\n${args}`;
        case '/fix':
            return `请检查并修复以下代码中的问题:\n${args}`;
        case '/commit':
            return `请为当前更改生成一个简洁的 Git commit 消息（遵循 Conventional Commits 规范）。`;
        case '/test':
            return `请为以下代码生成单元测试:\n${args}`;
        case '/refactor':
            return `请重构以下代码，提高可读性和性能:\n${args}`;
        default:
            return text;
    }
}
// ============================================================
// Commands
// ============================================================
function registerCommands(context) {
    // Open chat panel
    context.subscriptions.push(vscode.commands.registerCommand('omnia.openChat', () => {
        createChatPanel(context);
    }));
    // Explain code
    context.subscriptions.push(vscode.commands.registerCommand('omnia.explainCode', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selected = editor.document.getText(editor.selection);
        if (!selected) {
            vscode.window.showWarningMessage('Please select some code first.');
            return;
        }
        createChatPanel(context);
        setTimeout(() => {
            chatPanel?.webview.postMessage({ command: 'autoSend', text: `/explain ${selected}` });
        }, 500);
    }));
    // Fix code
    context.subscriptions.push(vscode.commands.registerCommand('omnia.fixCode', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selected = editor.document.getText(editor.selection);
        if (!selected) {
            vscode.window.showWarningMessage('Please select some code first.');
            return;
        }
        createChatPanel(context);
        setTimeout(() => {
            chatPanel?.webview.postMessage({ command: 'autoSend', text: `/fix ${selected}` });
        }, 500);
    }));
    // Inline edit with diff preview
    context.subscriptions.push(vscode.commands.registerCommand('omnia.inlineEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selected = editor.document.getText(editor.selection);
        if (!selected) {
            vscode.window.showWarningMessage('Please select some code first.');
            return;
        }
        const instruction = await vscode.window.showInputBox({
            prompt: 'How should I edit this code?',
            placeHolder: 'e.g., Add error handling, Optimize performance, Add types...',
        });
        if (instruction) {
            await performInlineEdit(editor, instruction);
        }
    }));
    // Quick edit (no dialog, just ask for instruction)
    context.subscriptions.push(vscode.commands.registerCommand('omnia.quickEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        // If no selection, select current line
        if (editor.selection.isEmpty) {
            const line = editor.document.lineAt(editor.selection.active.line);
            editor.selection = new vscode.Selection(line.range.start, line.range.end);
        }
        const selected = editor.document.getText(editor.selection);
        const instruction = await vscode.window.showInputBox({
            prompt: 'Edit instruction',
            placeHolder: 'What should I change?',
        });
        if (instruction) {
            await performInlineEdit(editor, instruction);
        }
    }));
    // Send to chat
    context.subscriptions.push(vscode.commands.registerCommand('omnia.sendToChat', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selected = editor.document.getText(editor.selection);
        if (!selected) {
            vscode.window.showWarningMessage('Please select some code first.');
            return;
        }
        createChatPanel(context);
        setTimeout(() => {
            chatPanel?.webview.postMessage({ command: 'insertText', text: selected });
        }, 200);
    }));
    // Generate commit message
    context.subscriptions.push(vscode.commands.registerCommand('omnia.commitChanges', async () => {
        createChatPanel(context);
        setTimeout(() => {
            chatPanel?.webview.postMessage({ command: 'autoSend', text: '/commit' });
        }, 500);
    }));
    // Generate tests for current file
    context.subscriptions.push(vscode.commands.registerCommand('omnia.generateTests', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const doc = editor.document;
        const content = doc.getText();
        createChatPanel(context);
        setTimeout(() => {
            chatPanel?.webview.postMessage({
                command: 'autoSend',
                text: `/test \`\`\`${doc.languageId}\n${content}\n\`\`\``
            });
        }, 500);
    }));
}
// ============================================================
// Activation
// ============================================================
function activate(context) {
    omniaChannel = vscode.window.createOutputChannel('Omnia AI');
    log('Omnia AI Assistant activated');
    // Register diff content provider
    context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider('omnia-diff', diffProvider));
    // Register CodeLens provider
    context.subscriptions.push(vscode.languages.registerCodeLensProvider('*', new OmniaCodeLensProvider()));
    // Register inline completion provider
    context.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider('*', new OmniaCompletionProvider()));
    // Register all commands
    registerCommands(context);
    // Listen for editor changes
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
        sendContext(editor, true);
        updateContextBar();
    }));
    context.subscriptions.push(vscode.window.onDidChangeTextEditorSelection((e) => {
        sendContext(e.textEditor);
        updateContextBar();
    }));
    // Initial context push
    const editor = vscode.window.activeTextEditor;
    if (editor) {
        sendContext(editor, true);
    }
    // Retry context push
    [500, 2000, 5000].forEach((ms) => {
        const t = setTimeout(() => {
            if (vscode.window.activeTextEditor) {
                sendContext(vscode.window.activeTextEditor, true);
            }
        }, ms);
        context.subscriptions.push({ dispose: () => clearTimeout(t) });
    });
    // Show welcome message
    vscode.window.showInformationMessage('Omnia AI Assistant is ready! Press Ctrl+Shift+O to open chat.');
}
function deactivate() {
    if (chatPanel) {
        chatPanel.dispose();
    }
}
//# sourceMappingURL=extension.js.map