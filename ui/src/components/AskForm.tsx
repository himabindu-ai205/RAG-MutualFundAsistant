import { PII_HELPER } from "../lib/constants";
import { Icon } from "./Icon";

type AskFormProps = {
  question: string;
  disabled: boolean;
  fieldError: string | null;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
};

export function AskForm({
  question,
  disabled,
  fieldError,
  onQuestionChange,
  onSubmit,
}: AskFormProps) {
  return (
    <section className="bg-surface-container-lowest rounded-2xl border border-black/5 p-md shadow-[0_4px_20px_rgba(0,0,0,0.04)] shrink-0 flex flex-col gap-sm">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className="sr-only" htmlFor="faq-query">
          Factual question
        </label>
        <textarea
          id="faq-query"
          rows={2}
          value={question}
          disabled={disabled}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Type a factual question about an in-scope SBI scheme…"
          autoComplete="off"
          className="w-full bg-surface font-body-md text-body-md text-on-surface placeholder-outline-variant border border-outline-variant rounded-xl p-md focus:border-teal-button focus:ring-1 focus:ring-teal-button focus-visible:outline-none transition-shadow resize-none disabled:opacity-70"
        />
        {fieldError ? (
          <p className="font-body-sm text-body-sm text-error mt-sm mb-0" role="alert">
            {fieldError}
          </p>
        ) : null}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-sm mt-sm">
          <p className="font-label-md text-[11px] text-secondary flex items-start gap-xs m-0">
            <Icon name="lock" className="text-[14px] mt-px" />
            {PII_HELPER}
          </p>
          <button
            type="submit"
            disabled={disabled}
            className="bg-teal-button hover:bg-teal-button/90 text-white font-label-md text-label-md px-lg py-2.5 min-h-[44px] rounded-lg shadow-sm transition-all flex items-center gap-sm w-full sm:w-auto justify-center disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal-button"
          >
            <span>Ask</span>
            <Icon name="send" className="text-sm" />
          </button>
        </div>
      </form>
    </section>
  );
}
