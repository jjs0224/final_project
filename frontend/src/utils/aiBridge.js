export async function readReceiptResult() {
  const res = await fetch("/receipt_to_store.json", {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("Failed to load receipt JSON");
  }

  return await res.json();
}
