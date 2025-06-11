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
import traceback
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

import time
import threading
import itertools

class LLMFeedback:
    """A simple console feedback provider for long-running operations."""
    def __init__(self, message="🤖 Generating response..."):
        self.message = message
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._stop_event = threading.Event()
        self.start_time: Optional[float] = None
        self.final_message = ""

    def _animate(self):
        """Cycle through spinner characters."""
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        
        while not self._stop_event.is_set():
            if self.start_time:
                elapsed = time.time() - self.start_time
                sys.stdout.write(f'\r{next(spinner)} {self.message} ({elapsed:.1f}s) ')
            else:
                sys.stdout.write(f'\r{next(spinner)} {self.message} ')
            sys.stdout.flush()
            time.sleep(0.1)
            
        # Clear the line before printing the final message
        sys.stdout.write(f'\r{" " * (len(self.message) + 20)}\r')
        if self.final_message:
            print(self.final_message)

    def start(self):
        """Start the feedback animation."""
        self.start_time = time.time()
        self._thread.start()

    def stop(self, final_message: str = ""):
        """Stop the feedback animation."""
        self.final_message = final_message
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join()
    
    def update_message(self, new_message: str):
        """Update the message displayed by the feedback animation."""
        self.message = new_message
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
            'model': 'google/gemini-2.5-flash-preview-05-20',
            'api_key': '',
            'docs_dir': 'docs',
            'auto_stage': 'false',
            'interactive': 'false',
            'intelligent_grouping_strategy': 'auto',
            'commit_flow': 'interactive'
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
            'openrouter': 'google/gemini-2.5-flash-preview-05-20',
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-sonnet-4-20250514',
            'gemini': 'gemini-2.5-flash-preview-05-20'
        }
        return defaults.get(provider, 'gpt-4o-mini')
    
    def save_config(self):
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
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
    
    def set_provider_config(self, provider: str, api_key: Optional[str] = None, model: Optional[str] = None):
        """Set provider configuration"""
        section = f'provider.{provider}'
        if section not in self.config:
            self.config[section] = {}
        
        if api_key is not None:
            self.config[section]['api_key'] = api_key
        if model is not None:
            self.config[section]['model'] = model

