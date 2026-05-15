import { useState } from "react";
import {
  ArrowRight,
  Calculator,
  CheckCircle2,
  Landmark,
  Percent,
  ShieldAlert,
  SlidersHorizontal,
  WalletCards,
} from "lucide-react";
import { financialProducts, profile, subscriptions } from "../data/cheongyak";

const categories = ["전체", "전세대출", "주택담보대출", "청약통장", "적금"];

function scoreColor(score: number) {
  if (score >= 92) return "bg-blue-600";
  if (score >= 86) return "bg-emerald-500";
  return "bg-amber-500";
}

export function FinancePage() {
  const [category, setCategory] = useState("전체");
  const products =
    category === "전체" ? financialProducts : financialProducts.filter((product) => product.category === category);
  const topSubscription = subscriptions[0];

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <div className="mb-6 grid gap-4 lg:grid-cols-[1fr_360px]">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-semibold text-blue-700">사용자맞춤 금융상품 추천</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">
                청약 일정에 맞춰 자금 계획까지 연결합니다
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                {profile.name}님의 예산, 가구 구성, 청약 마감일, 예상 계약금 흐름을 기준으로 금융상품을
                추천합니다.
              </p>
            </div>
            <div className="inline-flex w-fit items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-sm font-bold text-blue-700">
              <WalletCards className="h-4 w-4" />
              {financialProducts.length}개 상품 분석
            </div>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {[
              ["추천 청약", topSubscription.name],
              ["예상 계약금", topSubscription.deposit],
              ["예산 범위", profile.budget],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-1 font-bold text-slate-950">{value}</p>
              </div>
            ))}
          </div>
        </section>

        <aside className="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white/10">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-300">월 상환 여력</p>
              <p className="text-2xl font-bold">약 138만원</p>
            </div>
          </div>
          <div className="mt-5 space-y-3 text-sm">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-300">소득 대비 부담률</span>
              <span className="font-bold">27%</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-300">권장 비상금</span>
              <span className="font-bold">1,200만원</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">계약금 준비율</span>
              <span className="font-bold text-emerald-300">82%</span>
            </div>
          </div>
        </aside>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <section className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <SlidersHorizontal className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold text-slate-950">상품 유형 필터</p>
                <p className="text-sm text-slate-500">청약 단계별 필요한 상품만 보기</p>
              </div>
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

          {products.map((product) => (
            <article key={product.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="grid gap-5 lg:grid-cols-[1fr_220px]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                      {product.category}
                    </span>
                    <span className="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">
                      {product.matchScore}% 적합
                    </span>
                  </div>
                  <h2 className="mt-3 text-xl font-bold text-slate-950">{product.name}</h2>
                  <p className="mt-1 text-sm font-semibold text-slate-500">{product.provider}</p>

                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    {[
                      ["금리", product.rate, Percent],
                      ["한도", product.limit, Landmark],
                      ["기간", product.period, WalletCards],
                    ].map(([label, value, Icon]) => (
                      <div key={label as string} className="rounded-lg bg-slate-50 p-4">
                        <div className="mb-2 flex items-center gap-2 text-sm text-slate-500">
                          <Icon className="h-4 w-4" />
                          {label as string}
                        </div>
                        <p className="font-bold text-slate-950">{value as string}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-5 grid gap-4 lg:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm font-semibold text-slate-700">추천 이유</p>
                      <div className="space-y-2">
                        {product.reasons.map((reason) => (
                          <div key={reason} className="flex items-start gap-2 text-sm text-slate-600">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                            <span>{reason}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-sm font-semibold text-slate-700">주의 사항</p>
                      <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>{product.caution}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-500">적합도</p>
                    <p className="text-2xl font-bold text-slate-950">{product.matchScore}%</p>
                  </div>
                  <div className="mt-3 h-3 overflow-hidden rounded-full bg-white">
                    <div className={`h-full rounded-full ${scoreColor(product.matchScore)}`} style={{ width: `${product.matchScore}%` }} />
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {product.tags.map((tag) => (
                      <span key={tag} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <button className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700">
                    상세 조건 비교
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-24">
            <h2 className="font-bold text-slate-950">자금 플랜</h2>
            <div className="mt-4 space-y-3">
              {[
                ["계약금", "4,680만원", "82% 준비"],
                ["중도금", "2.8억", "대출 검토"],
                ["잔금", "1.3억", "입주 전 준비"],
              ].map(([label, amount, status]) => (
                <div key={label} className="rounded-lg bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500">{label}</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold text-blue-700">{status}</span>
                  </div>
                  <p className="mt-2 text-lg font-bold text-slate-950">{amount}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
