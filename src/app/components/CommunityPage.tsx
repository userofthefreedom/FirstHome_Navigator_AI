import { useState } from "react";
import {
  Flame,
  Heart,
  MessageSquare,
  PenLine,
  Search,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { communityPosts, profile, subscriptions } from "../data/cheongyak";

const categories = ["전체", "후기", "질문", "꿀팁", "동네정보"];

const weeklyTopics = [
  "신혼 특공 소득 기준",
  "서류 발급일 실수",
  "서초 모델하우스 후기",
  "계약금 마련 플랜",
];

export function CommunityPage() {
  const [category, setCategory] = useState("전체");
  const posts = category === "전체" ? communityPosts : communityPosts.filter((post) => post.category === category);

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <div className="mb-6 grid gap-4 lg:grid-cols-[1fr_360px]">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-semibold text-blue-700">커뮤니티</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">
                청약 경험과 동네 정보를 함께 확인하세요
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                관심 단지 후기, 특별공급 질문, 서류 실수 방지 팁을 같은 조건의 사용자들과 공유합니다.
              </p>
            </div>
            <button className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-bold text-white transition hover:bg-blue-700">
              <PenLine className="h-4 w-4" />
              글쓰기
            </button>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {[
              ["관심 지역", profile.region],
              ["활성 게시글", `${communityPosts.length * 12}개`],
              ["내 추천 단지", subscriptions[0].name],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-1 font-bold text-slate-950">{value}</p>
              </div>
            ))}
          </div>
        </section>

        <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-rose-50 text-rose-700">
              <Flame className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-500">이번 주 인기 주제</p>
              <h2 className="text-lg font-bold text-slate-950">실시간 질문 TOP 4</h2>
            </div>
          </div>
          <div className="mt-5 space-y-2">
            {weeklyTopics.map((topic, index) => (
              <button
                key={topic}
                type="button"
                className="flex w-full items-center gap-3 rounded-lg bg-slate-50 px-3 py-3 text-left transition hover:bg-blue-50"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-white text-sm font-bold text-blue-700">
                  {index + 1}
                </span>
                <span className="text-sm font-semibold text-slate-700">{topic}</span>
              </button>
            ))}
          </div>
        </aside>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <section className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative w-full max-w-md">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  placeholder="단지명, 지역, 키워드 검색"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {categories.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setCategory(item)}
                    className={`h-9 rounded-lg border px-3 text-sm font-semibold transition ${
                      category === item
                        ? "border-blue-600 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {posts.map((post) => (
            <article key={post.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-200">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                      {post.category}
                    </span>
                    <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                      {post.district}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">{post.createdAt}</span>
                  </div>
                  <h2 className="mt-3 text-xl font-bold text-slate-950">{post.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{post.summary}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {post.tags.map((tag) => (
                      <span key={tag} className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-3 text-sm text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <Heart className="h-4 w-4 text-rose-500" />
                    {post.likes}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MessageSquare className="h-4 w-4 text-blue-600" />
                    {post.replies}
                  </span>
                </div>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
                    {post.author.slice(0, 1)}
                  </div>
                  <span className="text-sm font-semibold text-slate-700">{post.author}</span>
                </div>
                <button className="text-sm font-bold text-blue-700 transition hover:text-blue-800">자세히 보기</button>
              </div>
            </article>
          ))}
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-24">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <UsersRound className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-950">내 주변 커뮤니티</h2>
                <p className="text-sm text-slate-500">{profile.region}</p>
              </div>
            </div>
            <div className="space-y-3">
              {subscriptions.slice(0, 3).map((item) => (
                <div key={item.id} className="rounded-lg bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-950">{item.district}</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-blue-700">
                      {item.matchScore}%
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{item.name}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <h2 className="font-bold text-slate-950">커뮤니티 운영 기준</h2>
            </div>
            <p className="text-sm leading-6 text-slate-600">
              개인정보, 허위 경쟁률, 특정 단지 비방 글은 자동 숨김 처리됩니다. 실제 신청 전에는 반드시 공고문을 확인하세요.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
