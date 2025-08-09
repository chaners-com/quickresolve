export default function ProductPage() {
  const steps = [
    { t: 'Create workspace', d: 'Spin up a workspace for your brand and team.' },
    { t: 'Connect knowledge', d: 'Upload docs or connect S3/MinIO. We extract text and generate embeddings.' },
    { t: 'Tune guardrails', d: 'Set tone, restricted topics, and escalation policy.' },
    { t: 'Embed widget', d: 'Copy one script to add your AI agent to any site or app.' },
  ];
  return (
    <main className="relative bg-white">
      <section className="mx-auto max-w-7xl px-6 py-16">
        <h1 className="text-4xl font-extrabold text-center">Product</h1>
        <p className="text-slate-600 text-center mt-2">From scattered knowledge to reliable answers — in minutes.</p>
        <div className="grid md:grid-cols-4 gap-6 mt-10">
          {steps.map((s, i) => (
            <div key={s.t} className="rounded-2xl border border-slate-200 p-6 bg-white shadow-sm">
              <div className="text-sm text-slate-500">Step {i + 1}</div>
              <div className="mt-2 font-semibold">{s.t}</div>
              <div className="mt-1 text-slate-600 text-sm">{s.d}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}




