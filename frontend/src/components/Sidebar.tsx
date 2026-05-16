"use client";

import { useState, useEffect } from "react";
import {
  BookOpen,
  RefreshCw,
  Upload,
  Globe,
  BarChart3,
  FileText,
  Database,
} from "lucide-react";
import { getStats, triggerSync, getSyncStatus, type IndexStats, type SyncStatus } from "@/lib/api";

interface SidebarProps {
  activeView: "chat" | "knowledge";
  onViewChange: (view: "chat" | "knowledge") => void;
  onOpenPDFUpload: () => void;
  onOpenWebIngest: () => void;
}

export function Sidebar({ activeView, onViewChange, onOpenPDFUpload, onOpenWebIngest }: SidebarProps) {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);

  const loadData = async () => {
    try {
      const [s, ss] = await Promise.all([getStats(), getSyncStatus()]);
      setStats(s);
      setSyncStatus(ss);
    } catch {
      // Backend not ready
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerSync();
      // Poll for completion
      setTimeout(async () => {
        await loadData();
        setSyncing(false);
      }, 3000);
    } catch {
      setSyncing(false);
    }
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-gray-100">
        <h1 className="text-lg font-bold text-gray-800 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-500" />
          Obsidian RAG
        </h1>
        <p className="text-xs text-gray-400 mt-1">知识库问答系统</p>
      </div>

      {/* Navigation */}
      <nav className="p-3 space-y-1">
        <button
          onClick={() => onViewChange("chat")}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            activeView === "chat"
              ? "bg-indigo-50 text-indigo-700 font-medium"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          对话问答
        </button>
        <button
          onClick={() => onViewChange("knowledge")}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            activeView === "knowledge"
              ? "bg-indigo-50 text-indigo-700 font-medium"
              : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          <Database className="w-4 h-4" />
          知识库管理
        </button>
      </nav>

      {/* Sync section */}
      <div className="px-4 py-3 border-t border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-500">Obsidian 同步</span>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="p-1 rounded hover:bg-gray-100 transition-colors"
            title="同步 Obsidian Vault"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-gray-500 ${syncing ? "animate-spin" : ""}`} />
          </button>
        </div>
        {syncStatus && (
          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>文件数</span>
              <span className="text-gray-700">{syncStatus.total_files}</span>
            </div>
            <div className="flex justify-between">
              <span>已索引</span>
              <span className="text-gray-700">{syncStatus.indexed_files}</span>
            </div>
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="px-4 py-3 border-t border-gray-100 space-y-2">
        <span className="text-xs font-medium text-gray-500">导入文档</span>
        <button
          onClick={onOpenPDFUpload}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-600 hover:bg-gray-50 border border-gray-200 transition-colors"
        >
          <Upload className="w-3.5 h-3.5" />
          上传 PDF 文献
        </button>
        <button
          onClick={onOpenWebIngest}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-gray-600 hover:bg-gray-50 border border-gray-200 transition-colors"
        >
          <Globe className="w-3.5 h-3.5" />
          导入网页内容
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="px-4 py-3 border-t border-gray-100 mt-auto">
          <span className="text-xs font-medium text-gray-500">索引统计</span>
          <div className="mt-2 space-y-1 text-xs text-gray-500">
            <div className="flex justify-between">
              <span>文档数</span>
              <span className="text-gray-700">{stats.total_documents}</span>
            </div>
            <div className="flex justify-between">
              <span>向量块数</span>
              <span className="text-gray-700">{stats.total_chunks}</span>
            </div>
            {Object.entries(stats.source_breakdown).map(([type, count]) => (
              <div key={type} className="flex justify-between">
                <span className="flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  {type}
                </span>
                <span className="text-gray-700">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
