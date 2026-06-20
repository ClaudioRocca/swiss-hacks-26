import type { Concept } from "./use-pipeline";

/**
 * Maps common ticker symbols seen in portfolio/market data to
 * TradingView-compatible exchange:symbol format.
 */
const TICKER_MAP: Record<string, string> = {
  // Swiss stocks (SIX)
  "NESN": "SIX:NESN",
  "NESN.SW": "SIX:NESN",
  "NOVN": "SIX:NOVN",
  "NOVN.SW": "SIX:NOVN",
  "UBSG": "SIX:UBSG",
  "UBSG.SW": "SIX:UBSG",
  "ROP": "SIX:ROG",   // Roche (our data layer uses ROP); SIX:ROG on TradingView
  "ROG": "SIX:ROG",
  "ZURN": "SIX:ZURN",
  "ABBN": "SIX:ABBN",
  "SREN": "SIX:SREN",
  "LONN": "SIX:LONN",
  "GIVN": "SIX:GIVN",
  "ASML": "EURONEXT:ASML",
  // US stocks
  "AAPL": "NASDAQ:AAPL",
  "MSFT": "NASDAQ:MSFT",
  "GOOGL": "NASDAQ:GOOGL",
  "AMZN": "NASDAQ:AMZN",
  "NVDA": "NASDAQ:NVDA",
  "META": "NASDAQ:META",
  "TSLA": "NASDAQ:TSLA",
  "AMD": "NASDAQ:AMD",
  "INTC": "NASDAQ:INTC",
  "NFLX": "NASDAQ:NFLX",
  "JPM": "NYSE:JPM",
  "GS": "NYSE:GS",
  "BAC": "NYSE:BAC",
  "V": "NYSE:V",
  "MA": "NYSE:MA",
  // ETFs
  "SPY": "AMEX:SPY",
  "QQQ": "NASDAQ:QQQ",
  "GLD": "AMEX:GLD",
  "IWM": "AMEX:IWM",
  "VTI": "AMEX:VTI",
  // European
  "SIE.DE": "XETR:SIE",
  "SAP.DE": "XETR:SAP",
  "MC.PA": "EURONEXT:MC",
};

/**
 * Maps well-known company/entity names to TradingView symbols.
 * Used to resolve entities from conversation (e.g., "Nestlé" → SIX:NESN).
 */
const ENTITY_NAME_MAP: Record<string, string> = {
  "nestlé": "SIX:NESN",
  "nestle": "SIX:NESN",
  "novartis": "SIX:NOVN",
  "roche": "SIX:ROG",
  "asml": "EURONEXT:ASML",
  "ubs": "SIX:UBSG",
  "zurich insurance": "SIX:ZURN",
  "abb": "SIX:ABBN",
  "swiss re": "SIX:SREN",
  "lonza": "SIX:LONN",
  "givaudan": "SIX:GIVN",
  "apple": "NASDAQ:AAPL",
  "microsoft": "NASDAQ:MSFT",
  "google": "NASDAQ:GOOGL",
  "alphabet": "NASDAQ:GOOGL",
  "amazon": "NASDAQ:AMZN",
  "nvidia": "NASDAQ:NVDA",
  "meta": "NASDAQ:META",
  "tesla": "NASDAQ:TSLA",
  "amd": "NASDAQ:AMD",
  "intel": "NASDAQ:INTC",
  "netflix": "NASDAQ:NFLX",
  "jp morgan": "NYSE:JPM",
  "jpmorgan": "NYSE:JPM",
  "goldman sachs": "NYSE:GS",
  "goldman": "NYSE:GS",
  "bank of america": "NYSE:BAC",
  "visa": "NYSE:V",
  "mastercard": "NYSE:MA",
};

/**
 * Resolve a raw ticker string or entity name into a TradingView symbol.
 * Returns null if unresolvable.
 */
export function resolveToTradingViewSymbol(raw: string): string | null {
  const upper = raw.trim().toUpperCase();
  const lower = raw.trim().toLowerCase();

  // Direct ticker match
  if (TICKER_MAP[upper]) return TICKER_MAP[upper];

  // Entity name match
  if (ENTITY_NAME_MAP[lower]) return ENTITY_NAME_MAP[lower];

  // If it already looks like EXCHANGE:SYMBOL, pass through
  if (/^[A-Z]+:[A-Z0-9.]+$/.test(upper)) return upper;

  // Otherwise unresolvable — do NOT guess. A free-text entity like "ROCHE" or
  // "TODAY" must not be passed through as a fake ticker (it 404s the chart).
  return null;
}

/**
 * Extracts all unique TradingView-compatible ticker symbols from an array
 * of concepts. Looks at both entities and executed query results.
 */
export function extractTickersFromConcepts(concepts: Concept[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const concept of concepts) {
    // Check entities
    for (const entity of concept.entities) {
      const symbol = resolveToTradingViewSymbol(entity);
      if (symbol && !seen.has(symbol)) {
        seen.add(symbol);
        result.push(symbol);
      }
    }

    // Check executed query results for ticker fields
    for (const query of concept.executed_queries) {
      if (query.source === "market_movements" || query.source === "portfolio" || query.source === "trades") {
        const rows = query.results as Array<Record<string, unknown>> | null;
        if (Array.isArray(rows)) {
          for (const row of rows) {
            if (typeof row.ticker === "string") {
              const symbol = resolveToTradingViewSymbol(row.ticker);
              if (symbol && !seen.has(symbol)) {
                seen.add(symbol);
                result.push(symbol);
              }
            }
          }
        }
      }
    }
  }

  return result;
}
