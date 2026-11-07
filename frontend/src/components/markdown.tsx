import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Markdown for assistant output. HTML is not rendered (react-markdown escapes
 * it by default), so model output cannot inject markup into the page.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-3 text-sm leading-relaxed break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p>{children}</p>,
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline decoration-[var(--accent)] underline-offset-2"
            >
              {children}
            </a>
          ),
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
          h1: ({ children }) => <h1 className="text-base font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="font-semibold">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[var(--border)] pl-3 text-[var(--muted)]">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="border-[var(--border)]" />,
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-[var(--border)] px-2 py-1 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-[var(--border)] px-2 py-1">{children}</td>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 font-mono text-xs leading-relaxed">
              {children}
            </pre>
          ),
          code: ({ className, children, ...props }: ComponentProps<"code">) => {
            // Fenced blocks arrive with a language-* class and live inside <pre>.
            const block = /language-/.test(className ?? "");
            return (
              <code
                className={
                  block
                    ? className
                    : "rounded bg-[var(--bg)] px-1 py-0.5 font-mono text-[0.85em]"
                }
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
