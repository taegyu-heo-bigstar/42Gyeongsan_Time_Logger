const API_BASE = "42-gyeongsan-time-logger-fi688ghoq-taegyu-heo-bigstars-projects.vercel.app";
const PASSWORD_KEY = "time_logger_admin_password";

const $ = (selector) => document.querySelector(selector);

function getPassword() {
  return sessionStorage.getItem(PASSWORD_KEY) || "";
}

function setPassword(password) {
  sessionStorage.setItem(PASSWORD_KEY, password);
}

function clearPassword() {
  sessionStorage.removeItem(PASSWORD_KEY);
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  const password = getPassword();

  if (options.auth !== false) {
    headers["X-Admin-Password"] = password;
  }

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message = data?.detail || `요청 실패: ${response.status}`;
    throw new Error(message);
  }

  return data;
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function dateKey(year, monthIndex, day) {
  return `${year}-${pad2(monthIndex + 1)}-${pad2(day)}`;
}

function todayKey() {
  const now = new Date();
  return dateKey(now.getFullYear(), now.getMonth(), now.getDate());
}

function formatDateTime(value) {
  if (!value) return "-";

  return new Date(value).toLocaleString("ko-KR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatTime(value) {
  if (!value) return "-";

  return new Date(value).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds) {
  seconds = Number(seconds || 0);

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);

  if (h > 0) return `${h}시간 ${m}분`;
  if (m > 0) return `${m}분`;
  return `${seconds}초`;
}

function setMessage(text, isError = true) {
  const loginMessage = $("#loginMessage");
  const appMessage = $("#appMessage");
  const target = loginMessage || appMessage;

  if (!target) return;

  target.textContent = text || "";
  target.style.color = isError ? "#dc2626" : "#2563eb";
}

function setupLoginPage() {
  const form = $("#loginForm");

  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");

    const password = $("#password").value.trim();

    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || "로그인 실패");
      }

      setPassword(password);
      location.href = "calendar.html";
    } catch (error) {
      setMessage(error.message);
    }
  });
}

let currentYear;
let currentMonthIndex;
let selectedDate = todayKey();
let monthLogs = [];
let currentLog = null;

async function setupCalendarPage() {
  if (!$("#calendarGrid")) return;

  if (!getPassword()) {
    location.href = "index.html";
    return;
  }

  const now = new Date();
  currentYear = now.getFullYear();
  currentMonthIndex = now.getMonth();

  $("#logoutBtn").addEventListener("click", () => {
    clearPassword();
    location.href = "index.html";
  });

  $("#prevMonthBtn").addEventListener("click", async () => {
    currentMonthIndex -= 1;

    if (currentMonthIndex < 0) {
      currentMonthIndex = 11;
      currentYear -= 1;
    }

    selectedDate = dateKey(currentYear, currentMonthIndex, 1);
    await refreshAll();
  });

  $("#nextMonthBtn").addEventListener("click", async () => {
    currentMonthIndex += 1;

    if (currentMonthIndex > 11) {
      currentMonthIndex = 0;
      currentYear += 1;
    }

    selectedDate = dateKey(currentYear, currentMonthIndex, 1);
    await refreshAll();
  });

  $("#startBtn").addEventListener("click", startLog);
  $("#stopBtn").addEventListener("click", stopLog);

  await refreshAll();
}

async function refreshAll() {
  try {
    setMessage("");

    const [monthData, currentData] = await Promise.all([
      api(`/logs/month?year=${currentYear}&month=${currentMonthIndex + 1}`),
      api("/logs/current"),
    ]);

    monthLogs = monthData.logs || [];
    currentLog = currentData.current_log;

    renderStatus();
    renderCalendar();
    await renderSelectedDay();
  } catch (error) {
    setMessage(error.message);

    if (error.message.includes("비밀번호") || error.message.includes("401")) {
      clearPassword();
    }
  }
}

function renderStatus() {
  const runningStatus = $("#runningStatus");
  const runningDetail = $("#runningDetail");
  const startBtn = $("#startBtn");
  const stopBtn = $("#stopBtn");

  if (currentLog) {
    runningStatus.textContent = "작업 기록 중";
    runningDetail.textContent = `시작: ${formatDateTime(currentLog.start_time)} / 작업일: ${currentLog.work_date}`;
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } else {
    runningStatus.textContent = "대기 중";
    runningDetail.textContent = "진행 중인 작업 로그가 없습니다.";
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }
}

