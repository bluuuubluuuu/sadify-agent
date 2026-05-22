import type { Choice } from "../lib/mockState";

type Props = {
  text: string;
  whyThisMatters: string;
  choices: Choice[];
  selectedChoiceId?: string;
  onChoiceSelect?: (choiceId: string) => void;
};

export function CurrentQuestion({
  text,
  whyThisMatters,
  choices,
  selectedChoiceId = "",
  onChoiceSelect,
}: Props) {
  return (
    <section className="question-panel" aria-labelledby="current-question">
      <p className="eyebrow">Current question</p>
      <h2 id="current-question">{text}</h2>
      <p className="why">{whyThisMatters}</p>

      <div className="choice-grid" aria-label="Answer choices">
        {choices.map((choice) => {
          const choiceClassName = `choice-button ${
            selectedChoiceId === choice.id ? "selected" : ""
          }${choice.is_disabled ? " disabled-choice" : ""}${
            onChoiceSelect ? "" : " read-only"
          }`;

          return onChoiceSelect ? (
            <button
              key={choice.id}
              type="button"
              className={choiceClassName}
              aria-pressed={selectedChoiceId === choice.id}
              disabled={choice.is_disabled}
              onClick={() => onChoiceSelect(choice.id)}
            >
              <span>{choice.label}</span>
              {choice.status_label ? <small>{choice.status_label}</small> : null}
            </button>
          ) : (
            <div key={choice.id} className={choiceClassName} role="listitem">
              <span>{choice.label}</span>
              {choice.status_label ? <small>{choice.status_label}</small> : null}
            </div>
          );
        })}
      </div>

      <label className="amend-field">
        <span>Amend answer</span>
        <textarea placeholder="Add details or correct the answer here." rows={4} />
      </label>
    </section>
  );
}
