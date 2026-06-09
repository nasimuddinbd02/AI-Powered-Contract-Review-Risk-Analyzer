"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, Download, FileText,
  Loader2, MessageSquareText, Quote, Scale, Send, Sparkles, ShieldCheck, Upload,
} from "lucide-react";
import { api, type Clause, type Contract, type QATurn } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { AuthScreen } from "@/components/auth-screen";
import { UserManagement } from "@/components/user-management";
import { UserMenu } from "@/components/user-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ThemeToggle } from "@/components/theme-toggle";

// --- risk helpers ----------------------------------------------------------

type Health = Awaited<ReturnType<typeof api.health>>;

function riskMeta(level: string | null) {
  switch (level) {
    case "HIGH": return { variant: "high" as const, Icon: AlertTriangle, label: "High", text: "text-risk-high" };
    case "MEDIUM": return { variant: "medium" as const, Icon: AlertCircle, label: "Medium", text: "text-risk-medium" };
    case "LOW": return { variant: "low" as const, Icon: CheckCircle2, label: "Low", text: "text-risk-low" };
    default: return { variant: "outline" as const, Icon: AlertCircle, label: "—", text: "text-muted-foreground" };
  }
}

function RiskBadge({ level }: { level: string | null }) {
  const m = riskMeta(level);
  return (
    <Badge variant={m.variant} className="gap-1">
      <m.Icon className="h-3 w-3" /> {m.label}
    </Badge>
  );
}

function scoreTone(score: number) {
  if (score >= 67) return "text-risk-high";
  if (score >= 34) return "text-risk-medium";
  return "text-risk-low";
}

// Circular risk gauge
function RiskGauge({ value }: { value: number }) {
  const r = 52, c = 2 * Math.PI * r, pct = Math.max(0, Math.min(100, value));
  const stroke = pct >= 67 ? "hsl(var(--risk-high))" : pct >= 34 ? "hsl(var(--risk-medium))" : "hsl(var(--risk-low))";
  return (
    <div className="relative h-32 w-32 shrink-0">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="hsl(var(--muted))" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={stroke} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-3xl font-bold tabular-nums", scoreTone(value))}>{Math.round(value)}</span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Risk / 100</span>
      </div>
    </div>
  );
}

// --- page ------------------------------------------------------------------

export default function Page() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  if (!user) return <AuthScreen />;
  return <Dashboard />;
}

function Dashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState<Health | null>(null);
  const [stage, setStage] = useState<"idle" | "uploading" | "analyzing">("idle");
  const [error, setError] = useState("");
  const [contract, setContract] = useState<Contract | null>(null);
  const [view, setView] = useState<"dashboard" | "users">("dashboard");

  useEffect(() => { api.health().then(setHealth).catch(() => {}); }, []);

  async function handleFile(file: File) {
    setError(""); setContract(null);
    try {
      setStage("uploading");
      const up = await api.upload(file);
      setStage("analyzing");
      setContract(await api.analyze(up.contract_id));
    } catch (e) {
      setError(humanError(e));
    } finally {
      setStage("idle");
    }
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-background">
        <TopBar health={health} onHome={() => setView("dashboard")} onOpenUsers={() => setView("users")} />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {view === "users" && user?.role === "admin" ? (
            <UserManagement onBack={() => setView("dashboard")} />
          ) : (
            <>
              {health && !health.llm_ready && <KeyBanner />}
              {error && <ErrorBanner message={error} onDismiss={() => setError("")} />}

              {!contract && stage === "idle" && <Landing onFile={handleFile} />}
              {stage !== "idle" && <Processing stage={stage} />}

              {contract && stage === "idle" && (
                <div className="animate-fade-in space-y-6">
                  <SummaryCard contract={contract} onReset={() => setContract(null)} />
                  <div className="grid gap-6 lg:grid-cols-5">
                    <div className="lg:col-span-3">
                      <ClauseSection contract={contract} />
                    </div>
                    <div className="lg:col-span-2">
                      <ChatPanel contractId={contract.contract_id} ready={!!health?.llm_ready} />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </TooltipProvider>
  );
}

function humanError(e: unknown): string {
  const s = String(e);
  if (s.includes("OPENAI_API_KEY") || s.includes("No LLM provider"))
    return "AI is not configured. Add your OPENAI_API_KEY to the backend .env and restart the server.";
  return s.replace(/^Error:\s*/, "");
}

// --- top bar ---------------------------------------------------------------

function TopBar({ health, onHome, onOpenUsers }: { health: Health | null; onHome: () => void; onOpenUsers: () => void }) {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-border/70 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        <button onClick={onHome} className="group flex items-center gap-2.5 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm ring-1 ring-inset ring-white/10 transition-transform group-hover:scale-105">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="text-left leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">ContractIQ</div>
            <div className="hidden text-[11px] text-muted-foreground sm:block">Contract Review &amp; Risk Analyzer</div>
          </div>
        </button>
        <div className="flex items-center gap-1.5 sm:gap-2">
          {health && (
            <Badge variant={health.llm_ready ? "low" : "medium"} className="hidden font-normal sm:inline-flex">
              <span className={cn("h-1.5 w-1.5 rounded-full", health.llm_ready ? "bg-risk-low" : "bg-risk-medium")} />
              {health.llm_ready ? `${health.llm_model}` : "AI not configured"}
            </Badge>
          )}
          <ThemeToggle />
          <div className="mx-0.5 hidden h-6 w-px bg-border sm:block" />
          <UserMenu onOpenUsers={onOpenUsers} />
        </div>
      </div>
    </header>
  );
}

// --- banners ---------------------------------------------------------------

function KeyBanner() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-lg border border-risk-medium/30 bg-risk-medium/10 p-4 text-sm">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-risk-medium" />
      <div>
        <p className="font-medium text-foreground">AI provider not configured</p>
        <p className="text-muted-foreground">
          Add <code className="rounded bg-muted px-1 py-0.5 text-xs">OPENAI_API_KEY</code> to the backend{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">.env</code> and restart. Until then, upload and analysis will fail.
        </p>
      </div>
    </div>
  );
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mb-6 flex items-start justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <p className="text-foreground">{message}</p>
      </div>
      <button onClick={onDismiss} className="text-muted-foreground hover:text-foreground">✕</button>
    </div>
  );
}

