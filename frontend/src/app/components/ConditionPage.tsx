import { useState } from "react";
import { useNavigate } from "react-router";
import {
  Banknote,
  Building2,
  CalendarDays,
  Check,
  MapPin,
  RotateCcw,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";

const regions = ["서울", "경기", "인천", "부산", "대전", "광주"];
const supplyTypes = ["민영", "공공분양", "신혼 특공", "생애최초", "다자녀"];
const houseTypes = ["아파트", "오피스텔", "도시형 생활주택"];
const ownershipTypes = ["무주택", "1주택 처분 예정", "세대원 주택 보유"];

export function ConditionPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    region: "서울",
    district: "강남, 송파, 서초",
    supplyType: "민영",
    houseType: "아파트",
    ownership: "무주택",
    minBudget: "30000",
    maxBudget: "48000",
    area: "84",
    household: "3",
    income: "7200",
    accountYears: "8",
    moveIn: "2028-02",
    commute: "30",
  });

  const setValue = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate("/recommendation");
  };

  const reset = () => {
    setFormData({
      region: "서울",
      district: "",
      supplyType: "민영",
      houseType: "아파트",
      ownership: "무주택",
      minBudget: "25000",
      maxBudget: "50000",
      area: "84",
      household: "2",
      income: "6500",
      accountYears: "5",
      moveIn: "2028-01",
      commute: "40",
    });
  };

  return (
    <div className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-700">조건 입력</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">청약 자격과 선호 조건</h1>
          <p className="mt-2 text-sm text-slate-500">2026년 5월 15일 기준 프로필</p>
        </div>
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          <RotateCcw className="h-4 w-4" />
          초기화
        </button>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <div className="space-y-5">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <MapPin className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">지역 조건</h2>
                <p className="text-sm text-slate-500">희망 권역과 세부 지역</p>
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">권역</label>
                <div className="grid grid-cols-3 gap-2">
                  {regions.map((region) => (
                    <button
                      key={region}
                      type="button"
                      onClick={() => setValue("region", region)}
                      className={`h-10 rounded-lg border text-sm font-semibold transition ${
                        formData.region === region
                          ? "border-blue-600 bg-blue-50 text-blue-700"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {region}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label htmlFor="district" className="mb-2 block text-sm font-semibold text-slate-700">
                  세부 지역
                </label>
                <input
                  id="district"
                  value={formData.district}
                  onChange={(event) => setValue("district", event.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  placeholder="예: 강남, 송파, 성남"
                />
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">공급 조건</h2>
                <p className="text-sm text-slate-500">공급 유형, 주택 유형, 면적</p>
              </div>
            </div>

            <div className="grid gap-5">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">공급 유형</label>
                <div className="flex flex-wrap gap-2">
                  {supplyTypes.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setValue("supplyType", type)}
                      className={`inline-flex h-10 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition ${
                        formData.supplyType === type
                          ? "border-emerald-600 bg-emerald-50 text-emerald-700"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {formData.supplyType === type && <Check className="h-4 w-4" />}
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <div>
                  <label htmlFor="houseType" className="mb-2 block text-sm font-semibold text-slate-700">
                    주택 유형
                  </label>
                  <select
                    id="houseType"
                    value={formData.houseType}
                    onChange={(event) => setValue("houseType", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  >
                    {houseTypes.map((type) => (
                      <option key={type}>{type}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="area" className="mb-2 block text-sm font-semibold text-slate-700">
                    전용면적
                  </label>
                  <div className="relative">
                    <input
                      id="area"
                      type="number"
                      value={formData.area}
                      onChange={(event) => setValue("area", event.target.value)}
                      className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-10 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">㎡</span>
                  </div>
                </div>
                <div>
                  <label htmlFor="moveIn" className="mb-2 block text-sm font-semibold text-slate-700">
                    입주 희망
                  </label>
                  <input
                    id="moveIn"
                    type="month"
                    value={formData.moveIn}
                    onChange={(event) => setValue("moveIn", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
                <Banknote className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">자금 조건</h2>
                <p className="text-sm text-slate-500">분양가, 소득, 출퇴근 허용 범위</p>
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <label htmlFor="minBudget" className="mb-2 block text-sm font-semibold text-slate-700">
                  최소 예산
                </label>
                <div className="relative">
                  <input
                    id="minBudget"
                    type="number"
                    value={formData.minBudget}
                    onChange={(event) => setValue("minBudget", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-12 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">만원</span>
                </div>
              </div>
              <div>
                <label htmlFor="maxBudget" className="mb-2 block text-sm font-semibold text-slate-700">
                  최대 예산
                </label>
                <div className="relative">
                  <input
                    id="maxBudget"
                    type="number"
                    value={formData.maxBudget}
                    onChange={(event) => setValue("maxBudget", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-12 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">만원</span>
                </div>
              </div>
              <div>
                <label htmlFor="income" className="mb-2 block text-sm font-semibold text-slate-700">
                  연소득
                </label>
                <div className="relative">
                  <input
                    id="income"
                    type="number"
                    value={formData.income}
                    onChange={(event) => setValue("income", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-12 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">만원</span>
                </div>
              </div>
              <div>
                <label htmlFor="commute" className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700">
                  출퇴근 허용 시간
                  <span className="text-blue-700">{formData.commute}분</span>
                </label>
                <input
                  id="commute"
                  type="range"
                  min="10"
                  max="90"
                  step="5"
                  value={formData.commute}
                  onChange={(event) => setValue("commute", event.target.value)}
                  className="h-11 w-full accent-blue-600"
                />
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-50 text-rose-700">
                <UserRound className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">가구와 자격</h2>
                <p className="text-sm text-slate-500">세대 구성, 주택 보유, 통장 기간</p>
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-3">
              <div>
                <label htmlFor="household" className="mb-2 block text-sm font-semibold text-slate-700">
                  가구원 수
                </label>
                <select
                  id="household"
                  value={formData.household}
                  onChange={(event) => setValue("household", event.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                >
                  {["1", "2", "3", "4", "5"].map((size) => (
                    <option key={size} value={size}>
                      {size}인
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="ownership" className="mb-2 block text-sm font-semibold text-slate-700">
                  주택 보유
                </label>
                <select
                  id="ownership"
                  value={formData.ownership}
                  onChange={(event) => setValue("ownership", event.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                >
                  {ownershipTypes.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="accountYears" className="mb-2 block text-sm font-semibold text-slate-700">
                  통장 가입 기간
                </label>
                <div className="relative">
                  <input
                    id="accountYears"
                    type="number"
                    value={formData.accountYears}
                    onChange={(event) => setValue("accountYears", event.target.value)}
                    className="h-11 w-full rounded-lg border border-slate-200 bg-white px-3 pr-8 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">년</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-24">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">입력 요약</h2>
                <p className="text-sm text-slate-500">{formData.region} 중심 추천</p>
              </div>
            </div>

            <dl className="mt-5 space-y-3 text-sm">
              {[
                ["지역", `${formData.region} ${formData.district}`],
                ["공급", `${formData.supplyType} · ${formData.houseType}`],
                ["예산", `${Number(formData.minBudget).toLocaleString()}~${Number(formData.maxBudget).toLocaleString()}만원`],
                ["자격", `${formData.household}인 · ${formData.ownership}`],
                ["면적", `${formData.area}㎡`],
              ].map(([label, value]) => (
                <div key={label} className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="text-right font-semibold text-slate-950">{value}</dd>
                </div>
              ))}
            </dl>

            <div className="mt-5 rounded-lg bg-slate-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
                <CalendarDays className="h-4 w-4" />
                다음 기준일
              </div>
              <p className="text-sm text-slate-500">청약홈 공고 반영</p>
              <p className="mt-1 font-bold text-slate-950">2026-05-16 09:00</p>
            </div>

            <button
              type="submit"
              className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              <Search className="h-4 w-4" />
              맞춤 청약 찾기
            </button>
          </div>
        </aside>
      </form>
    </div>
  );
}
