import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

export default function ConfigSection({ title, icon, requiresRestart = false, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div
      className="glass overflow-hidden rounded-2xl"
      style={{ border: "1px solid var(--border-subtle)" }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-[rgba(148,163,184,0.05)]"
      >
        {icon ? <span className="text-base">{icon}</span> : null}
        <span className="flex-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </span>
        {requiresRestart ? (
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{
              background: "var(--accent-warning-dim)",
              color: "var(--accent-warning)",
              border: "1px solid var(--border-glow-warning)",
            }}
          >
            restart
          </span>
        ) : null}
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ color: "var(--text-dim)" }}
        >
          <ChevronDown size={16} />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div
              className="space-y-4 border-t px-4 py-4"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              {children}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
