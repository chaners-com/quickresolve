"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

const testimonials = [
  {
    id: 1,
    quote: "We reduced our average response time from 48 hours to under 2 minutes. Game changer.",
    author: "Sarah Chen",
    role: "Head of Support, TechCorp",
    avatar: "SC",
  },
  {
    id: 2,
    quote: "The citation feature gives our compliance team confidence. Every answer is auditable.",
    author: "Michael Rodriguez",
    role: "Compliance Lead, FinanceApp",
    avatar: "MR",
  },
  {
    id: 3,
    quote: "Setup took 30 minutes. ROI was visible within the first week.",
    author: "Emma Thompson",
    role: "Operations Manager, E-commerce Plus",
    avatar: "ET",
  },
];

export function TestimonialCarousel() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative max-w-4xl mx-auto">
      <AnimatePresence mode="wait">
        <motion.div
          key={testimonials[current].id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-white/20 text-white font-semibold text-xl">
              {testimonials[current].avatar}
            </div>
          </div>
          <blockquote className="text-2xl md:text-3xl text-white font-light italic mb-6">
            "{testimonials[current].quote}"
          </blockquote>
          <div className="text-white/80">
            <div className="font-semibold">{testimonials[current].author}</div>
            <div className="text-sm">{testimonials[current].role}</div>
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="flex justify-center gap-2 mt-8">
        {testimonials.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`w-2 h-2 rounded-full transition-all ${
              i === current ? "bg-white w-8" : "bg-white/40"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

