import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getAiCompletion } from './backend/aiService';
import { GitService } from './backend/gitService';
import { ExtensionConfig } from './backend/types';

export function activate(context: vscode.ExtensionContext) {
    console.log('AI-Commit extension is now active.');

    // Register the command to show the settings webview
    const showSettingsCommand = vscode.commands.registerCommand('ai-commit.showSettings', () => {
        SettingsPanel.createOrShow(context);
    });
    context.subscriptions.push(showSettingsCommand);

    // Register the command to generate the commit message
    const generateCommitCommand = vscode.commands.registerCommand('ai-commit.generateCommitMessage', async () => {
        await generateCommitMessage();
    });
    context.subscriptions.push(generateCommitCommand);

    console.log('AI-Commit commands registered.');
}

export function deactivate() {}

function getExtensionConfig(): ExtensionConfig {
    const config = vscode.workspace.getConfiguration('aiCommit');
    const provider = config.get<ExtensionConfig['provider']>('provider', 'openrouter');
    
    return {
        provider,
        commitStyle: config.get<ExtensionConfig['commitStyle']>('commit.style', 'Conventional Commit'),
        providers: {
            openrouter: {
                apiKey: config.get<string>('openrouter.apiKey', ''),
                model: config.get<string>('openrouter.model', 'google/gemini-flash-1.5'),
            },
            openai: {
                apiKey: config.get<string>('openai.apiKey', ''),
                model: config.get<string>('openai.model', 'gpt-4o-mini'),
            },
            anthropic: {
                apiKey: config.get<string>('anthropic.apiKey', ''),
                model: config.get<string>('anthropic.model', 'claude-3-haiku-20240307'),
            },
            gemini: {
                apiKey: config.get<string>('gemini.apiKey', ''),
                model: config.get<string>('gemini.model', 'gemini-1.5-flash-latest'),
            },
        }
    };
}

/**
 * Main function to generate the commit message.
 */
async function generateCommitMessage() {
    try {
        const gitService = await GitService.create();
        const repo = gitService.getRepository();
        const stagedChanges = await gitService.getStagedDiff();

        if (!stagedChanges) {
            vscode.window.showInformationMessage('No staged changes found. Please stage files to generate a commit message.');
            return;
        }

        const config = getExtensionConfig();
        const providerConfig = config.providers[config.provider];

        if (!providerConfig.apiKey) {
            vscode.window.showErrorMessage(`AI Commit: API Key for ${config.provider} is not set. Please set it in the settings.`, 'Open Settings')
                .then(selection => {
                    if (selection === 'Open Settings') {
                        vscode.commands.executeCommand('ai-commit.showSettings');
                    }
                });
            return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.SourceControl,
            title: `AI Commit: Generating message with ${config.provider}...`,
            cancellable: false
        }, async () => {
            try {
                const commitMessage = await getAiCompletion(stagedChanges, config);
                repo.inputBox.value = commitMessage;
            } catch (error: any) {
                vscode.window.showErrorMessage(`Error generating commit message: ${error.message}`);
            }
        });

    } catch (error: any) {
        vscode.window.showErrorMessage(`AI Commit Error: ${error.message}`);
    }
}


function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

/**
 * Manages the settings webview panel.
 */
class SettingsPanel {
    public static currentPanel: SettingsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionPath: string;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(context: vscode.ExtensionContext) {
        const column = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.viewColumn : undefined;

        if (SettingsPanel.currentPanel) {
            SettingsPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'aiCommitSettings',
            'AI Commit Settings',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.file(path.join(context.extensionPath, 'dist', 'webview'))]
            }
        );

        SettingsPanel.currentPanel = new SettingsPanel(panel, context.extensionPath);
    }

    private constructor(panel: vscode.WebviewPanel, extensionPath: string) {
        this._panel = panel;
        this._extensionPath = extensionPath;

        this._update();

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(
            async message => {
                switch (message.command) {
                    case 'getSettings':
                        this._sendSettings();
                        break;
                    case 'updateSetting':
                        await vscode.workspace.getConfiguration('aiCommit').update(message.key, message.value, vscode.ConfigurationTarget.Global);
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    private _sendSettings() {
        const config = getExtensionConfig();
        this._panel.webview.postMessage({
            command: 'setSettings',
            settings: config
        });
    }

    private _update() {
        const webview = this._panel.webview;
        this._panel.title = 'AI Commit Settings';

        const htmlPath = path.join(this._extensionPath, 'dist', 'webview', 'settings.html');
        let htmlContent = fs.readFileSync(htmlPath, 'utf8');

        const nonce = getNonce();

        const cssUri = webview.asWebviewUri(vscode.Uri.file(path.join(this._extensionPath, 'dist', 'webview', 'settings.css')));
        const jsUri = webview.asWebviewUri(vscode.Uri.file(path.join(this._extensionPath, 'dist', 'webview', 'settings.js')));

        htmlContent = htmlContent.replace(/#{cspSource}/g, webview.cspSource);
        htmlContent = htmlContent.replace(/#{nonce}/g, nonce);
        htmlContent = htmlContent.replace(/#{cssUri}/g, cssUri.toString());
        htmlContent = htmlContent.replace(/#{jsUri}/g, jsUri.toString());

        webview.html = htmlContent;
    }

    public dispose() {
        SettingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}
