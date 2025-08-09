"use client";
import { motion } from "framer-motion";

type Box = { x: number; y: number; size: number; delay: number; duration: number };

const boxes: Box[] = Array.from({ length: 10 }).map((_, i) => ({
  x: Math.random() * 100,
  y: Math.random() * 60 + 10,
  size: Math.random() * 80 + 40,
  delay: Math.random() * 1.5,
  duration: Math.random() * 8 + 8,
}));

export function FloatingNodes() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {boxes.map((b, i) => (
        <motion.div
          key={i}
          initial={{ y: b.y + "%" }}
          animate={{ y: (b.y + 6) + "%" }}
          transition={{ repeat: Infinity, repeatType: "reverse", duration: b.duration, delay: b.delay, ease: "easeInOut" }}
          className="absolute"
          style={{ left: b.x + "%" }}
        >
          <div className="glass rounded-2xl" style={{ width: b.size, height: b.size }} />
        </motion.div>
      ))}
    </div>
  );
}


