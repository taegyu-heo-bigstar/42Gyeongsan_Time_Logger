const API_BASE = "https://42-gyeongsan-time-logger.vercel.app";
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

  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
  } catch (error) {
    throw new Error(`${API_BASE}${path} 요청 실패`);
  }

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

function toDateKey(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function dateKey(year, monthIndex, day) {
  return `${year}-${pad2(monthIndex + 1)}-${pad2(day)}`;
}

function todayKey() {
  return toDateKey(new Date());
}

function formatDateKorean(dateString) {
  const d = new Date(`${dateString}T00:00:00`);
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}

function formatTime(value) {
  if (!value) return "-";

  return new Date(value).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatDuration(seconds) {
  seconds = Number(seconds || 0);

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  return `${h}시간 ${m}분 ${s}초`;
}

function formatDurationShort(seconds) {
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

/* login page */
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

/* calendar page */
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
  // API가 실패하더라도 월/날짜 UI는 먼저 그린다.
  renderHeader();
  renderStatus();
  renderCalendar();
  renderMonthTotal(0);

  try {
    setMessage("");

    const [monthData, currentData] = await Promise.all([
      api(`/logs/month?year=${currentYear}&month=${currentMonthIndex + 1}`),
      api("/logs/current"),
    ]);

    monthLogs = monthData.logs || [];
    currentLog = currentData.current_log;

    renderHeader();
    renderStatus();
    renderCalendar();
    renderMonthTotal(monthData.total_duration_seconds || 0);
  } catch (error) {
    renderHeader();
    renderStatus();
    renderCalendar();

    setMessage(`백엔드 연결 실패: ${error.message}`);

    if (error.message.includes("비밀번호") || error.message.includes("401")) {
      clearPassword();
    }
  }
}

function renderHeader() {
  const monthTitle = $("#monthTitle");
  const prevMonthLabel = $("#prevMonthLabel");
  const nextMonthLabel = $("#nextMonthLabel");
  const selectedDateTitle = $("#selectedDateTitle");

  monthTitle.textContent = `${currentMonthIndex + 1}월`;

  const prev = new Date(currentYear, currentMonthIndex - 1, 1);
  const next = new Date(currentYear, currentMonthIndex + 1, 1);

  prevMonthLabel.textContent = `${prev.getMonth() + 1}월`;
  nextMonthLabel.textContent = `${next.getMonth() + 1}월`;
  selectedDateTitle.textContent = formatDateKorean(selectedDate);
}

function renderStatus() {
  const runningStatus = $("#runningStatus");
  const startBtn = $("#startBtn");
  const stopBtn = $("#stopBtn");

  if (currentLog) {
    runningStatus.textContent = `진행 중: ${currentLog.work_date} ${formatTime(currentLog.start_time)} 시작`;
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } else {
    runningStatus.textContent = "현재 진행 중인 로그가 없습니다.";
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }
}

function renderMonthTotal(totalSeconds) {
  $("#monthTotal").textContent = `합계 시간 : ${formatDuration(totalSeconds)}`;
}

function groupLogsByDate() {
  const map = new Map();

  for (const log of monthLogs) {
    if (!map.has(log.work_date)) {
      map.set(log.work_date, []);
    }

    map.get(log.work_date).push(log);
  }

  return map;
}

function renderCalendar() {
  const grid = $("#calendarGrid");
  const logsByDate = groupLogsByDate();

  grid.innerHTML = "";

  const firstDate = new Date(currentYear, currentMonthIndex, 1);
  const firstDayIndex = firstDate.getDay();
  const lastDate = new Date(currentYear, currentMonthIndex + 1, 0).getDate();

  const prevMonthLastDate = new Date(currentYear, currentMonthIndex, 0).getDate();

  for (let i = firstDayIndex - 1; i >= 0; i--) {
    const day = prevMonthLastDate - i;
    const cell = makeDayCell({
      day,
      key: null,
      logs: [],
      otherMonth: true,
      dayIndex: null,
    });
    grid.appendChild(cell);
  }

  for (let day = 1; day <= lastDate; day++) {
    const key = dateKey(currentYear, currentMonthIndex, day);
    const dayIndex = new Date(currentYear, currentMonthIndex, day).getDay();
    const logs = logsByDate.get(key) || [];

    const cell = makeDayCell({
      day,
      key,
      logs,
      otherMonth: false,
      dayIndex,
    });

    grid.appendChild(cell);
  }

  const currentCells = grid.children.length;
  const remaining = currentCells <= 35 ? 35 - currentCells : 42 - currentCells;

  for (let day = 1; day <= remaining; day++) {
    const cell = makeDayCell({
      day,
      key: null,
      logs: [],
      otherMonth: true,
      dayIndex: null,
    });
    grid.appendChild(cell);
  }
}

function makeDayCell({ day, key, logs, otherMonth, dayIndex }) {
  const cell = document.createElement("button");
  cell.type = "button";
  cell.className = "day-cell";

  if (otherMonth) {
    cell.classList.add("empty", "other-month");
  }

  if (!otherMonth && key === selectedDate) {
    cell.classList.add("selected");
  }

  if (!otherMonth && key === todayKey()) {
    cell.classList.add("today");
  }

  if (!otherMonth && dayIndex === 0) {
    cell.classList.add("sunday");
  }

  if (!otherMonth && dayIndex === 6) {
    cell.classList.add("saturday");
  }

  const logRows = makeLogRows(logs, key);

  cell.innerHTML = `
    <span class="day-number">${day}</span>
    <div class="log-stack">${logRows}</div>
  `;

  if (!otherMonth) {
    cell.addEventListener("click", () => {
      selectedDate = key;
      renderHeader();
      renderCalendar();
    });
  } else {
    cell.disabled = true;
  }

  return cell;
}

function makeLogRows(logs, key) {
  const allLogs = [...logs];

  if (
    currentLog &&
    currentLog.work_date === key &&
    !allLogs.some((log) => log.id === currentLog.id)
  ) {
    allLogs.push(currentLog);
  }

  if (allLogs.length === 0) {
    return "";
  }

  const visibleLogs = allLogs.slice(0, 3);
  const hiddenCount = allLogs.length - visibleLogs.length;

  const rows = visibleLogs.map((log) => {
    const statusClass =
      log.status === "RUNNING"
        ? "running"
        : log.status === "AUTO_STOPPED"
          ? "auto"
          : "completed";

    const text =
      log.status === "RUNNING"
        ? `${formatTime(log.start_time)} ~ 진행 중`
        : `${formatTime(log.start_time)} · ${formatDurationShort(log.duration_seconds)}`;

    return `<span class="log-row ${statusClass}" title="${text}">${text}</span>`;
  });

  if (hiddenCount > 0) {
    rows.push(`<span class="more-log">+${hiddenCount}개 더</span>`);
  }

  return rows.join("");
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
