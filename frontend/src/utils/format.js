export function formatMoney(value) {
    return `${Math.round(value / 10000).toLocaleString()}만원`;
}
