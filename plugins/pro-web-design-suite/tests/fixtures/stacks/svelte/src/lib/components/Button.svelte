<script lang="ts">
  import type { Snippet } from 'svelte';

  let { href, tone, children }: { href: string; tone: 'accent' | 'surface'; children: Snippet } = $props();
</script>

<!-- A style directive may set the component's own custom property to a token. -->
<a class="btn" {href} style:--btn-bg={tone === 'accent' ? 'var(--bg-accent)' : 'var(--bg-surface)'}>
  {@render children()}
</a>

<style>
  @layer components {
    .btn {
      --btn-fg: var(--fg-on-accent);

      display: inline-flex;
      align-items: center;
      gap: var(--gap-fused);
      min-block-size: var(--tap-min);
      padding-inline: var(--pad-inline-md);
      padding-block: var(--pad-block-md);
      border: var(--stroke-default) solid transparent;
      border-radius: var(--radius-lg);
      background-color: var(--btn-bg);
      color: var(--btn-fg);
      font: var(--type-ui);
      text-decoration: none;
    }
  }
</style>
