// TEMPLATE: example
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Item {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

interface CreateItemInput {
  name: string;
  description?: string | null;
}

const ITEMS_KEY = ["items"] as const;

export function useItems() {
  return useQuery({
    queryKey: ITEMS_KEY,
    queryFn: () => api.get<Item[]>("/items"),
  });
}

export function useCreateItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateItemInput) => api.post<Item>("/items", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ITEMS_KEY }),
  });
}
