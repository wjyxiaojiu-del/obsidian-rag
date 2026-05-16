"use client";

import { FileText, Globe, BookOpen, ExternalLink } from "lucide-react";
import type { SourceRef } from "@/lib/api";

interface SourcePanelProps {
  sources: SourceRef[];
}

const sourceIcons: Record<string, React.ReactNode> = {
  obsidian: <BookOpen className="w-4 h-4" />,
  pdf: <FileText className="w-4 h-4" />,
  web: <Globe className="w-4 h-4" />,
};

const sourceColors: Record<string, string> = {
  obsidian: "bg-purple-100 text-purple-700 border-purple-200",
  pdf: "bg-red-100 text-red-700 border-red-200",
  web: "bg-blue-100 text-blue-700 border-blue-200",
};

export function SourcePanel({ sources }: SourcePanelProps) {
  return (
    <div className="w-80 border-l border-gray-200 bg-gray-50 overflow-y-auto">
      <div className="p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          引用来源 ({sources.length})
        </h3>
        <div className="space-y-3">
          {sources.map((src, i) => (
            <div
              key={src.doc_id}
              className="bg-white rounded-lg border border-gray-200 p-3 hover:shadow-sm transition-shadow"
            >
              {/* Header */}
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                    sourceColors[src.source_type] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {sourceIcons[src.source_type] || <FileText className="w-3 h-3" />}
                  {src.source_type}
                </span>
                <span className="text-xs text-gray-400 ml-auto">
                  {(src.score * 100).toFixed(0)}%
                </span>
              </div>

              {/* File name */}
              <p className="text-sm font-medium text-gray-800 mb-1 truncate">
                {src.file_name}
              </p>

              {/* Heading path */}
              {src.heading_path && (
                <p className="text-xs text-gray-500 mb-2">{src.heading_path}</p>
              )}

              {/* Chunk preview */}
              <p className="text-xs text-gray-600 leading-relaxed line-clamp-4">
                {src.chunk_text.slice(0, 200)}
                {src.chunk_text.length > 200 ? "..." : ""}
              </p>

              {/* Link */}
              {src.url && (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-2 text-xs text-indigo-500 hover:text-indigo-700"
                >
                  <ExternalLink className="w-3 h-3" />
                  打开原文
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
