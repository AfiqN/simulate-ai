import { useEffect, useRef } from "react";

/**
 * Requests notification permission on mount (if not already decided),
 * and exposes a `notify` function to fire browser notifications.
 */
export function useNotification() {
  const permissionRef = useRef<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );

  useEffect(() => {
    if (typeof Notification === "undefined") return;
    if (Notification.permission === "default") {
      Notification.requestPermission().then((p) => {
        permissionRef.current = p;
      });
    }
  }, []);

  function notify(title: string, body?: string) {
    if (typeof Notification === "undefined") return;
    if (permissionRef.current !== "granted") return;
    // Only fire when tab is not focused (user is away)
    if (document.visibilityState === "visible") return;

    const n = new Notification(title, {
      body,
      icon: "/logo-mark.svg",
      tag: "simulate-ai-result", // replaces previous if still showing
    });
    n.onclick = () => {
      window.focus();
      n.close();
    };
  }

  return { notify };
}
