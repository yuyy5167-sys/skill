import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const relativeModulePath = path.join(
  "codex-runtimes",
  "codex-primary-runtime",
  "dependencies",
  "node",
  "node_modules",
  "@oai",
  "artifact-tool",
  "dist",
  "artifact_tool.mjs",
);

const candidates = [
  process.env.CODEX_ARTIFACT_TOOL_MODULE,
  path.join(os.homedir(), ".cache", relativeModulePath),
  process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, relativeModulePath),
].filter(Boolean);

const modulePath = candidates.find((candidate) => (
  String(candidate).startsWith("file:") || fs.existsSync(candidate)
));

if (!modulePath) {
  throw new Error(
    "artifact-toolが見つかりません。CODEX_ARTIFACT_TOOL_MODULEにartifact_tool.mjsのパスを指定してください。",
  );
}

const moduleUrl = String(modulePath).startsWith("file:")
  ? modulePath
  : pathToFileURL(modulePath).href;

const artifactTool = await import(moduleUrl);

export const { FileBlob, SpreadsheetFile, Workbook } = artifactTool;
