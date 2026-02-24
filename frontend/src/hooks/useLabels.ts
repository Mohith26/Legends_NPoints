import { useQuery } from "@tanstack/react-query";
import { getLabel, getLabels, getLabelStats } from "../api/labels";

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

export function useLabelStats() {
  return useQuery({
    queryKey: ["labelStats"],
    queryFn: getLabelStats,
  });
}
