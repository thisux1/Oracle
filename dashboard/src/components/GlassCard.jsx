export default function GlassCard({
  title,
  subtitle,
  glow = false,
  className = "",
  headerRight = null,
  children,
}) {
  const base = glow ? "glass-glow" : "glass";

  return (
    <section
      className={`${base} rounded-2xl p-4 transition-all duration-200 md:p-5 ${className}`}
    >
      {title ? (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h3
              className="text-sm font-semibold tracking-wide"
              style={{ color: glow ? "var(--accent-cyan)" : "var(--text-primary)" }}
            >
              {title}
            </h3>
            {subtitle ? (
              <p className="mt-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                {subtitle}
              </p>
            ) : null}
          </div>
          {headerRight ? <div className="shrink-0">{headerRight}</div> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}
