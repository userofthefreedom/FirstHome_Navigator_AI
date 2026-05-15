import { useMemo, useState } from "react";
import { Link } from "react-router";
import {
  ArrowRight,
  Banknote,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileCheck2,
  Landmark,
  MapPin,
  ReceiptText,
  ShieldAlert,
  Sparkles,
  Trophy,
  WalletCards,
} from "lucide-react";
import { documents, profile, subscriptions } from "../data/cheongyak";

type ApplicationState = {
  subscriptionId: number;
  receiptNo: string;
  submittedAt: string;
  status: "APPLIED";
};

const APPLICATION_KEY = "cheongyak:application";
const weekDays = ["일", "월", "화", "수", "목", "금", "토"];
const calendarSlots = Array.from({ length: 42 }, (_, index) => {
  const day = index - 4;
  return day >= 1 && day <= 31 ? day : null;
});

function readApplication() {
  try {
    const raw = window.localStorage.getItem(APPLICATION_KEY);
    return raw ? (JSON.parse(raw) as ApplicationState) : null;
  } catch {
    return null;
  }
}

function getRankTone(rank: number) {
  if (rank === 1) return "bg-blue-600 text-white";
  if (rank === 2) return "bg-emerald-500 text-white";
  if (rank === 3) return "bg-amber-500 text-white";
  return "bg-slate-200 text-slate-700";
}

function getPreApplyTasks(selected: (typeof subscriptions)[number]) {
  return [
    {
      title: "청약 자격과 예치금 확인",
      date: "오늘",
      status: "진행",
      description: `${selected.supplyType} 1순위 조건, 지역별 예치금, 무주택 기준을 다시 점검합니다.`,
    },
    {
      title: "필수 서류 발급 기준 확인",
      date: "D-7",
      status: "준비",
      description: `${documents.slice(0, 3).join(", ")}가 공고일 이후 발급본인지 확인합니다.`,
    },
    {
      title: "청약 접수 완료",
      date: selected.deadline,
      status: "마감",
      description: "신청 타입, 선택 주택형, 접수번호를 저장하고 캡처본을 보관합니다.",
    },
    {
      title: "당첨자 발표 알림 설정",
      date: selected.winnerDate,
      status: "예정",
      description: "발표 당일 확인 후 계약금 납부와 계약 일정으로 플랜을 전환합니다.",
    },
  ];
}

function getPostApplyPlan(selected: (typeof subscriptions)[number]) {
  return [
    {
      phase: "접수 완료",
      date: "2026-05-15",
      amount: "-",
      status: "완료",
      owner: "신청자",
      description: "접수번호와 신청 주택형을 저장했습니다. 마감 전까지 수정 가능 여부만 확인합니다.",
    },
    {
      phase: "당첨자 발표 확인",
      date: selected.winnerDate,
      amount: "-",
      status: "대기",
      owner: "신청자",
      description: "당첨 여부, 예비번호, 서류 제출 대상 여부를 확인합니다.",
    },
    {
      phase: "계약금 납부",
      date: "2026-06-10 ~ 06-15",
      amount: "약 4,680만원",
      status: "예정",
      owner: "자금",
      description: "분양가 10% 기준 계약금 납부와 계약서 작성이 필요합니다.",
    },
    {
      phase: "중도금 대출 사전심사",
      date: "2026-07-01",
      amount: "한도 약 2.8억",
      status: "예정",
      owner: "금융",
      description: "소득, DSR, 기존 대출을 기준으로 중도금 대출 가능 한도를 확인합니다.",
    },
    {
      phase: "중도금 1차",
      date: "2026-10-15",
      amount: "약 7,020만원",
      status: "예정",
      owner: "금융",
      description: "대출 실행 조건과 이자 납입 방식을 확정합니다.",
    },
    {
      phase: "중도금 2차",
      date: "2027-02-15",
      amount: "약 7,020만원",
      status: "예정",
      owner: "금융",
      description: "금리 변동과 상환 여력을 재점검합니다.",
    },
    {
      phase: "중도금 3차",
      date: "2027-06-15",
      amount: "약 7,020만원",
      status: "예정",
      owner: "금융",
      description: "잔금 대출 전환 가능성과 추가 현금 필요액을 계산합니다.",
    },
    {
      phase: "잔금 및 입주",
      date: selected.moveIn,
      amount: "잔금 약 1.8억",
      status: "예정",
      owner: "입주",
      description: "주택담보대출 실행, 등기, 입주 예약을 한 번에 관리합니다.",
    },
  ];
}

