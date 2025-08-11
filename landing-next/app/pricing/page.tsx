export default function PricingPage() {
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
    <main className="relative bg-white">
      <section className="mx-auto max-w-7xl px-6 py-16">
        <h1 className="text-4xl font-extrabold text-center">Pricing</h1>
        <p className="text-slate-600 text-center mt-2">Choose a plan that grows with you.</p>
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
        <p className="text-xs text-slate-500 text-center mt-3">Overages billed at tier rate. Contact us for annual discounts.</p>
      </section>
    </main>
  );
}