class IntelligentStager:
    def __init__(self, tool: 'GitCommitTool'):
        self.tool = tool
        self.config = tool.config

    def plan_commits(self, hunks: List[Dict]) -> Dict:
        """
        Analyze hunks and create a plan for multiple commits using an LLM,
        with real-time feedback.
        """
        strategy = self.config.get('intelligent_grouping_strategy')
        
        hunks_for_prompt = [{"id": h['id'], "filepath": h['filepath'], "header": h['header'], "content": h['content']} for h in hunks]

        messages = [
            {
                "role": "system",
                "content": f"""You are an expert at analyzing code changes and creating a logical series of git commits.
Your task is to group all the provided hunks into separate, focused commits.
You must return a JSON object with two keys: "commit_plan" (a list of planned commits) and "unplanned_hunk_ids" (a list of IDs for hunks that do not fit).
Each commit in "commit_plan" must have "commit_message" and "hunk_ids".
Grouping Strategy: {strategy}
Analyze the hunks and create a clear, logical commit plan. Your primary goal is to create a comprehensive commit plan that includes all changes. Avoid leaving any hunks unplanned if possible. If you absolutely cannot group a hunk, you can place its ID in 'unplanned_hunk_ids', but this should be a last resort.
"""
            },
            {
                "role": "user",
                "content": f"Here are the hunks to analyze:\n\n{json.dumps(hunks_for_prompt, indent=2)}"
            }
        ]

        feedback = LLMFeedback("🧠 Analyzing changes for commit plan...")
        feedback.start()
        
        full_response_str = ""
        
        try:
            # Stream the response to get the full text, showing feedback while doing so
            response_generator = self.tool._call_llm(messages, temperature=0.2, stream=True)
            for chunk in response_generator:
                full_response_str += chunk

            if feedback.start_time:
                feedback.stop(f"✅ Analysis complete in {time.time() - feedback.start_time:.1f}s")
            else:
                feedback.stop("✅ Analysis complete.")
            
            # Robustly extract JSON from the potentially messy LLM output
            match = re.search(r'\{.*\}', full_response_str, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                raise ValueError("No JSON object found in LLM response")

        except Exception as e:
            feedback.stop("❌ Error during analysis.")
            print(f"⚠️ Could not parse LLM response for commit plan: {e}")
            return {"commit_plan": [], "unplanned_hunk_ids": [h['id'] for h in hunks]}
class GitCommitTool:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.provider_name = self.config.get('provider')
        self.provider = ProviderConfig.get_providers()[self.provider_name]
        self.api_key, self.model = self.config.get_provider_config(self.provider_name)
        self.repo_root = self._get_repo_root()
        
    def _get_repo_root(self) -> Path:
        """Get the root directory of the git repository"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            raise Exception("Not in a git repository")
    
    def _call_llm(self, messages: List[Dict], temperature: float = 0.3, stream: bool = False):
        """Make API call to LLM provider. Returns a string or a generator."""
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
            "max_tokens": 32768,
            "stream": stream
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
                "max_tokens": 32768,
                "temperature": temperature,
                "messages": user_messages,
                "stream": stream
            }
            
            if system_message:
                data["system"] = system_message
            
            endpoint = f"{self.provider.base_url}/messages"
        else:
            endpoint = f"{self.provider.base_url}/chat/completions"
        
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=300, stream=stream)
            response.raise_for_status()
            
            if not stream:
                result = response.json()
                if self.provider_name == 'anthropic':
                    return result["content"][0]["text"]
                else:
                    return result["choices"][0]["message"]["content"]
            else:
                return self._stream_response_generator(response)
                
        except Exception as e:
            raise Exception(f"LLM API call failed for {self.provider.name}: {e}")

    def _stream_response_generator(self, response: requests.Response):
        """Generator for handling streaming responses from OpenAI-compatible APIs."""
        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8')
                if chunk_str.startswith('data: '):
                    chunk_str = chunk_str[6:]
                if chunk_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(chunk_str)
                    if 'choices' in data and data['choices']:
                        delta = data['choices'][0].get('delta', {})
                        if 'content' in delta and delta['content']:
                            yield delta['content']
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue # Ignore malformed chunks
    
    def get_modified_files(self) -> List[Tuple[str, str]]:
        """Get list of modified and untracked files."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        files = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            status = line[:2]
            filepath = line[3:]
            if status.strip() == 'R':
                # Handle renamed files: R old_path -> new_path
                _, filepath = filepath.split(' -> ')
            files.append((status, filepath))
        return files

    def get_file_diff(self, file_info: Tuple[str, str]) -> str:
        """Get diff for a specific file"""
        status, filepath = file_info
        
        # For untracked files, diff against /dev/null
        if status.strip() == '??':
            # Ensure the file is not empty before diffing
            if os.path.getsize(filepath) == 0:
                return ""
            result = subprocess.run(
                ["git", "diff", "--no-index", "--", "/dev/null", filepath],
                capture_output=True, text=True, encoding='utf-8'
            )
        else:
            result = subprocess.run(
                ["git", "diff", "HEAD", "--", filepath],
                capture_output=True, text=True, encoding='utf-8'
            )
        return result.stdout
    
    def get_file_hunks(self, file_info: Tuple[str, str]) -> List[Dict]:
        """Parse file diff into individual hunks"""
        diff = self.get_file_diff(file_info)
        filepath = file_info[1]
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
    
    def interactive_stage_hunks(self, file_info: Tuple[str, str]) -> List[Dict]:
        """Interactively stage hunks from a file"""
        hunks = self.get_file_hunks(file_info)
        if not hunks:
            return []
        
        filepath = file_info[1]
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
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False, encoding='utf-8') as f:
                f.write(patch_content)
                patch_file = f.name
            
            try:
                subprocess.run(
                    ["git", "apply", "--cached", "--ignore-whitespace", patch_file],
                    check=True, capture_output=True, encoding='utf-8'
                )
                print(f"✅ Staged changes for {filepath}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to stage {filepath}: {e.stderr}")
                return False
            finally:
                os.unlink(patch_file)
        
        return True
    
    def generate_commit_message(self, staged_diff: str) -> str:
        """Generate a commit message based on staged changes, with streaming."""
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
        
        feedback = LLMFeedback("🤖 Generating commit message...")
        feedback.start()
        
        try:
            response_generator = self._call_llm(messages, stream=True)
            
            # Stop the initial feedback before printing the streaming response
            if feedback.start_time:
                feedback.stop(f"✅ Generation started in {time.time() - feedback.start_time:.1f}s")
            else:
                feedback.stop("✅ Generation started.")

            commit_message = ""
            sys.stdout.write("\n📝 Proposed commit message:\n")
            sys.stdout.write("-" * 50 + "\n")
            
            # Stream the commit message
            for chunk in response_generator:
                commit_message += chunk
                sys.stdout.write(chunk)
                sys.stdout.flush()
                
            sys.stdout.write("\n" + "-" * 50 + "\n")
            
            print("✅ Generation complete.")
            return commit_message.strip()
            
        except Exception as e:
            feedback.stop("❌ Error during generation.")
            raise e
    
    def get_staged_diff(self) -> str:
        """Get the diff of staged changes"""
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout

    def get_all_hunks(self) -> List[Dict]:
        """Get all hunks from all modified files"""
        all_hunks = []
        modified_files = self.get_modified_files()
        for file_info in modified_files:
            hunks = self.get_file_hunks(file_info)
            filepath = file_info[1]
            # Add a unique ID to each hunk for tracking
            for i, hunk in enumerate(hunks):
                hunk['id'] = f"{filepath}-{i}"
            all_hunks.extend(hunks)
        return all_hunks

    def commit_staged_changes(self, message: str) -> bool:
        """Commit the staged changes"""
        try:
            subprocess.run(["git", "commit", "-m", message], check=True, encoding='utf-8')
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
            capture_output=True, text=True, encoding='utf-8'
        )
        recent_commits = result.stdout
        
        # Get current staged/modified files
        modified_files_with_status = self.get_modified_files()
        modified_files = [f for _, f in modified_files_with_status]
        
        # Get project structure
        important_files = []
        for pattern in ['*.py', '*.js', '*.ts', '*.go', '*.rs', '*.java', 'README*', 'package.json', 'requirements.txt', 'Cargo.toml']:
            result = subprocess.run(
                ["find", str(self.repo_root), "-name", pattern, "-type", "f"],
                capture_output=True, text=True, encoding='utf-8'
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
        
        docs_content = {}
        for doc_file in existing_docs[:5]:
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    docs_content[str(doc_file.relative_to(self.repo_root))] = f.read()[:1000]
            except Exception:
                continue
        
        messages = [
            {
                "role": "system",
                "content": "You are a technical documentation expert. Analyze the project and suggest documentation updates as a JSON object."
            },
            {
                "role": "user",
                "content": f"Project analysis:\n{project_analysis}\n\nExisting documentation:\n{json.dumps(docs_content, indent=2)}\n\nSuggest documentation updates needed based on recent changes."
            }
        ]
        
        feedback = LLMFeedback("📄 Analyzing documentation...")
        feedback.start()
        try:
            response = self._call_llm(messages, stream=False)
            if feedback.start_time:
                feedback.stop(f"✅ Doc analysis complete in {time.time() - feedback.start_time:.1f}s")
            else:
                feedback.stop("✅ Doc analysis complete.")
            if isinstance(response, str):
                return json.loads(response)
            else:
                # This case should not happen with stream=False
                raise TypeError("Expected a string response for doc analysis.")
        except (json.JSONDecodeError, TypeError):
            feedback.stop("❌ Error analyzing docs.")
            print("⚠️ Could not parse LLM response as JSON")
            return {"updates": [], "suggestions": []}

    def create_doc_file(self, filepath: Path, content_type: str) -> str:
        """Generate content for a new documentation file"""
        project_analysis = self.analyze_project_for_docs(filepath.parent)
        
        messages = [
            {
                "role": "system",
                "content": f"You are a technical writer creating {content_type} documentation. Use markdown format."
            },
            {
                "role": "user",
                "content": f"Create documentation for: {filepath.name}\nContent type: {content_type}\n\nProject context:\n{project_analysis}\n\nWrite comprehensive documentation."
            }
        ]
        
        feedback = LLMFeedback(f"✍️ Creating {filepath.name}...")
        feedback.start()
        try:
            response = self._call_llm(messages, stream=False)
            if feedback.start_time:
                feedback.stop(f"✅ Created doc in {time.time() - feedback.start_time:.1f}s")
            else:
                feedback.stop("✅ Doc creation complete.")
            if isinstance(response, str):
                return response
            else:
                raise TypeError("Expected a string response for doc creation.")
        except Exception as e:
            feedback.stop("❌ Error creating doc.")
            raise e

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
                "content": "You are a technical writer updating documentation. Provide updates in a simple patch format (use PATCH_START, SECTION, ACTION, CONTENT, PATCH_END)."
            },
            {
                "role": "user",
                "content": f"Current file content:\n```\n{current_content}\n```\n\nUpdate instructions: {update_instructions}\n\nProvide patches to update this documentation."
            }
        ]
        
        feedback = LLMFeedback(f"✍️ Updating {filepath.name}...")
        feedback.start()
        try:
            response = self._call_llm(messages, stream=False)
            if feedback.start_time:
                feedback.stop(f"✅ Updated doc in {time.time() - feedback.start_time:.1f}s")
            else:
                feedback.stop("✅ Doc update complete.")
            if isinstance(response, str):
                return response
            else:
                raise TypeError("Expected a string response for doc update.")
        except Exception as e:
            feedback.stop("❌ Error updating doc.")
            raise e

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

