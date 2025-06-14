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

    public async getUnstagedDiff(): Promise<string> {
        if (!this.git) {
            return '';
        }
        let diff = await this.git.diff();
        const untracked = (await this.git.raw(['ls-files', '--others', '--exclude-standard']))
            .split('\n')
            .filter(f => f);
        for (const file of untracked) {
            diff += await this.git.diff(['--no-index', '/dev/null', file]);
        }
        return diff;
    }

    public async hasStagedChanges(): Promise<boolean> {
        if (!this.git) {
            return false;
        }
        const status = await this.git.status();
        return status.staged.length > 0;
    }

    public async getModifiedFiles(): Promise<string[]> {
        if (!this.git) {
            return [];
        }
        const status = await this.git.status();
        const renamed = status.renamed.map(r => r.to);
        return [
            ...status.modified,
            ...status.created,
            ...status.deleted,
            ...status.not_added,
            ...renamed,
            ...status.staged,
        ];
    }

    public async getFileDiff(filePath: string): Promise<string> {
        if (!this.git) {
            return '';
        }
        const tracked = (await this.git.raw(['ls-files', '--', filePath])).trim().length > 0;
        if (tracked) {
            return await this.git.diff([filePath]);
        }
        return await this.git.diff(['--no-index', '/dev/null', filePath]);
    }

    public async stageFiles(files: string[]): Promise<void> {
        if (!this.git || files.length === 0) {
            return;
        }
        await this.git.add(files);
    }

    public async commit(message: string): Promise<void> {
        if (!this.git) {
            return;
        }
        await this.git.commit(message);
    }

    // Add other git methods here as needed for future features
    // e.g., stageHunks, getModifiedFiles, etc.
}