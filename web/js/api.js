export async function loadDefaults() {
  const response = await fetch("/api/scenario");
  return response.json();
}

export async function runSimulation(body) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
  return data;
}

export async function downloadRun(runId) {
  const response = await fetch("/api/export/" + encodeURIComponent(runId));
  if (!response.ok) return null;
  return response.blob();
}
