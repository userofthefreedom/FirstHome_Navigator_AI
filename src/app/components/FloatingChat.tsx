import { useState } from "react";
import { Bot, MessageCircle, Send, Sparkles, UserRound, X } from "lucide-react";
import { financialProducts, subscriptions } from "../data/cheongyak";

type FloatingMessage = {
  id: number;
  sender: "ai" | "user";
  text: string;
};

const starterMessages: FloatingMessage[] = [
  {
    id: 1,
    sender: "ai",
    text: "안녕하세요. 청약 조건, 금융상품, 서류 준비까지 바로 도와드릴게요.",
  },
];

const suggestions = ["내 추천 청약 요약", "계약금 준비 방법", "서류 체크", "커뮤니티 인기글"];

function getReply(text: string) {
  if (text.includes("계약금") || text.includes("금융")) {
    return `${financialProducts[0].name}이 가장 잘 맞습니다. 예상 한도는 ${financialProducts[0].limit}, 금리는 ${financialProducts[0].rate}부터예요.`;
  }
  if (text.includes("서류")) {
    return "현재 필수 서류 5종은 준비 완료 상태입니다. 공고일 이후 발급본인지 한 번 더 확인하면 좋아요.";
  }
  if (text.includes("커뮤니티")) {
    return "지금은 모델하우스 후기와 신혼 특공 소득 기준 질문이 가장 활발합니다. 커뮤니티 탭에서 바로 볼 수 있어요.";
  }
  return `${subscriptions[0].name}이 매칭률 ${subscriptions[0].matchScore}%로 가장 높습니다. 마감일은 ${subscriptions[0].deadline}입니다.`;
}

export function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<FloatingMessage[]>(starterMessages);

  const sendMessage = (value = inputValue) => {
    const text = value.trim();
    if (!text) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now(), sender: "user", text },
      { id: Date.now() + 1, sender: "ai", text: getReply(text) },
    ]);
    setInputValue("");
    setIsOpen(true);
  };

  return (
    <div className="fixed bottom-24 right-5 z-50 lg:bottom-6 lg:right-6">
      {isOpen && (
        <section className="mb-3 flex h-[520px] w-[calc(100vw-2rem)] max-w-[380px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-4 py-3 text-white">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="font-bold">청약내비 AI</p>
                <p className="text-xs text-slate-300">청약 · 금융 · 서류 상담</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-300 transition hover:bg-white/10 hover:text-white"
              aria-label="챗봇 닫기"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-auto bg-slate-50 p-4">
            {messages.map((message) => {
              const isUser = message.sender === "user";

              return (
                <div key={message.id} className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
                  {!isUser && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}
                  <div
                    className={`max-w-[78%] rounded-lg px-3 py-2 text-sm leading-6 ${
                      isUser ? "bg-slate-950 text-white" : "border border-slate-200 bg-white text-slate-700"
                    }`}
                  >
                    {message.text}
                  </div>
                  {isUser && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700">
                      <UserRound className="h-4 w-4" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="border-t border-slate-200 bg-white p-3">
            <div className="mb-3 flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => sendMessage(suggestion)}
                  className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600 transition hover:bg-blue-50 hover:text-blue-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
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
                className="h-10 flex-1 rounded-lg border border-slate-200 px-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                placeholder="궁금한 점을 입력하세요"
              />
              <button
                type="button"
                onClick={() => sendMessage()}
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700"
                aria-label="메시지 보내기"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="group flex h-14 items-center gap-3 rounded-full bg-blue-600 px-4 font-bold text-white shadow-xl shadow-blue-600/30 transition hover:-translate-y-0.5 hover:bg-blue-700"
      >
        <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-white/15">
          <MessageCircle className="h-5 w-5" />
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-400">
            <Sparkles className="h-2.5 w-2.5 text-slate-950" />
          </span>
        </span>
        <span className="hidden sm:inline">AI 상담</span>
      </button>
    </div>
  );
}
