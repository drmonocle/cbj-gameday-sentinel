import React, { useState } from "react";
import { NewsItem, TeamPreset } from "../types";
import { ExternalLink, Newspaper, Clock } from "lucide-react";
import { openExternalUrl } from "../services/platform";

interface NewsTabProps {
  news: NewsItem[];
  team: TeamPreset;
  isLoading: boolean;
}

export const NewsTab: React.FC<NewsTabProps> = ({ news, team, isLoading }) => {
  const [filterSource, setFilterSource] = useState<string>("all");

  const filteredNews =
    filterSource === "all"
      ? news
      : news.filter((n) => n.source.toLowerCase().includes(filterSource.toLowerCase()));

  const formatAgo = (ts: number): string => {
    const secs = Math.max(0, Math.floor((Date.now() - ts) / 1000));
    if (secs < 60) return "just now";
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Source Filter Controls */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          {["all", "NHL.com", "ESPN"].map((src) => (
            <button
              key={src}
              onClick={() => setFilterSource(src)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition capitalize ${
                filterSource === src
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              {src === "all" ? "All Sources" : src}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-500 font-medium">
          {filteredNews.length} Stories Found
        </span>
      </div>

      {isLoading && news.length === 0 ? (
        <div className="p-8 text-center text-slate-400">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <p className="text-xs">Fetching latest team news feeds...</p>
        </div>
      ) : filteredNews.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {filteredNews.map((item) => (
            <div
              key={item.id}
              className="bg-[#0b1726] border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 flex flex-col justify-between transition group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2 text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 font-bold uppercase tracking-wider border border-blue-800/40">
                    {item.source}
                  </span>
                  <span className="text-slate-500 flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3 text-slate-600" />
                    <span>{formatAgo(item.ts)}</span>
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-100 group-hover:text-blue-400 transition leading-snug">
                  {item.title}
                </h4>

                {item.desc && (
                  <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                )}
              </div>

              <div className="mt-4 pt-2.5 border-t border-slate-800/60 flex items-center justify-end">
                <button
                  onClick={() => openExternalUrl(item.link)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-blue-400 hover:text-blue-300 transition cursor-pointer"
                >
                  <span>Read Article</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center text-slate-400 bg-[#0b1726] rounded-xl border border-slate-800">
          <p className="text-xs">No news stories found for this selection.</p>
        </div>
      )}
    </div>
  );
};
