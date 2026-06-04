import { useCallback, useEffect, useRef, useState } from "react";
import { useOracleStore } from "../stores/useOracleStore";
import StatusBadge from "./StatusBadge";
import { apiCreateProfile, apiDeleteProfile, apiExportProfile, apiImportProfile } from "../lib/api";
import { Plus, Copy, Trash2, Download, Upload, MoreVertical } from "lucide-react";

function ProfileMenu({ profile, isDefault, onAction, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute right-0 top-full z-50 mt-1 w-44 overflow-hidden rounded-xl py-1"
      style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
    >
      <button
        type="button"
        onClick={() => { onAction("duplicate"); onClose(); }}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-[rgba(148,163,184,0.08)]"
        style={{ color: "var(--text-secondary)" }}
      >
        <Copy size={13} /> Duplicate
      </button>
      <button
        type="button"
        onClick={() => { onAction("export"); onClose(); }}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-[rgba(148,163,184,0.08)]"
        style={{ color: "var(--text-secondary)" }}
      >
        <Download size={13} /> Export
      </button>
      {!isDefault ? (
        <button
          type="button"
          onClick={() => { onAction("delete"); onClose(); }}
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-[rgba(248,113,113,0.1)]"
          style={{ color: "var(--accent-danger)" }}
        >
          <Trash2 size={13} /> Delete
        </button>
      ) : null}
    </div>
  );
}

function CreateProfileDialog({ onConfirm, onClose }) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name is required");
      return;
    }
    if (/[\\/]/.test(trimmed)) {
      setError("Invalid characters in name");
      return;
    }
    onConfirm(trimmed);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm rounded-2xl p-5" style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>New Profile</h3>
        <form onSubmit={handleSubmit}>
          <input
            autoFocus
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(""); }}
            placeholder="my_profile"
            className="input mb-2"
          />
          {error ? <p className="mb-2 text-xs" style={{ color: "var(--accent-danger)" }}>{error}</p> : null}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="btn btn-ghost text-xs">Cancel</button>
            <button type="submit" className="btn btn-primary text-xs">Create</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ProfileSidebar({ open, onClose }) {
  const profiles = useOracleStore((s) => s.profiles);
  const activeProfile = useOracleStore((s) => s.activeProfile);
  const botState = useOracleStore((s) => s.botState);
  const setActiveProfile = useOracleStore((s) => s.setActiveProfile);
  const fetchProfiles = useOracleStore((s) => s.fetchProfiles);

  const [menuProfile, setMenuProfile] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [importInput, setImportInput] = useState(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleSelect = useCallback((profile) => {
    setActiveProfile(profile);
    onClose();
  }, [setActiveProfile, onClose]);

  const handleAction = useCallback(async (action, profile) => {
    switch (action) {
      case "duplicate": {
        const baseName = profile.replace(/\.ini$/i, "");
        const newName = `${baseName}_copy`;
        try {
          await apiCreateProfile(newName, profile);
          await fetchProfiles();
        } catch (err) {
          alert(err?.message || "Failed to duplicate profile");
        }
        break;
      }
      case "export": {
        try {
          await apiExportProfile(profile);
        } catch (err) {
          alert(err?.message || "Failed to export profile");
        }
        break;
      }
      case "delete": {
        if (!confirm(`Delete "${profile}"? This cannot be undone.`)) break;
        try {
          await apiDeleteProfile(profile);
          if (profile === activeProfile) {
            setActiveProfile("options.ini");
          }
          await fetchProfiles();
        } catch (err) {
          alert(err?.message || "Failed to delete profile");
        }
        break;
      }
    }
  }, [activeProfile, fetchProfiles, setActiveProfile]);

  const handleCreate = useCallback(async (name) => {
    try {
      await apiCreateProfile(name);
      await fetchProfiles();
      setShowCreate(false);
    } catch (err) {
      alert(err?.message || "Failed to create profile");
    }
  }, [fetchProfiles]);

  const handleImport = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await apiImportProfile(file);
      await fetchProfiles();
    } catch (err) {
      alert(err?.message || "Failed to import profile");
    }
    e.target.value = "";
  }, [fetchProfiles]);

  const sidebar = (
    <aside
      className="flex h-full w-[260px] flex-col glass-heavy"
      style={{ borderRight: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center justify-between px-4 pt-5 pb-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--accent-cyan)" }}>
            Oracle OS
          </p>
          <p className="mt-0.5 text-[10px]" style={{ color: "var(--text-dim)" }}>v3.0</p>
        </div>
        <button type="button" onClick={() => fetchProfiles()} className="btn btn-ghost px-2 py-1 text-[11px]" title="Reload">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
            <path d="M16 16h5v5" />
          </svg>
        </button>
      </div>

      <div className="px-3 pb-2">
        <div className="mb-2 flex items-center justify-between">
          <p className="px-1 text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)" }}>
            Profiles
          </p>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="rounded-lg p-1 transition-colors hover:bg-[rgba(148,163,184,0.1)]"
              style={{ color: "var(--text-dim)" }}
              title="New profile"
            >
              <Plus size={13} />
            </button>
            <label
              className="cursor-pointer rounded-lg p-1 transition-colors hover:bg-[rgba(148,163,184,0.1)]"
              style={{ color: "var(--text-dim)" }}
              title="Import .ini"
            >
              <Upload size={13} />
              <input type="file" accept=".ini" className="hidden" onChange={handleImport} />
            </label>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {profiles.map((profile) => {
          const isActive = profile === activeProfile;
          const profileName = profile.replace(/\.ini$/i, "");
          const isDefault = profile === "options.ini";
          return (
            <div key={profile} className="relative">
              <button
                type="button"
                onClick={() => handleSelect(profile)}
                className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-150 ${isActive ? "glow-cyan" : ""}`}
                style={{
                  background: isActive ? "var(--accent-cyan-dim)" : "transparent",
                  color: isActive ? "var(--accent-cyan)" : "var(--text-secondary)",
                  border: `1px solid ${isActive ? "var(--border-glow-cyan)" : "transparent"}`,
                }}
              >
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${isActive && botState === "online" ? "animate-oracle-pulse" : ""}`}
                  style={{
                    background: isActive && botState === "online" ? "var(--accent-success)" : isActive ? "var(--accent-cyan)" : "var(--text-dim)",
                  }}
                />
                <span className="flex-1 truncate font-medium">{profileName}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuProfile(menuProfile === profile ? null : profile);
                  }}
                  className="shrink-0 rounded-lg p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-[rgba(148,163,184,0.1)]"
                  style={{ color: "var(--text-dim)" }}
                >
                  <MoreVertical size={13} />
                </button>
              </button>
              {menuProfile === profile ? (
                <ProfileMenu
                  profile={profile}
                  isDefault={isDefault}
                  onAction={(action) => handleAction(action, profile)}
                  onClose={() => setMenuProfile(null)}
                />
              ) : null}
            </div>
          );
        })}
      </nav>

      <div className="mt-auto border-t px-4 py-3" style={{ borderColor: "var(--border-subtle)" }}>
        <StatusBadge state={botState} size="xs" />
      </div>
    </aside>
  );

  return (
    <>
      <div className="hidden md:fixed md:inset-y-0 md:left-0 md:z-30 md:flex">{sidebar}</div>
      {open ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
          <div className="relative z-50 h-full">{sidebar}</div>
        </div>
      ) : null}
      {showCreate ? <CreateProfileDialog onConfirm={handleCreate} onClose={() => setShowCreate(false)} /> : null}
    </>
  );
}
