# AI Commit VS Code Extension

AI Commit helps you craft commit messages for staged changes using large language models. The extension talks directly to providers such as OpenRouter, OpenAI, Anthropic, and Google Gemini – no separate Python tools are required.

## Features

- Generate a commit message from your staged diff with a single command
- Choose between several message styles: Conventional Commit, Descriptive (Past Tense), Emoji‑Prefixed, or a simple Default style
- Configure your preferred provider, model, and API key in a dedicated settings panel
- Works with the built‑in Git extension and inserts the result straight into the commit input box

## Getting Started

1. Install **AI Commit** from the VS Code Marketplace or load the packaged `.vsix` file.
2. Open a Git repository and stage the changes you want to commit.
3. Run **`AI Commit: Generate Commit Message`** from the Command Palette or use the button shown in the Source Control view.
4. Review the generated text in the commit box and edit it if needed before committing.

### Configuration

Use **`AI Commit: Open Settings`** to open the webview panel where you can:

- Select your LLM provider (OpenRouter, OpenAI, Anthropic, or Gemini)
- Enter the API key and model for that provider
- Pick the style used for generated messages

Settings are stored globally in VS Code, so you only need to configure them once.

## Requirements

- VS Code 1.101.0 or later
- A valid API key for your chosen provider

The extension runs entirely within Node.js and does not depend on the `llm-git-commits` Python CLI.

## License

This extension is released under the MIT License. See the [LICENSE](LICENSE) file for details.

