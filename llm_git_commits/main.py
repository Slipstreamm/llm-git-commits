#!/usr/bin/env python3
"""
Intelligent Git Commit Tool with LLM Integration
Automatically generates commit messages and manages documentation using OpenRouter API
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import difflib
import configparser
from dataclasses import dataclass

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)

@dataclass
class ProviderConfig:
    """Configuration for different LLM providers"""
    name: str
    base_url: str
    headers_template: Dict[str, str]
    model_format: str  # How to format model names for this provider
    
    @classmethod
    def get_providers(cls) -> Dict[str, 'ProviderConfig']:
        return {
            "openrouter": cls(
                name="OpenRouter",
                base_url="https://openrouter.ai/api/v1",
                headers_template={
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/llm-git-commits",
                    "X-Title": "Git Commit Tool"
                },
                model_format="{model}"  # Use model name as-is
            ),
            "openai": cls(
                name="OpenAI",
                base_url="https://api.openai.com/v1",
                headers_template={
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                model_format="{model}"
            ),
            "anthropic": cls(
                name="Anthropic",
                base_url="https://api.anthropic.com/v1",
                headers_template={
                    "x-api-key": "{api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                model_format="{model}"
            ),
            "gemini": cls(
                name="Google Gemini",
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                headers_template={
                    "Authorization": "Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                model_format="{model}"
            )
        }

class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "git-commit-tool"
        self.config_file = self.config_dir / "config.ini"
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            self.config.read(self.config_file)
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config['DEFAULT'] = {
            'provider': 'openrouter',
            'model': 'google/gemini-2.0-flash-exp',
            'api_key': '',
            'docs_dir': 'docs',
            'auto_stage': 'false',
            'interactive': 'false'
        }
        
        self.config['providers'] = {}
        for name, provider in ProviderConfig.get_providers().items():
            self.config[f'provider.{name}'] = {
                'api_key': '',
                'model': self._get_default_model(name)
            }
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for each provider"""
        defaults = {
            'openrouter': 'google/gemini-2.0-flash-exp',
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'gemini': 'gemini-2.0-flash-exp'
        }
        return defaults.get(provider, 'gpt-3.5-turbo')
    
    def save_config(self):
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, key: str, section: str = 'DEFAULT') -> str:
        """Get configuration value"""
        return self.config.get(section, key, fallback='')
    
    def set(self, key: str, value: str, section: str = 'DEFAULT'):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def get_provider_config(self, provider: str) -> Tuple[str, str]:
        """Get API key and model for a provider"""
        section = f'provider.{provider}'
        api_key = self.config.get(section, 'api_key', fallback='')
        model = self.config.get(section, 'model', fallback=self._get_default_model(provider))
        return api_key, model
    
    def set_provider_config(self, provider: str, api_key: str = None, model: str = None):
        """Set provider configuration"""
        section = f'provider.{provider}'
        if section not in self.config:
            self.config[section] = {}
        
        if api_key is not None:
            self.config[section]['api_key'] = api_key
        if model is not None:
            self.config[section]['model'] = model

