import { Play, Pause } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface AudioPlayerProps {
  title: string;
  subtitle: string;
  duration?: string;
  src?: string;
}

export const AudioPlayer = ({ title, subtitle, duration, src }: AudioPlayerProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!src) return;

    // Convert data URL to blob URL for better browser compatibility
    let blobUrl: string | null = null;
    
    if (src.startsWith("data:audio/")) {
      try {
        // Extract base64 data from data URL
        const base64Data = src.split(",")[1];
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: "audio/mpeg" });
        blobUrl = URL.createObjectURL(blob);
        blobUrlRef.current = blobUrl;
      } catch (error) {
        console.error("[AudioPlayer] Failed to convert data URL to blob:", error);
        return;
      }
    } else {
      // Regular URL, use as-is
      blobUrl = src;
    }

    const audio = new Audio(blobUrl);
    audioRef.current = audio;

    const handleEnded = () => {
      setIsPlaying(false);
    };

    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.pause();
      audio.removeEventListener("ended", handleEnded);
      if (blobUrlRef.current && blobUrlRef.current.startsWith("blob:")) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      audioRef.current = null;
      blobUrlRef.current = null;
    };
  }, [src]);

  const togglePlay = () => {
    if (!src) return;
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      void audio.play();
      setIsPlaying(true);
    }
  };

  const disabled = !src;

  return (
    <div className="audio-player group">
      <button
        onClick={togglePlay}
        className="play-button"
        aria-label={isPlaying ? "Pause" : "Play"}
        disabled={disabled}
      >
        {isPlaying ? (
          <Pause className="w-5 h-5" />
        ) : (
          <Play className="w-5 h-5 ml-0.5" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-foreground truncate">{title}</h4>
        <p className="text-sm text-muted-foreground">
          {subtitle}
          {disabled && " (audio not available yet)"}
        </p>
      </div>
      {duration && (
        <span className="text-sm text-muted-foreground font-medium">{duration}</span>
      )}
    </div>
  );
};
