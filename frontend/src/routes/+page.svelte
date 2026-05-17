<script lang="ts">
    import { onMount } from "svelte";
    import { marked } from "marked";

    let query = $state("");
    let messages = $state<
        {
            role: "user" | "agent";
            content: string;
            citations?: string[];
            trace?: any[];
        }[]
    >([]);
    let isLoading = $state(false);

    async function askQuestion() {
        if (!query.trim() || isLoading) return;

        // Add User Message
        const q = query;
        messages = [...messages, { role: "user", content: q }];
        query = "";
        isLoading = true;

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q }),
            });
            if (!res.ok) throw new Error("API Error");
            const data = await res.json();

            messages = [
                ...messages,
                {
                    role: "agent",
                    content: data.answer,
                    citations: data.citations,
                    trace: data.trace,
                },
            ];
        } catch (e) {
            messages = [
                ...messages,
                {
                    role: "agent",
                    content: `Error: Could not reach the agent. Please make sure the FastAPI backend is running.`,
                },
            ];
        } finally {
            isLoading = false;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            askQuestion();
        }
    }
</script>

<svelte:head>
    <title>Meridian Policy Advisor</title>
</svelte:head>

<main class="max-w-4xl mx-auto p-4 md:p-8 h-screen flex flex-col">
    <!-- Header -->
    <header class="mb-6 flex items-center justify-between">
        <div>
            <h1
                class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3"
            >
                <div
                    class="h-8 w-8 rounded-lg bg-blue-500 bg-opacity-20 flex items-center justify-center border border-blue-400"
                >
                    <svg
                        class="w-5 h-5 text-blue-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                        ></path></svg
                    >
                </div>
                Meridian<span
                    class="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent"
                    >Advisor</span
                >
            </h1>
            <p class="text-slate-400 mt-1 text-sm font-medium">
                Agentic Retrieval Engine for Corporate Policies
            </p>
        </div>
        <a
            href="/admin"
            class="px-4 py-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 text-sm font-semibold transition-all hover:shadow-lg flex items-center gap-2"
        >
            <svg
                class="w-4 h-4 text-purple-400"
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
            Trace Admin
        </a>
    </header>

    <!-- Chat Area (Glassmorphism) -->
    <div
        class="flex-1 overflow-y-auto mb-6 rounded-2xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-xl shadow-2xl p-4 md:p-6 flex flex-col gap-6 custom-scrollbar"
    >
        {#if messages.length === 0}
            <div
                class="flex-1 flex flex-col items-center justify-center text-slate-500 space-y-4"
            >
                <svg
                    class="w-16 h-16 opacity-30"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1.5"
                        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    ></path></svg
                >
                <p>Ask anything about Meridian's corporate policies.</p>
                <div class="flex flex-wrap justify-center gap-2 mt-4 max-w-lg">
                    <button
                        onclick={() =>
                            (query = "What is the standard notice period?")}
                        class="px-3 py-1.5 rounded-full border border-slate-700 hover:border-blue-500 hover:text-blue-400 text-sm transition-colors text-slate-400"
                        >Notice Period</button
                    >
                    <button
                        onclick={() =>
                            (query =
                                "Can I carry forward unused sick days to next year?")}
                        class="px-3 py-1.5 rounded-full border border-slate-700 hover:border-purple-500 hover:text-purple-400 text-sm transition-colors text-slate-400"
                        >Contradiction Test</button
                    >
                    <button
                        onclick={() =>
                            (query =
                                "If I travel to the UAE for a client meeting, what expense category applies?")}
                        class="px-3 py-1.5 rounded-full border border-slate-700 hover:border-emerald-500 hover:text-emerald-400 text-sm transition-colors text-slate-400"
                        >Composition Task</button
                    >
                </div>
            </div>
        {/if}

        {#each messages as msg}
            {#if msg.role === "user"}
                <div
                    class="flex justify-end animate-in fade-in slide-in-from-bottom-2"
                >
                    <div
                        class="bg-blue-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[85%] shadow-md"
                    >
                        {msg.content}
                    </div>
                </div>
            {:else}
                <div
                    class="flex justify-start animate-in fade-in slide-in-from-bottom-2"
                >
                    <div
                        class="bg-slate-800/80 border border-slate-700/50 text-slate-200 px-5 py-4 rounded-2xl rounded-tl-sm max-w-[95%] shadow-md"
                    >
                        <!-- Agent message formatting -->
                        <div
                            class="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700"
                        >
                            {@html marked.parse(msg.content)}
                        </div>

                        <!-- Citations UI -->
                        {#if msg.citations && msg.citations.length > 0}
                            <div
                                class="mt-4 pt-4 border-t border-slate-700 flex flex-wrap gap-2 items-center"
                            >
                                <span
                                    class="text-xs text-slate-400 font-medium tracking-wide uppercase"
                                    >Citations:</span
                                >
                                {#each msg.citations as doc}
                                    <span
                                        class="text-xs bg-slate-700/50 border border-slate-600 text-blue-300 px-2 py-1 rounded-md"
                                        >{doc}</span
                                    >
                                {/each}
                            </div>
                        {/if}

                        <!-- Expandable Trace UI -->
                        {#if msg.trace && msg.trace.length > 0}
                            <div class="mt-4">
                                <details class="text-xs text-slate-500 group">
                                    <summary
                                        class="cursor-pointer hover:text-slate-300 transition-colors list-none font-mono flex items-center gap-1"
                                    >
                                        <svg
                                            class="w-3 h-3 transition-transform group-open:rotate-90"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M9 5l7 7-7 7"
                                            ></path></svg
                                        >
                                        [View Agent Trace]
                                    </summary>
                                    <div
                                        class="mt-2 ml-4 pl-3 border-l text-[10px] border-slate-700 space-y-2 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto mb-2"
                                    >
                                        {#each msg.trace as step}
                                            <div
                                                class="bg-slate-900/50 p-2 rounded"
                                            >
                                                <span
                                                    class="text-emerald-500 font-bold"
                                                    >{step.step}</span
                                                >
                                                {#if step.tool}
                                                    ({step.tool}){/if}
                                                {#if step.arguments}<br /><span
                                                        class="text-blue-300"
                                                        >Args:</span
                                                    >
                                                    {JSON.stringify(
                                                        step.arguments,
                                                    )}{/if}
                                                {#if step.result_preview}<br
                                                    /><span
                                                        class="text-purple-300"
                                                        >Result:</span
                                                    >
                                                    {step.result_preview}{/if}
                                            </div>
                                        {/each}
                                    </div>
                                </details>
                            </div>
                        {/if}
                    </div>
                </div>
            {/if}
        {/each}

        {#if isLoading}
            <div class="flex justify-start mt-2">
                <div
                    class="bg-slate-800/80 border border-slate-700/50 text-slate-300 px-5 py-3 rounded-2xl rounded-tl-sm shadow-md flex items-center gap-2"
                >
                    <div class="flex gap-1">
                        <div
                            class="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]"
                        ></div>
                        <div
                            class="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]"
                        ></div>
                        <div
                            class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                        ></div>
                    </div>
                    <span class="text-sm font-medium ml-2 text-slate-400"
                        >Agent evaluating corpus...</span
                    >
                </div>
            </div>
        {/if}
    </div>

    <!-- Input Area -->
    <div class="relative group">
        <div
            class="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"
        ></div>
        <div
            class="relative flex items-center bg-slate-900/90 rounded-xl border border-slate-700 p-2 shadow-xl backdrop-blur-sm"
        >
            <textarea
                bind:value={query}
                onkeydown={handleKeydown}
                disabled={isLoading}
                rows="1"
                placeholder="Ask a policy question..."
                class="w-full bg-transparent text-white border-0 focus:ring-0 resize-none p-3 max-h-32 text-sm placeholder:text-slate-500 custom-scrollbar disabled:opacity-50"
            ></textarea>
            <button
                onclick={askQuestion}
                disabled={isLoading || !query.trim()}
                class="m-1 p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 cursor-pointer text-white rounded-lg transition-transform hover:scale-105 active:scale-95 border border-blue-500/50 shadow-lg flex-shrink-0"
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M14 5l7 7m0 0l-7 7m7-7H3"
                    ></path></svg
                >
            </button>
        </div>
        <p
            class="text-[10px] text-center text-slate-600 mt-3 relative z-10 font-medium"
        >
            Meridian Policy Advisor - Agentic System Prototype
        </p>
    </div>
</main>

<style>
    /* Base custom scrollbar */
    .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: rgba(71, 85, 105, 0.4);
        border-radius: 10px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: rgba(71, 85, 105, 0.8);
    }
</style>
