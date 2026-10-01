import { SIGN_VOCAB, type SignMeaning } from "./signVocab";

export type { SignMeaning };

export const SIGN_MEANING_VALUES: readonly SignMeaning[] = SIGN_VOCAB.map(
  (item) => item.meaning,
);

export const MAX_SENTENCE_TOKENS = 10;
export const SENTENCE_SPEAK_IDLE_MS = 2200;

/** Natural English / AAC reading order (not signing order). */
const WORD_ORDER: Record<SignMeaning, number> = {
  Hello: 10,
  Please: 20,
  Yes: 30,
  No: 30,
  Okay: 35,
  Understood: 36,
  I: 38,
  You: 40,
  Want: 50,
  Food: 55,
  Water: 56,
  Direction: 58,
  Doctor: 59,
  Sick: 59,
  Happy: 59,
  Today: 57,
  Tomorrow: 57,
  Help: 60,
  "I love you": 70,
  "Thank you": 80,
  Goodbye: 90,
  Clear: 999,
  Undo: 999,
};

export function isSignMeaning(value: string): value is SignMeaning {
  return (SIGN_MEANING_VALUES as readonly string[]).includes(value);
}

/**
 * Live preview: only the signed words, in the order they were signed.
 * Does not expand Want → "I want that".
 */
export function formatSignedWords(meanings: readonly string[]): string {
  const tokens = meanings
    .map((item) => item.trim())
    .filter((item) => item.length > 0 && item !== "Clear" && item !== "Undo");
  if (tokens.length === 0) return "";
  return tokens.join(", ");
}

/**
 * Tokens ready for Speak / polish.
 * AAC-only: natural English reorder. ASL/ISL (or mixed): keep signing order.
 */
export function prepareTokensForSpeak(
  meanings: readonly string[],
): string[] {
  const raw = meanings
    .map((item) => item.trim())
    .filter((item) => item.length > 0 && item !== "Clear" && item !== "Undo");
  if (raw.length === 0) return [];
  const allAac = raw.every((item) => isSignMeaning(item));
  if (allAac) {
    return reorderSignTokens(raw);
  }
  return raw;
}

/**
 * Sort signed words into a natural spoken order.
 * Example: Goodbye, Hello, Thank you → Hello, Thank you, Goodbye.
 * Stable for equal ranks (keeps relative signing order).
 */
export function reorderSignTokens(
  meanings: readonly string[],
): SignMeaning[] {
  const tokens = meanings.filter(isSignMeaning);
  return [...tokens]
    .map((token, index) => ({ token, index }))
    .sort((a, b) => {
      const rankA = WORD_ORDER[a.token] ?? 50;
      const rankB = WORD_ORDER[b.token] ?? 50;
      if (rankA !== rankB) return rankA - rankB;
      return a.index - b.index;
    })
    .map((row) => row.token);
}

function clauseFor(meaning: SignMeaning): string {
  switch (meaning) {
    case "Hello":
      return "Hello";
    case "Yes":
      return "Yes";
    case "No":
      return "No";
    case "Help":
      return "I need help";
    case "Thank you":
      return "Thank you";
    case "Goodbye":
      return "Goodbye";
    case "Please":
      return "Please";
    case "You":
      return "You";
    case "I":
      return "I";
    case "Want":
      return "I want that";
    case "Food":
      return "I need food";
    case "Water":
      return "I need water";
    case "Direction":
      return "I need directions";
    case "Okay":
      return "Okay";
    case "Understood":
      return "I understand";
    case "Doctor":
      return "I need a doctor";
    case "Sick":
      return "I am sick";
    case "Happy":
      return "I am happy";
    case "Today":
      return "Today";
    case "Tomorrow":
      return "Tomorrow";
    case "I love you":
      return "I love you";
    case "Clear":
      return "";
    case "Undo":
      return "";
    default: {
      const exhaustive: never = meaning;
      return exhaustive;
    }
  }
}

