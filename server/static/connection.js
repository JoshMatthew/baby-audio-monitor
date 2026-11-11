// Keeps a listening connection to the server alive, reconnecting after drops and sleep.
const WRONG_PASSWORD_CODE = 4001;
const CHECK_INTERVAL_MS = 2000;
const STALE_AFTER_MS = 15000;
const FIRST_RETRY_MS = 1000;
const MAX_RETRY_MS = 10000;

export class Connection {
  constructor(password, { onStatus, onAudio }) {
    this.password = password;
    this.onStatus = onStatus;
    this.onAudio = onAudio;
    this.retryDelay = FIRST_RETRY_MS;
  }

  start() {
    this.connect();
    this.healthTimer = setInterval(() => this.checkHealth(), CHECK_INTERVAL_MS);
  }

  stop() {
    clearInterval(this.healthTimer);
    clearTimeout(this.retryTimer);
    this.closeSocket();
  }

  connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${scheme}://${location.host}/listen`);
    socket.binaryType = "arraybuffer";
    socket.onopen = () =>
      socket.send(JSON.stringify({ password: this.password }));
    socket.onmessage = (event) => this.receive(event.data);
    socket.onclose = (event) => this.handleClose(event.code);

    this.socket = socket;
    this.lastMessageAt = Date.now();
    this.onStatus("connecting");
  }

  receive(data) {
    this.lastMessageAt = Date.now();
    this.retryDelay = FIRST_RETRY_MS;

    if (typeof data === "string") {
      this.onStatus(JSON.parse(data).transmitter ? "live" : "offline");
    } else {
      this.onAudio(new Uint8Array(data));
    }
  }

  handleClose(code) {
    if (code === WRONG_PASSWORD_CODE) {
      this.stop();
      this.onStatus("wrong-password");
      return;
    }

    this.onStatus("reconnecting");
    this.retryTimer = setTimeout(() => this.connect(), this.retryDelay);
    this.retryDelay = Math.min(this.retryDelay * 2, MAX_RETRY_MS);
  }

  // The server sends something every few seconds, so a long silence means the connection
  // died without telling us, which is what happens when the laptop sleeps.
  checkHealth() {
    const waitingToRetry = this.socket.readyState === WebSocket.CLOSED;
    const silentFor = Date.now() - this.lastMessageAt;

    if (!waitingToRetry && silentFor > STALE_AFTER_MS) this.reconnectNow();
  }

  reconnectNow() {
    clearTimeout(this.retryTimer);
    this.closeSocket();
    this.connect();
  }

  closeSocket() {
    this.socket.onclose = null;
    this.socket.onmessage = null;
    this.socket.close();
  }
}
