import { API_BASE_URL } from "./api";

function normalizeWsBaseUrl() {
  const explicit = import.meta.env.VITE_WS_BASE_URL;
  if (explicit) {
    return explicit.replace(/\/$/, "");
  }

  const apiUrl = new URL(API_BASE_URL);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = "";
  apiUrl.search = "";
  apiUrl.hash = "";
  return apiUrl.toString().replace(/\/$/, "");
}

export function connectTerminal(profile, handlers = {}) {
  const {
    onOpen,
    onClose,
    onError,
    onBinary,
    onJson,
    onText,
  } = handlers;

  const base = normalizeWsBaseUrl();
  const url = `${base}/ws/terminal?profile=${encodeURIComponent(profile)}`;
  const socket = new WebSocket(url);
  socket.binaryType = "arraybuffer";

  socket.addEventListener("open", () => {
    if (typeof onOpen === "function") {
      onOpen();
    }
  });

  socket.addEventListener("close", (event) => {
    if (typeof onClose === "function") {
      onClose(event);
    }
  });

  socket.addEventListener("error", (event) => {
    if (typeof onError === "function") {
      onError(event);
    }
  });

  socket.addEventListener("message", (event) => {
    const payload = event.data;

    if (typeof payload === "string") {
      try {
        const parsed = JSON.parse(payload);
        if (typeof onJson === "function") {
          onJson(parsed);
        }
      } catch {
        if (typeof onText === "function") {
          onText(payload);
        }
      }
      return;
    }

    if (payload instanceof ArrayBuffer) {
      if (typeof onBinary === "function") {
        onBinary(new Uint8Array(payload));
      }
    }
  });

  return {
    socket,
    sendBinary(input) {
      if (socket.readyState !== WebSocket.OPEN) {
        return false;
      }

      socket.send(input);
      return true;
    },
    sendControl(message) {
      if (socket.readyState !== WebSocket.OPEN) {
        return false;
      }

      socket.send(JSON.stringify(message));
      return true;
    },
    disconnect(code = 1000, reason = "client_disconnect") {
      if (socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        return;
      }

      socket.close(code, reason);
    },
  };
}
