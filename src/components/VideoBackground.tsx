"use client";

import { useEffect, useRef } from "react";

export function VideoBackground() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const fadeFrameRef = useRef<number>(0);
  const isFadingOut = useRef<boolean>(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // ensure it starts at 0 opacity
    video.style.opacity = "0";

    const animateFade = (
      startTime: number,
      targetOpacity: number,
      duration: number,
      onComplete?: () => void
    ) => {
      const startOpacity = parseFloat(video.style.opacity) || 0;
      
      const step = (timestamp: number) => {
        const elapsed = timestamp - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentOpacity = startOpacity + (targetOpacity - startOpacity) * progress;
        video.style.opacity = currentOpacity.toFixed(3);
        
        if (progress < 1) {
          fadeFrameRef.current = requestAnimationFrame(step);
        } else {
          if (onComplete) onComplete();
        }
      };
      
      cancelAnimationFrame(fadeFrameRef.current);
      fadeFrameRef.current = requestAnimationFrame(step);
    };

    const handleTimeUpdate = () => {
      // time remaining before end
      const timeLeft = video.duration - video.currentTime;
      
      if (timeLeft <= 0.55 && !isFadingOut.current) {
        isFadingOut.current = true;
        // Fade out
        animateFade(performance.now(), 0, 250);
      }
    };

    const handlePlaying = () => {
      // Fade in on load / loop start
      isFadingOut.current = false;
      animateFade(performance.now(), 1, 250);
    };

    const handleEnded = () => {
      video.style.opacity = "0";
      setTimeout(() => {
        if (video) {
          video.currentTime = 0;
          video.play().catch(e => console.error("Play error:", e));
        }
      }, 100);
      // Wait for play to fire handlePlaying which will fade it in again
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("playing", handlePlaying);
    video.addEventListener("ended", handleEnded);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("playing", handlePlaying);
      video.removeEventListener("ended", handleEnded);
      cancelAnimationFrame(fadeFrameRef.current);
    };
  }, []);

  return (
    <>
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[115vw] h-[115vh] z-[-2] overflow-hidden pointer-events-none">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-full object-cover object-top"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260329_050842_be71947f-f16e-4a14-810c-06e83d23ddb5.mp4"
        />
      </div>
      <div className="fixed inset-0 z-[-1] bg-black/42 pointer-events-none mix-blend-multiply" />
    </>
  );
}
