import { Button } from '../components/Button';

// A Server Component: a CSS Module needs no client boundary.
export default function Page() {
  return (
    <main className="stack">
      <h1>Pricing</h1>
      <p>One plan, billed monthly.</p>
      <Button href="/signup">Start the trial</Button>
    </main>
  );
}
