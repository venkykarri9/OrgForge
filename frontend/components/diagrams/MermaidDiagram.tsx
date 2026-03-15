"use client";
import { useEffect, useRef } from "react";

interface Props {
  chart: string;
}

export default function MermaidDiagram({ chart }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    import("mermaid").then((m) => {
      m.default.initialize({ startOnLoad: false, theme: "default" });
      ref.current!.innerHTML = "";
      const id = `mermaid-${Math.random().toString(36).slice(2)}`;
      m.default
        .render(id, chart)
        .then(({ svg }) => {
          if (ref.current) ref.current.innerHTML = svg;
        })
        .catch((err) => {
          if (ref.current) ref.current.innerHTML = `<pre class="text-red-500 text-xs">${err}</pre>`;
        });
    });
  }, [chart]);

  return <div ref={ref} className="bg-white border rounded p-4 overflow-auto" />;
}
