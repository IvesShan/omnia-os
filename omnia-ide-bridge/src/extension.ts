import * as vscode from 'vscode';
import * as http from 'http';
import * as fs from 'fs';
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
// Global State
// ============================================================

let currentContext: IdeContext | null = null;
let omniaChannel: vscode.OutputChannel;
let chatHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [];

function getEndpoint(): string {
    return vscode.workspace.getConfiguration('omnia.ideBridge').get<string>('endpoint', 'http://127.0.0.1:8765');
}

function log(msg: string) {
    const ts = new Date().toISOString();
    omniaChannel.appendLine(`[${ts}] ${msg}`);
}

// ============================================================
// Context Building
// ============================================================

function buildContext(editor: vscode.TextEditor | undefined): IdeContext {
    if (!editor) {
        return { file: null, language: null, line: null, column: null, selectedText: '', timestamp: Date.now() };
    }
    const doc = editor.document;
    const pos = editor.selection.active;
    const selected = editor.selection.isEmpty ? '' : doc.getText(editor.selection);
    const maxLen = vscode.workspace.getConfiguration('omnia.ai').get<number>('maxContextLength', 4000);

    let fullContent = '';
    if (doc.fileName) {
        try {
            fullContent = doc.getText();
            if (fullContent.length > maxLen) {
                fullContent = fullContent.slice(0, maxLen) + '\n... (truncated)';
            }
        } catch { }
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

function formatContextForPrompt(ctx: IdeContext | null): string {
    if (!ctx || !ctx.file) return '';
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

let debounceTimer: NodeJS.Timeout | undefined;

function pushContext(ctx: IdeContext) {
    const cfg = vscode.workspace.getConfiguration('omnia.ideBridge');
    if (!cfg.get<boolean>('enabled', true)) return;

    const endpoint = cfg.get<string>('endpoint', 'http://127.0.0.1:8765');
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

function sendContext(editor: vscode.TextEditor | undefined, immediate = false) {
    const debounceMs = vscode.workspace.getConfiguration('omnia.ideBridge').get<number>('debounceMs', 300);
    currentContext = buildContext(editor);

    if (immediate) {
        pushContext(currentContext);
        return;
    }
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => pushContext(currentContext!), debounceMs);
}

// ============================================================
// Omnia API Helper (streaming)
// ============================================================

async function callOmniaChatStream(prompt: string, onChunk: (text: string) => void): Promise<void> {
    const endpoint = getEndpoint();
    const url = new URL('/api/chat/stream', endpoint);

    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({ message: prompt, history: chatHistory });

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
            res.on('data', (chunk: Buffer) => {
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
                        } catch { }
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

class DiffContentProvider implements vscode.TextDocumentContentProvider {
    private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
    private contents = new Map<string, string>();

    onDidChange = this._onDidChange.event;

    setContent(uri: string, content: string) {
        this.contents.set(uri, content);
    }

    provideTextDocumentContent(uri: vscode.Uri): string {
        return this.contents.get(uri.toString()) || '';
    }
}

const diffProvider = new DiffContentProvider();

// ============================================================
// Inline Edit with Diff Preview
// ============================================================

function cleanCodeResponse(code: string, language: string): string {
    let cleaned = code.trim();
    // Remove markdown code fences
    cleaned = cleaned.replace(/^```[\w]*\n?/gm, '');
    cleaned = cleaned.replace(/```$/gm, '');
    return cleaned.trim();
}

async function performInlineEdit(editor: vscode.TextEditor, instruction: string) {
    const selected = editor.document.getText(editor.selection);
    if (!selected) return;

    const language = editor.document.languageId;

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

            modified = cleanCodeResponse(modified, language);
            await showDiffPreview(editor, selected, modified, instruction);
        } catch (err: any) {
            vscode.window.showErrorMessage(`Omnia AI Error: ${err.message}`);
        }
    });
}

async function showDiffPreview(
    editor: vscode.TextEditor,
    original: string,
    modified: string,
    instruction: string
) {
    const originalUri = vscode.Uri.parse(`omnia-diff:original_${Date.now()}.txt`);
    const modifiedUri = vscode.Uri.parse(`omnia-diff:modified_${Date.now()}.txt`);

    diffProvider.setContent(originalUri.toString(), original);
    diffProvider.setContent(modifiedUri.toString(), modified);

    const diffTitle = `Omnia Edit: ${instruction.slice(0, 50)}`;
    await vscode.commands.executeCommand(
        'vscode.diff',
        originalUri,
        modifiedUri,
        diffTitle
    );

    const action = await vscode.window.showInformationMessage(
        'Apply this edit?',
        { modal: true },
        '✅ Apply',
        '❌ Reject',
        '📋 Copy'
    );

    if (action === '✅ Apply') {
        await editor.edit((editBuilder) => {
            editBuilder.replace(editor.selection, modified);
        });
        vscode.window.showInformationMessage('✅ Edit applied!');
    } else if (action === '📋 Copy') {
        await vscode.env.clipboard.writeText(modified);
        vscode.window.showInformationMessage('📋 Copied to clipboard!');
    }
}

// ============================================================
// CodeLens Provider
// ============================================================

class OmniaCodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
    onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

    provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];

        const topRange = new vscode.Range(0, 0, 0, 0);
        lenses.push(new vscode.CodeLens(topRange, {
            title: '✨ Ask Omnia (@omnia)',
            command: 'editor.action.terminalChat.focus',
            tooltip: 'Open Copilot Chat and type @omnia'
        }));

        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const text = line.text.trim();

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

class OmniaCompletionProvider implements vscode.InlineCompletionItemProvider {
    private lastRequest = 0;

    async provideInlineCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        context: vscode.InlineCompletionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.InlineCompletionItem[]> {
        if (context.triggerKind === vscode.InlineCompletionTriggerKind.Automatic) {
            return [];
        }

        const line = document.lineAt(position);
        if (line.text.trim().length === 0) {
            return [];
        }

        const now = Date.now();
        if (now - this.lastRequest < 500) {
            return [];
        }
        this.lastRequest = now;

        const textBefore = document.getText(new vscode.Range(
            Math.max(0, position.line - 10), 0,
            position.line, position.character
        ));

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
        } catch (err) {
            log(`Completion error: ${err}`);
        }

        return [];
    }
}

