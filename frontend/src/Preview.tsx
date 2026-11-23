import { isImage, mediaUrl, type Json } from "./api";

/** Shows any output value: images, lists of things, text, numbers. */
export function Preview({ value, big = false }: { value: Json; big?: boolean }) {
  if (isImage(value)) return <img className={big ? "shot big" : "shot"} src={mediaUrl(value)} alt="" loading="lazy" />;
  if (Array.isArray(value)) {
    return <div className="items">{value.map((v, i) => <Preview key={i} value={v} big={big} />)}</div>;
  }
  if (value !== null && typeof value === "object") return <pre className="text">{JSON.stringify(value, null, 1)}</pre>;
  return <p className={big ? "text big" : "text"}>{String(value)}</p>;
}
