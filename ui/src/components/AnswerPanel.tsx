import { useEffect, useRef } from "react";
import { DISCLAIMER, LOADING_COPY, REFUSAL_INTENTS } from "../lib/constants";
import type { ChatResponse } from "../lib/chat";
import { isPublicHttpUrl } from "../lib/chat";
import { Icon } from "./Icon";

export type TurnState =
  | { kind: "loading" }
  | { kind: "result"; payload: ChatResponse }
  | { kind: "error"; message: string };

export type ChatTurn = {
  id: string;
  question: string;
  state: TurnState;
};

type AnswerPanelProps = {
  turns: ChatTurn[];
};

function SourceLink({ url }: { url: string }) {
  if (!isPublicHttpUrl(url)) {
    return (
      <p className="font-body-sm text-body-sm text-on-surface-variant m-0">
        Source link unavailable.
      </p>
    );
  }
  return (
    <a
      className="font-body-sm text-body-sm text-primary-container hover:underline mt-1 block break-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-button rounded-sm"
      href={url}
      rel="noopener noreferrer"
      target="_blank"
    >
      {url}
    </a>
  );
}

function DisclaimerChip({ text = DISCLAIMER }: { text?: string }) {
  return (
    <div
      className="bg-[#FFF8E1] text-[#F57F17] px-sm py-xs rounded-full inline-flex items-center gap-xs text-[11px] font-semibold tracking-wider uppercase border border-[#FFE082]"
      aria-label={DISCLAIMER}
    >
      <Icon name="gavel" className="text-[14px]" />
      {text.trim() || DISCLAIMER}
    </div>
  );
}

function TurnLoading() {
  return (
    <div className="flex items-center gap-md" aria-busy="true">
      <div className="h-8 w-8 rounded-full border-2 border-teal-button/30 border-t-teal-button animate-spin shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-body-md text-body-md text-on-surface m-0">{LOADING_COPY}</p>
        <div className="mt-sm space-y-sm">
          <div className="h-3 rounded bg-surface-container-high w-full animate-pulse" />
          <div className="h-3 rounded bg-surface-container-high w-5/6 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function TurnAnswer({ state }: { state: TurnState }) {
  if (state.kind === "loading") {
    return <TurnLoading />;
  }

  if (state.kind === "error") {
    return (
      <p className="font-body-md text-body-md text-error m-0" role="alert">
        {state.message}
      </p>
    );
  }

  const { payload } = state;
  const refused = REFUSAL_INTENTS.has(payload.intent);
  const disclaimer = payload.disclaimer.trim() || DISCLAIMER;

  return (
    <div
      className={`flex flex-col gap-sm relative ${refused ? "pl-sm border-l-4 border-secondary-fixed" : ""}`}
    >
      <div className="flex items-start gap-md">
        <div
          className={`${
            refused
              ? "bg-secondary-container text-on-secondary-container"
              : "bg-teal-button/10 text-teal-button"
          } rounded-full p-2 flex-shrink-0 mt-0.5`}
        >
          <Icon name={refused ? "shield" : "fact_check"} filled={refused} />
        </div>
        <div className="flex-grow flex flex-col gap-sm min-w-0">
          <p className="font-body-lg text-body-lg text-on-surface m-0 leading-relaxed">
            {payload.answer}
          </p>
          {!refused ? (
            <div className="bg-surface-container-low rounded-lg p-sm border border-outline-variant/50">
              <div className="flex items-center gap-sm">
                <Icon name="link" className="text-outline text-sm" />
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">
                  Source
                </span>
              </div>
              <SourceLink url={payload.source} />
            </div>
          ) : null}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-sm pt-xs">
            <div className="flex items-center gap-xs text-on-surface-variant">
              <Icon name="update" className="text-[16px]" />
              <span className="font-label-md text-label-md">
                Last updated from sources: {payload.last_updated_from_sources}
              </span>
            </div>
            <DisclaimerChip text={disclaimer} />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyPlaceholder() {
  return (
    <div className="flex flex-col justify-center items-center text-center flex-grow min-h-[220px] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-surface-container-low to-surface-container-lowest opacity-50 z-0 pointer-events-none" />
      <div className="z-10 flex flex-col items-center gap-md p-xl">
        <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center mb-sm">
          <Icon name="chat_bubble" className="text-outline text-3xl" />
        </div>
        <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface-variant font-medium m-0">
          Answers appear here.
        </h3>
        <p className="font-body-sm text-body-sm text-secondary max-w-sm m-0">
          Each reply includes one source link and a last-updated date. Previous questions stay
          visible above.
        </p>
        <DisclaimerChip />
      </div>
    </div>
  );
}

export function AnswerPanel({ turns }: AnswerPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  return (
    <section
      className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex-grow flex flex-col gap-md min-h-[220px] max-h-[min(70vh,720px)] overflow-y-auto"
      aria-live="polite"
    >
      {turns.length === 0 ? (
        <EmptyPlaceholder />
      ) : (
        <div className="flex flex-col gap-lg">
          {turns.map((turn) => (
            <article
              key={turn.id}
              className="flex flex-col gap-sm pb-lg border-b border-outline-variant/30 last:border-b-0 last:pb-0"
            >
              <div className="flex justify-end">
                <div className="bg-primary-container/10 text-on-surface rounded-2xl rounded-tr-sm px-md py-sm max-w-[92%]">
                  <p className="font-label-md text-label-md text-on-surface-variant uppercase m-0 mb-xs">
                    Question
                  </p>
                  <p className="font-body-md text-body-md text-on-surface m-0">{turn.question}</p>
                </div>
              </div>
              <TurnAnswer state={turn.state} />
            </article>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </section>
  );
}