const PAIR_CLAUSES: Partial<Record<string, string>> = {
  "Hello|Help": "Hello, I need help",
  "Hello|You": "Hello, how are you",
  "Hello|Thank you": "Hello. Thank you",
  "Hello|Goodbye": "Hello. Goodbye",
  "Hello|I love you": "Hello. I love you",
  "Yes|Help": "Yes, I need help",
  "Yes|Please": "Yes, please",
  "Please|Help": "Please, I need help",
  "Please|You": "Please, I need you",
  "Please|Thank you": "Please, and thank you",
  "You|Help": "I need your help",
  "You|Thank you": "Thank you",
  "Want|Help": "I want help",
  "Want|You": "I want to talk to you",
  "Want|Please": "I want that, please",
  "I|Want|Food": "I want food",
  "I|Want|Water": "I want water",
  "I|Want|Help": "I want help",
  "I|Food": "I need food",
  "I|Water": "I need water",
  "Want|Food": "I want food",
  "Want|Water": "I want water",
  "Want|Direction": "I want directions",
  "Hello|Direction": "Hello. I need directions",
  "No|Help": "I do not need help",
  "No|Thank you": "No, thank you",
  "Okay|Thank you": "Okay. Thank you",
  "Okay|Goodbye": "Okay. Goodbye",
  "Understood|Thank you": "Understood. Thank you",
  "I|Sick": "I am sick",
  "I|Happy": "I am happy",
  "I|Doctor": "I need a doctor",
  "Want|Doctor": "I want a doctor",
  "Help|Doctor": "I need a doctor",
  "Sick|Doctor": "I am sick and need a doctor",
  "Today|Doctor": "I need a doctor today",
  "Tomorrow|Doctor": "I need a doctor tomorrow",
  "Today|Help": "I need help today",
  "Tomorrow|Help": "I need help tomorrow",
  "Today|Food": "I need food today",
  "Tomorrow|Water": "I need water tomorrow",
  "Thank you|Goodbye": "Thank you. Goodbye",
  "I love you|You": "I love you",
};

const TRIPLE_CLAUSES: Partial<Record<string, string>> = {
  "Please|Want|Help": "Please, I want help",
  "Yes|Please|Help": "Yes, please help me",
  "Please|You|Help": "Please, I need your help",
  "I|Want|Food": "I want food",
  "I|Want|Water": "I want water",
  "I|Want|Help": "I want help",
  "Hello|I love you|You": "Hello. I love you",
  "Hello|Thank you|Goodbye": "Hello. Thank you. Goodbye",
};

/**
 * Turns signed words into one spoken sentence with grammar templates.
 * Words are reordered into natural English order first.
 * Freeform ASL/ISL glosses (outside AAC vocab) are joined as-is for LLM polish.
 */
export function composeSignSentence(meanings: readonly string[]): string {
  const raw = meanings
    .map((item) => item.trim())
    .filter((item) => item.length > 0 && item !== "Clear" && item !== "Undo");
  if (raw.length === 0) return "";

  const hasLexiconOnly = raw.some((item) => !isSignMeaning(item));
  if (hasLexiconOnly) {
    const text = raw.join(" ");
    return text.endsWith(".") ? text : `${text}.`;
  }

  const tokens = reorderSignTokens(raw);
  if (tokens.length === 0) return "";

  const clauses: string[] = [];
  let index = 0;

  while (index < tokens.length) {
    const first = tokens[index];
    if (!first) {
      break;
    }
    const second = tokens[index + 1];
    const third = tokens[index + 2];

    if (second && third) {
      const triple = TRIPLE_CLAUSES[`${first}|${second}|${third}`];
      if (triple) {
        clauses.push(triple);
        index += 3;
        continue;
      }
    }

    if (second) {
      const pair = PAIR_CLAUSES[`${first}|${second}`];
      if (pair) {
        clauses.push(pair);
        index += 2;
        continue;
      }
    }

    clauses.push(clauseFor(first));
    index += 1;
  }

  const spoken = clauses.filter((clause) => clause.length > 0);
  if (spoken.length === 0) return "";
  const text = spoken.join(". ");
  return text.endsWith(".") ? text : `${text}.`;
}

export function appendSignToken(
  tokens: readonly string[],
  meaning: string,
): string[] {
  const word = meaning.trim();
  if (!word) return [...tokens];
  if (word === "Clear") return [];
  if (word === "Undo") return undoLastSignToken(tokens);
  if (tokens.length >= MAX_SENTENCE_TOKENS) return [...tokens];
  return [...tokens, word];
}

/** Remove only the last signed word. Clear still wipes everything. */
export function undoLastSignToken(tokens: readonly string[]): string[] {
  if (tokens.length === 0) return [];
  return tokens.slice(0, -1);
}
