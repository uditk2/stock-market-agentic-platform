const CLI_TARGETS = {
  codex: {
    id: 'codex',
    label: 'OpenAI Codex CLI',
    packageName: '@openai/codex',
    authCommand: 'codex auth login',
    verifyCommand: 'codex --version',
  },
  claude: {
    id: 'claude',
    label: 'Claude CLI',
    packageName: '@anthropic-ai/claude-code',
    authCommand: 'claude auth login',
    verifyCommand: 'claude --version',
  },
};

const SUBSCRIPTION_ACCESS = {
  none: [],
  codex: ['codex'],
  claude: ['claude'],
  both: ['codex', 'claude'],
};

function npmInstallHint(platform) {
  if (platform === 'darwin') {
    return 'Install Node.js first: brew install node';
  }
  if (platform === 'win32') {
    return 'Install Node.js first: winget install OpenJS.NodeJS.LTS';
  }
  return 'Install Node.js/npm first: sudo apt-get install -y npm';
}

function buildWizardCliInstallPlan({ platform, subscription, cliId }) {
  const target = CLI_TARGETS[String(cliId || '').trim()];
  if (!target) {
    return {
      ok: false,
      error: 'unknown_cli_target',
      message: 'Select a valid CLI target (Codex or Claude).',
    };
  }
  const access = SUBSCRIPTION_ACCESS[String(subscription || '').trim()];
  if (!access) {
    return {
      ok: false,
      error: 'unknown_subscription',
      message: 'Select your subscription before starting install.',
    };
  }
  if (!access.includes(target.id)) {
    return {
      ok: false,
      error: 'subscription_mismatch',
      message: `Selected subscription does not include ${target.label}.`,
    };
  }
  const installCommand = `npm install -g ${target.packageName}`;
  return {
    ok: true,
    cli_id: target.id,
    cli_label: target.label,
    subscription,
    prereq_check_command: 'npm --version',
    install_command: installCommand,
    auth_command: target.authCommand,
    verify_command: target.verifyCommand,
    node_install_hint: npmInstallHint(platform),
  };
}

module.exports = {
  CLI_TARGETS,
  SUBSCRIPTION_ACCESS,
  buildWizardCliInstallPlan,
};
