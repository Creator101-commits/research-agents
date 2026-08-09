import { expect, test } from "bun:test";

test("python unittest suite passes", { timeout: 30_000 }, async () => {
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
