import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './MarkdownRenderer.css'

interface MarkdownRendererProps {
  content: string
  className?: string
}

// Define paragraph component with displayName for detection in li
const MdParagraph: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <p className="md-p">{children}</p>
)
MdParagraph.displayName = 'MdParagraph'

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = '',
}) => {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Code blocks with syntax highlighting
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const codeString = String(children).replace(/\n$/, '')

            // Determine if this is inline code:
            // - inline prop is explicitly true
            // - OR inline is undefined AND no language AND no newlines (single-line code)
            const hasNewlines = codeString.includes('\n')
            const isInline = inline === true || (inline === undefined && !match && !hasNewlines)

            // Code block with language specification
            if (!isInline && match) {
              return (
                <div className="code-block-wrapper">
                  <div className="code-block-header">
                    <span className="code-language">{match[1]}</span>
                    <button
                      className="copy-button"
                      onClick={() => navigator.clipboard.writeText(codeString)}
                      title="Copy code"
                    >
                      Copy
                    </button>
                  </div>
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      borderRadius: '0 0 6px 6px',
                      fontSize: '13px',
                    }}
                    {...props}
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              )
            }

            // Code block without language (multi-line code)
            if (!isInline && !match) {
              return (
                <div className="code-block-wrapper">
                  <SyntaxHighlighter
                    style={oneDark}
                    language="text"
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      borderRadius: '6px',
                      fontSize: '13px',
                    }}
                    {...props}
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              )
            }

            // Inline code (single-line, no language)
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            )
          },

          // Custom heading styles
          h1: ({ children }) => <h1 className="md-h1">{children}</h1>,
          h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
          h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
          h4: ({ children }) => <h4 className="md-h4">{children}</h4>,

          // Links
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
              {children}
            </a>
          ),

          // Lists
          ul: ({ children }) => <ul className="md-ul">{children}</ul>,
          ol: ({ children }) => <ol className="md-ol">{children}</ol>,
          li: ({ children }) => {
            // Unwrap first paragraph to keep content on same line as list marker
            const childArray = React.Children.toArray(children)

            // Filter out whitespace-only text nodes that cause line breaks
            const filteredChildren = childArray.filter(child => {
              if (typeof child === 'string') {
                return child.trim() !== ''
              }
              return true
            })

            // Find first valid React element
            for (let i = 0; i < filteredChildren.length; i++) {
              const child = filteredChildren[i]
              if (React.isValidElement(child)) {
                // Check if it's our MdParagraph component
                const childType = child.type as React.FC & { displayName?: string }
                const isParagraph =
                  childType === 'p' ||
                  childType === MdParagraph ||
                  childType.displayName === 'MdParagraph'

                if (isParagraph && child.props?.children) {
                  // Replace paragraph with span containing its children
                  const newChildren = [
                    ...filteredChildren.slice(0, i),
                    <span key="li-first" className="md-li-first">{child.props.children}</span>,
                    ...filteredChildren.slice(i + 1)
                  ]
                  return <li className="md-li">{newChildren}</li>
                }
                break // Only check first element
              }
            }
            return <li className="md-li">{filteredChildren}</li>
          },

          // Blockquote
          blockquote: ({ children }) => (
            <blockquote className="md-blockquote">{children}</blockquote>
          ),

          // Horizontal rule
          hr: () => <hr className="md-hr" />,

          // Table
          table: ({ children }) => (
            <div className="table-wrapper">
              <table className="md-table">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="md-th">{children}</th>,
          td: ({ children }) => <td className="md-td">{children}</td>,

          // Paragraph - use named component for li detection
          p: MdParagraph,

          // Strong/Bold
          strong: ({ children }) => <strong className="md-strong">{children}</strong>,

          // Emphasis/Italic
          em: ({ children }) => <em className="md-em">{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
