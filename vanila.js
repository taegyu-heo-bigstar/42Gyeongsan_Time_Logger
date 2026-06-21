await fetch("http://localhost:8000/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ password })
});

await fetch("http://localhost:8000/logs/start", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Admin-Password": password
  },
  body: JSON.stringify({
    work_date: "2026-06-21"
  })
});

await fetch("http://localhost:8000/logs/stop", {
  method: "POST",
  headers: {
    "X-Admin-Password": password
  }
});