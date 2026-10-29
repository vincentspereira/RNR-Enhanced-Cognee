// Reviewed local source backport for CVE-2026-93687 / GHSA-vfj7-8cjw-p6xm.
// Upstream braces remains MIT licensed, version 3.0.3. npm findings stay visible.
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const guard = "    if (depth > 64) throw new SyntaxError('RNR brace nesting limit exceeded (64)');\n";
const originals = {
  "parse.js": "e572166565f15fa6ad9865ae49d678218e32aabfd1b3720f6d0d43d39800d310",
  "compile.js": "dc98f22eee3d511785d92a00758d5f0d48efed5f5813bdecc2de430c529b5c9f",
  "expand.js": "41ccc196ebfa7b7781a634e721eb744e4e7bcb54cba427a7e3d6806a1b9e58f7",
  "stringify.js": "379f22d77bfa1478341ccd49c5e4267464aabcbba03558bab332aac23fc6f23a",
};
const digest = text => createHash("sha256").update(text).digest("hex");

function transform(name, text) {
  if (name === "parse.js") {
    return text.replaceAll("      stack.push(block);",
      "      stack.push(block);\n      if (stack.length > 64) throw new SyntaxError('RNR brace nesting limit exceeded (64)');");
  }
  if (name === "stringify.js") {
    return text.replace("const stringify = (node, parent = {}) => {",
      "const stringify = (node, parent = {}, depth = 0) => {\n" + guard)
      .replace("stringify(child);", "stringify(child, node, depth + 1);");
  }
  return text.replace("const walk = (node, parent = {}) => {",
    "const walk = (node, parent = {}, depth = 0) => {\n" + guard)
    .replaceAll("walk(child, node)", "walk(child, node, depth + 1)");
}

export function applyBackport(project) {
  const root = fs.realpathSync(project);
  const require = createRequire(path.join(root, "package.json"));
  const metadata = fs.realpathSync(require.resolve("braces/package.json"));
  if (!metadata.startsWith(path.join(root, "node_modules") + path.sep))
    throw new Error("Refusing to patch dependencies outside this frontend's node_modules");
  const location = path.dirname(metadata);
  const pkg = JSON.parse(fs.readFileSync(metadata));
  if (pkg.name !== "braces" || pkg.version !== "3.0.3")
    throw new Error("Review the backport against the changed upstream braces version");
  const changes = [];
  for (const [name, expected] of Object.entries(originals)) {
    const file = path.join(location, "lib", name);
    if (fs.lstatSync(file).isSymbolicLink() || !fs.realpathSync(file).startsWith(location + path.sep))
      throw new Error("Refusing a linked or escaped library file");
    const saved = file + ".rnr-before-depth-backport";
    if (fs.existsSync(saved) && (fs.lstatSync(saved).isSymbolicLink()
        || digest(fs.readFileSync(saved, "utf8")) !== expected))
      throw new Error("Braces saved-original integrity mismatch");
    const current = fs.readFileSync(file, "utf8");
    let original = current;
    if (digest(current) !== expected) {
      if (!fs.existsSync(saved) || fs.lstatSync(saved).isSymbolicLink())
        throw new Error("Unrecognized braces source; no fuzzy patching is allowed");
      original = fs.readFileSync(saved, "utf8");
    }
    if (digest(original) !== expected) throw new Error("Braces original source integrity mismatch");
    const patched = transform(name, original);
    if (patched === original) throw new Error("Backport has no effect");
    if (current !== original && current !== patched) throw new Error("Braces patched source integrity mismatch");
    changes.push({ file, saved, current, original, patched });
  }
  // Validate every file before changing any. Retain originals; reruns are safe.
  for (const item of changes) {
    if (item.current === item.patched) continue;
    if (!fs.existsSync(item.saved)) fs.writeFileSync(item.saved, item.original, { flag: "wx" });
    fs.writeFileSync(item.file, item.patched);
  }
  return Object.fromEntries(changes.map(item => [path.basename(item.file), digest(item.patched)]));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = applyBackport(process.argv[2] || process.cwd());
  console.log(JSON.stringify({ backport: "CVE-2026-93687-depth-64", files: result,
    upstream_version_unchanged: true, official_npm_advisory_still_applies: true }));
}
