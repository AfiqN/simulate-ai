import { useState, useEffect } from "react";

export interface LLMSettings {
  apiKey: string;
  provider: "gemini" | "openai";
  model: string;
}

const STORAGE_KEY = "simulateai_settings";
const LEGACY_STORAGE_KEY = "simulate-ai-settings";
const DEFAULT_MODELS: Record<string, string> = {
  gemini: "gemma-4-26b-a4b-it",
  openai: "gpt-4o",
};

export function getStoredSettings(): LLMSettings | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
      || localStorage.getItem(STORAGE_KEY)
      || localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return null;
    const settings = JSON.parse(raw) as LLMSettings;
    // Migrate persistent legacy settings to tab-scoped storage.
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    return settings;
  } catch {
    return null;
  }
}

export function getApiKey(): string | null {
  const s = getStoredSettings();
  return s?.apiKey || null;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SettingsPanel({ open, onClose }: Props) {
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState<"gemini" | "openai">("gemini");
  const [model, setModel] = useState(DEFAULT_MODELS.gemini);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const existing = getStoredSettings();
    if (existing) {
      setApiKey(existing.apiKey);
      setProvider(existing.provider);
      setModel(existing.model);
    }
  }, [open]);

  const handleSave = () => {
    const settings: LLMSettings = { apiKey, provider, model };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClear = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_STORAGE_KEY);
    setApiKey("");
    setProvider("gemini");
    setModel(DEFAULT_MODELS.gemini);
  };

  const handleProviderChange = (p: "gemini" | "openai") => {
    setProvider(p);
    setModel(DEFAULT_MODELS[p]);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-[10px] border border-[#E5E5E5] shadow-lg w-full max-w-[480px] p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[17px] font-medium tracking-[-0.02em]">API Settings</h2>
          <button onClick={onClose} className="text-[#9B9B9B] hover:text-[#0F0F0F] text-[20px]">&times;</button>
        </div>

        <div className="bg-[#F8FFFE] border border-[#D1FAE5] rounded-[6px] p-3">
          <p className="text-[12px] text-[#065F46] leading-relaxed">
            Your API key is stored for this browser tab only (sessionStorage). It is sent per request over HTTPS and never persisted by our server. Like any browser storage, it still depends on the page remaining free of XSS vulnerabilities.{" "}
            <a
              href="https://github.com/AfiqN/simulate-ai/blob/master/src/api/queue.py"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium"
            >
              Verify in source code
            </a>
          </p>
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
            Provider
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => handleProviderChange("gemini")}
              className={`px-3 py-1.5 text-[13px] rounded-[6px] border transition-colors ${
                provider === "gemini"
                  ? "border-[#1A1A1A] bg-[#1A1A1A] text-white"
                  : "border-[#E5E5E5] text-[#6B6B6B] hover:border-[#D0D0D0]"
              }`}
            >
              Gemini
            </button>
            <button
              onClick={() => handleProviderChange("openai")}
              className={`px-3 py-1.5 text-[13px] rounded-[6px] border transition-colors ${
                provider === "openai"
                  ? "border-[#1A1A1A] bg-[#1A1A1A] text-white"
                  : "border-[#E5E5E5] text-[#6B6B6B] hover:border-[#D0D0D0]"
              }`}
            >
              OpenAI
            </button>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider === "gemini" ? "AIza..." : "sk-..."}
            className="w-full px-3 py-2 text-[14px] border border-[#E5E5E5] rounded-[6px] focus:outline-none focus:border-[#0F0F0F] font-mono"
          />
          <p className="text-[11px] text-[#9B9B9B]">
            {provider === "gemini" ? (
              <>Get a free key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="underline">Google AI Studio</a></>
            ) : (
              <>Get a key at <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline">OpenAI Platform</a></>
            )}
          </p>
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
            Model
          </label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="Model name"
            className="w-full px-3 py-2 text-[14px] border border-[#E5E5E5] rounded-[6px] focus:outline-none focus:border-[#0F0F0F] font-mono"
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={!apiKey.trim()}
            className="px-4 py-2 text-[13px] font-medium bg-[#1A1A1A] text-white rounded-[6px] hover:bg-[#333] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {saved ? "Saved!" : "Save"}
          </button>
          <button
            onClick={handleClear}
            className="px-4 py-2 text-[13px] text-[#6B6B6B] hover:text-[#0F0F0F] transition-colors"
          >
            Clear & use demo
          </button>
        </div>

        <p className="text-[11px] text-[#9B9B9B] leading-relaxed">
          Without your own key, you get 3 demo runs per day. BYOK raises the abuse-protection limit to 30 runs/day and provider usage is billed to your account.
        </p>
      </div>
    </div>
  );
}
