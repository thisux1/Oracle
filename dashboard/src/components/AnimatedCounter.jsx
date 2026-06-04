import { useEffect, useRef } from "react";
import gsap from "gsap";

export default function AnimatedCounter({ value = 0, label, color = "var(--accent-cyan)", duration = 0.8 }) {
  const ref = useRef(null);
  const currentRef = useRef(0);

  useEffect(() => {
    if (!ref.current) return;
    const target = Number(value) || 0;
    const obj = { val: currentRef.current };

    gsap.to(obj, {
      val: target,
      duration,
      ease: "power2.out",
      onUpdate: () => {
        currentRef.current = Math.round(obj.val);
        if (ref.current) {
          ref.current.textContent = currentRef.current.toLocaleString();
        }
      },
    });
  }, [value, duration]);

  return (
    <div className="rounded-xl p-3 text-center" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}>
      <p
        ref={ref}
        className="text-2xl font-bold tabular-nums md:text-3xl"
        style={{ color, fontFamily: "var(--font-mono)" }}
      >
        {Number(value) || 0}
      </p>
      <p className="mt-1 text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
        {label}
      </p>
    </div>
  );
}
