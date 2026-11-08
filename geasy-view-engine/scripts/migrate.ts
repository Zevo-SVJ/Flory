import { runMigrations } from "../src/lib/migrate";
import { closePool } from "../src/lib/db";

runMigrations()
  .then((a) => console.log(a.length ? `Applied: ${a.join(", ")}` : "Database up to date"))
  .catch((e) => { console.error(e); process.exitCode = 1; })
  .finally(() => closePool());
