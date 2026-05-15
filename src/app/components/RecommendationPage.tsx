import { useState } from "react";
import { Link } from "react-router";
import {
  ArrowUpDown,
  Bookmark,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Filter,
  MapPin,
  ShieldAlert,
  Sparkles,
  TrainFront,
  TrendingUp,
} from "lucide-react";
import { profile, subscriptions } from "../data/cheongyak";

const filters = ["전체", "민영", "공공분양", "신혼 특공"];

function getScoreColor(score: number) {
  if (score >= 92) return "bg-blue-600";
  if (score >= 86) return "bg-emerald-500";
  return "bg-amber-500";
}

export function RecommendationPage() {
  const [activeFilter, setActiveFilter] = useState("전체");
  const visibleSubscriptions =
    activeFilter === "전체"
      ? subscriptions
      : subscriptions.filter((item) => item.supplyType === activeFilter || item.tags.includes(activeFilter));

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-700">추천 청약</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">조건 기반 매칭 결과</h1>
          <p className="mt-2 text-sm text-slate-500">
            {profile.region} · {profile.budget} · {profile.household}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter(filter)}
              className={`h-10 rounded-lg border px-4 text-sm font-semibold transition ${
                activeFilter === filter
                  ? "border-blue-600 bg-blue-50 text-blue-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <section className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold text-slate-950">{visibleSubscriptions.length}개 청약이 조건에 맞습니다</p>
                <p className="text-sm text-slate-500">매칭률, 마감일, 예산 적합도 반영</p>
              </div>
            </div>
            <button className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
              <ArrowUpDown className="h-4 w-4" />
              매칭률순
            </button>
          </div>

          {visibleSubscriptions.map((item, index) => (
            <article key={item.id} className="rounded-lg border border-slate-200 bg-white shadow-sm">
              <div className="grid gap-5 p-5 lg:grid-cols-[1fr_220px]">
                <div>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                          추천 {index + 1}
                        </span>
                        <span className="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
                          {item.supplyType}
                        </span>
                        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                          {item.housingType}
                        </span>
                      </div>
                      <h2 className="mt-3 text-xl font-bold text-slate-950">{item.name}</h2>
                      <p className="mt-2 flex items-center gap-1 text-sm text-slate-500">
                        <MapPin className="h-4 w-4" />
                        {item.address}
                      </p>
                    </div>
                    <button className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-blue-700">
                      <Bookmark className="h-5 w-5" />
                    </button>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                      ["분양가", item.price],
                      ["면적", item.area],
                      ["경쟁률", item.competition],
                      ["입주", item.moveIn],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg bg-slate-50 p-3">
                        <p className="text-xs font-semibold text-slate-500">{label}</p>
                        <p className="mt-1 font-bold text-slate-950">{value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 grid gap-4 lg:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm font-semibold text-slate-700">추천 근거</p>
                      <div className="space-y-2">
                        {item.strengths.map((strength) => (
                          <div key={strength} className="flex items-start gap-2 text-sm text-slate-600">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                            <span>{strength}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-sm font-semibold text-slate-700">확인 사항</p>
                      <div className="space-y-2">
                        {item.cautions.map((caution) => (
                          <div key={caution} className="flex items-start gap-2 text-sm text-slate-600">
                            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                            <span>{caution}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <span key={tag} className="rounded-md border border-slate-200 bg-white px-3 py-1 text-sm text-slate-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-500">매칭률</p>
                    <p className="text-2xl font-bold text-slate-950">{item.matchScore}%</p>
                  </div>
                  <div className="mt-3 h-3 overflow-hidden rounded-full bg-white">
                    <div className={`h-full rounded-full ${getScoreColor(item.matchScore)}`} style={{ width: `${item.matchScore}%` }} />
                  </div>

                  <div className="mt-5 space-y-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-slate-500">
                        <CalendarDays className="h-4 w-4" />
                        접수 마감
                      </span>
                      <span className="font-bold text-slate-950">{item.deadline}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-slate-500">
                        <Clock3 className="h-4 w-4" />
                        발표일
                      </span>
                      <span className="font-bold text-slate-950">{item.winnerDate}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-slate-500">
                        <TrainFront className="h-4 w-4" />
                        출퇴근
                      </span>
                      <span className="font-bold text-slate-950">{item.commute}</span>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-2">
                    <Link
                      to="/map"
                      className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      지도에서 보기
                    </Link>
                    <Link
                      to="/confirmation"
                      className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
                    >
                      신청 확인
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-24">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-white">
                <Filter className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">추천 기준</h2>
                <p className="text-sm text-slate-500">현재 프로필 반영</p>
              </div>
            </div>

            <dl className="mt-5 space-y-3 text-sm">
              {[
                ["권역", profile.region],
                ["가구", profile.household],
                ["예산", profile.budget],
                ["자격 점수", `${profile.score}점`],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="font-bold text-slate-950">{value}</dd>
                </div>
              ))}
            </dl>

            <div className="mt-5 rounded-lg bg-blue-50 p-4 text-sm text-blue-800">
              <div className="mb-2 flex items-center gap-2 font-bold">
                <TrendingUp className="h-4 w-4" />
                경쟁률 예측
              </div>
              <p className="leading-6">
                서초와 송파는 마감 3일 전부터 접수량이 빠르게 증가하는 패턴입니다.
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
