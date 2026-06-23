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

export function formatMoneyText(value) {
    return String(value || '')
        .replace(/(\d[\d,]*)\s*만원/g, (_, raw) => {
            const manwon = Number(String(raw).replace(/,/g, ''));
            if (!Number.isFinite(manwon))
                return `${raw}만원`;
            return formatMoney(manwon * 10000);
        })
        .replace(/(\d[\d,]*)\s*원/g, (_, raw) => {
            const won = Number(String(raw).replace(/,/g, ''));
            if (!Number.isFinite(won))
                return `${raw}원`;
            return formatMoney(won);
        });
}
