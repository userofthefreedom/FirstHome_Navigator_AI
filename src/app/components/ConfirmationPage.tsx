import { useState } from "react";
import { useNavigate } from "react-router";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  FileCheck2,
  Home,
  UserRound,
} from "lucide-react";
import { documents, profile, subscriptions } from "../data/cheongyak";

export function ConfirmationPage() {
  const navigate = useNavigate();
  const [agreed, setAgreed] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const item = subscriptions[0];

  const handleSubmit = () => {
    const application = {
      subscriptionId: item.id,
      receiptNo: "CY-20260515-0012",
      submittedAt: "2026-05-15 14:30",
      status: "APPLIED",
    };

    window.localStorage.setItem("cheongyak:application", JSON.stringify(application));
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-4xl items-center justify-center p-4 sm:p-6">
        <section className="w-full rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm sm:p-8">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
            <CheckCircle2 className="h-9 w-9" />
          </div>
          <h1 className="mt-5 text-2xl font-bold text-slate-950">신청 확인이 완료되었습니다</h1>
          <p className="mt-2 text-sm text-slate-500">접수 관리 번호 CY-20260515-0012</p>

          <div className="mx-auto mt-6 grid max-w-2xl gap-3 text-left sm:grid-cols-3">
            {[
              ["신청 단지", item.name],
              ["접수 마감", item.deadline],
              ["당첨 발표", item.winnerDate],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-1 font-bold text-slate-950">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="inline-flex h-11 items-center justify-center rounded-lg bg-blue-600 px-5 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              대시보드로 이동
            </button>
            <button
              type="button"
              onClick={() => navigate("/recommendation")}
              className="inline-flex h-11 items-center justify-center rounded-lg border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              다른 청약 보기
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="mb-5 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-slate-950"
      >
        <ArrowLeft className="h-4 w-4" />
        이전 화면
      </button>

      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-700">신청 확인</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">청약 신청 전 최종 검토</h1>
          <p className="mt-2 text-sm text-slate-500">2026년 5월 15일 14:30 저장본</p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm font-bold text-amber-700">
          <AlertTriangle className="h-4 w-4" />
          접수 마감 {item.deadline}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <section className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <Home className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">청약 정보</h2>
                <p className="text-sm text-slate-500">{item.name}</p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["위치", item.district],
                ["공급 유형", item.supplyType],
                ["전용면적", item.area],
                ["분양가", item.price],
                ["계약금", item.deposit],
                ["경쟁률", item.competition],
                ["입주 예정", item.moveIn],
                ["매칭률", `${item.matchScore}%`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="mt-1 font-bold text-slate-950">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <UserRound className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">신청자 정보</h2>
                <p className="text-sm text-slate-500">{profile.name}</p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["이름", profile.name],
                ["가구 구성", profile.household],
                ["희망 지역", profile.region],
                ["청약통장", profile.subscriptionAccount],
                ["예산", profile.budget],
                ["자격 점수", `${profile.score}점`],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-500">{label}</span>
                  <span className="font-bold text-slate-950">{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-50 text-rose-700">
                <CalendarDays className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">일정</h2>
                <p className="text-sm text-slate-500">접수 이후 주요 날짜</p>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {[
                ["접수 마감", item.deadline, "amber"],
                ["당첨 발표", item.winnerDate, "emerald"],
                ["입주 예정", item.moveIn, "blue"],
              ].map(([label, value, tone]) => (
                <div key={label} className="rounded-lg border border-slate-200 p-4">
                  <span
                    className={`rounded-md px-2 py-1 text-xs font-bold ${
                      tone === "amber"
                        ? "bg-amber-50 text-amber-700"
                        : tone === "emerald"
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-blue-50 text-blue-700"
                    }`}
                  >
                    {label}
                  </span>
                  <p className="mt-4 text-lg font-bold text-slate-950">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-24">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <FileCheck2 className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">서류 체크</h2>
                <p className="text-sm text-slate-500">필수 {documents.length}종</p>
              </div>
            </div>

            <div className="space-y-2">
              {documents.map((document) => (
                <div key={document} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-3 text-sm">
                  <span className="font-semibold text-slate-700">{document}</span>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                </div>
              ))}
            </div>

            <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-4">
              <input
                checked={agreed}
                onChange={(event) => setAgreed(event.target.checked)}
                type="checkbox"
                className="mt-1 h-4 w-4 accent-blue-600"
              />
              <span className="text-sm leading-6 text-slate-600">
                신청 정보와 제출 서류 기준일을 확인했으며 개인정보 활용에 동의합니다.
              </span>
            </label>

            <button
              type="button"
              disabled={!agreed}
              onClick={handleSubmit}
              className="mt-4 inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              <ClipboardCheck className="h-4 w-4" />
              신청 확인 완료
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}
