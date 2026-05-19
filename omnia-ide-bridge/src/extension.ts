import * as vscode from 'vscode';
import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import { OmniaChatPanel } from './chatPanel';

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

interface WorkspaceFileEdit {
    filePath: string;
    content: string;
    description?: string;
}

interface ProjectGenerationResponse {
    projectName: string;
    description: string;
    techStack: string;
    files: Array<{ path: string; content: string }>;
    dependencies?: string[];
    devDependencies?: string[];
    scripts?: Record<string, string>;
    setupCommands?: string[];
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
                fullContent = fullContent.slice(0, maxLen) + '\n... (已截断)';
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
        log(`上下文推送: ${res.statusCode}`);
    });
    req.on('error', (err) => log(`上下文推送错误: ${err.message}`));
    req.write(payload);
    req.end();
}

function sendContext(editor: vscode.TextEditor | undefined, immediate = false) {
    const debounceMs = vscode.workspace.getConfiguration('omnia.ideBridge').get<number>('debounceMs', 300);
    currentContext = buildContext(editor);

    // Also update chat panel if it exists
    if (OmniaChatPanel.currentPanel && currentContext) {
        OmniaChatPanel.currentPanel.updateContext(currentContext);
    }

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

async function callOmniaChatStream(prompt: string, onChunk: (text: string) => void): Promise<string> {
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
            let fullResponse = '';
            res.on('data', (chunk: Buffer) => {
                buffer += chunk.toString();
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            resolve(fullResponse);
                            return;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                fullResponse += parsed.content;
                                onChunk(parsed.content);
                            }
                        } catch { }
                    }
                }
            });
            res.on('end', () => resolve(fullResponse));
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
        title: 'Omnia AI: 正在生成修改...',
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: '思考中...' });

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
            vscode.window.showErrorMessage(`Omnia AI 错误: ${err.message}`);
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

    const diffTitle = `Omnia 编辑: ${instruction.slice(0, 50)}`;
    await vscode.commands.executeCommand(
        'vscode.diff',
        originalUri,
        modifiedUri,
        diffTitle
    );

    const action = await vscode.window.showInformationMessage(
        '应用此次修改？',
        { modal: true },
        '✅ 应用',
        '❌ 拒绝',
        '📋 复制'
    );

    if (action === '✅ 应用') {
        await editor.edit((editBuilder) => {
            editBuilder.replace(editor.selection, modified);
        });
        vscode.window.showInformationMessage('✅ 修改已应用！');
    } else if (action === '📋 复制') {
        await vscode.env.clipboard.writeText(modified);
        vscode.window.showInformationMessage('📋 已复制到剪贴板！');
    }
}

// ============================================================
// 🤖 手 #1: AI 终端命令执行
// ============================================================

async function executeTerminalCommand(command: string, cwd?: string): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve) => {
        const workspaceFolder = cwd || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.env.HOME || '/';

        exec(command, { cwd: workspaceFolder, timeout: 30000, maxBuffer: 1024 * 1024 * 5 }, (error, stdout, stderr) => {
            resolve({
                stdout: stdout || '',
                stderr: stderr || '',
                exitCode: error ? (error as any).code || 1 : 0,
            });
        });
    });
}

