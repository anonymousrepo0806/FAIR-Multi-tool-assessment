import { useState } from "react";
import HomePage from "./pages/HomePage";
import CorpusPage from "./pages/CorpusPage";
import GalleryPage from "./pages/GalleryPage";
import Dashboard from "./pages/Dashboard";
import SnapshotsPage from "./pages/SnapshotsPage";
import MappingPage from "./pages/MappingPage";
import SparqlPage from "./pages/SparqlPage";
import "./index.css";


export default function App() {
  const [page, setPage] = useState("home");


  const [gallerySource, setGallerySource] = useState(null);

  const NAV_ITEMS = [
    { key: "home", label: "Home", icon: "🏠" },
    { key: "gallery", label: "FAIR Results", icon: "📊" },
    { key: "cloud", label: "Search", icon: "🔍" },
    { key: "assess", label: "New Assessment", icon: "⚡" },
    { key: "snapshots", label: "Snapshots", icon: "🗂️" },
    { key: "mapping", label: "FAIR Mapping", icon: "🧭" },
    { key: "sparql", label: "SPARQL", icon: "🔎" },
  ];

  function goTo(key) {
    if (key === "gallery") setGallerySource(null);
    setPage(key);
  }

  function goToGalleryForCategory(categoryKey) {
    setGallerySource(`cat:${categoryKey}`);
    setPage("gallery");
  }

  return (
    <div>
      <div className="app-bg-blobs" aria-hidden="true">
        <span className="app-bg-blob app-bg-blob--1" />
        <span className="app-bg-blob app-bg-blob--2" />
        <span className="app-bg-blob app-bg-blob--3" />
      </div>

      <nav className="app-nav">
        <button className="app-nav__brand" onClick={() => setPage("home")}>
          <span className="app-nav__logo">F</span>
          <span>FAIR Multi-Assessor</span>
        </button>
        <div className="app-nav__links">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={page === item.key ? "active" : ""}
              onClick={() => goTo(item.key)}
            >
              <span className="app-nav__icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {page === "home" && <HomePage onSelectCategory={goToGalleryForCategory} />}
      {page === "cloud" && <CorpusPage />}
      {page === "gallery" && <GalleryPage initialSource={gallerySource} />}
      {page === "assess" && <Dashboard />}
      {page === "snapshots" && <SnapshotsPage />}
      {page === "mapping" && <MappingPage />}
      {page === "sparql" && <SparqlPage />}
    </div>
  );
}
