import * as vscode from 'vscode';
import simpleGit, { SimpleGit } from 'simple-git';
import { API, GitExtension, Repository } from './types';

export class GitService {
    private git: SimpleGit | undefined;
    private vscGitApi: API | undefined;

    private constructor(vscGitApi: API) {
        this.vscGitApi = vscGitApi;
        if (vscGitApi.repositories[0]) {
            const repoPath = vscGitApi.repositories[0].rootUri.fsPath;
            this.git = simpleGit(repoPath);
        }
    }

    public static async create(): Promise<GitService> {
        const extension = vscode.extensions.getExtension<GitExtension>('vscode.git');
        if (!extension) {
            throw new Error('Git extension is not available.');
        }
        if (!extension.isActive) {
            await extension.activate();
        }
        const vscGitApi = extension.exports.getAPI(1);
        if (vscGitApi.repositories.length === 0) {
            throw new Error('No Git repository found.');
        }
        return new GitService(vscGitApi);
    }

    public getRepository(): Repository {
        if (!this.vscGitApi || this.vscGitApi.repositories.length === 0) {
            throw new Error('No Git repository available.');
        }
        return this.vscGitApi.repositories[0];
    }

    public async getStagedDiff(): Promise<string | undefined> {
        const repo = this.getRepository();
        let diff = '';
        for (const change of repo.state.indexChanges) {
            diff += await repo.diffIndexWith('HEAD', change.uri.fsPath);
        }
        return diff;
    }
    
    // Add other git methods here as needed for future features
    // e.g., stageHunks, getModifiedFiles, etc.
}