async function aiExecuteTerminal() {
    const instruction = await vscode.window.showInputBox({
        prompt: '描述你想做什么（AI 会生成并执行命令）',
        placeHolder: '例如：列出所有 Python 文件、查找 TODO 注释、检查磁盘空间...',
    });

    if (!instruction) return;

    // Ask AI to generate the command
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Omnia AI: 正在生成命令...',
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: 'AI 思考中...' });

        const platform = process.platform;
        const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.env.HOME || '/';

        const prompt = `你是一个终端命令生成器。用户在 ${platform} 系统上，当前工作目录是 ${cwd}。

用户需求: ${instruction}

**重要规则：**
1. 只输出一条可直接执行的终端命令，不要包含任何解释
2. 不要添加 markdown 代码块标记
3. 不要添加多余的换行
4. 确保命令在 ${platform} 上可执行
5. 如果需要多条命令，用 && 连接

请直接输出命令:`;

        try {
            let command = '';
            await callOmniaChatStream(prompt, (chunk) => {
                command += chunk;
            });

            command = cleanCodeResponse(command, '').trim();

            if (!command) {
                vscode.window.showErrorMessage('AI 未能生成命令。');
                return;
            }

            // Show generated command and ask for confirmation
            const autoConfirm = vscode.workspace.getConfiguration('omnia.ai.terminal').get<boolean>('autoConfirm', false);

            if (!autoConfirm) {
                const action = await vscode.window.showInformationMessage(
                    `执行命令？\n\n${command}`,
                    { modal: true },
                    '✅ 执行',
                    '✏️ 先编辑',
                    '❌ 取消'
                );

                if (action === '✏️ 先编辑') {
                    const edited = await vscode.window.showInputBox({
                        value: command,
                        prompt: '编辑命令后再执行',
                    });
                    if (!edited) return;
                    command = edited;
                } else if (action !== '✅ 执行') {
                    return;
                }
            }

            // Execute
            progress.report({ message: '执行中...' });
            const result = await executeTerminalCommand(command, cwd);

            // Show result in terminal output panel
            const terminalOutput = `> ${command}\n\n${result.stdout}${result.stderr ? `\n[错误输出]: ${result.stderr}` : ''}\n\n退出码: ${result.exitCode}`;

            // Create output document
            const doc = await vscode.workspace.openTextDocument({
                content: terminalOutput,
                language: 'shellscript',
            });
            await vscode.window.showTextDocument(doc, { preview: true });

            if (result.exitCode === 0) {
                vscode.window.showInformationMessage(`✅ 命令执行成功 (退出码 0)`);
            } else {
                vscode.window.showWarningMessage(`⚠️ 命令退出码 ${result.exitCode}`);
            }

            log(`终端命令执行: ${command} -> 退出码 ${result.exitCode}`);
        } catch (err: any) {
            vscode.window.showErrorMessage(`终端错误: ${err.message}`);
        }
    });
}

// ============================================================
// 📁 手 #2: 多文件批量编辑
// ============================================================

