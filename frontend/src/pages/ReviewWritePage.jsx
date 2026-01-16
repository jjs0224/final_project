import { useState } from "react";

export default function ReviewWritePage() {
  const [step, setStep] = useState("upload"); // upload -> confirm -> write -> done
  const [receipt, setReceipt] = useState(null);
  const [review, setReview] = useState("");
  const [rating, setRating] = useState(5);
  const [loading, setLoading] = useState(false);
  const [imageFile, setImageFile] = useState(null);

  const runReceiptOCR = async () => {
    if (!imageFile) {
      alert("Please select an image first");
      return;
    }

    console.log("[DEBUG] Image info:", {
      name: imageFile.name,
      size: imageFile.size,
      type: imageFile.type,
    });

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("image", imageFile); // backend key 이름 중요

      const res = await fetch("/upload/receipt", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("OCR failed");

      const data = await res.json();
      console.log("[DEBUG] OCR response JSON:", data);

      setReceipt(data);
      setStep("confirm");
    } catch (err) {
      console.error(err);
      alert("Failed to load receipt");
    } finally {
      setLoading(false);
    }
  };


  const submitReview = () => {

    const total = rating
//     setFinalRating(total);

    setStep("done");

    const payload = {

      review_title: `${receipt.store_name} review`,
      // review_menu: receipt[0].menu_name,
      review_content: review,
      rating: rating,
      location: receipt.address,
      member_id: 5,

    };
    console.log("REVIEW PAYLOAD:", payload)
  }

  return (
    <div>
      {/* LEFT COLUMN: Persistent Controls */}
      <div>
        <h2>1. Upload & Detect</h2>
        <input
            type="file" 
            accept="image/*" 
            disabled={step !== "upload"} 
            onChange={(e) => setImageFile(e.target.files[0])}/>
        <button 
          onClick={runReceiptOCR} 
          disabled={!imageFile || step !== "upload" || loading}
        >
          {loading ? "Analyzing..." : "Upload receipt"}
        </button>

        {/* This section stays visible once data exists */}
        {receipt && (
          <div style={{ marginTop: "40px", opacity: step === "upload" ? 0.5 : 1 }}>
            <h2>2. Receipt Details</h2>
            <div style={{ background: "#f9f9f9", padding: "15px", borderRadius: "8px" }}>
              <h3>{receipt.store_name}</h3>
              <p>{receipt.address}</p>
              <h4>Menu Items:</h4>
              <ul>
                {receipt.menu_name?.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
              {step === "confirm" && (
                <button onClick={() => setStep("write")}>Confirm Details</button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: Review Writing (Visible only after confirmation) */}
      <div>
        <h2>3. Your Review</h2>
        <textarea
          placeholder="Write your review here"
          value={review}
          onChange={(e) => setReview(e.target.value)}
          rows={10}
          style={{ width: "100%" }}
        />
        <div style={{ marginTop: "10px" }}>
          <label>Rating: </label>
          <input 
            type="number" 
            min={1} max={10} 
            value={rating} 
            onChange={(e) => setRating(Number(e.target.value))} 
          />
          <p>We will also calculate AI rating based on your review. <br />
            This score will be used as decimal point of your rating.<br />
            E.g: your score:8, AI_score:3 => final score: 8.3
          </p>
            
        </div>
        <button 
          onClick={submitReview}
        >
          Post Review
        </button>
      </div>
    </div>
  );

}