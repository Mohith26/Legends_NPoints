import client from "./client";
import type { LabelDetail, LabelListResponse, LabelStats } from "../types";

export async function getLabels(): Promise<LabelListResponse> {
  const { data } = await client.get<LabelListResponse>("/api/labels");
  return data;
}

export async function getLabel(id: number): Promise<LabelDetail> {
  const { data } = await client.get<LabelDetail>(`/api/labels/${id}`);
  return data;
}

export async function getLabelStats(): Promise<LabelStats> {
  const { data } = await client.get<LabelStats>("/api/labels/stats");
  return data;
}
