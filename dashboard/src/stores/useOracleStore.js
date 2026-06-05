import { create } from "zustand";
import {
  ApiClientError,
  apiGetConfig,
  apiGetStatus,
  apiListProfiles,
  apiSaveConfig,
  apiStartBot,
  apiStopBot,
  apiGetStats,
  apiGetLogs,
} from "../lib/api";

const DEFAULT_PROFILE = "options.ini";

function createEmptySessionStats() {
  return {
    commands: {
      hunt: 0,
      adventure: 0,
      farm: 0,
      training: 0,
      work: 0,
      quest: 0,
      daily: 0,
      weekly: 0,
      lootbox: 0,
    },
    progress: {
      coins: 0,
      xp: 0,
      levels: 0,
    },
    loot: {
      mob_drops: {},
      lootbox_drops: {},
      work_drops: {},
      farm_drops: {},
    },
    misc: {
      cards: {},
      coolness: 0,
      arena_cookies: 0,
    },
  };
}

function normalizeProfilesPayload(payload) {
  let raw = [];
  if (Array.isArray(payload)) {
    raw = payload;
  } else if (Array.isArray(payload?.profiles)) {
    raw = payload.profiles;
  }

  return raw.map((item) => {
    if (typeof item === "string") {
      return { name: item, state: "offline", is_incomplete: false };
    }
    return {
      name: item.name || "",
      state: item.state || "offline",
      is_incomplete: !!item.is_incomplete,
    };
  }).filter(p => p.name.endsWith(".ini"));
}

