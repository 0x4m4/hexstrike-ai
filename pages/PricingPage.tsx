import { Link } from 'react-router-dom';

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    features: [
      '10 analyses per month',
      'Single AI provider',
      'Quick analysis mode',
      'Basic clip export',
      'Community support',
    ],
    cta: 'Get Started',
    highlighted: false,
  },
  {
    name: 'Pro',
    price: '$19',
    period: '/month',
    features: [
      '100 analyses per month',
      'All AI providers',
      'Board of Advisors mode',
      'HD clip export',
      'Project management',
      'Priority support',
      'Analytics dashboard',
    ],
    cta: 'Start Pro Trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: '$79',
    period: '/month',
    features: [
      '1000 analyses per month',
      'All AI providers',
      'Board of Advisors mode',
      '4K clip export',
      'Team collaboration',
      'API access',
      'Custom brand guidelines',
      'Dedicated support',
    ],
    cta: 'Contact Sales',
    highlighted: false,
  },
];

export function PricingPage() {
  return (
    <div className="py-12">
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold text-text-primary">Simple Pricing</h1>
        <p className="text-lg text-text-secondary">Start free, upgrade as you grow</p>
      </div>

      <div className="mx-auto grid max-w-5xl gap-6 px-4 md:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`glass rounded-2xl p-6 ${
              plan.highlighted ? 'ring-2 ring-primary shadow-elevated' : ''
            }`}
          >
            {plan.highlighted && (
              <div className="mb-4 inline-block rounded-full bg-primary/20 px-3 py-1 text-xs font-medium text-primary">
                Most Popular
              </div>
            )}
            <h3 className="text-xl font-bold text-text-primary">{plan.name}</h3>
            <div className="my-4">
              <span className="text-4xl font-bold text-text-primary">{plan.price}</span>
              <span className="text-text-muted">{plan.period}</span>
            </div>
            <ul className="mb-6 space-y-3">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2 text-sm text-text-secondary">
                  <span className="mt-0.5 text-green-400">&#10003;</span>
                  {feature}
                </li>
              ))}
            </ul>
            <Link
              to="/dashboard"
              className={`block rounded-lg py-3 text-center font-medium transition-all ${
                plan.highlighted
                  ? 'bg-primary text-white hover:bg-primary-hover'
                  : 'bg-surface text-text-primary hover:bg-surface-hover'
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
