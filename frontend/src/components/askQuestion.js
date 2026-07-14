import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const normalizeAnswerText = (text) => {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n');
};

export default function AskQuestion() {
  const [videoLink, setVideoLink] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!videoLink.trim() || !question.trim()) {
      setError('Please enter both a YouTube video link and a question.');
      return;
    }

    setLoading(true);
    setError('');
    setAnswer('');

    try {
      const response = await fetch('http://16.113.44.255/userQuery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtubeUrl: videoLink,
          user_question: question,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || data?.message || 'Failed to get an answer.');
      }

      if (data?.answer) {
        setAnswer(data.answer);
      } else if (data?.message) {
        setAnswer(data.message);
      } else {
        setAnswer(JSON.stringify(data));
      }
    } catch (err) {
      console.error('Error asking question:', err);
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyAnswer = async () => {
    if (!answer) {
      return;
    }

    try {
      await navigator.clipboard.writeText(normalizeAnswerText(answer));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy answer:', err);
      setError('Unable to copy the answer.');
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Ask a Question About a YouTube Video</h1>
      <p className="mb-6 text-gray-700">Paste a YouTube video link and ask a question about its content. The app will try to answer it from the video context.</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">YouTube video link</label>
          <input
            type="text"
            value={videoLink}
            onChange={(e) => setVideoLink(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full border rounded-md p-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What is this video about?"
            rows="4"
            className="w-full border rounded-md p-2"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 disabled:bg-blue-300 hover:bg-blue-700 text-white py-2 px-5 rounded-md"
        >
          {loading ? 'Asking...' : 'Ask'}
        </button>
      </form>

      {error && <div className="mt-4 text-red-600">{error}</div>}

      {answer && (
        <div className="mt-6 rounded-lg border bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Reply</h2>
            <button
              type="button"
              onClick={handleCopyAnswer}
              className="rounded-md border border-gray-300 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              {copied ? 'Copied!' : 'Copy answer'}
            </button>
          </div>
          <div className="space-y-2 break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ node, ...props }) => <p className="whitespace-pre-wrap leading-relaxed text-gray-800" {...props} />,
                ul: ({ node, ...props }) => <ul className="ml-5 list-disc space-y-1 text-gray-800" {...props} />,
                ol: ({ node, ...props }) => <ol className="ml-5 list-decimal space-y-1 text-gray-800" {...props} />,
                li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
                strong: ({ node, ...props }) => <strong className="font-semibold text-gray-900" {...props} />,
                em: ({ node, ...props }) => <em className="italic text-gray-900" {...props} />,
                code: ({ node, className, children, ...props }) => (
                  <code className="rounded bg-gray-100 px-1 py-0.5 text-sm font-mono text-gray-900" {...props}>
                    {children}
                  </code>
                ),
                h1: ({ node, ...props }) => <h1 className="text-xl font-bold text-gray-900" {...props} />,
                h2: ({ node, ...props }) => <h2 className="text-lg font-semibold text-gray-900" {...props} />,
                h3: ({ node, ...props }) => <h3 className="text-base font-semibold text-gray-900" {...props} />,
              }}
            >
              {normalizeAnswerText(answer)}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
