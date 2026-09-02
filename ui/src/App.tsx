import { useCallback, useMemo, useState } from "react";
import { AnswerPanel, type ChatTurn } from "./components/AnswerPanel";
import { AskForm } from "./components/AskForm";
import { ExampleChips } from "./components/ExampleChips";
import { WelcomeCard } from "./components/WelcomeCard";
import { askQuestion, ChatRequestError } from "./lib/chat";
import { EMPTY_QUESTION_ERROR } from "./lib/constants";

/** Ported from stitch_sbi_mutual_fund_faq_assistant/code1.html (home) and code.html (refusal). */

function newTurnId(): string {
  return crypto.randomUUID();
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);

  const loading = useMemo(
    () => turns.some((turn) => turn.state.kind === "loading"),
    [turns],
  );

  const submit = useCallback(async (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) {
      setFieldError(EMPTY_QUESTION_ERROR);
      return;
    }
    setFieldError(null);
    setQuestion("");

    const turnId = newTurnId();
    setTurns((prev) => [
      ...prev,
      { id: turnId, question: trimmed, state: { kind: "loading" } },
    ]);

    try {
      const payload = await askQuestion(trimmed);
      setTurns((prev) =>
        prev.map((turn) =>
          turn.id === turnId ? { ...turn, state: { kind: "result", payload } } : turn,
        ),
      );
    } catch (error) {
      if (error instanceof ChatRequestError && error.code === "question_required") {
        setFieldError(EMPTY_QUESTION_ERROR);
        setTurns((prev) => prev.filter((turn) => turn.id !== turnId));
        return;
      }
      const message =
        error instanceof ChatRequestError
          ? error.message
          : "The assistant could not be reached.";
      setTurns((prev) =>
        prev.map((turn) =>
          turn.id === turnId ? { ...turn, state: { kind: "error", message } } : turn,
        ),
      );
    }
  }, []);

  return (
    <div className="bg-background text-on-background min-h-screen flex flex-col font-body-md antialiased">
      <header className="bg-surface shadow-sm sticky top-0 z-50">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between px-gutter py-md w-full max-w-container-max mx-auto gap-sm">
          <div>
            <h1 className="font-headline-md text-headline-md font-bold text-primary m-0">
              SBI Mutual Fund FAQ Assistant
            </h1>
          </div>
        </div>
      </header>

      <main className="flex-grow w-full max-w-container-max mx-auto px-gutter py-lg flex flex-col gap-lg">
        <div className="flex flex-col lg:flex-row gap-xl flex-grow min-h-[400px]">
          <div className="flex flex-col gap-lg w-full lg:w-5/12 shrink-0">
            <WelcomeCard />
            <ExampleChips
              disabled={loading}
              onSelect={(example) => {
                void submit(example);
              }}
            />
          </div>
          <div className="flex flex-col gap-lg w-full lg:w-7/12 flex-grow">
            <AnswerPanel turns={turns} />
            <AskForm
              question={question}
              disabled={loading}
              fieldError={fieldError}
              onQuestionChange={(value) => {
                setQuestion(value);
                if (fieldError) {
                  setFieldError(null);
                }
              }}
              onSubmit={() => {
                void submit(question);
              }}
            />
          </div>
        </div>
      </main>

      <footer className="bg-surface-container border-t border-outline-variant mt-auto shrink-0">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center px-gutter py-lg w-full max-w-container-max mx-auto gap-md">
          <p className="font-body-sm text-body-sm text-on-surface-variant m-0">
            © SBI Mutual Fund FAQ Assistant. Facts-only information source.
          </p>
        </div>
      </footer>
    </div>
  );
}
