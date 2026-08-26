import { EXAMPLE_QUESTIONS } from "../lib/constants";

type ExampleChipsProps = {
  disabled: boolean;
  onSelect: (question: string) => void;
};

export function ExampleChips({ disabled, onSelect }: ExampleChipsProps) {
  return (
    <section className="flex flex-col gap-sm">
      <h3 className="font-label-md text-label-md text-secondary uppercase tracking-widest m-0">
        Example Questions
      </h3>
      <div className="flex flex-wrap gap-sm">
        {EXAMPLE_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(question)}
            className="bg-teal-button/10 hover:bg-teal-button/20 text-teal-button font-body-sm text-body-sm px-4 py-2 min-h-[44px] rounded-full transition-colors text-left shadow-sm border border-teal-button/20 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-button"
          >
            {question}
          </button>
        ))}
      </div>
    </section>
  );
}
