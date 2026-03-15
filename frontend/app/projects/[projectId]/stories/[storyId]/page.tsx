"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import MermaidDiagram from "@/components/diagrams/MermaidDiagram";

interface Story {
  id: string;
  jira_issue_key: string;
  jira_summary: string;
  jira_description: string | null;
  jira_acceptance_criteria: string | null;
  status: string;
  tdd_document: string | null;
  mermaid_erd: string | null;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

type ActiveTab = "tdd" | "erd";

export default function StoryDetailPage() {
  const { projectId, storyId } = useParams<{ projectId: string; storyId: string }>();
  const router = useRouter();

  const [story, setStory] = useState<Story | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("tdd");
  const [tddContent, setTddContent] = useState<string>("");

  // Chat state
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Pipeline actions
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const loadStory = async () => {
    const r = await fetch(`/api/pipeline/stories/${storyId}`);
    const data: Story = await r.json();
    setStory(data);
    if (data.tdd_document) setTddContent(data.tdd_document);
  };

  useEffect(() => { loadStory(); }, [storyId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  // ── Pipeline actions ──────────────────────────────────────────────────────
  const draftTDD = async () => {
    setActionLoading(true);
    setActionMsg("Asking Claude to generate TDD…");
    await fetch(`/api/pipeline/stories/${storyId}/draft-tdd`, { method: "POST" });
    // Poll for completion
    const poll = setInterval(async () => {
      const r = await fetch(`/api/pipeline/stories/${storyId}`);
      const data: Story = await r.json();
      if (data.tdd_document) {
        setStory(data);
        setTddContent(data.tdd_document);
        setActionMsg("TDD generated. Review and refine below, then confirm.");
        setActionLoading(false);
        clearInterval(poll);
      }
    }, 3000);
  };

  const approveTDD = async () => {
    setActionLoading(true);
    setActionMsg("Approving TDD and starting development…");
    await fetch(`/api/pipeline/stories/${storyId}/approve-tdd`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved: true }),
    });
    await loadStory();
    setActionMsg("Development started! Assign a developer to implement.");
    setActionLoading(false);
  };

  // ── LLM Chat ──────────────────────────────────────────────────────────────
  const sendMessage = async () => {
    const msg = input.trim();
    if (!msg || chatLoading) return;
    setInput("");

    const userMsg: ChatMessage = { role: "user", content: msg };
    const newHistory = [...history, userMsg];
    setHistory(newHistory);
    setChatLoading(true);

    try {
      const r = await fetch(`/api/chat/stories/${storyId}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, history }),
      });
      const data = await r.json();

      const assistantMsg: ChatMessage = { role: "assistant", content: data.reply };
      setHistory([...newHistory, assistantMsg]);

      if (data.updated_tdd) {
        setTddContent(data.updated_tdd);
        setStory((s) => s ? { ...s, tdd_document: data.updated_tdd } : s);
      }
    } catch {
      setHistory([...newHistory, { role: "assistant", content: "Error — please try again." }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (!story) return <div className="p-10 text-gray-400 text-sm">Loading story…</div>;

  const canDraft = story.status === "STORY_LOADED";
  const canApprove = story.status === "TDD_DRAFTED" && !!tddContent;
  const isDone = !["STORY_LOADED", "TDD_DRAFTED"].includes(story.status);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b px-5 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}/stories`} className="text-sm text-blue-600 hover:underline">
            ← Stories
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-mono text-sm text-gray-500">{story.jira_issue_key}</span>
          <span className="text-gray-900 font-medium text-sm truncate max-w-xs">{story.jira_summary}</span>
          <StatusPill status={story.status} />
        </div>

        <div className="flex items-center gap-2">
          {actionMsg && <span className="text-xs text-blue-600">{actionMsg}</span>}
          {canDraft && (
            <ActionBtn label="✨ Generate TDD" onClick={draftTDD} loading={actionLoading} color="blue" />
          )}
          {canApprove && (
            <ActionBtn label="✅ Confirm & Start Dev" onClick={approveTDD} loading={actionLoading} color="green" />
          )}
          {isDone && (
            <span className="text-xs text-green-700 bg-green-50 px-3 py-1.5 rounded">
              Development in progress
            </span>
          )}
        </div>
      </header>

      {/* Main split layout */}
      <div className="flex flex-1 min-h-0">
        {/* LEFT — Story details */}
        <aside className="w-72 shrink-0 border-r bg-white overflow-y-auto p-4 space-y-4">
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Summary</h3>
            <p className="text-sm text-gray-800">{story.jira_summary}</p>
          </div>

          {story.jira_description && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Description</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{story.jira_description}</p>
            </div>
          )}

          {story.jira_acceptance_criteria && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                Acceptance Criteria
              </h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{story.jira_acceptance_criteria}</p>
            </div>
          )}
        </aside>