def select_model_interactively(provider_config: ProviderConfig, api_key: str) -> Optional[str]:
    """Fetch models and let the user select one interactively."""
    headers = {}
    for key, template in provider_config.headers_template.items():
        headers[key] = template.format(api_key=api_key)
    
    endpoint = f"{provider_config.base_url}/models"
    models = []
    print("\n⏳ Fetching available models...")
    try:
        response = requests.get(endpoint, headers=headers, timeout=15)
        if response.status_code == 200:
            json_response = response.json()
            if isinstance(json_response, dict):
                models_data = json_response.get('data', [])
            elif isinstance(json_response, list):
                models_data = json_response
            else:
                models_data = []
            models = sorted(models_data, key=lambda x: x.get('name', '').lower())
        else:
            print(f"⚠️ Failed to fetch models (status: {response.status_code}). Response: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️ Could not fetch models: {e}.")
        return None

    if not models:
        print("No models found.")
        return None

    print(f"✅ Found {len(models)} models for {provider_config.name}.")
    
    all_models = models
    while True:  # Search loop
        search_term = input("\n🔍 Search for a model (or press Enter to list all): ").strip().lower()
        if search_term:
            filtered_models = [
                m for m in all_models
                if search_term in m.get('id', '').lower()
                or search_term in m.get('name', '').lower()
                or (m.get('description') and search_term in m.get('description').lower())
            ]
        else:
            filtered_models = all_models

        if not filtered_models:
            print("No models found matching your search.")
            continue  # Restart search loop

        start_index = 0
        page_size = 25
        while True:  # Display and select loop
            print("\n--- Matching Models ---")
            end_index = min(start_index + page_size, len(filtered_models))
            
            for i, model in enumerate(filtered_models[start_index:end_index], start=start_index):
                model_id = model.get('id', 'N/A')
                name = model.get('name', 'N/A')
                context = model.get('context_length', 'N/A')
                print(f"{i+1:3d}. {name:<40} ({model_id}) - Context: {context}")
            
            prompt = f"Select a model #, (s)earch again, or (q)uit"
            if end_index < len(filtered_models):
                prompt += ", (m)ore"

            choice = input(f"{prompt}: ").strip().lower()

            if choice == 's':
                break
            if choice == 'q' or choice == '':
                return None
            if choice == 'm' and end_index < len(filtered_models):
                start_index = end_index
                continue
            
            try:
                model_index = int(choice) - 1
                if 0 <= model_index < len(filtered_models):
                    selected_model_id = filtered_models[model_index]['id']
                    print(f"✅ Selected model: {selected_model_id}")
                    return selected_model_id
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
        
        if choice == 's':
            continue
        else:
            return None

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
    
    api_key_to_use = new_api_key or current_api_key
    
    if api_key_to_use:
        choice = input("\nFetch and select from available models? [Y/n]: ").strip().lower()
        if choice in ('', 'y', 'yes'):
            selected_model = select_model_interactively(provider, api_key_to_use)
            if selected_model:
                config.set_provider_config(provider_key, model=selected_model)
            else:
                print("Model selection cancelled.")
                new_model = input("Enter model name manually (or press Enter to keep current): ").strip()
                if new_model:
                    config.set_provider_config(provider_key, model=new_model)
        else:
            new_model = input("Enter model name (or press Enter to keep current): ").strip()
            if new_model:
                config.set_provider_config(provider_key, model=new_model)
    else:
        print("\n⚠️ API key not set. Please enter model name manually.")
        new_model = input(f"Enter model name for {provider.name} (or press Enter to keep '{current_model}'): ").strip()
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

    print("\n🧠 Intelligent Staging Settings")
    current_grouping = config.get('intelligent_grouping_strategy') or 'auto'
    print(f"Current grouping strategy: {current_grouping}")
    print("1. auto (Let LLM decide)")
    print("2. feature (Group by feature/bug)")
    print("3. file (Group by file)")
    grouping_choice = input("Choose grouping strategy [1/2/3 or Enter]: ").strip()
    if grouping_choice == '1':
        config.set('intelligent_grouping_strategy', 'auto')
    elif grouping_choice == '2':
        config.set('intelligent_grouping_strategy', 'feature')
    elif grouping_choice == '3':
        config.set('intelligent_grouping_strategy', 'file')

    current_flow = config.get('commit_flow') or 'interactive'
    print(f"\nCurrent commit flow: {current_flow}")
    print("1. interactive (Confirm each commit)")
    print("2. propose_all (Confirm all at once)")
    print("3. automatic (No confirmation needed)")
    flow_choice = input("Choose commit flow [1/2/3 or Enter]: ").strip()
    if flow_choice == '1':
        config.set('commit_flow', 'interactive')
    elif flow_choice == '2':
        config.set('commit_flow', 'propose_all')
    elif flow_choice == '3':
        config.set('commit_flow', 'automatic')
    
    # Save configuration
    config.save_config()
    print(f"\n✅ Configuration saved to {config.config_file}")
    
    # Test the configuration
    test_config = input("\nTest the configuration? [y/N]: ").strip().lower()
    if test_config in ['y', 'yes']:
        try:
            tool = GitCommitTool(config)
            print(f"✅ Successfully configured {tool.provider.name} with model {tool.model}")
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")

