import { useEffect, useState } from "react";

// True while the CSS media query matches, e.g. useMediaQuery("(max-width: 639px)").
// For layout that CSS alone can't express (chart axis widths, tick formats).
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches
  );

  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
