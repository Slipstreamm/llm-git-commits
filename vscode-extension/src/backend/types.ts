/**
 * Represents the built-in Git extension API.
 */
export interface GitExtension {
    getAPI(version: 1): API;
}

export interface API {
    repositories: Repository[];
}

export interface Repository {
    rootUri: { fsPath: string };
    inputBox: { value: string };
    diffIndexWith(ref: string, path: string): Promise<string>;
    state: {
        indexChanges: { uri: { fsPath: string } }[];
    };
}

/**
 * Defines the structure for the extension's configuration.
 */

export type CommitStyle = 'Conventional Commit' | 'Descriptive (Past Tense)' | 'Emoji-Prefixed' | 'Default';
export type AIProvider = 'openrouter' | 'openai' | 'anthropic' | 'gemini';

export interface ProviderConfig {
    apiKey: string;
    model: string;
}

export interface ExtensionConfig {
    provider: AIProvider;
    commitStyle: CommitStyle;
    providers: {
        openrouter: ProviderConfig;
        openai: ProviderConfig;
        anthropic: ProviderConfig;
        gemini: ProviderConfig;
    };
}