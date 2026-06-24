<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { createAgoraComment, createAgoraPost, deleteAgoraComment, deleteAgoraPost, fetchAgoraPosts, fetchAuthSession, fetchDefaultVideos, searchVideos } from '../api/firsthome';

const boardTabs = [
  { value: 'all', label: '전체' },
  { value: 'notice', label: '청약' },
  { value: 'product', label: '금융상품' },
  { value: 'funding', label: '자금준비' },
  { value: 'free', label: '자유 게시판' },
];

const categoryLabels = {
  notice: '청약',
  product: '금융상품',
  funding: '자금준비',
  free: '자유',
};

const session = ref(null);
const videoQuery = ref('청약 공공분양');
const videos = ref([]);
const videoMessage = ref('');
const videoLoading = ref(false);
const lastVideoQuery = ref('');
const selectedVideo = ref(null);
const posts = ref([]);
const activeBoard = ref('all');
const postForm = ref({ title: '', content: '', category: 'notice' });
const commentInputs = ref({});
const error = ref('');
const isLoggedIn = computed(() => Boolean(session.value?.user?.is_authenticated));
const isAllBoard = computed(() => activeBoard.value === 'all');
const boardTitle = computed(() => boardTabs.find((tab) => tab.value === activeBoard.value)?.label ?? '전체');
let videoSearchTimer = null;

function normalizedVideoQuery(value) {
  return (value ?? '').trim().replace(/\s+/g, ' ');
}

function requestVideoSearch() {
  const query = normalizedVideoQuery(videoQuery.value);
  if (!query || videoLoading.value || query === lastVideoQuery.value) {
    return;
  }
  if (videoSearchTimer) {
    clearTimeout(videoSearchTimer);
  }
  videoSearchTimer = setTimeout(() => {
    loadVideos(true, query);
  }, 500);
}

async function loadVideos(useSearch = false, requestedQuery = '') {
  if (videoLoading.value) {
    return;
  }
  const query = normalizedVideoQuery(requestedQuery || videoQuery.value);
  if (useSearch && !query) {
    return;
  }
  videoLoading.value = true;
  try {
    const response = useSearch ? await searchVideos(query) : await fetchDefaultVideos();
    videos.value = (response.items ?? []).slice(0, 3);
    videoMessage.value = response.fallback_reason ?? '';
    lastVideoQuery.value = useSearch ? query : '';
  } finally {
    videoLoading.value = false;
  }
}

async function loadPosts() {
  const params = isAllBoard.value ? undefined : { category: activeBoard.value };
  posts.value = await fetchAgoraPosts(params);
}

async function selectBoard(board) {
  activeBoard.value = board;
  if (!isAllBoard.value) {
    postForm.value = { ...postForm.value, category: board };
  }
  await loadPosts();
}

async function submitPost() {
  if (!isLoggedIn.value) {
    error.value = '로그인 후 글을 작성할 수 있습니다.';
    return;
  }
  const category = isAllBoard.value ? postForm.value.category : activeBoard.value;
  await createAgoraPost({ ...postForm.value, category });
  postForm.value = { title: '', content: '', category: isAllBoard.value ? postForm.value.category : activeBoard.value };
  await loadPosts();
}

async function removePost(post) {
  await deleteAgoraPost(post.id);
  await loadPosts();
}

async function submitComment(post) {
  const content = commentInputs.value[post.id] ?? '';
  if (!content.trim())
    return;
  await createAgoraComment(post.id, { content });
  commentInputs.value = { ...commentInputs.value, [post.id]: '' };
  await loadPosts();
}

async function removeComment(comment) {
  await deleteAgoraComment(comment.id);
  await loadPosts();
}

onMounted(async () => {
  session.value = await fetchAuthSession();
  await Promise.all([loadVideos(false), loadPosts()]);
});

