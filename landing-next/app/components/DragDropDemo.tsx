"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

type Item = { id: string; name: string };

const initial: Item[] = [
  { id: "1", name: "wiki.md" },
  { id: "2", name: "policy.pdf" },
  { id: "3", name: "tickets.csv" },
];

export function DragDropDemo() {
  const [files, setFiles] = useState<Item[]>(initial);
  const [dropped, setDropped] = useState<Item[]>([]);
  const [step, setStep] = useState(0);

  function onDropAll() {
    setDropped(files);
    setFiles([]);
    setTimeout(() => setStep(1), 400);
    setTimeout(() => setStep(2), 1200);
  }

  return (
    <div id="demo" className="grid md:grid-cols-2 gap-6 items-start">
      <div className="rounded-2xl bg-white p-6 border border-slate-200 shadow-sm">
        <div className="font-semibold">Drag your docs</div>
        <div className="text-slate-600 text-sm">Wiki, docs, PDFs, and old tickets</div>
        <div className="mt-4 min-h-[160px] rounded-xl border border-dashed border-slate-300 p-4">
          <AnimatePresence>
            {files.map((f) => (
              <motion.div
                key={f.id}
                className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 mb-2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                {f.name}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <button onClick={onDropAll} className="btn-primary mt-4">Upload to workspace</button>
      </div>

      <div className="rounded-2xl bg-white p-6 border border-slate-200 shadow-sm">
        <div className="font-semibold">Your AI assistant</div>
        <div className="text-slate-600 text-sm">Answers with citations</div>
        <div className="mt-4 min-h-[160px] rounded-xl border border-slate-200 p-4">
          <AnimatePresence>
            {dropped.map((f) => (
              <motion.div
                key={f.id}
                className="rounded-lg bg-indigo-50 text-indigo-900 px-3 py-2 mb-2"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                Indexed: {f.name}
              </motion.div>
            ))}
          </AnimatePresence>
          {step >= 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-lg bg-white border border-slate-200 px-3 py-2">
              How do I reset 2FA?
            </motion.div>
          )}
          {step >= 2 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-lg bg-white border border-slate-200 px-3 py-2 mt-2">
              Here’s the process. Source: policy.pdf (Section 3)
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}




