"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const http = require("http");
const fs = require("fs");
let debounceTimer;
function debug(msg) {
    fs.appendFileSync('/tmp/omnia_ide_bridge.log', `${Date.now()} ${msg}\n`);
}
function buildContext(editor) {
    if (!editor) {
        return {
            file: null,
            language: null,
            line: null,
            column: null,
            selectedText: '',
            timestamp: Date.now(),
        };
    }
    const doc = editor.document;
    const pos = editor.selection.active;
    const selected = editor.selection.isEmpty ? '' : doc.getText(editor.selection);
    return {
        file: doc.fileName,
        language: doc.languageId,
        line: pos.line + 1,
        column: pos.character + 1,
        selectedText: selected.length > 200 ? selected.slice(0, 200) + '...' : selected,
        timestamp: Date.now(),
    };
}
function pushContext(ctx) {
    const cfg = vscode.workspace.getConfiguration('omnia.ideBridge');
    if (!cfg.get('enabled', true)) {
        debug('push skipped: disabled');
        return;
    }
    const endpoint = cfg.get('endpoint', 'http://127.0.0.1:5001/ide-context');
    const url = new URL(endpoint);
    const payload = JSON.stringify(ctx);
    const options = {
        hostname: url.hostname,
        port: parseInt(url.port || '80'),
        path: url.pathname,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(payload),
        },
    };
    debug(`pushing to ${endpoint} file=${ctx.file}`);
    const req = http.request(options, (res) => {
        debug(`response status=${res.statusCode}`);
    });
    req.on('error', (err) => {
        debug(`error ${err.message}`);
    });
    req.write(payload);
    req.end();
}
function send(editor, immediate = false) {
    const cfg = vscode.workspace.getConfiguration('omnia.ideBridge');
    const debounceMs = cfg.get('debounceMs', 300);
    if (immediate) {
        pushContext(buildContext(editor));
        return;
    }
    if (debounceTimer) {
        clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
        pushContext(buildContext(editor));
    }, debounceMs);
}
function activate(context) {
    debug('activate called');
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
        debug(`active editor changed: ${editor?.document.fileName || 'null'}`);
        send(editor, true);
    }));
    context.subscriptions.push(vscode.window.onDidChangeTextEditorSelection((e) => {
        send(e.textEditor);
    }));
    const delays = [500, 2000, 5000];
    delays.forEach((ms) => {
        const t = setTimeout(() => {
            const editor = vscode.window.activeTextEditor;
            debug(`retry ${ms} editor=${editor?.document.fileName || 'null'}`);
            if (editor) {
                send(editor, true);
            }
        }, ms);
        context.subscriptions.push({ dispose: () => clearTimeout(t) });
    });
    debug(`initial editor=${vscode.window.activeTextEditor?.document.fileName || 'null'}`);
    send(vscode.window.activeTextEditor, true);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map