def main():
    if 'config' in sys.argv:
        configure_tool()
        return
    
    parser = argparse.ArgumentParser(description="Intelligent Git Commit Tool with LLM")
    parser.add_argument("--docs-dir", type=Path, help="Documentation directory to manage")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive mode for staging hunks")
    parser.add_argument("--auto-stage", "-a", action="store_true",
                       help="Automatically stage all changes")
    parser.add_argument("--intelligent", action="store_true",
                        help="Use LLM to automatically create multiple focused commits")
    parser.add_argument("--docs-only", action="store_true",
                       help="Only work on documentation updates")
    parser.add_argument("--commit-message", "-m", help="Override generated commit message")
    
    args = parser.parse_args()
    
    try:
        config = ConfigManager()
        tool = GitCommitTool(config)
        
        if args.docs_only and args.docs_dir:
            # Documentation management mode
            print("🔍 Analyzing project for documentation updates...")
            suggestions = tool.suggest_doc_updates(args.docs_dir)
            
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
                filepath = args.docs_dir / update.get('file', '')
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
        modified_files_with_status = tool.get_modified_files()
        if not modified_files_with_status:
            print("✨ No modified files found!")
            return
        
        modified_files = [f for _, f in modified_files_with_status]
        print(f"📁 Modified files: {', '.join(modified_files)}")
        
        if args.intelligent:
            # Intelligent staging mode
            print("🧠 Starting intelligent staging...")
            stager = IntelligentStager(tool)
            all_hunks = tool.get_all_hunks()
            
            if not all_hunks:
                print("✨ No changes to process!")
                return

            commit_plan_data = stager.plan_commits(all_hunks)
            commit_plan = commit_plan_data.get('commit_plan', [])
            unplanned_hunk_ids = commit_plan_data.get('unplanned_hunk_ids', [])

            if not commit_plan:
                print("ℹ️ LLM did not propose any commits. You can stage changes manually.")
                return

            print(f"\n🤖 LLM has proposed {len(commit_plan)} commit(s).")
            
            # Create a map of hunk IDs to hunks for easy lookup
            hunk_map = {h['id']: h for h in all_hunks}

            # Execute the commit plan
            for i, commit in enumerate(commit_plan):
                print("-" * 50)
                print(f"Commit {i+1}/{len(commit_plan)}:")
                print(commit['commit_message'])
                print(f"Hunks: {', '.join(commit['hunk_ids'])}")
                
                commit_hunks = [hunk_map[h_id] for h_id in commit['hunk_ids'] if h_id in hunk_map]
                
                if config.get('commit_flow') != 'automatic':
                    confirm = input("Proceed with this commit? [Y/n]: ").lower()
                    if confirm not in ('', 'y', 'yes'):
                        print("❌ Commit skipped.")
                        continue
                
                if tool.stage_hunks(commit_hunks):
                    tool.commit_staged_changes(commit['commit_message'])
                else:
                    print("❌ Failed to stage hunks for this commit.")

            # Handle unplanned hunks
            if unplanned_hunk_ids:
                print("-" * 50)
                print(f"ℹ️ {len(unplanned_hunk_ids)} hunk(s) were not included in the commit plan.")
                choice = input("Stage and commit remaining hunks in a separate commit? [y/N]: ").lower()
                if choice == 'y':
                    remaining_hunks = [hunk_map[h_id] for h_id in unplanned_hunk_ids if h_id in hunk_map]
                    if tool.stage_hunks(remaining_hunks):
                        staged_diff = tool.get_staged_diff()
                        message = tool.generate_commit_message(staged_diff)
                        print(f"\n📝 Proposed commit for remaining changes:")
                        print(message)
                        confirm = input("Proceed with commit? [Y/n]: ").lower()
                        if confirm in ('', 'y', 'yes'):
                            tool.commit_staged_changes(message)
            
            return

        elif args.auto_stage:
            # Auto-stage all changes
            subprocess.run(["git", "add", "."], check=True, encoding='utf-8')
            print("✅ Auto-staged all changes")
        elif args.interactive:
            # Interactive staging mode
            all_selected_hunks = []
            for status, filepath in modified_files_with_status:
                selected_hunks = tool.interactive_stage_hunks((status, filepath))
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
            print("2. Interactive staging (review and stage changes piece-by-piece)")
            print("3. Stage specific files")
            print("4. Intelligent Staging (use AI to automatically group related changes into separate, logical commits)")

            choice = input("Choose option [1/2/3/4]: ").strip()

            if choice == '1':
                subprocess.run(["git", "add", "."], check=True, encoding='utf-8')
                print("✅ Auto-staged all changes")
            elif choice == '2':
                all_selected_hunks = []
                for status, filepath in modified_files_with_status:
                    selected_hunks = tool.interactive_stage_hunks((status, filepath))
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
                    subprocess.run(["git", "add"] + selected_files, check=True, encoding='utf-8')
                    print(f"✅ Staged: {', '.join(selected_files)}")
                else:
                    print("ℹ️ No files selected")
                    return
            elif choice == '4':
                # Intelligent staging mode
                print("🧠 Starting intelligent staging...")
                stager = IntelligentStager(tool)
                all_hunks = tool.get_all_hunks()

                if not all_hunks:
                    print("✨ No changes to process!")
                    return

                commit_plan_data = stager.plan_commits(all_hunks)
                commit_plan = commit_plan_data.get('commit_plan', [])
                unplanned_hunk_ids = commit_plan_data.get('unplanned_hunk_ids', [])

                if not commit_plan:
                    print("ℹ️ LLM did not propose any commits. You can stage changes manually.")
                    return

                print(f"\n🤖 LLM has proposed {len(commit_plan)} commit(s).")

                # Create a map of hunk IDs to hunks for easy lookup
                hunk_map = {h['id']: h for h in all_hunks}

                # Execute the commit plan
                for i, commit in enumerate(commit_plan):
                    print("-" * 50)
                    print(f"Commit {i+1}/{len(commit_plan)}:")
                    print(commit['commit_message'])
                    print(f"Hunks: {', '.join(commit['hunk_ids'])}")

                    commit_hunks = [hunk_map[h_id] for h_id in commit['hunk_ids'] if h_id in hunk_map]

                    if config.get('commit_flow') != 'automatic':
                        confirm = input("Proceed with this commit? [Y/n]: ").lower()
                        if confirm not in ('', 'y', 'yes'):
                            print("❌ Commit skipped.")
                            continue

                    if tool.stage_hunks(commit_hunks):
                        tool.commit_staged_changes(commit['commit_message'])
                    else:
                        print("❌ Failed to stage hunks for this commit.")

                # Handle unplanned hunks
                if unplanned_hunk_ids:
                    print("-" * 50)
                    print(f"ℹ️ {len(unplanned_hunk_ids)} hunk(s) were not included in the commit plan.")
                    choice = input("Stage and commit remaining hunks in a separate commit? [y/N]: ").lower()
                    if choice == 'y':
                        remaining_hunks = [hunk_map[h_id] for h_id in unplanned_hunk_ids if h_id in hunk_map]
                        if tool.stage_hunks(remaining_hunks):
                            staged_diff = tool.get_staged_diff()
                            message = tool.generate_commit_message(staged_diff)
                            print(f"\n📝 Proposed commit for remaining changes:")
                            print(message)
                            confirm = input("Proceed with commit? [Y/n]: ").lower()
                            if confirm in ('', 'y', 'yes'):
                                tool.commit_staged_changes(message)

                return # End of intelligent staging workflow
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
            commit_message = tool.generate_commit_message(staged_diff)
        
        # Confirm commit
        confirm = input("\nProceed with commit? [Y/n]: ").lower()
        if confirm in ('', 'y', 'yes'):
            tool.commit_staged_changes(commit_message)
        else:
            print("❌ Commit cancelled")
    
    except Exception as e:
        print(f"❌ Error: {e}\n\n{traceback.format_exc()}")
        if "API key" in str(e):
            print("💡 Tip: Run 'python git-commit-tool.py config' to set up your configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()