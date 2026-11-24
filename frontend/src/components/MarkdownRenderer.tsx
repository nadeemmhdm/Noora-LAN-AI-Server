import React, { useState } from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split content by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className={`space-y-2 leading-relaxed text-slate-200 ${className}`}>
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          // It is a code block
          return <CodeBlock key={index} rawBlock={part} />;
        } else {
          // Regular text block with paragraphs, lists, bold, italic, headings
          return <TextBlock key={index} text={part} />;
        }
      })}
    </div>
  );
};

const CodeBlock: React.FC<{ rawBlock: string }> = ({ rawBlock }) => {
  const [copied, setCopied] = useState(false);
  const lines = rawBlock.slice(3, -3).trim().split('\n');
  let language = '';
  let code = rawBlock.slice(3, -3);

  // Check if first line is a language identifier
  if (lines.length > 0 && /^[a-zA-Z0-9_-]+$/.test(lines[0].trim())) {
    language = lines[0].trim();
    code = lines.slice(1).join('\n');
  } else {
    code = lines.join('\n');
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2.5 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/90 shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900 border-b border-slate-800 text-[11px] text-slate-400">
        <span className="font-mono uppercase font-semibold text-indigo-400 flex items-center gap-1.5">
          <i className="bx bx-code-curly text-sm"></i>
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Copy code to clipboard"
        >
          <i className={`bx ${copied ? 'bx-check text-emerald-400' : 'bx-copy'}`}></i>
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto font-mono text-xs text-slate-200 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const TextBlock: React.FC<{ text: string }> = ({ text }) => {
  const paragraphs = text.split(/\n\s*\n/);

  return (
    <>
      {paragraphs.map((p, pIdx) => {
        const trimmed = p.trim();
        if (!trimmed) return null;

        const lines = trimmed.split('\n');

        // Check if paragraph is a list
        const isUnorderedList = lines.every(l => /^\s*[-*]\s+/.test(l));
        const isOrderedList = lines.every(l => /^\s*\d+\.\s+/.test(l));
        const isBlockquote = lines.every(l => /^\s*>\s+/.test(l));

        if (isUnorderedList) {
          return (
            <ul key={pIdx} className="list-disc list-inside space-y-1 my-1.5 text-slate-300">
              {lines.map((l, lIdx) => {
                const itemText = l.replace(/^\s*[-*]\s+/, '');
                return <li key={lIdx}>{renderInlineMarkdown(itemText)}</li>;
              })}
            </ul>
          );
        }

        if (isOrderedList) {
          return (
            <ol key={pIdx} className="list-decimal list-inside space-y-1 my-1.5 text-slate-300">
              {lines.map((l, lIdx) => {
                const itemText = l.replace(/^\s*\d+\.\s+/, '');
                return <li key={lIdx}>{renderInlineMarkdown(itemText)}</li>;
              })}
            </ol>
          );
        }

        if (isBlockquote) {
          return (
            <blockquote key={pIdx} className="border-l-2 border-indigo-500/60 pl-3.5 my-2 italic text-slate-400 bg-indigo-500/5 py-1 rounded-r-lg">
              {lines.map((l, lIdx) => {
                const quoteText = l.replace(/^\s*>\s*/, '');
                return <p key={lIdx}>{renderInlineMarkdown(quoteText)}</p>;
              })}
            </blockquote>
          );
        }

        // Headings check
        if (lines.length === 1) {
          if (trimmed.startsWith('### ')) {
            return <h3 key={pIdx} className="text-sm font-bold text-white mt-2 mb-1">{renderInlineMarkdown(trimmed.slice(4))}</h3>;
          }
          if (trimmed.startsWith('## ')) {
            return <h2 key={pIdx} className="text-base font-bold text-white mt-2.5 mb-1">{renderInlineMarkdown(trimmed.slice(3))}</h2>;
          }
          if (trimmed.startsWith('# ')) {
            return <h1 key={pIdx} className="text-lg font-extrabold text-white mt-3 mb-1.5">{renderInlineMarkdown(trimmed.slice(2))}</h1>;
          }
        }

        // Standard paragraph with linebreaks
        return (
          <p key={pIdx} className="my-1">
            {lines.map((line, lIdx) => (
              <React.Fragment key={lIdx}>
                {renderInlineMarkdown(line)}
                {lIdx < lines.length - 1 && <br />}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
};

// Render inline markdown: bold, italic, bold-italic, inline code, links
function renderInlineMarkdown(str: string): React.ReactNode {
  if (!str) return '';

  // Regex tokens:
  // 1. Links: [text](url)
  // 2. Inline code: `code`
  // 3. Bold-Italic: ***text*** or ___text___
  // 4. Bold: **text** or __text__
  // 5. Italic: *text* or _text_
  const tokenRegex = /(\[[^\]]+\]\(https?:\/\/[^\)]+\)|`[^`]+`|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)/g;
  const parts = str.split(tokenRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // Link: [text](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\)]+)\)$/);
    if (linkMatch) {
      return (
        <a
          key={index}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 hover:text-indigo-300 font-semibold underline inline-flex items-center gap-0.5"
        >
          <span>{linkMatch[1]}</span>
          <i className="bx bx-link-external text-[10px]"></i>
        </a>
      );
    }

    // Inline code: `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={index}
          className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-xs border border-slate-700/80 mx-0.5"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold & Italic: ***text***
    if (part.startsWith('***') && part.endsWith('***') && part.length > 6) {
      return (
        <strong key={index} className="font-bold italic text-white">
          {part.slice(3, -3)}
        </strong>
      );
    }

    // Bold: **text** or __text__
    if ((part.startsWith('**') && part.endsWith('**') && part.length > 4) ||
        (part.startsWith('__') && part.endsWith('__') && part.length > 4)) {
      return (
        <strong key={index} className="font-bold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic: *text* or _text_
    if ((part.startsWith('*') && part.endsWith('*') && part.length > 2) ||
        (part.startsWith('_') && part.endsWith('_') && part.length > 2)) {
      return (
        <em key={index} className="italic text-slate-300">
          {part.slice(1, -1)}
        </em>
      );
    }

    return part;
  });
}
