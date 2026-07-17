const tracks = [
  { name: "API", status: "ready", command: "make api-ci", accent: "bg-emerald-500" },
  { name: "Web", status: "active", command: "pnpm --filter @rapid-template/web dev", accent: "bg-sky-500" },
  { name: "Templates", status: "ready", command: "make create-project", accent: "bg-violet-500" },
  { name: "Turbo", status: "active", command: "pnpm lint", accent: "bg-amber-500" },
];

const checks = [
  ["API quality", "100 tests", "91% coverage"],
  ["Web quality", "ESLint", "TypeScript"],
  ["Generator", "Manifest", "Smoke test"],
  ["Workspace", "pnpm", "Turborepo"],
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="mx-auto grid min-h-screen w-full max-w-7xl grid-cols-1 gap-8 px-5 py-6 md:grid-cols-[280px_1fr] lg:px-8">
        <aside className="flex flex-col justify-between border-b border-black/10 pb-6 md:border-b-0 md:border-r md:pb-0 md:pr-6 dark:border-white/10">
          <div>
            <p className="font-mono text-xs uppercase text-black/55 dark:text-white/55">
              rapid-template
            </p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight">Launch Console</h1>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-1">
            {tracks.map((track) => (
              <div
                key={track.name}
                className="grid min-h-24 grid-rows-[auto_1fr_auto] border border-black/10 bg-white/70 p-4 dark:border-white/10 dark:bg-white/5"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">{track.name}</span>
                  <span className={`h-2.5 w-2.5 rounded-full ${track.accent}`} />
                </div>
                <p className="mt-3 text-sm text-black/60 dark:text-white/60">{track.status}</p>
                <code className="mt-4 block truncate font-mono text-xs text-black/65 dark:text-white/65">
                  {track.command}
                </code>
              </div>
            ))}
          </div>
        </aside>

        <div className="flex flex-col gap-6">
          <section className="grid gap-4 border border-black/10 bg-[#e9ebe1] p-5 md:grid-cols-[1fr_280px] dark:border-white/10 dark:bg-[#20251d]">
            <div>
              <p className="font-mono text-xs uppercase text-black/55 dark:text-white/55">
                workspace state
              </p>
              <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight md:text-6xl">
                API, web, generator, and orchestration in one repo.
              </h2>
            </div>

            <div className="grid grid-cols-2 gap-2 self-end">
              {["apps/api", "apps/web", "templates", "turbo"].map((item) => (
                <div
                  key={item}
                  className="flex aspect-square items-end border border-black/10 bg-background p-3 font-mono text-xs dark:border-white/10"
                >
                  {item}
                </div>
              ))}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {checks.map(([title, primary, secondary]) => (
              <article
                key={title}
                className="min-h-36 border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-white/5"
              >
                <p className="font-mono text-xs uppercase text-black/50 dark:text-white/50">
                  {title}
                </p>
                <p className="mt-5 text-2xl font-semibold">{primary}</p>
                <p className="mt-2 text-sm text-black/60 dark:text-white/60">{secondary}</p>
              </article>
            ))}
          </section>

          <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div className="border border-black/10 bg-white p-5 dark:border-white/10 dark:bg-white/5">
              <p className="font-mono text-xs uppercase text-black/50 dark:text-white/50">
                next batches
              </p>
              <div className="mt-5 grid gap-3">
                {["shared config package", "typed API client", "doctor profiles"].map((item) => (
                  <div
                    key={item}
                    className="flex items-center justify-between border border-black/10 px-3 py-3 text-sm dark:border-white/10"
                  >
                    <span>{item}</span>
                    <span className="font-mono text-xs text-black/45 dark:text-white/45">
                      queued
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="border border-black/10 bg-[#1e211c] p-5 text-[#f2f0e8] dark:border-white/10">
              <p className="font-mono text-xs uppercase text-white/50">command lane</p>
              <div className="mt-5 space-y-3 font-mono text-sm">
                <p>pnpm lint</p>
                <p>pnpm typecheck</p>
                <p>pnpm test</p>
                <p>make api-ci</p>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