onBeforeUnmount(() => {
  if (videoSearchTimer) {
    clearTimeout(videoSearchTimer);
  }
});
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p class="text-sm font-bold text-blue-700">청약 정보 광장</p>
      <h1 class="mt-1 text-3xl font-black text-slate-950">청약 아고라</h1>
      <p class="mt-2 text-sm leading-6 text-slate-500">청약, 분양, 금리, 주거 금융 관련 영상을 검색하고 의견을 나눕니다.</p>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex flex-col gap-3 md:flex-row">
        <input v-model="videoQuery" class="h-11 flex-1 rounded-lg border border-slate-200 px-3 text-sm font-bold" type="search" placeholder="관심 키워드 검색" @keydown.enter.prevent="requestVideoSearch" />
        <button class="rounded-lg bg-blue-600 px-4 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-60" type="button" :disabled="videoLoading || !normalizedVideoQuery(videoQuery)" @click="requestVideoSearch">
          {{ videoLoading ? '검색 중...' : '검색' }}
        </button>
      </div>
      <p v-if="videoMessage" class="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm font-bold text-slate-500">{{ videoMessage }}</p>
      <div class="mt-4 grid gap-4 lg:grid-cols-3">
        <button v-for="video in videos" :key="video.video_id" type="button" class="overflow-hidden rounded-lg border border-slate-200 bg-white text-left shadow-sm" @click="selectedVideo = video">
          <img :src="video.thumbnail_url" alt="" class="aspect-video w-full object-cover" />
          <div class="p-4">
            <p class="line-clamp-2 font-black text-slate-950">{{ video.title }}</p>
            <p class="mt-2 text-sm font-bold text-slate-500">{{ video.channel_title }}</p>
          </div>
        </button>
      </div>
      <div v-if="!videos.length" class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-5 text-sm font-bold text-slate-500">
        표시할 청약 관련 영상이 없습니다. 검색어를 바꾸거나 YouTube API 키 설정을 확인해 주세요.
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-lg font-black text-slate-950">커뮤니티</h2>
          <p class="mt-1 text-sm font-bold text-slate-500">{{ boardTitle }} 게시글을 확인합니다.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tab in boardTabs"
            :key="tab.value"
            type="button"
            class="h-10 rounded-lg border px-4 text-sm font-black transition"
            :class="activeBoard === tab.value ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-blue-50'"
            @click="selectBoard(tab.value)"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
      <p v-if="error" class="mt-2 text-sm font-bold text-amber-700">{{ error }}</p>
      <div class="mt-4 grid gap-3 md:grid-cols-[160px_1fr]">
        <select v-if="isAllBoard" v-model="postForm.category" class="h-11 rounded-lg border border-slate-200 px-3 text-sm font-bold">
          <option value="notice">청약</option>
          <option value="product">금융상품</option>
          <option value="funding">자금준비</option>
          <option value="free">자유</option>
        </select>
        <div v-else class="flex h-11 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-black text-blue-700">
          {{ categoryLabels[activeBoard] }}
        </div>
        <input v-model="postForm.title" class="h-11 rounded-lg border border-slate-200 px-3 text-sm font-bold" :placeholder="`${boardTitle} 글 제목`" />
        <textarea v-model="postForm.content" class="min-h-24 rounded-lg border border-slate-200 p-3 text-sm font-bold md:col-span-2" placeholder="내용"></textarea>
        <button type="button" class="h-11 rounded-lg bg-slate-950 px-4 text-sm font-black text-white md:col-span-2" @click="submitPost">
          {{ isLoggedIn ? '글쓰기' : '로그인 후 글쓰기' }}
        </button>
      </div>

      <div class="mt-5 space-y-3">
        <article v-for="post in posts" :key="post.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs font-black text-blue-700">{{ categoryLabels[post.category] ?? post.category }} · {{ post.author_username }} · 댓글 {{ post.comment_count }}</p>
              <h3 class="mt-1 text-lg font-black text-slate-950">{{ post.title }}</h3>
              <p class="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{{ post.content }}</p>
            </div>
            <button v-if="post.can_edit" type="button" class="text-sm font-black text-rose-600" @click="removePost(post)">삭제</button>
          </div>
          <div class="mt-4 space-y-2">
            <div v-for="comment in post.comments" :key="comment.id" class="flex items-start justify-between gap-3 rounded-md bg-white p-3 text-sm">
              <p><b>{{ comment.author_username }}</b> · {{ comment.content }}</p>
              <button v-if="comment.can_edit" type="button" class="font-black text-rose-600" @click="removeComment(comment)">삭제</button>
            </div>
            <div class="flex gap-2">
              <input v-model="commentInputs[post.id]" class="h-10 flex-1 rounded-lg border border-slate-200 px-3 text-sm font-bold" placeholder="댓글" />
              <button type="button" class="rounded-lg bg-blue-600 px-3 text-sm font-black text-white" @click="submitComment(post)">등록</button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="selectedVideo" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4" @click.self="selectedVideo = null">
      <section class="w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <iframe class="aspect-video w-full" :src="selectedVideo.embed_url || `https://www.youtube.com/embed/${selectedVideo.video_id}`" title="video" allowfullscreen></iframe>
        <div class="p-5">
          <h2 class="text-xl font-black text-slate-950">{{ selectedVideo.title }}</h2>
          <p class="mt-1 text-sm font-bold text-slate-500">{{ selectedVideo.channel_title }} · {{ selectedVideo.published_at }}</p>
          <button class="mt-4 rounded-lg bg-slate-950 px-4 py-2 text-sm font-black text-white" type="button" @click="selectedVideo = null">닫기</button>
        </div>
      </section>
    </div>
  </div>
</template>