// --- landing / upload ------------------------------------------------------

const FEATURES = [
  { Icon: FileText, title: "Clause extraction", body: "Identifies 10 standard clause types with page references — no hallucinated text." },
  { Icon: Scale, title: "Risk scoring", body: "AI grades every clause High / Medium / Low with a rationale and a weighted overall score." },
  { Icon: MessageSquareText, title: "RAG Q&A", body: "Ask questions and get answers grounded in the contract, with page citations." },
];

function Landing({ onFile }: { onFile: (f: File) => void }) {
  return (
    <div className="animate-fade-in space-y-10">
      <div className="mx-auto max-w-2xl pt-6 text-center">
        <Badge variant="secondary" className="mb-4 gap-1.5 font-normal">
          <Sparkles className="h-3 w-3" /> AI-powered contract analysis
        </Badge>
        <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
          Understand any contract in seconds
        </h1>
        <p className="mt-4 text-pretty text-lg text-muted-foreground">
          Upload a contract and get clause-level risk scoring, plain-English summaries, negotiation
          suggestions, and an AI assistant that answers questions with citations.
        </p>
      </div>
      <Dropzone onFile={onFile} />
      <div className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <Card key={f.title} className="transition-shadow hover:shadow-md">
            <CardHeader>
              <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <f.Icon className="h-5 w-5" />
              </div>
              <CardTitle className="text-base">{f.title}</CardTitle>
              <CardDescription>{f.body}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Dropzone({ onFile }: { onFile: (f: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  return (
    <Card
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]); }}
      className={cn(
        "bg-grid border-2 border-dashed transition-colors",
        drag ? "border-primary bg-primary/5" : "border-border"
      )}
    >
      <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Upload className="h-7 w-7" />
        </div>
        <div>
          <p className="text-lg font-medium">Drag &amp; drop a contract</p>
          <p className="text-sm text-muted-foreground">PDF up to 50 MB · a .txt also works for quick tests</p>
        </div>
        <Button size="lg" onClick={() => inputRef.current?.click()}>
          <Upload className="h-4 w-4" /> Choose file
        </Button>
        <input
          ref={inputRef} type="file" accept=".pdf,.txt" className="hidden"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
      </CardContent>
    </Card>
  );
}

// --- processing ------------------------------------------------------------

