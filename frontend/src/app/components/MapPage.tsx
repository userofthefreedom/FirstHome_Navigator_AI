import { useState } from "react";
import { Layers, LocateFixed, MapPin, Navigation, Search, TrainFront, ZoomIn, ZoomOut } from "lucide-react";
import { subscriptions } from "../data/cheongyak";

export function MapPage() {
  const [selectedId, setSelectedId] = useState(subscriptions[0].id);
  const selected = subscriptions.find((item) => item.id === selectedId) ?? subscriptions[0];

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-slate-100">
      <div className="absolute inset-x-0 top-0 z-20 border-b border-slate-200 bg-white/95 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-700">지도 탐색</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-950">지역 기반 청약 현황</h1>
          </div>
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              placeholder="지역, 지하철역, 단지명 검색"
            />
          </div>
        </div>
      </div>

      <aside className="absolute left-4 top-32 z-20 hidden w-80 space-y-3 lg:block">
        {subscriptions.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSelectedId(item.id)}
            className={`w-full rounded-lg border bg-white p-4 text-left shadow-sm transition ${
              selectedId === item.id ? "border-blue-500 ring-4 ring-blue-100" : "border-slate-200 hover:bg-slate-50"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-slate-950">{item.name}</p>
                <p className="mt-1 flex items-center gap-1 text-sm text-slate-500">
                  <MapPin className="h-4 w-4" />
                  {item.district}
                </p>
              </div>
              <span className="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                {item.matchScore}%
              </span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-lg bg-slate-50 p-2">
                <p className="text-slate-500">분양가</p>
                <p className="font-semibold text-slate-950">{item.price}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-2">
                <p className="text-slate-500">마감</p>
                <p className="font-semibold text-slate-950">{item.deadline}</p>
              </div>
            </div>
          </button>
        ))}
      </aside>

      <div className="absolute right-4 top-32 z-20 flex flex-col gap-2">
        {[
          { icon: Layers, label: "레이어" },
          { icon: LocateFixed, label: "현재 위치" },
          { icon: ZoomIn, label: "확대" },
          { icon: ZoomOut, label: "축소" },
        ].map((control) => {
          const Icon = control.icon;

          return (
            <button
              key={control.label}
              type="button"
              title={control.label}
              aria-label={control.label}
              className="flex h-11 w-11 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50"
            >
              <Icon className="h-5 w-5" />
            </button>
          );
        })}
      </div>

      <div className="absolute inset-0 pt-28">
        <div className="relative h-full w-full overflow-hidden bg-[#e9eef0]">
          <div className="absolute inset-0 opacity-70 [background-image:linear-gradient(#cbd5e1_1px,transparent_1px),linear-gradient(90deg,#cbd5e1_1px,transparent_1px)] [background-size:56px_56px]" />

          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1200 760" preserveAspectRatio="none">
            <path d="M0 210 C160 230 220 170 360 190 C520 215 590 300 760 285 C940 268 1020 180 1200 205" fill="none" stroke="#94a3b8" strokeWidth="18" strokeLinecap="round" opacity="0.7" />
            <path d="M100 620 C250 520 380 520 520 460 C680 390 740 280 880 220 C1010 164 1100 150 1200 118" fill="none" stroke="#94a3b8" strokeWidth="16" strokeLinecap="round" opacity="0.55" />
            <path d="M620 0 C610 160 650 260 620 390 C590 520 510 610 500 760" fill="none" stroke="#f59e0b" strokeWidth="8" strokeLinecap="round" opacity="0.75" />
            <path d="M0 470 C210 430 360 420 530 450 C730 486 900 560 1200 535" fill="none" stroke="#2563eb" strokeWidth="7" strokeLinecap="round" opacity="0.7" />
            <path d="M140 0 C170 100 220 210 330 300 C450 398 470 500 430 760" fill="none" stroke="#10b981" strokeWidth="7" strokeLinecap="round" opacity="0.7" />

            {[
              { x: 535, y: 318, label: "강남" },
              { x: 780, y: 360, label: "송파" },
              { x: 625, y: 525, label: "판교" },
              { x: 360, y: 292, label: "마곡" },
            ].map((zone) => (
              <g key={zone.label}>
                <rect x={zone.x - 34} y={zone.y - 18} width="68" height="36" rx="8" fill="white" opacity="0.85" />
                <text x={zone.x} y={zone.y + 5} textAnchor="middle" fontSize="16" fontWeight="700" fill="#334155">
                  {zone.label}
                </text>
              </g>
            ))}
          </svg>

          {subscriptions.map((item) => {
            const isSelected = selectedId === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                style={{ top: item.position.top, left: item.position.left }}
                className="group absolute z-10 -translate-x-1/2 -translate-y-1/2"
              >
                <span
                  className={`flex h-12 w-12 items-center justify-center rounded-lg border-2 bg-white shadow-lg transition ${
                    isSelected ? "border-blue-600 text-blue-700" : "border-white text-rose-600 hover:border-blue-200"
                  }`}
                >
                  <MapPin className="h-6 w-6" fill="currentColor" />
                </span>
                <span
                  className={`absolute left-1/2 top-14 min-w-44 -translate-x-1/2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left shadow-lg transition ${
                    isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                  }`}
                >
                  <span className="block text-sm font-bold text-slate-950">{item.name}</span>
                  <span className="mt-1 block text-xs text-slate-500">{item.district}</span>
                </span>
              </button>
            );
          })}

          <div className="absolute bottom-4 left-4 right-4 z-20 rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:left-auto lg:w-[420px]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-blue-700">선택 단지</p>
                <h2 className="mt-1 text-lg font-bold text-slate-950">{selected.name}</h2>
                <p className="mt-1 text-sm text-slate-500">{selected.address}</p>
              </div>
              <span className="rounded-md bg-blue-50 px-2 py-1 text-sm font-bold text-blue-700">
                {selected.matchScore}%
              </span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-slate-500">분양가</p>
                <p className="mt-1 font-bold text-slate-950">{selected.price}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-slate-500">면적</p>
                <p className="mt-1 font-bold text-slate-950">{selected.area}</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-slate-500">마감</p>
                <p className="mt-1 font-bold text-slate-950">{selected.deadline}</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
              <TrainFront className="h-4 w-4 text-blue-700" />
              {selected.commute}
            </div>
          </div>

          <div className="absolute bottom-4 left-1/2 z-20 hidden -translate-x-1/2 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm md:flex">
            <Navigation className="h-4 w-4 text-blue-700" />
            {subscriptions.length}개 청약 위치 표시
          </div>
        </div>
      </div>
    </div>
  );
}
