import React, { useState, useEffect, useRef } from 'react';
import type { ServerStatus, ModelItem, ApiKeyItem } from '../types';
import { api } from '../services/api';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  time?: string;
  tokensPerSec?: number;
}

interface ParsedSource {
  title: string;
  url: string;
  domain: string;
  snippet?: string;
}

function parseMessageContent(rawContent: string): { mainText: string; sources: ParsedSource[] } {
  if (!rawContent) return { mainText: '', sources: [] };

  // Check for <details class="noora-sources-accordion"
  const detailsIndex = rawContent.indexOf('<details class="noora-sources-accordion"');
  const legacyIndex = rawContent.indexOf('🌐 **Web Sources:**');

  const splitIndex = detailsIndex !== -1 ? detailsIndex : legacyIndex;
  if (splitIndex === -1) {
    return { mainText: rawContent.trim(), sources: [] };
  }

  const mainText = rawContent.slice(0, splitIndex).trim();
  const sourcesPart = rawContent.slice(splitIndex);

  const sources: ParsedSource[] = [];
  // Match markdown links: [Title](url) — *Source*
  const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)(?:\s*—\s*\*([^*]+)\*)?/g;
  let match;
  while ((match = linkRegex.exec(sourcesPart)) !== null) {
    const title = match[1];
    const url = match[2];
    let domain = match[3] || '';
    if (!domain && url.includes('://')) {
      domain = url.split('://')[1].split('/')[0];
    }
    // Check if there is a blockquote snippet after it
    const afterPos = match.index + match[0].length;
    const snippetMatch = sourcesPart.slice(afterPos, afterPos + 300).match(/>\s*([^\n<]+)/);
    const snippet = snippetMatch ? snippetMatch[1].trim() : undefined;

    sources.push({
      title,
      url,
      domain: domain || 'Web Source',
      snippet
    });
  }

  return { mainText, sources };
}