// ============================================================
// @file Reference Resolver
// ============================================================

async function resolveFileReferences(prompt: string): Promise<string> {
    const fileRefs = prompt.match(/@[\w\-\.]+/g);
    if (!fileRefs) return prompt;

    let processed = prompt;
    for (const ref of fileRefs) {
        const fileName = ref.slice(1);
        const files = await vscode.workspace.findFiles(`**/${fileName}*`, null, 5);
        if (files.length > 0) {
            try {
                const content = fs.readFileSync(files[0].fsPath, 'utf-8');
                const maxLen = 2000;
                const truncated = content.length > maxLen ? content.slice(0, maxLen) + '\n... (truncated)' : content;
                processed = processed.replace(ref, `\n[File: ${fileName}]\n\`\`\`\n${truncated}\n\`\`\`\n`);
            } catch { }
        }
    }
    return processed;
}

// ============================================================
// Slash Commands
// ============================================================

function handleSlashCommand(text: string): string {
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
// Chat Participant (Native VSCode Chat API)
// ============================================================

function registerChatParticipant(context: vscode.ExtensionContext) {
    const handler: vscode.ChatRequestHandler = async (
        request: vscode.ChatRequest,
        chatContext: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult | void> => {
        log(`Chat request: ${request.prompt}`);

        // Build context-aware prompt
        let prompt = request.prompt;

        // Process @file references
        prompt = await resolveFileReferences(prompt);

        // Handle slash commands
        if (prompt.startsWith('/')) {
            prompt = handleSlashCommand(prompt);
        }

        // Auto-inject IDE context
        const autoInject = vscode.workspace.getConfiguration('omnia.ai').get<boolean>('autoInjectContext', true);
        if (autoInject && currentContext) {
            prompt += formatContextForPrompt(currentContext);
        }

        // Build history from chat context
        const history: Array<{ role: 'user' | 'assistant'; content: string }> = [];
        for (const turn of chatContext.history) {
            if (turn instanceof vscode.ChatRequestTurn) {
                history.push({ role: 'user', content: turn.prompt });
            } else if (turn instanceof vscode.ChatResponseTurn) {
                const responseText = turn.response.map(r => {
                    if (r instanceof vscode.ChatResponseMarkdownPart) {
                        return r.value.value;
                    }
                    return '';
                }).join('');
                history.push({ role: 'assistant', content: responseText });
            }
        }

        // Show progress
        stream.progress('🧠 Thinking...');

        // Stream response from Omnia
        let fullResponse = '';
        try {
            await callOmniaChatStream(prompt, (chunk) => {
                if (token.isCancellationRequested) return;
                fullResponse += chunk;
                stream.markdown(chunk);
            });
        } catch (err: any) {
            stream.markdown(`\n\n❌ **Error:** ${err.message}`);
            return { errorDetails: { message: err.message } };
        }

        // Update chat history
        chatHistory.push({ role: 'user', content: request.prompt });
        chatHistory.push({ role: 'assistant', content: fullResponse });

        // Keep history manageable
        if (chatHistory.length > 40) {
            chatHistory = chatHistory.slice(-40);
        }

        // Return followups
        return {
            metadata: { command: request.command },
        };
    };

    const participant = vscode.chat.createChatParticipant('omnia', handler);
    participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'resources', 'omnia-icon.svg');

    participant.followupProvider = {
        provideFollowups(_result: vscode.ChatResult, _context: vscode.ChatContext, _token: vscode.CancellationToken) {
            return [
                { prompt: '/explain', label: '📝 Explain the code' },
                { prompt: '/fix', label: '🔧 Fix issues' },
                { prompt: '/test', label: '🧪 Generate tests' },
                { prompt: '/commit', label: '💬 Generate commit message' },
                { prompt: '/refactor', label: '♻️ Refactor code' },
            ] as vscode.ChatFollowup[];
        }
    };

    context.subscriptions.push(participant);
    log('Chat participant @omnia registered');
}

// ============================================================
// Commands
// ============================================================

function registerCommands(context: vscode.ExtensionContext) {
    // Explain code — sends to Copilot Chat with @omnia
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('Please select some code first.');
                return;
            }
            // Use VSCode's chat API to send message
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: `@omnia /explain \`\`\`${editor.document.languageId}\n${selected}\n\`\`\``
            });
        })
    );

    // Fix code
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.fixCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('Please select some code first.');
                return;
            }
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: `@omnia /fix \`\`\`${editor.document.languageId}\n${selected}\n\`\`\``
            });
        })
    );

    // Inline edit with diff preview
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.inlineEdit', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
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
        })
    );

    // Quick edit
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.quickEdit', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;

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
        })
    );

    // Send to chat
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.sendToChat', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('Please select some code first.');
                return;
            }
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: `@omnia \`\`\`${editor.document.languageId}\n${selected}\n\`\`\`\n`
            });
        })
    );

    // Generate commit message
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.commitChanges', async () => {
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: '@omnia /commit'
            });
        })
    );

    // Generate tests
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const doc = editor.document;
            const content = doc.getText();
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: `@omnia /test \`\`\`${doc.languageId}\n${content}\n\`\`\``
            });
        })
    );

    // Clear chat history
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.clearHistory', () => {
            chatHistory = [];
            vscode.window.showInformationMessage('Omnia chat history cleared.');
        })
    );
}

// ============================================================
// Activation
// ============================================================

export function activate(context: vscode.ExtensionContext) {
    omniaChannel = vscode.window.createOutputChannel('Omnia AI');
    log('Omnia AI Assistant v0.4.0 activated (Native Chat API)');

    // Register diff content provider
    context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider('omnia-diff', diffProvider)
    );

    // Register CodeLens provider
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider('*', new OmniaCodeLensProvider())
    );

    // Register inline completion provider
    context.subscriptions.push(
        vscode.languages.registerInlineCompletionItemProvider('*', new OmniaCompletionProvider())
    );

    // Register Chat Participant (@omnia)
    registerChatParticipant(context);

    // Register all commands
    registerCommands(context);

    // Listen for editor changes
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            sendContext(editor, true);
        })
    );

    context.subscriptions.push(
        vscode.window.onDidChangeTextEditorSelection((e) => {
            sendContext(e.textEditor);
        })
    );

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

    vscode.window.showInformationMessage('Omnia AI is ready! Open Copilot Chat and type @omnia');
}

export function deactivate() {}
