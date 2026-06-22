<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Loader2, MessageCircle, Send, Sparkles, X } from 'lucide-vue-next';
import { askCoachChat, fetchDashboard } from '../api/firsthome';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
import { readCurrentSelection } from '../utils/selectionState';
const route = useRoute();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const isOpen = ref(false);
const pending = ref(false);
const draft = ref('');
const activeNoticeId = ref(null);
const messageListRef = ref(null);
const initialMessage = {
    role: 'assistant',
    content: '어느 화면에서든 청약 조건, 자금 흐름, 화면 이용 방법을 물어보세요. 선택한 공고와 옵션이 있으면 그 기준으로 답변할게요.',
};
const messages = ref([
    {
        ...initialMessage,
    },
]);
const canSend = computed(() => draft.value.trim().length > 0 && !pending.value);
const pageType = computed(() => {
    const name = String(route.name || '');
    if (name === 'notice-detail')
        return 'notice_detail';
    if (name === 'ai-coach')
        return 'ai_coach';
    return name || 'unknown';
});
const quickPrompts = computed(() => {
    const byPage = {
        home: ['이 화면은 어떻게 쓰면 돼?', '처음이면 무엇부터 하면 돼?', '추천 후보를 고르는 흐름을 알려줘.'],
        profile: ['조건 입력은 어떤 값이 중요해?', '희망 지역은 어떻게 선택해야 해?', '저장하면 어디에 반영돼?'],
        recommendations: ['추천 점수는 어떻게 봐야 해?', '어떤 공고부터 열어보면 돼?', 'Fixture와 실제 공고는 뭐가 달라?'],
        notice_detail: ['이 공고에서 먼저 볼 항목은?', '필수 서류는 어디에서 확인해?', '옵션을 바꾸면 뭐가 달라져?'],
        funding: ['계약금 부족액을 어떻게 봐야 해?', '다른 옵션과 비교하는 방법은?', 'AI 코칭 받기는 언제 눌러?'],
        ai_coach: ['바로 처리할 일을 요약해줘.', '공식 확인 항목은 어떻게 봐?', '이 후보를 계속 볼지 판단 기준은?'],
        map: ['지도 화면은 어떻게 써?', '지역 공고를 선택하면 다음은?', '관심 지역을 비교하는 방법은?'],
        favorites: ['관심목록은 어떻게 활용해?', '저장한 옵션 자금은 어디서 봐?', '관심 공고를 다시 비교하려면?'],
    };
    return byPage[pageType.value] ?? ['이 화면은 어떻게 쓰면 돼?', '청약 추천 흐름을 알려줘.', '내가 다음에 할 일은?'];
});
function resetChat() {
    messages.value = [{ ...initialMessage }];
    draft.value = '';
    pending.value = false;
    activeNoticeId.value = null;
    isOpen.value = false;
}
async function scrollToLatestMessage() {
    await nextTick();
    if (!messageListRef.value)
        return;
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
}
watch(() => authStore.user.is_authenticated, () => {
    resetChat();
});
watch([messages, pending, isOpen], () => {
    if (isOpen.value) {
        void scrollToLatestMessage();
    }
}, { deep: true });
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
function selectedNoticeId() {
    return routeNoticeId() || readCurrentSelection().noticeId || null;
}
function selectedOptionId() {
    return routeOptionId() || readCurrentSelection().optionId || null;
}
function pageContext(noticeId) {
    return {
        path: route.fullPath,
        page_type: pageType.value,
        notice_id: noticeId || selectedNoticeId(),
        option_id: selectedOptionId(),
        is_authenticated: Boolean(authStore.user.is_authenticated),
    };
}
async function resolveNoticeId() {
    const selected = selectedNoticeId();
    if (selected) {
        activeNoticeId.value = selected;
        return selected;
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
        const response = await askCoachChat(noticeId, content, profileStore.profile, selectedOptionId(), pageContext(noticeId));
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
        fixture: 'Fixture',
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
              청약 네비 챗봇
              <Sparkles class="h-3.5 w-3.5 text-amber-300" />
            </p>
            <p class="text-xs text-slate-300">화면 설명, 청약 질문, 이용 방법</p>
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

      <div ref="messageListRef" class="max-h-[380px] space-y-3 overflow-y-auto p-4">
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
              {{ message.source === 'llm' ? 'OpenAI LLM' : message.source === 'template_fallback' ? '기본 답변' : message.source }}
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
      title="청약 네비 챗봇 열기"
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
