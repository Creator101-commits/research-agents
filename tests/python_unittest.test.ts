import { expect, test } from "bun:test";

// The suite includes multi-year ledger, body-weight and per-control runs (about 35 s).
test("python unittest suite passes", { timeout: 120_000 }, async () => {
  const proc = Bun.spawn(["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], {
    stdout: "pipe",
    stderr: "pipe",
  });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  expect(`${stdout}\n${stderr}`).toBeString();
  expect(exitCode).toBe(0);
});
