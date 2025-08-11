"use client";
import { motion } from "framer-motion";

export function HeroAurora() {
  return (
    <div className="relative overflow-hidden">
      <div className="aurora absolute inset-0" />
      <div className="mx-auto max-w-7xl px-6 pt-20 pb-12 grid md:grid-cols-12 gap-8 items-center relative">
        <motion.div
          className="md:col-span-7"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3 py-1 text-sm text-white/90">
            <span className="inline-block h-2 w-2 rounded-full bg-fuchsia-400" />
            AI Customer Service Agent for modern teams
          </div>
          <h1 className="mt-4 text-4xl md:text-6xl font-extrabold text-white leading-tight">
            QuickResolve
          </h1>
          <p className="mt-3 text-white/90 text-lg max-w-2xl">
            Turn your docs, tickets and policies into a trustworthy AI customer service expert. One workspace. One widget. Cited answers.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="#waitlist" className="btn-primary">Request access</a>
            <a href="#demo" className="btn-secondary">See how it works</a>
          </div>
        </motion.div>

        <motion.div
          className="md:col-span-5"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          <div className="glass rounded-2xl p-5 shadow-2xl">
            <div className="rounded-xl bg-ink/90 text-slate-200 px-4 py-2 text-sm">Brand Preview</div>
            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
              <div className="rounded-xl h-20 bg-white/90 border border-slate-200" />
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}




