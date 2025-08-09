"use client";
import { motion } from "framer-motion";
import { useState } from "react";
import { GlassCard } from "./GlassCard";

const features = [
  {
    id: "semantic",
    icon: "🔮",
    title: "Semantic Understanding",
    description: "AI that truly understands context, not just keywords",
    details: "Our advanced NLP models comprehend intent, handle typos, and understand conversational nuances.",
  },
  {
    id: "citations",
    icon: "📚",
    title: "Trustworthy Citations",
    description: "Every answer backed by verifiable sources",
    details: "See exactly which documents informed each response with relevance scores and direct links.",
  },
  {
    id: "realtime",
    icon: "⚡",
    title: "Real-time Responses",
    description: "Sub-second query processing at scale",
    details: "Optimized vector search and caching deliver instant answers even with millions of documents.",
  },
  {
    id: "privacy",
    icon: "🛡️",
    title: "Enterprise Privacy",
    description: "Your data stays yours, always",
    details: "On-premise deployment options, SOC2 compliance, and zero training on customer data.",
  },
];

export function FeatureShowcase() {
  const [activeFeature, setActiveFeature] = useState(features[0]);

  return (
    <div className="grid md:grid-cols-2 gap-8 items-start">
      <div className="space-y-4">
        {features.map((feature, i) => (
          <motion.div
            key={feature.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            onClick={() => setActiveFeature(feature)}
            className={`cursor-pointer p-4 rounded-xl transition-all ${
              activeFeature.id === feature.id
                ? "bg-white/20 border border-white/30"
                : "bg-white/5 border border-white/10 hover:bg-white/10"
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">{feature.icon}</span>
              <div>
                <h3 className="font-semibold text-white">{feature.title}</h3>
                <p className="text-white/70 text-sm mt-1">{feature.description}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <GlassCard className="sticky top-24" hoverable={false}>
        <motion.div
          key={activeFeature.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <span className="text-4xl">{activeFeature.icon}</span>
          <h3 className="text-xl font-bold text-white mt-4">{activeFeature.title}</h3>
          <p className="text-white/90 mt-3">{activeFeature.details}</p>
          <div className="mt-6 p-4 bg-white/5 rounded-lg">
            <div className="text-sm text-white/60">Example:</div>
            <div className="mt-2 text-white/90">
              {activeFeature.id === "semantic" && "User: 'How do I reset my pwd?' → AI understands 'password reset process'"}
              {activeFeature.id === "citations" && "Answer: 'Follow these steps...' Source: Security Policy v2.1, Page 23"}
              {activeFeature.id === "realtime" && "Average response time: 127ms for 1M+ document corpus"}
              {activeFeature.id === "privacy" && "Deploy in your VPC with end-to-end encryption"}
            </div>
          </div>
        </motion.div>
      </GlassCard>
    </div>
  );
}

