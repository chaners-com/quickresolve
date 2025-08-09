export default function SecurityPage() {
  const items = [
    { t: 'Data residency', d: 'Run in your infrastructure or our managed cloud with region options.' },
    { t: 'Access control', d: 'Workspace-level permissions, PII redaction, and audit trails.' },
    { t: 'Compliance', d: 'SOC2-ready architecture; configurable retention and logging.' },
    { t: 'Privacy', d: 'Your data is not used to train public models. No vendor lock-in.' },
  ];
  return (
    <main className="relative bg-white">
      <section className="mx-auto max-w-7xl px-6 py-16">
        <h1 className="text-4xl font-extrabold text-center">Security & Privacy</h1>
        <p className="text-slate-600 text-center mt-2">Built for trust from day one.</p>
        <div className="grid md:grid-cols-2 gap-6 mt-10">
          {items.map((i) => (
            <div key={i.t} className="rounded-2xl border border-slate-200 p-6 bg-white shadow-sm">
              <div className="font-semibold">{i.t}</div>
              <div className="mt-1 text-slate-600">{i.d}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}




