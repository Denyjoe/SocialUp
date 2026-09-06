import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

import { Modal } from "./Modal";

export interface ConfirmOptions {
  /** Defaults to "Please confirm". */
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Styles the confirm button as a destructive action (deletes, refunds, etc.). */
  danger?: boolean;
}

type ConfirmFn = (options: ConfirmOptions | string) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

/**
 * App-styled replacement for the browser's native `confirm()` — that popup
 * carries the browser's own chrome (its own font, its own OK/Cancel
 * wording, no dark-mode awareness) rather than looking like part of the
 * app. Mounted once near the root; any component calls `useConfirm()` and
 * awaits the result exactly like the native function, just async since a
 * real modal can't block the way `confirm()` does.
 */
export function ConfirmDialogProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);

  const confirmAction = useCallback<ConfirmFn>((options) => {
    const normalized = typeof options === "string" ? { message: options } : options;
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
      setPending(normalized);
    });
  }, []);

  function settle(result: boolean) {
    resolver.current?.(result);
    resolver.current = null;
    setPending(null);
  }

  return (
    <ConfirmContext.Provider value={confirmAction}>
      {children}
      {pending && (
        <Modal title={pending.title ?? "Please confirm"} onClose={() => settle(false)}>
          <p style={{ marginTop: 0 }}>{pending.message}</p>
          <div className="confirm-dialog__actions">
            <button type="button" className="btn-secondary" onClick={() => settle(false)}>
              {pending.cancelLabel ?? "Cancel"}
            </button>
            <button
              type="button"
              className={pending.danger ? "btn-danger" : ""}
              onClick={() => settle(true)}
            >
              {pending.confirmLabel ?? "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </ConfirmContext.Provider>
  );
}

/** Returns an async function: `if (await confirmDialog("Delete this?")) { ... }` */
export function useConfirm(): ConfirmFn {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a ConfirmDialogProvider");
  return ctx;
}
