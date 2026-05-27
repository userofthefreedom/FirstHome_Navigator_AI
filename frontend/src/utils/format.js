export function formatMoney(value) {
    const amount = Number(value || 0);
    const tenThousands = Math.round(amount / 10000);
    if (Math.abs(amount) < 100000000) {
        return `${tenThousands.toLocaleString()}만원`;
    }

    const eok = Math.trunc(tenThousands / 10000);
    const man = Math.abs(tenThousands % 10000);
    return man > 0 ? `${eok.toLocaleString()}억 ${man.toLocaleString()}만원` : `${eok.toLocaleString()}억원`;
}
