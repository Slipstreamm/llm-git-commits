import * as vscode from 'vscode';
import * as path from 'path';
import { exec, execFile } from 'child_process';

const python = process.platform === 'win32' ? 'python' : 'python3';
const script = path.join(
  __dirname,
  '..',
  'python',
  'llm_git_commits',
  'main.py',
);

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand(
    'llmGitCommits.generateCommit',
    () => {
      runGenerateCommit();
    },
  );

  context.subscriptions.push(disposable);

  const sidebarProvider = new SidebarProvider();
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'llmGitCommits.sidebar',
      sidebarProvider,
    ),
  );
}

class SidebarProvider implements vscode.WebviewViewProvider {
  resolveWebviewView(view: vscode.WebviewView) {
    view.webview.options = { enableScripts: true };
    view.webview.html = getSidebarContent();
    view.webview.onDidReceiveMessage((msg) => {
      if (msg.command === 'generate') {
        runGenerateCommit();
      }
    });
  }
}

async function runGenerateCommit() {
  const output = vscode.window.createOutputChannel('llm-git-commits');
  output.show(true);
  const staged = await hasStagedChanges();
  const args = staged ? ['--extension-json'] : ['--auto-stage', '--extension-json'];

  execFile(python, [script, ...args], (err, stdout, stderr) => {
    if (err) {
      vscode.window.showErrorMessage(`Error running llm-git-commits: ${err.message}`);
      output.append(stderr);
      return;
    }
    try {
      const data = JSON.parse(stdout.trim());
      showWebview(data.commit_message, output);
    } catch {
      vscode.window.showErrorMessage('Failed to parse commit message output');
      output.append(stdout);
    }
  });
}

function hasStagedChanges(): Promise<boolean> {
  return new Promise((resolve) => {
    exec('git diff --cached --name-only', (err, stdout) => {
      if (err) {
        resolve(false);
        return;
      }
      resolve(stdout.trim().length > 0);
    });
  });
}

function showWebview(message: string, output: vscode.OutputChannel) {
  const panel = vscode.window.createWebviewPanel(
    'llmGitCommitsPreview',
    'LLM Commit Message',
    vscode.ViewColumn.Active,
    {
      enableScripts: true,
    }
  );

  panel.webview.onDidReceiveMessage((m) => {
    if (m.command === 'commit') {
      panel.dispose();
      output.appendLine('Committing...');
      execFile(
        python,
        [
          script,
          '--auto-stage',
          '--commit-message',
          message,
          '--no-confirm',
        ],
        (err, stdout, stderr) => {
          if (err) {
            vscode.window.showErrorMessage(`Commit failed: ${err.message}`);
            output.append(stderr);
            return;
          }
          vscode.window.showInformationMessage('Commit created');
          output.append(stdout);
        },
      );
    } else if (m.command === 'cancel') {
      panel.dispose();
    }
  });

  panel.webview.html = getWebviewContent(message);
}

function getWebviewContent(msg: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
body { font-family: sans-serif; padding: 20px; }
pre { background: #f3f3f3; padding: 1em; border-radius: 4px; white-space: pre-wrap; }
button { margin-right: 1em; padding: 0.5em 1em; }
</style>
</head>
<body>
<h2>Proposed Commit Message</h2>
<pre>${msg}</pre>
<button id="commit">Commit</button>
<button id="cancel">Cancel</button>
<script>
const vscode = acquireVsCodeApi();

document.getElementById('commit').addEventListener('click', () => {
  vscode.postMessage({ command: 'commit' });
});

document.getElementById('cancel').addEventListener('click', () => {
  vscode.postMessage({ command: 'cancel' });
});
</script>
</body>
</html>`;
}

function getSidebarContent(): string {
  return `<!DOCTYPE html>
<html lang="en">
<body>
  <button id="generate">Generate Commit</button>
  <script>
    const vscode = acquireVsCodeApi();
    document.getElementById('generate').addEventListener('click', () => {
      vscode.postMessage({ command: 'generate' });
    });
  </script>
</body>
</html>`;
}
