import { DISCLAIMER, LOADING_COPY, REFUSAL_INTENTS } from "../lib/constants";
import type { ChatResponse } from "../lib/chat";
import { isPublicHttpUrl } from "../lib/chat";
import { Icon } from "./Icon";

export type AnswerState =
  | { kind: "empty" }
  | { kind: "loading" }
  | { kind: "result"; payload: ChatResponse }
  | { kind: "error"; message: string };

type AnswerPanelProps = {
  state: AnswerState;
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

export function AnswerPanel({ state }: AnswerPanelProps) {
  if (state.kind === "empty") {
    return (
      <section className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex-grow flex flex-col justify-center items-center text-center relative overflow-hidden min-h-[220px]">
        <div className="absolute inset-0 bg-gradient-to-br from-surface-container-low to-surface-container-lowest opacity-50 z-0 pointer-events-none" />
        <div className="z-10 flex flex-col items-center gap-md p-xl">
          <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center mb-sm">
            <Icon name="chat_bubble" className="text-outline text-3xl" />
          </div>
          <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface-variant font-medium m-0">
            Answers appear here.
          </h3>
          <p className="font-body-sm text-body-sm text-secondary max-w-sm m-0">
            Each reply includes one source link and a last-updated date.
          </p>
        </div>
      </section>
    );
  }

  if (state.kind === "loading") {
    return (
      <section
        className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex-grow flex flex-col justify-center min-h-[220px]"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="flex items-center gap-md">
          <div className="h-10 w-10 rounded-full border-2 border-teal-button/30 border-t-teal-button animate-spin shrink-0" />
          <div className="flex-1">
            <p className="font-body-md text-body-md text-on-surface m-0">{LOADING_COPY}</p>
            <div className="mt-md space-y-sm">
              <div className="h-3 rounded bg-surface-container-high w-full animate-pulse" />
              <div className="h-3 rounded bg-surface-container-high w-5/6 animate-pulse" />
              <div className="h-3 rounded bg-surface-container-high w-2/3 animate-pulse" />
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (state.kind === "error") {
    return (
      <section
        className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex-grow min-h-[180px]"
        role="alert"
      >
        <p className="font-body-md text-body-md text-error m-0">{state.message}</p>
      </section>
    );
  }

  const { payload } = state;
  const refused = REFUSAL_INTENTS.has(payload.intent);
  const disclaimer = payload.disclaimer.trim() || DISCLAIMER;

  return (
    <section
      className="bg-surface-container-lowest rounded-2xl border border-black/5 p-lg shadow-[0_4px_20px_rgba(0,0,0,0.04)] flex-grow flex flex-col gap-md relative overflow-hidden min-h-[220px]"
      aria-live="polite"
    >
      {refused ? (
        <div className="absolute left-0 top-0 bottom-0 w-[4px] bg-secondary-fixed" />
      ) : null}
      <div className="flex items-start gap-md">
        <div
          className={`${
            refused
              ? "bg-secondary-container text-on-secondary-container"
              : "bg-teal-button/10 text-teal-button"
          } rounded-full p-2 flex-shrink-0 mt-1`}
        >
          <Icon name={refused ? "shield" : "fact_check"} filled={refused} />
        </div>
        <div className="flex-grow flex flex-col gap-sm pt-1 min-w-0">
          <p className="font-label-md text-label-md text-on-surface-variant uppercase m-0">
            Answer
          </p>
          <p className="font-body-lg text-body-lg text-on-surface m-0 leading-relaxed">
            {payload.answer}
          </p>
          {!refused ? (
            <div className="mt-md bg-surface-container-low rounded-lg p-sm border border-outline-variant/50">
              <div className="flex items-center gap-sm">
                <Icon name="link" className="text-outline text-sm" />
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">
                  Source
                </span>
              </div>
              <SourceLink url={payload.source} />
            </div>
          ) : null}
        </div>
      </div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-sm pt-sm border-t border-outline-variant/30 gap-sm">
        <div className="flex items-center gap-xs text-on-surface-variant">
          <Icon name="update" className="text-[16px]" />
          <span className="font-label-md text-label-md">
            Last updated from sources: {payload.last_updated_from_sources}
          </span>
        </div>
        <div className="bg-[#FFF8E1] text-[#F57F17] px-sm py-xs rounded-full inline-flex items-center gap-xs text-[11px] font-semibold tracking-wider uppercase border border-[#FFE082]">
          <Icon name="gavel" className="text-[14px]" />
          {disclaimer}
        </div>
      </div>
    </section>
  );
}
