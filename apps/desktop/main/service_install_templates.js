const fs = require('fs');
const path = require('path');

const TEMPLATE_FILES = {
  linux: 'linux.systemd-user.service.tmpl',
  macos: 'macos.launchagent.plist.tmpl',
  windows: 'windows.task.xml.tmpl',
};

function templatesDir() {
  return path.join(__dirname, '..', 'resources', 'service_templates');
}

function xmlEscape(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function readTemplate(target) {
  const fileName = TEMPLATE_FILES[target];
  if (!fileName) {
    throw new Error(`unsupported_target:${target}`);
  }
  return fs.readFileSync(path.join(templatesDir(), fileName), 'utf8');
}

function replaceTokens(content, replacements) {
  let rendered = content;
  for (const [key, value] of Object.entries(replacements)) {
    rendered = rendered.split(`{{${key}}}`).join(String(value));
  }
  return rendered;
}

function asArgsSegment(args) {
  if (!Array.isArray(args) || args.length === 0) {
    return '';
  }
  return ` ${args.join(' ')}`;
}

function renderLinuxSystemdUnit(input) {
  const template = readTemplate('linux');
  const replacements = {
    DESCRIPTION: input.description || 'SMAP Background Service',
    WORKING_DIRECTORY: input.workingDirectory,
    SERVICE_BIN: input.serviceBin,
    SERVICE_ARGS_SEGMENT: asArgsSegment(input.serviceArgs || []),
  };
  return replaceTokens(template, replacements);
}

function renderMacLaunchAgent(input) {
  const template = readTemplate('macos');
  const args = [input.serviceBin, ...(input.serviceArgs || [])];
  const argsXml = args.map((entry) => `      <string>${xmlEscape(entry)}</string>`).join('\n');
  const replacements = {
    LABEL: input.label || 'com.smap.service',
    WORKING_DIRECTORY: xmlEscape(input.workingDirectory),
    PROGRAM_ARGUMENTS_XML: argsXml,
    STDOUT_PATH: xmlEscape(input.stdoutPath || path.join(input.workingDirectory, 'smap-service.out.log')),
    STDERR_PATH: xmlEscape(input.stderrPath || path.join(input.workingDirectory, 'smap-service.err.log')),
  };
  return replaceTokens(template, replacements);
}

function renderWindowsTaskXml(input) {
  const template = readTemplate('windows');
  const replacements = {
    DESCRIPTION: xmlEscape(input.description || 'SMAP Background Service Task'),
    SERVICE_BIN: xmlEscape(input.serviceBin),
    SERVICE_ARGS: xmlEscape((input.serviceArgs || []).join(' ')),
    WORKING_DIRECTORY: xmlEscape(input.workingDirectory),
  };
  return replaceTokens(template, replacements);
}

function renderServiceTemplate(target, input) {
  if (target === 'linux') {
    return renderLinuxSystemdUnit(input);
  }
  if (target === 'macos') {
    return renderMacLaunchAgent(input);
  }
  if (target === 'windows') {
    return renderWindowsTaskXml(input);
  }
  throw new Error(`unsupported_target:${target}`);
}

module.exports = {
  renderLinuxSystemdUnit,
  renderMacLaunchAgent,
  renderWindowsTaskXml,
  renderServiceTemplate,
  xmlEscape,
};
