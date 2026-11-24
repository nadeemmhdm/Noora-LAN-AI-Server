import React, { useState, useEffect, useRef } from 'react';
import type { ServerStatus, KnowledgeDocument, KnowledgeChunk, KnowledgeSearchResult } from '../types';
import { api } from '../services/api';

interface TrainingViewProps {
  status: ServerStatus | null;
}

export const TrainingView: React.FC<TrainingViewProps> = ({ status }) => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [totalWords, setTotalWords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [trainStatusText, setTrainStatusText] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Active training tab: 'upload' | 'text'
  const [trainMode, setTrainMode] = useState<'upload' | 'text'>('upload');

  // Direct text state
  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');

  // Selected file for upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Memory inspect modal
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);
  const [docChunks, setDocChunks] = useState<KnowledgeChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);

  // Memory test query
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [testingQuery, setTestingQuery] = useState(false);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await api.getKnowledgeDocuments();
      setDocuments(res.documents || []);
      setTotalChunks(res.total_chunks || 0);
      setTotalWords(res.total_words || 0);
    } catch (err: any) {
      console.error('Failed to fetch knowledge documents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.md') || file.name.endsWith('.txt') || file.name.endsWith('.markdown')) {
        setSelectedFile(file);
        setErrorMsg(null);
      } else {
        setErrorMsg('Please select a Markdown (.md) or Text (.txt) file.');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setErrorMsg(null);
    }
  };

  const handleTrainFile = async () => {
    if (!selectedFile) return;
    try {
      setTraining(true);
      setErrorMsg(null);
      setSuccessMsg(null);
      setTrainStatusText('Reading document bytes...');

      const text = await selectedFile.text();
      if (!text.trim()) {
        setErrorMsg('The selected file is empty.');
        setTraining(false);
        return;
      }

      setTrainStatusText('Analyzing structure, sections and semantic keywords...');
      const res = await api.uploadKnowledgeFile(selectedFile.name, text);

      setSuccessMsg(`Trained "${res.title}" successfully! Learned ${res.chunk_count} memory chunks (${res.word_count.toLocaleString()} words).`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to train document.');
    } finally {
      setTraining(false);
      setTrainStatusText('');
    }
  };

  const handleTrainDirectText = async () => {
    if (!docContent.trim()) {
      setErrorMsg('Please enter document content to train.');
      return;
    }
    const filename = (docTitle.trim() || 'manual_knowledge').replace(/[^a-zA-Z0-9_\-]/g, '_') + '.md';

    try {
      setTraining(true);
      setErrorMsg(null);
      setSuccessMsg(null);
      setTrainStatusText('Analyzing document structure and semantic sections...');

      const res = await api.trainKnowledgeText(filename, docContent);
      setSuccessMsg(`Trained "${res.title}" successfully! Learned ${res.chunk_count} memory chunks (${res.word_count.toLocaleString()} words).`);
      setDocTitle('');
      setDocContent('');
      fetchDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to train document.');
    } finally {
      setTraining(false);
      setTrainStatusText('');
    }
  };

  const handleDeleteDoc = async (docId: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}" and remove all its learned memory chunks?`)) {
      return;
    }
    try {
      await api.deleteKnowledgeDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      setSuccessMsg(`Removed document "${title}" from memory.`);
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null);
      }
      fetchDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete knowledge document.');
    }
  };

  const handleInspectDoc = async (doc: KnowledgeDocument) => {
    setSelectedDoc(doc);
    setLoadingChunks(true);
    try {
      const res = await api.getKnowledgeDocument(doc.id);
      setDocChunks(res.chunks || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load document chunks.');
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleTestQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testQuery.trim()) return;
    try {
      setTestingQuery(true);
      const res = await api.testKnowledgeQuery(testQuery, 4);
      setTestResults(res.matches || []);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to test knowledge query.');
    } finally {
      setTestingQuery(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="rounded-2xl border border-slate-800/80 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900 p-6 shadow-xl backdrop-blur-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-xs font-semibold">
              <i className="bx bx-book-reader text-sm"></i>
              <span>On-Device Knowledge Memory</span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              AI Training & Knowledge Base
            </h1>
            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              Upload documentation, SOPs, policies, guides, or code notes in Markdown format. Noora analyzes document hierarchy, extracts semantic concepts, and stores them in persistent memory to answer questions across your LAN.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchDocuments}
              className="px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/60 text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm"
              title="Refresh Knowledge Documents"
            >
              <i className={`bx bx-refresh text-base ${loading ? 'animate-spin' : ''}`}></i>
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Knowledge Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800/60">
          <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Trained Docs</span>
              <i className="bx bx-file text-indigo-400 text-base"></i>
            </div>
            <div className="text-xl font-bold text-white mt-1.5">{documents.length}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Active knowledge files</div>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Learned Chunks</span>
              <i className="bx bx-brain text-purple-400 text-base"></i>
            </div>
            <div className="text-xl font-bold text-white mt-1.5">{totalChunks}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Semantic memory blocks</div>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Trained Words</span>
              <i className="bx bx-text text-emerald-400 text-base"></i>
            </div>
            <div className="text-xl font-bold text-white mt-1.5">{totalWords.toLocaleString()}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Parsed & indexed tokens</div>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/60 rounded-xl p-3.5">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Memory Engine</span>
              <i className="bx bx-bolt-circle text-amber-400 text-base"></i>
            </div>
            <div className="text-sm font-bold text-amber-300 mt-1.5 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
              Fast BM25 Ranker
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">&lt;5ms zero-RAM query</div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bx-error-circle text-lg shrink-0"></i>
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">
            <i className="bx bx-x text-lg"></i>
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bx-check-circle text-lg shrink-0"></i>
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">
            <i className="bx bx-x text-lg"></i>
          </button>
        </div>
      )}

      {/* Training Input Section */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <i className="bx bx-cloud-upload text-xl"></i>
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Train New Knowledge</h2>
              <p className="text-xs text-slate-400">Add documents to teach Noora custom information</p>
            </div>
          </div>

          {/* Toggle Mode */}
          <div className="flex items-center bg-slate-950/60 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setTrainMode('upload')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                trainMode === 'upload'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <i className="bx bx-file"></i>
              <span>Upload File</span>
            </button>
            <button
              onClick={() => setTrainMode('text')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                trainMode === 'text'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <i className="bx bx-edit-alt"></i>
              <span>Write / Paste Text</span>
            </button>
          </div>
        </div>

        {trainMode === 'upload' ? (
          <div className="space-y-4">
            {/* Drag & Drop Upload Zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
                dragOver
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : selectedFile
                  ? 'border-emerald-500/60 bg-emerald-500/5'
                  : 'border-slate-700/80 hover:border-slate-600 bg-slate-950/40 hover:bg-slate-950/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".md,.txt,.markdown"
                onChange={handleFileSelect}
                className="hidden"
              />

              <div className="flex flex-col items-center justify-center space-y-3">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl shadow-lg transition-transform ${
                  selectedFile
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                }`}>
                  <i className={`bx ${selectedFile ? 'bx-check-double' : 'bx-upload'}`}></i>
                </div>

                {selectedFile ? (
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-emerald-300">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Click or drag another file to replace
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-slate-200">
                      Click to browse or drag and drop a Markdown file here
                    </p>
                    <p className="text-xs text-slate-500">
                      Supports Markdown (<span className="text-slate-300 font-mono">.md</span>, <span className="text-slate-300 font-mono">.markdown</span>) and plain text (<span className="text-slate-300 font-mono">.txt</span>)
                    </p>
                  </div>
                )}
              </div>
            </div>

            {selectedFile && (
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  disabled={training}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/50 transition-all"
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={handleTrainFile}
                  disabled={training}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 shadow-md shadow-indigo-600/30 flex items-center gap-2 transition-all disabled:opacity-50"
                >
                  {training ? (
                    <>
                      <i className="bx bx-loader-alt animate-spin text-base"></i>
                      <span>Training AI ({trainStatusText || 'Processing...'})...</span>
                    </>
                  ) : (
                    <>
                      <i className="bx bx-brain text-base"></i>
                      <span>Start AI Training</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Direct Text Mode */
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Document Title / Subject
              </label>
              <input
                type="text"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                placeholder="e.g. Company Leave Policy 2026, API Integration Guide..."
                className="w-full bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200 focus:outline-none focus:border-indigo-500/80 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Markdown / Text Content
              </label>
              <textarea
                value={docContent}
                onChange={(e) => setDocContent(e.target.value)}
                rows={8}
                placeholder="# Document Title&#10;&#10;## Section One&#10;Write knowledge here using markdown headers, bullet points, or paragraphs...&#10;&#10;## Section Two&#10;Noora will automatically extract sections and memorize the facts!"
                className="w-full bg-slate-950/60 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500/80 transition-colors leading-relaxed resize-y"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-500">
                {docContent.trim().split(/\s+/).filter(Boolean).length} words
              </span>
              <button
                type="button"
                onClick={handleTrainDirectText}
                disabled={training || !docContent.trim()}
                className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 shadow-md shadow-indigo-600/30 flex items-center gap-2 transition-all disabled:opacity-50"
              >
                {training ? (
                  <>
                    <i className="bx bx-loader-alt animate-spin text-base"></i>
                    <span>Training AI ({trainStatusText || 'Processing...'})...</span>
                  </>
                ) : (
                  <>
                    <i className="bx bx-brain text-base"></i>
                    <span>Train & Save into Memory</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Memory Retrieval Live Tester */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <i className="bx bx-search-alt text-xl"></i>
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Test Learned AI Memory</h2>
            <p className="text-xs text-slate-400">Ask a question to test how Noora retrieves your trained knowledge chunks</p>
          </div>
        </div>

        <form onSubmit={handleTestQuery} className="flex gap-2">
          <input
            type="text"
            value={testQuery}
            onChange={(e) => setTestQuery(e.target.value)}
            placeholder="e.g. How many days of annual leave do employees receive?"
            className="flex-1 bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            disabled={testingQuery || !testQuery.trim()}
            className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50 shadow-md shadow-purple-600/20 shrink-0"
          >
            {testingQuery ? (
              <i className="bx bx-loader-alt animate-spin text-base"></i>
            ) : (
              <i className="bx bx-search text-base"></i>
            )}
            <span>Query Memory</span>
          </button>
        </form>

        {testResults && (
          <div className="mt-4 space-y-3 pt-3 border-t border-slate-800/60">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Memory Retrieval Results: <strong className="text-purple-300">{testResults.length}</strong> matching chunk(s)</span>
              <button onClick={() => setTestResults(null)} className="text-slate-500 hover:text-slate-300 text-[11px]">Clear Results</button>
            </div>

            {testResults.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60 text-center text-xs text-slate-500">
                No matching memory chunks found for this query with the minimum relevance score threshold.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {testResults.map((match, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950/50 border border-indigo-900/40 hover:border-indigo-500/40 transition-colors space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-indigo-300 truncate max-w-[70%]">
                        {match.section_title || match.doc_title}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                        Score: {match.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3">
                      {match.content}
                    </p>
                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                      <i className="bx bx-file"></i>
                      <span className="truncate">{match.filename}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Trained Knowledge Documents List */}
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <i className="bx bx-library text-xl"></i>
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Trained Knowledge Documents ({documents.length})</h2>
              <p className="text-xs text-slate-400">All documents currently active in Noora's persistent memory</p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
            <i className="bx bx-loader-alt animate-spin text-2xl text-indigo-400"></i>
            <span>Loading trained knowledge memory...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="py-12 text-center rounded-xl border border-dashed border-slate-800 p-8 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/50 flex items-center justify-center text-slate-500 text-2xl mx-auto">
              <i className="bx bx-book-open"></i>
            </div>
            <p className="text-sm font-medium text-slate-300">No knowledge documents trained yet</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Upload your company documents, guides, or personal notes above to endow Noora with specialized local knowledge.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 hover:border-slate-700/80 transition-all flex flex-col justify-between group shadow-sm"
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-base shrink-0">
                        <i className="bx bx-file"></i>
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-white line-clamp-1 group-hover:text-indigo-300 transition-colors">
                          {doc.title || doc.filename}
                        </h3>
                        <p className="text-[10px] font-mono text-slate-500">{doc.filename}</p>
                      </div>
                    </div>
                  </div>

                  {doc.summary && (
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed bg-slate-900/50 p-2 rounded-lg border border-slate-800/50">
                      {doc.summary}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                    <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 font-medium">
                      {doc.chunk_count} chunks
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-medium">
                      {doc.word_count.toLocaleString()} words
                    </span>
                    <span className="text-[10px] text-slate-500 ml-auto">
                      {new Date(doc.created_at * 1000).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-slate-800/60">
                  <button
                    onClick={() => handleInspectDoc(doc)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 flex items-center gap-1 transition-all"
                  >
                    <i className="bx bx-show text-sm"></i>
                    <span>Inspect Memory</span>
                  </button>
                  <button
                    onClick={() => handleDeleteDoc(doc.id, doc.title || doc.filename)}
                    className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-rose-400 hover:text-white hover:bg-rose-600/80 border border-rose-500/30 transition-all flex items-center gap-1"
                    title="Delete knowledge and wipe memory"
                  >
                    <i className="bx bx-trash text-sm"></i>
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Inspect Memory Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-lg">
                  <i className="bx bx-brain"></i>
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {selectedDoc.title || selectedDoc.filename}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {selectedDoc.chunk_count} learned chunks • {selectedDoc.word_count.toLocaleString()} words
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="w-8 h-8 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
              >
                <i className="bx bx-x text-xl"></i>
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {selectedDoc.summary && (
                <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-800/40 text-xs text-slate-300">
                  <span className="font-bold text-indigo-300 block mb-1 uppercase tracking-wider text-[10px]">
                    Document Summary
                  </span>
                  {selectedDoc.summary}
                </div>
              )}

              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Extracted Semantic Chunks
              </h4>

              {loadingChunks ? (
                <div className="py-8 text-center text-xs text-slate-500 flex flex-col items-center gap-2">
                  <i className="bx bx-loader-alt animate-spin text-xl text-indigo-400"></i>
                  <span>Loading memory chunks...</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {docChunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-indigo-300">
                          {chunk.section_title || `Chunk #${chunk.chunk_index + 1}`}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          Index #{chunk.chunk_index + 1}
                        </span>
                      </div>

                      <p className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                        {chunk.content}
                      </p>

                      {chunk.keywords && (
                        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800/60">
                          <span className="text-[10px] text-slate-500 mr-1 flex items-center gap-1">
                            <i className="bx bx-tag"></i> Keywords:
                          </span>
                          {chunk.keywords.split(',').map((kw, i) => (
                            <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60">
                              {kw.trim()}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex justify-end">
              <button
                onClick={() => setSelectedDoc(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
