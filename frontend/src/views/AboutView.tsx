import React, { useState } from 'react';
import { ServerStatus } from '../types';

interface AboutViewProps {
  status: ServerStatus | null;
}

export const AboutView: React.FC<AboutViewProps> = ({ status }) => {
  const [copiedCode, setCopiedCode] = useState(false);

  const pythonSnippet = `from openai import OpenAI

# Connect to your Noora AI LAN Server
client = OpenAI(
    base_url="${status?.api_base_url || 'http://192.168.1.100:8080/v1'}",
    api_key="YOUR_API_KEY_HERE"  # Generate in the API Keys tab
)

response = client.chat.completions.create(
    model="local-ai",
    messages=[
        {"role": "user", "content": "Hello Noora, what can you help me with?"}
    ]
)

print(response.choices[0].message.content)`;

  const copyCode = () => {
    navigator.clipboard.writeText(pythonSnippet);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Brand Profile Banner */}
      <div className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-xl shadow-indigo-500/30 text-white text-3xl">
              <i className="bx bx-bot"></i>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-2xl font-black text-white tracking-tight">Noora AI</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  v1.0.0
                </span>
              </div>
              <p className="text-sm font-semibold text-indigo-400 mt-0.5">
                On-Demand Local LAN AI Server
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Engineered & Developed by <span className="font-bold text-slate-200">Nadeem</span>
              </p>
            </div>
          </div>

          <p className="mt-5 text-sm text-slate-300 leading-relaxed max-w-2xl">
            Noora AI transforms your Windows laptop into a fully private, on-demand AI server. It exposes a standard OpenAI-compatible API endpoint across your local Wi-Fi or Ethernet network without relying on cloud services, tunnels, or third-party gateways.
          </p>
        </div>

        {/* Ambient subtle glow */}
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Hardware Architecture & Specifications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-6 rounded-2xl space-y-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <i className="bx bx-chip text-indigo-400"></i>
            Hardware Architecture
          </h3>
          <ul className="text-xs space-y-2 text-slate-400">
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Target Processor:</span>
              <span className="font-semibold text-slate-200">Intel Core i5 (CPU Inference)</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Target Memory:</span>
              <span className="font-semibold text-slate-200">4GB RAM (Low-Footprint)</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Inference Engine:</span>
              <span className="font-semibold text-slate-200">llama.cpp (llama-server)</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Model Quantization:</span>
              <span className="font-semibold text-slate-200">GGUF (Q4_K_M)</span>
            </li>
            <li className="flex justify-between py-1">
              <span>Dedicated GPU:</span>
              <span className="font-semibold text-emerald-400">Not Required (100% CPU)</span>
            </li>
          </ul>
        </div>

        <div className="glass-card p-6 rounded-2xl space-y-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <i className="bx bx-lock-alt text-indigo-400"></i>
            Security & Privacy
          </h3>
          <ul className="text-xs space-y-2 text-slate-400">
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Network Isolation:</span>
              <span className="font-semibold text-slate-200">Local LAN Subnet Only</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Key Hashing:</span>
              <span className="font-semibold text-slate-200">SHA-256 (Secrets never stored)</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Inference Loopback:</span>
              <span className="font-semibold text-slate-200">127.0.0.1 Binding Only</span>
            </li>
            <li className="flex justify-between py-1 border-b border-slate-800">
              <span>Cloud Dependency:</span>
              <span className="font-semibold text-emerald-400">Zero (Completely Air-gapped)</span>
            </li>
            <li className="flex justify-between py-1">
              <span>On-Demand Lifecycle:</span>
              <span className="font-semibold text-slate-200">Full RAM release on stop</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Quick Python Integration Code */}
      <div className="glass-panel p-6 rounded-2xl space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <i className="bx bxl-python text-indigo-400 text-lg"></i>
            OpenAI Python SDK Integration Sample
          </h3>
          <button
            onClick={copyCode}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all active:scale-95"
          >
            <i className={`bx ${copiedCode ? 'bx-check' : 'bx-copy'}`}></i>
            <span>{copiedCode ? 'Copied!' : 'Copy Code'}</span>
          </button>
        </div>

        <pre className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed">
          {pythonSnippet}
        </pre>
      </div>
    </div>
  );
};
