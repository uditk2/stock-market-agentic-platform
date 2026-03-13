const PROFILES = {
  ops_status: {
    description: 'Operational status and readonly health checks',
    validators: [
      /^pwd$/,
      /^ls(\s+[-\w./]+)?$/,
      /^git\s+status$/,
      /^curl\s+http:\/\/127\.0\.0\.1:\d+\/(health|connectors\/diagnostics|connectors\/observability)$/,
    ],
  },
  service_logs: {
    description: 'Service state and recent logs',
    validators: [
      /^systemctl\s+status\s+[\w@.-]+(\.service)?$/,
      /^journalctl\s+-u\s+[\w@.-]+(\.service)?\s+-n\s+\d+\s+--no-pager$/,
    ],
  },
  repo_dev: {
    description: 'Repository inspection commands (non-destructive)',
    validators: [
      /^pwd$/,
      /^ls(\s+[-\w./]+)?$/,
      /^git\s+status$/,
      /^git\s+diff(\s+--\s+.*)?$/,
      /^git\s+log\s+--oneline(\s+-n\s+\d+)?$/,
      /^npm\s+run\s+(test|build)$/,
      /^python3\s+--version$/,
    ],
  },
};

function hasShellMetacharacters(command) {
  return /[;&|`]/.test(command);
}

function isCommandAllowed(profile, command) {
  const trimmed = (command || '').trim();
  if (!trimmed) {
    return false;
  }
  if (hasShellMetacharacters(trimmed)) {
    return false;
  }
  const rules = PROFILES[profile];
  if (!rules) {
    return false;
  }
  return rules.validators.some((validator) => validator.test(trimmed));
}

module.exports = {
  PROFILES,
  isCommandAllowed,
};
