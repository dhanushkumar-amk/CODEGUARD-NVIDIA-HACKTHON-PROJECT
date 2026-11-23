import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { isAxiosError } from 'axios';
import { askReport, type ReportChatResponse } from '../api/client';
import { Button } from './Button';

interface ChatTurn extends ReportChatResponse {
  question: string;
}

export function ReportChat({ scanId }: { scanId: string }) {
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const requestInFlight = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || requestInFlight.current) return;

    requestInFlight.current = true;
    setPending(true);
    setError('');
    try {
      const response = await askReport(scanId, text, turns.slice(-3).map((turn) => turn.question));
      setTurns((current) => [...current, { question: text, ...response }]);
      setQuestion('');
    } catch (err) {
      const detail = isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(typeof detail === 'string' ? detail : 'Could not get an answer. Try again.');
    } finally {
      requestInFlight.current = false;
      setPending(false);
    }
  }

  return (
    <section aria-labelledby="report-chat-heading" className="rounded-md border border-line bg-surface-1 p-4 sm:p-6">
      <h2 id="report-chat-heading" className="text-lg font-semibold text-ink">Ask this report</h2>
      <div role="log" aria-label="Report conversation" className="max-h-96 space-y-4 overflow-auto">
        {turns.map((turn, index) => (
          <article key={index} className="mt-3 space-y-2 rounded-md border border-line bg-paper p-3 text-sm">
            <p className="break-words font-semibold text-ink">{turn.question}</p>
            <p className="whitespace-pre-wrap break-words text-ink">{turn.answer}</p>
            {turn.citations.length > 0 && (
              <>
                <h3 className="font-semibold">Scan evidence</h3>
                <ul className="list-disc space-y-2 pl-5">
                  {turn.citations.map((source) => (
                    <li key={source.violation_id} className="break-words">
                      <code>{source.file}{source.line != null ? `:${source.line}` : ''}</code>
                      <p>{source.rule} · {source.description}</p>
                      {source.verification_status && <p>{source.verification_status.replace(/_/g, ' ')}</p>}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </article>
        ))}
      </div>
      <form onSubmit={submit} className="mt-3 space-y-2">
        <label htmlFor="report-chat-question" className="block text-sm font-medium text-ink">
          Question about this scan
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="report-chat-question"
            className="min-w-0 flex-1 rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Which findings affect keyboard navigation?"
            maxLength={500}
            readOnly={pending}
            required
          />
          <Button type="submit" disabled={pending || !question.trim()}>Ask</Button>
        </div>
      </form>
      {pending && <p role="status" className="mt-2 text-sm">Checking scan evidence…</p>}
      {error && <p role="alert" className="mt-2 text-sm text-ink">{error}</p>}
    </section>
  );
}
