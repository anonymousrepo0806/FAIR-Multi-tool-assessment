
import client from "./client";

export async function fetchMappingReference() {
  const { data } = await client.get("/mapping/reference");
  return data;
}
