import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Terminal,
  Settings,
  BarChart3,
} from "lucide-react";

const TABS = [
  { key: "overview", label: "Visão Geral", Icon: LayoutDashboard },
  { key: "terminal", label: "Terminal", Icon: Terminal },
  { key: "config", label: "Configurações", Icon: Settings },
  { key: "stats", label: "Estatísticas", Icon: BarChart3 },
];

export default function TabNav({ activeTab, onTabChange }) {
  return (
    <nav
      className="glass flex items-center gap-1 rounded-2xl p-1.5"
      role="tablist"
    >
      {TABS.map(({ key, label, Icon }) => {
        const isActive = key === activeTab;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onTabChange(key)}
            className="relative flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150"
            style={{
              color: isActive ? "var(--accent-primary)" : "var(--text-secondary)",
            }}
          >
            {isActive ? (
              <motion.div
                layoutId="tab-indicator"
                className="absolute inset-0 rounded-xl"
                style={{
                  background: "var(--accent-primary-dim)",
                  border: "1px solid rgba(167, 139, 250, 0.3)",
                }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            ) : null}
            <span className="relative z-10 flex items-center gap-2">
              <Icon size={16} />
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
