import { Connection } from "./connection.js";
import { Player } from "./player.js";

const PASSWORD_KEY = "baby-monitor-password";
const STATUS_TEXT = {
  stopped: "Not listening",
  connecting: "Connecting…",
  live: "Listening",
  offline: "The baby Mac is offline",
  reconnecting: "Connection lost, reconnecting…",
  "wrong-password": "Wrong password",
};

const statusText = document.getElementById("status");
const level = document.getElementById("level");
const login = document.getElementById("login");
const passwordInput = document.getElementById("password");
const controls = document.getElementById("controls");
const volume = document.getElementById("volume");
const stopButton = document.getElementById("stop");

let player;
let connection;

function savedPassword() {
  try {
    return localStorage.getItem(PASSWORD_KEY) ?? "";
  } catch {
    return "";
  }
}

function savePassword(password) {
  try {
    localStorage.setItem(PASSWORD_KEY, password);
  } catch {
    // Without storage the password is simply asked again next time.
  }
}

function showStatus(state) {
  statusText.textContent = STATUS_TEXT[state];
  statusText.dataset.state = state;
}

function handleStatus(state) {
  showStatus(state);

  if (state === "wrong-password") {
    savePassword("");
    stopListening();
  }
}

function playAudio(bytes) {
  const peak = player.play(bytes);

  level.style.transform = `scaleX(${Math.min(1, Math.sqrt(peak))})`;
}

function startListening(password) {
  player = new Player();
  player.setVolume(volume.valueAsNumber);

  connection = new Connection(password, {
    onStatus: handleStatus,
    onAudio: playAudio,
  });
  connection.start();

  login.hidden = true;
  controls.hidden = false;
}

function stopListening() {
  connection.stop();
  player.close();

  level.style.transform = "scaleX(0)";
  login.hidden = false;
  controls.hidden = true;
}

login.addEventListener("submit", (event) => {
  event.preventDefault();

  savePassword(passwordInput.value);
  startListening(passwordInput.value);
});

stopButton.addEventListener("click", () => {
  stopListening();
  showStatus("stopped");
});

volume.addEventListener("input", () => player.setVolume(volume.valueAsNumber));

passwordInput.value = savedPassword();
