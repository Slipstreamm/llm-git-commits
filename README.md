# 🤖 Intelligent Git Commit Tool

An AI-powered command-line tool that automatically generates meaningful commit messages and manages project documentation using Large Language Models (LLMs) via OpenRouter API.

## ✨ Features

### 🎯 Smart Commit Messages
- **AI-Generated**: Creates contextual, descriptive commit messages by analyzing your code changes
- **Conventional Commits**: Follows best practices with proper type prefixes (`feat:`, `fix:`, `docs:`, etc.)
- **Customizable**: Override generated messages or use different AI models

### 🔍 Interactive Staging
- **Hunk-by-Hunk**: Stage individual changes within files, similar to `git add -p`
- **Visual Diff**: Colored output showing additions, deletions, and context
- **Flexible Options**: Auto-stage all changes, select specific files, or choose individual hunks

### 📚 Documentation Management
- **Smart Analysis**: Automatically suggests documentation updates based on code changes
- **CRUD Operations**: Create, update, and manage documentation files
- **Simple Patch Format**: Uses an LLM-friendly patch system for precise updates
- **Multi-Format Support**: Works with Markdown, reStructuredText, and plain text files

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Git repository
- OpenRouter API key ([Get one here](https://openrouter.ai/))

### Installation

1. **Clone or download the script**:
   ```bash
   wget https://raw.githubusercontent.com/your-repo/git-commit-tool.py
   chmod +x git-commit-tool.py
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   ```

3. **Set up your API key**:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

### Basic Usage

```bash
# Interactive mode - stage changes selectively
python git-commit-tool.py --api-key $OPENROUTER_API_KEY --interactive

# Auto-commit all changes
python git-commit-tool.py --api-key $OPENROUTER_API_KEY --auto-stage

# Manage documentation
python git-commit-tool.py --api-key $OPENROUTER_API_KEY --docs-dir ./docs --docs-only
```

## 📖 Detailed Usage

### Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--api-key` | | **Required.** OpenRouter API key |
| `--model` | | AI model to use (default: `anthropic/claude-3-sonnet`) |
| `--interactive` | `-i` | Interactive hunk staging mode |
| `--auto-stage` | `-a` | Automatically stage all changes |
| `--docs-dir` | | Path to documentation directory |
| `--docs-only` | | Only perform documentation management |
| `--commit-message` | `-m` | Override generated commit message |

### Usage Examples

#### 1. Interactive Staging (Recommended)
```bash
python git-commit-tool.py --api-key $OPENROUTER_API_KEY -i
```

This mode lets you:
- Review each change individually
- Stage only the changes you want to commit
- Generate focused commit messages for specific changes

#### 2. Quick Commit All Changes
```bash
python git-commit-tool.py --api-key $OPENROUTER_API_KEY -a
```

Perfect for when you want to commit all your changes with an AI-generated message.

#### 3. Documentation Management
```bash
python git-commit-tool.py --api-key $OPENROUTER_API_KEY --docs-dir ./docs --docs-only
```

The tool will:
- Analyze your recent changes
- Suggest documentation updates
- Help create or update documentation files
- Use a simple patch system for precise edits

#### 4. Custom Model
```bash
python git-commit-tool.py --api-key $OPENROUTER_API_KEY --model "openai/gpt-4-turbo" -i
```

Supported models include:
- `anthropic/claude-3-sonnet` (default)
- `anthropic/claude-3-opus`
- `openai/gpt-4-turbo`
- `openai/gpt-3.5-turbo`
- And many more via OpenRouter

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

### Environment Variables

Set these for convenience:

```bash
export OPENROUTER_API_KEY="your-api-key"
export GIT_COMMIT_TOOL_MODEL="anthropic/claude-3-sonnet"
export GIT_COMMIT_TOOL_DOCS_DIR="./docs"
```

### Model Options

Popular models available through OpenRouter:

| Model | Best For | Context |Cost |
|-------|----------|------|------|
| `anthropic/claude-sonnet-4` (recommended) | Balanced performance | 200K | $$ |
| `anthropic/claude-opus-4` (best as of 6/10/25) | Highest quality | 200K | $$$$ |
| `google/gemini-2.5-pro-preview` | High quality | 1M | $$ |
| `google/gemini-2.5-flash-preview-05-20` | Fast, good quality | 1M | $ |
| `meta-llama/llama-4-maverick:free` | Free and capable | 128K | Free |


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

# Install dependencies
pip install requests

# Run tests (if available)
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