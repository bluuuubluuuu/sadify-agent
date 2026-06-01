"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "../ui/Icon";
import { ThinkingDots } from "../ui/ThinkingDots";
import styles from "./chat.module.css";

export type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  text: string;
  why?: string;
};

export function ChatThread({
  messages,
  thinking,
  footer,
}: {
  messages: ChatMessage[];
  thinking?: boolean;
  footer?: ReactNode;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, thinking]);

  return (
    <>
      <div className={styles.thread}>
        {messages.map((message) =>
          message.role === "assistant" ? (
            <div key={message.id} className={`${styles.bubble} ${styles.bot}`}>
              <span className={styles.botHead}>
                <Icon name="sparkle" size={18} color="var(--c-secondary)" />
                <span>{message.text}</span>
              </span>
              {message.why ? (
                <span className={styles.why}>
                  <Icon name="info" size={14} color="var(--c-subtle)" />
                  Why this matters: {message.why}
                </span>
              ) : null}
            </div>
          ) : (
            <div key={message.id} className={`${styles.bubble} ${styles.me}`}>
              {message.text}
            </div>
          ),
        )}
        {thinking ? <ThinkingDots /> : null}
        <div ref={endRef} />
      </div>
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </>
  );
}