async function aiMultiFileEdit() {
    const instruction = await vscode.window.showInputBox({
        prompt: '描述你想要的多文件修改（AI 会生成变更）',
        placeHolder: '例如：给所有 API 文件添加日志、在项目中重命名函数 X 为 Y...',
    });

    if (!instruction) return;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Omnia AI: 正在分析项目进行多文件编辑...',
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: '扫描项目文件...' });

        // Gather project context
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('没有打开工作区文件夹。');
            return;
        }

        // Find relevant files (limit to reasonable number)
        progress.report({ message: '查找相关文件...' });
        const allFiles = await vscode.workspace.findFiles('**/*.{ts,js,py,java,cpp,c,go,rs,md,json,yaml,yml}', '**/node_modules/**', 50);

        let projectContext = `[项目根目录]: ${workspaceFolder.uri.fsPath}\n\n`;
        const maxFileLen = 500;

        for (const file of allFiles.slice(0, 20)) {
            try {
                const content = fs.readFileSync(file.fsPath, 'utf-8');
                const relPath = path.relative(workspaceFolder.uri.fsPath, file.fsPath);
                const truncated = content.length > maxFileLen ? content.slice(0, maxFileLen) + '\n...(已截断)' : content;
                projectContext += `[文件: ${relPath}]\n\`\`\`\n${truncated}\n\`\`\`\n\n`;
            } catch { }
        }

        // Ask AI for multi-file changes
        progress.report({ message: 'AI 正在规划修改...' });

        const prompt = `你是一个代码编辑助手。用户想要对多个文件进行修改。

**项目信息:**
${projectContext}

**用户指令:** ${instruction}

**重要规则：**
1. 输出一个 JSON 数组，每个元素包含 filePath (相对路径), content (修改后的完整文件内容), description (修改说明)
2. 只输出 JSON，不要包含任何其他文字
3. 不要添加 markdown 代码块标记
4. filePath 使用相对路径
5. content 必须是修改后的完整文件内容

请直接输出 JSON 数组:`;

        try {
            let response = '';
            await callOmniaChatStream(prompt, (chunk) => {
                response += chunk;
            });

            // Parse response
            let cleaned = response.trim();
            cleaned = cleaned.replace(/^```[\w]*\n?/gm, '');
            cleaned = cleaned.replace(/```$/gm, '');

            let edits: WorkspaceFileEdit[];
            try {
                edits = JSON.parse(cleaned.trim());
            } catch {
                vscode.window.showErrorMessage('AI 返回了无效的 JSON。请重试或简化你的请求。');
                log(`无效的 JSON 响应: ${cleaned.slice(0, 200)}`);
                return;
            }

            if (!Array.isArray(edits) || edits.length === 0) {
                vscode.window.showWarningMessage('AI 没有生成任何修改。');
                return;
            }

            // Show summary and ask for confirmation
            const summary = edits.map(e => `• ${e.filePath}: ${e.description || '已修改'}`).join('\n');
            const action = await vscode.window.showInformationMessage(
                `应用 ${edits.length} 个文件修改？\n\n${summary}`,
                { modal: true },
                '✅ 全部应用',
                '👁️ 先预览',
                '❌ 取消'
            );

            if (action === '❌ 取消' || !action) return;

            if (action === '👁️ 先预览') {
                // Show each edit in diff view
                for (const edit of edits) {
                    const fullPath = path.join(workspaceFolder.uri.fsPath, edit.filePath);
                    let original = '';
                    try {
                        original = fs.readFileSync(fullPath, 'utf-8');
                    } catch {
                        original = '(新文件)';
                    }

                    const originalUri = vscode.Uri.parse(`omnia-diff:orig_${Date.now()}_${edit.filePath}.txt`);
                    const modifiedUri = vscode.Uri.parse(`omnia-diff:mod_${Date.now()}_${edit.filePath}.txt`);
                    diffProvider.setContent(originalUri.toString(), original);
                    diffProvider.setContent(modifiedUri.toString(), edit.content);

                    await vscode.commands.executeCommand('vscode.diff', originalUri, modifiedUri, `Omnia: ${edit.description || edit.filePath}`);
                }

                const applyAction = await vscode.window.showInformationMessage(
                    '现在应用所有修改？',
                    '✅ 全部应用',
                    '❌ 取消'
                );

                if (applyAction !== '✅ 全部应用') return;
            }

            // Apply all edits
            progress.report({ message: '正在应用修改...' });
            const workspaceEdit = new vscode.WorkspaceEdit();

            for (const edit of edits) {
                const fullPath = path.join(workspaceFolder.uri.fsPath, edit.filePath);
                const uri = vscode.Uri.file(fullPath);

                try {
                    const existing = fs.readFileSync(fullPath, 'utf-8');
                    // Replace entire file
                    const fullRange = new vscode.Range(0, 0, existing.split('\n').length, 0);
                    workspaceEdit.replace(uri, fullRange, edit.content);
                } catch {
                    // File doesn't exist, create it
                    workspaceEdit.createFile(uri, { ignoreIfExists: true });
                    workspaceEdit.insert(uri, new vscode.Position(0, 0), edit.content);
                }
            }

            const success = await vscode.workspace.applyEdit(workspaceEdit);
            if (success) {
                vscode.window.showInformationMessage(`✅ 已应用 ${edits.length} 个文件修改！`);
                log(`多文件编辑已应用: ${edits.length} 个文件`);
            } else {
                vscode.window.showErrorMessage('应用工作区编辑失败。');
            }
        } catch (err: any) {
            vscode.window.showErrorMessage(`多文件编辑错误: ${err.message}`);
        }
    });
}

// ============================================================
// 🏗️ 手 #4: Builder Mode - AI 项目生成
// ============================================================

