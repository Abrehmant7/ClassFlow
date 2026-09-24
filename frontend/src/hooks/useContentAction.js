import { useRef, useState } from "react";

import { parseContentError } from "../utils/classContent.js";

export default function useContentAction() {
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run(action) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (apiError) {
      setError(parseContentError(apiError));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return { busy, error, setError, run };
}
