"use client";

import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatBox } from "@/components/ChatBox";
import { KnowledgePanel } from "@/components/KnowledgePanel";

export default function Home() {
  const [activeView, setActiveView] = useState<"chat" | "knowledge">("chat");

  return (
    <div className="flex h-screen">
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        onOpenPDFUpload={() => setActiveView("knowledge")}
        onOpenWebIngest={() => setActiveView("knowledge")}
      />
      <main className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
        {activeView === "chat" ? <ChatBox /> : <KnowledgePanel />}
      </main>
    </div>
  );
}
