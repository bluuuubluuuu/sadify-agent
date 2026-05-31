"use client";

import { useState, type ReactNode } from "react";
import type { Stage } from "../../lib/stage";
import { Icon } from "../ui/Icon";
import styles from "./AppShell.module.css";

/**
 * Three-pane workspace shell (Sidebar | Chat | Preview) with stage-driven
 * adaptive emphasis and responsive collapse.
 *
 * Observation hooks (non-visible, for tests/manual reference, NOT user-facing
 * logging): the root carries data-stage; each pane carries data-pane and the
 * active pane carries data-hero.
 */
export function AppShell({
  stage,
  sidebar,
  chat,
  preview,
  previewLabel = "Preview",
}: {
  stage: Stage;
  sidebar: ReactNode;
  chat: ReactNode;
  preview: ReactNode;
  previewLabel?: string;
}) {
  const [mobileTab, setMobileTab] = useState<"chat" | "preview">("chat");
  const [navOpen, setNavOpen] = useState(false);
  const [previewDrawer, setPreviewDrawer] = useState(false);
  const heroPane = stage === "review" ? "preview" : "chat";

  return (
    <div className={styles.shell} data-stage={stage}>
      {/* Mobile top bar */}
      <div className={styles.mobileBar}>
        <button
          type="button"
          className={styles.iconBtn}
          aria-label="Open projects and account"
          onClick={() => setNavOpen(true)}
        >
          <Icon name="menu" size={22} />
        </button>
        <div className={styles.segment} role="tablist" aria-label="Switch view">
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === "chat"}
            className={mobileTab === "chat" ? styles.segOn : styles.seg}
            onClick={() => setMobileTab("chat")}
          >
            Chat
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mobileTab === "preview"}
            className={mobileTab === "preview" ? styles.segOn : styles.seg}
            onClick={() => setMobileTab("preview")}
          >
            {previewLabel}
          </button>
        </div>
      </div>

      {/* Sidebar (drawer on mobile) */}
      {navOpen ? (
        <button
          type="button"
          className={styles.scrim}
          aria-label="Close menu"
          onClick={() => setNavOpen(false)}
        />
      ) : null}
      <aside
        className={[styles.sidebar, navOpen ? styles.sidebarOpen : ""].filter(Boolean).join(" ")}
        data-pane="sidebar"
      >
        {sidebar}
      </aside>

      {/* Chat */}
      <section
        className={[styles.chat, mobileTab === "chat" ? styles.mobileActive : styles.mobileHidden]
          .filter(Boolean)
          .join(" ")}
        data-pane="chat"
        data-hero={heroPane === "chat" ? "true" : undefined}
      >
        {chat}
      </section>

      {/* Tablet preview toggle */}
      <button
        type="button"
        className={styles.previewToggle}
        onClick={() => setPreviewDrawer(true)}
      >
        {previewLabel}
        <Icon name="caretRight" size={18} />
      </button>

      {/* Preview (drawer on tablet) */}
      {previewDrawer ? (
        <button
          type="button"
          className={styles.scrim}
          aria-label="Close preview"
          onClick={() => setPreviewDrawer(false)}
        />
      ) : null}
      <section
        className={[
          styles.preview,
          previewDrawer ? styles.previewDrawerOpen : "",
          mobileTab === "preview" ? styles.mobileActive : styles.mobileHidden,
        ]
          .filter(Boolean)
          .join(" ")}
        data-pane="preview"
        data-hero={heroPane === "preview" ? "true" : undefined}
      >
        {preview}
      </section>
    </div>
  );
}
