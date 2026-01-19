// 카메라 사용

import { useEffect, useRef, useState } from "react";

export default function useCamera() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const initCamera = async () => {
      try {
        if (streamRef.current) return;

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });

        if (!mounted) return;

        streamRef.current = stream;

        const video = videoRef.current;
        if (!video) return;

        video.srcObject = stream;

        video.onloadedmetadata = async () => {
          try {
            await video.play();
            if (mounted && video.videoWidth > 0) {
              setIsReady(true);
            }
          } catch {
            setError("PLAY_FAILED");
          }
        };
      } catch (err) {
        setError("DENIED");
      }
    };

    initCamera();

    return () => {
      mounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const capture = async () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) {
      console.warn("Capture blocked: video not ready");
      return null;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    return new Promise((resolve) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            console.warn("Blob creation failed");
            resolve(null);
          }
          resolve(blob);
        },
        "image/jpeg",
        0.9
      );
    });
  };

  return {
    videoRef,
    isReady,
    error,
    capture,
  };
}
