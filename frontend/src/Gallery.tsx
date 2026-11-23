import { useEffect, useState } from "react";
import { api, mediaUrl } from "./api";

/** Every image made or uploaded, newest first. Click to view large and download. */
export function Gallery({ refresh }: { refresh: number }) {
  const [images, setImages] = useState<{ name: string; time: number }[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { void api.gallery().then(setImages); }, [refresh]);

  return (
    <div className="gallery">
      <h2>Gallery <span className="muted">{images.length} images</span></h2>
      {images.length === 0 && <p className="muted">Images you make or upload collect here.</p>}
      <div className="wall">
        {images.map((m) => (
          <figure key={m.name} onClick={() => setOpen(m.name)}>
            <img src={mediaUrl(m.name)} alt="" loading="lazy" />
            <figcaption>{new Date(m.time * 1000).toLocaleString()}</figcaption>
          </figure>
        ))}
      </div>
      {open && (
        <div className="lightbox" onClick={() => setOpen(null)}>
          <img src={mediaUrl(open)} alt="" />
          <div className="actions" onClick={(e) => e.stopPropagation()}>
            <a className="primary" href={mediaUrl(open)} download={open}>Download</a>
            <button onClick={() => setOpen(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
