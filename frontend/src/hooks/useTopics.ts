import { useQuery } from "@tanstack/react-query";
import {
  getMethodology,
  getStats,
  getTopic,
  getTopicPosts,
  getTopics,
} from "../api/topics";

export function useTopics() {
  return useQuery({
    queryKey: ["topics"],
    queryFn: getTopics,
  });
}

export function useTopic(id: number) {
  return useQuery({
    queryKey: ["topic", id],
    queryFn: () => getTopic(id),
    enabled: !!id,
  });
}

export function useTopicPosts(topicId: number, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["topicPosts", topicId, page, pageSize],
    queryFn: () => getTopicPosts(topicId, page, pageSize),
    enabled: !!topicId,
  });
}

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });
}

export function useMethodology() {
  return useQuery({
    queryKey: ["methodology"],
    queryFn: getMethodology,
  });
}
