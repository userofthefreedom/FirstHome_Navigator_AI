import { NavLink, Outlet } from "react-router";
import {
  Bell,
  ClipboardList,
  Landmark,
  Home,
  LayoutDashboard,
  Map,
  Search,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { profile } from "../data/cheongyak";
import { FloatingChat } from "./FloatingChat";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "대시보드", end: true },
  { path: "/condition", icon: ClipboardList, label: "조건 입력" },
  { path: "/recommendation", icon: Sparkles, label: "추천 청약" },
  { path: "/finance", icon: Landmark, label: "금융 추천" },
  { path: "/community", icon: UsersRound, label: "커뮤니티" },
  { path: "/map", icon: Map, label: "지도 탐색" },
];

export function RootLayout() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#f5f7fb] text-slate-950 lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="hidden bg-slate-950 text-white lg:block">
        <div className="sticky top-0 flex h-screen flex-col">
          <div className="border-b border-white/10 px-6 py-5">
            <NavLink to="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500 text-white shadow-lg shadow-blue-500/25">
                <Home className="h-5 w-5" />
              </div>
              <div>
                <p className="text-lg font-semibold tracking-normal text-white">청약내비</p>
                <p className="text-xs text-slate-400">CheongYak Navi</p>
              </div>
            </NavLink>
          </div>

          <nav className="flex-1 space-y-1 px-3 py-4">
            {navItems.map((item) => {
              const Icon = item.icon;

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                      isActive
                        ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                        : "text-slate-300 hover:bg-white/10 hover:text-white",
                    ].join(" ")
                  }
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>

          <div className="border-t border-white/10 p-4">
            <div className="rounded-lg border border-white/10 bg-white/[0.06] p-3">
              <p className="text-xs font-medium text-slate-400">내 청약 프로필</p>
              <div className="mt-3 flex items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">{profile.name}</p>
                  <p className="text-xs text-slate-400">{profile.region}</p>
                </div>
                <span className="rounded-md bg-emerald-400/15 px-2 py-1 text-xs font-semibold text-emerald-300">
                  {profile.score}점
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <NavLink to="/" className="flex items-center gap-2 lg:hidden">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/20">
                <Home className="h-4 w-4" />
              </div>
              <span className="font-semibold">청약내비</span>
            </NavLink>

            <div className="relative ml-auto hidden w-full max-w-lg md:block lg:ml-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50/80 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
                placeholder="단지명, 지역, 금융상품, 커뮤니티 검색"
                type="search"
              />
            </div>

            <div className="ml-auto flex items-center gap-2">
              <button className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50">
                <Bell className="h-4 w-4" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500" />
              </button>
              <div className="hidden items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white">
                  싸
                </div>
                <div>
                  <p className="text-sm font-semibold">{profile.name}</p>
                  <p className="text-xs text-slate-500">{profile.household}</p>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 pb-20 lg:pb-0">
          <Outlet />
        </main>
        <FloatingChat />

        <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white lg:hidden">
          <div className="grid grid-cols-6">
            {navItems.map((item) => {
              const Icon = item.icon;

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      "flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition",
                      isActive ? "text-blue-700" : "text-slate-500",
                    ].join(" ")
                  }
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
