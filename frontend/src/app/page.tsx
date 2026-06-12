import Link from "next/link";

export default function Home() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-[#050510]">
      {/* ─── Animated Background Orbs ─── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute top-[-10%] left-[15%] w-[500px] h-[500px] rounded-full opacity-20"
          style={{
            background: "radial-gradient(circle, rgba(59,130,246,0.4) 0%, transparent 70%)",
            animation: "orbFloat1 12s ease-in-out infinite",
          }}
        />
        <div
          className="absolute bottom-[-5%] right-[10%] w-[400px] h-[400px] rounded-full opacity-15"
          style={{
            background: "radial-gradient(circle, rgba(139,92,246,0.4) 0%, transparent 70%)",
            animation: "orbFloat2 15s ease-in-out infinite",
          }}
        />
        <div
          className="absolute top-[40%] right-[30%] w-[300px] h-[300px] rounded-full opacity-10"
          style={{
            background: "radial-gradient(circle, rgba(16,185,129,0.4) 0%, transparent 70%)",
            animation: "orbFloat3 10s ease-in-out infinite",
          }}
        />
      </div>

      {/* ─── Grid Pattern Overlay ─── */}
      <div className="pointer-events-none absolute inset-0 grid-pattern opacity-40" />

      {/* ─── Hero Content ─── */}
      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-4xl">
        {/* Badge */}
        <div className="animate-slideUp stagger-1 mb-8">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-xs font-medium text-gray-300 tracking-wide">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Multi-Agent AI Decision Engine
          </span>
        </div>

        {/* Title */}
        <h1 className="animate-slideUp stagger-2 text-5xl sm:text-7xl font-extrabold tracking-tight leading-[1.1]">
          <span className="text-white">Your Executive</span>
          <br />
          <span
            className="bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent animate-gradientShift"
            style={{ backgroundSize: "200% 200%" }}
          >
            Boardroom.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="animate-slideUp stagger-3 mt-6 text-lg sm:text-xl text-gray-400 max-w-2xl leading-relaxed">
          Stop guessing. Start consulting your AI CTO, CMO, and CFO instantly.
          <br className="hidden sm:block" />
          Get executive-grade strategy from a panel of specialized AI agents.
        </p>

        {/* CTA */}
        <div className="animate-slideUp stagger-4 mt-10 flex flex-col sm:flex-row gap-4">
          <Link
            href="/dashboard"
            className="group relative px-8 py-3.5 bg-gradient-to-r from-blue-600 to-blue-500 rounded-xl font-semibold text-white transition-all duration-300 hover:scale-[1.03] active:scale-[0.98] shadow-lg shadow-blue-600/25 hover:shadow-blue-500/40"
          >
            <span className="relative z-10 flex items-center gap-2">
              Enter the Boardroom
              <svg className="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </span>
          </Link>
        </div>
      </div>

      {/* ─── Feature Cards ─── */}
      <div className="relative z-10 mt-24 mb-16 grid grid-cols-1 sm:grid-cols-3 gap-5 px-6 max-w-4xl w-full">
        {[
          {
            icon: "👔",
            title: "Strategic Advisor",
            desc: "5 AI C-suite executives analyze your business with structured insights, risks, and recommendations.",
          },
          {
            icon: "🚀",
            title: "VC Pitch Panel",
            desc: "Simulate a VC pitch to Angel, SaaS, Deep Tech, and Growth investors with a Devil's Advocate.",
          },
          {
            icon: "📄",
            title: "RAG Knowledge Base",
            desc: "Upload documents. Your panel uses semantic search to ground every analysis in your real data.",
          },
        ].map((feature, idx) => (
          <div
            key={feature.title}
            className={`animate-slideUp stagger-${idx + 3} glass glass-hover rounded-2xl p-6 transition-all duration-300 hover:translate-y-[-2px] cursor-default`}
          >
            <div className="text-3xl mb-3">{feature.icon}</div>
            <h3 className="text-sm font-bold text-white mb-2">{feature.title}</h3>
            <p className="text-xs text-gray-400 leading-relaxed">{feature.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
