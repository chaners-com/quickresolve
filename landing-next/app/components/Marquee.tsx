"use client";
import { motion } from "framer-motion";

const logos = ["Acme", "Globex", "Initech", "Umbrella", "Hooli", "Stark", "Wayne", "Wonka"];

export function Marquee() {
  return (
    <div className="relative overflow-hidden">
      <motion.div
        className="flex gap-8 whitespace-nowrap"
        initial={{ x: 0 }}
        animate={{ x: "-50%" }}
        transition={{ repeat: Infinity, duration: 20, ease: "linear" }}
      >
        {[...logos, ...logos].map((name, i) => (
          <div key={i} className="rounded-lg border border-white/30 px-4 py-2 text-white/90">
            {name}
          </div>
        ))}
      </motion.div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-indigo-600/40 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-violet-600/40 to-transparent" />
    </div>
  );
}




