import React, { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { navigateToPreview } from "../../../common/utils/navigateToPreview";
import "./UploadPage.css";

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    navigateToPreview(navigate, file, { source: "upload" });
  };

  return (
    <main className="page upload-page container">
      <div className="upload-zone">
        <h2 className="font-4 upload-title font-bold">Upload Menu Image</h2>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="upload-input-hidden"
          onChange={handleFileChange}
        />
        <button className="button big color-main" onClick={() => inputRef.current.click()}>
          Choose from Gallery
        </button>
      </div>
      <button className="button medium color-ghost" onClick={() => navigate(-1)}>
        Go Back
      </button>
    </main>
  );
}
