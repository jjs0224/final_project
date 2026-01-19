
import React, { useState } from "react";
import { mockUser } from "../../assets/mock/mockData";

export default function ReviewWritePage() {
  const [step, setStep] = useState("upload"); // upload -> confirm -> write -> done
  const [receipt, setReceipt] = useState(null);
  const [review, setReview] = useState("");
  const [rating, setRating] = useState(5);
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const runReceiptOCR = async () => {
    if (!imageFile) {
      alert("이미지를 선택해주세요");
      return;
    }
    setLoading(true);
    try {
      // 실제 서버 호출 예시
      // const formData = new FormData();
      // formData.append("image", imageFile);
      // const res = await fetch("/upload/receipt", { method: "POST", body: formData });
      // const data = await res.json();

      // 목업 데이터
      const data = {
        store_name: "Ebi Don Store",
        address: "Seoul, Korea",
        menu_name: ["Ebi Don", "Tempura"],
      };

      setReceipt(data);
      setStep("confirm");
    } catch (err) {
      console.error(err);
      alert("영수증 분석 실패");
    } finally {
      setLoading(false);
    }
  };

  const submitReview = () => {
    const payload = {
      review_title: `${receipt.store_name} review`,
      review_content: review,
      rating,
      location: receipt.address,
      member_id: mockUser.member_id,
    };
    console.log("REVIEW PAYLOAD:", payload);
    setStep("done");
    alert("리뷰 작성 완료 (콘솔 확인)");
  };

  return (
    <div className="reviewWritePage">
      {/* 1. Upload & Detect */}
      <h2>1. 영수증 업로드</h2>
      <input
        type="file"
        accept="image/*"
        disabled={step !== "upload"}
        onChange={(e) => setImageFile(e.target.files[0])}
      />
      <button
        disabled={!imageFile || step !== "upload" || loading}
        onClick={runReceiptOCR}
      >
        {loading ? "분석 중..." : "업로드"}
      </button>

      {/* 2. Receipt 확인 */}
      {receipt && (
        <div style={{ marginTop: 20, opacity: step === "upload" ? 0.5 : 1 }}>
          <h3>영수증 확인</h3>
          <div>
            <p>가게명: {receipt.store_name}</p>
            <p>주소: {receipt.address}</p>
            <p>메뉴: {receipt.menu_name.join(", ")}</p>
            {step === "confirm" && (
              <button onClick={() => setStep("write")}>확인 완료</button>
            )}
          </div>
        </div>
      )}

      {/* 3. Review 작성 */}
      {step === "write" && (
        <div style={{ marginTop: 20 }}>
          <h3>리뷰 작성</h3>
          <textarea
            rows={5}
            value={review}
            onChange={(e) => setReview(e.target.value)}
            placeholder="리뷰 작성"
            style={{ width: "100%" }}
          />
          <div>
            <label>평점: </label>
            <input
              type="number"
              min={1}
              max={10}
              value={rating}
              onChange={(e) => setRating(Number(e.target.value))}
            />
          </div>
          <button onClick={submitReview}>리뷰 제출</button>
        </div>
      )}

      {step === "done" && <div>리뷰 작성 완료!</div>}
    </div>
  );
}