class GitCommitTool:
    def __init__(self, api_key: str, model: str = "anthropic/claude-3-sonnet", base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.repo_root = self._get_repo_root()
        
    def _get_repo_root(self) -> Path:
        """Get the root directory of the git repository"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, check=True
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            raise Exception("Not in a git repository")
    
    def _call_llm(self, messages: List[Dict], temperature: float = 0.3) -> str:
        """Make API call to LLM provider"""
        # Build headers from template
        headers = {}
        for key, template in self.provider.headers_template.items():
            headers[key] = template.format(api_key=self.api_key)
        
        # Format model name
        model = self.provider.model_format.format(model=self.model)
        
        # Prepare request data
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }
        
        # Handle Anthropic's different API format
        if self.provider_name == 'anthropic':
            # Anthropic uses a different message format
            system_message = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            data = {
                "model": model,
                "max_tokens": 2000,
                "temperature": temperature,
                "messages": user_messages
            }
            
            if system_message:
                data["system"] = system_message
            
            endpoint = f"{self.provider.base_url}/messages"
        else:
            endpoint = f"{self.provider.base_url}/chat/completions"
        
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if self.provider_name == 'anthropic':
                return result["content"][0]["text"]
            else:
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            raise Exception(f"LLM API call failed for {self.provider.name}: {e}")
    
    def get_modified_files(self) -> List[str]:
        """Get list of modified files in the repository"""
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True
        )
        return [f for f in result.stdout.strip().split('\n') if f]
    
    def get_file_diff(self, filepath: str) -> str:
        """Get diff for a specific file"""
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", filepath],
            capture_output=True, text=True
        )
        return result.stdout
    
    def get_file_hunks(self, filepath: str) -> List[Dict]:
        """Parse file diff into individual hunks"""
        diff = self.get_file_diff(filepath)
        if not diff:
            return []
        
        hunks = []
        current_hunk = []
        hunk_header = None
        
        for line in diff.split('\n'):
            if line.startswith('@@'):
                if current_hunk and hunk_header:
                    hunks.append({
                        'header': hunk_header,
                        'content': '\n'.join(current_hunk),
                        'filepath': filepath
                    })
                hunk_header = line
                current_hunk = []
            elif line.startswith(('+', '-', ' ')) and hunk_header:
                current_hunk.append(line)
        
        if current_hunk and hunk_header:
            hunks.append({
                'header': hunk_header,
                'content': '\n'.join(current_hunk),
                'filepath': filepath
            })
        
        return hunks
    
    def interactive_stage_hunks(self, filepath: str) -> List[Dict]:
        """Interactively stage hunks from a file"""
        hunks = self.get_file_hunks(filepath)
        if not hunks:
            return []
        
        selected_hunks = []
        
        print(f"\n📝 File: {filepath}")
        print("=" * 50)
        
        for i, hunk in enumerate(hunks):
            print(f"\nHunk {i+1}/{len(hunks)}:")
            print(hunk['header'])
            
            # Show a preview of the hunk
            lines = hunk['content'].split('\n')[:10]  # Show first 10 lines
            for line in lines:
                if line.startswith('+'):
                    print(f"  \033[32m{line}\033[0m")  # Green for additions
                elif line.startswith('-'):
                    print(f"  \033[31m{line}\033[0m")  # Red for deletions
                else:
                    print(f"  {line}")
            
            if len(hunk['content'].split('\n')) > 10:
                print("  ... (truncated)")
            
            while True:
                choice = input(f"\nStage this hunk? [y/n/q/d]: ").lower()
                if choice == 'y':
                    selected_hunks.append(hunk)
                    break
                elif choice == 'n':
                    break
                elif choice == 'q':
                    return selected_hunks
                elif choice == 'd':
                    print(f"\nFull hunk content:")
                    for line in hunk['content'].split('\n'):
                        if line.startswith('+'):
                            print(f"\033[32m{line}\033[0m")
                        elif line.startswith('-'):
                            print(f"\033[31m{line}\033[0m")
                        else:
                            print(line)
                else:
                    print("Please enter y, n, q (quit), or d (show full diff)")
        
        return selected_hunks
    
    def stage_hunks(self, hunks: List[Dict]) -> bool:
        """Stage the selected hunks using git apply"""
        if not hunks:
            return False
        
        # Group hunks by file
        files_hunks = {}
        for hunk in hunks:
            filepath = hunk['filepath']
            if filepath not in files_hunks:
                files_hunks[filepath] = []
            files_hunks[filepath].append(hunk)
        
        # Create patch for each file and apply it
        for filepath, file_hunks in files_hunks.items():
            # Create a temporary patch file
            patch_content = f"diff --git a/{filepath} b/{filepath}\n"
            patch_content += f"index 0000000..1111111 100644\n"  # Dummy index line
            patch_content += f"--- a/{filepath}\n"
            patch_content += f"+++ b/{filepath}\n"
            
            for hunk in file_hunks:
                patch_content += hunk['header'] + '\n'
                patch_content += hunk['content'] + '\n'
            
            # Apply the patch to the index
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch_content)
                patch_file = f.name
            
            try:
                subprocess.run(
                    ["git", "apply", "--cached", patch_file],
                    check=True, capture_output=True
                )
                print(f"✅ Staged changes for {filepath}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to stage {filepath}: {e.stderr.decode()}")
                return False
            finally:
                os.unlink(patch_file)
        
        return True
    
    def generate_commit_message(self, staged_diff: str) -> str:
        """Generate a commit message based on staged changes"""
        messages = [
            {
                "role": "system",
                "content": """You are an expert software developer who writes excellent git commit messages. 
                
Guidelines for commit messages:
- Use conventional commits format: type(scope): description
- Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf
- Keep the first line under 50 characters
- Use imperative mood (e.g., "Add" not "Added")
- Be specific and descriptive
- If there are multiple changes, focus on the most significant one
- Add a body if needed to explain WHY the change was made

Analyze the git diff and write a concise, informative commit message."""
            },
            {
                "role": "user", 
                "content": f"Generate a commit message for these changes:\n\n```diff\n{staged_diff}\n```"
            }
        ]
        
        return self._call_llm(messages).strip()
    
    def get_staged_diff(self) -> str:
        """Get the diff of staged changes"""
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True, text=True
        )
        return result.stdout
    
    def commit_staged_changes(self, message: str) -> bool:
        """Commit the staged changes"""
        try:
            subprocess.run(["git", "commit", "-m", message], check=True)
            print(f"✅ Committed: {message}")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to commit changes")
            return False
    
    def find_doc_files(self, docs_dir: Path) -> List[Path]:
        """Find documentation files in the docs directory"""
        if not docs_dir.exists():
            return []
        
        doc_extensions = {'.md', '.rst', '.txt', '.mdx'}
        doc_files = []
        
        for file_path in docs_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in doc_extensions:
                doc_files.append(file_path)
        
        return doc_files
    
    def analyze_project_for_docs(self, docs_dir: Path) -> str:
        """Analyze the project to understand what documentation might be needed"""
        # Get recent commits
        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True
        )
        recent_commits = result.stdout
        
        # Get current staged/modified files
        modified_files = self.get_modified_files()
        
        # Get project structure
        important_files = []
        for pattern in ['*.py', '*.js', '*.ts', '*.go', '*.rs', '*.java', 'README*', 'package.json', 'requirements.txt', 'Cargo.toml']:
            result = subprocess.run(
                ["find", str(self.repo_root), "-name", pattern, "-type", "f"],
                capture_output=True, text=True
            )
            important_files.extend(result.stdout.strip().split('\n'))
        
        important_files = [f for f in important_files if f and not f.startswith('.')][:20]
        
        return f"""
Project Analysis:

Recent commits:
{recent_commits}

Modified files:
{chr(10).join(modified_files)}

Key project files:
{chr(10).join(important_files)}

Documentation directory: {docs_dir}
"""
    
    def suggest_doc_updates(self, docs_dir: Path) -> Dict:
        """Suggest documentation updates based on project changes"""
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True, exist_ok=True)
        
        project_analysis = self.analyze_project_for_docs(docs_dir)
        existing_docs = self.find_doc_files(docs_dir)
        
        # Read existing docs content (first 1000 chars of each)
        docs_content = {}
        for doc_file in existing_docs[:5]:  # Limit to first 5 docs
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    docs_content[str(doc_file.relative_to(self.repo_root))] = f.read()[:1000]
            except Exception:
                continue
        
        messages = [
            {
                "role": "system",
                "content": """You are a technical documentation expert. Analyze the project and suggest documentation updates.

Return your response as a JSON object with this structure:
{
    "updates": [
        {
            "file": "path/to/file.md",
            "action": "create|update|delete",
            "reason": "Why this change is needed",
            "priority": "high|medium|low"
        }
    ],
    "suggestions": [
        {
            "type": "content",
            "description": "What specific content should be added/updated"
        }
    ]
}

Focus on:
- API documentation
- Installation/setup guides
- Usage examples
- Architecture documentation
- Changelog updates
"""
            },
            {
                "role": "user",
                "content": f"""Project analysis:
{project_analysis}

Existing documentation:
{json.dumps(docs_content, indent=2)}

Suggest documentation updates needed based on recent changes."""
            }
        ]
        
        response = self._call_llm(messages)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print("⚠️ Could not parse LLM response as JSON")
            return {"updates": [], "suggestions": []}
    
    def create_doc_file(self, filepath: Path, content_type: str) -> str:
        """Generate content for a new documentation file"""
        project_analysis = self.analyze_project_for_docs(filepath.parent)
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a technical writer creating {content_type} documentation. 
Write clear, comprehensive documentation that follows best practices.
Use markdown format with appropriate headings, code blocks, and examples."""
            },
            {
                "role": "user",
                "content": f"""Create documentation for: {filepath.name}
Content type: {content_type}

Project context:
{project_analysis}

Write comprehensive documentation that would be helpful for users/developers."""
            }
        ]
        
        return self._call_llm(messages)
    
    def update_doc_file(self, filepath: Path, update_instructions: str) -> str:
        """Update an existing documentation file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except Exception:
            current_content = ""
        
        messages = [
            {
                "role": "system",
                "content": """You are a technical writer updating documentation. 
