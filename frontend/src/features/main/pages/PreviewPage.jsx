import React, { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import mockPreview from "../../../assets/mock/processed_preview.jpg";
import "./PreviewPage.css";
import Header from "../../../common/components/ui/Header";

export default function PreviewPage() {
  const navigate = useNavigate();
  const { state } = useLocation();

  const imageBlob = state?.imageBlob;
  const source = state?.source;

  useEffect(() => {
    if (!imageBlob) {
      navigate("/", { replace: true });
    }
  }, [imageBlob, navigate]);

  if (!imageBlob) return null;

  const handleConfirm = async () => {
    navigate("/result", {
      state: {
        imageUrl: mockPreview,
        source,
      },
    });
  };

  const previewUrl = URL.createObjectURL(imageBlob);

  return (
    <main className="page preview-page">
      <Header />
      <header className="container" style={{ paddingTop: '20px', paddingBottom: 0 }}>
        <h2 className="font-5 font-bold text-center">Confirm Photo</h2>
        <p className="font-9 text-center" style={{ color: 'var(--gray-700)' }}>
          Make sure the text is clear and readable.
        </p>
      </header>

      <section className="preview-image-section">
        <img src={previewUrl} alt="Preview" className="preview-image" />
      </section>

      <section className="preview-controls">
        <button className="button big color-main" onClick={handleConfirm}>
          Analyze Menu
        </button>
        <button className="button medium color-ghost" onClick={() => navigate(-1)}>
          Go Home
        </button>
      </section>
    </main>
  );
}
