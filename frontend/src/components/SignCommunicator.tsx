"use client";

import { SIGN_LEXICON_MODES, TOPIC_CHIPS } from "../lib/signTopics";

export type ConversationTurn = {
  role: "user" | "assistant";
  content: string;
};

type SignCommunicatorProps = {
  voiceUnlocked: boolean;
  speaking: boolean;
  speakingTarget?: "user" | "assistant" | null;
  polishing?: boolean;
  replyLoading?: boolean;
  replyError?: string | null;
  replySource?: "elevenlabs" | "ollama" | "fallback" | null;
  tokens: string[];
  sentence: string;
  lastSpoken: string | null;
  userSentence: string | null;
  assistantReply: string | null;
  conversation: ConversationTurn[];
  currentMeaning: string | null;
  currentLabel: string | null;
  recognized: boolean;
  scorePercent: number;
  motionProgress: number | null;
  motionHint: string | null;
  handStyle: "motion" | "hold" | null;
  onEnableVoice: () => void;
  onSpeak: () => void;
  onUndo: () => void;
  onRepeat: () => void;
  onRepeatReply: () => void;
  onClear: () => void;
  onNewConversation: () => void;
  onTopicChip?: (sentence: string, tokens: string[]) => void;
  lexiconMode?: "aac" | "asl" | "isl";
  onLexiconModeChange?: (mode: "aac" | "asl" | "isl") => void;
  lexiconStatusNote?: string | null;
};

