import { useState } from "react";
import { readReceiptResult } from "../utils/aiBridge";

export default function ReviewWritePage() {
  const [step, setStep] = useState("upload");
  const [receipt, setReceipt] = useState(null);
  const [error, setError] = useState(null);
  const [review, setReview] = useState("");
  const [rating, setRating] = useState(5);
//   const [finalRating, setFinalRating] = useState(null);

  const runReceiptOCR = async () => {
    try {
      const data = await readReceiptResult();
      console.log("RECEIPT DATA:", data);
      setReceipt(data);
      setStep("confirm");
    } catch (err) {
      console.error(err);
      setError("Failed to load receipt");
    }
  };

  const submitReview = () => {

    const total = rating

//     setFinalRating(total);
    setStep("done");

  }

//   const payload = {
//       review_title: `${receipt[0].store_name} review`,
//       review_menu: receipt[0].menu_name,
//       review_content: review,
//       rating: rating,
//       location: receipt[0].address,
//       member_id: 5,
//
//   };


  return (
    <div>
      <h2>Review Write Page</h2>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {step === "upload" && (
        <>
          <button onClick={runReceiptOCR}>Detect Receipt</button>
        </>
      )}

      {step === "confirm" && receipt && (
        <>
          <h3>{receipt[0].store_name}</h3>
          <p>{receipt[0].address}</p>
          <p>{receipt[0].city}</p>
          <h4>Menu</h4>
          <ul>
            {receipt[0].menu_name?.map((item, i) => (
                <li key={i}>{item}</li>
            ))}
          </ul>

          <p>Please confirm if following details are correct</p>
          <button onClick={() => setStep("write")}>Confirm</button>
        </>
      )}


      {step === "write" && (
        <>
            <h3>Write your review</h3>
            <textarea
                placeholder="Write review here"
                value={review}
                onChange={(e) => setReview(e.target.value)}
                rows={5}
            />
            <label>Rating (1-10): </label>
            <input
                type="number"
                min={1}
                max={10}
                value={rating}
                onChange={(e) => setRating(Number(e.target.value))}
            />
            <button onClick={submitReview}>
                Add Review
            </button>
        </>


      )}
    </div>
  );
}
