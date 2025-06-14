import fetch from 'node-fetch';
import { ExtensionConfig, AIProvider } from './types';
import { getSystemPrompt } from './prompts';

interface ProviderDetails {
    baseURL: string;
    modelFormat: (model: string) => string;
    headers: (apiKey: string) => Record<string, string>;
    body: (model: string, messages: any[]) => Record<string, any>;
    responseExtractor: (data: any) => string;
}

const providerDetails: Record<AIProvider, ProviderDetails> = {
    openrouter: {
        baseURL: 'https://openrouter.ai/api/v1',
        modelFormat: model => model,
        headers: apiKey => ({
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/llm-git-commits',
            'X-Title': 'Git Commit Tool'
        }),
        body: (model, messages) => ({
            model,
            messages,
            temperature: 0.3,
            max_tokens: 2048,
        }),
        responseExtractor: data => data.choices[0].message.content,
    },
    openai: {
        baseURL: 'https://api.openai.com/v1',
        modelFormat: model => model,
        headers: apiKey => ({
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
        }),
        body: (model, messages) => ({
            model,
            messages,
            temperature: 0.3,
            max_tokens: 2048,
        }),
        responseExtractor: data => data.choices[0].message.content,
    },
    anthropic: {
        baseURL: 'https://api.anthropic.com/v1',
        modelFormat: model => model,
        headers: apiKey => ({
            'x-api-key': apiKey,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
        }),
        body: (model, messages) => {
            const systemMessage = messages.find(msg => msg.role === 'system');
            const userMessages = messages.filter(msg => msg.role !== 'system');
            return {
                model,
                system: systemMessage?.content,
                messages: userMessages,
                temperature: 0.3,
                max_tokens: 2048,
            };
        },
        responseExtractor: data => data.content[0].text,
    },
    gemini: {
        baseURL: 'https://generativelanguage.googleapis.com/v1beta',
        modelFormat: model => `models/${model}`,
        headers: apiKey => ({
            'Content-Type': 'application/json',
        }),
        body: (model, messages) => {
            // Gemini has a different message format
            // System messages should be passed via the system_instruction field
            const systemMessage = messages.find(msg => msg.role === 'system');
            const userMessages = messages.filter(msg => msg.role !== 'system');

            const contents = userMessages.map(msg => ({
                role: msg.role === 'assistant' ? 'model' : msg.role,
                parts: [{ text: msg.content }],
            }));

            const body: any = { contents };
            if (systemMessage) {
                body.system_instruction = {
                    role: 'system',
                    parts: [{ text: systemMessage.content }],
                };
            }

            return body;
        },
        responseExtractor: data => data.candidates[0].content.parts[0].text,
    },
};

export async function getAiCompletion(diff: string, config: ExtensionConfig): Promise<string> {
    const { commitStyle } = config;
    const systemPrompt = getSystemPrompt(commitStyle);
    const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Generate a commit message for these changes:\n\n\`\`\`diff\n${diff}\n\`\`\`` },
    ];
    return getAiCompletionFromMessages(messages, config);
}

export async function getAiCompletionFromMessages(messages: any[], config: ExtensionConfig): Promise<string> {
    const { provider } = config;
    const providerConfig = config.providers[provider];

    if (!providerConfig.apiKey) {
        throw new Error(`API key for ${provider} is not set.`);
    }

    const details = providerDetails[provider];

    const endpoint = provider === 'gemini'
        ? `${details.baseURL}/${details.modelFormat(providerConfig.model)}:generateContent?key=${providerConfig.apiKey}`
        : `${details.baseURL}/chat/completions`;

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: details.headers(providerConfig.apiKey),
        body: JSON.stringify(details.body(providerConfig.model, messages)),
    });

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`API request failed with status ${response.status}: ${errorBody}`);
    }

    const data = await response.json();
    return details.responseExtractor(data).trim();
}

export interface FileDiff {
    id: string;
    filepath: string;
    diff: string;
}

export interface CommitPlan {
    commit_plan: { commit_message: string; file_ids: string[] }[];
    unplanned_file_ids: string[];
}

export async function getCommitPlan(diffs: FileDiff[], config: ExtensionConfig): Promise<CommitPlan> {
    const systemPrompt = `You are an expert at analyzing code changes and creating a logical series of git commits.\n` +
        `Your task is to group all provided file diffs into focused commits.\n` +
        `Return a JSON object with \"commit_plan\" (list of commits with commit_message and file_ids) ` +
        `and \"unplanned_file_ids\" (list of files that do not fit).`;

    const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Here are the diffs:\n\n${JSON.stringify(diffs, null, 2)}` },
    ];

    const response = await getAiCompletionFromMessages(messages, config);
    const match = response.match(/\{.*\}/s);
    if (match) {
        try {
            return JSON.parse(match[0]);
        } catch {
            // ignore
        }
    }
    throw new Error('Could not parse commit plan from LLM response');
}