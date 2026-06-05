import { fetchAccountState, saveAccountStateToApi } from '../api/firsthome';

const STORAGE_KEY = 'firsthome.current_selection';

export function readCurrentSelection() {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw)
            return {};
        const parsed = JSON.parse(raw);
        return {
            noticeId: Number(parsed.noticeId || 0) || null,
            optionId: Number(parsed.optionId || 0) || null,
            updatedAt: parsed.updatedAt || '',
        };
    }
    catch {
        return {};
    }
}

export function saveCurrentSelection(noticeId, optionId) {
    const nextNoticeId = Number(noticeId || 0) || null;
    const nextOptionId = Number(optionId || 0) || null;
    if (!nextNoticeId)
        return {};
    const selection = {
        noticeId: nextNoticeId,
        optionId: nextOptionId,
        updatedAt: new Date().toISOString(),
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
    void saveAccountStateToApi({
        current_notice_id: nextNoticeId,
        current_option_id: nextOptionId,
    }).catch(() => {});
    return selection;
}

export function clearCurrentSelection() {
    window.localStorage.removeItem(STORAGE_KEY);
}

export function applyAccountSelection(accountState) {
    const noticeId = Number(accountState?.current_notice_id || accountState?.noticeId || 0) || null;
    const optionId = Number(accountState?.current_option_id || accountState?.optionId || 0) || null;
    if (!noticeId)
        return {};
    const selection = {
        noticeId,
        optionId,
        updatedAt: accountState?.updated_at || new Date().toISOString(),
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
    return selection;
}

export async function syncCurrentSelectionWithAccount(accountState = null) {
    const state = accountState ?? await fetchAccountState().catch(() => null);
    const serverSelection = applyAccountSelection(state);
    if (serverSelection.noticeId)
        return serverSelection;
    const localSelection = readCurrentSelection();
    if (localSelection.noticeId) {
        await saveAccountStateToApi({
            current_notice_id: localSelection.noticeId,
            current_option_id: localSelection.optionId,
        }).catch(() => {});
    }
    return localSelection;
}

export function currentSelectionRoute(basePath) {
    const selection = readCurrentSelection();
    if (!selection.noticeId)
        return basePath;
    const path = `${basePath}/${selection.noticeId}`;
    return selection.optionId ? { path, query: { option_id: selection.optionId } } : path;
}