const AssistantMessageBubble: React.FC<{ content: string; time?: string; isGenerating?: boolean }> = ({ content, time, isGenerating }) => {
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const { mainText, sources } = parseMessageContent(content);
  const hasSources = sources.length > 0;

  return (
    <div className="max-w-[85%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed bg-slate-900/90 text-slate-200 border border-slate-800 shadow-md rounded-tl-sm space-y-2">
      <div className="flex items-center justify-between text-[10px] text-slate-400 pb-1 border-b border-slate-800/80">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-slate-300">Noora AI</span>
          {hasSources ? (
            <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] font-medium flex items-center gap-1">
              <i className="bx bx-globe"></i> Live Web Verified
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-medium flex items-center gap-1">
              <i className="bx bx-chip"></i> Direct Neural Knowledge
            </span>
          )}
        </div>
        <span>{time}</span>
      </div>

      {/* Main Response Text with Rich Markdown (Bold, Italic, Code, Lists) */}
      <div className="font-sans text-slate-200 text-xs sm:text-sm">
        {mainText ? (
          <MarkdownRenderer content={mainText} />
        ) : isGenerating ? (
          <span className="flex items-center space-x-1.5 text-indigo-400 py-1">
            <i className="bx bx-loader-alt animate-spin text-base"></i>
            <span>Analyzing question & generating answer on CPU...</span>
          </span>
        ) : content ? (
          <MarkdownRenderer content={content} />
        ) : null}
      </div>

      {/* Collapsible & Expandable Web Sources Section */}
      {hasSources && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <div className="rounded-xl border border-indigo-500/30 bg-slate-950/70 overflow-hidden">
            <button
              type="button"
              onClick={() => setSourcesOpen(!sourcesOpen)}
              className="w-full px-3 py-2 bg-slate-900/80 hover:bg-slate-900 flex items-center justify-between text-xs font-semibold text-indigo-300 transition-colors cursor-pointer"
            >
              <div className="flex items-center space-x-2">
                <i className="bx bx-globe text-cyan-400 text-sm"></i>
                <span>Web Sources & Citations</span>
                <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">
                  {sources.length} sources
                </span>
              </div>
              <div className="flex items-center space-x-1 text-[11px] text-slate-400">
                <span>{sourcesOpen ? 'Hide Sources' : 'Expand Sources'}</span>
                <i className={`bx ${sourcesOpen ? 'bx-chevron-up' : 'bx-chevron-down'} text-base`}></i>
              </div>
            </button>

            {sourcesOpen && (
              <div className="p-3 space-y-2 border-t border-slate-800/80">
                {sources.map((s, sIdx) => (
                  <div key={sIdx} className="p-2.5 rounded-lg bg-slate-900/90 border border-slate-800/90 space-y-1 hover:border-indigo-500/40 transition-colors">
                    <div className="flex items-center justify-between gap-2">
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-semibold text-indigo-300 hover:text-indigo-200 hover:underline flex items-center gap-1.5 truncate"
                      >
                        <i className="bx bx-link-external shrink-0 text-[11px] text-slate-400"></i>
                        <span className="truncate">{s.title}</span>
                      </a>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700 shrink-0 font-mono">
                        {s.domain}
                      </span>
                    </div>
                    {s.snippet && (
                      <p className="text-[11px] text-slate-400 leading-relaxed pl-2 border-l-2 border-indigo-500/30">
                        {s.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

interface PlaygroundViewProps {
  status: ServerStatus | null;
  models: ModelItem[];
  keys: ApiKeyItem[];
  refreshStatus: () => void;
}

export const PlaygroundView: React.FC<PlaygroundViewProps> = ({ status, models, keys, refreshStatus }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I am Noora, developed and trained by Nadeem. I am running 100% locally on this machine with high speed and zero cloud dependencies. How can I assist you today?',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('N.1 Faster');
  const [selectedKey, setSelectedKey] = useState<string>('');
  const [activeRawKey, setActiveRawKey] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(512);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [systemPrompt, setSystemPrompt] = useState('You are Noora, an intelligent and courteous local AI assistant developed and trained by Nadeem. Running on Noora LAN AI Server.');
  const [showSettings, setShowSettings] = useState(false);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-collect working API Key
  useEffect(() => {
    api.getActiveKeyInfo().then(info => {
      if (info?.raw_key) {
        setActiveRawKey(info.raw_key);
        if (!selectedKey) {
          setSelectedKey(info.raw_key);
        }
      }
    }).catch(() => {});
  }, [keys]);

  // Check live internet connectivity
  useEffect(() => {
    api.getConnectivity().then(c => setIsOnline(c.online)).catch(() => setIsOnline(false));
    const timer = setInterval(() => {
      api.getConnectivity().then(c => setIsOnline(c.online)).catch(() => setIsOnline(false));
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const copyWorkingKey = () => {
    if (activeRawKey) {
      navigator.clipboard.writeText(activeRawKey);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputPrompt.trim() || isGenerating) return;

    // Check if server is offline and start it automatically
    if (status?.status !== 'ONLINE') {
      try {
        await api.startServer();
        refreshStatus();
      } catch (err: any) {
        alert(`Cannot start server: ${err.message}`);
        return;
      }
    }

    const userText = inputPrompt.trim();
    setInputPrompt('');

    const newMessages: Message[] = [
      ...messages,
      {
        role: 'user',
        content: userText,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];

    setMessages(newMessages);
    setIsGenerating(true);
    setLastLatencyMs(null);

    // Prepare assistant placeholder message
    const assistantMsgIndex = newMessages.length;
    setMessages([
      ...newMessages,
      {
        role: 'assistant',
        content: '',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);

    const startTime = performance.now();
    let accumulatedContent = '';

    try {
      const authHeader = selectedKey ? `Bearer ${selectedKey}` : 'Bearer auto';
      const endpoint = `${status?.api_base_url || 'http://127.0.0.1:8080/v1'}/chat/completions`;

      const reqMessages = [
        ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
        ...newMessages.map(m => ({ role: m.role, content: m.content }))
      ];

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': authHeader
        },
        body: JSON.stringify({
          model: selectedModel || 'local-ai',
          web_search: webSearchEnabled,
          messages: reqMessages,
          temperature,
          max_tokens: maxTokens,
          stream: true
        })
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned error HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) {
        throw new Error('Streaming not supported by browser.');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ') && !trimmed.endsWith('[DONE]')) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              const delta = data.choices?.[0]?.delta?.content || '';
              accumulatedContent += delta;

              setMessages(prev => {
                const updated = [...prev];
                if (updated[assistantMsgIndex]) {
                  updated[assistantMsgIndex] = {
                    ...updated[assistantMsgIndex],
                    content: accumulatedContent
                  };
                }
                return updated;
              });
            } catch {
              // ignore parse errors for partial chunks
            }
          }
        }
      }

      const totalTimeMs = Math.round(performance.now() - startTime);
      setLastLatencyMs(totalTimeMs);
    } catch (err: any) {
      setMessages(prev => {
        const updated = [...prev];
        if (updated[assistantMsgIndex]) {
          updated[assistantMsgIndex] = {
            ...updated[assistantMsgIndex],
            content: `⚠️ Error: ${err.message || 'Request timed out or failed. Check if AI engine is loaded.'}`
          };
        }
        return updated;
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Conversation cleared. How can I help you today?',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const samplePrompts = [
    'What is the latest release of Python in 2026?',
    'Write a quick Python script to parse a JSON file.',
    'Who are you and who developed and trained you?',
    'What are the latest news headlines in technology today?'
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-3">
      {/* Top Controls & Auto-Detected Key Banner */}
      <div className="glass-panel p-3.5 rounded-2xl flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>{status?.status === 'ONLINE' ? 'Model Loaded & Ready' : 'Ready (Auto-Start)'}</span>
          </div>

          {/* Model Selector with Capability Badges */}
          <div className="flex items-center space-x-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="glass-input px-2.5 py-1 rounded-lg text-slate-200 text-xs font-semibold focus:outline-none bg-slate-900 border border-indigo-500/40"
            >
              <optgroup label="Noora Models (Trained & Developed by Nadeem)">
                <option value="N.1 Faster">⚡ Noora N.1 Faster (Speed / Ultra-Low Latency)</option>
                <option value="N.1 Pro">🧠 Noora N.1 Pro Reasoning (Code & Deep Logic)</option>
                <option value="N.1 Core">⚖️ Noora N.1 Core (Balanced & Knowledge)</option>
              </optgroup>
              <optgroup label="Default & Local Files">
                <option value="local-ai">local-ai (Auto-Selected Active Model)</option>
                {models.map(m => (
                  <option key={m.id} value={m.filename}>{m.name} ({m.filename})</option>
                ))}
              </optgroup>
            </select>
            <span className="hidden lg:inline text-[11px] text-indigo-400 font-medium px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
              By Nadeem
            </span>
          </div>
        </div>

        {/* Working API Key Auto-Collector Bar */}
        <div className="flex items-center space-x-2 bg-slate-900/80 px-3 py-1 rounded-xl border border-indigo-500/30">
          <span className="text-indigo-400 font-semibold flex items-center gap-1">
            <i className="bx bx-key"></i> Active Key:
          </span>
          <span className="font-mono text-slate-300 max-w-[140px] truncate select-all">
            {activeRawKey || 'Auto-Detected'}
          </span>
          <button
            onClick={copyWorkingKey}
            className="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-[11px] transition-all flex items-center space-x-1"
            title="Copy API key to use on other Wi-Fi devices"
          >
            <i className={`bx ${copiedKey ? 'bx-check' : 'bx-copy'}`}></i>
            <span>{copiedKey ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>

        {/* Actions & AI Mode */}
        <div className="flex items-center space-x-2">
          {/* AI Mode: Automatic Intelligent Web Search */}
          <button
            onClick={() => setWebSearchEnabled(!webSearchEnabled)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              webSearchEnabled
                ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 hover:bg-indigo-600/30 shadow-sm'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
            title={
              webSearchEnabled
                ? (isOnline ? "AI Mode Active: AI automatically analyzes each question and triggers web search only when current/updated info is needed." : "AI Mode Active: Offline (Answers using 100% local model knowledge)")
                : "AI Mode: Web search forced OFF (Local model only)"
            }
          >
            <i className={`bx ${webSearchEnabled ? 'bx-brain' : 'bx-chip'} text-sm text-indigo-400`}></i>
            <span>AI Mode: {webSearchEnabled ? 'Auto Web Search' : 'Local Only'}</span>
            <span
              className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
              title={isOnline ? "Internet Online (Live Search Ready)" : "Internet Offline (Local Model Active)"}
            ></span>
          </button>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`px-2.5 py-1 rounded-lg border text-xs flex items-center space-x-1 transition-all ${
              showSettings ? 'bg-indigo-600 text-white border-indigo-500' : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            <i className="bx bx-slider"></i>
            <span>Tune</span>
          </button>
          <button
            onClick={clearChat}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 text-xs transition-all"
            title="Clear conversation"
          >
            <i className="bx bx-trash"></i>
          </button>
        </div>
      </div>

      {/* Optional Tuning Drawer */}
      {showSettings && (
        <div className="glass-card p-4 rounded-xl border border-indigo-500/30 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div>
            <label className="text-slate-300 block mb-1 font-medium">Temperature: {temperature}</label>
            <input
              type="range"
              min="0.1"
              max="1.5"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full cursor-pointer accent-indigo-500"
            />
          </div>
          <div>
            <label className="text-slate-300 block mb-1 font-medium">Max Response Tokens: {maxTokens}</label>
            <input
              type="range"
              min="64"
              max="2048"
              step="64"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              className="w-full cursor-pointer accent-indigo-500"
            />
          </div>
          <div>
            <label className="text-slate-300 block mb-1 font-medium">System Persona Prompt</label>
            <input
              type="text"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full glass-input px-2 py-1 rounded text-slate-200 text-xs focus:outline-none"
            />
          </div>
        </div>
      )}

      {/* Chat Messages Stream Area */}
      <div className="flex-1 glass-card p-5 rounded-2xl overflow-y-auto space-y-4">
        {messages.map((m, idx) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={idx}
              className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center text-sm font-bold shadow-md shrink-0 ${
                  isUser
                    ? 'bg-slate-700 text-slate-200'
                    : 'bg-gradient-to-tr from-indigo-600 to-violet-500 text-white'
                }`}
              >
                <i className={`bx ${isUser ? 'bx-user' : 'bx-bot'}`}></i>
              </div>

              {/* Message Bubble */}
              {isUser ? (
                <div className="max-w-[80%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed bg-indigo-600 text-white shadow-lg shadow-indigo-600/20 rounded-tr-sm">
                  <div className="flex items-center justify-between text-[10px] text-indigo-200 mb-1">
                    <span className="font-semibold text-white">You</span>
                    <span>{m.time}</span>
                  </div>
                  <div className="whitespace-pre-wrap font-sans">
                    {m.content}
                  </div>
                </div>
              ) : (
                <AssistantMessageBubble
                  content={m.content}
                  time={m.time}
                  isGenerating={isGenerating && idx === messages.length - 1}
                />
              )}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Latency Meter Tag */}
      {lastLatencyMs && (
        <div className="text-[11px] text-slate-400 px-3 flex items-center space-x-2">
          <i className="bx bx-check-circle text-emerald-400"></i>
          <span>Response completed in <strong className="text-slate-200 font-mono">{lastLatencyMs} ms</strong></span>
          <span>•</span>
          <span className="text-slate-500">Zero cloud calls • 100% on-device</span>
        </div>
      )}

      {/* Suggestion Prompts */}
      {messages.length <= 2 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {samplePrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => {
                setInputPrompt(p);
              }}
              className="text-[11px] px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all hover:border-indigo-500/40 text-left"
            >
              💡 {p}
            </button>
          ))}
        </div>
      )}

      {/* Input Composer */}
      <form onSubmit={handleSendMessage} className="relative flex items-center">
        <textarea
          value={inputPrompt}
          onChange={(e) => setInputPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          disabled={isGenerating}
          rows={1}
          placeholder="Type your message to Noora... (Press Enter to send)"
          className="w-full glass-input px-4 py-3.5 pr-24 rounded-2xl text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none resize-none"
        />

        <button
          type="submit"
          disabled={isGenerating || !inputPrompt.trim()}
          className="absolute right-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-semibold text-xs shadow-md shadow-indigo-600/30 transition-all active:scale-95 disabled:opacity-40 flex items-center space-x-1.5"
        >
          <i className={`bx ${isGenerating ? 'bx-loader-alt animate-spin' : 'bx-send'} text-sm`}></i>
          <span>Send</span>
        </button>
      </form>
    </div>
  );
};
