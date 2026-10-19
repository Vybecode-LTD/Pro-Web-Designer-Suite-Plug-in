<script lang="ts">
  // The global entry, imported by the root layout, so every route has it.
  import '../styles/index.css';
  import '../app.css';

  let { children } = $props();
</script>

{@render children()}