function renderCalendar() {
  const grid = $("#calendarGrid");
  const monthTitle = $("#monthTitle");

  grid.innerHTML = "";

  monthTitle.textContent = `${currentYear}년 ${currentMonthIndex + 1}월`;

  const first = new Date(currentYear, currentMonthIndex, 1);
  const firstDay = first.getDay();
  const lastDate = new Date(currentYear, currentMonthIndex + 1, 0).getDate();

  const logsByDate = new Map();

  for (const log of monthLogs) {
    const key = log.work_date;

    if (!logsByDate.has(key)) {
      logsByDate.set(key, []);
    }

    logsByDate.get(key).push(log);
  }

  for (let i = 0; i < firstDay; i++) {
    const empty = document.createElement("button");
    empty.className = "day-cell empty";
    empty.type = "button";
    empty.disabled = true;
    grid.appendChild(empty);
  }

  for (let day = 1; day <= lastDate; day++) {
    const key = dateKey(currentYear, currentMonthIndex, day);
    const logs = logsByDate.get(key) || [];
    const total = logs.reduce((sum, log) => {
      return sum + Number(log.duration_seconds || 0);
    }, 0);

    const hasRunning =
      logs.some((log) => log.status === "RUNNING") ||
      currentLog?.work_date === key;

    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "day-cell";

    if (key === todayKey()) {
      cell.classList.add("today");
    }

    if (key === selectedDate) {
      cell.classList.add("selected");
    }

    cell.innerHTML = `
      <span class="day-number">${day}</span>
      <span class="day-meta">
        ${total ? `<span>${formatDuration(total)}</span>` : "<span>기록 없음</span>"}
        ${hasRunning ? `<span class="running-chip">RUNNING</span>` : ""}
      </span>
    `;

    cell.addEventListener("click", async () => {
      selectedDate = key;
      renderCalendar();
      await renderSelectedDay();
    });

    grid.appendChild(cell);
  }
}

async function renderSelectedDay() {
  const title = $("#selectedDateTitle");
  const total = $("#dayTotal");
  const list = $("#dayLogs");

  title.textContent = selectedDate;
  list.innerHTML = "불러오는 중...";

  try {
    const data = await api(`/logs/day?work_date=${selectedDate}`);
    const logs = data.logs || [];

    const totalSeconds = logs.reduce((sum, log) => {
      return sum + Number(log.duration_seconds || 0);
    }, 0);

    total.textContent = `합계 ${formatDuration(totalSeconds)}`;

    if (logs.length === 0) {
      list.innerHTML = `<p class="muted">해당 날짜의 기록이 없습니다.</p>`;
      return;
    }

    list.innerHTML = logs.map((log) => {
      const statusClass =
        log.status === "RUNNING"
          ? "running"
          : log.status === "AUTO_STOPPED"
            ? "auto"
            : "completed";

      const endText = log.end_time ? formatTime(log.end_time) : "진행 중";

      const durationText = log.duration_seconds
        ? formatDuration(log.duration_seconds)
        : "계산 전";

      return `
        <article class="log-item">
          <div>
            <div class="log-time">${formatTime(log.start_time)} ~ ${endText}</div>
            <div class="log-duration">${durationText}</div>
          </div>
          <span class="status-chip ${statusClass}">${log.status}</span>
        </article>
      `;
    }).join("");
  } catch (error) {
    list.innerHTML = `<p class="message">${error.message}</p>`;
  }
}

async function startLog() {
  try {
    setMessage("");

    await api("/logs/start", {
      method: "POST",
      body: JSON.stringify({
        work_date: selectedDate,
      }),
    });

    await refreshAll();
  } catch (error) {
    setMessage(error.message);
  }
}

async function stopLog() {
  try {
    setMessage("");

    await api("/logs/stop", {
      method: "POST",
    });

    await refreshAll();
  } catch (error) {
    setMessage(error.message);
  }
}

setupLoginPage();
setupCalendarPage();