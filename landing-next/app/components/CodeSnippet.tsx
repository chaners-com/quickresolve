"use client";
import { useState } from "react";

export function CodeSnippet({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <pre className="rounded-2xl bg-slate-900 text-slate-100 p-4 overflow-auto border border-slate-800 shadow-lg">
        <code>{code}</code>
      </pre>
      <button
        onClick={() => {
          navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="absolute top-2 right-2 rounded-lg bg-white/10 px-3 py-1 text-sm text-white border border-white/20 hover:bg-white/20"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}