function statusClass(status: string) {
  if (status === "완료") return "bg-emerald-50 text-emerald-700";
  if (status === "대기" || status === "진행") return "bg-blue-50 text-blue-700";
  if (status === "마감") return "bg-amber-50 text-amber-700";
  return "bg-slate-100 text-slate-600";
}

export function HomePage() {
  const [application] = useState<ApplicationState | null>(() => readApplication());
  const [selectedId, setSelectedId] = useState(() => application?.subscriptionId ?? subscriptions[0].id);
  const isApplied = Boolean(application);
  const activeId = application?.subscriptionId ?? selectedId;
  const selected = subscriptions.find((item) => item.id === activeId) ?? subscriptions[0];
  const preApplyTasks = getPreApplyTasks(selected);
  const postApplyPlan = getPostApplyPlan(selected);

  const eventsByDay = useMemo(() => {
    return subscriptions.reduce<Record<number, Array<{ id: number; label: string; type: "deadline" | "selected" }>>>(
      (acc, item) => {
        const day = Number(item.deadline.split("-")[2]);
        acc[day] = [
          ...(acc[day] ?? []),
          {
            id: item.id,
            label: item.name,
            type: item.id === activeId ? "selected" : "deadline",
          },
        ];
        return acc;
      },
      {},
    );
  }, [activeId]);

  const completedPlanCount = postApplyPlan.filter((item) => item.status === "완료").length;

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 p-4 sm:p-6">
      <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="mb-4 inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
                <Sparkles className="h-4 w-4" />
                {isApplied ? "신청 완료 대시보드" : "청약 홈 대시보드"}
              </div>
              <h1 className="max-w-3xl break-words text-2xl font-bold leading-tight text-slate-950 [overflow-wrap:anywhere] sm:text-3xl">
                {isApplied
                  ? `${selected.name} 신청 이후 납부와 계약 일정을 관리합니다`
                  : `${profile.name}님의 추천 청약 순위와 접수 일정을 한눈에 관리합니다`}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                {isApplied
                  ? "접수 완료 이후에는 당첨 발표, 계약금, 중도금 대출, 잔금까지 이어지는 실행 계획을 중심으로 보여줍니다."
                  : "원하는 청약을 선택하면 해당 단지의 요약, 리스크, 접수 전 해야 할 일을 바로 확인할 수 있습니다."}
              </p>
            </div>
            <Link
              to={isApplied ? "/confirmation" : "/condition"}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800"
            >
              {isApplied ? "신청 내역 보기" : "조건 수정"}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-4">
            {(isApplied
              ? [
                  ["진행 상태", "접수 완료"],
                  ["접수 번호", application?.receiptNo ?? "-"],
                  ["다음 일정", selected.winnerDate],
                  ["완료 단계", `${completedPlanCount}/${postApplyPlan.length}`],
                ]
              : [
                  ["추천 청약", `${subscriptions.length}건`],
                  ["최고 매칭률", `${subscriptions[0].matchScore}%`],
                  ["가장 빠른 마감", subscriptions[0].deadline],
                  ["자격 점수", `${profile.score}점`],
                ]
            ).map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-500">{label}</p>
                <p className="mt-2 text-xl font-bold text-slate-950">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-300">
                {isApplied ? "내 신청 청약" : "현재 선택 청약"}
              </p>
              <h2 className="mt-1 text-2xl font-bold">{selected.name}</h2>
              <p className="mt-2 text-sm text-slate-300">{selected.district}</p>
            </div>
            <span className="rounded-md bg-blue-500 px-2.5 py-1 text-sm font-bold text-white">
              {selected.matchScore}%
            </span>
          </div>
          <div className="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-emerald-400" style={{ width: `${selected.matchScore}%` }} />
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-white/10 p-3">
              <p className="text-slate-300">분양가</p>
              <p className="mt-1 font-bold text-white">{selected.price}</p>
            </div>
            <div className="rounded-lg bg-white/10 p-3">
              <p className="text-slate-300">당첨 발표</p>
              <p className="mt-1 font-bold text-white">{selected.winnerDate}</p>
            </div>
            <div className="rounded-lg bg-white/10 p-3">
              <p className="text-slate-300">계약금</p>
              <p className="mt-1 font-bold text-white">{selected.deposit}</p>
            </div>
            <div className="rounded-lg bg-white/10 p-3">
              <p className="text-slate-300">입주 예정</p>
              <p className="mt-1 font-bold text-white">{selected.moveIn}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-5">
            <div>
              <h2 className="text-lg font-bold text-slate-950">청약 순위 요약</h2>
              <p className="mt-1 text-sm text-slate-500">
                {isApplied ? "신청한 청약을 기준으로 고정 표시됩니다" : "청약을 선택하면 오른쪽 관리 화면이 바뀝니다"}
              </p>
            </div>
            <Trophy className="h-5 w-5 text-blue-600" />
          </div>
          <div className="divide-y divide-slate-100">
            {subscriptions.map((item, index) => {
              const rank = index + 1;
              const isSelected = item.id === activeId;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    if (!isApplied) setSelectedId(item.id);
                  }}
                  className={`grid w-full gap-4 p-5 text-left transition sm:grid-cols-[1fr_auto] ${
                    isSelected ? "bg-blue-50/80" : isApplied ? "opacity-65" : "hover:bg-slate-50"
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-md px-2.5 py-1 text-xs font-bold ${getRankTone(rank)}`}>
                        {isSelected && isApplied ? "신청" : `${rank}순위`}
                      </span>
                      <h3 className="font-bold text-slate-950">{item.name}</h3>
                      <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                        {item.supplyType}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {item.district}
                      </span>
                      <span>{item.area}</span>
                      <span>{item.price}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm sm:w-52">
                    <div className="rounded-lg bg-white p-3">
                      <p className="text-slate-500">매칭률</p>
                      <p className="mt-1 font-bold text-blue-700">{item.matchScore}%</p>
                    </div>
                    <div className="rounded-lg bg-white p-3">
                      <p className="text-slate-500">마감</p>
                      <p className="mt-1 font-bold text-slate-950">{item.deadline}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-950">2026년 5월 청약 캘린더</h2>
              <p className="mt-1 text-sm text-slate-500">접수 마감일과 신청 상태를 함께 표시합니다</p>
            </div>
            <CalendarDays className="h-5 w-5 text-slate-400" />
          </div>

          <div className="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
            {weekDays.map((day) => (
              <div key={day}>{day}</div>
            ))}
          </div>
          <div className="mt-2 grid grid-cols-7 gap-2">
            {calendarSlots.map((day, index) => {
              const events = day ? eventsByDay[day] ?? [] : [];
              const isToday = day === 15;

              return (
                <div
                  key={`${day ?? "blank"}-${index}`}
                  className={`min-h-24 rounded-lg border p-2 ${
                    day ? "border-slate-200 bg-slate-50" : "border-transparent bg-transparent"
                  } ${isToday ? "ring-2 ring-blue-200" : ""}`}
                >
                  {day && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-bold ${isToday ? "text-blue-700" : "text-slate-700"}`}>
                          {day}
                        </span>
                        {isToday && (
                          <span className="rounded-md bg-blue-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                            오늘
                          </span>
                        )}
                      </div>
                      <div className="mt-2 space-y-1">
                        {events.map((event) => (
                          <button
                            key={`${event.id}-${event.label}`}
                            type="button"
                            onClick={() => {
                              if (!isApplied) setSelectedId(event.id);
                            }}
                            className={`w-full truncate rounded-md px-2 py-1 text-left text-[11px] font-bold ${
                              event.type === "selected"
                                ? isApplied
                                  ? "bg-emerald-600 text-white"
                                  : "bg-blue-600 text-white"
                                : "bg-amber-50 text-amber-700"
                            }`}
                          >
                            {event.type === "selected" && isApplied ? "신청 완료" : event.label}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {isApplied ? (
        <section className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">신청 청약 상세 요약</h2>
                <p className="mt-1 text-sm text-slate-500">접수번호 {application?.receiptNo}</p>
              </div>
              <ClipboardCheck className="h-5 w-5 text-emerald-600" />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["신청 단지", selected.name],
                ["접수 일시", application?.submittedAt ?? "-"],
                ["공급 유형", selected.supplyType],
                ["전용면적", selected.area],
                ["분양가", selected.price],
                ["계약금", selected.deposit],
                ["당첨 발표", selected.winnerDate],
                ["입주 예정", selected.moveIn],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="mt-1 font-bold text-slate-950">{value}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-lg border border-blue-100 bg-blue-50 p-4">
              <div className="flex items-start gap-3">
                <ReceiptText className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
                <div>
                  <p className="font-bold text-slate-950">다음 핵심 액션</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    당첨자 발표 전까지 서류 원본과 계약금 유동성을 준비하고, 발표 이후 바로 계약금 납부와
                    중도금 대출 사전심사로 넘어가야 합니다.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">계약·납부 실행 계획</h2>
                <p className="mt-1 text-sm text-slate-500">계약금, 중도금, 잔금까지 이어지는 관리표</p>
              </div>
              <WalletCards className="h-5 w-5 text-slate-400" />
            </div>

            <div className="overflow-hidden rounded-lg border border-slate-200">
              <div className="grid grid-cols-[1.2fr_1fr_1fr_0.8fr] bg-slate-50 px-4 py-3 text-xs font-bold text-slate-500">
                <span>단계</span>
                <span>일정</span>
                <span>금액/한도</span>
                <span>상태</span>
              </div>
              <div className="divide-y divide-slate-100">
                {postApplyPlan.map((plan) => (
                  <div key={plan.phase} className="grid gap-3 px-4 py-4 text-sm md:grid-cols-[1.2fr_1fr_1fr_0.8fr]">
                    <div>
                      <p className="font-bold text-slate-950">{plan.phase}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{plan.description}</p>
                    </div>
                    <div className="font-semibold text-slate-700">{plan.date}</div>
                    <div className="font-semibold text-slate-700">{plan.amount}</div>
                    <div>
                      <span className={`rounded-md px-2 py-1 text-xs font-bold ${statusClass(plan.status)}`}>
                        {plan.status}
                      </span>
                      <p className="mt-2 text-xs text-slate-500">{plan.owner}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {[
                ["계약금 준비", "4,680만원", CreditCard],
                ["중도금 대출", "사전심사 필요", Landmark],
                ["잔금 계획", "입주 전 확정", Banknote],
              ].map(([label, value, Icon]) => (
                <div key={label as string} className="rounded-lg bg-slate-50 p-4">
                  <Icon className="mb-3 h-5 w-5 text-blue-700" />
                  <p className="text-sm text-slate-500">{label as string}</p>
                  <p className="mt-1 font-bold text-slate-950">{value as string}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : (
        <section className="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">선택 청약 상세 요약</h2>
                <p className="mt-1 text-sm text-slate-500">{selected.name} 기준</p>
              </div>
              <Link
                to="/recommendation"
                className="inline-flex items-center gap-1 text-sm font-bold text-blue-700 hover:text-blue-800"
              >
                상세 비교
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["위치", selected.district],
                ["공급 유형", selected.supplyType],
                ["분양가", selected.price],
                ["전용면적", selected.area],
                ["경쟁률", selected.competition],
                ["입주 예정", selected.moveIn],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">{label}</p>
                  <p className="mt-1 font-bold text-slate-950">{value}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-bold text-slate-700">추천 근거</p>
                <div className="space-y-2">
                  {selected.strengths.map((strength) => (
                    <div key={strength} className="flex items-start gap-2 text-sm text-slate-600">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      <span>{strength}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-bold text-slate-700">주의 사항</p>
                <div className="space-y-2">
                  {selected.cautions.map((caution) => (
                    <div key={caution} className="flex items-start gap-2 text-sm text-slate-600">
                      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                      <span>{caution}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-950">접수 전 해야 할 일</h2>
                <p className="mt-1 text-sm text-slate-500">선택한 청약의 신청 준비 계획</p>
              </div>
              <ClipboardList className="h-5 w-5 text-slate-400" />
            </div>

            <div className="space-y-3">
              {preApplyTasks.map((plan, index) => (
                <div key={plan.title} className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[72px_1fr]">
                  <div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-sm font-bold text-blue-700">
                      {index + 1}
                    </div>
                    <p className="mt-2 text-xs font-bold text-slate-500">{plan.date}</p>
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-slate-950">{plan.title}</h3>
                      <span className={`rounded-md px-2 py-1 text-xs font-bold ${statusClass(plan.status)}`}>
                        {plan.status}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{plan.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-lg bg-blue-50 p-4">
              <div className="flex items-start gap-3">
                <FileCheck2 className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
                <div>
                  <p className="font-bold text-slate-950">신청 후에는 대시보드가 계약 관리 모드로 바뀝니다</p>
                  <p className="mt-1 text-sm text-slate-600">
                    신청 완료 후 계약금, 중도금 대출, 잔금 계획을 단계별로 보여줍니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
