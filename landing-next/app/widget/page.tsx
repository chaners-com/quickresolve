import { CodeSnippet } from "../components/CodeSnippet";

export default function WidgetPage() {
  const embed = `<script src="https://cdn.quickresolve.ai/widget.js" async></script>\n<div id="quickresolve-widget" data-workspace="YOUR_WORKSPACE_ID"></div>`;
  return (
    <main className="relative bg-white">
      <section className="mx-auto max-w-5xl px-6 py-16">
        <h1 className="text-4xl font-extrabold text-center">Embed Widget</h1>
        <p className="text-slate-600 text-center mt-2">Add your AI customer service agent anywhere with one script.</p>
        <div className="mt-8 grid md:grid-cols-2 gap-6">
          <div>
            <h2 className="font-semibold">Installation</h2>
            <p className="text-slate-600 text-sm">Paste this in your site and set your workspace ID.</p>
            <div className="mt-3"><CodeSnippet code={embed} /></div>
            <ul className="mt-4 list-disc pl-5 text-slate-700 space-y-1">
              <li>Branding controls (colors, logo)</li>
              <li>Inline citations and sources</li>
              <li>Request limits by plan</li>
              <li>Consent and analytics options</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="font-semibold">Preview</div>
            <div className="mt-3 rounded-xl border border-slate-200 p-4">
              <div className="rounded-xl bg-indigo-50 text-indigo-900 px-4 py-3 ml-auto max-w-md">Where can I find my invoice?</div>
              <div className="rounded-xl bg-white text-ink px-4 py-3 border border-slate-200 max-w-md mt-2">Invoices are available under Billing. Source: Help Center → Billing</div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}




