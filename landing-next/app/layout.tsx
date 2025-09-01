import './globals.css';
import { ReactNode } from 'react';
import { ConditionalSiteHeader } from './components/ConditionalSiteHeader';

export const metadata = {
  title: 'QuickResolve — AI for Customer Support',
  description: 'Resolve issues instantly with retrieval‑augmented AI. Cited answers. Enterprise privacy.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gradient-to-br from-indigo-500 to-violet-600 text-ink/90">
        <ConditionalSiteHeader />
        {children}
      </body>
    </html>
  );
}

