import { useState } from "react";
import { readReceiptResult } from "../utils/aiBridge";

export default function ReviewWritePage() {
  const [step, setStep] = useState("upload"); // upload -> confirm -> write -> done
  const [receipt, setReceipt] = useState(null);
  const [review, setReview] = useState("");
  const [rating, setRating] = useState(5);
  const [loading, setLoading] = useState(false);

  const runReceiptOCR = async () => {
    setLoading(true);
    try {
      const data = await readReceiptResult();
      setReceipt(data);
      setStep("confirm");
    } catch (err) {
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

      review_title: `${receipt[0].store_name} review`,
      // review_menu: receipt[0].menu_name,
      review_content: review,
      rating: rating,
      location: receipt[0].address,
      member_id: 5,

    };
    console.log("REVIEW PAYLOAD:", payload)
  }

  return (
    <div>
      {/* LEFT COLUMN: Persistent Controls */}
      <div>
        <h2>1. Upload & Detect</h2>
        <input type="file" accept="image/*" disabled={step !== "upload"} />
        <button 
          onClick={runReceiptOCR} 
          disabled={step !== "upload" || loading}
        >
          {loading ? "Analyzing..." : "Detect Receipt"}
        </button>

        {/* This section stays visible once data exists */}
        {receipt && (
          <div style={{ marginTop: "40px", opacity: step === "upload" ? 0.5 : 1 }}>
            <h2>2. Receipt Details</h2>
            <div style={{ background: "#f9f9f9", padding: "15px", borderRadius: "8px" }}>
              <h3>{receipt[0].store_name}</h3>
              <p>{receipt[0].address}</p>
              <h4>Menu Items:</h4>
              <ul>
                {receipt[0].menu_name?.map((item, i) => <li key={i}>{item}</li>)}
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