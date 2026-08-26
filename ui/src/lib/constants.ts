export const DISCLAIMER = "Facts-only. No investment advice.";

export const EXAMPLE_QUESTIONS = [
  "What is the expense ratio of SBI Large Cap Direct Growth?",
  "What is the ELSS lock-in period for SBI ELSS Tax Saver?",
  "What is the minimum SIP for SBI Flexicap Direct Growth?",
] as const;

export const PII_HELPER =
  "Only a question is sent. Do not enter PAN, Aadhaar, account numbers, OTP, email, or phone.";

export const EMPTY_QUESTION_ERROR = "Please type a factual question.";

export const LOADING_COPY = "Retrieving facts from the closed corpus…";

export const REFUSAL_INTENTS = new Set([
  "advisory",
  "comparative",
  "performance",
  "pii",
  "out_of_scope",
]);
