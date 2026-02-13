"use client";

// ---------------------------------------------------------------------------
// AURA Landing Page — /landing
// Single scroll, 5 sections. Communicates what AURA is in 10 seconds.
// ---------------------------------------------------------------------------

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { useAssembly } from "@/context/AssemblyContext";
import { ArchitectureGrid } from "@/components/landing/ArchitectureGrid";

const LandingViewer = dynamic(
  () =>
    import("@/components/landing/LandingViewer").then((m) => ({
      default: m.LandingViewer,
    })),
  { ssr: false },
);

// ---------------------------------------------------------------------------
// Pipeline step data
// ---------------------------------------------------------------------------

const PIPELINE = [
  {
    number: "01",
    title: "Parse",
    description:
      "Upload a STEP file. AURA extracts parts, contacts, and geometry in seconds.",
  },
  {
    number: "02",
    title: "Plan",
    description:
      "Automatic assembly sequence. Primitives for easy steps, teaching slots for hard ones.",
  },
  {
    number: "03",
    title: "Teach",
    description:
      "Demonstrate hard steps with force-feedback teleoperation. 10 demos, 5 minutes each.",
  },
  {
    number: "04",
    title: "Run",
    description:
      "Autonomous execution. Per-step learned policies. Human fallback on failure.",
  },
];

// ---------------------------------------------------------------------------
// Landing Page
// ---------------------------------------------------------------------------

export default function LandingPage() {
  const { assembly } = useAssembly();

  // Scroll-reveal: observe .reveal elements, add .revealed on intersection
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15 },
    );
    const elements = document.querySelectorAll(".reveal");
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="h-screen overflow-y-auto scroll-smooth">
      {/* ----------------------------------------------------------------- */}
      {/* Section 1: Hero                                                    */}
      {/* ----------------------------------------------------------------- */}
      <section className="flex min-h-screen flex-col items-center justify-center px-6 py-16">
        <h1 className="text-[32px] font-semibold tracking-[0.12em] text-accent md:text-[48px]">
          AURA
        </h1>
        <p className="mt-2 text-center text-[14px] tracking-[0.05em] text-text-secondary md:text-[18px]">
          Autonomous Universal Robotic Assembly
        </p>
        <p className="mt-3 text-center text-[14px] text-text-tertiary">
          Upload a CAD file. The robot figures out the rest.
        </p>

        <div className="mt-8 aspect-[4/3] w-full max-w-3xl overflow-hidden rounded-lg bg-bg-viewer md:aspect-[16/10]">
          {assembly && <LandingViewer assembly={assembly} />}
        </div>

        <div className="mt-6 flex gap-3">
          <a
            href="#"
            className="rounded-md border border-bg-tertiary bg-bg-secondary px-4 py-2 text-[13px] font-medium text-text-primary transition-colors hover:bg-bg-tertiary"
          >
            Watch Demo
          </a>
          <a
            href="/"
            className="rounded-md bg-accent px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-accent-hover"
          >
            Try It
          </a>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Section 2: The Problem                                             */}
      {/* ----------------------------------------------------------------- */}
      <section className="px-6 py-16 md:py-24">
        <div className="mx-auto grid max-w-4xl gap-12 md:grid-cols-2">
          <div className="reveal">
            <p className="font-mono text-[32px] font-semibold text-text-primary">$43B</p>
            <p className="mt-2 text-[14px] leading-relaxed text-text-secondary">
              spent annually on human assembly labor that can&apos;t be automated
              because every product is different.
            </p>
          </div>
          <div className="reveal">
            <p className="font-mono text-[32px] font-semibold text-text-primary">
              6+ months
            </p>
            <p className="mt-2 text-[14px] leading-relaxed text-text-secondary">
              to program a new assembly with current solutions. Hard-coded
              trajectories that break when anything changes. We need days.
            </p>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Section 3: How AURA Works                                          */}
      {/* ----------------------------------------------------------------- */}
      <section id="how-it-works" className="px-6 py-16 md:py-24">
        <div className="mx-auto max-w-5xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
            How it works
          </p>
          <div className="mt-10 grid gap-8 sm:grid-cols-2 md:grid-cols-4">
            {PIPELINE.map((step) => (
              <div key={step.number} className="reveal">
                <p className="font-mono text-[13px] font-semibold text-accent">
                  {step.number}
                </p>
                <h3 className="mt-2 text-[16px] font-semibold text-text-primary">
                  {step.title}
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-text-secondary">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Section 4: The Stack                                               */}
      {/* ----------------------------------------------------------------- */}
      <section className="px-6 py-16 md:py-24">
        <div className="reveal mx-auto max-w-5xl">
          <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
            The stack
          </p>
          <p className="mt-3 text-[14px] text-text-secondary">
            ~5,920 lines of Python. 29 source files. Every module tested.
          </p>
          <div className="mt-10">
            <ArchitectureGrid />
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* Section 5: The Vision                                              */}
      {/* ----------------------------------------------------------------- */}
      <section className="px-6 py-16 md:py-24">
        <div className="reveal mx-auto max-w-3xl text-center">
          <p className="text-[16px] italic leading-relaxed text-text-secondary">
            &ldquo;The PC fulfilled Turing&apos;s universal computer.
            <br />
            AURA fulfills von Neumann&apos;s universal constructor.&rdquo;
          </p>
          <p className="mt-10 text-[20px] font-semibold text-text-primary">
            Every home will have one.
          </p>
          <p className="mt-4 text-[13px] text-text-secondary">
            Roberto De la Cruz &mdash; Founder, Nextis
          </p>
          <div className="mt-4 flex justify-center gap-4">
            <a
              href="https://github.com/FLASH-73/Nextis_Bridge"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-text-tertiary underline underline-offset-2 transition-colors hover:text-text-primary"
            >
              GitHub
            </a>
            <a
              href="mailto:roberto@nextis.tech"
              className="text-[13px] text-text-tertiary underline underline-offset-2 transition-colors hover:text-text-primary"
            >
              Email
            </a>
            <a
              href="/"
              className="text-[13px] text-accent underline underline-offset-2 transition-colors hover:text-accent-hover"
            >
              Open Dashboard
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
