"use client";

import { useState } from "react";

import { SIGN_VOCAB, type SignGesture } from "../lib/signVocab";

type SignRulebookProps = {
  open: boolean;
  selectedGesture: SignGesture;
  referenceStatus: Record<string, "recorded" | "default"> | null;
  recordBusy: boolean;
  onClose: () => void;
  onSelect: (gesture: SignGesture) => void;
  onRecord: (gesture: SignGesture) => void;
  onResetOne: (gesture: SignGesture) => void;
  onResetAll: () => void;
};

export function SignRulebook({
  open,
  selectedGesture,
  referenceStatus,
  recordBusy,
  onClose,
  onSelect,
  onRecord,
  onResetOne,
  onResetAll,
}: SignRulebookProps) {
  const [detailOpen, setDetailOpen] = useState(false);

  if (!open) {
    return null;
  }

  const selected =
    SIGN_VOCAB.find((item) => item.key === selectedGesture) ?? SIGN_VOCAB[0];
  if (!selected) {
    return null;
  }

  const recorded = referenceStatus?.[selected.key] === "recorded";

  function handleSelect(gesture: SignGesture) {
    onSelect(gesture);
    setDetailOpen(true);
  }

  function handleClose() {
    setDetailOpen(false);
    onClose();
  }

  return (
    <>
      <aside
        className="panel absolute left-0 top-0 z-20 flex max-h-[calc(100vh-7rem)] w-[min(100%,20rem)] flex-col overflow-hidden rounded-l-none border-l-0 shadow-panel"
        aria-label="Sign guide"
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-ink/8 px-4 py-3.5">
          <div>
            <h2 className="font-heading text-lg font-medium text-ink">Signs</h2>
            <p className="mt-1 text-xs leading-relaxed text-muted">
              Tap a word for how-to steps.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="nav-pill shrink-0 !px-3 !py-1.5"
          >
            Close
          </button>
        </div>

        <ul className="grid min-h-0 flex-1 grid-cols-2 content-start gap-2 overflow-y-auto overscroll-contain px-4 py-4">
          {SIGN_VOCAB.map((item) => {
            const isSelected = detailOpen && item.key === selected.key;
            const isRecorded = referenceStatus?.[item.key] === "recorded";
            return (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => handleSelect(item.key)}
                  className={`min-h-14 w-full rounded-[0.85rem] border px-3 py-2.5 text-left transition-all ${
                    isSelected
                      ? "border-accent/40 bg-accent-soft shadow-sm"
                      : "border-ink/10 bg-background/70 hover:border-accent/30 hover:bg-white"
                  }`}
                >
                  <span className="block text-sm font-semibold text-ink">
                    {item.meaning}
                  </span>
                  <span
                    className={`mt-0.5 block text-[0.7rem] ${
                      isRecorded ? "text-success" : "text-muted"
                    }`}
                  >
                    {isRecorded ? "Your hand" : "Default"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </aside>

      {detailOpen && (
        <div
          className="panel fixed bottom-4 right-4 z-40 flex max-h-[min(70vh,32rem)] w-[min(100%-1.5rem,22rem)] flex-col overflow-hidden shadow-lg sm:bottom-6 sm:right-6"
          role="dialog"
          aria-modal="false"
          aria-label={`${selected.meaning} how to`}
        >
          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-ink/8 px-5 py-4">
            <div className="min-w-0">
              <p className="soft-label">How to do it</p>
              <p className="font-heading mt-1 truncate text-2xl font-medium text-ink">
                {selected.meaning}
              </p>
              <p className="mt-0.5 text-sm text-muted">{selected.label}</p>
            </div>
            <button
              type="button"
              onClick={() => setDetailOpen(false)}
              className="nav-pill shrink-0 !px-3 !py-1.5"
            >
              Close
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4">
            <ol className="list-decimal space-y-2.5 pl-5 text-sm leading-relaxed text-ink-soft">
              {selected.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p
              className={`mt-4 text-xs leading-relaxed ${
                recorded ? "text-success" : "text-muted"
              }`}
            >
              {recorded
                ? "Using your recorded hand for this sign."
                : "Using the built-in default. Record your hand if it fits you better."}
            </p>
            <button
              type="button"
              onClick={() => onRecord(selected.key)}
              disabled={recordBusy}
              className="btn-primary mt-4 w-full"
            >
              Record this sign
            </button>
            {recorded && (
              <button
                type="button"
                onClick={() => onResetOne(selected.key)}
                disabled={recordBusy}
                className="btn-secondary mt-2 w-full"
              >
                Use default for this sign
              </button>
            )}
            <button
              type="button"
              onClick={onResetAll}
              disabled={recordBusy}
              className="btn-secondary mt-2 w-full"
            >
              Clear all recorded references
            </button>
          </div>
        </div>
      )}
    </>
  );
}
