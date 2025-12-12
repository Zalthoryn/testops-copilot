import { useEffect, useRef } from "react";

export const usePolling = (callback: () => Promise<void>, interval: number, enabled = true) => {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    let isActive = true;

    const tick = async () => {
      if (!isActive) return;
      try {
        await savedCallback.current();
      } catch (e) {
        console.error("Polling error", e);
      }
    };

    const id = setInterval(tick, interval);
    tick();

    return () => {
      isActive = false;
      clearInterval(id);
    };
  }, [interval, enabled]);
};

