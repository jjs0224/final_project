import React from "react";
import { useNavigate } from "react-router-dom";
import useCamera from "../../../common/utils/useCamera";
import { navigateToPreview } from "../../../common/utils/navigateToPreview";
import "./CameraPage.css";
import Header from "../../../common/components/ui/Header";

export default function CameraPage() {
  const navigate = useNavigate();
  const { videoRef, isReady, error, capture } = useCamera();

  const handleCapture = async () => {
    if (!isReady) return;
    const blob = await capture();
    if (!blob) return;
    navigateToPreview(navigate, blob, { source: "camera" });
  };

  const handleCancel = () => navigate(-1);

  if (error) {
    return (
      <main className="camera-page">
        <div className="camera-error container">
          <p className="font-7 font-medium">
            {error === "DENIED"
              ? "Please enable camera access in your browser settings."
              : "Cannot access camera. Another app might be using it."}
          </p>
          <button className="button big color-ghost" onClick={handleCancel}>
            Go Back
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="camera-page">
      <section className="camera-view">
        {!isReady && <p>Initializing camera...</p>}
        <video ref={videoRef} className="camera-video" playsInline muted />
      </section>

      <section className="camera-controls">
        <button className="button big color-main" onClick={handleCapture} disabled={!isReady}>
          Take Photo
        </button>
        <button className="button medium color-ghost" onClick={handleCancel}>
          Cancel
        </button>
      </section>
    </main>
  );
}
