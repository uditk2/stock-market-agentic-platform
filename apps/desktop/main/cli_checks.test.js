const test = require('node:test');
const assert = require('node:assert/strict');

const { checkSingleCli, runMandatoryCliChecks } = require('./cli_checks');

function makeRunner(map) {
  return (binary, args) => {
    const key = `${binary} ${args.join(' ')}`;
    const result = map[key];
    if (!result) {
      return {
        success: false,
        stdout: '',
        stderr: 'not mocked',
        exitCode: 1,
        error: 'not mocked',
      };
    }
    return result;
  };
}

test('checkSingleCli fails when executable is missing', () => {
  const runner = makeRunner({
    'codex --version': {
      success: false,
      stdout: '',
      stderr: 'not found',
      exitCode: 127,
      error: 'ENOENT',
    },
  });

  const result = checkSingleCli(
    {
      id: 'codex',
      label: 'OpenAI Codex CLI',
      binary: 'codex',
      authCandidates: [['auth', 'status']],
    },
    runner,
  );

  assert.equal(result.installed, false);
  assert.equal(result.pass, false);
});

test('checkSingleCli passes when version and auth probes pass', () => {
  const runner = makeRunner({
    'codex --version': {
      success: true,
      stdout: 'codex 1.2.3',
      stderr: '',
      exitCode: 0,
      error: null,
    },
    'codex auth status': {
      success: true,
      stdout: 'authenticated',
      stderr: '',
      exitCode: 0,
      error: null,
    },
  });

  const result = checkSingleCli(
    {
      id: 'codex',
      label: 'OpenAI Codex CLI',
      binary: 'codex',
      authCandidates: [['auth', 'status']],
    },
    runner,
  );

  assert.equal(result.installed, true);
  assert.equal(result.auth_ok, true);
  assert.equal(result.pass, true);
});

test('runMandatoryCliChecks aggregates status', () => {
  const runner = makeRunner({
    'codex --version': { success: true, stdout: 'codex 1.2.3', stderr: '', exitCode: 0, error: null },
    'codex auth status': { success: true, stdout: 'ok', stderr: '', exitCode: 0, error: null },
    'claude --version': { success: true, stdout: 'claude 0.9.0', stderr: '', exitCode: 0, error: null },
    'claude auth status': { success: false, stdout: '', stderr: 'not logged in', exitCode: 1, error: null },
    'claude whoami': { success: false, stdout: '', stderr: 'not logged in', exitCode: 1, error: null },
  });

  const result = runMandatoryCliChecks(runner);
  assert.equal(result.ok, false);
  assert.equal(result.checks.length >= 2, true);
});
