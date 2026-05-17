<script lang="ts">
  import '../app.css';
  let { children } = $props();
</script>

<div class="app-container min-h-screen">
  {@render children()}
</div>
