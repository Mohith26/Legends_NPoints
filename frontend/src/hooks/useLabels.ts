import { useQuery } from "@tanstack/react-query";
import { getLabel, getLabels, getLabelPosts, getLabelStats } from "../api/labels";

export function useLabels() {
  return useQuery({
    queryKey: ["labels"],
    queryFn: getLabels,
  });
}

export function useLabel(id: number) {
  return useQuery({
    queryKey: ["label", id],
    queryFn: () => getLabel(id),
    enabled: !!id,
  });
}

export function useLabelPosts(labelId: number, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ["labelPosts", labelId, page, pageSize],
    queryFn: () => getLabelPosts(labelId, page, pageSize),
    enabled: !!labelId,
  });
}

export function useLabelStats() {
  return useQuery({
    queryKey: ["labelStats"],
    queryFn: getLabelStats,
  });
}
