import { useState, useEffect } from "react";
import { Globe, Plus, Trash2, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Webhook } from "../../types";

const AVAILABLE_EVENTS = [
  "simulation.started",
  "simulation.completed",
  "simulation.failed",
];

export function WebhookManager() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formUrl, setFormUrl] = useState("");
  const [formSecret, setFormSecret] = useState("");
  const [formEvents, setFormEvents] = useState<string[]>(["simulation.completed"]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWebhooks = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/webhooks");
      if (res.ok) {
        const data = await res.json();
        setWebhooks(data.webhooks || []);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formUrl.trim()) return;
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch("/api/webhooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: formUrl.trim(),
          events: formEvents,
          secret: formSecret.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setFormUrl("");
      setFormSecret("");
      setFormEvents(["simulation.completed"]);
      setShowForm(false);
      await fetchWebhooks();
    } catch (err: any) {
      setError(err.message || "Failed to create webhook");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/webhooks/${id}`, { method: "DELETE" });
      setWebhooks((prev) => prev.filter((w) => w.id !== id));
    } catch {
      // ignore
    }
  };

  const toggleEvent = (event: string) => {
    setFormEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Webhooks</CardTitle>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchWebhooks}
              className="p-1.5 rounded-[4px] hover:bg-[#F5F5F5] transition-colors"
              title="Refresh"
            >
              <RefreshCw size={13} className="text-[#9B9B9B]" />
            </button>
            {!showForm && (
              <Button size="sm" onClick={() => setShowForm(true)}>
                <Plus size={12} className="mr-1" />
                Add
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Create form */}
        {showForm && (
          <form onSubmit={handleCreate} className="mb-4 p-3 rounded-[6px] border border-[#E5E5E5] space-y-3">
            <div>
              <label className="text-[11px] text-[#6B6B6B] uppercase tracking-wider block mb-1">
                Endpoint URL
              </label>
              <input
                type="url"
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
                placeholder="https://your-server.com/webhook"
                required
                className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-[6px] bg-white text-[#0F0F0F] placeholder:text-[#9B9B9B] focus:outline-none focus:border-[#0F0F0F] transition-colors"
              />
            </div>

            <div>
              <label className="text-[11px] text-[#6B6B6B] uppercase tracking-wider block mb-1">
                Secret (optional, for HMAC signing)
              </label>
              <input
                type="text"
                value={formSecret}
                onChange={(e) => setFormSecret(e.target.value)}
                placeholder="your-webhook-secret"
                className="w-full px-3 py-2 text-[13px] border border-[#E5E5E5] rounded-[6px] bg-white text-[#0F0F0F] placeholder:text-[#9B9B9B] focus:outline-none focus:border-[#0F0F0F] transition-colors"
              />
            </div>

            <div>
              <label className="text-[11px] text-[#6B6B6B] uppercase tracking-wider block mb-1.5">
                Events
              </label>
              <div className="flex flex-wrap gap-1.5">
                {AVAILABLE_EVENTS.map((ev) => (
                  <button
                    key={ev}
                    type="button"
                    onClick={() => toggleEvent(ev)}
                    className={`px-2.5 py-1 text-[11px] rounded-[4px] border transition-colors ${
                      formEvents.includes(ev)
                        ? "border-[#0F0F0F] bg-[#0F0F0F] text-white"
                        : "border-[#E5E5E5] bg-white text-[#6B6B6B] hover:border-[#9B9B9B]"
                    }`}
                  >
                    {ev}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <p className="text-[12px] text-[#8B1A1A]">{error}</p>
            )}

            <div className="flex items-center gap-2 pt-1">
              <Button type="submit" size="sm" disabled={submitting || formEvents.length === 0}>
                {submitting ? "Creating..." : "Create Webhook"}
              </Button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setError(null); }}
                className="px-3 py-1.5 text-[12px] text-[#6B6B6B] hover:text-[#0F0F0F] transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* List */}
        {loading ? (
          <p className="text-[12px] text-[#9B9B9B]">Loading...</p>
        ) : webhooks.length === 0 ? (
          <div className="text-center py-6">
            <Globe size={20} className="mx-auto text-[#9B9B9B] mb-2" />
            <p className="text-[12px] text-[#9B9B9B]">No webhooks configured</p>
            <p className="text-[11px] text-[#9B9B9B] mt-1">Webhooks notify external services when simulations complete.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {webhooks.map((wh) => (
              <div
                key={wh.id}
                className="flex items-center gap-3 p-3 rounded-[6px] border border-[#E5E5E5] group"
              >
                <div className="flex-shrink-0">
                  {wh.active ? (
                    <CheckCircle size={14} className="text-[#16653A]" />
                  ) : (
                    <XCircle size={14} className="text-[#8B1A1A]" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-[13px] text-[#0F0F0F] truncate font-['JetBrains_Mono']">
                    {wh.url}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    {wh.events.map((ev) => (
                      <Badge key={ev} variant="secondary" size="sm">{ev}</Badge>
                    ))}
                    {!wh.active && (
                      <Badge variant="destructive" size="sm">Disabled</Badge>
                    )}
                    {wh.failure_count > 0 && wh.active && (
                      <span className="text-[10px] text-[#D97706]">
                        {wh.failure_count} failure{wh.failure_count > 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(wh.id)}
                  className="flex-shrink-0 p-1.5 rounded-[4px] opacity-0 group-hover:opacity-100 hover:bg-[#FEF2F2] transition-all"
                  title="Delete webhook"
                >
                  <Trash2 size={13} className="text-[#8B1A1A]" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
