// Text as a search should compare it: lower-case, with accents removed, so
// "Binan" finds "Biñan" (and "Biñan" finds "Binan"), "Banos" finds "Baños".
export function foldText(s) {
  return String(s ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

// True when `text` contains `query`, ignoring case and accents. `query` should
// already be folded (fold it once, outside the loop).
export const matchesQuery = (text, foldedQuery) => !foldedQuery || foldText(text).includes(foldedQuery);
