const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  GBP: "\u00A3",
  EUR: "\u20AC",
  CAD: "C$",
  AUD: "A$",
  INR: "\u20B9",
};

function getCurrencySymbol(currency: string): string {
  return CURRENCY_SYMBOLS[currency.toUpperCase()] ?? currency.toUpperCase();
}

export function formatSalary(
  min: number,
  max: number,
  currency: string,
): string {
  const symbol = getCurrencySymbol(currency);
  return `${symbol}${min.toLocaleString()} - ${symbol}${max.toLocaleString()}`;
}
