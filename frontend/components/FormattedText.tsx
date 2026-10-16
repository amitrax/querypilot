"use client";

import React from "react";

interface FormattedTextProps {
  text: string;
  className?: string;
}

/**
 * Safely renders text with lightweight Markdown styling (**bold**, *italic*, `code`)
 * into React elements without raw Markdown markers and without dangerouslySetInnerHTML.
 */
export function FormattedText({ text, className = "" }: FormattedTextProps) {
  if (!text) return null;

  const parts: React.ReactNode[] = [];
  // Regex to match **bold**, *italic*, and `code`
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong
          key={match.index}
          className="font-semibold text-slate-900 dark:text-slate-100"
        >
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em
          key={match.index}
          className="italic text-slate-800 dark:text-slate-200"
        >
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={match.index}
          className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] text-blue-700 dark:bg-slate-800 dark:text-blue-400"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return <span className={className}>{parts}</span>;
}
