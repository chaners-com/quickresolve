"use client";
import { motion } from "framer-motion";
import Link from "next/link";
import { ParticleField } from "./components/ParticleField";
import { ScrollAnimation } from "./components/ScrollAnimation";
import { GradientOrbs } from "./components/GradientOrbs";
import { GlassCard } from "./components/GlassCard";
import { FeatureShowcase } from "./components/FeatureShowcase";
import { TestimonialCarousel } from "./components/TestimonialCarousel";
import { AnimatedFooter } from "./components/AnimatedFooter";
import { DragDropDemo } from "./components/DragDropDemo";
import { CodeSnippet } from "./components/CodeSnippet";

export default function HomePage() {
  const plans = [
    {
      name: 'Starter', price: '$49/mo', subtitle: 'For early-stage teams',
      features: [
        'Up to 10,000 requests/month',
        '1 workspace',
        'Email support',
        'Cited answers',
        'Widget embed',
      ],
    },
    {
      name: 'Growth', price: '$199/mo', subtitle: 'Scale up engagement',
      features: [
        'Up to 50,000 requests/month',
        '3 workspaces',
        'Priority email support',
        'Custom branding',
        'Advanced analytics',
      ],
      highlight: true,
    },
    {
      name: 'Scale', price: '$499/mo', subtitle: 'High-traffic operations',
      features: [
        'Up to 200,000 requests/month',
        '10 workspaces',
        'Chat support',
        'Access controls & redaction',
        'SLA targets',
      ],
    },
    {
      name: 'Enterprise', price: 'Custom', subtitle: 'Security & compliance at scale',
      features: [
        'Unlimited requests (fair use)',
        'SAML/SSO',
        'VPC deployment',
        'SOC2-ready architecture',
        'Dedicated CSM & SLA',
      ],
    },
  ];

  return (
    <div className="relative min-h-screen overflow-hidden">
      <GradientOrbs />
      <ParticleField />

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 rounded-full glass-premium px-4 py-2 mb-6"
            >
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-white/90 text-sm">AI-Powered Customer Service</span>
            </motion.div>

            <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-6">
              <span className="gradient-text">QuickResolve</span>
            </h1>
            <p className="text-xl md:text-2xl text-white/80 mb-8 max-w-3xl mx-auto">
              Transform your support with AI that understands context, cites sources, and scales infinitely
            </p>

            <div className="flex flex-wrap gap-4 justify-center">
              <motion.a
                href="#waitlist"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold rounded-full shadow-lg hover:shadow-emerald-500/25"
              >
                Get Early Access
              </motion.a>
              <motion.a
                href="#demo"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 glass-premium text-white font-semibold rounded-full"
              >
                Watch Demo
              </motion.a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-16 relative"
          >
            <div className="absolute inset-0 bg-gradient-to-t from-indigo-500/20 to-transparent blur-3xl" />
            <GlassCard hoverable={false} className="max-w-4xl mx-auto">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <div className="text-white/60 text-sm mb-2">Customer</div>
                  <div className="rounded-xl bg-white/10 p-4 text-white">
                    How do I integrate with Shopify webhooks?
                  </div>
                </div>
                <div>
                  <div className="text-white/60 text-sm mb-2">QuickResolve AI</div>
                  <div className="rounded-xl bg-emerald-500/20 p-4 text-white">
                    Here's the webhook setup process... <span className="text-emerald-400">Source: API Docs v3.2</span>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        </div>
      </section>

      {/* Interactive Features */}
      <section className="relative py-20">
        <ScrollAnimation>
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-4xl font-bold text-white text-center mb-4">
              Why teams choose QuickResolve
            </h2>
            <p className="text-white/70 text-center mb-12 max-w-2xl mx-auto">
              Built for modern support teams who need accuracy, speed, and trust
            </p>
            <FeatureShowcase />
          </div>
        </ScrollAnimation>
      </section>

      {/* Drag & Drop Demo */}
      <section id="demo" className="relative py-20 bg-white/5">
        <ScrollAnimation>
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-4xl font-bold text-white text-center mb-4">
              See it in action
            </h2>
            <p className="text-white/70 text-center mb-12">
              Upload your docs and watch the AI learn instantly
            </p>
            <DragDropDemo />
          </div>
        </ScrollAnimation>
      </section>

      {/* Testimonials */}
      <section className="relative py-20">
        <ScrollAnimation>
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-4xl font-bold text-white text-center mb-12">
              Trusted by support leaders
            </h2>
            <TestimonialCarousel />
          </div>
        </ScrollAnimation>
      </section>

      {/* Pricing Cards */}
      <section className="relative py-20 bg-white/5">
        <ScrollAnimation>
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-4xl font-extrabold text-center text-white">Pricing</h2>
            <p className="text-white/70 text-center mt-2">Choose a plan that grows with you.</p>
            <div className="grid md:grid-cols-4 gap-6 mt-10">
              {plans.map((p) => (
                <div key={p.name} className={`rounded-2xl p-6 border ${p.highlight ? 'border-violet-400 shadow-lg' : 'border-slate-200 shadow-sm'} bg-white`}>
                  <div className="text-sm text-slate-500">{p.name}</div>
                  <div className="mt-2 text-3xl font-extrabold">{p.price}</div>
                  <div className="text-slate-600">{p.subtitle}</div>
                  <ul className="mt-4 space-y-2 text-slate-700">
                    {p.features.map((f) => <li key={f}>• {f}</li>)}
                  </ul>
                  <a href="/widget" className="btn-primary mt-4 inline-flex">Get started</a>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-300 text-center mt-3">Overages billed at tier rate. Contact us for annual discounts.</p>
          </div>
        </ScrollAnimation>
      </section>

      {/* Widget Integration */}
      <section className="relative py-20">
        <ScrollAnimation>
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-4xl font-bold text-white text-center mb-12">
              One-line integration
            </h2>
            <div className="max-w-3xl mx-auto">
              <CodeSnippet code={`<script src="https://cdn.quickresolve.ai/widget.js" async></script>
<div id="quickresolve-widget" data-workspace="YOUR_WORKSPACE_ID"></div>`} />
            </div>
          </div>
        </ScrollAnimation>
      </section>

      {/* Waitlist Form */}
      <section id="waitlist" className="relative py-20 bg-white/5">
        <ScrollAnimation>
          <div className="mx-auto max-w-2xl px-6">
            <GlassCard hoverable={false}>
              <h2 className="text-3xl font-bold text-white text-center mb-2">
                Join the waitlist
              </h2>
              <p className="text-white/70 text-center mb-8">
                Be among the first to transform your customer support
              </p>
              <WaitlistForm />
            </GlassCard>
          </div>
        </ScrollAnimation>
      </section>

      {/* Footer */}
      <AnimatedFooter />
    </div>
  );
}

function WaitlistForm() {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData(e.currentTarget);
    const payload = {
      name: formData.get('name'),
      email: formData.get('email'),
      company: formData.get('company'),
      team_size: formData.get('teamSize'),
    };
    
    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Failed');
      setMsg('🎉 You\'re on the list! Check your email soon.');
      e.currentTarget.reset();
    } catch {
      setMsg('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <input
        name="name"
        required
        placeholder="Full name"
        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <input
        name="email"
        type="email"
        required
        placeholder="Work email"
        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <input
        name="company"
        placeholder="Company (optional)"
        className="w-full px-4 py-3 rounded-lg glass-premium text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <select
        name="teamSize"
        className="w-full px-4 py-3 rounded-lg glass-premium text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
      >
        <option value="">Team size</option>
        <option>1-10</option>
        <option>11-50</option>
        <option>51-200</option>
        <option>201-1000</option>
        <option>1000+</option>
      </select>
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold disabled:opacity-50 hover:shadow-lg hover:shadow-emerald-500/25 transition"
      >
        {loading ? 'Submitting...' : 'Request Access'}
      </button>
      {msg && <p className="text-center text-white/80">{msg}</p>}
    </form>
  );
}

import { useState } from "react";