export const useOracleStore = create((set, get) => ({
  profiles: [{ name: DEFAULT_PROFILE, state: "offline", is_incomplete: false }],
  activeProfile: DEFAULT_PROFILE,

  botState: "offline",
  uptime: 0,
  lastCommand: "",
  hpqSize: 0,
  lpqSize: 0,
  lastExitCode: null,
  lastCrashAt: null,

  config: {},
  configDirty: false,

  sessionStats: createEmptySessionStats(),
  totalStats: createEmptySessionStats(),

  terminalConnected: false,
  terminalConnection: null,
  terminalLines: [],
  binaryHistory: [],
  lastBinaryChunk: null,
  heartbeatInterval: null,
  reconnectTimeout: null,

  loadingProfiles: false,
  loadingConfig: false,
  loadingStatus: false,
  savingConfig: false,
  botActionPending: false,
  lastError: null,

  setActiveProfile: (name) => {
    const nextProfile = typeof name === "string" && name.trim() ? name.trim() : DEFAULT_PROFILE;
    set({ activeProfile: nextProfile, configDirty: false, lastError: null });
  },

  setConfigField: (key, value) => {
    set((state) => ({
      config: {
        ...state.config,
        [key]: value,
      },
      configDirty: true,
    }));
  },

  connectTerminal: (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    
    // Clean up existing connection if any
    get().disconnectTerminal();
    
    // Clear terminal history on new connection
    set({ terminalLines: [], binaryHistory: [], lastBinaryChunk: null });

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const defaultWsUrl = import.meta.env.DEV 
      ? "ws://127.0.0.1:8000" 
      : `${wsProtocol}//${window.location.host}`;
    const wsUrl = `${import.meta.env.VITE_WS_URL || defaultWsUrl}/ws/terminal?profile=${targetProfile}`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    // Set connection state
    set({ terminalConnection: ws, terminalConnected: false });

    ws.onopen = () => {
      set({ terminalConnected: true });
      
      // Start heartbeat
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "heartbeat" }));
        }
      }, 30000);
      set({ heartbeatInterval: interval });
    };

    ws.onmessage = (event) => {
      // 1. Handle binary process output
      if (event.data instanceof ArrayBuffer) {
        const chunk = new Uint8Array(event.data);
        
        // Save binary history (keep last 200 chunks for terminal view replay)
        set((state) => {
          const history = [...state.binaryHistory, chunk];
          if (history.length > 200) history.shift();
          return {
            binaryHistory: history,
            lastBinaryChunk: chunk
          };
        });
      }
      // 2. Handle control status JSON frames
      else if (typeof event.data === "string") {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "pong") {
            return;
          }
          if (payload.type === "status" || payload.state) {
            set({
              botState: payload.state || get().botState,
              uptime: typeof payload.uptime === "number" ? payload.uptime : get().uptime,
              hpqSize: typeof payload.hpq === "number" ? payload.hpq : get().hpqSize,
              lpqSize: typeof payload.lpq === "number" ? payload.lpq : get().lpqSize,
            });
            get().fetchProfiles();
          }
        } catch (e) {
          console.error("Error parsing websocket JSON message", e);
        }
      }
    };

    ws.onclose = () => {
      set({ terminalConnected: false, terminalConnection: null });
      
      // Auto-reconnect after 3s if not manually disconnected
      if (get().activeProfile === targetProfile) {
        const timeout = setTimeout(() => {
          if (get().activeProfile === targetProfile) {
            get().connectTerminal(targetProfile);
          }
        }, 3000);
        set({ reconnectTimeout: timeout });
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  },

  disconnectTerminal: () => {
    const ws = get().terminalConnection;
    const interval = get().heartbeatInterval;
    const timeout = get().reconnectTimeout;

    if (interval) clearInterval(interval);
    if (timeout) clearTimeout(timeout);
    if (ws) {
      ws.onclose = null;
      ws.close();
    }

    set({
      terminalConnection: null,
      terminalConnected: false,
      heartbeatInterval: null,
      reconnectTimeout: null,
    });
  },

  sendTerminalBinary: (data) => {
    const ws = get().terminalConnection;
    if (ws && ws.readyState === WebSocket.OPEN) {
      const encoder = new TextEncoder();
      const binary = encoder.encode(data);
      ws.send(binary);
    }
  },

  resizeTerminal: (cols, rows) => {
    const ws = get().terminalConnection;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "resize", cols, rows }));
    }
  },

  fetchStats: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    try {
      const rawStats = await apiGetStats(targetProfile, "session");
      set({
        sessionStats: {
          commands: rawStats.command_data || {},
          progress: rawStats.progress_data || {},
          loot: rawStats.loot_data || { mob_drops: {}, lootbox_drops: {}, work_drops: {}, farm_drops: {} },
          misc: rawStats.misc || {},
        },
      });
      return rawStats;
    } catch (error) {
      throw error;
    }
  },

  fetchTotalStats: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    try {
      const rawStats = await apiGetStats(targetProfile, "total");
      set({
        totalStats: {
          commands: rawStats.command_data || {},
          progress: rawStats.progress_data || {},
          loot: rawStats.loot_data || { mob_drops: {}, lootbox_drops: {}, work_drops: {}, farm_drops: {} },
          misc: rawStats.misc || {},
        },
      });
      return rawStats;
    } catch (error) {
      throw error;
    }
  },

  fetchProfiles: async () => {
    set({ loadingProfiles: true, lastError: null });
    const currentProfile = get().activeProfile || DEFAULT_PROFILE;

    try {
      const payload = await apiListProfiles();
      const loadedProfiles = normalizeProfilesPayload(payload);
      const profiles = loadedProfiles.length > 0 ? loadedProfiles : [{ name: DEFAULT_PROFILE, state: "offline", is_incomplete: false }];
      const profileNames = profiles.map(p => p.name);
      const nextActive = profileNames.includes(currentProfile) ? currentProfile : profileNames[0];
      set({ profiles, activeProfile: nextActive, loadingProfiles: false });
      return profiles;
    } catch (error) {
      const fallbackObj = { name: currentProfile, state: "offline", is_incomplete: false };
      if (error instanceof ApiClientError && error.status === 404) {
        set({
          profiles: [fallbackObj],
          activeProfile: currentProfile,
          loadingProfiles: false,
          lastError: null,
        });
        return [fallbackObj];
      }

      set({
        profiles: [fallbackObj],
        activeProfile: currentProfile,
        loadingProfiles: false,
        lastError: error,
      });
      return [fallbackObj];
    }
  },

  fetchConfig: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    set({ loadingConfig: true, lastError: null });

    try {
      const payload = await apiGetConfig(targetProfile);
      set({
        activeProfile: payload.profile || targetProfile,
        config: payload.config || {},
        configDirty: false,
        loadingConfig: false,
      });
      return payload;
    } catch (error) {
      set({ loadingConfig: false, lastError: error });
      throw error;
    }
  },

  saveConfig: async (updates = {}, profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    const currentConfig = get().config || {};
    const settings = {
      ...currentConfig,
      ...(updates || {}),
    };

    set({ savingConfig: true, lastError: null });

    try {
      const payload = await apiSaveConfig(targetProfile, settings);
      set({ config: settings, configDirty: false, savingConfig: false });
      get().fetchProfiles();
      return payload;
    } catch (error) {
      set({ savingConfig: false, lastError: error });
      throw error;
    }
  },

  fetchStatus: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    set({ loadingStatus: true, lastError: null });

    try {
      const status = await apiGetStatus(targetProfile);
      set({
        botState: status.state || "offline",
        uptime: Number(status.uptime || 0),
        hpqSize: Number(status.hpq || 0),
        lpqSize: Number(status.lpq || 0),
        lastExitCode: status.lastExitCode ?? null,
        lastCrashAt: status.lastCrashAt ?? null,
        loadingStatus: false,
      });
      get().fetchProfiles().catch(() => undefined);
      return status;
    } catch (error) {
      set({ loadingStatus: false, lastError: error });
      throw error;
    }
  },

  fetchLogs: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    try {
      const data = await apiGetLogs(targetProfile, 50);
      set({ terminalLines: data.lines || [] });
      return data;
    } catch (error) {
      console.error("Failed to fetch logs:", error);
    }
  },

  startBot: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    set({ botActionPending: true, lastError: null, botState: "starting" });

    try {
      const payload = await apiStartBot(targetProfile);
      await get().fetchStatus(targetProfile);
      await get().fetchLogs(targetProfile);
      await get().fetchProfiles();
      set({ botActionPending: false });
      return payload;
    } catch (error) {
      set({ botActionPending: false, botState: "offline", lastError: error });
      throw error;
    }
  },

  stopBot: async (profile) => {
    const targetProfile = profile || get().activeProfile || DEFAULT_PROFILE;
    set({ botActionPending: true, lastError: null, botState: "stopping" });

    try {
      const payload = await apiStopBot(targetProfile);
      await get().fetchStatus(targetProfile);
      await get().fetchProfiles();
      set({ botActionPending: false });
      return payload;
    } catch (error) {
      set({ botActionPending: false, lastError: error });
      throw error;
    }
  },
}));

export { DEFAULT_PROFILE };
