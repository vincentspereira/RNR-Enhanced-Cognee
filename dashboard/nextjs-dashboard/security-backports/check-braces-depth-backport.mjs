// Generated from scripts/check-braces-depth-backport.mjs; edit the maintained source and sync.
// Run in a bounded child process against the actual installed frontend package.
import assert from "node:assert/strict";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import { createRequire } from "node:module";
import { applyBackport } from "./apply-braces-depth-backport.mjs";

const project = path.resolve(process.argv[2] || process.cwd());
assert.deepEqual(applyBackport(project), applyBackport(project));
const require = createRequire(path.join(project, "package.json"));
const braces = require("braces");
const library = path.join(path.dirname(require.resolve("braces/package.json")), "lib");
const originalParse = require(path.join(library, "parse.js.rnr-before-depth-backport"));
const originalCompile = require(path.join(library, "compile.js.rnr-before-depth-backport"));
const attack = "{".repeat(4000) + "a,b" + "}".repeat(4000);
assert.throws(() => originalCompile(originalParse(attack)), /Maximum call stack size exceeded/);
assert.deepEqual(braces.expand("file-{one,two}-{1..2}.txt"),
  ["file-one-1.txt", "file-one-2.txt", "file-two-1.txt", "file-two-2.txt"]);
assert.equal(braces.compile("file-{one,two}.txt"), "file-(one|two).txt");
assert.deepEqual(braces.expand("\\{literal\\}"), ["{literal}"]);
assert(braces.compile("{".repeat(8) + "a,b" + "}".repeat(8)));
for (const count of [128, 4000]) {
  const input = "{".repeat(count) + "a,b" + "}".repeat(count);
  for (const operation of [braces, braces.parse, braces.compile, braces.expand])
    assert.throws(() => operation(input), error => error instanceof SyntaxError && /RNR brace nesting limit/.test(error.message));
  assert.throws(() => braces.parse("(".repeat(count) + "x" + ")".repeat(count)), /RNR brace nesting limit/);
}
// Already-parsed AST entry points also need bounds, independently of parsing.
const cyclic = { type: "root", nodes: [] };
cyclic.nodes.push(cyclic);
for (const operation of [braces.compile, braces.expand, braces.stringify])
  assert.throws(() => operation(cyclic), error => error instanceof SyntaxError && /RNR brace nesting limit/.test(error.message));
assert.equal(require("braces/package.json").version, "3.0.3");
// A changed dependency must fail before the first write, not receive a fuzzy patch.
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "rnr-braces-integrity-"));
const fixtureLib = path.join(fixture, "node_modules/braces/lib");
fs.mkdirSync(fixtureLib, { recursive: true });
fs.writeFileSync(path.join(fixture, "package.json"), "{}");
fs.writeFileSync(path.join(fixtureLib, "../package.json"), JSON.stringify({ name: "braces", version: "3.0.3" }));
for (const name of ["parse.js", "compile.js", "expand.js", "stringify.js"])
  fs.copyFileSync(path.join(library, name + ".rnr-before-depth-backport"), path.join(fixtureLib, name));
fs.appendFileSync(path.join(fixtureLib, "compile.js"), "\n// synthetic source-integrity mismatch\n");
assert.throws(() => applyBackport(fixture), /Unrecognized braces source/);
assert(!fs.existsSync(path.join(fixtureLib, "parse.js.rnr-before-depth-backport")));
const linked = fs.mkdtempSync(path.join(os.tmpdir(), "rnr-braces-linked-"));
fs.mkdirSync(path.join(linked, "node_modules/braces"), { recursive: true });
fs.writeFileSync(path.join(linked, "package.json"), "{}");
fs.writeFileSync(path.join(linked, "node_modules/braces/package.json"), JSON.stringify({ name: "braces", version: "3.0.3" }));
fs.symlinkSync(fixtureLib, path.join(linked, "node_modules/braces/lib"));
assert.throws(() => applyBackport(linked), /escaped library file/);
for (const name of ["one/a.ts", "two/b.tsx"]) {
  const file = path.join(fixture, "src", name);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, "// invented glob fixture\n");
}
assert.deepEqual(require("fast-glob").globSync("src/{one,two}/**/*.{ts,tsx}", { cwd: fixture }).sort(),
  ["src/one/a.ts", "src/two/b.tsx"]);
console.log("Braces backport: original exploit reproduced; normal/escaped patterns, nested strings, direct ASTs, repeat application and source-integrity refusal passed; upstream audit remains visible");
