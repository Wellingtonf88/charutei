// Hooks React Query — estado servidor (cache, retries, invalidação). Telas consomem estes,
// nunca o fetch direto. Token vem do AuthContext.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useToken } from "../auth/context";
import { recordAdded } from "../store/aging";
import {
  addToCollection,
  ask,
  AskResult,
  Collection,
  getCatalog,
  getCollection,
  recognizeBand,
  RecognitionResult,
} from "./client";

// Tipo de dados inferido do `queryFn` (v5) — evita `data: any` da forma com generic único.
export function useCollection() {
  const token = useToken();
  return useQuery({
    queryKey: ["collection"],
    queryFn: () => getCollection(token),
  });
}

export function useCatalog() {
  const token = useToken();
  return useQuery({
    queryKey: ["catalog"],
    queryFn: () => getCatalog(token),
    staleTime: 1000 * 60 * 10, // catálogo muda pouco
  });
}

export function useRecognize() {
  const token = useToken();
  return useMutation<
    RecognitionResult,
    Error,
    { ref: string; visualText?: string; dataB64?: string }
  >({
    mutationFn: (input) => recognizeBand(token, input),
  });
}

export function useAddToCollection() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation<Collection, Error, string>({
    mutationFn: (cigarId) => addToCollection(token, cigarId, `add-${cigarId}-${Date.now()}`),
    onSuccess: (col, cigarId) => {
      qc.setQueryData(["collection"], col);
      void recordAdded(cigarId); // registra aging + agenda lembrete de descanso
    },
  });
}

export function useAsk() {
  const token = useToken();
  return useMutation<AskResult, Error, string>({
    mutationFn: (q) => ask(token, q),
  });
}
