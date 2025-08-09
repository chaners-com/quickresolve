"use client";
import { motion } from "framer-motion";
import Link from "next/link";

const footerLinks = [
  { name: "Product", items: ["Features", "Pricing", "Security", "Roadmap"] },
  { name: "Company", items: ["About", "Blog", "Careers", "Contact"] },
  { name: "Resources", items: ["Documentation", "API", "Status", "Terms"] },
];

export function AnimatedFooter() {
  return (
    <footer className="relative mt-20 border-t border-white/10">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h3 className="text-2xl font-bold text-white mb-4">QuickResolve</h3>
            <p className="text-white/70 text-sm">
              AI-powered customer service that scales with your business.
            </p>
          </motion.div>

          {footerLinks.map((section, i) => (
            <motion.div
              key={section.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              <h4 className="font-semibold text-white mb-4">{section.name}</h4>
              <ul className="space-y-2">
                {section.items.map((item) => (
                  <li key={item}>
                    <Link
                      href="#"
                      className="text-white/70 hover:text-white transition-colors text-sm"
                    >
                      {item}
                    </Link>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-8 pt-8 border-t border-white/10 text-center text-white/60 text-sm"
        >
          © {new Date().getFullYear()} QuickResolve. All rights reserved.
        </motion.div>
      </div>
    </footer>
  );
}

