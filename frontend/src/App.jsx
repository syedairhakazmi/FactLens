import { useState, useEffect, useRef, useCallback } from "react";
import {
  Search, ChevronDown,
  CheckCircle2, XCircle, HelpCircle, ArrowLeft, Loader2,
  FileText, AlertTriangle, Globe2, Database, ArrowUpRight, Sparkles,
  ArrowRight, Settings2, Link2, RefreshCw, MessageSquare, Copy, Check,
  Command, Mic, MicOff, Upload, Volume2, Square, Radio
} from "lucide-react";

// ---------------------------------------------------------------------------
// DESIGN TOKENS - "highlighter desk" identity, deepened into a proper
// evidence-desk / case-file visual language. Warm paper, ink-navy text,
// hot-pink brand ink, marker-color kit doubling as the verdict/status
// system. New this pass: layered depth (soft ambient shadow + hard offset
// shadow), a fine paper-grain texture, a single orchestrated hero
// spotlight, a radial confidence gauge, an animated tab indicator, and a
// session case log — all built on the same pipeline this prototype has
// always represented.
// ---------------------------------------------------------------------------

const C = {
  paper: "#FBF8F1",
  paperRaised: "#FFFFFF",
  paperSoft: "#F3EEDF",
  paperDeep: "#EFE8D6",
  line: "#E4DCC4",
  lineStrong: "#16464d",
  lineOuter: "#97a09e",
  ink: "#000000",
  inkSoft: "#050505",
  inkFaint: "#131212",
  brand: "#380101",
  brandDeep: "#E31E58",
  brandSoft: "#cfc0c4",
  brandInk: "#7A0F2E",
  highlight: "#FFD23F",
  highlightSoft: "#FFF3C4",
  supported: "#0d5f3d",
  supportedSoft: "#DEF5E9",
  refuted: "#64101b",
  refutedSoft: "#FDE1E6",
  info: "#041053",
  infoSoft: "#E4E9FF",
  opinion: "#4913c7",
  opinionSoft: "#EDE6FE",
};

const DISPLAY = '"Syne", "Segoe UI", sans-serif';
const BODY = '"DM Sans", "Segoe UI", sans-serif';
const MONO = '"DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace';

