import type { ReactNode } from 'react';
import styles from './Button.module.css';

export function Button({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a className={styles.root} href={href}>
      {children}
    </a>
  );
}
