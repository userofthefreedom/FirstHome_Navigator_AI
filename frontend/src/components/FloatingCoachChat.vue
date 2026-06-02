<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { Loader2, MessageCircle, Send, Sparkles, X } from 'lucide-vue-next';
import { askCoachChat, fetchDashboard } from '../api/firsthome';
import { useProfileStore } from '../stores/profileStore';
const route = useRoute();
const profileStore = useProfileStore();
const isOpen = ref(false);
const pending = ref(false);
const draft = ref('');
const activeNoticeId = ref(null);
const messages = ref([
    {
        role: 'assistant',
        content: '선택한 공고와 주택형 옵션을 기준으로 계약금 부족액, 납부 일정, 공식 확인 포인트를 정리해드릴게요.',
    },
]);
const quickPrompts = [
    '이 옵션에서 내가 가장 먼저 확인할 조건은?',
    '선택한 옵션의 계약금 부담은 어느 정도야?',
    '59A와 74A 중 지금 자금으로 더 현실적인 옵션은?',
    '공식 공고문에서 확인해야 할 근거는 어디야?',
    '이번 주에 해야 할 일을 3개로 정리해줘.',
];
const canSend = computed(() => draft.value.trim().length > 0 && !pending.value);
function routeNoticeId() {
    const raw = route.params.noticeId;
    const value = Array.isArray(raw) ? raw[0] : raw;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
function routeOptionId() {
    const raw = route.query.option_id;
    const value = Array.isArray(raw) ? raw[0] : raw;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
async function resolveNoticeId() {
    const fromRoute = routeNoticeId();
    if (fromRoute) {
        activeNoticeId.value = fromRoute;
        return fromRoute;
    }
    if (activeNoticeId.value)
        return activeNoticeId.value;
    const dashboard = await fetchDashboard();
    activeNoticeId.value = dashboard.top_recommendations[0]?.notice_id ?? 101;
    return activeNoticeId.value;
}
async function sendMessage(nextMessage = draft.value) {
    const content = nextMessage.trim();
    if (!content || pending.value)
        return;
    messages.value.push({ role: 'user', content });
    draft.value = '';
    pending.value = true;
    try {
        if (!profileStore.loaded) {
            await profileStore.hydrateProfile();
        }
        const noticeId = await resolveNoticeId();
        const response = await askCoachChat(noticeId, content, profileStore.profile, routeOptionId());
        messages.value.push({
            role: 'assistant',
            content: response.reply,
            actions: response.suggested_actions,
            source: response.source,
            contextRefs: response.context_refs,
        });
    }
    catch {
        messages.value.push({
            role: 'assistant',
            content: '잠시 연결이 불안정합니다. 백엔드 서버 상태를 확인한 뒤 다시 시도해주세요.',
        });
    }
    finally {
        pending.value = false;
    }
}
function handleEnter(event) {
    if (event.shiftKey)
        return;
    event.preventDefault();
    void sendMessage();
}
function contextLabel(ref) {
    const labels = {
        notice: '공고',
        funding_plan: '자금계산',
        unit_option: '주택형',
        payment_schedule: '납부일정',
        checklist: '체크리스트',
        evidence: '근거문장',
        required_document: '필수서류',
    };
    const type = String(ref.type ?? '');
    const label = String(ref.label ?? ref.id ?? '');
    return `${(labels[type] ?? type) || '근거'}: ${label}`;
}
</script>

<template>
  <div class="fixed bottom-24 right-4 z-50 lg:bottom-6 lg:right-6">
    <section
      v-if="isOpen"
      class="w-[min(calc(100vw-2rem),400px)] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
    >
      <div class="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-950 px-4 py-3 text-white">
        <div class="flex items-center gap-2">
          <span class="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-sm font-black text-slate-950 shadow-sm">
            AI
          </span>
          <div>
            <p class="flex items-center gap-1 text-sm font-bold text-white">
              주택형 자금 코치
              <Sparkles class="h-3.5 w-3.5 text-amber-300" />
            </p>
            <p class="text-xs text-slate-300">옵션별 계약금, 일정, 공식 근거</p>
          </div>
        </div>
        <button
          type="button"
          class="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/10 text-white transition hover:bg-white/15"
          title="닫기"
          @click="isOpen = false"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="max-h-[380px] space-y-3 overflow-y-auto p-4">
        <div
          v-for="(message, index) in messages"
          :key="`${message.role}-${index}`"
          class="flex"
          :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[88%] rounded-lg px-3 py-2 text-sm leading-6 shadow-sm"
            :class="message.role === 'user' ? 'bg-blue-600 text-white' : 'border border-slate-200 bg-slate-50 text-slate-700'"
          >
            <p>{{ message.content }}</p>
            <ul v-if="message.actions?.length" class="mt-2 space-y-1 border-t border-slate-200 pt-2 text-xs leading-5">
              <li v-for="action in message.actions" :key="action" class="flex gap-1.5">
                <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                <span>{{ action }}</span>
              </li>
            </ul>
            <p v-if="message.source" class="mt-2 border-t border-slate-200 pt-2 text-[11px] font-bold uppercase text-slate-400">
              source: {{ message.source }}
            </p>
            <div
              v-if="message.contextRefs?.length"
              class="mt-2 border-t border-slate-200 pt-2 text-[11px] text-slate-500"
            >
              <p class="font-bold text-slate-400">사용한 근거</p>
              <div class="mt-1 flex flex-wrap gap-1">
                <span
                  v-for="ref in message.contextRefs.slice(0, 4)"
                  :key="`${ref.type}-${ref.id}`"
                  class="rounded border border-slate-200 bg-white px-1.5 py-0.5"
                >
                  {{ contextLabel(ref) }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="pending" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
          <Loader2 class="h-4 w-4 animate-spin" />
          답변 생성 중
        </div>
      </div>

      <div class="flex flex-wrap gap-2 border-t border-slate-200 px-4 py-3">
        <button
          v-for="prompt in quickPrompts"
          :key="prompt"
          type="button"
          class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
          :disabled="pending"
          @click="sendMessage(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <form class="flex gap-2 border-t border-slate-200 p-3" @submit.prevent="sendMessage()">
        <textarea
          v-model="draft"
          rows="1"
          class="min-h-10 flex-1 resize-none rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
          placeholder="궁금한 내용을 입력"
          @keydown.enter="handleEnter"
        />
        <button
          type="submit"
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!canSend"
          title="전송"
        >
          <Send class="h-4 w-4" />
        </button>
      </form>
    </section>

    <button
      v-else
      type="button"
      class="relative flex h-16 w-16 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700"
      title="주택형 자금 코치 열기"
      @click="isOpen = true"
    >
      <span class="text-sm font-black leading-none">AI</span>
      <span class="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500 text-xs font-bold text-white">
        Q
      </span>
      <MessageCircle class="absolute bottom-2 right-2 h-4 w-4" />
    </button>
  </div>
</template>
