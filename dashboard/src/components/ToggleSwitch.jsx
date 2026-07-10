import { motion } from "framer-motion";

export default function ToggleSwitch({ checked = false, onChange, label, disabled = false }) {
  return (
    <label
      className={`flex items-center justify-between gap-3 ${disabled ? "opacity-50" : "cursor-pointer"}`}
    >
      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange?.(!checked)}
        className="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200"
        style={{
          background: checked ? "var(--accent-cyan)" : "var(--bg-elevated)",
          border: `1px solid ${checked ? "var(--border-glow-cyan)" : "var(--border-subtle)"}`,
        }}
      >
        <motion.div
          className="h-4 w-4 rounded-full"
          style={{ background: checked ? "var(--text-primary)" : "var(--text-dim)" }}
          animate={{ x: checked ? 22 : 3 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </button>
    </label>
  );
}