async function aiCreateProject() {
    // 1. Ask for project description
    const description = await vscode.window.showInputBox({
        prompt: '描述你想要创建的项目',
        placeHolder: '例如：一个 React 计算器应用、Python Flask API、Node.js Express 后端...',
    });

    if (!description) return;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Omnia AI: 正在生成项目...',
        cancellable: false,
    }, async (progress) => {
        progress.report({ message: 'AI 正在设计项目结构...' });

        // 2. Ask AI to generate project structure
        const prompt = `你是一个项目生成器。用户想要创建一个项目。

**用户描述:** ${description}

**重要规则：**
1. 输出一个 JSON 对象，包含以下字段：
   - projectName: 项目名称（小写字母、数字、连字符）
   - description: 项目描述
   - techStack: 使用的技术栈
   - files: 数组，每个元素包含 path (相对路径) 和 content (文件内容)
   - dependencies: 生产依赖数组 (可选)
   - devDependencies: 开发依赖数组 (可选)
   - scripts: npm scripts 对象 (可选)
   - setupCommands: 初始化命令数组 (可选，如 ["npm install", "git init"])
2. 只输出 JSON，不要包含任何其他文字
3. 不要添加 markdown 代码块标记
4. 确保生成的代码是完整、可运行的
5. 包含必要的配置文件（如 package.json, tsconfig.json 等）
6. 如果是前端项目，包含 index.html 和入口文件
7. 如果是后端项目，包含主入口文件和路由示例

请直接输出 JSON:`;

        try {
            let response = '';
            await callOmniaChatStream(prompt, (chunk) => {
                response += chunk;
            });

            // Parse response
            let cleaned = response.trim();
            cleaned = cleaned.replace(/^```[\w]*\n?/gm, '');
            cleaned = cleaned.replace(/```$/gm, '');

            let projectData: ProjectGenerationResponse;
            try {
                projectData = JSON.parse(cleaned.trim());
            } catch {
                vscode.window.showErrorMessage('AI 返回了无效的 JSON。请重试或简化你的请求。');
                log(`无效的 JSON 响应: ${cleaned.slice(0, 200)}`);
                return;
            }

            if (!projectData.files || projectData.files.length === 0) {
                vscode.window.showWarningMessage('AI 没有生成任何文件。');
                return;
            }

            // 3. Show preview and ask for confirmation
            const fileList = projectData.files.map(f => `• ${f.path}`).join('\n');
            const summary = `项目: ${projectData.projectName}\n描述: ${projectData.description}\n技术栈: ${projectData.techStack}\n\n文件列表:\n${fileList}`;

            const action = await vscode.window.showInformationMessage(
                `创建项目？\n\n${summary}`,
                { modal: true },
                '✅ 创建项目',
                '👁️ 预览文件',
                '❌ 取消'
            );

            if (action === '❌ 取消' || !action) return;

            // 4. Get workspace folder
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) {
                vscode.window.showErrorMessage('没有打开工作区文件夹。请先打开一个文件夹。');
                return;
            }

            const projectRoot = path.join(workspaceFolder.uri.fsPath, projectData.projectName);

            // 5. Create project directory
            progress.report({ message: '创建项目目录...' });
            if (!fs.existsSync(projectRoot)) {
                fs.mkdirSync(projectRoot, { recursive: true });
            }

            // 6. Create all files
            progress.report({ message: '生成项目文件...' });
            for (const file of projectData.files) {
                const filePath = path.join(projectRoot, file.path);
                const dir = path.dirname(filePath);

                if (!fs.existsSync(dir)) {
                    fs.mkdirSync(dir, { recursive: true });
                }

                fs.writeFileSync(filePath, file.content, 'utf-8');
                log(`创建文件: ${file.path}`);
            }

            // 7. Show preview if requested
            if (action === '👁️ 预览文件') {
                for (const file of projectData.files.slice(0, 5)) { // Preview first 5 files
                    const filePath = path.join(projectRoot, file.path);
                    const doc = await vscode.workspace.openTextDocument(filePath);
                    await vscode.window.showTextDocument(doc, { preview: true });
                }
            }

            // 8. Run setup commands
            if (projectData.setupCommands && projectData.setupCommands.length > 0) {
                progress.report({ message: '执行初始化命令...' });

                for (const cmd of projectData.setupCommands) {
                    log(`执行命令: ${cmd}`);
                    const result = await executeTerminalCommand(cmd, projectRoot);

                    if (result.exitCode !== 0) {
                        log(`命令失败: ${cmd}\n${result.stderr}`);
                        vscode.window.showWarningMessage(`命令执行失败: ${cmd}`);
                    } else {
                        log(`命令成功: ${cmd}`);
                    }
                }
            }

            // 9. Success message
            vscode.window.showInformationMessage(`✅ 项目 "${projectData.projectName}" 已创建！\n\n位置: ${projectRoot}`);

            // 10. Open the project folder
            const openFolder = await vscode.window.showInformationMessage(
                '是否在新窗口中打开项目？',
                '✅ 打开',
                '❌ 稍后'
            );

            if (openFolder === '✅ 打开') {
                vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(projectRoot), true);
            }

            log(`项目已创建: ${projectData.projectName}`);

        } catch (err: any) {
            vscode.window.showErrorMessage(`项目生成错误: ${err.message}`);
        }
    });
}

