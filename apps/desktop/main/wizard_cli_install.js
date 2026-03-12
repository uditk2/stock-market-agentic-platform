const { spawn } = require('child_process');
const { buildCommandEnv, runCommand } = require('./cli_checks');

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

function shellCommandForPlatform(platform, command) {
  if (platform === 'win32') {
    return { binary: 'cmd.exe', args: ['/d', '/s', '/c', command] };
  }
  return { binary: '/bin/bash', args: ['-lc', command] };
}

function runShellCommand(command, { platform, env } = {}) {
  const spec = shellCommandForPlatform(platform, command);
  return new Promise((resolve) => {
    const child = spawn(spec.binary, spec.args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: env || buildCommandEnv(),
      shell: false,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
    child.on('error', (error) => {
      resolve({
        ok: false,
        code: 1,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        error: String(error.message || error),
      });
    });
    child.on('close', (code) => {
      resolve({
        ok: code === 0,
        code: typeof code === 'number' ? code : 1,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        error: null,
      });
    });
  });
}

async function runWizardCliInstall(options, commandRunner = runShellCommand) {
  const plan = buildWizardCliInstallPlan(options);
  if (!plan.ok) {
    return plan;
  }
  const target = CLI_TARGETS[plan.cli_id];
  const env = buildCommandEnv();
  const prereq = await commandRunner(plan.prereq_check_command, {
    platform: options?.platform,
    env,
  });
  if (!prereq.ok) {
    return {
      ok: false,
      error: 'prereq_failed',
      message: `npm is required before installing ${plan.cli_label}. ${plan.node_install_hint}`,
      stdout: prereq.stdout,
      stderr: prereq.stderr || prereq.error,
      cli_id: plan.cli_id,
      cli_label: plan.cli_label,
    };
  }
  const install = await commandRunner(plan.install_command, {
    platform: options?.platform,
    env,
  });
  if (!install.ok) {
    return {
      ok: false,
      error: 'install_failed',
      message: `${plan.cli_label} install failed.`,
      stdout: install.stdout,
      stderr: install.stderr || install.error,
      cli_id: plan.cli_id,
      cli_label: plan.cli_label,
      auth_command: plan.auth_command,
    };
  }
  const verifyTokens = String(target.verifyCommand).split(/\s+/);
  const verify = runCommand(verifyTokens[0], verifyTokens.slice(1));
  return {
    ok: verify.success,
    error: verify.success ? null : 'verify_failed',
    message: verify.success
      ? `${plan.cli_label} installed. Run '${plan.auth_command}' if login is still pending.`
      : `${plan.cli_label} install completed but verify failed.`,
    stdout: install.stdout,
    stderr: install.stderr,
    version: verify.stdout || verify.stderr || null,
    cli_id: plan.cli_id,
    cli_label: plan.cli_label,
    auth_command: plan.auth_command,
  };
}

module.exports = {
  CLI_TARGETS,
  SUBSCRIPTION_ACCESS,
  buildWizardCliInstallPlan,
  shellCommandForPlatform,
  runShellCommand,
  runWizardCliInstall,
};
