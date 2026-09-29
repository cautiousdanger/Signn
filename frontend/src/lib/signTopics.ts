export const TOPIC_CHIPS = [
  {
    id: "study",
    label: "Study",
    sentence: "I need help with studying.",
    tokens: ["Want", "Help"],
  },
  {
    id: "food",
    label: "Food",
    sentence: "I need help with food.",
    tokens: ["Want", "Help"],
  },
  {
    id: "health",
    label: "Health",
    sentence: "I need help with my health.",
    tokens: ["Want", "Help"],
  },
  {
    id: "home",
    label: "Home",
    sentence: "I need help at home.",
    tokens: ["Want", "Help"],
  },
  {
    id: "other",
    label: "Other",
    sentence: "I need help with something else.",
    tokens: ["Want", "Help"],
  },
] as const;

export type TopicChipId = (typeof TOPIC_CHIPS)[number]["id"];

export type SignLexiconMode = "aac" | "asl" | "isl";

export const SIGN_LEXICON_MODES: {
  id: SignLexiconMode;
  label: string;
  hint: string;
}[] = [
  {
    id: "aac",
    label: "AAC",
    hint: "13 hand shapes (live now)",
  },
  {
    id: "asl",
    label: "ASL",
    hint: "American signs (after MS-ASL train)",
  },
  {
    id: "isl",
    label: "ISL",
    hint: "Indian signs (after INCLUDE train)",
  },
];
