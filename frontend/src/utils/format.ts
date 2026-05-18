export function formatMoney(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`
}