// ============================================================
// 🔀 手 #3: AI Git 操作
// ============================================================

async function getGitStatus(): Promise<string> {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!cwd) return '';

    const result = await executeTerminalCommand('git status --short && echo "---" && git diff --stat && echo "---" && git diff --cached --stat', cwd);
    return result.stdout;
}

async function aiGitCommit() {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!cwd) {
        vscode.window.showErrorMessage('没有打开工作区文件夹。');
        return;
    }

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Omnia AI: 正在分析变更...',
        cancellable: false,
    }, async (progress) => {
        // Get git status and diff
        progress.report({ message: '读取 Git 状态...' });
        const gitStatus = await getGitStatus();

        if (!gitStatus.trim()) {
            vscode.window.showWarningMessage('没有检测到变更。');
            return;
        }

        // Get the actual diff
        const diffResult = await executeTerminalCommand('git diff HEAD', cwd);
        const diffContent = diffResult.stdout.slice(0, 4000); // Limit size

        // Ask AI for commit message
        progress.report({ message: 'AI 正在编写提交信息...' });

        const prompt = `你是一个 Git commit 消息生成器。

**Git 状态:**
${gitStatus}

**差异 (已截断):**
\`\`\`
${diffContent}
\`\`\`

**规则:**
1. 生成一个简洁的 commit 消息（Conventional Commits 格式）
2. 第一行是主题（不超过 72 字符）
3. 空一行后可以加正文（可选）
4. 只输出 commit 消息，不要其他内容
5. 不要添加 markdown 标记

请直接输出 commit 消息:`;

        try {
            let commitMsg = '';
            await callOmniaChatStream(prompt, (chunk) => {
                commitMsg += chunk;
            });

            commitMsg = cleanCodeResponse(commitMsg, '').trim();

            // Show and allow editing
            const editedMsg = await vscode.window.showInputBox({
                value: commitMsg,
                prompt: '编辑提交信息（或按回车使用 AI 建议）',
                placeHolder: 'feat: 你的提交信息',
            });

            if (!editedMsg) return;

            // Stage all and commit
            progress.report({ message: '提交中...' });
            const stageResult = await executeTerminalCommand('git add -A', cwd);
            const commitResult = await executeTerminalCommand(`git commit -m "${editedMsg.replace(/"/g, '\\"')}"`, cwd);

            if (commitResult.exitCode === 0) {
                vscode.window.showInformationMessage(`✅ 已提交: ${editedMsg.split('\n')[0]}`);
                log(`Git 提交: ${editedMsg.split('\n')[0]}`);
            } else {
                vscode.window.showErrorMessage(`提交失败: ${commitResult.stderr}`);
            }
        } catch (err: any) {
            vscode.window.showErrorMessage(`Git 提交错误: ${err.message}`);
        }
    });
}

async function showGitDiff() {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!cwd) {
        vscode.window.showErrorMessage('没有打开工作区文件夹。');
        return;
    }

    const result = await executeTerminalCommand('git diff HEAD', cwd);

    if (!result.stdout.trim()) {
        vscode.window.showInformationMessage('没有变更可显示。');
        return;
    }

    const doc = await vscode.workspace.openTextDocument({
        content: result.stdout,
        language: 'diff',
    });
    await vscode.window.showTextDocument(doc, { preview: true });
}

// ============================================================
// CodeLens Provider
// ============================================================

class OmniaCodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
    onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

    provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
        const lenses: vscode.CodeLens[] = [];

        for (let i = 0; i < document.lineCount; i++) {
            const line = document.lineAt(i);
            const text = line.text.trim();

            if (text.match(/^(function|def|async function|const \w+ = |class |public |private |protected )/)) {
                const range = new vscode.Range(i, 0, i, 0);
                lenses.push(new vscode.CodeLens(range, {
                    title: '📝 解释',
                    command: 'omnia.explainCode',
                    arguments: [document, range],
                    tooltip: '让 Omnia 解释这段代码'
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

        const prompt = `继续这段代码（只输出续写内容，不要解释）:
\`\`\`${document.languageId}
${textBefore}
\`\`\`

从断点处继续:`;

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
            log(`补全错误: ${err}`);
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
                const truncated = content.length > maxLen ? content.slice(0, maxLen) + '\n... (已截断)' : content;
                processed = processed.replace(ref, `\n[文件: ${fileName}]\n\`\`\`\n${truncated}\n\`\`\`\n`);
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
// Commands
// ============================================================

function registerCommands(context: vscode.ExtensionContext) {
    // Open chat panel
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.openChat', () => {
            OmniaChatPanel.createOrShow(context.extensionUri);
        })
    );

    // Explain code
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('请先选中代码。');
                return;
            }
            // Open chat and send message
            OmniaChatPanel.createOrShow(context.extensionUri);
            setTimeout(() => {
                if (OmniaChatPanel.currentPanel) {
                    (OmniaChatPanel.currentPanel as any)._handleUserMessage(`请解释这段代码:\n\`\`\`${editor.document.languageId}\n${selected}\n\`\`\``);
                }
            }, 500);
        })
    );

    // Fix code
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.fixCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('请先选中代码。');
                return;
            }
            // Open chat and send message
            OmniaChatPanel.createOrShow(context.extensionUri);
            setTimeout(() => {
                if (OmniaChatPanel.currentPanel) {
                    (OmniaChatPanel.currentPanel as any)._handleUserMessage(`请修复这段代码中的问题:\n\`\`\`${editor.document.languageId}\n${selected}\n\`\`\``);
                }
            }, 500);
        })
    );

    // Inline edit with diff preview
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.inlineEdit', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selected = editor.document.getText(editor.selection);
            if (!selected) {
                vscode.window.showWarningMessage('请先选中代码。');
                return;
            }

            const instruction = await vscode.window.showInputBox({
                prompt: '如何修改这段代码？',
                placeHolder: '例如：添加错误处理、优化性能、添加类型标注...',
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
                prompt: '编辑指令',
                placeHolder: '你想修改什么？',
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
                vscode.window.showWarningMessage('请先选中代码。');
                return;
            }
            // Open chat and send message
            OmniaChatPanel.createOrShow(context.extensionUri);
            setTimeout(() => {
                if (OmniaChatPanel.currentPanel) {
                    (OmniaChatPanel.currentPanel as any)._handleUserMessage(selected);
                }
            }, 500);
        })
    );

    // Generate commit message
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.commitChanges', async () => {
            await aiGitCommit();
        })
    );

    // Generate tests
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const doc = editor.document;
            const content = doc.getText();
            // Open chat and send message
            OmniaChatPanel.createOrShow(context.extensionUri);
            setTimeout(() => {
                if (OmniaChatPanel.currentPanel) {
                    (OmniaChatPanel.currentPanel as any)._handleUserMessage(`请为这段代码生成单元测试:\n\`\`\`${doc.languageId}\n${content}\n\`\`\``);
                }
            }, 500);
        })
    );

    // Clear chat history
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.clearHistory', () => {
            chatHistory = [];
            vscode.window.showInformationMessage('Omnia 聊天记录已清空。');
        })
    );

    // 🤖 手 #1: 终端命令执行
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.executeTerminal', () => aiExecuteTerminal())
    );

    // 📁 手 #2: 多文件编辑
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.applyWorkspaceEdit', () => aiMultiFileEdit())
    );

    // 🏗️ 手 #4: 项目生成
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.createProject', () => aiCreateProject())
    );

    // 🔀 手 #3: Git 提交
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.gitCommit', () => aiGitCommit())
    );

    // 🔀 Git 差异
    context.subscriptions.push(
        vscode.commands.registerCommand('omnia.gitDiff', () => showGitDiff())
    );
}

// ============================================================
// Activation
// ============================================================

export function activate(context: vscode.ExtensionContext) {
    omniaChannel = vscode.window.createOutputChannel('Omnia AI');
    log('Omnia AI 助手 v0.8.0 已激活（Webview 聊天面板 + 四只手）');

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

    // Auto-open chat panel on startup
    setTimeout(() => {
        OmniaChatPanel.createOrShow(context.extensionUri);
    }, 1000);

    vscode.window.showInformationMessage('Omnia AI 已就绪！使用 Ctrl+Shift+O 打开聊天');
}

export function deactivate() {}