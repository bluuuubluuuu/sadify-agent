import { cp, mkdir, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const standaloneDir = join(root, ".next", "standalone");

async function copyIfExists(source, destination) {
  if (!existsSync(source)) {
    return;
  }

  await rm(destination, { force: true, recursive: true });
  await mkdir(join(destination, ".."), { recursive: true });
  await cp(source, destination, { recursive: true });
}

await copyIfExists(
  join(root, ".next", "static"),
  join(standaloneDir, ".next", "static"),
);
await copyIfExists(join(root, "public"), join(standaloneDir, "public"));
