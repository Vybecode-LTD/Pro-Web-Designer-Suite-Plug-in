// The global entry is the root layout's first import: Next.js orders CSS by
// import order, so index.css, which states the layer order, comes first.
import './styles/index.css';
import type { ReactNode } from 'react';

export const metadata = { title: 'Stacks: Next.js' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
