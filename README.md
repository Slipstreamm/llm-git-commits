# 🤖 Intelligent Git Commit Tool

An AI-powered command-line tool that automatically generates meaningful commit messages and manages project documentation using Large Language Models (LLMs) from multiple providers including OpenRouter, OpenAI, Anthropic, and Google Gemini.

## ✨ Features

### 🎯 Smart Commit Messages
- **AI-Generated**: Creates contextual, descriptive commit messages by analyzing your code changes
- **Conventional Commits**: Follows best practices with proper type prefixes (`feat:`, `fix:`, `docs:`, etc.)
- **Customizable**: Override generated messages or use different AI models

### 🔍 Interactive Staging
- **Hunk-by-Hunk**: Stage individual changes within files, similar to `git add -p`
- **Visual Diff**: Colored output showing additions, deletions, and context
- **Flexible Options**: Auto-stage all changes, select specific files, or choose individual hunks

### 🧠 Intelligent Staging
- **Automatic Commit Planning**: Let the LLM analyze all your changes and group them into logical, separate commits.
- **Multi-Commit Workflow**: Automatically generates multiple focused commit messages for the planned commits.
- **Interactive Confirmation**: Review and approve each proposed commit before it's made.

### 📚 Documentation Management
- **Smart Analysis**: Automatically suggests documentation updates based on code changes
- **CRUD Operations**: Create, update, and manage documentation files
- **Simple Patch Format**: Uses an LLM-friendly patch system for precise updates
- **Multi-Format Support**: Works with Markdown, reStructuredText, and plain text files

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git repository
- API keys for OpenRouter, OpenAI, Anthropic, or Google Gemini

### Installation

1. **Install from PyPI**:
   ```bash
   pip install llm-git-commits
   ```

2. **Configure the tool**:
   Run the interactive configuration wizard to set up your provider, API key, and default model.
   ```bash
   llm-git-commits config
   ```

### Basic Usage

```bash
# Interactive mode - stage changes selectively
llm-git-commits -i

# Auto-commit all changes
llm-git-commits -a

# Manage documentation
llm-git-commits --docs-dir ./docs --docs-only

# Let the AI create multiple commits automatically
llm-git-commits --intelligent
```

## 📖 Detailed Usage

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `config` | | Run the interactive configuration wizard. |
| `--interactive` | `-i` | Interactive hunk staging mode. |
| `--auto-stage` | `-a` | Automatically stage all changes. |
| `--intelligent` | | Use LLM to group changes into multiple commits. |
| `--docs-dir` | | Path to documentation directory. |
| `--docs-only` | | Only perform documentation management. |
| `--commit-message` | `-m` | Override generated commit message. |

### Usage Examples

#### 1. Interactive Staging (Recommended)
```bash
llm-git-commits -i
```

This mode lets you:
- Review each change individually
- Stage only the changes you want to commit
- Generate focused commit messages for specific changes

#### 2. Quick Commit All Changes
```bash
llm-git-commits -a
```

Perfect for when you want to commit all your changes with an AI-generated message.

#### 3. Documentation Management
```bash
llm-git-commits --docs-dir ./docs --docs-only
```

The tool will:
- Analyze your recent changes
- Suggest documentation updates
- Help create or update documentation files
- Use a simple patch system for precise edits

#### 4. Intelligent Staging
```bash
llm-git-commits --intelligent
```
This mode analyzes all modified files and uses the LLM to group related changes into separate, logical commits. It will then propose each commit for your approval.

## 🛠️ How It Works

### Commit Message Generation

The tool analyzes your staged changes and generates commit messages following these principles:

- **Conventional Commits**: Uses standard prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, etc.)
- **Imperative Mood**: "Add feature" not "Added feature"
- **Descriptive**: Explains what and why, not just what
- **Concise**: First line under 50 characters

Example generated messages:
```
feat(auth): add OAuth2 login support
fix(api): handle null response in user endpoint
docs: update installation instructions for Docker
refactor: simplify database connection logic
```

### Interactive Staging

When you use `--interactive`, the tool:

1. **Parses Diffs**: Breaks down file changes into individual "hunks"
2. **Shows Previews**: Displays colored diffs for each change
3. **Prompts for Action**: Ask whether to stage each hunk
4. **Applies Changes**: Uses `git apply --cached` to stage selected hunks

### Documentation Updates

The documentation system:

1. **Analyzes Context**: Reviews recent commits, modified files, and project structure
2. **Suggests Changes**: Recommends documentation updates based on code changes
3. **Provides Templates**: Generates new documentation from scratch
4. **Applies Patches**: Uses a simple patch format for precise updates

#### Patch Format

The tool uses a simple, LLM-friendly patch format:

```
PATCH_START
SECTION: Installation
ACTION: REPLACE
CONTENT:
## Installation

1. Install Python 3.8+
2. Run: `pip install -r requirements.txt`
3. Set up your config file
PATCH_END
```

## 🎨 Interactive Mode Demo

```
📝 File: src/auth.py
==================================================

Hunk 1/3:
@@ -45,6 +45,12 @@ def authenticate(username, password):
     if not username or not password:
         return False
     
+    # Add rate limiting
+    if check_rate_limit(username):
+        raise RateLimitError("Too many attempts")
+    
     user = get_user(username)
     return verify_password(user, password)

Stage this hunk? [y/n/q/d]: y

🤖 Generating commit message...

📝 Proposed commit message:
--------------------------------------------------
feat(auth): add rate limiting to authentication

Prevents brute force attacks by limiting login attempts
per username. Raises RateLimitError when threshold exceeded.
--------------------------------------------------

Proceed with commit? [Y/n]: 
```

## 🔧 Configuration

### Configuration File

The first time you run `llm-git-commits config`, it will create a configuration file at `~/.config/git-commit-tool/config.ini`. This file stores your API keys, default model, and other preferences.

You can edit this file manually or re-run `llm-git-commits config` at any time.

### Model Selection

During the interactive configuration, you can search for and select from all models available from your chosen provider.

Popular models include:

| Provider | Model Name |
|---|---|
| **OpenRouter** | `google/gemini-2.5-flash-preview-05-20` (Default) |
| | `anthropic/claude-sonnet-4-20250514` |
| | `openai/gpt-4o-mini` |
| **OpenAI** | `gpt-4o-mini` |
| **Anthropic** | `claude-sonnet-4-20250514` |

## 🤝 Contributing

Contributions are welcome! Here are some ways to help:

- **Bug Reports**: Found an issue? Please open an issue with details
- **Feature Requests**: Have an idea? We'd love to hear it
- **Code Contributions**: Submit pull requests for improvements
- **Documentation**: Help improve these docs

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Slipstreamm/llm-git-commits.git
cd llm-git-commits

# Install in editable mode
pip install -e .

# Run tests (if you add them)
python -m pytest tests/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenRouter** for providing easy access to multiple LLM providers
- **Conventional Commits** for the commit message format specification
- **Git** for the amazing version control system that makes this all possible

## 🆘 Troubleshooting

### Common Issues

**"Not in a git repository"**
- Make sure you're running the tool from within a git repository
- Initialize a repo with `git init` if needed

**"LLM API call failed"**
- Check your API key is correct and has credits
- Verify network connectivity
- Try a different model

**"Failed to stage changes"**
- Ensure files aren't locked or in use by other processes
- Check git status for any conflicts

**"No changes staged for commit"**
- Make sure you have modified files
- Try `git status` to see what's changed
- Use `--auto-stage` to stage everything

### Getting Help

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check this README and inline help (`--help`)
