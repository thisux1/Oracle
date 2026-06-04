export default function SectionCard({ title, subtitle, children }) {
  return (
    <section className="rounded-2xl border border-cyan-300/20 bg-slate-950/45 p-4 backdrop-blur-xl md:p-5">
      <header className="mb-3">
        <h3 className="text-sm font-semibold tracking-wide text-cyan-100">{title}</h3>
        {subtitle ? <p className="mt-1 text-xs text-slate-400">{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}
