"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { DengueData } from "@/lib/types";

interface DataContextValue {
  data: DengueData | null;
  loading: boolean;
  error: string | null;
}

const DataContext = createContext<DataContextValue>({ data: null, loading: true, error: null });

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "force-cache" });
  if (!response.ok) throw new Error(`โหลดข้อมูล ${path} ไม่สำเร็จ (${response.status})`);
  return response.json() as Promise<T>;
}

export function DataProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<DengueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      readJson("/data/predictions.json"),
      readJson("/data/weather_daily.json"),
      readJson("/data/prevention_actions.json"),
      readJson("/data/questions.json"),
      readJson("/data/options.json"),
      readJson("/data/assessment_rules.json"),
      readJson("/data/recommendations.json"),
      readJson("/data/meta.json"),
      readJson("/data/thailand_provinces.geojson"),
      readJson("/data/provinces_odpc4.geojson"),
    ]).then(([predictions, weather, preventionActions, questions, options, rules, recommendations, meta, thailandGeo, odpcGeo]) => {
      if (!active) return;
      setData({
        predictions: predictions as DengueData["predictions"],
        weather: weather as DengueData["weather"],
        preventionActions: preventionActions as DengueData["preventionActions"],
        questions: questions as DengueData["questions"],
        options: options as DengueData["options"],
        rules: rules as DengueData["rules"],
        recommendations: recommendations as DengueData["recommendations"],
        meta: meta as DengueData["meta"],
        thailandGeo: thailandGeo as DengueData["thailandGeo"],
        odpcGeo: odpcGeo as DengueData["odpcGeo"],
      });
      setLoading(false);
    }).catch((cause: unknown) => {
      if (!active) return;
      setError(cause instanceof Error ? cause.message : "เกิดข้อผิดพลาดในการโหลดข้อมูล");
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const value = useMemo(() => ({ data, loading, error }), [data, loading, error]);
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useDengueData() {
  return useContext(DataContext);
}
