import client from "./client";
import type {
  MethodologyData,
  PostListResponse,
  Stats,
  TopicDetail,
  TopicListResponse,
} from "../types";

export async function getTopics(): Promise<TopicListResponse> {
  const { data } = await client.get<TopicListResponse>("/api/topics");
  return data;
}

export async function getTopic(id: number): Promise<TopicDetail> {
  const { data } = await client.get<TopicDetail>(`/api/topics/${id}`);
  return data;
}

export async function getTopicPosts(
  topicId: number,
  page = 1,
  pageSize = 20
): Promise<PostListResponse> {
  const { data } = await client.get<PostListResponse>(
    `/api/topics/${topicId}/posts`,
    { params: { page, page_size: pageSize } }
  );
  return data;
}

export async function getStats(): Promise<Stats> {
  const { data } = await client.get<Stats>("/api/stats");
  return data;
}

export async function getMethodology(): Promise<MethodologyData> {
  const { data } = await client.get<MethodologyData>("/api/methodology");
  return data;
}
