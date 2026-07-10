import { useEffect, useState } from "react";

export default function CustomCursor() {
  const [state, setState] = useState({ hovered: false, clicked: false, visible: false });

  useEffect(() => {
    const updateCursor = (e) => {
      document.documentElement.style.setProperty("--cursor-x", `${e.clientX}px`);
      document.documentElement.style.setProperty("--cursor-y", `${e.clientY}px`);
      setState((prev) => (prev.visible ? prev : { ...prev, visible: true }));
    };

    const handleMouseOver = (e) => {
      const target = e.target;
      if (!target) return;

      const isInteractive = target.closest(
        'button, a, [role="button"], input, select, textarea, label, [onClick], [type="file"], .btn'
      );
      const hovered = !!isInteractive;
      setState((prev) => (prev.hovered === hovered ? prev : { ...prev, hovered }));
    };

    const handleMouseDown = () => setState((prev) => ({ ...prev, clicked: true }));
    const handleMouseUp = () => setState((prev) => ({ ...prev, clicked: false }));
    const handleMouseLeave = () => setState((prev) => ({ ...prev, visible: false }));
    const handleMouseEnter = () => setState((prev) => ({ ...prev, visible: true }));

    window.addEventListener("pointermove", updateCursor);
    window.addEventListener("mouseover", handleMouseOver);
    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("mouseleave", handleMouseLeave);
    document.addEventListener("mouseenter", handleMouseEnter);

    return () => {
      window.removeEventListener("pointermove", updateCursor);
      window.removeEventListener("mouseover", handleMouseOver);
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("mouseleave", handleMouseLeave);
      document.removeEventListener("mouseenter", handleMouseEnter);
    };
  }, []);

  if (!state.visible) return null;

  return (
    <>
      <div className="custom-cursor-dot hidden md:block" />
      <div
        className={`custom-cursor-ring hidden md:block ${state.hovered ? "cursor-hover" : ""} ${state.clicked ? "cursor-click" : ""}`}
      />
    </>
  );
}
