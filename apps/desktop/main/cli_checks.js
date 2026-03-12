const { spawnSync } = require('child_process');

const CLI_DEFINITIONS = [
  {
    id: 'codex',
    label: 'OpenAI Codex CLI',
    binary: 'codex',
    authCandidates: [
      ['login', 'status'],
      ['whoami'],
    ],
  },
  {
    id: 'claude',
    label: 'Claude CLI',
    binary: 'claude',
    authCandidates: [],
  },
];

function runCommand(binary, args) {
  const result = spawnSync(binary, args, {
    encoding: 'utf8',
    timeout: 5000,
    shell: false,
  });
  const stdout = (result.stdout || '').trim();
  const stderr = (result.stderr || '').trim();
  const exitCode = typeof result.status === 'number' ? result.status : 1;
  const success = !result.error && exitCode === 0;
  return {
    success,
    stdout,
    stderr,
    exitCode,
    error: result.error ? String(result.error.message || result.error) : null,
  };
}

function parseVersion(raw) {
  if (!raw) {
    return null;
  }
  return raw.split('\n')[0].trim() || null;
}

function checkSingleCli(definition, runner = runCommand) {
  const versionProbe = runner(definition.binary, ['--version']);
  if (!versionProbe.success) {
    return {
      id: definition.id,
      label: definition.label,
      installed: false,
      version: null,
      auth_ok: false,
      pass: false,
      diagnostics: {
        version_probe: versionProbe,
        auth_probe: null,
      },
    };
  }

  const version = parseVersion(versionProbe.stdout || versionProbe.stderr);
  if (!definition.authCandidates.length) {
    return {
      id: definition.id,
      label: definition.label,
      installed: true,
      version,
      auth_ok: true,
      pass: Boolean(version),
      diagnostics: {
        version_probe: versionProbe,
        auth_probe: null,
      },
    };
  }

  let authProbe = null;
  for (const candidate of definition.authCandidates) {
    const probe = runner(definition.binary, candidate);
    if (probe.success) {
      authProbe = {
        ...probe,
        command: `${definition.binary} ${candidate.join(' ')}`,
      };
      break;
    }
    if (!authProbe) {
      authProbe = {
        ...probe,
        command: `${definition.binary} ${candidate.join(' ')}`,
      };
    }
  }

  const authOk = Boolean(authProbe && authProbe.success);
  return {
    id: definition.id,
    label: definition.label,
    installed: true,
    version,
    auth_ok: authOk,
    pass: Boolean(version && authOk),
    diagnostics: {
      version_probe: versionProbe,
      auth_probe: authProbe,
    },
  };
}

function runMandatoryCliChecks(optionsOrRunner = {}, maybeRunner = runCommand) {
  let options = optionsOrRunner;
  let runner = maybeRunner;
  if (typeof optionsOrRunner === 'function') {
    runner = optionsOrRunner;
    options = {};
  }
  const requiredCliIds = Array.isArray(options?.requiredCliIds)
    ? new Set(options.requiredCliIds.map((item) => String(item)))
    : null;
  const definitions = requiredCliIds && requiredCliIds.size
    ? CLI_DEFINITIONS.filter((definition) => requiredCliIds.has(definition.id))
    : CLI_DEFINITIONS;
  const checks = definitions.map((definition) => checkSingleCli(definition, runner));
  return {
    ok: checks.every((entry) => entry.pass),
    checks,
    required_cli_ids: definitions.map((definition) => definition.id),
    checked_at: new Date().toISOString(),
  };
}

module.exports = {
  CLI_DEFINITIONS,
  runCommand,
  checkSingleCli,
  runMandatoryCliChecks,
};
