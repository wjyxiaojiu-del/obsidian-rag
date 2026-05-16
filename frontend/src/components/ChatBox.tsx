"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { chatStream, type SourceRef } from "@/lib/api";
import { MessageBubble, type Message } from "./MessageBubble";
import { SourcePanel } from "./SourcePanel";

interface ChatBoxProps {
  sessionId?: string;
}

export function ChatBox({ sessionId }: ChatBoxProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentSources, setCurrentSources] = useState<SourceRef[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState(sessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setIsLoading(true);
    setCurrentSources([]);

    // Add user message
    const userMsg: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder for assistant
    const assistantIdx = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    await chatStream(
      question,
      currentSessionId,
      (sources, sid) => {
        setCurrentSources(sources);
        setCurrentSessionId(sid);
      },
      (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[assistantIdx] = {
            ...updated[assistantIdx],
            content: updated[assistantIdx].content + token,
          };
          return updated;
        });
      },
      () => setIsLoading(false),
      (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[assistantIdx] = {
            role: "assistant",
            content: `Error: ${err.message}`,
          };
          return updated;
        });
        setIsLoading(false);
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-full">
      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <div className="text-6xl mb-4">📚</div>
              <h2 className="text-xl font-semibold text-gray-600 mb-2">
                Obsidian RAG 知识库问答
              </h2>
              <p className="text-sm text-center max-w-md">
                基于你的 Obsidian 笔记、PDF 文献和网页内容，
                <br />
                使用 RAG 技术提供精准的知识问答
              </p>
              <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                {[
                  "我的笔记里关于XX写了什么？",
                  "帮我总结这篇文献的实验方法",
                  "最近的项目进展如何？",
                  "搜索关于XX的所有笔记",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); inputRef.current?.focus(); }}
                    className="px-4 py-2 rounded-xl border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-left text-gray-600"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="flex items-end gap-3 max-w-4xl mx-auto">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题... (Shift+Enter 换行)"
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-shadow text-sm"
              style={{ maxHeight: "120px" }}
              disabled={isLoading}
            />
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading}
              className="rounded-xl bg-indigo-500 p-3 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Source panel */}
      {currentSources.length > 0 && (
        <SourcePanel sources={currentSources} />
      )}
    </div>
  );
}
