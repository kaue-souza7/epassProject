import { api } from "./client";
import type { MyChildrenResponse } from "../types/responsavel";

export async function getMyChildren(): Promise<MyChildrenResponse[]> {
  const { data } = await api.get<MyChildrenResponse[]>("/students/my-children");
  return data;
}