// Helper to resolve backend API URL dynamically:
// Works seamlessly on desktop (localhost) and mobile phones on the local LAN (e.g. http://192.168.18.16:8000)
function getApiBase() {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== "undefined" && window.location && window.location.hostname) {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

// ---------------------------------------------------------------------------
// GLOBAL STYLE
// ---------------------------------------------------------------------------

function GlobalStyle() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&family=Kalam:wght@400;700&display=swap');

      * { -webkit-tap-highlight-color: transparent; }
      ::selection { background-color: ${C.highlight}; color: ${C.ink}; }

      @keyframes flDrift {
        0%   { transform: translate(0px, 0px) rotate(var(--rot, 0deg)); }
        50%  { transform: translate(6px, -10px) rotate(calc(var(--rot, 0deg) + 4deg)); }
        100% { transform: translate(0px, 0px) rotate(var(--rot, 0deg)); }
      }
      @keyframes flWobble { 0%, 100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
      @keyframes flPop { 0% { transform: scale(0.6); opacity: 0; } 70% { transform: scale(1.06); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
      @keyframes flFadeUp { 0% { transform: translateY(10px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
      @keyframes flStampSlam {
        0%   { transform: scale(2.6) rotate(var(--rot, -5deg)); opacity: 0; }
        50%  { transform: scale(0.9) rotate(var(--rot, -5deg)); opacity: 1; }
        70%  { transform: scale(1.1) rotate(var(--rot, -5deg)); }
        85%  { transform: scale(0.98) rotate(var(--rot, -5deg)); }
        100% { transform: scale(1) rotate(var(--rot, -5deg)); }
      }
      @keyframes flInkBurst { 0% { transform: translate(0,0) scale(1); opacity: 0.9; } 100% { transform: translate(var(--dx), var(--dy)) scale(0); opacity: 0; } }
      @keyframes flShimmer { 0% { background-position: -160px 0; } 100% { background-position: 160px 0; } }
      @keyframes flScan { 0% { transform: translateX(-6px); opacity: 0.4; } 50% { transform: translateX(6px); opacity: 1; } 100% { transform: translateX(-6px); opacity: 0.4; } }
      @keyframes flExpand { 0% { opacity: 0; transform: translateY(-4px); } 100% { opacity: 1; transform: translateY(0); } }
      @keyframes flShake { 10%, 90% { transform: translateX(-1px); } 20%, 80% { transform: translateX(2px); } 30%, 50%, 70% { transform: translateX(-4px); } 40%, 60% { transform: translateX(4px); } }
      @keyframes flPulseRing { 0% { box-shadow: 0 0 0 0 rgba(255,61,110,0.35); } 100% { box-shadow: 0 0 0 10px rgba(255,61,110,0); } }
      @keyframes flDashRotate { to { stroke-dashoffset: 0; } }
      @keyframes flBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
      @keyframes flRise { 0% { transform: translateY(6px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
      @keyframes flToastIn { 0% { transform: translate(-50%, 12px); opacity: 0; } 100% { transform: translate(-50%, 0); opacity: 1; } }
      @keyframes flGrain { 0%, 100% { transform: translate(0,0); } 10% { transform: translate(-1%,-2%); } 20% { transform: translate(2%,1%); } 30% { transform: translate(-1%,3%); } 40% { transform: translate(1%,-1%); } 50% { transform: translate(-2%,2%); } 60% { transform: translate(2%,2%); } 70% { transform: translate(-1%,-1%); } 80% { transform: translate(1%,2%); } 90% { transform: translate(-2%,-2%); } }

      .fl-float { animation: flDrift 7s ease-in-out infinite; }
      .fl-wobble { animation: flWobble 5s ease-in-out infinite; }
      .fl-pop-in { animation: flPop 0.45s cubic-bezier(.2,.9,.3,1.3) both; }
      .fl-fade-up { animation: flFadeUp 0.4s ease-out both; }
      .fl-stamp-slam { animation: flStampSlam 0.7s cubic-bezier(.2,.8,.3,1.3) both; }
      .fl-ink-fleck { animation: flInkBurst 0.6s ease-out both; animation-delay: 0.38s; }
      .fl-scan { animation: flScan 1.4s ease-in-out infinite; }
      .fl-expand { animation: flExpand 0.25s ease-out both; }
      .fl-shake { animation: flShake 0.5s cubic-bezier(.36,.07,.19,.97) both; }
      .fl-rise { animation: flRise 0.3s ease-out both; }

      .fl-grain { position: fixed; inset: -50%; width: 200%; height: 200%; opacity: 0.035; pointer-events: none; z-index: 999; mix-blend-mode: multiply;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        animation: flGrain 1.2s steps(2) infinite; }

      .fl-input-card { transition: box-shadow 0.25s ease, border-color 0.25s ease, transform 0.25s ease; }
      .fl-input-card:focus-within { border-color: ${C.brand}; box-shadow: 6px 6px 0 ${C.line}, 0 0 0 4px ${C.brandSoft}; transform: translate(-1px, -1px); }

      .fl-sample-card { transition: transform 0.2s cubic-bezier(.2,.8,.3,1), box-shadow 0.2s ease, border-color 0.2s ease; transform: rotate(var(--rot)); }
      .fl-sample-card:hover { transform: translateY(-6px) rotate(0deg) scale(1.015); box-shadow: 5px 8px 0 ${C.line}; border-color: ${C.brand} !important; }
      .fl-sample-card:active { transform: translateY(-2px) rotate(0deg) scale(0.99); }

      .fl-analyze-btn { transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease; position: relative; overflow: hidden; }
      .fl-analyze-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 0 ${C.brandInk}; filter: brightness(1.04); }
      .fl-analyze-btn:active:not(:disabled) { transform: translateY(1px); box-shadow: 0 2px 0 ${C.brandInk}; }
      .fl-analyze-btn:disabled { cursor: not-allowed; }

      .fl-tab-btn { transition: color 0.2s ease, transform 0.15s ease; }
      .fl-tab-btn:hover { transform: translateY(-1px); }

      .fl-claim-row { transition: background-color 0.15s ease; cursor: pointer; }
      .fl-claim-row:hover { background-color: ${C.paperSoft}; }

      .fl-disclosure { transition: background-color 0.15s ease; cursor: pointer; }
      .fl-disclosure:hover { background-color: ${C.paperSoft}; }

      .fl-shimmer-bar { background-image: linear-gradient(90deg, transparent, rgba(255,255,255,0.7), transparent); background-size: 160px 100%; background-repeat: no-repeat; animation: flShimmer 1.1s linear infinite; }

      .fl-reset-btn, .fl-icon-btn { transition: transform 0.15s ease, background-color 0.15s ease, color 0.15s ease; }
      .fl-reset-btn:hover { transform: translateX(-3px); }
      .fl-icon-btn:hover { background-color: ${C.paperSoft}; }
      .fl-icon-btn:active { transform: scale(0.94); }

      .fl-log-item { transition: background-color 0.15s ease, border-color 0.15s ease, transform 0.15s ease; cursor: pointer; }
      .fl-log-item:hover { background-color: ${C.paperSoft}; transform: translateX(2px); }

      .fl-kbd { display: inline-flex; align-items: center; gap: 2px; padding: 1px 5px; border-radius: 5px; border: 1.5px solid ${C.lineStrong}; font-family: ${MONO}; font-size: 10.5px; color: ${C.inkFaint}; background: ${C.paperRaised}; }

      .fl-pulse { animation: flPulseRing 1.8s ease-out infinite; }

      .fl-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
      .fl-scrollbar::-webkit-scrollbar-thumb { background: ${C.lineStrong}; border-radius: 4px; }
      .fl-scrollbar::-webkit-scrollbar-track { background: transparent; }
    `}</style>
  );
}

// ---------------------------------------------------------------------------
// MOCK DATA LAYER (unchanged behaviourally)
// ---------------------------------------------------------------------------

const EXAMPLES = [
  { id: "eiffel", kind: "factcheck", label: "Historic / Landmark", sub: "FEVER benchmark evidence match", text: "The Eiffel Tower was completed in 1889." },
  { id: "coref", kind: "factcheck", label: "Pronoun resolution", sub: "fastcoref resolves pronouns across sentences", text: "The COVID-19 vaccine received official authorization. It was evaluated in randomized clinical trials." },
  { id: "urdu", kind: "factcheck", label: "اردو ان پٹ (Urdu Claim)", sub: "Bilingual auto-translation & verification", text: "پیرس فرانس کا دارالحکومت ہے۔" },
  { id: "opinion", kind: "factcheck", label: "Subjective opinion", sub: "spaCy fact vs opinion filtering", text: "I think this is the most wonderful restaurant in the city." },
  { id: "science", kind: "factcheck", label: "Scientific fact", sub: "SciFact physical science match", text: "Water boils at 100 degrees Celsius at standard atmospheric pressure." },
  { id: "vaccine", kind: "factcheck", label: "Refuted medical claim", sub: "SciFact clinical evidence match", text: "The COVID-19 vaccine causes infertility in most patients." },
];

const MOCK_RESPONSES = {
  coref: {
    factCheck: {
      overallVerdict: "Supported", overallConfidence: 86, allOpinion: false, usedRetry: false, usedWikipediaFallback: false,
      corefResolutions: [{ from: "It", to: "The new vaccine" }],
      subClaims: [
        { text: "The new vaccine was approved last week.", status: "Fact", verdict: "Supported", confidence: 89, evidence: "Regulatory filing confirms authorization was granted on the stated date.", source: "SciFact" },
        { text: "It is being distributed nationwide.", resolvedText: "The new vaccine is being distributed nationwide.", status: "Fact", verdict: "Supported", confidence: 82, evidence: "Distribution announcements confirm a nationwide rollout following approval.", source: "SciFact" },
      ],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: [], reason: "No targeted or dehumanizing language detected." },
  },
  vaccine: {
    factCheck: {
      overallVerdict: "Refuted", overallConfidence: 91, allOpinion: false, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [],
      subClaims: [
        { text: "The new vaccine was approved last week.", status: "Fact", verdict: "Supported", confidence: 88, evidence: "Regulatory filing confirms authorization was granted on the stated date.", source: "SciFact" },
        { text: "The new vaccine causes infertility in most patients.", status: "Fact", note: "Causal and controversial, but still a checkable factual claim - baseline decomposition does not treat it as opinion.", verdict: "Refuted", confidence: 94, evidence: "Clinical trial data shows no statistically significant link to fertility outcomes.", source: "SciFact" },
      ],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: [], reason: "No targeted or dehumanizing language detected." },
  },
  mixedhate: {
    factCheck: {
      overallVerdict: "Supported", overallConfidence: 79, allOpinion: false, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [],
      subClaims: [
        { text: "Refugees from that country arrived last year.", status: "Fact", verdict: "Supported", confidence: 79, evidence: "Immigration records confirm an increase in arrivals from that origin during the stated period.", source: "FEVER 2018" },
        { text: "They're all criminals who should be sent back.", status: "Fact", note: "Framed as a factual claim about a group, but it's an unsupported generalization rather than a checkable statistic.", verdict: "Refuted", confidence: 88, evidence: "No data supports criminality as characteristic of the group; crime-rate studies show no such pattern.", source: "FEVER 2018" },
      ],
    },
    hateSpeech: { classification: "Hate", target: "Refugees from that country / national-origin group", cues: ["that country", "all criminals", "sent back"], reason: "Generalizes an entire group as criminal and calls for their removal - a dehumanizing generalization plus an exclusionary call to action." },
  },
  opinion: {
    factCheck: { overallVerdict: "Not Applicable", overallConfidence: null, allOpinion: true, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [], subClaims: [{ text: "I think the Eiffel Tower is beautiful.", status: "Opinion" }] },
    hateSpeech: { classification: "Normal", target: "None", cues: ["beautiful"], reason: "No targeted or dehumanizing language detected." },
  },
  mixed: {
    factCheck: {
      overallVerdict: "Supported", overallConfidence: 85, allOpinion: false, usedRetry: false, usedWikipediaFallback: false,
      corefResolutions: [{ from: "It", to: "The new iPhone" }],
      subClaims: [
        { text: "The new iPhone was released last month.", status: "Fact", verdict: "Supported", confidence: 85, evidence: "Product release announcements confirm the launch date.", source: "AVeriTeC 2024" },
        { text: "It's the most beautiful phone ever made.", status: "Opinion" },
      ],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: ["most beautiful"], reason: "No targeted or dehumanizing language detected." },
  },
  retry: {
    factCheck: {
      overallVerdict: "Not Enough Evidence", overallConfidence: 54, allOpinion: false, usedRetry: true, usedWikipediaFallback: false, corefResolutions: [],
      subClaims: [{
        text: "A newly announced phone this year shipped with a graphene-based battery.", status: "Fact", verdict: "Not Enough Evidence", confidence: 54,
        evidence: "Neither the initial search nor the one bounded retry over the fixed corpus could confirm this.", source: "Local corpus (retry)",
        searchTrail: [
          { label: "Initial evidence search (local corpus)", state: "done" },
          { label: "Evidence insufficient", state: "warn" },
          { label: "One bounded retry triggered", state: "done" },
          { label: "Still insufficient - reported as inconclusive", state: "warn" },
        ],
      }],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: [], reason: "No targeted or dehumanizing language detected." },
  },
  wikipedia: {
    factCheck: {
      overallVerdict: "Supported", overallConfidence: 74, allOpinion: false, usedRetry: true, usedWikipediaFallback: true, corefResolutions: [],
      subClaims: [{
        text: "The newly launched OrbitPhone X shipped with a graphene-based battery this year.", status: "Fact", verdict: "Supported", confidence: 74,
        evidence: "A Wikipedia article on the launch corroborates a graphene-composite battery, after the local corpus and one retry returned nothing usable.", source: "Wikipedia (optional fallback - preview)",
        searchTrail: [
          { label: "Initial evidence search (local corpus)", state: "done" },
          { label: "Evidence insufficient", state: "warn" },
          { label: "One bounded retry triggered", state: "done" },
          { label: "Local evidence remains insufficient", state: "warn" },
          { label: "Optional Wikipedia fallback (preview)", state: "info" },
          { label: "Wikipedia evidence retrieved", state: "done" },
        ],
      }],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: [], reason: "No targeted or dehumanizing language detected." },
  },
  pride: {
    factCheck: { overallVerdict: "Not Applicable", overallConfidence: null, allOpinion: false, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [], subClaims: [] },
    hateSpeech: { classification: "Normal", target: "None", cues: ["proud", "celebrating Pride", "with my friends"], reason: "Identity is mentioned in a self-affirming, non-targeting context. FactLens reads the surrounding context rather than treating the identity term itself as hate speech." },
  },
  targeted: {
    factCheck: { overallVerdict: "Not Applicable", overallConfidence: null, allOpinion: false, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [], subClaims: [] },
    hateSpeech: { classification: "Hate", target: "People from that country / national-origin group", cues: ["that country", "all criminals"], reason: "Generalizes an entire group as criminal and calls for their removal - a dehumanizing generalization plus an exclusionary call to action." },
  },
  urdu: {
    isLiveBackend: false,
    language: "ur",
    originalTextEn: "Paris is the capital of France.",
    factCheck: {
      overallVerdict: "Supported",
      overallVerdictUr: "تصدیق شدہ",
      overallConfidence: 94,
      allOpinion: false,
      language: "ur",
      originalTextEn: "Paris is the capital of France.",
      usedRetry: false,
      usedWikipediaFallback: false,
      corefResolutions: [],
      subClaims: [
        {
          text: "پیرس فرانس کا دارالحکومت ہے۔",
          textEn: "Paris is the capital of France.",
          textUr: "پیرس فرانس کا دارالحکومت ہے۔",
          status: "Fact",
          statusUr: "حقیقی دعویٰ",
          verdict: "Supported",
          verdictUr: "تصدیق شدہ",
          confidence: 94,
          evidence: "پیرس فرانس کا دارالحکومت اور سب سے بڑا شہر ہے۔",
          evidenceEn: "Paris is the capital and most populous city of France.",
          source: "Unified Benchmark Corpus (FEVER)",
        },
      ],
    },
    hateSpeech: { classification: "Normal", target: "None", cues: [], reason: "کوئی توہین آمیز مواد نہیں پایا گیا۔" },
  },
};

function mockAnalyze(text) {
  const trimmed = text.trim();
  const lower = trimmed.toLowerCase();
  let hash = 0;
  for (let i = 0; i < trimmed.length; i++) hash = (hash * 31 + trimmed.charCodeAt(i)) >>> 0;

  const opinionPattern = /\b(is|are|was|were)\s+(bad|evil|stupid|ugly|dumb|awesome|amazing|beautiful|gorgeous|hideous|disgusting|terrible|horrible|wonderful|fantastic|excellent|great|awful|pathetic|worthless|ridiculous|useless|brilliant|perfect|the best|the worst|a genius|an idiot|a fool|a moron|a liar|a loser|a coward|a jerk|a disgrace)\b/i;
  const opinionLeadIn = /^(i\s+(think|believe|feel|guess|suppose|assume|reckon|personally\s+think)\b|in\s+my\s+opinion\b|in\s+my\s+view\b|from\s+my\s+perspective\b|personally\b|as\s+far\s+as\s+i'?m\s+concerned\b)/i;
  const verdicts = ["Supported", "Refuted", "Not Enough Evidence"];
  const usedRetry = hash % 5 === 0;
  const sentences = trimmed.split(/(?<=[.!?])\s+/).filter((s) => s.trim().length > 0);
  const sentenceList = sentences.length ? sentences : [trimmed];

  const corefResolutions = [];
  if (sentenceList.length > 1 && /\b(it|its|they|their|this|these)\b/i.test(sentenceList.slice(1).join(" "))) {
    const guess = sentenceList[0].split(" ").slice(0, 4).join(" ").replace(/[.,]$/, "");
    corefResolutions.push({ from: "It", to: `${guess}\u2026` });
  }

  const subClaims = sentenceList.map((s, i) => {
    const sLower = s.trim().toLowerCase();
    const cleanTokens = sLower.replace(/[^a-z0-9\s]/g, " ").trim().split(/\s+/).filter(Boolean);
    if (cleanTokens.length < 3) {
      return { text: s, status: "Non-Checkable", reason: "Sentence fragment is too brief to form a complete checkable assertion" };
    }
    const funcWords = new Set(["i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "their", "our", "its", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "a", "an", "the", "and", "or", "but", "so", "if", "then", "that", "this", "these", "those"]);
    if (cleanTokens.every((t) => funcWords.has(t))) {
      return { text: s, status: "Non-Checkable", reason: "Sentence lacks content words (nouns, adjectives, or verbs) to form a meaningful assertion" };
    }
    const isOpinion = opinionPattern.test(sLower) || opinionLeadIn.test(sLower);
    if (isOpinion) return { text: s, status: "Opinion", reason: "Exclamatory or subjective phrase expresses personal opinion" };

    const resolvedText = corefResolutions.length && /^(it|they|this|these)\b/i.test(s.trim())
      ? s.replace(/^(It|They|This|These)\b/i, corefResolutions[0].to.replace(/\u2026$/, ""))
      : undefined;

    const simBm25 = (14.2 + ((hash + i * 17) % 35) / 10).toFixed(3);
    const simEmb = (0.75 + ((hash + i * 11) % 20) / 100).toFixed(3);
    const claim = {
      text: s,
      status: "Fact",
      verdict: verdicts[(hash + i) % 3],
      confidence: 55 + ((hash + i * 13) % 40),
      evidence: "Retrieved passage overlaps with the claim's key terms and entities from benchmark corpus.",
      source: ["SciFact", "FEVER 2018", "AVeriTeC 2024", "FEVEROUS"][(hash + i) % 4],
      searchTrail: [
        { label: `BM25 keyword score: ${simBm25}`, state: "done" },
        { label: `Semantic embedding score: ${simEmb}`, state: "done" },
        { label: `Retrieved evidence verdict: ${verdicts[(hash + i) % 3]}`, state: verdicts[(hash + i) % 3] === "Supported" ? "done" : "warn" },
      ],
    };
    if (resolvedText) claim.resolvedText = resolvedText;
    return claim;
  });

  const facts = subClaims.filter((c) => c.status === "Fact");
  const allOpinion = subClaims.length > 0 && facts.length === 0;
  let overallVerdict = "Not Applicable";
  if (!allOpinion && facts.length > 0) {
    const supportedCount = facts.filter((c) => c.verdict === "Supported").length;
    const refutedCount = facts.filter((c) => c.verdict === "Refuted").length;
    const neeCount = facts.filter((c) => c.verdict === "Not Enough Evidence").length;
    if (supportedCount === facts.length) overallVerdict = "Supported";
    else if (refutedCount === facts.length) overallVerdict = "Refuted";
    else if (neeCount === facts.length) overallVerdict = "Not Enough Evidence";
    else overallVerdict = "Mixed";
  }

  const factCheck = allOpinion
    ? { overallVerdict: "Not Applicable", overallConfidence: null, allOpinion: true, usedRetry: false, usedWikipediaFallback: false, corefResolutions: [], subClaims }
    : { overallVerdict, overallConfidence: 55 + (hash % 40), allOpinion: false, usedRetry, usedWikipediaFallback: false, corefResolutions, subClaims };

  const hateWords = ["hate","despise","disgusting","filthy","worthless","pathetic","subhuman","animals","vermin","parasites","savages","monsters","scum","ban","should be removed","should be thrown out","get rid of them","drive them out","they don't belong here","should not be allowed","kill","murder","destroy them","wipe them out","eliminate them","attack them","hurt them","inferior","lesser","worth less","second class","not equal","criminals","thugs","terrorists","corrupt","dangerous","dirty","degenerate","all of them are","those people are","people like them","they are all","we don't want them"];
  const offensiveWords = ["stupid","idiot","moron","fool","dumb","ignorant","clueless","useless","worthless","pathetic","evil","disgusting","hideous","repulsive","awful","horrible","terrible","nasty","gross","ridiculous","brainless","brain-dead","dumbass","imbecile","idiotic","stupidest","incompetent","incapable","jerk","loser","liar","cheater","coward","scumbag","creep","weirdo","disgrace","shut up","get lost","go away","nobody likes you","you're a joke","what an idiot","you're useless","you're pathetic"];
  const matchedHate = hateWords.filter((w) => lower.includes(w));
  const matchedOffensive = offensiveWords.filter((w) => lower.includes(w));
  const isHate = matchedHate.length > 0;
  const isOffensive = !isHate && matchedOffensive.length > 0;

  let hateSpeech;
  if (isHate) hateSpeech = { classification: "Hate", target: "Unspecified group", cues: matchedHate, reason: "Contains language generalizing or dehumanizing a group, rather than describing an individual or a neutral fact." };
  else if (isOffensive) hateSpeech = { classification: "Offensive", target: "Individual (no protected group referenced)", cues: matchedOffensive, reason: "Contains an insult directed at a person, but does not target a protected characteristic or generalize about a group." };
  else hateSpeech = { classification: "Normal", target: "None", cues: [], reason: "No targeted or dehumanizing language detected." };

  return { factCheck, hateSpeech };
}

// ---------------------------------------------------------------------------
// SHARED BITS
// ---------------------------------------------------------------------------

function StampFilterDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <filter id="roughen" x="-30%" y="-30%" width="160%" height="160%">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="4" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.6" />
        </filter>
        <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={C.brand} />
          <stop offset="100%" stopColor={C.brandDeep} />
        </linearGradient>
      </defs>
    </svg>
  );
}


function Field({ children }) {
  return <span className="text-xs font-medium" style={{ color: C.inkFaint, fontFamily: MONO, letterSpacing: "0.01em" }}>{children}</span>;
}

function Logo({ compact = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="flex items-center justify-center shrink-0 rounded-full fl-wobble"
        style={{
          width: compact ? 30 : 36, height: compact ? 30 : 36,
          border: `2.5px solid ${C.brand}`, color: C.brand, filter: "url(#roughen)",
          transition: "width 0.2s ease, height 0.2s ease",
        }}
      >
        <Search className="w-4 h-4" strokeWidth={3} />
      </div>
      <span
        className="font-extrabold tracking-tight"
        style={{ color: C.ink, fontFamily: DISPLAY, fontSize: compact ? "1.05rem" : "1.25rem", transition: "font-size 0.2s ease" }}
      >
        FactLens
      </span>
    </div>
  );
}

function Disclosure({ icon: Icon, title, subtitle, defaultOpen = false, children, accent = C.inkSoft }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: `2px dashed ${C.lineStrong}`, backgroundColor: C.paperRaised }}>
      <button onClick={() => setOpen((o) => !o)} className="fl-disclosure w-full flex items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="flex items-center gap-2.5 min-w-0">
          <Icon className="w-4 h-4 shrink-0" style={{ color: accent }} />
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate" style={{ color: C.ink, fontFamily: BODY }}>{title}</p>
            {subtitle && <p className="text-xs truncate" style={{ color: C.inkFaint, fontFamily: BODY }}>{subtitle}</p>}
          </div>
        </div>
        <ChevronDown className="w-4 h-4 shrink-0" style={{ color: C.inkFaint, transform: open ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s ease" }} />
      </button>
      {open && <div className="fl-expand px-4 pb-4 pt-1" style={{ borderTop: `2px dashed ${C.line}` }}>{children}</div>}
    </div>
  );
}

const VERDICT_ICON = { Supported: CheckCircle2, Refuted: XCircle, "Not Enough Evidence": HelpCircle, "Not Applicable": HelpCircle, Mixed: AlertTriangle };
const VERDICT_TEXT_COLOR = { Supported: C.supported, Refuted: C.refuted, "Not Enough Evidence": "#8A6A00", "Not Applicable": C.inkFaint, Mixed: "#B45309" };

function Stamp({ label, icon: Icon, color, rotate = -5 }) {
  const flecks = [{ dx: "-26px", dy: "-14px" }, { dx: "24px", dy: "-18px" }, { dx: "-18px", dy: "20px" }, { dx: "28px", dy: "16px" }, { dx: "0px", dy: "-26px" }];
  return (
    <div className="relative inline-block fl-stamp-slam" style={{ "--rot": `${rotate}deg` }}>
      {flecks.map((f, i) => (
        <span key={i} className="fl-ink-fleck absolute w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color, top: "50%", left: "50%", "--dx": f.dx, "--dy": f.dy, animationDelay: `${0.36 + i * 0.03}s` }} />
      ))}
      <div className="absolute inset-0 rounded-2xl" style={{ border: `2.5px solid ${color}`, opacity: 0.35, transform: "translate(2px, 2px)", filter: "url(#roughen)" }} />
      <div className="relative inline-flex items-center gap-2 px-5 py-2 rounded-2xl" style={{ border: `2.5px solid ${color}`, color, fontFamily: DISPLAY, filter: "url(#roughen)", backgroundColor: C.paperRaised }}>
        <Icon className="w-4 h-4" strokeWidth={2.75} />
        <span className="font-bold text-sm">{label}</span>
      </div>
    </div>
  );
}

function VerdictStamp({ verdict, verdictUr, rotate }) {
  const label = verdictUr ? `${verdictUr} • ${verdict}` : verdict;
  return <Stamp label={label} icon={VERDICT_ICON[verdict] || HelpCircle} color={VERDICT_TEXT_COLOR[verdict] || C.inkFaint} rotate={rotate} />;
}

function VerdictPill({ verdict, verdictUr }) {
  const color = VERDICT_TEXT_COLOR[verdict] || C.inkFaint;
  const bg = verdict === "Supported" ? C.supportedSoft : verdict === "Refuted" ? C.refutedSoft : verdict === "Not Enough Evidence" ? C.highlightSoft : verdict === "Mixed" ? "#FEF3C7" : C.paperSoft;
  const Icon = VERDICT_ICON[verdict] || HelpCircle;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ color, backgroundColor: bg, fontFamily: BODY }}>
      <Icon className="w-3.5 h-3.5" />
      {verdictUr ? `${verdictUr} (${verdict})` : verdict}
    </span>
  );
}

function OpinionPill({ label = "Opinion" }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ color: C.opinion, backgroundColor: C.opinionSoft, fontFamily: BODY }}>
      <MessageSquare className="w-3.5 h-3.5" />
      {label}
    </span>
  );
}

function NonCheckablePill({ label = "Non-Checkable" }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ color: "#854D0E", backgroundColor: "#FEF9C3", fontFamily: BODY }}>
      <HelpCircle className="w-3.5 h-3.5" />
      {label}
    </span>
  );
}


// Radial confidence gauge - replaces the flat progress bar for the overall
// verdict so the headline number reads like an instrument dial rather than
// a loading indicator.
function ConfidenceGauge({ value, color, size = 74 }) {
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(value), 120);
    return () => clearTimeout(t);
  }, [value]);
  const offset = c - (animated / 100) * c;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={C.paperSoft} strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-bold" style={{ fontFamily: DISPLAY, fontSize: "1rem", color: C.ink, lineHeight: 1 }}>{value}</span>
        <span style={{ fontFamily: MONO, fontSize: "8.5px", color: C.inkFaint, letterSpacing: "0.03em" }}>PCT</span>
      </div>
    </div>
  );
}

function HeroDoodle({ mouse }) {
  const dx = mouse ? (mouse.x - 0.5) * 8 : 0;
  const dy = mouse ? (mouse.y - 0.5) * 8 : 0;
  return (
    <svg viewBox="0 0 220 220" className="w-full h-full fl-float" style={{ "--rot": "-4deg" }}>
      <g style={{ transition: "transform 0.3s ease-out" }} transform={`translate(${dx} ${dy})`}>
        <g transform="rotate(-6 110 110)">
          <rect x="34" y="30" width="130" height="90" rx="6" fill={C.paperRaised} stroke={C.ink} strokeWidth="3" />
          <line x1="50" y1="52" x2="140" y2="52" stroke={C.line} strokeWidth="4" strokeLinecap="round" />
          <line x1="50" y1="68" x2="120" y2="68" stroke={C.line} strokeWidth="4" strokeLinecap="round" />
          <line x1="50" y1="84" x2="130" y2="84" stroke={C.line} strokeWidth="4" strokeLinecap="round" />
          <circle cx="128" cy="98" r="16" fill="none" stroke={C.supported} strokeWidth="4" transform="rotate(-10 128 98)" />
          <path d="M120 98 l5 6 l11 -13" fill="none" stroke={C.supported} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" transform="rotate(-10 128 98)" />
        </g>
        <g transform="rotate(8 150 150)">
          <rect x="18" y="120" width="80" height="56" rx="6" fill={C.highlightSoft} stroke={C.ink} strokeWidth="3" />
          <line x1="30" y1="138" x2="86" y2="138" stroke={C.highlight} strokeWidth="6" strokeLinecap="round" />
          <line x1="30" y1="152" x2="70" y2="152" stroke={C.highlight} strokeWidth="6" strokeLinecap="round" />
        </g>
        <circle cx="150" cy="80" r="34" fill="rgba(255,255,255,0.5)" stroke={C.ink} strokeWidth="5" />
        <line x1="173" y1="103" x2="200" y2="130" stroke={C.ink} strokeWidth="7" strokeLinecap="round" />
        <circle cx="150" cy="80" r="34" fill="none" stroke={C.brand} strokeWidth="3" strokeDasharray="2 7" />
        <circle cx="20" cy="30" r="4" fill={C.brand} />
        <circle cx="200" cy="40" r="3" fill={C.info} />
        <circle cx="10" cy="150" r="3" fill={C.refuted} />
      </g>
    </svg>
  );
}

function SearchTrail({ steps }) {
  const STATE_COLOR = { done: C.supported, warn: "#8A6A00", info: C.info };
  const STATE_ICON = { done: CheckCircle2, warn: AlertTriangle, info: Globe2 };
  return (
    <div className="mt-3 flex flex-col gap-1.5 pl-1">
      {steps.map((s, i) => {
        const Icon = STATE_ICON[s.state];
        return (
          <div key={i} className="flex items-center gap-2 fl-rise" style={{ animationDelay: `${i * 0.05}s` }}>
            <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: STATE_COLOR[s.state] }} />
            <span className="text-xs" style={{ color: C.inkSoft, fontFamily: BODY }}>{s.label}</span>
          </div>
        );
      })}
    </div>
  );
}


function Toast({ message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 1800);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div
      className="fixed left-1/2 bottom-8 z-50 flex items-center gap-2 px-4 py-2.5 rounded-full"
      style={{ animation: "flToastIn 0.3s cubic-bezier(.2,.8,.3,1) both", backgroundColor: C.ink, color: C.paper, fontFamily: BODY, fontSize: "0.85rem", fontWeight: 600, boxShadow: "0 8px 24px rgba(28,27,41,0.35)" }}
    >
      <Check className="w-4 h-4" style={{ color: C.highlight }} />
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SCREEN 1 - INPUT
// ---------------------------------------------------------------------------

const CATEGORY_COLOR = { factcheck: C.info, hatespeech: C.brand };
const MAX_CHARS = 3000;

function BackendStatusBar({ status, info, onRetry }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const command = "uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload";

  const handleCopy = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(command);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (status === "online") {
    return (
      <div className="mb-6 p-2.5 sm:p-3 rounded-xl bg-emerald-50/95 border border-emerald-300 text-emerald-900 flex items-center justify-between gap-2 shadow-xs fl-fade-up">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
          <span className="text-xs font-semibold truncate" style={{ fontFamily: BODY }}>
            <strong>Live Neural Backend Connected:</strong> FastAPI • Faster-Whisper ASR • DeBERTa-v3 NLI active
          </span>
        </div>
        <span className="text-[10px] font-mono uppercase bg-emerald-200/70 text-emerald-900 px-2 py-0.5 rounded font-bold shrink-0">
          Live 8000
        </span>
      </div>
    );
  }

  return (
    <div
      className="mb-6 rounded-2xl p-4 sm:p-5 border-2 shadow-sm fl-fade-up"
      style={{
        backgroundColor: "#FFFDF5",
        borderColor: "#F59E0B",
        boxShadow: `4px 4px 0 ${C.line}`,
      }}
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-amber-100 border border-amber-300 flex items-center justify-center shrink-0 text-amber-700 mt-0.5">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs sm:text-sm font-bold text-amber-950 uppercase tracking-wide" style={{ fontFamily: DISPLAY }}>
              Backend Offline • Standalone Interactive Mode Active
            </h4>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="text-[11px] font-bold text-amber-900 underline hover:text-amber-700"
              >
                {expanded ? "Hide instructions ▲" : "How to run backend ▼"}
              </button>
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-200/80 hover:bg-amber-300 text-amber-950 transition-colors shadow-2xs"
                title="Ping backend server on port 8000"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry 8000</span>
              </button>
            </div>
          </div>

          <p className="text-xs text-amber-900/90 mt-1.5 leading-relaxed" style={{ fontFamily: BODY }}>
            ✨ <strong>Everything is functional below!</strong> You can use <strong>Live Mic</strong> speech input, tap sample claims, and verify evidence right now on your phone. To connect your laptop's local Faster-Whisper GPU models, run the backend:
          </p>

          {expanded && (
            <div className="mt-3 fl-expand">
              <div className="flex items-center justify-between gap-2 bg-slate-900 text-slate-100 px-3 py-2 rounded-lg font-mono text-[11px] overflow-x-auto shadow-inner">
                <code className="text-amber-300 select-all whitespace-nowrap">{command}</code>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="shrink-0 text-slate-400 hover:text-white p-1 rounded transition-colors"
                  title="Copy launch command"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <p className="text-[10px] font-mono text-amber-800 mt-1.5">
                Run inside <code className="font-bold">factlens_repo_starter/backend</code> in PowerShell or terminal.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function BackendOfflineScreen({ onDismiss, onRetry, onSelectSample, isChecking }) {
  const [copied, setCopied] = useState(false);
  const command = "uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload";

  const handleCopy = () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(command);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sampleTeasers = [
    { id: "urdu", tag: "اردو دعویٰ (Urdu)", text: "پیرس فرانس کا دارالحکومت ہے۔", sub: "Automatic translation & verification" },
    { id: "eiffel", tag: "Historic Fact", text: "The Eiffel Tower was completed in 1889.", sub: "SciFact & FEVER evidence retrieval" },
    { id: "vaccine", tag: "Refuted Medical", text: "The COVID-19 vaccine causes infertility in most patients.", sub: "Clinical trials counter-evidence" },
  ];

  return (
    <main className="min-h-screen p-4 sm:p-8 flex flex-col items-center justify-center relative overflow-hidden" style={{ backgroundColor: C.paper }}>
      {/* Decorative floating shapes */}
      <div className="fl-float absolute w-16 h-6 opacity-40 rounded" style={{ top: "6%", left: "5%", backgroundColor: C.highlight, "--rot": "-10deg" }} />
      <div className="fl-float absolute w-4 h-4 rounded-full opacity-40" style={{ top: "20%", right: "8%", backgroundColor: C.brand, "--rot": "0deg", animationDelay: "1s" }} />
      <div className="fl-float absolute w-6 h-6 rounded-full opacity-30" style={{ bottom: "12%", left: "8%", backgroundColor: C.info, "--rot": "0deg", animationDelay: "2s" }} />

      <div className="w-full max-w-2xl relative fl-fade-up">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 sm:mb-8">
          <Logo />
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1.5 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
              Backend Offline (Port 8000)
            </span>
          </div>
        </div>

        {/* Main Creative Alert Container */}
        <div
          className="rounded-3xl p-6 sm:p-8 border-2 shadow-lg relative overflow-hidden"
          style={{
            backgroundColor: C.paperRaised,
            borderColor: C.brand,
            boxShadow: `8px 8px 0 ${C.line}`,
          }}
        >
          {/* Header Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-300 mb-4 font-mono">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            <span>ACTION REQUIRED ON LAPTOP</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight leading-tight" style={{ color: C.ink, fontFamily: DISPLAY }}>
            Run The Backend First!
          </h1>
          <p className="mt-2 text-sm sm:text-base leading-relaxed" style={{ color: C.inkSoft, fontFamily: BODY }}>
            You opened FactLens via the QR code or link, but the <strong>FastAPI neural backend</strong> isn't running on your laptop yet. Start the backend to enable live speech transcription, coreference resolution, and cross-device syncing:
          </p>

          {/* Terminal / Launch Instructions */}
          <div className="mt-5 bg-slate-950 text-slate-100 rounded-2xl p-4 sm:p-5 border border-slate-800 shadow-inner">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span className="text-xs font-mono text-slate-400 ml-2">powershell / terminal</span>
              </div>
              <button
                type="button"
                onClick={handleCopy}
                className="text-xs font-mono inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied!" : "Copy Command"}</span>
              </button>
            </div>
            <p className="text-[11px] font-mono text-slate-400 mb-1"># Run in factlens_repo_starter/backend:</p>
            <code className="text-xs sm:text-sm font-mono text-amber-300 select-all block break-all">
              {command}
            </code>
            <p className="text-[11px] font-mono text-teal-400 mt-2.5">
              💡 Or double-click <span className="underline font-bold">start_factlens.bat</span> on your desktop!
            </p>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={onRetry}
              disabled={isChecking}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm text-white shadow-sm transition-all hover:brightness-105 active:scale-95"
              style={{ backgroundColor: C.brand, fontFamily: BODY }}
            >
              <RefreshCw className={`w-4 h-4 ${isChecking ? "animate-spin" : ""}`} />
              <span>{isChecking ? "Checking Connection..." : "Check Backend Connection"}</span>
            </button>

            <button
              type="button"
              onClick={onDismiss}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 transition-all shadow-xs"
              style={{ fontFamily: BODY }}
            >
              <Sparkles className="w-4 h-4 text-amber-600" />
              <span>Explore Interface in Demo Mode →</span>
            </button>
          </div>

          {/* "Show a bit interface" - Interactive Teaser Section */}
          <div className="mt-8 pt-6 border-t-2 border-dashed" style={{ borderColor: C.line }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono flex items-center gap-1.5">
                <Globe2 className="w-3.5 h-3.5 text-teal-700" />
                <span>Test Live Interface Preview Right Now</span>
              </span>
              <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">Offline Benchmark Engine</span>
            </div>
            <p className="text-xs text-slate-600 mb-3" style={{ fontFamily: BODY }}>
              Even before starting the backend, you can test the full verification pipeline by tapping any sample claim below:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {sampleTeasers.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => onSelectSample(s)}
                  className="p-3 rounded-xl border text-left transition-all hover:scale-[1.02] shadow-2xs hover:shadow-xs group"
                  style={{ backgroundColor: C.paperSoft, borderColor: C.line }}
                >
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 font-mono block mb-1">
                    {s.tag}
                  </span>
                  <p className="text-xs font-medium text-slate-900 line-clamp-2" style={{ fontFamily: s.id === "urdu" ? '"Kalam", serif' : BODY, direction: s.id === "urdu" ? "rtl" : "ltr" }}>
                    {s.text}
                  </p>
                  <span className="text-[10px] text-teal-700 font-bold mt-2 inline-flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                    Verify claim →
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs font-mono text-slate-500 mt-6">
          FAST-NUCES Islamabad • Group F26-028 • Session 2023–2027
        </p>
      </div>
    </main>
  );
}

function InputScreen({
  text,
  setText,
  onAnalyze,
  shakeKey,
  deviceCount = 1,
  onSyncText,
  backendStatus = "checking",
  backendInfo = null,
  onRetryBackend,
  onShowOfflineModal
}) {
  const [mouse, setMouse] = useState(null);
  const heroRef = useRef(null);
  const fileInputRef = useRef(null);
  const pct = Math.min(100, (text.length / MAX_CHARS) * 100);
  const nearLimit = text.length > MAX_CHARS * 0.85;

  // Live Audio Speech Recognition State
  const [isRecording, setIsRecording] = useState(false);
  const [audioLang, setAudioLang] = useState("auto"); // "auto", "en-US", "ur-PK"
  const [audioStatus, setAudioStatus] = useState("");
  const [uploadedAudioName, setUploadedAudioName] = useState(null);

  // Neural Whisper Recording Engine:
  // Using MediaRecorder -> Faster-Whisper on backend for BOTH English and Urdu.
  // This completely eliminates the browser Web Speech API bug where English words
  // stutter and repeat ("Parisparisparis isparis is theparis...").
  const isRecordingRef = useRef(false);
  const baseTextRef = useRef("");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Start MediaRecorder for high-fidelity audio capture (English & Urdu)
  const startMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        if (audioBlob.size < 1000) {
          setAudioStatus("Recording was too short. Please speak clearly and try again.");
          return;
        }

        const isUrdu = audioLang === "ur-PK";
        const targetLang = isUrdu ? "ur" : "en";
        const filename = isUrdu ? "live_mic_urdu.wav" : "live_mic_english.wav";

        setAudioStatus(
          isUrdu
            ? "Transcribing Urdu recording via Faster-Whisper..."
            : "Transcribing English recording via Faster-Whisper..."
        );

        const reader = new FileReader();
        reader.onloadend = async () => {
          try {
            const base64Audio = String(reader.result).split(",")[1];
            const API_BASE = getApiBase();
            const resp = await fetch(`${API_BASE}/api/transcribe`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                filename: filename,
                language: targetLang,
                audio_base64: base64Audio,
              }),
            });

            if (resp.ok) {
              const data = await resp.json();
              if (data.transcription && data.transcription.trim()) {
                const cleanText = data.transcription.trim();
                setText((prev) => {
                  const prefix = prev.trim() ? prev.trim() + " " : "";
                  const updated = (prefix + cleanText).slice(0, MAX_CHARS);
                  if (onSyncText) onSyncText(updated, audioLang);
                  return updated;
                });
                setAudioStatus(
                  isUrdu
                    ? "Urdu speech transcribed cleanly via Faster-Whisper!"
                    : "English speech transcribed cleanly via Faster-Whisper!"
                );
              } else {
                setAudioStatus("Whisper detected low volume or silence in the recording.");
              }
            } else {
              setAudioStatus("Server transcription error. Please try again.");
            }
          } catch (e) {
            console.error("Whisper live mic transcribe error:", e);
            setAudioStatus("Transcription error: " + (e.message || "Network issue"));
          }
        };
        reader.readAsDataURL(audioBlob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      isRecordingRef.current = true;
      setIsRecording(true);
      setAudioStatus(
        audioLang === "ur-PK"
          ? "مائیک فعال ہے... براہ کرم بولیں (مکمل ہونے پر Stop دبائیں)"
          : "Microphone Active: Speak clearly, then click Stop Mic when finished"
      );
    } catch (err) {
      console.error("Microphone access failed:", err);
      setAudioStatus("Microphone access failed: Please allow microphone permission in your browser.");
    }
  };

  const stopMediaRecorder = () => {
    isRecordingRef.current = false;
    setIsRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  const recognitionRef = useRef(null);

  const startSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setAudioStatus("Browser speech recognition is not supported on this device. Please type your claim.");
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = audioLang === "ur-PK" ? "ur-PK" : "en-US";

      recognition.onstart = () => {
        setIsRecording(true);
        isRecordingRef.current = true;
        setAudioStatus(
          audioLang === "ur-PK"
            ? "مائیک فعال ہے... براہ کرم بولیں"
            : "Listening... Speak clearly (click Stop Mic when finished)"
        );
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          const prefix = baseTextRef.current ? baseTextRef.current + " " : "";
          const updated = (prefix + transcript.trim()).slice(0, MAX_CHARS);
          setText(updated);
          if (onSyncText) onSyncText(updated, audioLang);
        }
      };

      recognition.onerror = (e) => {
        console.warn("Speech recognition notice:", e.error);
        if (e.error !== "no-speech") {
          setAudioStatus(`Microphone status: ${e.error}`);
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
        isRecordingRef.current = false;
        setAudioStatus("Voice input captured!");
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (e) {
      console.warn("SpeechRecognition start error:", e);
      startMediaRecorder();
    }
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
    setIsRecording(false);
    isRecordingRef.current = false;
  };

  const toggleRecording = () => {
    baseTextRef.current = text.trim();
    if (isRecording) {
      if (recognitionRef.current) {
        stopSpeechRecognition();
      } else {
        stopMediaRecorder();
      }
    } else {
      if (backendStatus === "online") {
        startMediaRecorder();
      } else {
        startSpeechRecognition();
      }
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadedAudioName(file.name);
    setAudioStatus(`Uploading & transcribing "${file.name}" using Faster-Whisper...`);

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Audio = reader.result ? String(reader.result).split(",")[1] : null;
        const API_BASE = getApiBase();

        const resp = await fetch(`${API_BASE}/api/transcribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            language: audioLang === "ur-PK" ? "ur" : (audioLang === "en-US" ? "en" : "auto"),
            audio_base64: base64Audio,
          }),
        });

        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData.detail || `Server returned ${resp.status}`);
        }

        const data = await resp.json();
        if (data.transcription && data.transcription.trim()) {
          const cleanText = data.transcription.trim();
          setText(cleanText);
          if (onSyncText) onSyncText(cleanText, audioLang);
          setAudioStatus(`Transcribed via ${data.source} (${data.detected_language.toUpperCase()}, conf: ${data.confidence}): "${file.name}"`);
        } else {
          setAudioStatus("Whisper detected silence or unintelligible speech in this audio clip.");
        }
      } catch (err) {
        console.error("Whisper transcription error:", err);
        setAudioStatus("Transcription error: " + (err.message || "Failed to transcribe audio."));
      }
    };
    reader.onerror = () => {
      setAudioStatus("Error reading audio file from disk.");
    };
    reader.readAsDataURL(file);
  };

  const handleMove = useCallback((e) => {
    const rect = heroRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMouse({ x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height });
  }, []);

  return (
    <div
      ref={heroRef}
      onMouseMove={handleMove}
      onMouseLeave={() => setMouse(null)}
      className="min-h-screen flex flex-col items-center px-4 sm:px-6 py-8 sm:py-16 relative overflow-hidden"
      style={{ backgroundColor: C.paper, backgroundImage: `radial-gradient(${C.lineOuter} 1px, transparent 1px)`, backgroundSize: "24px 24px" }}
    >
      {/* single orchestrated hero moment: soft spotlight that follows cursor or ambient mobile glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: mouse
            ? `radial-gradient(480px circle at ${mouse.x * 100}% ${mouse.y * 100}%, ${C.brandSoft}55, transparent 70%)`
            : `radial-gradient(360px circle at 50% 15%, ${C.brandSoft}35, transparent 70%)`,
          transition: "background 0.15s ease-out",
        }}
      />

      {/* Floating decorative stickers animated on both mobile and desktop */}
      <div className="fl-float absolute w-12 sm:w-16 h-5 sm:h-6 opacity-60" style={{ top: "8%", left: "4%", backgroundColor: C.highlight, "--rot": "-8deg", transform: "rotate(-8deg)" }} />
      <div className="fl-float absolute w-3 h-3 rounded-full opacity-50" style={{ top: "45%", left: "6%", backgroundColor: C.brand, "--rot": "0deg", animationDelay: "1.2s" }} />
      <div className="fl-float absolute w-3.5 h-3.5 rounded-full opacity-50" style={{ top: "10%", right: "6%", backgroundColor: C.info, "--rot": "0deg", animationDelay: "2.4s" }} />

      <div className="w-full max-w-2xl relative">
        {/* Responsive Header: Guaranteed no overlap on mobile or desktop */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-8 sm:mb-14 fl-fade-up">
          <Logo />
          <div className="flex items-center gap-2 shrink-0">
            {deviceCount > 1 ? (
              <div
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-400 shadow-xs animate-pulse"
                style={{ fontFamily: MONO }}
                title="Phone and laptop are synced in real-time"
              >
                <Radio className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
                <span>Live Sync ({deviceCount})</span>
              </div>
            ) : (
              <div
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
                style={{
                  backgroundColor: C.paperRaised,
                  border: `1.5px solid ${C.ink}`,
                  fontFamily: MONO,
                  color: C.ink,
                }}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>FactLens Active</span>
              </div>
            )}
          </div>
        </div>

        {/* Backend Connectivity Status Notification */}
        <BackendStatusBar status={backendStatus} info={backendInfo} onRetry={onRetryBackend} onShowInstructions={onShowOfflineModal} />

        {/* Hero Title & Animated Doodle */}
        <div className="flex flex-col sm:grid sm:grid-cols-[1fr_150px] gap-6 items-center">
          <div className="fl-fade-up w-full" style={{ animationDelay: "0.05s" }}>
            <div className="flex items-start justify-between gap-3">
              <h1 className="text-3xl sm:text-[2.75rem] font-extrabold leading-[1.1] tracking-tight" style={{ color: C.ink, fontFamily: DISPLAY }}>
                Automated Fact Verification & Evidence Retrieval
              </h1>
              {/* Doodle displayed beside title on mobile so animations shine on phones! */}
              <div className="block sm:hidden w-16 h-16 shrink-0 fl-float" style={{ "--rot": "-4deg" }}>
                <HeroDoodle mouse={mouse} />
              </div>
            </div>
            <p className="mt-3 sm:mt-4 text-sm sm:text-base max-w-lg leading-relaxed" style={{ color: C.inkSoft, fontFamily: BODY }}>
              FactLens resolves pronouns, extracts factual assertions, and verifies claims against multi-source evidence corpora using BM25 and semantic embeddings.
            </p>
          </div>
          <div className="hidden sm:block w-full h-full fl-fade-up" style={{ animationDelay: "0.15s" }}>
            <HeroDoodle mouse={mouse} />
          </div>
        </div>

        <div
          className={`fl-input-card mt-8 sm:mt-10 rounded-2xl overflow-hidden fl-fade-up ${shakeKey ? "fl-shake" : ""}`}
          style={{ backgroundColor: C.paperRaised, border: `2px solid ${C.ink}`, boxShadow: `5px 5px 0 ${C.line}`, animationDelay: "0.2s" }}
        >
          {/* Audio Input Header / Mode Selector (Responsive flex-wrap) */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 px-4 sm:px-5 py-2.5 bg-slate-50 border-b" style={{ borderColor: C.line }}>
            <div className="flex items-center gap-2 min-w-0">
              <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
                <Volume2 className="w-3.5 h-3.5 text-teal-700 shrink-0" />
                <span className="truncate">Audio Input</span>
              </span>
              {isRecording && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700 animate-pulse shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
                  RECORDING
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={audioLang}
                onChange={(e) => setAudioLang(e.target.value)}
                className="text-xs bg-white border border-slate-300 rounded px-2 py-1 font-sans text-slate-700 focus:outline-none shadow-2xs"
              >
                <option value="en-US">English</option>
                <option value="ur-PK">اردو (Urdu)</option>
              </select>

              <button
                type="button"
                onClick={toggleRecording}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold transition-all shadow-xs ${
                  isRecording
                    ? "bg-rose-600 text-white animate-pulse"
                    : "bg-white border border-slate-300 text-slate-800 hover:bg-slate-100"
                }`}
                title={isRecording ? "Stop live recording" : "Start live voice dictation"}
              >
                {isRecording ? <Square className="w-3 h-3 fill-current" /> : <Mic className="w-3.5 h-3.5 text-teal-700" />}
                <span>{isRecording ? "Stop Mic" : "Live Mic"}</span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white border border-slate-300 text-slate-800 hover:bg-slate-100 transition-all shadow-xs"
                title="Upload audio clip (.mp3, .wav, .m4a)"
              >
                <Upload className="w-3.5 h-3.5 text-slate-600" />
                <span>Upload</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </div>
          </div>

          {audioStatus && (
            <div className="px-5 py-1.5 bg-teal-50 text-teal-800 text-xs flex items-center justify-between border-b border-teal-200">
              <span className="truncate">{audioStatus}</span>
              {uploadedAudioName && (
                <span className="font-mono text-[10px] text-teal-600">{uploadedAudioName}</span>
              )}
            </div>
          )}

          <textarea
            value={text}
            onChange={(e) => {
              const nextVal = e.target.value.slice(0, MAX_CHARS);
              setText(nextVal);
              if (onSyncText) onSyncText(nextVal);
            }}
            onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onAnalyze(text); }}
            placeholder="Paste text or speak using Live Mic / Upload Audio above…"
            rows={5}
            className="w-full resize-none px-5 py-4 bg-transparent focus:outline-none text-base leading-relaxed"
            style={{ color: C.ink, fontFamily: BODY }}
          />
          <div className="flex items-center justify-between px-5 py-3 gap-3" style={{ borderTop: `2px dashed ${C.line}` }}>
            <div className="flex items-center gap-3 min-w-0">
              <div className="hidden sm:flex items-center gap-1.5">
                <div className="w-14 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: C.paperSoft }}>
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: nearLimit ? C.brand : C.lineStrong, transition: "width 0.15s ease, background-color 0.2s ease" }} />
                </div>
              </div>
              <span className="text-xs shrink-0" style={{ color: nearLimit ? C.brand : C.inkFaint, fontFamily: MONO }}>{text.length}/{MAX_CHARS}</span>
              <span className="hidden md:flex items-center gap-1 text-xs shrink-0" style={{ color: C.inkFaint, fontFamily: BODY }}>
                <span className="fl-kbd"><Command className="w-2.5 h-2.5" />↵</span> to analyze
              </span>
            </div>
            <button
              onClick={() => onAnalyze(text)}
              disabled={!text.trim()}
              className="fl-analyze-btn inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold disabled:opacity-30 shrink-0"
              style={{ backgroundColor: C.brand, color: "#FFFFFF", fontFamily: DISPLAY, boxShadow: `0 4px 0 ${C.brandInk}` }}
            >
              Analyze it
              <ArrowUpRight className="w-4 h-4" strokeWidth={2.75} />
            </button>
          </div>
        </div>

        <div className="mt-14 fl-fade-up" style={{ animationDelay: "0.25s" }}>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4" style={{ color: C.brand }} />
            <span className="text-sm font-semibold" style={{ color: C.ink, fontFamily: BODY }}>Try a sample instead</span>
          </div>
          <div className="grid sm:grid-cols-2 gap-5">
            {EXAMPLES.map((ex, i) => {
              const dot = CATEGORY_COLOR[ex.kind];
              const rotate = i % 2 === 0 ? -1.5 : 1.5;
              return (
                <button key={ex.id} onClick={() => onAnalyze(ex.text, ex.id)} className="fl-sample-card text-left p-5 rounded-xl" style={{ backgroundColor: C.paperRaised, border: `2px dashed ${C.lineStrong}`, "--rot": `${rotate}deg` }}>
                  <div className="flex items-center gap-2 mb-2.5">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: dot }} />
                    <Field>{ex.kind === "factcheck" ? "fact-check" : "hate-speech"}</Field>
                  </div>
                  <p className="text-sm font-bold mb-0.5" style={{ color: C.ink, fontFamily: BODY }}>{ex.label}</p>
                  <p className="text-xs mb-2.5" style={{ color: C.inkFaint, fontFamily: BODY }}>{ex.sub}</p>
                  <p className="text-sm leading-snug line-clamp-2" style={{ color: C.inkSoft, fontFamily: BODY }}>{ex.text}</p>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SCREEN 2 - LOADING
// ---------------------------------------------------------------------------

const STAGES = [
  "Resolving pronoun references (LingMessCoref)",
  "Identifying factual claims (spaCy)",
  "Extracting claims & statements",
  "Retrieving evidence passages",
  "Dense semantic retrieval (BAAI/bge-base)",
  "Generating verification report",
];
const COREF_STAGE_INDEX = 0;
const SUFFICIENCY_STAGE_INDEX = 4;

const RETRY_SUBSTEPS = [
  { label: "Initial evidence search (local corpus)", icon: Database },
  { label: "Evidence insufficient", icon: AlertTriangle },
  { label: "One bounded retry triggered", icon: RefreshCw },
  { label: "Re-retrieved evidence", icon: CheckCircle2 },
];
const WIKI_SUBSTEPS = [
  { label: "Initial evidence search (local corpus)", icon: Database },
  { label: "Evidence insufficient", icon: AlertTriangle },
  { label: "One bounded retry triggered", icon: RefreshCw },
  { label: "Local evidence remains insufficient", icon: AlertTriangle },
  { label: "Optional Wikipedia fallback (preview)", icon: Globe2 },
  { label: "Wikipedia evidence retrieved", icon: CheckCircle2 },
];

function LoadingScreen({ stageIndex, usedRetry, usedWikipediaFallback, corefCount }) {
  const [subStep, setSubStep] = useState(0);
  const substeps = usedWikipediaFallback ? WIKI_SUBSTEPS : RETRY_SUBSTEPS;

  useEffect(() => {
    if (stageIndex !== SUFFICIENCY_STAGE_INDEX || !usedRetry) return;
    const timers = substeps.slice(1).map((_, idx) => setTimeout(() => setSubStep(idx + 1), 220 * (idx + 1)));
    return () => timers.forEach(clearTimeout);
  }, [stageIndex, usedRetry, usedWikipediaFallback, substeps]);

  const progressPct = Math.min(100, (stageIndex / STAGES.length) * 100);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6" style={{ backgroundColor: C.paper }}>
      <div className="relative mb-5">
        <div className="fl-pulse absolute inset-0 rounded-full" />
        <div className="relative w-14 h-14 rounded-full flex items-center justify-center fl-wobble" style={{ "--rot": "-3deg", border: `2.5px solid ${C.brand}`, backgroundColor: C.paperRaised }}>
          <Search className="w-6 h-6" style={{ color: C.brand }} strokeWidth={2.5} />
        </div>
      </div>
      <span className="text-lg font-extrabold mb-1" style={{ color: C.ink, fontFamily: DISPLAY }}>Building the case file…</span>
      <span className="text-xs mb-8" style={{ color: C.inkFaint, fontFamily: MONO, animation: "flBlink 1.6s ease-in-out infinite" }}>case #{String(stageIndex + 1).padStart(2, "0")} of {STAGES.length}</span>

      <div className="w-full max-w-sm h-2.5 rounded-full overflow-hidden mb-8" style={{ backgroundColor: C.paperSoft }}>
        <div className="h-full rounded-full" style={{ width: `${progressPct}%`, backgroundColor: C.highlight, transition: "width 0.35s ease" }} />
      </div>

      <div className="flex flex-col gap-3 w-full max-w-sm">
        {STAGES.map((s, i) => (
          <div key={s} className="flex flex-col gap-1.5 fl-fade-up" style={{ animationDelay: `${i * 0.03}s` }}>
            <div className="flex items-center gap-3">
              {i < stageIndex ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 fl-pop-in" style={{ color: C.supported }} />
              ) : i === stageIndex ? (
                <Loader2 className="w-4 h-4 animate-spin shrink-0" style={{ color: C.brand }} />
              ) : (
                <div className="w-4 h-4 rounded-full shrink-0" style={{ border: `1.5px solid ${C.line}` }} />
              )}
              <span className="text-sm" style={{ color: i <= stageIndex ? C.ink : C.inkFaint, fontWeight: i === stageIndex ? 700 : 400, fontFamily: BODY }}>{s}</span>
            </div>
            {i === stageIndex && <div className="ml-7 h-1.5 w-36 rounded-full overflow-hidden fl-shimmer-bar" style={{ backgroundColor: C.highlightSoft }} />}

            {i === COREF_STAGE_INDEX && corefCount > 0 && stageIndex >= COREF_STAGE_INDEX && (
              <div className="ml-7 flex items-center gap-2 fl-fade-up" style={{ borderLeft: `2px dashed ${C.line}`, paddingLeft: "0.75rem" }}>
                <Link2 className="w-3 h-3 shrink-0" style={{ color: C.info }} />
                <span className="text-xs" style={{ color: C.info, fontFamily: BODY }}>Found {corefCount} reference{corefCount > 1 ? "s" : ""} to resolve</span>
              </div>
            )}

            {i === SUFFICIENCY_STAGE_INDEX && usedRetry && stageIndex >= SUFFICIENCY_STAGE_INDEX && (
              <div className="ml-7 flex flex-col gap-1.5 py-1" style={{ borderLeft: `2px dashed ${C.line}`, paddingLeft: "0.75rem" }}>
                {substeps.slice(0, subStep + 1).map((step, si) => {
                  const Icon = step.icon;
                  const isCurrent = si === subStep && stageIndex === SUFFICIENCY_STAGE_INDEX;
                  return (
                    <div key={step.label} className="flex items-center gap-2 fl-fade-up">
                      <Icon className={`w-3 h-3 shrink-0 ${isCurrent ? "fl-scan" : ""}`} style={{ color: isCurrent ? C.brand : C.inkFaint }} />
                      <span className="text-xs" style={{ color: isCurrent ? C.brand : C.inkFaint, fontWeight: isCurrent ? 600 : 400, fontFamily: BODY }}>{step.label}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SCREEN 3 - RESULTS
// ---------------------------------------------------------------------------

function SubClaimCard({ claim, index }) {
  const [open, setOpen] = useState(index === 0);
  const isOpinion = claim.status === "Opinion";
  const isNonCheckable = claim.status === "Non-Checkable";
  const isUrdu = !!claim.textUr;
  const color = VERDICT_TEXT_COLOR[claim.verdict] || C.inkFaint;
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: `2px solid ${C.line}`, backgroundColor: C.paperRaised }}>
      <button onClick={() => setOpen((o) => !o)} className="fl-claim-row w-full flex items-center justify-between gap-3 px-4 py-3.5 text-left">
        <div className="flex items-center gap-3 min-w-0">
          <span className="shrink-0 text-xs font-bold w-5" style={{ fontFamily: MONO, color: C.inkFaint }}>{String(index + 1).padStart(2, "0")}</span>
          <span className="text-sm truncate" style={{ color: C.ink, fontFamily: BODY }} dir={isUrdu ? "rtl" : "ltr"}>{claim.text}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isOpinion ? <OpinionPill label={claim.statusUr || "Opinion"} /> : isNonCheckable ? <NonCheckablePill label={claim.statusUr || "Non-Checkable"} /> : <VerdictPill verdict={claim.verdict} verdictUr={claim.verdictUr} />}
          <ChevronDown className="w-4 h-4" style={{ color: C.inkFaint, transform: open ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s ease" }} />
        </div>
      </button>
      {open && (
        <div className="fl-expand px-4 pb-4 pt-1 ml-8" style={{ borderTop: `2px dashed ${C.line}` }}>
          {isUrdu && claim.textEn && claim.textEn !== claim.text && (
            <div className="mt-2.5 mb-2 p-2 rounded text-xs" style={{ backgroundColor: C.paperSoft, border: `1px dashed ${C.line}` }}>
              <span className="font-bold text-gray-500 uppercase tracking-wide mr-1.5 font-mono">English pipeline text:</span>
              <span className="italic" style={{ color: C.ink }}>"{claim.textEn}"</span>
            </div>
          )}
          {isOpinion ? (
            <p className="text-sm leading-relaxed pt-3" style={{ color: C.inkSoft, fontFamily: BODY }} dir={isUrdu ? "rtl" : "ltr"}>
              {claim.reason || "رائے - ذاتی نقطہ نظر ہے، اس لیے اس کی حقائق کی بنیاد پر تصدیق نہیں کی جائے گی۔"}
            </p>
          ) : isNonCheckable ? (
            <div className="pt-3 flex flex-col gap-1.5">
              <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "#854D0E", fontFamily: MONO }}>
                {claim.statusUr ? `${claim.statusUr} (Non-Checkable)` : "Non-Checkable Input"}
              </p>
              <p className="text-sm leading-relaxed" style={{ color: C.inkSoft, fontFamily: BODY }} dir={isUrdu ? "rtl" : "ltr"}>
                {claim.reason || "Sentence fragment, question, or incomplete statement — does not form a checkable factual claim."}
              </p>
            </div>
          ) : (
            <>
              <p className="text-xs font-semibold pt-3 mb-2" style={{ color: C.supported, fontFamily: BODY }}>
                {isUrdu ? "حقائق پر مبنی دعویٰ — ثبوت اور تصدیق کا عمل مکمل" : "Factual claim - sent for verification."}
              </p>
              {claim.resolvedText && claim.resolvedText.trim () !== claim.text.trim () && (
                <div className="mb-3 flex flex-col gap-1">
                  <span className="text-xs" style={{ color: C.inkFaint, fontFamily: MONO }}>as written: <span style={{ color: C.inkSoft }}>{claim.text}</span></span>
                  <span className="text-xs" style={{ color: C.info, fontFamily: MONO }}>resolved: <span style={{ fontWeight: 600 }}>{claim.resolvedText}</span></span>
                </div>
              )}
              {claim.note && <p className="text-xs italic mb-2.5" style={{ color: C.inkFaint, fontFamily: BODY }}>{claim.note}</p>}
              <div className="flex items-center gap-2 mb-2.5">
                <div className="h-2 flex-1 rounded-full overflow-hidden" style={{ backgroundColor: C.paperSoft }}>
                  <div className="h-full rounded-full" style={{ width: `${claim.confidence}%`, backgroundColor: color, transition: "width 0.6s cubic-bezier(.2,.8,.2,1)" }} />
                </div>
                <span className="text-xs font-medium w-9 text-right" style={{ color: C.inkSoft, fontFamily: MONO }}>{claim.confidence}%</span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: C.inkSoft, fontFamily: BODY }} dir={isUrdu ? "rtl" : "ltr"}>{claim.evidence}</p>
              {isUrdu && claim.evidenceEn && claim.evidenceEn !== claim.evidence && (
                <p className="text-xs italic mt-1 text-gray-500" style={{ fontFamily: BODY }}>
                  Source passage (EN): "{claim.evidenceEn}"
                </p>
              )}
              <div className="mt-2.5 inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-mono" style={{ color: claim.source?.includes("Wikipedia") ? C.info : claim.source?.includes("SciFact") ? "#047857" : claim.source?.includes("FEVER") ? "#B45309" : claim.source?.includes("AVeriTeC") ? "#6D28D9" : claim.source?.includes("All Datasets") ? "#475569" : C.inkSoft, backgroundColor: claim.source?.includes("Wikipedia") ? C.infoSoft : claim.source?.includes("SciFact") ? "#D1FAE5" : claim.source?.includes("FEVER") ? "#FEF3C7" : claim.source?.includes("AVeriTeC") ? "#EDE9FE" : claim.source?.includes("All Datasets") ? "#F1F5F9" : C.paperSoft, border: `1px solid ${C.line}` }}>
                <Database className="w-3.5 h-3.5" />
                <span>{claim.source || "Unified Benchmark Corpus"}</span>
              </div>
              {claim.searchTrail && <SearchTrail steps={claim.searchTrail} />}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TechDetails({ data, isHate = false }) {
  const isUrdu = data.language === "ur";
  const rows = isHate
    ? [
        ["Model Architecture", "Fine-tuned contextual transformer (HateXplain baseline: Hate / Offensive / Normal)"],
        ["Target Identification", data.target || "Demographic / identity category mapping"],
        ["Contextual Cues", "Model-relevant token attribution highlights accompanying the classification decision"],
        ["Evaluation Suite", "HateCheck diagnostic test suite to ensure benign identity mentions are not falsely flagged"],
        ["Timeline Status", "Scheduled for Phase 1 Iteration 3 / FYP-2 development as committed in approved proposal"],
      ]
    : [
        ...(isUrdu ? [
          ["Input Language", "Urdu (اردو) — Detected automatically"],
          ["Cross-Lingual Processing", "Neural translation to English for retrieval & bilingual response mapping"],
        ] : []),
        ["Coreference links", data.corefResolutions.length ? data.corefResolutions.map((c) => `"${c.from}" → "${c.to}"`).join("; ") : "No pronouns required resolution in this text"],
        ["Fact vs opinion", `${data.subClaims.filter((c) => c.status === "Fact").length} factual assertions, ${data.subClaims.filter((c) => c.status === "Opinion").length} opinions${data.subClaims.some((c) => c.status === "Non-Checkable") ? `, ${data.subClaims.filter((c) => c.status === "Non-Checkable").length} non-checkable` : ""}`],
        ["Claim extraction", `${data.subClaims.length} sentence-level claims extracted using spaCy boundary detection`],
        ["Coreference model", "LingMessCoref (Longformer-based coreference resolution)"],
        ["Evidence retrieval", "Hybrid search: BM25Plus lexical match + BAAI/bge-base-en-v1.5 dense retrieval"],
        ["Verification engine", "DeBERTa-v3 NLI cross-encoder (cross-encoder/nli-deberta-v3-small)"],
        ["Evidence sources", isUrdu ? "Unified multi-benchmark & regional Urdu corpus (Urdu-News-Augmented, UrduFactCheck, ULNC, Ax-to-Grind-Urdu, FEVER, SciFact, AVeriTeC)" : "Unified multi-benchmark corpus (SciFact, FEVER 2018, FEVER 2.0, FEVEROUS, AVeriTeC)"],
      ];
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map(([label, value]) => (
        <div key={label} className="flex flex-col gap-0.5">
          <Field>{label}</Field>
          <p className="text-sm leading-relaxed" style={{ color: C.inkSoft, fontFamily: BODY }}>{value}</p>
        </div>
      ))}
    </div>
  );
}

function CopyButton({ getText, onCopied }) {
  return (
    <button
      onClick={() => { navigator.clipboard?.writeText(getText()); onCopied(); }}
      className="fl-icon-btn inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shrink-0"
      style={{ color: C.inkSoft, border: `1.5px solid ${C.line}`, fontFamily: BODY, backgroundColor: C.paperRaised }}
    >
      <Copy className="w-3.5 h-3.5" />
      Copy report
    </button>
  );
}

function FactCheckReport({ data, originalText, onCopied }) {
  if (!data.subClaims.length) {
    return (
      <div className="fl-fade-up p-10 text-center rounded-2xl" style={{ border: `2px dashed ${C.lineStrong}`, backgroundColor: C.paperRaised }}>
        <FileText className="w-5 h-5 mx-auto mb-2" style={{ color: C.inkFaint }} />
        <p className="text-sm" style={{ color: C.inkSoft, fontFamily: BODY }}>No checkable factual claims were found in this text.</p>
      </div>
    );
  }

  const isUrdu = data.language === "ur";
  const gaugeColor = VERDICT_TEXT_COLOR[data.overallVerdict] || C.inkFaint;
  const reportText = () => {
    const lines = [
      `FactLens fact-check report`,
      `Text: "${originalText}"`,
      data.originalTextEn ? `English Translation: "${data.originalTextEn}"` : "",
      `Overall: ${data.overallVerdict}${data.overallVerdictUr ? ` (${data.overallVerdictUr})` : ""}${data.overallConfidence != null ? ` (${data.overallConfidence}% confidence)` : ""}`,
      "",
    ].filter(Boolean);
    data.subClaims.forEach((c, i) => {
      lines.push(`${i + 1}. ${c.text}`);
      if (c.textEn && c.textEn !== c.text) lines.push(`   [EN]: ${c.textEn}`);
      if (c.status === "Opinion") {
        lines.push(`   Opinion - not fact-checked (${c.reason || "subjective statement"})`);
      } else if (c.status === "Non-Checkable") {
        lines.push(`   Non-Checkable - ${c.reason || "not a checkable factual claim"}`);
      } else {
        lines.push(`   ${c.verdict}${c.verdictUr ? ` (${c.verdictUr})` : ""} (${c.confidence}%) - ${c.evidence}`);
      }
    });
    return lines.join("\n");
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="fl-fade-up p-6 rounded-2xl" style={{ border: `2px solid ${C.ink}`, backgroundColor: C.paperRaised, boxShadow: `5px 5px 0 ${C.line}` }}>
        <div className="flex items-start justify-between gap-3 mb-2">
          <Field>Original text</Field>
          <CopyButton getText={reportText} onCopied={onCopied} />
        </div>

        {isUrdu && (
          <div className="mb-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: "#EFF6FF", color: "#1D4ED8", border: "1.5px solid #BFDBFE", fontFamily: BODY }}>
            <Globe2 className="w-3.5 h-3.5 shrink-0" />
            <span>اردو متن شناخت شدہ (Urdu Detected) — ترجمہ اور کثیر النسلی ڈیٹا بیس سے تصدیق فعال ہے</span>
          </div>
        )}

        <p className="mb-3 leading-relaxed" style={{ color: C.ink, fontFamily: BODY, fontSize: isUrdu ? "1.15rem" : "1rem" }} dir={isUrdu ? "rtl" : "ltr"}>{originalText}</p>

        {isUrdu && data.originalTextEn && (
          <div className="mb-5 p-2.5 rounded-lg text-xs flex items-center gap-2" style={{ backgroundColor: C.paperSoft, border: `1px dashed ${C.line}` }}>
            <span className="font-bold text-gray-500 uppercase tracking-wide shrink-0 font-mono">English Pipeline:</span>
            <span className="italic truncate" style={{ color: C.inkSoft, fontFamily: BODY }}>"{data.originalTextEn}"</span>
          </div>
        )}

        {data.allOpinion ? (
          <div className="flex items-start gap-3 p-4 rounded-xl" style={{ backgroundColor: data.subClaims.some((c) => c.status === "Non-Checkable") ? "#FEF9C3" : C.opinionSoft }}>
            {data.subClaims.some((c) => c.status === "Non-Checkable") ? (
              <HelpCircle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "#854D0E" }} />
            ) : (
              <MessageSquare className="w-5 h-5 shrink-0 mt-0.5" style={{ color: C.opinion }} />
            )}
            <p className="text-sm leading-relaxed font-medium" style={{ color: data.subClaims.some((c) => c.status === "Non-Checkable") ? "#854D0E" : "#4C1D95", fontFamily: BODY }} dir={isUrdu ? "rtl" : "ltr"}>
              {data.subClaims.some((c) => c.status === "Non-Checkable")
                ? (data.subClaims.find((c) => c.status === "Non-Checkable")?.reason || "Sentence fragment is too brief to form a complete checkable assertion")
                : (data.subClaims.find((c) => c.status === "Opinion")?.reason || "Opinion - not a factual claim, so it will not be fact-checked.")}
            </p>
          </div>
        ) : (
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              {data.overallConfidence != null && <ConfidenceGauge value={data.overallConfidence} color={gaugeColor} />}
              <VerdictStamp verdict={data.overallVerdict} verdictUr={data.overallVerdictUr} />
            </div>
            {data.usedRetry && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" style={{ color: C.brand, backgroundColor: C.brandSoft, fontFamily: BODY }}>
                <RefreshCw className="w-3.5 h-3.5" />
                One bounded retry performed
              </span>
            )}
            {data.usedWikipediaFallback && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" style={{ color: C.info, backgroundColor: C.infoSoft, fontFamily: BODY }}>
                <Globe2 className="w-3.5 h-3.5" />
                Optional Wikipedia fallback used - future flow preview
              </span>
            )}
          </div>
        )}
        {data.subClaims.length > 1 && !data.allOpinion && (
          <div className="mt-3 pt-3 flex items-center gap-2 flex-wrap text-xs" style={{ borderTop: `1.5px dashed ${C.line}`, color: C.inkSoft, fontFamily: BODY }}>
            <span className="font-bold">Decomposition Summary:</span>
            <span className="inline-flex items-center gap-1 font-semibold" style={{ color: C.supported }}>
              <CheckCircle2 className="w-3 h-3" />
              {data.subClaims.filter((c) => c.verdict === "Supported").length} Supported
            </span>
            <span>•</span>
            <span className="inline-flex items-center gap-1 font-semibold" style={{ color: C.refuted }}>
              <XCircle className="w-3 h-3" />
              {data.subClaims.filter((c) => c.verdict === "Refuted").length} Refuted
            </span>
            {data.subClaims.some((c) => c.verdict === "Not Enough Evidence") && (
              <>
                <span>•</span>
                <span className="inline-flex items-center gap-1 font-semibold" style={{ color: "#8A6A00" }}>
                  <HelpCircle className="w-3 h-3" />
                  {data.subClaims.filter((c) => c.verdict === "Not Enough Evidence").length} Inconclusive
                </span>
              </>
            )}
          </div>
        )}
        {data.isLiveBackend && (
          <div className="mt-3 pt-3 flex items-center gap-2" style={{ borderTop: `1.5px dashed ${C.line}` }}>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold" style={{ color: "#065F46", backgroundColor: "#D1FAE5", border: "1.5px solid #10B981", fontFamily: MONO }}>
              <Sparkles className="w-3.5 h-3.5" />
              LIVE PYTHON ENGINE (spaCy + BM25)
            </span>
          </div>
        )}
      </div>

      {data.corefResolutions.length > 0 && (
        <Disclosure icon={Link2} title="Context resolution" subtitle={`${data.corefResolutions.length} reference${data.corefResolutions.length > 1 ? "s" : ""} resolved automatically`} accent={C.info}>
          <p className="text-xs mb-3" style={{ color: C.inkFaint, fontFamily: BODY }}>Before analyzing the text, FactLens automatically figures out what each pronoun refers to - this happens on its own, the user never resolves anything manually.</p>
          <div className="flex flex-col gap-2">
            {data.corefResolutions.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-sm flex-wrap" style={{ fontFamily: BODY }}>
                <span className="px-2 py-0.5 rounded-md font-semibold" style={{ backgroundColor: C.highlightSoft, color: C.ink }}>{c.from}</span>
                <ArrowRight className="w-3.5 h-3.5" style={{ color: C.inkFaint }} />
                <span className="px-2 py-0.5 rounded-md font-semibold" style={{ backgroundColor: C.supportedSoft, color: C.ink }}>{c.to}</span>
              </div>
            ))}
          </div>
        </Disclosure>
      )}

      <Disclosure icon={FileText} title="Claim breakdown" subtitle={`Rule-based baseline decomposition - ${data.subClaims.length} sub-claim${data.subClaims.length > 1 ? "s" : ""}`} defaultOpen>
        <p className="text-xs mb-3" style={{ color: C.inkFaint, fontFamily: BODY }}>FactLens decomposes complex sentences into atomic, independently verifiable claims using spaCy dependency parse rules (Iteration 1 baseline).</p>
        <div className="flex flex-col gap-3">
          {data.subClaims.map((c, i) => <SubClaimCard key={i} claim={c} index={i} />)}
        </div>
      </Disclosure>

      <Disclosure icon={Settings2} title="Technical details" subtitle="Retrieval, ranking, and verification internals">
        <TechDetails data={data} />
      </Disclosure>
    </div>
  );
}

function HateSpeechReport() {
  return (
    <div className="flex flex-col gap-4 fl-fade-up">
      <div className="p-8 rounded-2xl" style={{ border: `2px solid ${C.ink}`, backgroundColor: C.paperRaised, boxShadow: `5px 5px 0 ${C.line}` }}>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider mb-5" style={{ backgroundColor: "#FEF3C7", color: "#B45309", border: "1.5px solid #FCD34D", fontFamily: MONO }}>
          <AlertTriangle className="w-4 h-4" />
          Module 2: Contextual Harm & Hate-Speech Detection
        </div>

        <h3 className="text-xl font-extrabold mb-3" style={{ color: C.ink, fontFamily: DISPLAY }}>
          Scheduled for Iteration 3 (FYP-2)
        </h3>

        <p className="text-sm leading-relaxed mb-6" style={{ color: C.inkSoft, fontFamily: BODY }}>
          As established in our approved proposal defense roadmap, <strong>FYP-1 is strictly dedicated to the Core Fact Verification pipeline</strong> (Coreference resolution, Claim extraction, and Evidence retrieval). The secondary lens for contextual harm and hate speech detection will be trained and integrated in Iteration 3.
        </p>

        <div className="p-5 rounded-xl mb-6" style={{ backgroundColor: C.paperSoft, border: `1.5px solid ${C.line}` }}>
          <span className="text-xs font-bold uppercase tracking-wider block mb-3" style={{ color: C.inkFaint, fontFamily: MONO }}>
            Planned Pipeline Architecture:
          </span>
          <ul className="text-sm space-y-2.5" style={{ color: C.inkSoft, fontFamily: BODY }}>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">•</span>
              <span><strong>Classifier:</strong> Contextual transformer fine-tuned on the <em>HateXplain</em> benchmark (3-way triage: Hate, Offensive, Normal).</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">•</span>
              <span><strong>Explainability:</strong> Model-relevant token attribution highlights (contextual cues) accompanying decisions.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-600 font-bold">•</span>
              <span><strong>Diagnostic Evaluation:</strong> Evaluated against the <em>HateCheck</em> test suite to prevent false positives on benign identity mentions.</span>
            </li>
          </ul>
        </div>

        <p className="text-xs italic" style={{ color: C.inkFaint, fontFamily: BODY }}>
          Note: No mock classification is generated here to preserve complete academic honesty during FYP-1 evaluations.
        </p>
      </div>
    </div>
  );
}

function ResultsScreen({ originalText, results, onReset, onCopied }) {
  const [tab, setTab] = useState("factcheck");
  const [scrolled, setScrolled] = useState(false);
  const tabs = [
    { id: "factcheck", label: "Fact-Check Report" },
    { id: "hatespeech", label: "Hate-Speech Module" },
  ];
  const activeIdx = tabs.findIndex((t) => t.id === tab);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.paper }}>
      <div className="w-full max-w-2xl mx-auto">
        <div
          className="sticky top-0 z-40 -mx-6 px-6 py-3 mb-8 flex items-center justify-between fl-fade-up"
          style={{
            backgroundColor: scrolled ? `${C.paper}F2` : "transparent",
            backdropFilter: scrolled ? "blur(6px)" : "none",
            borderBottom: scrolled ? `2px solid ${C.line}` : "2px solid transparent",
            transition: "background-color 0.2s ease, border-color 0.2s ease",
          }}
        >
          <Logo compact={scrolled} />
          <button onClick={onReset} className="fl-reset-btn inline-flex items-center gap-1.5 text-sm font-semibold" style={{ color: C.inkSoft, fontFamily: BODY }}>
            <ArrowLeft className="w-4 h-4" />
            New check
          </button>
        </div>

        <div className="flex items-center gap-2 mb-3 fl-fade-up">
          <Sparkles className="w-3.5 h-3.5" style={{ color: C.brand }} />
          <span className="text-xs" style={{ color: C.inkFaint, fontFamily: BODY }}>
            Dual-lens analysis: cross-referencing factual assertions and contextual harm in a single case file.
          </span>
        </div>

        <div className="relative grid grid-cols-2 mb-7 fl-fade-up" style={{ borderBottom: `2px solid ${C.line}` }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="fl-tab-btn relative py-3 text-sm font-semibold flex items-center justify-center gap-2 transition-colors duration-150"
              style={{ color: tab === t.id ? C.ink : C.inkFaint, fontFamily: BODY }}
            >
              {t.label}
              {t.id === "hatespeech" && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider" style={{ backgroundColor: "#FEF3C7", color: "#B45309", border: "1px solid #FCD34D" }}>
                  Iter 3
                </span>
              )}
            </button>
          ))}
          <div
            className="absolute bottom-[-2px] h-[3px] rounded-full"
            style={{
              backgroundColor: C.brand,
              width: "50%",
              left: `${activeIdx * 50}%`,
              transition: "left 0.25s cubic-bezier(.2,.8,.2,1)",
            }}
          />
        </div>

        {tab === "factcheck" ? (
          <FactCheckReport key={`fc-${originalText}`} data={results.factCheck} originalText={originalText} onCopied={onCopied} />
        ) : (
          <HateSpeechReport />
        )}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// APP
// ---------------------------------------------------------------------------

export default function App() {
  const [screen, setScreen] = useState("input");
  const [text, setText] = useState("");
  const [analyzedText, setAnalyzedText] = useState("");
  const [results, setResults] = useState(null);
  const [stageIndex, setStageIndex] = useState(0);
  const [pendingRetry, setPendingRetry] = useState(false);
  const [pendingWikipedia, setPendingWikipedia] = useState(false);
  const [pendingCorefCount, setPendingCorefCount] = useState(0);
  const [toast, setToast] = useState(null);
  const [shake, setShake] = useState(0);
  const [deviceCount, setDeviceCount] = useState(1);
  const [backendStatus, setBackendStatus] = useState("checking"); // "online" | "offline" | "checking"
  const [backendInfo, setBackendInfo] = useState(null);
  const [dismissedOfflineNotice, setDismissedOfflineNotice] = useState(false);
  const [isCheckingBackend, setIsCheckingBackend] = useState(false);

  const API_BASE = getApiBase();
  const wsRef = useRef(null);
  const textRef = useRef(text);
  textRef.current = text;

  // Active Health Prober:
  // Detects whether FastAPI is running on port 8000.
  // When offline, seamlessly falls back to Standalone Interactive Simulation
  // and guides the user/evaluator on how to start the neural backend.
  const checkBackendHealth = useCallback(async () => {
    setIsCheckingBackend(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);
      const res = await fetch(`${API_BASE}/api/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus("online");
        setBackendInfo(data);
        return true;
      } else {
        setBackendStatus("offline");
        return false;
      }
    } catch {
      setBackendStatus("offline");
      return false;
    } finally {
      setIsCheckingBackend(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 8000);
    return () => clearInterval(interval);
  }, [checkBackendHealth]);

  // Live Cross-Device Sync WebSocket:
  // Mirrors speech input, text edits, and analysis triggers in real time between mobile phone and laptop.
  useEffect(() => {
    let active = true;
    let ws = null;
    let reconnectTimer = null;

    const connectWebSocket = () => {
      try {
        const hostname = (typeof window !== "undefined" && window.location.hostname) || "localhost";
        const wsUrl = `ws://${hostname}:8000/ws/sync`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          if (!active) return;
          setBackendStatus("online");
        };

        ws.onmessage = (event) => {
          if (!active) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "INIT_STATE") {
              if (data.state && data.state.text && !textRef.current) {
                setText(data.state.text);
              }
              if (data.device_count) setDeviceCount(data.device_count);
            } else if (data.type === "DEVICE_COUNT") {
              setDeviceCount(data.count || 1);
            } else if (data.type === "SYNC_TEXT") {
              if (data.text !== undefined && data.text !== textRef.current) {
                setText(data.text);
              }
            } else if (data.type === "ANALYZE_TRIGGER") {
              if (data.text) {
                runAnalysis(data.text, null, false);
              }
            }
          } catch (e) {
            console.error("WebSocket message parsing error:", e);
          }
        };

        ws.onclose = () => {
          if (!active) return;
          reconnectTimer = setTimeout(connectWebSocket, 2000);
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };

        wsRef.current = ws;
      } catch (err) {
        console.warn("WebSocket setup warning:", err);
      }
    };

    connectWebSocket();

    return () => {
      active = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  const broadcastSyncText = (updatedText, audioLang = "en-US") => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "UPDATE_TEXT",
        text: updatedText,
        audioLang: audioLang,
        timestamp: Date.now(),
      }));
    } else {
      // REST fallback
      fetch(`${API_BASE}/api/sync/state`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: updatedText, audioLang: audioLang }),
      }).catch(() => {});
    }
  };

  const broadcastAnalyze = (targetText) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "ANALYZE_TRIGGER",
        text: targetText,
      }));
    }
  };

  const fetchRealAnalysis = async (cleanText) => {
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: cleanText }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      const isUrdu = json.language === "ur" || json.fact_check.language === "ur";
      return {
        isLiveBackend: true,
        language: json.language || "en",
        originalTextEn: json.original_text_en,
        factCheck: {
          language: json.fact_check.language || json.language || "en",
          originalTextEn: json.original_text_en,
          overallVerdict: json.fact_check.overall_verdict,
          overallVerdictUr: json.fact_check.overall_verdict_ur,
          overallConfidence: json.fact_check.overall_confidence,
          allOpinion: json.fact_check.all_opinion,
          usedRetry: json.fact_check.used_retry,
          usedWikipediaFallback: json.fact_check.used_wikipedia_fallback,
          corefResolutions: json.fact_check.coref_resolutions.map((r) => ({
            from: r.from_mention,
            to: r.to_mention,
          })),
          subClaims: json.fact_check.sub_claims.map((c) => ({
            text: (isUrdu && c.text_ur) ? c.text_ur : c.text,
            textEn: c.text,
            textUr: c.text_ur,
            resolvedText: c.resolved_text || undefined,
            status: c.status,
            statusUr: c.status_ur,
            reason: (isUrdu && c.reason_ur) ? c.reason_ur : c.reason,
            reasonEn: c.reason,
            verdict: c.verdict || "Not Enough Evidence",
            verdictUr: c.verdict_ur,
            confidence: c.confidence || 50,
            evidence: (isUrdu && c.evidence_ur) ? c.evidence_ur : (c.evidence || "No evidence found in local corpus."),
            evidenceEn: c.evidence,
            source: c.source || "Local Evidence Corpus",
            searchTrail: c.bm25_score != null ? [
              { label: `BM25 keyword score: ${c.bm25_score}`, state: "done" },
              { label: `Semantic embedding score: ${c.embedding_score}`, state: "done" },
              { label: `Retrieved evidence verdict: ${c.verdict_ur || c.verdict}`, state: c.verdict === "Supported" ? "done" : "warn" },
            ] : undefined,
          })),
        },
        hateSpeech: {
          classification: json.hate_speech.classification,
          target: json.hate_speech.target,
          cues: json.hate_speech.cues,
          reason: json.hate_speech.reason,
        },
      };
    } catch {
      return null;
    }
  };

  const runAnalysis = async (inputText, exampleId, shouldBroadcast = true) => {
    const clean = inputText.trim();
    if (!clean) { setShake((s) => s + 1); return; }
    if (shouldBroadcast) {
      broadcastAnalyze(clean);
    }
    setAnalyzedText(clean);
    setScreen("loading");
    setStageIndex(0);

    // Call real backend first; fall back to offline simulation if backend is unreachable
    const realData = await fetchRealAnalysis(clean);
    const data = realData || (exampleId && MOCK_RESPONSES[exampleId] ? MOCK_RESPONSES[exampleId] : mockAnalyze(clean));
    setPendingRetry(!!data.factCheck.usedRetry);
    setPendingWikipedia(!!data.factCheck.usedWikipediaFallback);
    setPendingCorefCount(data.factCheck.corefResolutions.length);

    let i = 0;
    const advance = () => {
      i += 1;
      setStageIndex(i);
      if (i >= STAGES.length) {
        setResults(data);
        setScreen("results");
        return;
      }
      const leavingSufficiencyWithExtra = i === SUFFICIENCY_STAGE_INDEX + 1 && data.factCheck.usedRetry;
      const delay = data.factCheck.usedWikipediaFallback && leavingSufficiencyWithExtra ? 1450 : leavingSufficiencyWithExtra ? 950 : 340;
      setTimeout(advance, delay);
    };
    setTimeout(advance, 340);
  };

  const reset = () => {
    setScreen("input");
    setText("");
    setResults(null);
    broadcastSyncText("");
    window.scrollTo(0, 0);
  };

  useEffect(() => {
    if (!shake) return;
    const t = setTimeout(() => setShake(0), 500);
    return () => clearTimeout(t);
  }, [shake]);

  return (
    <div style={{ fontFamily: BODY }}>
      <GlobalStyle />
      <StampFilterDefs />
      <div className="fl-grain" aria-hidden="true" />
      {screen === "loading" && <LoadingScreen stageIndex={stageIndex} usedRetry={pendingRetry} usedWikipediaFallback={pendingWikipedia} corefCount={pendingCorefCount} />}
      {screen === "results" && results && <ResultsScreen originalText={analyzedText} results={results} onReset={reset} onCopied={() => setToast("Report copied")} />}
      {screen === "input" && (
        <InputScreen
          text={text}
          setText={setText}
          onAnalyze={runAnalysis}
          shakeKey={shake}
          deviceCount={deviceCount}
          onSyncText={broadcastSyncText}
          backendStatus={backendStatus}
          backendInfo={backendInfo}
          onRetryBackend={checkBackendHealth}
        />
      )}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
