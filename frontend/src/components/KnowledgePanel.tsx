"use client";

import { useState, useEffect, useRef } from "react";
import { Upload, Globe, Trash2, FileText, Loader2, CheckCircle, MessageSquare } from "lucide-react";
import { getStats, ingestPDF, ingestWeb, importWeChat, type IndexStats } from "@/lib/api";

export function KnowledgePanel() {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [webUrl, setWebUrl] = useState("");
  const [webTitle, setWebTitle] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [wxTalker, setWxTalker] = useState("");
  const [wxName, setWxName] = useState("");
  const [wxDistill, setWxDistill] = useState(true);

  const loadStats = async () => {
    try {
      const s = await getStats();
      setStats(s);
    } catch {}
  };

  useEffect(() => {
    loadStats();
  }, []);

  const showMsg = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handlePDFUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading("pdf");
    try {
      const result = await ingestPDF(file);
      showMsg("success", result.message);
      await loadStats();
    } catch (err) {
      showMsg("error", `上传失败: ${err}`);
    } finally {
      setLoading(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleWebIngest = async () => {
    if (!webUrl.trim()) return;

    setLoading("web");
    try {
      const result = await ingestWeb(webUrl, webTitle || undefined);
      showMsg("success", result.message);
      setWebUrl("");
      setWebTitle("");
      await loadStats();
    } catch (err) {
      showMsg("error", `导入失败: ${err}`);
    } finally {
      setLoading(null);
    }
  };

  const handleWeChatImport = async () => {
    if (!wxTalker.trim()) return;

    setLoading("wechat");
    try {
      const result = await importWeChat(wxTalker, wxName, wxDistill);
      showMsg("success", result.message);
      setWxTalker("");
      setWxName("");
      await loadStats();
    } catch (err) {
      showMsg("error", `导入失败: ${err}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">知识库管理</h2>

        {/* Status message */}
        {message && (
          <div
            className={`mb-4 p-3 rounded-lg text-sm flex items-center gap-2 ${
              message.type === "success"
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            <CheckCircle className="w-4 h-4" />
            {message.text}
          </div>
        )}

        {/* Stats overview */}
        {stats && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 mb-1">总文档数</p>
              <p className="text-2xl font-bold text-gray-800">{stats.total_documents}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 mb-1">向量块数</p>
              <p className="text-2xl font-bold text-gray-800">{stats.total_chunks}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 mb-1">数据源</p>
              <p className="text-2xl font-bold text-gray-800">
                {Object.keys(stats.source_breakdown).length}
              </p>
            </div>
          </div>
        )}

        {/* Upload PDF */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-red-500" />
            导入 PDF 文献
          </h3>
          <p className="text-xs text-gray-500 mb-3">
            上传 PDF 文件，系统会自动提取文本内容并建立索引
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handlePDFUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading === "pdf"}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 text-sm transition-colors disabled:opacity-50"
          >
            {loading === "pdf" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            选择 PDF 文件
          </button>
        </div>

        {/* Web ingest */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Globe className="w-4 h-4 text-blue-500" />
            导入网页内容
          </h3>
          <p className="text-xs text-gray-500 mb-3">
            输入网页 URL，系统会抓取页面内容并建立索引
          </p>
          <div className="space-y-2">
            <input
              type="url"
              value={webUrl}
              onChange={(e) => setWebUrl(e.target.value)}
              placeholder="https://example.com/article"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <input
              type="text"
              value={webTitle}
              onChange={(e) => setWebTitle(e.target.value)}
              placeholder="标题（可选）"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              onClick={handleWebIngest}
              disabled={!webUrl.trim() || loading === "web"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-sm transition-colors disabled:opacity-50"
            >
              {loading === "web" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Globe className="w-4 h-4" />
              )}
              抓取并索引
            </button>
          </div>
        </div>

        {/* WeChat import */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-green-500" />
            导入微信聊天记录
          </h3>
          <p className="text-xs text-gray-500 mb-3">
            通过 WeFlow HTTP API 导入微信聊天记录。需先在本机运行 WeFlow 并开启 HTTP 服务。
            {wxDistill && " 开启蒸馏模式会用 LLM 提取关键信息，生成结构化笔记。"}
          </p>
          <div className="space-y-2">
            <input
              type="text"
              value={wxTalker}
              onChange={(e) => setWxTalker(e.target.value)}
              placeholder="wxid_xxx（联系人/群的 wxid）"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <input
              type="text"
              value={wxName}
              onChange={(e) => setWxName(e.target.value)}
              placeholder="备注名（可选，如：导师、课题组）"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={wxDistill}
                onChange={(e) => setWxDistill(e.target.checked)}
                className="rounded"
              />
              蒸馏模式（推荐，用 LLM 提取关键信息）
            </label>
            <button
              onClick={handleWeChatImport}
              disabled={!wxTalker.trim() || loading === "wechat"}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 text-sm transition-colors disabled:opacity-50"
            >
              {loading === "wechat" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <MessageSquare className="w-4 h-4" />
              )}
              {wxDistill ? "蒸馏并导入" : "导入原始聊天"}
            </button>
          </div>
        </div>

        {/* Source breakdown */}
        {stats && Object.keys(stats.source_breakdown).length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">数据源分布</h3>
            <div className="space-y-2">
              {Object.entries(stats.source_breakdown).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5" />
                    {type === "obsidian" ? "Obsidian 笔记" : type === "pdf" ? "PDF 文献" : type === "web" ? "网页" : type === "wechat" ? "微信聊天" : type}
                  </span>
                  <span className="text-sm font-medium text-gray-800">{count} 块</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
