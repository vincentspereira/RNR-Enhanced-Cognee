// Keep standalone frontend/Docker contexts in sync with one maintained backport.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const check = process.argv.includes("--check");
for (const project of ["dashboard/nextjs-dashboard", "cognee-frontend"]) {
  for (const name of ["apply-braces-depth-backport.mjs", "check-braces-depth-backport.mjs"]) {
    const header = "// Generated from scripts/" + name + "; edit the maintained source and sync.\n";
    const text = header + fs.readFileSync(path.join(root, "scripts", name), "utf8");
    const target = path.join(root, project, "security-backports", name);
    const old = fs.existsSync(target) ? fs.readFileSync(target, "utf8") : null;
    if (old === text) continue;
    if (check) throw new Error("Frontend backport copy is missing or stale: " + project + "/" + name);
    if (old !== null && !old.startsWith("// Generated from scripts/"))
      throw new Error("Refusing to replace an unrelated file");
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
  }
}
console.log(check ? "Frontend backport copies match maintained source" : "Frontend backport copies synchronized");
