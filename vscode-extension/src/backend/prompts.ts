import { CommitStyle } from './types';

const conventionalCommitPrompt = `You are an expert software developer who writes excellent git commit messages.
Guidelines for commit messages:
- Use conventional commits format: type(scope): description
- Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf
- Keep the first line under 50 characters
- Use imperative mood (e.g., "Add" not "Added")
- Be specific and descriptive
- If there are multiple changes, focus on the most significant one
- Add a body if needed to explain WHY the change was made
Analyze the git diff and write a concise, informative commit message.
Do not wrap the commit message in any kind of markdown or say anything other than the final commit text.`;

const descriptivePastTensePrompt = `You are an expert software developer who writes excellent git commit messages.
Generate a concise, imperative sentence in the past tense describing the changes.
Example: Added password reset functionality to the authentication module.
Analyze the git diff and write a concise, informative commit message.
Do not wrap the commit message in any kind of markdown or say anything other than the final commit text.`;

const emojiPrefixedPrompt = `You are an expert software developer who writes excellent git commit messages.
Generate a message that starts with a relevant emoji, followed by a present-tense description.
The AI should select an appropriate emoji for the change type (e.g., ✨ for a new feature, 🐛 for a bug fix, 📚 for documentation).
Example: ✨ Add password reset feature.
Analyze the git diff and write a concise, informative commit message.
Do not wrap the commit message in any kind of markdown or say anything other than the final commit text.`;

const defaultPrompt = `You are an expert software developer who writes excellent git commit messages.
Generate a clear, neutral, and concise summary of the changes.
Example: Update code to include password reset.
Analyze the git diff and write a concise, informative commit message.
Do not wrap the commit message in any kind of markdown or say anything other than the final commit text.`;

export function getSystemPrompt(style: CommitStyle): string {
    switch (style) {
        case 'Conventional Commit':
            return conventionalCommitPrompt;
        case 'Descriptive (Past Tense)':
            return descriptivePastTensePrompt;
        case 'Emoji-Prefixed':
            return emojiPrefixedPrompt;
        case 'Default':
            return defaultPrompt;
        default:
            return defaultPrompt;
    }
}