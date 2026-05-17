<script lang="ts">
    import { onMount } from "svelte";
    import { marked } from "marked";

    let logs = $state<any[]>([]);
    let isLoading = $state(true);
    let error = $state("");

    async function fetchLogs() {
        try {
            const res = await fetch("/api/logs");
            if (!res.ok) throw new Error("API Error");
            logs = await res.json();
        } catch (e) {
            error = "Could not reach backend. Make sure FastAPI is running.";
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
        fetchLogs();
    });
</script>

<svelte:head>
    <title>Admin Traces | Meridian Policy Advisor</title>
</svelte:head>

<main class="max-w-6xl mx-auto p-4 md:p-8 min-h-screen flex flex-col">
    <header class="mb-8 flex items-center justify-between">
        <div>
            <h1 class="text-3xl font-bold text-white flex items-center gap-3">
                <svg
                    class="w-8 h-8 text-purple-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    ></path></svg
                >
                Admin Tracing Console
            </h1>
            <p class="text-slate-400 mt-1">
                Audit logs for Agent Reasoning & Tool Execution
            </p>
        </div>
        <a
            href="/"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg border border-slate-700 transition-colors"
            >Return to Chat</a
        >
    </header>

    {#if isLoading}
        <div class="text-slate-400 animate-pulse">
            Loading execution traces...
        </div>
    {:else if error}
        <div
            class="text-red-400 bg-red-400/10 border border-red-400/20 p-4 rounded-lg"
        >
            {error}
        </div>
    {:else if logs.length === 0}
        <div
            class="text-slate-500 text-center py-12 border border-slate-800 rounded-xl bg-slate-900/50 backdrop-blur-md"
        >
            No queries have been executed yet. Ask a question in the main chat
            to generate logs.
        </div>
    {:else}
        <div class="space-y-6">
            {#each logs as log}
                <div
                    class="bg-slate-900/60 backdrop-blur-xl border border-slate-700 rounded-2xl overflow-hidden shadow-2xl"
                >
                    <div class="p-6">
                        <div class="flex justify-between items-start mb-4">
                            <h2 class="text-xl font-medium text-slate-200">
                                "{log.question}"
                            </h2>
                            <span
                                class="text-xs text-slate-500 font-mono whitespace-nowrap bg-slate-800 px-2 py-1 rounded"
                            >
                                {new Date(log.timestamp).toLocaleString()}
                            </span>
                        </div>

                        <div
                            class="bg-slate-800/80 p-4 rounded-xl border border-slate-700 mb-6 text-sm"
                        >
                            <p
                                class="text-emerald-400 font-mono mb-2 font-bold"
                            >
                                Final Answer:
                            </p>
                            <div
                                class="text-slate-300 prose prose-invert prose-sm max-w-none"
                            >
                                {@html marked.parse(log.answer)}
                            </div>
                        </div>

                        {#if log.citations && log.citations.length > 0}
                            <div class="mb-4 flex flex-wrap gap-2">
                                {#each log.citations as doc}
                                    <span
                                        class="text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 px-3 py-1 rounded-full"
                                        >Citation: {doc}</span
                                    >
                                {/each}
                            </div>
                        {/if}

                        <div class="mt-6">
                            <h3
                                class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-700 pb-2"
                            >
                                Execution Trace Sequence
                            </h3>
                            <div class="space-y-3">
                                {#each log.trace as step, index}
                                    <div class="flex">
                                        <div
                                            class="flex flex-col items-center mr-4"
                                        >
                                            <div
                                                class="w-6 h-6 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-[10px] text-slate-400 font-bold z-10 shrink-0"
                                            >
                                                {index + 1}
                                            </div>
                                            {#if index !== log.trace.length - 1}
                                                <div
                                                    class="w-px h-full bg-slate-700 my-1"
                                                ></div>
                                            {/if}
                                        </div>

                                        <div class="pb-4 w-full">
                                            <div
                                                class="bg-slate-800/50 p-4 rounded-lg border border-slate-700 w-full overflow-hidden"
                                            >
                                                <div
                                                    class="text-sm font-bold text-blue-300 mb-2 font-mono flex gap-2 items-center"
                                                >
                                                    {step.step.toUpperCase()}
                                                    {#if step.tool}
                                                        <span
                                                            class="px-2 py-0.5 bg-slate-700 text-[10px] rounded text-slate-300"
                                                            ><span
                                                                class="text-purple-400"
                                                                >tool:</span
                                                            >
                                                            {step.tool}</span
                                                        >
                                                    {/if}
                                                </div>

                                                {#if step.input}
                                                    <div
                                                        class="text-xs text-slate-400 font-mono mb-2"
                                                    >
                                                        Input: <span
                                                            class="text-slate-300"
                                                            >{step.input}</span
                                                        >
                                                    </div>
                                                {/if}

                                                {#if step.arguments && Object.keys(step.arguments).length > 0}
                                                    <div
                                                        class="bg-slate-900 rounded p-2 text-xs font-mono text-cyan-300 mb-2 overflow-x-auto"
                                                    >
                                                        Args: {JSON.stringify(
                                                            step.arguments,
                                                        )}
                                                    </div>
                                                {/if}

                                                {#if step.text}
                                                    <div
                                                        class="text-xs text-slate-400 border-l-2 border-emerald-500/50 pl-2 py-1"
                                                    >
                                                        {step.text}
                                                    </div>
                                                {/if}

                                                {#if step.result_preview}
                                                    <details
                                                        class="text-[10px] text-slate-500 mt-2"
                                                    >
                                                        <summary
                                                            class="cursor-pointer hover:text-slate-300 list-none"
                                                        >
                                                            [View Return Output]
                                                        </summary>
                                                        <div
                                                            class="mt-2 bg-slate-900 p-2 rounded whitespace-pre-wrap font-mono text-slate-400 max-h-40 overflow-y-auto"
                                                        >
                                                            {step.result_preview}
                                                        </div>
                                                    </details>
                                                {/if}
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</main>
