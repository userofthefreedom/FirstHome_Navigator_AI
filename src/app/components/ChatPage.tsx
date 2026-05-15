import { useState } from "react";
import { Bot, FileText, Lightbulb, Send, Sparkles, UserRound } from "lucide-react";
import { documents, profile, subscriptions } from "../data/cheongyak";

type Message = {
  id: number;
  text: string;
  sender: "user" | "ai";
  time: string;
};

const initialMessages: Message[] = [
  {
    id: 1,
    sender: "ai",
    time: "14:20",
    text: "서초 센트럴 라움은 현재 프로필 기준 매칭률 96%입니다. 무주택 기간과 청약통장 가입 기간이 강점으로 계산됐습니다.",
  },
  {
    id: 2,
    sender: "user",
    time: "14:21",
    text: "송파 레이크 포레랑 비교하면 뭐가 더 유리해?",
  },
  {
    id: 3,
    sender: "ai",
    time: "14:21",
    text: "서초는 매칭률과 출퇴근 조건이 더 좋고, 송파는 공공분양과 신혼 특공 조건에서 안정적입니다. 당첨 가능성만 보면 서초, 자금 부담까지 보면 송파가 더 균형 잡혀 있습니다.",
  },
];

const quickQuestions = [
  "1순위 자격 조건 확인해줘",
  "서류 누락 위험 알려줘",
  "예산 초과 가능성 비교해줘",
  "마감 임박 청약만 정리해줘",
];

function createAiReply(question: string) {
  if (question.includes("서류")) {
    return "현재 체크리스트 기준 필수 서류는 모두 준비된 상태입니다. 다만 주민등록등본은 공고일 이후 발급본인지 확인해야 합니다.";
  }
  if (question.includes("예산")) {
    return "서초 센트럴 라움은 예산 상단에 가깝고, 송파 레이크 포레는 계약금 부담이 낮습니다. 중도금 대출 조건까지 보면 송파 쪽 리스크가 더 작습니다.";
  }
  if (question.includes("마감")) {
    return "가장 가까운 마감은 서초 센트럴 라움 2026-05-23, 송파 레이크 포레 2026-05-28입니다.";
  }
  return "현재 프로필은 무주택, 청약통장 8년 4개월, 3인 가구로 계산되어 1순위 검토 대상입니다. 세부 가점은 공고별 기준에 따라 달라질 수 있습니다.";
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState("");

  const sendMessage = (value = inputValue) => {
    const text = value.trim();
    if (!text) return;

    const now = new Date().toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });

    const userMessage: Message = {
      id: Date.now(),
      sender: "user",
      text,
      time: now,
    };

    const aiMessage: Message = {
      id: Date.now() + 1,
      sender: "ai",
      text: createAiReply(text),
      time: now,
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);
    setInputValue("");
  };

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col">
      <div className="border-b border-slate-200 bg-white px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-700">AI 상담</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">청약 상담 워크스페이스</h1>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
            <Sparkles className="h-4 w-4 text-blue-700" />
            {profile.name} 프로필 연결됨
          </div>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-7xl flex-1 gap-5 p-4 sm:p-6 xl:grid-cols-[260px_1fr_320px]">
        <aside className="hidden space-y-5 xl:block">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="font-bold text-slate-950">빠른 질문</h2>
            <div className="mt-4 space-y-2">
              {quickQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => sendMessage(question)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-600" />
              <h2 className="font-bold text-slate-950">상담 포인트</h2>
            </div>
            <div className="space-y-3 text-sm text-slate-600">
              <p>공급 유형별 1순위 조건</p>
              <p>분양가와 계약금 부담</p>
              <p>서류 발급 기준일</p>
            </div>
          </div>
        </aside>

        <section className="flex min-h-[620px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-950">청약내비 AI</h2>
                <p className="text-sm text-slate-500">공고, 자격, 서류 기준 상담</p>
              </div>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-auto bg-slate-50 p-4 sm:p-6">
            {messages.map((message) => {
              const isUser = message.sender === "user";

              return (
                <div key={message.id} className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}
                  <div
                    className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 shadow-sm ${
                      isUser
                        ? "bg-slate-950 text-white"
                        : "border border-slate-200 bg-white text-slate-700"
                    }`}
                  >
                    <p>{message.text}</p>
                    <p className={`mt-2 text-xs ${isUser ? "text-slate-300" : "text-slate-400"}`}>{message.time}</p>
                  </div>
                  {isUser && (
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700">
                      <UserRound className="h-4 w-4" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="border-t border-slate-200 bg-white p-4">
            <div className="flex gap-2">
              <input
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    sendMessage();
                  }
                }}
                className="h-11 flex-1 rounded-lg border border-slate-200 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                placeholder="청약 조건, 서류, 일정 질문"
              />
              <button
                type="button"
                onClick={() => sendMessage()}
                disabled={!inputValue.trim()}
                className="inline-flex h-11 w-12 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-bold text-slate-950">상담 컨텍스트</h2>
            <div className="mt-4 space-y-3">
              {subscriptions.slice(0, 2).map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold text-slate-950">{item.name}</p>
                    <span className="text-sm font-bold text-blue-700">{item.matchScore}%</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{item.deadline} 마감</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-700" />
              <h2 className="font-bold text-slate-950">필수 서류</h2>
            </div>
            <div className="space-y-2">
              {documents.slice(0, 4).map((document) => (
                <div key={document} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="text-slate-700">{document}</span>
                  <span className="font-semibold text-emerald-700">완료</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