export function SignCommunicator({
  voiceUnlocked,
  speaking,
  speakingTarget = null,
  polishing = false,
  replyLoading = false,
  replyError = null,
  replySource = null,
  tokens,
  sentence,
  lastSpoken,
  userSentence,
  assistantReply,
  conversation,
  currentMeaning,
  currentLabel,
  recognized,
  scorePercent,
  motionProgress,
  motionHint,
  handStyle,
  onEnableVoice,
  onSpeak,
  onUndo,
  onRepeat,
  onRepeatReply,
  onClear,
  onNewConversation,
  onTopicChip,
  lexiconMode = "aac",
  onLexiconModeChange,
  lexiconStatusNote = null,
}: SignCommunicatorProps) {
  const displaySentence = sentence || lastSpoken;
  const busy = speaking || polishing || replyLoading;
  const canSpeak = Boolean(sentence) && voiceUnlocked && !busy;
  const canUndo = tokens.length > 0 && !busy;
  const canRepeat = Boolean(lastSpoken || userSentence) && voiceUnlocked && !busy;
  const canRepeatReply = Boolean(assistantReply) && voiceUnlocked && !busy;
  const canClear =
    tokens.length > 0 ||
    Boolean(lastSpoken) ||
    Boolean(userSentence) ||
    Boolean(assistantReply) ||
    conversation.length > 0;
  const canNewConversation =
    conversation.length > 0 || Boolean(userSentence) || Boolean(assistantReply);
  const moving = handStyle === "motion";
  const hasConversation =
    conversation.length > 0 || Boolean(userSentence) || Boolean(assistantReply);

  const recognizeTitle = recognized
    ? "Recognized"
    : moving
      ? "Reading motion"
      : currentLabel
        ? "Hold still"
        : "Ready";

  const recognizeDetail =
    recognized && currentMeaning === "Clear"
      ? "Sentence cleared"
      : recognized && currentMeaning === "Undo"
        ? "Last word removed"
        : recognized && currentMeaning
          ? currentMeaning
          : moving
            ? "Keep moving for Goodbye"
            : currentLabel
              ? "Hold to lock this word"
              : "Sign naturally toward the camera";

  const statusLabel = polishing
    ? "Preparing message…"
    : replyLoading
      ? "Thinking…"
      : speaking && speakingTarget === "assistant"
        ? "Speaking reply…"
        : speaking
          ? "Speaking…"
          : null;

  return (
    <section
      className="fade-up flex flex-col gap-3"
      aria-label="Sign language communicator"
    >
      {!voiceUnlocked && (
        <div className="panel flex flex-wrap items-center justify-between gap-3 border-accent/20 bg-accent-soft/50 px-4 py-3">
          <p className="text-sm leading-snug text-ink">
            Enable voice so messages and replies can be spoken aloud.
          </p>
          <button
            type="button"
            onClick={onEnableVoice}
            className="btn-primary !min-h-11 shrink-0 px-4"
          >
            Enable voice
          </button>
        </div>
      )}

      {/* Current recognition */}
      <div className="panel p-3.5 sm:p-4" aria-live="polite">
        <div className="flex items-start justify-between gap-3">
          <p className="soft-label">Current sign</p>
          {statusLabel ? (
            <span className="pulse-soft text-xs font-semibold text-accent">
              {statusLabel}
            </span>
          ) : null}
        </div>
        <div key={`${currentLabel ?? "none"}-${recognized}`} className="sign-pop mt-1.5">
          <p className="text-xs font-medium text-muted">{recognizeTitle}</p>
          <p
            className={`font-heading mt-0.5 text-xl font-medium leading-tight sm:text-2xl ${
              recognized
                ? "text-success"
                : moving
                  ? "text-accent"
                  : "text-ink"
            }`}
          >
            {recognizeDetail}
          </p>
          {currentLabel ? (
            <p className="mt-0.5 text-sm text-muted">{currentLabel}</p>
          ) : null}
        </div>
        {motionProgress !== null && (
          <div className="mt-2.5">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="font-medium text-accent">
                {moving && currentLabel === "Wave"
                  ? "Watching the wave…"
                  : "Reading motion…"}
              </span>
              <span className="tabular-nums text-muted">
                {Math.round(motionProgress * 100)}%
              </span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill bg-accent"
                style={{ width: `${Math.round(motionProgress * 100)}%` }}
              />
            </div>
          </div>
        )}
        {motionHint ? (
          <p className="mt-2 text-sm font-medium text-accent">{motionHint}</p>
        ) : null}
        {currentLabel ? (
          <div className="mt-2.5">
            <p className="mb-1 text-xs text-muted">Match</p>
            <div className="progress-track">
              <div
                className={`progress-fill ${
                  recognized ? "bg-success" : "bg-accent"
                }`}
                style={{ width: `${scorePercent}%` }}
              />
            </div>
          </div>
        ) : null}
      </div>

      {/* Sentence builder */}
      <div className="panel p-3.5 sm:p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="soft-label">Your message</p>
          {canNewConversation ? (
            <button
              type="button"
              onClick={onNewConversation}
              disabled={busy}
              className="btn-ghost !min-h-10 !px-2.5 !py-1 text-xs font-semibold"
            >
              New chat
            </button>
          ) : null}
        </div>

        {tokens.length > 0 ? (
          <ul
            className="mt-2.5 flex flex-wrap gap-2"
            aria-label="Words in this message"
          >
            {tokens.map((token, index) => (
              <li
                key={`${token}-${index}`}
                className={`chip ${
                  index === tokens.length - 1 ? "chip-latest" : ""
                }`}
              >
                {token}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2.5 text-sm leading-relaxed text-muted">
            Start signing to build your message.
          </p>
        )}

        <p
          className="font-heading mt-2 min-h-[2rem] text-lg font-medium leading-snug text-ink sm:text-xl"
          aria-live="assertive"
          aria-atomic="true"
        >
          {displaySentence ?? ""}
        </p>

        <div className="action-bar">
          <button
            type="button"
            onClick={onSpeak}
            disabled={!canSpeak}
            className="btn-primary w-full !min-h-12 text-base"
            aria-label="Speak your message"
          >
            {polishing
              ? "Preparing…"
              : replyLoading
                ? "Thinking…"
                : "Speak"}
          </button>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={onUndo}
              disabled={!canUndo}
              className="btn-secondary !min-h-11"
            >
              Undo
            </button>
            <button
              type="button"
              onClick={onRepeat}
              disabled={!canRepeat}
              className="btn-secondary !min-h-11"
            >
              Say again
            </button>
            <button
              type="button"
              onClick={onClear}
              disabled={!canClear}
              className="btn-danger !min-h-11"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Conversation */}
      <div className="panel flex min-h-0 flex-1 flex-col p-3.5 sm:p-4" aria-label="Conversation">
        <div className="flex items-center justify-between gap-3">
          <p className="soft-label">Conversation</p>
          {replySource === "fallback" && assistantReply ? (
            <span className="text-xs font-medium text-alert">Offline reply</span>
          ) : null}
        </div>

        {!hasConversation ? (
          <div className="mt-3 rounded-xl border border-dashed border-ink/10 bg-surface px-3 py-4 text-center">
            <p className="text-sm font-medium text-ink">
              Your conversation will appear here
            </p>
            <p className="mt-1 text-sm text-muted">
              Sign a message, then tap Speak to get a reply.
            </p>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {conversation.length > 0 ? (
              <ul className="flex flex-col gap-3" aria-live="polite">
                {conversation.map((turn, index) => {
                  const isLast = index === conversation.length - 1;
                  const offlineAssistant =
                    turn.role === "assistant" &&
                    isLast &&
                    replySource === "fallback";
                  return (
                    <li
                      key={`${turn.role}-${index}-${turn.content.slice(0, 24)}`}
                      className={isLast ? "fade-up" : undefined}
                    >
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                        {turn.role === "user"
                          ? "Your message"
                          : offlineAssistant
                            ? "Assistant · offline"
                            : "Assistant response"}
                      </p>
                      <div
                        className={`msg-bubble ${
                          turn.role === "user" ? "msg-user" : "msg-assistant"
                        }`}
                      >
                        {turn.content}
                      </div>
                      {turn.role === "assistant" && isLast ? (
                        <button
                          type="button"
                          onClick={onRepeatReply}
                          disabled={!canRepeatReply}
                          className="btn-ghost mt-2 !min-h-0 !px-2 !py-1 text-xs"
                          aria-label="Listen to assistant reply"
                        >
                          {speaking && speakingTarget === "assistant"
                            ? "Speaking…"
                            : "Listen"}
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <>
                {userSentence ? (
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                      Your message
                    </p>
                    <div className="msg-bubble msg-user">{userSentence}</div>
                  </div>
                ) : null}
                {assistantReply ? (
                  <div className="fade-up">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                      {replySource === "fallback"
                        ? "Assistant · offline"
                        : "Assistant response"}
                    </p>
                    <div className="msg-bubble msg-assistant">{assistantReply}</div>
                    <button
                      type="button"
                      onClick={onRepeatReply}
                      disabled={!canRepeatReply}
                      className="btn-ghost mt-2 !min-h-0 !px-2 !py-1 text-xs"
                      aria-label="Listen to assistant reply"
                    >
                      {speaking && speakingTarget === "assistant"
                        ? "Speaking…"
                        : "Listen"}
                    </button>
                  </div>
                ) : null}
              </>
            )}

            {replyLoading ? (
              <p className="pulse-soft text-sm font-semibold text-accent">
                Preparing response…
              </p>
            ) : null}
            {replyError ? (
              <p className="text-sm text-alert" role="status">
                {replyError}
              </p>
            ) : replySource === "fallback" &&
              assistantReply &&
              !replyLoading ? (
              <p className="text-xs text-muted" role="status">
                Using a short offline reply — live assistant was unavailable.
              </p>
            ) : null}
          </div>
        )}

        {(onLexiconModeChange || onTopicChip) && (
          <details className="mt-3 border-t border-ink/8 pt-3">
            <summary className="cursor-pointer text-xs font-semibold text-muted hover:text-ink">
              Signing options
            </summary>
            {onLexiconModeChange ? (
              <div
                className="mt-2.5 flex flex-wrap gap-1.5"
                role="group"
                aria-label="Sign lexicon"
              >
                {SIGN_LEXICON_MODES.map((modeOption) => {
                  const active = lexiconMode === modeOption.id;
                  return (
                    <button
                      key={modeOption.id}
                      type="button"
                      onClick={() => onLexiconModeChange(modeOption.id)}
                      className={
                        active
                          ? "min-h-10 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-white"
                          : "min-h-10 rounded-full border border-ink/12 bg-surface px-3 py-1.5 text-xs font-medium text-muted hover:text-ink"
                      }
                      title={modeOption.hint}
                    >
                      {modeOption.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
            {lexiconStatusNote ? (
              <p className="mt-2 text-xs text-muted">{lexiconStatusNote}</p>
            ) : null}
            {onTopicChip ? (
              <div className="mt-2.5">
                <p className="text-xs text-muted">Quick topics</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {TOPIC_CHIPS.map((chip) => (
                    <button
                      key={chip.id}
                      type="button"
                      disabled={busy || !voiceUnlocked}
                      onClick={() => onTopicChip(chip.sentence, [...chip.tokens])}
                      className="min-h-10 rounded-full border border-accent/25 bg-accent-soft/60 px-3 py-1.5 text-xs font-medium text-accent-deep disabled:opacity-40"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </details>
        )}
      </div>
    </section>
  );
}