function Processing({ stage }: { stage: "uploading" | "analyzing" }) {
  const steps = [
    { key: "uploading", label: "Ingesting & embedding", sub: "Parsing, chunking and vectorising the document" },
    { key: "analyzing", label: "Multi-agent analysis", sub: "Extracting clauses, scoring risk, writing summaries & suggestions" },
  ];
  const activeIdx = stage === "uploading" ? 0 : 1;
  return (
    <Card className="mx-auto max-w-xl animate-fade-in">
      <CardContent className="space-y-6 py-10">
        <div className="flex items-center justify-center">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
        <Progress value={stage === "uploading" ? 45 : 85} />
        <div className="space-y-3">
          {steps.map((s, i) => (
            <div key={s.key} className="flex items-start gap-3">
              {i < activeIdx ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-risk-low" />
              ) : i === activeIdx ? (
                <Loader2 className="mt-0.5 h-5 w-5 animate-spin text-primary" />
              ) : (
                <div className="mt-0.5 h-5 w-5 rounded-full border-2 border-muted" />
              )}
              <div>
                <p className={cn("text-sm font-medium", i <= activeIdx ? "text-foreground" : "text-muted-foreground")}>{s.label}</p>
                <p className="text-xs text-muted-foreground">{s.sub}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// --- summary ---------------------------------------------------------------

function SummaryCard({ contract, onReset }: { contract: Contract; onReset: () => void }) {
  const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 } as Record<string, number>;
  contract.clauses.forEach((c) => c.risk_level && counts[c.risk_level]++);
  const meta = [
    ["Type", contract.contract_type],
    ["Governing law", contract.governing_law],
    ["Parties", contract.parties.join("  ·  ") || "Not detected"],
    ["Document", `${contract.page_count} pages · ${contract.chunk_count} chunks`],
  ] as const;

  return (
    <Card className="animate-fade-in overflow-hidden">
      <CardContent className="flex flex-col gap-6 p-6 lg:flex-row lg:items-center">
        <div className="flex items-center gap-5">
          <RiskGauge value={contract.overall_risk_score} />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="font-semibold">{contract.filename}</span>
            </div>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-0.5 text-sm sm:grid-cols-2">
              {meta.map(([k, v]) => (
                <div key={k} className="flex gap-1.5">
                  <dt className="text-muted-foreground">{k}:</dt>
                  <dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>

        <Separator className="lg:hidden" />
        <div className="lg:ml-auto" />

        <div className="flex items-center gap-6">
          {(["HIGH", "MEDIUM", "LOW"] as const).map((lvl) => {
            const m = riskMeta(lvl);
            return (
              <div key={lvl} className="text-center">
                <div className={cn("text-2xl font-bold tabular-nums", m.text)}>{counts[lvl]}</div>
                <RiskBadge level={lvl} />
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 lg:flex-col">
          <Button onClick={() => api.downloadReport(contract.contract_id, `ContractIQ_${contract.filename.replace(/\.[^.]+$/, "")}.pdf`).catch(() => {})}>
            <Download className="h-4 w-4" /> Export PDF
          </Button>
          <Button variant="outline" onClick={onReset}>New contract</Button>
        </div>
      </CardContent>
      {contract.warnings.length > 0 && (
        <div className="border-t bg-risk-medium/10 px-6 py-3 text-xs text-risk-medium">
          {contract.warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
        </div>
      )}
    </Card>
  );
}

// --- clause section --------------------------------------------------------

function ClauseSection({ contract }: { contract: Contract }) {
  const [sortKey, setSortKey] = useState<"risk" | "type">("risk");
  const clauses = [...contract.clauses].sort((a, b) =>
    sortKey === "risk" ? (b.risk_score ?? 0) - (a.risk_score ?? 0) : a.clause_type.localeCompare(b.clause_type)
  );

  return (
    <Card className="animate-fade-in">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">Clauses ({clauses.length})</CardTitle>
        <Tabs value={sortKey} onValueChange={(v) => setSortKey(v as "risk" | "type")}>
          <TabsList className="h-8">
            <TabsTrigger value="risk" className="text-xs">By risk</TabsTrigger>
            <TabsTrigger value="type" className="text-xs">By type</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent className="pt-0">
        <Table className="table-fixed">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[34%] sm:w-[26%]">Clause</TableHead>
              <TableHead className="w-[92px]">Risk</TableHead>
              <TableHead className="w-[56px] text-right">Score</TableHead>
              <TableHead className="hidden md:table-cell">Summary</TableHead>
              <TableHead className="w-9" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {clauses.map((c) => <ClauseRow key={c.clause_id} clause={c} />)}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ClauseRow({ clause }: { clause: Clause }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow className="cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <TableCell className="font-medium">
          <div className="flex items-start gap-1.5">
            <span className="leading-snug">{clause.clause_type}</span>
            {clause.is_ambiguous && (
              <Tooltip>
                <TooltipTrigger asChild><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-risk-medium" /></TooltipTrigger>
                <TooltipContent>Ambiguous language — review carefully</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TableCell>
        <TableCell><RiskBadge level={clause.risk_level} /></TableCell>
        <TableCell className={cn("text-right font-semibold tabular-nums", scoreTone(clause.risk_score ?? 0))}>
          {clause.risk_score ?? "—"}
        </TableCell>
        <TableCell className="hidden truncate text-muted-foreground md:table-cell">
          {clause.plain_english_summary}
        </TableCell>
        <TableCell className="text-right">
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
        </TableCell>
      </TableRow>
      {open && (
        <TableRow className="hover:bg-transparent">
          <TableCell colSpan={5} className="bg-muted/40">
            <div className="space-y-4 p-2">
              <p className="text-sm md:hidden">{clause.plain_english_summary}</p>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Risk rationale</p>
                <p className="text-sm">{clause.risk_rationale}</p>
              </div>
              {clause.negotiation_suggestion && (
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-risk-high/20 bg-risk-high/5 p-3">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-risk-high">Original language</p>
                    <p className="text-sm text-muted-foreground">{clause.original_text.slice(0, 360)}{clause.original_text.length > 360 ? "…" : ""}</p>
                  </div>
                  <div className="rounded-lg border border-risk-low/20 bg-risk-low/5 p-3">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-risk-low">Suggested language</p>
                    <p className="text-sm">{clause.negotiation_suggestion}</p>
                  </div>
                </div>
              )}
              {clause.page_references.length > 0 && (
                <p className="text-xs text-muted-foreground">Pages: {clause.page_references.join(", ")}</p>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// --- chat ------------------------------------------------------------------

const SUGGESTED = ["What are the payment terms?", "Can the vendor terminate without notice?", "Is liability capped?"];

function ChatPanel({ contractId, ready }: { contractId: string; ready: boolean }) {
  const [turns, setTurns] = useState<QATurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [turns, busy]);

  async function send(q?: string) {
    const query = (q ?? input).trim();
    if (!query || busy) return;
    setInput(""); setBusy(true);
    try {
      const turn = await api.chat(contractId, query);
      setTurns((t) => [...t, turn]);
    } catch (e) {
      setTurns((t) => [...t, { turn_id: `err-${Date.now()}`, user_query: query, agent_answer: humanError(e), citations: [], retrieved_chunks: [] }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="sticky top-20 flex h-[36rem] flex-col">
      <CardHeader className="flex-row items-center gap-2 space-y-0 border-b py-3">
        <MessageSquareText className="h-4 w-4 text-primary" />
        <CardTitle className="text-base">Ask about this contract</CardTitle>
      </CardHeader>
      <ScrollArea className="flex-1">
        <div ref={scrollRef} className="flex h-full flex-col gap-4 p-4">
          {turns.length === 0 && (
            <div className="space-y-3 pt-2">
              <p className="text-sm text-muted-foreground">Try one of these:</p>
              {SUGGESTED.map((s) => (
                <button key={s} onClick={() => send(s)} disabled={!ready}
                  className="block w-full rounded-lg border bg-card px-3 py-2 text-left text-sm transition-colors hover:bg-accent disabled:opacity-50">
                  {s}
                </button>
              ))}
            </div>
          )}
          {turns.map((t) => (
            <div key={t.turn_id} className="space-y-2">
              <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground">
                {t.user_query}
              </div>
              <div className="w-fit max-w-[92%] rounded-2xl rounded-tl-sm bg-muted px-3.5 py-2 text-sm">
                <p className="whitespace-pre-wrap">{t.agent_answer}</p>
                {t.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-2 text-xs text-muted-foreground">
                    <Quote className="h-3 w-3" />
                    {t.citations.map((c, i) => <span key={i} className="rounded bg-background px-1.5 py-0.5">{c}</span>)}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
            </div>
          )}
        </div>
      </ScrollArea>
      <div className="flex items-center gap-2 border-t p-3">
        <Input
          value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={ready ? "Ask a question…" : "Configure AI to enable chat"}
          disabled={!ready || busy}
        />
        <Button size="icon" onClick={() => send()} disabled={!ready || busy}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
