export default function SolutionsPage() {
  const groups = [
    { t: 'Customer Support', items: ['Close tickets faster', 'Cited answers', 'Self-serve for customers'] },
    { t: 'Customer Success', items: ['Onboarding guidance', 'Proactive education', 'Reduced escalations'] },
    { t: 'Internal Knowledge', items: ['Unified search', 'Policy alignment', 'Fewer shoulder taps'] },
  ];
  return (
    <main className="relative bg-white">
      <section className="mx-auto max-w-7xl px-6 py-16">
        <h1 className="text-4xl font-extrabold text-center">Solutions</h1>
        <p className="text-slate-600 text-center mt-2">Tailored to the workflows that matter.</p>
        <div className="grid md:grid-cols-3 gap-6 mt-10">
          {groups.map((g) => (
            <div key={g.t} className="rounded-2xl border border-slate-200 p-6 bg-white shadow-sm">
              <div className="font-semibold">{g.t}</div>
              <ul className="mt-2 text-slate-700 space-y-1">
                {g.items.map((i) => <li key={i}>• {i}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}




