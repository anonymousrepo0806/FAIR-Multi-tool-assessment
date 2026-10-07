import { useState } from "react";
import { toPng } from "html-to-image";
import { jsPDF } from "jspdf";


export default function ChartDownloadButtons({ targetRef, filename = "chart" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function capture() {
    if (!targetRef.current) throw new Error("Chart not ready yet");


    return toPng(targetRef.current, { backgroundColor: "#ffffff", pixelRatio: 2 });
  }

  async function downloadPng() {
    setBusy(true);
    setError("");
    try {
      const dataUrl = await capture();
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `${filename}.png`;
      a.click();
    } catch (e) {
      setError(e.message || "Could not export PNG");
    } finally {
      setBusy(false);
    }
  }

  async function downloadPdf() {
    setBusy(true);
    setError("");
    try {
      const dataUrl = await capture();
      const img = new Image();
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = dataUrl;
      });
      const orientation = img.width >= img.height ? "landscape" : "portrait";
      const pdf = new jsPDF({ orientation, unit: "pt", format: "a4" });
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 24;
      const maxW = pageWidth - margin * 2;
      const maxH = pageHeight - margin * 2;
      const scale = Math.min(maxW / img.width, maxH / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      pdf.addImage(dataUrl, "PNG", (pageWidth - w) / 2, (pageHeight - h) / 2, w, h);
      pdf.save(`${filename}.pdf`);
    } catch (e) {
      setError(e.message || "Could not export PDF");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chart-download">
      <button className="chart-download__btn" onClick={downloadPng} disabled={busy}>
        ⬇ PNG
      </button>
      <button className="chart-download__btn" onClick={downloadPdf} disabled={busy}>
        ⬇ PDF
      </button>
      {error && <span className="chart-download__error">{error}</span>}
    </div>
  );
}
