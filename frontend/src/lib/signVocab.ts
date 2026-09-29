export const SIGN_VOCAB = [
  {
    key: "open_palm",
    label: "Open Palm",
    how: "Hold palm still",
    meaning: "Hello",
    steps: [
      "Face the camera with one hand in the frame.",
      "Open all five fingers — thumb out. Palm faces the camera.",
      "Hold still. Do not wag. Thumb sideways is Undo/Clear, not Hello.",
    ],
  },
  {
    key: "thumbs_up",
    label: "Thumbs Up",
    how: "Thumbs up",
    meaning: "Yes",
    steps: [
      "Close the fingers into a fist.",
      "Stick the thumb straight up, clearly above the fist.",
      "Thumb pointing sideways (not up) is Undo, not Yes.",
    ],
  },
  {
    key: "thumbs_down",
    label: "Thumbs Down",
    how: "Thumbs down",
    meaning: "No",
    steps: [
      "Make a fist.",
      "Point the thumb straight down.",
      "Keep the other fingers curled.",
    ],
  },
  {
    key: "fist",
    label: "Both Thumbs Sideways",
    how: "Two thumbs sideways",
    meaning: "Clear",
    steps: [
      "Make a fist on both hands.",
      "Stick both thumbs out sideways (not up, not down).",
      "Hold still. This erases the whole sentence. One sideways thumb is Undo.",
    ],
  },
  {
    key: "four",
    label: "Thumb Sideways",
    how: "One thumb sideways",
    meaning: "Undo",
    steps: [
      "Make a fist with one hand.",
      "Stick the thumb out sideways (left or right), not straight up.",
      "Hold still. This removes only the last word. Both sideways thumbs is Clear.",
    ],
  },
  {
    key: "pointing",
    label: "Pointing",
    how: "Point at camera",
    meaning: "I",
    steps: [
      "Curl middle, ring, and pinky.",
      "Point one index finger at the camera.",
      "Keep the thumb tucked. Two indexes (both hands) is Help, not I.",
    ],
  },
  {
    key: "peace_sign",
    label: "Peace Sign",
    how: "Peace",
    meaning: "Thank you",
    steps: [
      "Raise index and middle fingers in a V.",
      "Curl ring and pinky.",
      "Hold the V toward the camera.",
    ],
  },
  {
    key: "please",
    label: "Shaka",
    how: "Thumb and pinky",
    meaning: "Please",
    steps: [
      "Stick out the thumb and the pinky.",
      "Curl index, middle, and ring.",
      "Hold still.",
    ],
  },
  {
    key: "you",
    label: "Pinky",
    how: "Pinky up",
    meaning: "You",
    steps: [
      "Raise only the pinky.",
      "Keep thumb and the other fingers down.",
      "Hold still.",
    ],
  },
  {
    key: "want",
    label: "Three Fingers",
    how: "Three fingers",
    meaning: "Want",
    steps: [
      "Raise index, middle, and ring.",
      "Keep the pinky curled.",
      "Hold still.",
    ],
  },
  {
    key: "okay",
    label: "Okay Sign",
    how: "Okay (index curled)",
    meaning: "Okay",
    steps: [
      "Curl the index finger.",
      "Keep middle, ring, and pinky up.",
      "Hold still (one hand).",
    ],
  },
  {
    key: "understood",
    label: "Both Peace",
    how: "Two peace signs",
    meaning: "Understood",
    steps: [
      "Show both hands.",
      "On each hand make a peace / V (index + middle up).",
      "Hold still. One peace is Thank you; both is Understood.",
    ],
  },
  {
    key: "doctor",
    label: "Fist + Palm",
    how: "Fist and open palm",
    meaning: "Doctor",
    steps: [
      "One hand: closed fist (Clear shape).",
      "Other hand: open palm (Hello shape).",
      "Hold both still. Order of hands does not matter.",
    ],
  },
  {
    key: "sick",
    label: "Both Fists",
    how: "Two fists",
    meaning: "Sick",
    steps: [
      "Make a fist with both hands.",
      "Hold both fists still in frame.",
      "One fist alone is Clear, not Sick.",
    ],
  },
  {
    key: "happy",
    label: "Both Thumbs Up",
    how: "Two thumbs up",
    meaning: "Happy",
    steps: [
      "Thumbs up on both hands.",
      "Hold still.",
      "One thumbs up alone is Yes, not Happy.",
    ],
  },
  {
    key: "today",
    label: "Both Palms",
    how: "Two open palms",
    meaning: "Today",
    steps: [
      "Open both palms toward the camera (thumb out).",
      "Hold still — do not wave.",
      "One palm alone is Hello, not Today.",
    ],
  },
  {
    key: "tomorrow",
    label: "Both Pinkies",
    how: "Two pinkies up",
    meaning: "Tomorrow",
    steps: [
      "Raise only the pinky on each hand.",
      "Hold still.",
      "One pinky alone is You, not Tomorrow.",
    ],
  },
  {
    key: "i_love_you",
    label: "I Love You",
    how: "Thumb, index, pinky",
    meaning: "I love you",
    steps: [
      "Raise thumb, index, and pinky.",
      "Curl middle and ring.",
      "Hold still.",
    ],
  },
  {
    key: "i",
    label: "Both Indexes",
    how: "Two index fingers",
    meaning: "Help",
    steps: [
      "Show both hands to the camera.",
      "On each hand raise only the index finger; curl the rest.",
      "Hold still. One index at the camera is I, not Help.",
    ],
  },
  {
    key: "food",
    label: "Food",
    how: "Fingertips to mouth",
    meaning: "Food",
    steps: [
      "Bunch fingertips together (soft O / like holding a bite).",
      "Lift that hand so the tips sit clearly above your wrist, near your mouth.",
      "Hold still. A low fist is Clear; a pinch at the chin is Water.",
    ],
  },
  {
    key: "water",
    label: "Water",
    how: "Pinch near chin",
    meaning: "Water",
    steps: [
      "Pinch thumb and index together (other fingers curled).",
      "Lift the pinch so it sits above your wrist, near chin/mouth.",
      "Hold still. One index at the camera is I, not Water.",
    ],
  },
  {
    key: "direction",
    label: "Direction",
    how: "Point sideways",
    meaning: "Direction",
    steps: [
      "Curl middle, ring, and pinky; raise only the index.",
      "Point clearly left or right (sideways), not at the camera.",
      "Forward point at the camera is I; both indexes is Help.",
    ],
  },
  {
    key: "wave",
    label: "Wave",
    how: "Wag left-right twice",
    meaning: "Goodbye",
    steps: [
      "Open your hand.",
      "Wag left, then right, then left (two direction changes).",
      "A still palm is Hello, not Goodbye.",
    ],
  },
] as const;

export type SignGesture = (typeof SIGN_VOCAB)[number]["key"];
export type SignMeaning = (typeof SIGN_VOCAB)[number]["meaning"];
export type SignVocabItem = (typeof SIGN_VOCAB)[number];

export const SIGN_GESTURES: SignGesture[] = SIGN_VOCAB.map((item) => item.key);

export const SIGN_MEANINGS: Record<SignGesture, SignMeaning> = Object.fromEntries(
  SIGN_VOCAB.map((item) => [item.key, item.meaning]),
) as Record<SignGesture, SignMeaning>;

export const SIGN_LABELS: Record<SignGesture, string> = Object.fromEntries(
  SIGN_VOCAB.map((item) => [item.key, item.label]),
) as Record<SignGesture, string>;

export function isSignGesture(value: string): value is SignGesture {
  return (SIGN_GESTURES as readonly string[]).includes(value);
}

export function isClearMeaning(value: string | null | undefined): boolean {
  return value === "Clear";
}

export function isUndoMeaning(value: string | null | undefined): boolean {
  return value === "Undo";
}
