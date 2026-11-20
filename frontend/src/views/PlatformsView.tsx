import React, { useState, useEffect } from 'react';
import type { ServerStatus } from '../types';
import { api } from '../services/api';

interface PlatformsViewProps {
  status: ServerStatus | null;
}

export const PlatformsView: React.FC<PlatformsViewProps> = ({ status }) => {
  const [activeKey, setActiveKey] = useState<string>('sk-local-noora-default-lan-key');
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedPython, setCopiedPython] = useState(false);
  const [copiedPs, setCopiedPs] = useState(false);
  const [testingPing, setTestingPing] = useState(false);
  const [pingResult, setPingResult] = useState<{ success: boolean; latency: number; response: string } | null>(null);

  const lanUrl = status?.api_base_url || 'http://192.168.1.100:8080/v1';

  useEffect(() => {
    api.getActiveKeyInfo().then(data => {
      if (data?.raw_key) {
        setActiveKey(data.raw_key);
      }
    }).catch(() => {});
  }, []);

  const copyToClipboard = (text: string, setFn: (val: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setFn(true);
    setTimeout(() => setFn(false), 2000);
  };

  const runLivePingTest = async () => {
    setTestingPing(true);
    setPingResult(null);
    const start = performance.now();

    try {
      const res = await fetch(`${lanUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${activeKey}`
        },
        body: JSON.stringify({
          model: 'local-ai',
          messages: [{ role: 'user', content: 'Say "Working OK" in 2 words.' }],
          max_tokens: 10
        })
      });

      const data = await res.json();
      const end = performance.now();

      if (!res.ok) {
        throw new Error(data.detail || `Server returned HTTP ${res.status}`);
      }

      setPingResult({
        success: true,
        latency: Math.round(end - start),
        response: data.choices?.[0]?.message?.content || 'OK'
      });
    } catch (err: any) {
      const end = performance.now();
      setPingResult({
        success: false,
        latency: Math.round(end - start),
        response: err.message || 'Connection failed'
      });
    } finally {
      setTestingPing(false);
    }
  };

  const curlCommand = `curl -X POST "${lanUrl}/chat/completions" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${activeKey}" \\
  -d '{
    "model": "N.1 Faster",
    "messages": [{"role": "user", "content": "Hello Noora! Introduce yourself."}],
    "max_tokens": 100
  }'`;

  const pythonScript = `from openai import OpenAI

# Connect from any phone, laptop, or server on the same Wi-Fi
# Models available (Developed & Trained by Nadeem):
# - "N.1 Faster" (Speed / Low-Latency)
# - "N.1 Pro"    (Code & Deep Reasoning)
# - "N.1 Core"   (Balanced Knowledge)
# - "local-ai"   (Active server model)

client = OpenAI(
    base_url="${lanUrl}",
    api_key="${activeKey}"
)

completion = client.chat.completions.create(
    model="N.1 Faster",
    messages=[
        {"role": "user", "content": "Hello Noora! Are you working on our local LAN?"}
    ]
)

print(completion.choices[0].message.content)`;

  const powershellCommand = `$headers = @{
    "Content-Type"  = "application/json"
    "Authorization" = "Bearer ${activeKey}"
}
$body = @{
    model    = "N.1 Faster"
    messages = @(@{ role = "user"; content = "Hello Noora!" })
} | ConvertTo-Json

Invoke-RestMethod -Uri "${lanUrl}/chat/completions" -Method POST -Headers $headers -Body $body`;

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <i className="bx bx-devices text-indigo-400"></i>
            Example Platforms & Client Setup
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Connect devices on the same Wi-Fi (iPhone, Android, secondary PC) to your Noora AI Server.
          </p>
        </div>

        {/* Live Ping Verification Button */}
        <button
          onClick={runLivePingTest}
          disabled={testingPing}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/30 transition-all active:scale-95 disabled:opacity-50"
        >
          <i className={`bx ${testingPing ? 'bx-loader-alt animate-spin' : 'bx-broadcast'} text-base`}></i>
          <span>{testingPing ? 'Testing Connection...' : 'Test Connection (Ping)'}</span>
        </button>
      </div>

      {/* Ping Result Banner */}
      {pingResult && (
        <div className={`p-4 rounded-xl border flex items-center justify-between ${
          pingResult.success
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
        }`}>
          <div className="flex items-center space-x-3 text-xs">
            <i className={`bx ${pingResult.success ? 'bx-check-circle text-xl' : 'bx-error-circle text-xl'}`}></i>
            <div>
              <span className="font-bold block">
                {pingResult.success ? 'API & AI Engine Tested Successfully!' : 'Test Failed'}
              </span>
              <span className="text-slate-300">
                {pingResult.success
                  ? `Response: "${pingResult.response}" • Latency: ${pingResult.latency} ms`
                  : `Error: ${pingResult.response}`}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900">
            {pingResult.latency} ms
          </span>
        </div>
      )}

      {/* Connection Credentials Card */}
      <div className="glass-card p-5 rounded-2xl border border-indigo-500/30 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <i className="bx bx-key text-indigo-400"></i>
          Your Ready-to-Use Connection Credentials
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="text-slate-400 font-medium block mb-1">OpenAI API Host / Base URL</label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                readOnly
                value={lanUrl}
                className="w-full glass-input px-3 py-2 rounded-xl font-mono text-slate-200 select-all focus:outline-none"
              />
              <button
                onClick={() => copyToClipboard(lanUrl, setCopiedKey)}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium whitespace-nowrap"
              >
                Copy
              </button>
            </div>
          </div>

          <div>
            <label className="text-slate-400 font-medium block mb-1">Active Working API Key</label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                readOnly
                value={activeKey}
                className="w-full glass-input px-3 py-2 rounded-xl font-mono text-amber-300 select-all focus:outline-none"
              />
              <button
                onClick={() => copyToClipboard(activeKey, setCopiedKey)}
                className="px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold whitespace-nowrap"
              >
                {copiedKey ? 'Copied!' : 'Copy Key'}
              </button>
            </div>
          </div>
        </div>

        <div className="pt-2 text-[11px] text-slate-400 space-y-1">
          <div className="flex items-center space-x-2">
            <i className="bx bx-chip text-indigo-400 text-sm"></i>
            <span className="font-semibold text-slate-200">Available Noora Models (Trained & Developed by Nadeem):</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-emerald-400 font-bold block">"N.1 Faster"</span>
              <span className="text-slate-400 text-[10px]">Speed & Ultra-Low Latency</span>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-indigo-400 font-bold block">"N.1 Pro"</span>
              <span className="text-slate-400 text-[10px]">Deep Reasoning & Coding</span>
            </div>
            <div className="p-2 rounded bg-slate-900 border border-slate-800">
              <span className="text-amber-400 font-bold block">"N.1 Core"</span>
              <span className="text-slate-400 text-[10px]">Balanced Knowledge</span>
            </div>
          </div>
          <p className="text-[10px] text-slate-500 pt-1">
            Pass any of these IDs in the <code className="text-indigo-300">"model"</code> parameter or use <code className="text-indigo-300">"local-ai"</code> for the active model.
          </p>
        </div>
      </div>

      {/* Platform 1: Chatbox App (Recommended UI Client) */}
      <div className="glass-card p-6 rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/30 text-indigo-400 flex items-center justify-center text-2xl font-bold">
              <i className="bx bx-message-rounded-dots"></i>
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Platform 1: Chatbox (Free App for Windows, Android, iOS, Mac)</h4>
              <p className="text-xs text-slate-400">The easiest free client to chat with Noora AI from any phone or PC.</p>
            </div>
          </div>
          <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
            Recommended
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 space-y-2">
          <ol className="list-decimal list-inside space-y-1.5 leading-relaxed">
            <li>Download <strong>Chatbox</strong> on your phone, iPad, or secondary computer (chatboxai.app).</li>
            <li>Go to <strong>Settings → Model Provider</strong> and select <strong>OpenAI API</strong>.</li>
            <li>Set <strong>API Host</strong> to: <code className="text-indigo-400 font-mono font-bold">{lanUrl}</code></li>
            <li>Set <strong>API Key</strong> to: <code className="text-amber-400 font-mono font-bold">{activeKey}</code></li>
            <li>Set <strong>Model</strong> to: <code className="text-indigo-400 font-mono font-bold">N.1 Faster</code> (or <code className="text-indigo-300 font-mono">N.1 Pro</code> / <code className="text-indigo-300 font-mono">N.1 Core</code> / <code className="text-indigo-300 font-mono">local-ai</code>)</li>
            <li>Save and start chatting! You can now use your laptop's AI from anywhere in your house/office.</li>
          </ol>
        </div>
      </div>

      {/* Platform 2: Python Code */}
      <div className="glass-card p-6 rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bxl-python text-xl text-indigo-400"></i>
            <h4 className="text-sm font-bold text-white">Platform 2: Python (OpenAI SDK)</h4>
          </div>
          <button
            onClick={() => copyToClipboard(pythonScript, setCopiedPython)}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
          >
            {copiedPython ? 'Copied!' : 'Copy Python Script'}
          </button>
        </div>
        <pre className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed">
          {pythonScript}
        </pre>
      </div>

      {/* Platform 3: cURL Command */}
      <div className="glass-card p-6 rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bx-terminal text-xl text-indigo-400"></i>
            <h4 className="text-sm font-bold text-white">Platform 3: cURL (Linux / macOS / Git Bash)</h4>
          </div>
          <button
            onClick={() => copyToClipboard(curlCommand, setCopiedCurl)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            {copiedCurl ? 'Copied!' : 'Copy cURL'}
          </button>
        </div>
        <pre className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed">
          {curlCommand}
        </pre>
      </div>

      {/* Platform 4: Windows PowerShell */}
      <div className="glass-card p-6 rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bxl-windows text-xl text-indigo-400"></i>
            <h4 className="text-sm font-bold text-white">Platform 4: Windows PowerShell (Invoke-RestMethod)</h4>
          </div>
          <button
            onClick={() => copyToClipboard(powershellCommand, setCopiedPs)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            {copiedPs ? 'Copied!' : 'Copy PowerShell'}
          </button>
        </div>
        <pre className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed">
          {powershellCommand}
        </pre>
      </div>
    </div>
  );
};
