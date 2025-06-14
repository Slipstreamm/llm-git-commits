document.addEventListener('DOMContentLoaded', () => {
    // @ts-ignore
    const vscode = acquireVsCodeApi();

    const providerSelect = document.getElementById('provider');
    const commitStyleSelect = document.getElementById('commitStyle');
    const providerConfigSections = document.querySelectorAll('.provider-config');
    const allInputs = document.querySelectorAll('input[data-key], select');

    function showProviderSettings(provider) {
        providerConfigSections.forEach(section => {
            if (section.id === `${provider}-settings`) {
                section.classList.add('visible');
            } else {
                section.classList.remove('visible');
            }
        });
    }

    // --- Event Listeners for UI -> Extension ---

    allInputs.forEach(input => {
        const eventType = input.tagName === 'SELECT' ? 'change' : 'input';
        input.addEventListener(eventType, (e) => {
            const key = e.target.dataset.key || (e.target.id === 'provider' ? 'provider' : 'commit.style');
            vscode.postMessage({
                command: 'updateSetting',
                key: key,
                value: e.target.value,
            });
        });
    });

    providerSelect.addEventListener('change', (e) => {
        showProviderSettings(e.target.value);
    });


    // --- Event Listener for Extension -> UI ---

    window.addEventListener('message', event => {
        const message = event.data;
        if (message.command === 'setSettings') {
            const settings = message.settings;

            // Provider
            if (settings.provider) {
                providerSelect.value = settings.provider;
                showProviderSettings(settings.provider);
            }

            // Commit Style
            if (settings.commitStyle) {
                commitStyleSelect.value = settings.commitStyle;
            }

            // Provider-specific settings
            for (const provider in settings.providers) {
                const providerConf = settings.providers[provider];
                const apiKeyInput = document.getElementById(`${provider}.apiKey`);
                const modelInput = document.getElementById(`${provider}.model`);

                if (apiKeyInput && providerConf.apiKey) {
                    apiKeyInput.value = providerConf.apiKey;
                }
                if (modelInput && providerConf.model) {
                    modelInput.value = providerConf.model;
                }
            }
        }
    });

    // --- Request initial settings on load ---
    vscode.postMessage({ command: 'getSettings' });
});