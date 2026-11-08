import pg from "pg";
import { Redis } from "ioredis";

export default async function setup() {
  const admin = new pg.Client({ connectionString: "postgres://geasy:geasy@127.0.0.1:5432/postgres" });
  await admin.connect();
  await admin.query("DROP DATABASE IF EXISTS geasy_test WITH (FORCE)");
  await admin.query("CREATE DATABASE geasy_test");
  await admin.end();
  const r = new Redis("redis://127.0.0.1:6379/9");
  await r.flushdb();
  r.disconnect();
}
