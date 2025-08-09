"use client";
import { motion } from "framer-motion";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  hoverable?: boolean;
}

export function GlassCard({ children, className = "", delay = 0, hoverable = true }: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay }}
      whileHover={hoverable ? { y: -5, scale: 1.02 } : {}}
      className={`relative ${className}`}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-white/5 rounded-2xl backdrop-blur-xl" />
      <div className="relative bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-6 shadow-2xl">
        {children}
      </div>
    </motion.div>
  );
}