Provide updates in a simple patch format:

PATCH_START
SECTION: [section name or line numbers]
ACTION: [REPLACE|INSERT_AFTER|INSERT_BEFORE|DELETE]
CONTENT:
[new content here]
PATCH_END

You can provide multiple patches. Be precise with section identification."""
            },
            {
                "role": "user",
                "content": f"""Current file content:
```
{current_content}
```

Update instructions: {update_instructions}

Provide patches to update this documentation."""
            }
        ]
        
        return self._call_llm(messages)
    
    def apply_doc_patches(self, filepath: Path, patches_text: str) -> bool:
        """Apply simple patches to a documentation file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            lines = []
        
        # Parse patches
        patches = []
        current_patch = None
        
        for line in patches_text.split('\n'):
            line = line.strip()
            if line == "PATCH_START":
                current_patch = {}
            elif line == "PATCH_END":
                if current_patch:
                    patches.append(current_patch)
                current_patch = None
            elif current_patch is not None:
                if line.startswith("SECTION:"):
                    current_patch['section'] = line[8:].strip()
                elif line.startswith("ACTION:"):
                    current_patch['action'] = line[7:].strip()
                elif line.startswith("CONTENT:"):
                    current_patch['content'] = []
                elif 'content' in current_patch:
                    current_patch['content'].append(line)
        
        # Apply patches
        modified = False
        for patch in patches:
            if 'section' not in patch or 'action' not in patch:
                continue
            
            section = patch['section']
            action = patch['action']
            content = '\n'.join(patch.get('content', []))
            
            if action == "REPLACE":
                # Simple text replacement
                original_text = '\n'.join(lines)
                if section in original_text:
                    lines = original_text.replace(section, content).split('\n')
                    lines = [line + '\n' for line in lines[:-1]] + [lines[-1]]
                    modified = True
            elif action == "INSERT_AFTER":
                for i, line in enumerate(lines):
                    if section in line:
                        lines.insert(i + 1, content + '\n')
                        modified = True
                        break
            elif action == "INSERT_BEFORE":
                for i, line in enumerate(lines):
                    if section in line:
                        lines.insert(i, content + '\n')
                        modified = True
                        break
        
        if modified:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                return True
            except Exception as e:
                print(f"❌ Failed to write file {filepath}: {e}")
                return False
        
        return False