        {/* CENTRE — TDD / ERD viewer */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b bg-white shrink-0">
            {(["tdd", "erd"] as ActiveTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab === "tdd" ? "📄 Technical Design" : "🔗 ERD"}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {activeTab === "tdd" ? (
              tddContent ? (
                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                  {tddContent}
                </pre>
              ) : (
                <EmptyState
                  icon="📄"
                  title="No TDD yet"
                  desc={canDraft ? "Click Generate TDD to have Claude create the technical design document." : "TDD will appear here once generated."}
                />
              )
            ) : story.mermaid_erd ? (
              <MermaidDiagram chart={`erDiagram\n${story.mermaid_erd}`} />
            ) : (
              <EmptyState icon="🔗" title="No ERD yet" desc="ERD is generated alongside the TDD." />
            )}
          </div>
        </main>

        {/* RIGHT — LLM Chat */}
        <aside className="w-80 shrink-0 border-l bg-white flex flex-col">
          <div className="px-4 py-3 border-b shrink-0">
            <h2 className="text-sm font-semibold text-gray-800">✨ Refine with Claude</h2>
            <p className="text-xs text-gray-400 mt-0.5">Ask Claude to adjust the TDD before confirming</p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {history.length === 0 && (
              <div className="text-xs text-gray-400 text-center mt-4 space-y-2">
                <p>💬 Chat with Claude to refine the TDD</p>
                <div className="space-y-1">
                  {[
                    "Add a test class strategy section",
                    "Include flow automation instead of triggers",
                    "Add FLS checks to the Apex service",
                  ].map((s) => (
                    <button
                      key={s}
                      onClick={() => setInput(s)}
                      className="block w-full text-left text-xs bg-gray-50 border rounded px-2 py-1.5 hover:bg-blue-50 hover:border-blue-200 transition"
                    >
                      "{s}"
                    </button>
                  ))}
                </div>
              </div>
            )}
            {history.map((msg, i) => (
              <div
                key={i}
                className={`text-xs rounded-lg px-3 py-2 max-w-full ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white ml-4"
                    : "bg-gray-100 text-gray-800 mr-4"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
              </div>
            ))}
            {chatLoading && (
              <div className="bg-gray-100 text-gray-500 text-xs rounded-lg px-3 py-2 mr-4 animate-pulse">
                Claude is thinking…
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Input */}
          <div className="border-t p-3 shrink-0">
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder={tddContent ? "Ask Claude to refine the TDD…" : "Generate the TDD first"}
                disabled={!tddContent || chatLoading}
                rows={2}
                className="flex-1 text-xs border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:bg-gray-50"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || chatLoading || !tddContent}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 disabled:opacity-40 self-end"
              >
                Send
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1">Enter to send · Shift+Enter for newline</p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    STORY_LOADED: "bg-blue-100 text-blue-700",
    TDD_DRAFTED: "bg-yellow-100 text-yellow-700",
    TDD_APPROVED: "bg-green-100 text-green-700",
    IN_DEVELOPMENT: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function ActionBtn({
  label, onClick, loading, color,
}: {
  label: string; onClick: () => void; loading: boolean; color: "blue" | "green";
}) {
  const base = color === "green"
    ? "bg-green-600 hover:bg-green-700"
    : "bg-blue-600 hover:bg-blue-700";
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`px-4 py-1.5 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition ${base}`}
    >
      {loading ? "Working…" : label}
    </button>
  );
}

function EmptyState({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-2 text-gray-400">
      <span className="text-4xl">{icon}</span>
      <p className="font-medium text-gray-600">{title}</p>
      <p className="text-sm max-w-xs">{desc}</p>
    </div>
  );
}
