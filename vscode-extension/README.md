# LLM Git Commits VS Code Extension

This extension integrates the `llm-git-commits` tool with Visual Studio Code. It can generate commit messages using an LLM and let you commit directly from the editor.

## Usage

1. Run the `LLM Git: Generate Commit` command from the Command Palette or use the **Generate Commit** button in the Source Control view.
2. You can also open the *LLM Git Commits* sidebar panel to trigger generation.
3. A preview webview shows the proposed commit message.
4. Click **Commit** to finalize the commit or **Cancel** to close.

The Python CLI is bundled with the extension so you don't need to install it separately. A Python interpreter must be available on your system.