def configure_tool():
    """Interactive configuration setup"""
    config = ConfigManager()
    
    print("🔧 Git Commit Tool Configuration")
    print("=" * 40)
    
    # Show current configuration
    current_provider = config.get('provider') or 'openrouter'
    print(f"Current provider: {current_provider}")
    
    # Provider selection
    providers = ProviderConfig.get_providers()
    print("\nAvailable providers:")
    for i, (key, provider) in enumerate(providers.items(), 1):
        indicator = "→" if key == current_provider else " "
        print(f"{indicator} {i}. {provider.name} ({key})")
    
    while True:
        choice = input(f"\nSelect provider [1-{len(providers)}] or press Enter to keep current: ").strip()
        if not choice:
            provider_key = current_provider
            break
        try:
            provider_key = list(providers.keys())[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("Invalid choice. Please try again.")
    
    config.set('provider', provider_key)
    provider = providers[provider_key]
    
    print(f"\n🔑 Configuring {provider.name}")
    
    # API Key configuration
    current_api_key, current_model = config.get_provider_config(provider_key)
    if current_api_key:
        api_key_display = current_api_key[:8] + "..." + current_api_key[-4:] if len(current_api_key) > 12 else current_api_key
        print(f"Current API key: {api_key_display}")
    
    new_api_key = input("Enter API key (or press Enter to keep current): ").strip()
    if new_api_key:
        config.set_provider_config(provider_key, api_key=new_api_key)
    
    # Model configuration
    print(f"Current model: {current_model}")
    
    # Show some popular models for each provider
    popular_models = {
        'openrouter': [
            'google/gemini-2.0-flash-exp',
            'anthropic/claude-3-5-sonnet',
            'openai/gpt-4o-mini',
            'meta-llama/llama-3.2-3b-instruct'
        ],
        'openai': [
            'gpt-4o',
            'gpt-4o-mini', 
            'gpt-3.5-turbo'
        ],
        'anthropic': [
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-3-opus-20240229'
        ],
        'gemini': [
            'gemini-2.0-flash-exp',
            'gemini-1.5-pro',
            'gemini-1.5-flash'
        ]
    }
    
    if provider_key in popular_models:
        print("\nPopular models:")
        for model in popular_models[provider_key]:
            indicator = "→" if model == current_model else " "
            print(f"{indicator} {model}")
    
    new_model = input("Enter model name (or press Enter to keep current): ").strip()
    if new_model:
        config.set_provider_config(provider_key, model=new_model)
    
    # Other settings
    print("\n⚙️ General Settings")
    
    current_docs_dir = config.get('docs_dir') or 'docs'
    print(f"Current docs directory: {current_docs_dir}")
    new_docs_dir = input("Enter docs directory (or press Enter to keep current): ").strip()
    if new_docs_dir:
        config.set('docs_dir', new_docs_dir)
    
    # Default behavior
    current_interactive = config.get('interactive', 'DEFAULT').lower() == 'true'
    interactive_choice = input(f"Use interactive mode by default? [y/N]: ").strip().lower()
    if interactive_choice in ['y', 'yes']:
        config.set('interactive', 'true')
    elif interactive_choice in ['n', 'no']:
        config.set('interactive', 'false')
    
    # Save configuration
    config.save_config()
    print(f"\n✅ Configuration saved to {config.config_file}")
    
    # Test the configuration
    test_config = input("\nTest the configuration? [y/N]: ").strip().lower()
    if test_config in ['y', 'yes']:
        try:
            tool = GitCommitTool(config_manager=config)
            print(f"✅ Successfully configured {tool.provider.name} with model {tool.model}")
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Intelligent Git Commit Tool with LLM")
    parser.add_argument("--api-key", required=True, help="OpenRouter API key")
    parser.add_argument("--model", default="anthropic/claude-3-sonnet", 
                       help="Model to use (default: anthropic/claude-3-sonnet)")
    parser.add_argument("--docs-dir", type=Path, help="Documentation directory to manage")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive mode for staging hunks")
    parser.add_argument("--auto-stage", "-a", action="store_true",
                       help="Automatically stage all changes")
    parser.add_argument("--docs-only", action="store_true",
                       help="Only work on documentation updates")
    parser.add_argument("--commit-message", "-m", help="Override generated commit message")
    
    args = parser.parse_args()
    
    try:
        tool = GitCommitTool(args.api_key, args.model)
        
        if args.docs_only and args.docs_dir:
            # Documentation management mode
            print("🔍 Analyzing project for documentation updates...")
            suggestions = tool.suggest_doc_updates(docs_dir)
            
            print("\n📋 Documentation Update Suggestions:")
            for update in suggestions.get('updates', []):
                priority_emoji = {"high": "🔥", "medium": "⚡", "low": "💡"}
                emoji = priority_emoji.get(update.get('priority', 'low'), '💡')
                print(f"{emoji} {update.get('action', 'update').upper()}: {update.get('file', 'unknown')}")
                print(f"   Reason: {update.get('reason', 'No reason provided')}")
            
            print("\n💡 Content Suggestions:")
            for suggestion in suggestions.get('suggestions', []):
                print(f"• {suggestion.get('description', 'No description')}")
            
            # Interactive doc management
            for update in suggestions.get('updates', []):
                filepath = docs_dir / update.get('file', '')
                action = update.get('action', 'update')
                
                choice = input(f"\nApply {action} to {filepath.name}? [y/n]: ").lower()
                if choice != 'y':
                    continue
                
                if action == 'create':
                    content_type = input("Content type (e.g., 'API reference', 'tutorial'): ")
                    content = tool.create_doc_file(filepath, content_type)
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ Created {filepath}")
                
                elif action == 'update':
                    if filepath.exists():
                        instructions = input("Update instructions: ")
                        patches = tool.update_doc_file(filepath, instructions)
                        if tool.apply_doc_patches(filepath, patches):
                            print(f"✅ Updated {filepath}")
                        else:
                            print(f"⚠️ No changes applied to {filepath}")
            
            return
        
        # Regular commit mode
        modified_files = tool.get_modified_files()
        if not modified_files:
            print("✨ No modified files found!")
            return
        
        print(f"📁 Modified files: {', '.join(modified_files)}")
        
        if auto_stage:
            # Auto-stage all changes
            subprocess.run(["git", "add", "."], check=True)
            print("✅ Auto-staged all changes")
        elif interactive:
            # Interactive staging mode
            all_selected_hunks = []
            for filepath in modified_files:
                selected_hunks = tool.interactive_stage_hunks(filepath)
                all_selected_hunks.extend(selected_hunks)
            
            if all_selected_hunks:
                print(f"\n🎯 Staging {len(all_selected_hunks)} selected hunks...")
                if not tool.stage_hunks(all_selected_hunks):
                    print("❌ Failed to stage some changes")
                    return
            else:
                print("ℹ️ No changes selected for staging")
                return
        else:
            # Ask user what to do
            print("\nOptions:")
            print("1. Auto-stage all changes")
            print("2. Interactive staging")
            print("3. Stage specific files")
            
            choice = input("Choose option [1/2/3]: ").strip()
            
            if choice == '1':
                subprocess.run(["git", "add", "."], check=True)
                print("✅ Auto-staged all changes")
            elif choice == '2':
                all_selected_hunks = []
                for filepath in modified_files:
                    selected_hunks = tool.interactive_stage_hunks(filepath)
                    all_selected_hunks.extend(selected_hunks)
                
                if all_selected_hunks:
                    print(f"\n🎯 Staging {len(all_selected_hunks)} selected hunks...")
                    if not tool.stage_hunks(all_selected_hunks):
                        print("❌ Failed to stage some changes")
                        return
                else:
                    print("ℹ️ No changes selected for staging")
                    return
            elif choice == '3':
                print("\nSelect files to stage:")
                for i, filepath in enumerate(modified_files):
                    print(f"{i+1}. {filepath}")
                
                selections = input("Enter file numbers (comma-separated): ").strip()
                selected_files = []
                for s in selections.split(','):
                    try:
                        idx = int(s.strip()) - 1
                        if 0 <= idx < len(modified_files):
                            selected_files.append(modified_files[idx])
                    except ValueError:
                        continue
                
                if selected_files:
                    subprocess.run(["git", "add"] + selected_files, check=True)
                    print(f"✅ Staged: {', '.join(selected_files)}")
                else:
                    print("ℹ️ No files selected")
                    return
            else:
                print("❌ Invalid choice")
                return
        
        # Check if anything is staged
        staged_diff = tool.get_staged_diff()
        if not staged_diff:
            print("ℹ️ No changes staged for commit")
            return
        
        # Generate commit message
        if args.commit_message:
            commit_message = args.commit_message
        else:
            print("🤖 Generating commit message...")
            commit_message = tool.generate_commit_message(staged_diff)
        
        print(f"\n📝 Proposed commit message:")
        print("-" * 50)
        print(commit_message)
        print("-" * 50)
        
        # Confirm commit
        confirm = input("\nProceed with commit? [Y/n]: ").lower()
        if confirm in ('', 'y', 'yes'):
            tool.commit_staged_changes(commit_message)
        else:
            print("❌ Commit cancelled")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if "API key" in str(e):
            print("💡 Tip: Run 'python git-commit-tool.py config' to set up your configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()