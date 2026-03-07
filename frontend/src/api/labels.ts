import client from "./client";
import type { LabelDetail, LabelListResponse, LabelStats, PostListResponse } from "../types";

export async function getLabels(): Promise<LabelListResponse> {
  const { data } = await client.get<LabelListResponse>("/api/labels");
  return data;
}

export async function getLabel(id: number): Promise<LabelDetail> {
  const { data } = await client.get<LabelDetail>(`/api/labels/${id}`);
  return data;
}

export async function getLabelPosts(
  labelId: number,
  page = 1,
  pageSize = 20
): Promise<PostListResponse> {
  const { data } = await client.get<PostListResponse>(
    `/api/labels/${labelId}/posts`,
    { params: { page, page_size: pageSize } }
  );
  return data;
}

export async function getLabelStats(): Promise<LabelStats> {
  const { data } = await client.get<LabelStats>("/api/labels/stats");
  return data;
}
